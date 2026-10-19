# Maq122: C0d1nG

Writeup for the **C0d1nG** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Medium
> **Difficulty:** Medium

---

## Overview

A code review challenge that requires analyzing application source code to identify security flaws. The vulnerabilities found in the code are exploited to gain access and escalate privileges on the target system.

## Reconnaissance

1. Perform a port scan to identify running services.
2. Access the web application and explore its functionality.
3. Look for exposed source code files, backup files, or debug endpoints.
4. Download or read any accessible source code for review.

## Exploitation

1. Perform static analysis on the retrieved source code.
2. Identify vulnerabilities such as injection flaws, hardcoded secrets, or logic errors.
3. Craft payloads targeting the discovered code-level weaknesses.
4. Exploit the vulnerability to achieve remote code execution or authentication bypass.
5. Obtain a shell on the target with the web application's user context.

## Privilege Escalation

1. Review local application configuration files for additional credentials or tokens.
2. Enumerate system-level misconfigurations using the initial shell.
3. Identify the escalation path through the code's own privileged operations or system config.
4. Achieve root access and retrieve the flag.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Exploit Public-Facing Application | T1190 |
| Unsecured Credentials: Credentials in Files | T1552.001 |
| Command and Scripting Interpreter | T1059 |

### CWE

- **CWE-94:** Improper Control of Generation of Code (code injection)
- **CWE-798:** Use of Hard-coded Credentials (secrets embedded in source)
- **CWE-209:** Generation of Error Message Containing Sensitive Information

---

> "Reading code is the hacker's literacy test. Every variable tells a story, every unchecked input writes an exploit, and every hardcoded secret whispers: come in, the door is open."

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
