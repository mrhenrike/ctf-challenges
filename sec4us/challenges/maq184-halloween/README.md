# Maq184: Halloween SEC4US

Writeup for the **Halloween SEC4US** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Medium
> **Difficulty:** Medium

---

## Overview

A Halloween-themed "Trick or Treat" web challenge where the seasonal web application conceals exploitable vulnerabilities behind its festive facade. Creative enumeration and exploitation of the themed application lead to system compromise.

## Reconnaissance

1. Scan the target to identify web services and any additional ports.
2. Access the Halloween-themed web application and explore all visible pages.
3. Enumerate hidden directories and files using wordlists, including Halloween-themed terms.
4. Inspect page sources, JavaScript, cookies, and HTTP headers for hidden clues or parameters.
5. Check for robots.txt, sitemap.xml, or other metadata files that may reveal hidden paths.

## Exploitation

1. Identify the trick hidden in the treat: discover the exploitable vulnerability in the themed application.
2. Test discovered parameters and endpoints for injection flaws, authentication bypass, or file inclusion.
3. Exploit the vulnerability to gain code execution or sensitive information disclosure.
4. Establish a reverse shell or extract credentials for direct system access.
5. Gain initial foothold on the target machine.

## Privilege Escalation

1. Enumerate the system from the initial access context.
2. Check for SUID binaries, sudo permissions, cron jobs, and writable scripts.
3. Look for credentials in application configuration files or database connections.
4. Exploit the identified escalation vector to obtain root access.
5. Retrieve the flag to complete the Trick or Treat challenge.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Exploit Public-Facing Application | T1190 |
| Command and Scripting Interpreter | T1059 |
| Exploitation for Privilege Escalation | T1068 |

### CWE

- **CWE-200:** Exposure of Sensitive Information to an Unauthorized Actor
- **CWE-20:** Improper Input Validation
- **CWE-693:** Protection Mechanism Failure

---

> "Trick or treat? In this challenge, the treat is a shell and the trick is finding it. On Halloween night, every jack-o-lantern hides a vulnerability, and every candy wrapper conceals an exploit."

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
