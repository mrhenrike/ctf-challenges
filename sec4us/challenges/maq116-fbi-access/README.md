# Maq116: FBI Access

Writeup for the **FBI Access** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Medium
> **Difficulty:** Medium

---

## Overview

A Debian 6 target where manipulating the `X-Api-Version` HTTP header reveals a hidden API endpoint vulnerable to command injection. The outdated kernel opens a potential path to DirtyCOW (CVE-2016-5195) for privilege escalation.

## Reconnaissance

1. Run a port scan to identify web services and their versions.
2. Enumerate web directories and endpoints using standard wordlists.
3. Inspect HTTP response headers for hints about API versioning.
4. Identify that the application processes the `X-Api-Version` request header.

## Exploitation

1. Craft HTTP requests with various `X-Api-Version` header values to probe behavior.
2. Discover that certain header values trigger server-side command execution.
3. Inject OS commands through the `X-Api-Version` header to achieve remote code execution.
4. Establish a reverse shell as the web service user.
5. Enumerate the target system: confirm Debian 6 with an outdated Linux kernel.

## Privilege Escalation

1. Check kernel version and confirm it is vulnerable to CVE-2016-5195 (DirtyCOW).
2. Transfer the DirtyCOW exploit to the target or compile it locally.
3. Execute the exploit to overwrite a SUID binary or modify `/etc/passwd`.
4. Gain root-level access and retrieve the flag.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Exploit Public-Facing Application | T1190 |
| Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Exploitation for Privilege Escalation | T1068 |

### CWE

- **CWE-78:** Improper Neutralization of Special Elements in OS Commands (command injection via header)
- **CWE-269:** Improper Privilege Management (outdated kernel allowing local privesc)

---

> "Not every badge grants authority, and not every header tells the truth. When the API blindly trusts what you send, the bureau loses control of its own building."

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
