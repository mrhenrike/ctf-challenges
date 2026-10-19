# I Have Objections

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2024 |
| **Category** | ID |
| **Difficulty** | Unknown |
| **Points** | N/A |
| **Flag** | `poctf{uwsp_71m3_15_4n_1llu510n}` |
| **Status** | Solved |

---

## Challenge Overview

A web challenge involving a live stream site with a "Report Abuse" feature. The input field on the report page is vulnerable to Server-Side Template Injection (SSTI) in a Jinja2-based Flask application. Exploiting SSTI allows reading the application source code containing the flag.

---

## Objective

Exploit the SSTI vulnerability to read the backend source code and extract the flag.

---

## Methodology

### Step 1: Discover the /flag endpoint

The challenge hint mentions the path `/flag`. Navigating there returns a 403 Forbidden response, indicating the endpoint exists but is restricted.

### Step 2: Identify the injection point

Clicking the "Report Abuse / Service Issue" button reveals a form with an input field. Testing template syntax confirms SSTI vulnerability in the Jinja2 template engine.

### Step 3: Exploit SSTI to read source

Using a standard Jinja2 SSTI payload to execute OS commands:

```
{{request.application.__globals__.__builtins__.__import__('os').popen('cat app.py').read()}}
```

This payload traverses the Python object hierarchy to import `os` and execute `cat app.py`, dumping the application source code.

### Step 4: Extract the flag

The response includes the full `app.py` source, which contains the flag embedded in the application logic.

---

## Flag

```
poctf{uwsp_71m3_15_4n_1llu510n}
```

---

## Lessons Learned

| # | Lesson | Detail |
|---|--------|--------|
| 1 | User input in templates is dangerous | Unescaped input in Jinja2 templates enables full RCE |
| 2 | SSTI chains are powerful | Python's object model allows traversal to `os.popen` |
| 3 | 403 does not mean unreachable | Alternative attack vectors can bypass access controls |
| 4 | Report/feedback forms are attack surface | Any user input rendered server-side needs validation |

---

## MITRE ATT&CK Mapping

| Tactic          | Technique                        | ID        |
|-----------------|----------------------------------|-----------|
| Initial Access  | Exploit Public-Facing Application| T1190     |
| Execution       | Command and Scripting Interpreter| T1059     |
| Collection      | Data from Local System           | T1005     |

---

## OWASP Top 10 2021 Mapping

| Category | ID    | Relevance |
|----------|-------|-----------|
| Injection | A03:2021 | Server-Side Template Injection |
| Security Misconfiguration | A05:2021 | Application source accessible via SSTI |

---

## Remediation

### Technical Fixes
- Sanitize all user input before passing to template engines
- Use sandboxed template rendering environments
- Never render raw user input in server-side templates
- Implement proper access controls for sensitive files

### OWASP Top 10 2021
- **A03 Injection**: validate and escape all user-supplied data before template rendering
- **A05 Security Misconfiguration**: restrict file system access from the application process

### D3FEND Countermeasures
| Technique                  | ID        |
|----------------------------|-----------|
| Application Hardening      | D3-AH     |
| Process Spawn Analysis     | D3-PSA    |

### NIST CSF 2.0
| Function | Category                | Subcategory |
|----------|------------------------|-------------|
| Protect  | Platform Security      | PR.PS-01    |
| Detect   | Adverse Event Analysis | DE.AE-01    |

### NIST SP 800-53 Rev. 5
| Control     | Description                          |
|-------------|--------------------------------------|
| SI-10       | Information Input Validation         |
| AC-3        | Access Enforcement                   |
| SI-3        | Malicious Code Protection            |

### C2M2
| Practice Area               | MIL |
|-----------------------------|-----|
| Threat and Vulnerability Management | MIL2 |

### CWE
| ID       | Name                                     |
|----------|------------------------------------------|
| CWE-1336 | Improper Neutralization of Special Elements Used in a Template Engine |
| CWE-94   | Improper Control of Generation of Code   |

---

## References

- Based on solve approach from [Jdwalli](https://github.com/Jdwalli/ctf-writeups)
- [HackTricks SSTI](https://book.hacktricks.wiki/en/pentesting-web/ssti-server-side-template-injection/index.html)
- [OWASP Top 10 2021](https://owasp.org/Top10/)

---

## Closing

Thanks guys!! (❍ᴥ❍ʋ)

Time really is an illusion when you're deep in a template injection chain. One payload, one traversal, and suddenly you're reading the server's secrets. Never underestimate the power of unsanitized input.

[![Instagram](https://img.shields.io/badge/-Instagram-E4405F?style=flat&logo=instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/-LinkedIn-0077B5?style=flat&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/-X-000000?style=flat&logo=x&logoColor=white)](https://x.com/mrhenrike)
