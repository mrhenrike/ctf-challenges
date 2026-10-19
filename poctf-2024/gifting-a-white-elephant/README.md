# Gifting a White Elephant

| Detail      | Value                                      |
|-------------|--------------------------------------------|
| CTF         | Pointer Overflow CTF 2024                  |
| Category    | Web                                        |
| Difficulty  | Medium                                     |
| Points      | 200                                        |
| Flag        | `poctf{uwsp_4_fr13nd_70_4ll}`             |
| Status      | Solved                                     |

---

## Challenge Overview

A web challenge where the site presents a fake FBI seizure page for a carding forum. The HTML source contains a hidden link to `/agent-access`, which requires a specific User-Agent string to access. Spoofing the User-Agent header to `FBI-SiteAccess-Authorized-Agent` grants access and reveals the flag.

---

## Objective

Discover the hidden agent-access endpoint and bypass the User-Agent validation to retrieve the flag.

---

## Methodology

### Step 1: Inspect the seizure page

The main page displays a convincing FBI domain seizure notice with FBI and DOJ logos. Viewing the source reveals a hidden anchor tag:

```html
<!-- Agent access only -->
<a href="/agent-access"></a>
```

### Step 2: Navigate to /agent-access

Visiting `/agent-access` with a standard browser returns an access denied message:

```
Unauthorized access attempt has been logged. Federal authorities have been notified.
If you are authorized to view this page, please ensure you are using the department mandated browser
Err: 'Mozilla/5.0 (X11; Linux x86_64) ...'
```

The console also shows a warning revealing the expected User-Agent:

```
Not FBI-SiteAccess-Authorized-Agent. Unauthorized access detected.
```

### Step 3: Spoof the User-Agent

Using curl or Burp Suite to set the User-Agent header:

```bash
curl -H "User-Agent: FBI-SiteAccess-Authorized-Agent" http://<host>/agent-access
```

Alternatively, in Burp Suite: intercept the request and modify the `User-Agent` header to `FBI-SiteAccess-Authorized-Agent`.

### Step 4: Retrieve the flag

The server responds with the flag upon receiving the correct User-Agent.

---

## Flag

```
poctf{uwsp_4_fr13nd_70_4ll}
```

---

## Lessons Learned

| # | Lesson | Detail |
|---|--------|--------|
| 1 | HTML comments reveal secrets | Hidden links in source code are a common CTF pattern |
| 2 | Error messages leak information | The denied response explicitly names the required User-Agent |
| 3 | User-Agent is trivially spoofable | Client-side headers should never be trusted for access control |
| 4 | Console warnings contain clues | Browser developer tools reveal server-side validation logic |

---

## MITRE ATT&CK Mapping

| Tactic          | Technique                          | ID        |
|-----------------|------------------------------------|-----------|
| Defense Evasion | Masquerading                       | T1036     |
| Initial Access  | Exploit Public-Facing Application  | T1190     |
| Discovery       | System Information Discovery       | T1082     |

---

## OWASP Top 10 2021 Mapping

| Category | ID    | Relevance |
|----------|-------|-----------|
| Broken Access Control     | A01:2021 | Access control based on spoofable headers |
| Security Misconfiguration | A05:2021 | Hidden endpoint and verbose error messages |

---

## Remediation

### Technical Fixes
- Never use User-Agent headers for access control decisions
- Implement proper authentication (tokens, certificates, MFA)
- Suppress detailed error messages in production
- Remove hidden debug links from production HTML

### OWASP Top 10 2021
- **A01 Broken Access Control**: use server-side session management, not client headers
- **A05 Security Misconfiguration**: remove hidden endpoints and verbose errors from production

### D3FEND Countermeasures
| Technique                  | ID        |
|----------------------------|-----------|
| Application Hardening      | D3-AH     |
| Strong Authentication      | D3-MFA    |

### NIST CSF 2.0
| Function | Category                | Subcategory |
|----------|------------------------|-------------|
| Protect  | Identity Management and Access Control | PR.AA-01 |
| Protect  | Platform Security      | PR.PS-01    |

### NIST SP 800-53 Rev. 5
| Control     | Description                          |
|-------------|--------------------------------------|
| AC-3        | Access Enforcement                   |
| IA-2        | Identification and Authentication    |
| SI-11       | Error Handling                       |

### C2M2
| Practice Area               | MIL |
|-----------------------------|-----|
| Access Management           | MIL2 |

### CWE
| ID      | Name                                     |
|---------|------------------------------------------|
| CWE-290 | Authentication Bypass by Spoofing        |
| CWE-209 | Generation of Error Message Containing Sensitive Information |

---

## References

- Based on solve approach from [Jdwalli](https://github.com/Jdwalli/ctf-writeups)
- [Burp Suite](https://portswigger.net/burp)
- [OWASP Top 10 2021](https://owasp.org/Top10/)

---

## Closing

Thanks guys!! (❍ᴥ❍ʋ)

A friend to all, especially to those who know how to read HTML comments and swap a User-Agent header. The real FBI probably uses something more secure than a string match for authentication.

[![Instagram](https://img.shields.io/badge/-Instagram-E4405F?style=flat&logo=instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/-LinkedIn-0077B5?style=flat&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/-X-000000?style=flat&logo=x&logoColor=white)](https://x.com/mrhenrike)
