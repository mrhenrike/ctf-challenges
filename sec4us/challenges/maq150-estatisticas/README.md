# Maq150: Estatisticas

Writeup for the **Estatisticas** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Medium
> **Difficulty:** Medium

---

## Overview

A web application serving statistics functionality that contains exploitable vulnerabilities in its input handling. Careful enumeration of the web interface reveals injection points that lead to system compromise.

## Reconnaissance

1. Scan the target to identify web services and their technology stack.
2. Browse the statistics application, mapping all endpoints and input fields.
3. Inspect page sources, JavaScript files, and hidden form parameters.
4. Enumerate directories with wordlists to find admin panels or backup files.

## Exploitation

1. Identify input fields in the statistics application that interact with the backend.
2. Test for common web vulnerabilities: SQL injection, command injection, file inclusion.
3. Confirm the exploitable vulnerability and determine its type and scope.
4. Craft a payload to achieve remote code execution through the vulnerable parameter.
5. Establish a reverse shell as the web application user.

## Privilege Escalation

1. Enumerate the system for privilege escalation vectors from the initial shell.
2. Check configuration files, database connections, and cron jobs for stored credentials or misconfigurations.
3. Exploit the identified vector to elevate privileges to root.
4. Access and retrieve the final flag.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Exploit Public-Facing Application | T1190 |
| Command and Scripting Interpreter | T1059 |
| Exploitation for Privilege Escalation | T1068 |

### CWE

- **CWE-89:** Improper Neutralization of SQL Commands (if SQLi)
- **CWE-78:** Improper Neutralization of OS Commands (if command injection)
- **CWE-20:** Improper Input Validation

---

> "Statistics never lie, but the application serving them might accept far more than numbers. Every unvalidated input is a data point in the attacker's favor."

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
