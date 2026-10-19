# On My Own Terms

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2024 |
| **Category** | ID |
| **Difficulty** | Unknown |
| **Points** | N/A |
| **Flag** | `poctf{uwsp_w3_4r3_wh47_w3_7h1nk}` |
| **Status** | Solved |

---

## Challenge Overview

A web challenge where access to the flag is controlled by a cookie-based role check. The application sets a `role` cookie with a non-admin value. Modifying the cookie value to `admin` via the browser's developer tools reveals the flag.

---

## Objective

Escalate privileges by manipulating the `role` cookie to gain admin access and retrieve the flag.

---

## Methodology

### Step 1: Visit the challenge page

Navigating to the challenge URL shows a restricted page. The application assigns a `role` cookie to the browser session.

### Step 2: Inspect cookies

Open the browser's developer tools (F12), navigate to the **Application** tab, and examine the Cookies section. A cookie named `role` is present with a non-admin value (e.g., `user` or `guest`).

### Step 3: Modify the cookie

Change the `role` cookie value to `admin`:

1. In DevTools > Application > Cookies, double-click the `role` cookie value
2. Replace it with `admin`
3. Refresh the page

Alternatively, via the console:

```js
document.cookie = "role=admin";
location.reload();
```

### Step 4: Retrieve the flag

After refreshing with the modified cookie, the page displays the flag.

---

## Flag

```
poctf{uwsp_w3_4r3_wh47_w3_7h1nk}
```

---

## Lessons Learned

| # | Lesson | Detail |
|---|--------|--------|
| 1 | Client-side cookies are untrusted | Users can freely modify cookie values |
| 2 | Role checks must be server-side | Cookie-based roles without server validation are trivially bypassed |
| 3 | DevTools Application tab is powerful | Cookies, storage and session data are editable in real time |
| 4 | Never trust client state | Authorization decisions must rely on server-side session data |

---

## MITRE ATT&CK Mapping

| Tactic            | Technique                          | ID        |
|-------------------|------------------------------------|-----------|
| Privilege Escalation | Exploitation for Privilege Escalation | T1068 |
| Credential Access | Steal Web Session Cookie           | T1539     |
| Defense Evasion   | Modify Authentication Process      | T1556     |

---

## OWASP Top 10 2021 Mapping

| Category | ID    | Relevance |
|----------|-------|-----------|
| Broken Access Control     | A01:2021 | Privilege escalation via cookie tampering |
| Security Misconfiguration | A05:2021 | Role stored in client-side cookie |

---

## Remediation

### Technical Fixes
- Store role/authorization data in server-side sessions, not cookies
- Use signed or encrypted session tokens (e.g., JWT with HMAC)
- Validate all authorization checks on the server
- Set cookies with HttpOnly, Secure, and SameSite flags

### OWASP Top 10 2021
- **A01 Broken Access Control**: enforce access control server-side; never trust client-supplied role claims
- **A05 Security Misconfiguration**: use secure cookie attributes and server-side session management

### D3FEND Countermeasures
| Technique                  | ID        |
|----------------------------|-----------|
| Credential Hardening       | D3-CH     |
| Application Hardening      | D3-AH     |

### NIST CSF 2.0
| Function | Category                | Subcategory |
|----------|------------------------|-------------|
| Protect  | Identity Management and Access Control | PR.AA-01 |
| Protect  | Data Security          | PR.DS-01    |

### NIST SP 800-53 Rev. 5
| Control     | Description                          |
|-------------|--------------------------------------|
| AC-3        | Access Enforcement                   |
| AC-6        | Least Privilege                      |
| SC-23       | Session Authenticity                 |

### C2M2
| Practice Area               | MIL |
|-----------------------------|-----|
| Access Management           | MIL2 |

### CWE
| ID      | Name                                     |
|---------|------------------------------------------|
| CWE-565 | Reliance on Cookies without Validation and Integrity Checking |
| CWE-639 | Authorization Bypass Through User-Controlled Key |

---

## References

- Based on solve approach from [Jdwalli](https://github.com/Jdwalli/ctf-writeups)
- [OWASP Top 10 2021](https://owasp.org/Top10/)

---

## Closing

Thanks guys!! (❍ᴥ❍ʋ)

We are what we think, and in this case, the server thinks we're admin because we said so in a cookie. A reminder that trust must be earned on the server side, not granted by the client.

[![Instagram](https://img.shields.io/badge/-Instagram-E4405F?style=flat&logo=instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/-LinkedIn-0077B5?style=flat&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/-X-000000?style=flat&logo=x&logoColor=white)](https://x.com/mrhenrike)
