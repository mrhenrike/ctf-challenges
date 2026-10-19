# Maq135: LigGoat

Writeup for the **LigGoat** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Medium
> **Difficulty:** Medium

---

## Overview

A challenge built around OWASP WebGoat, the deliberately insecure web application. Multiple vulnerability categories from the OWASP Top 10 are exercised to progress through the lessons and ultimately compromise the underlying system.

## Reconnaissance

1. Scan the target to identify the WebGoat application and its running port.
2. Access the WebGoat interface and enumerate available lessons and categories.
3. Identify the WebGoat version to research known escape or OS-level vulnerabilities.
4. Map out which lessons allow interaction with the underlying operating system.

## Exploitation

1. Work through WebGoat lessons that expose real vulnerabilities: injection, authentication flaws, access control issues.
2. Identify lessons or features that allow command execution on the host system.
3. Exploit an injection vulnerability (SQL injection, command injection, or XXE) to break out of the WebGoat sandbox.
4. Leverage the vulnerability to execute OS commands and establish a reverse shell.
5. Gain initial foothold as the application service user.

## Privilege Escalation

1. Enumerate local users, SUID binaries, sudo configurations, and scheduled tasks.
2. Check application configuration for database credentials or service account tokens.
3. Exploit the discovered escalation vector to gain root-level access.
4. Retrieve the flag to complete the challenge.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Exploit Public-Facing Application | T1190 |
| Command and Scripting Interpreter | T1059 |
| Exploitation for Privilege Escalation | T1068 |

### CWE

- **CWE-89:** Improper Neutralization of SQL Commands (SQL injection)
- **CWE-78:** Improper Neutralization of OS Commands (command injection)
- **CWE-285:** Improper Authorization (broken access control)

---

> "WebGoat teaches you to attack so you learn to defend. But when the goat itself runs on a real server with real permissions, the lessons become a lot more consequential."

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
