# Maq170: StormTroopers

Writeup for the **StormTroopers** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Medium
> **Difficulty:** Medium

---

## Overview

A web application using the Twig template engine where the "token" cookie is vulnerable to Server-Side Template Injection (SSTI). After achieving RCE through SSTI, SSH access as user "bisonho" and a sudo misconfiguration with `awk` lead to full root compromise.

## Reconnaissance

1. Scan the target to identify web and SSH services.
2. Access the web application and analyze its behavior, noting cookie values.
3. Identify the "token" cookie as user-controllable and reflected in server responses.
4. Detect Twig template engine fingerprints in the response output.

## Exploitation

1. Test the "token" cookie for SSTI by injecting a basic expression: `{{7*7}}`.
2. Confirm template injection when the response renders `49`.
3. Escalate the SSTI payload to achieve remote code execution using Twig-specific syntax.
4. Example Twig RCE payload structure (without real values):
   ```
   {{_self.env.registerUndefinedFilterCallback("exec")}}{{_self.env.getFilter("id")}}
   ```
5. Use the SSTI RCE to establish a reverse shell on the attacker machine.

## Privilege Escalation

1. From the initial web shell, enumerate system users and discover "bisonho".
2. Find SSH credentials for user "bisonho" in application files or through further enumeration.
3. SSH into the system as "bisonho" for a stable shell.
4. Run `sudo -l` and discover that `awk` can be run with sudo without a password.
5. Exploit awk's system execution capability: `sudo awk 'BEGIN {system("/bin/bash")}'`.
6. Obtain a root shell and retrieve the flag.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Exploit Public-Facing Application | T1190 |
| Command and Scripting Interpreter | T1059 |
| Abuse Elevation Control Mechanism: Sudo | T1548.003 |
| Valid Accounts: Local Accounts | T1078.003 |

### CWE

- **CWE-1336:** Improper Neutralization of Special Elements Used in a Template Engine (SSTI)
- **CWE-269:** Improper Privilege Management (sudo awk shell escape)

---

> "StormTroopers never hit their target, but this SSTI lands every time. When Twig renders your cookie as code and awk hands you a root shell, the Empire's defenses crumble from the inside."

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
