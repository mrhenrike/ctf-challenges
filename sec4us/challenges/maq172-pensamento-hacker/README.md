# Maq172: Pensamento Hacker

Writeup for the **Pensamento Hacker** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Medium
> **Difficulty:** Medium

---

## Overview

A lateral-thinking web exploitation challenge that rewards creative problem-solving. The target requires unconventional approaches to discover hidden functionality, bypass restrictions, and ultimately achieve system access through non-obvious attack vectors.

## Reconnaissance

1. Scan the target to identify all exposed services and their versions.
2. Perform thorough web enumeration: directories, files, subdomains, virtual hosts.
3. Inspect all client-side code, comments, and hidden parameters in the web application.
4. Look for non-standard ports, obscure protocols, or services that are not immediately obvious.
5. Think laterally: check source code comments, HTTP headers, and unusual response behaviors.

## Exploitation

1. Identify the hidden or non-obvious entry point that requires lateral thinking.
2. Apply creative techniques: parameter manipulation, encoding tricks, or logic abuse.
3. Chain discoveries from multiple sources to form a complete exploitation path.
4. Achieve code execution through the unconventional attack vector.
5. Establish a foothold on the target system.

## Privilege Escalation

1. Enumerate the system thoroughly for escalation opportunities.
2. Apply the same lateral-thinking approach to privilege escalation.
3. Look for unusual system configurations, custom scripts, or overlooked permissions.
4. Escalate privileges and retrieve the flag.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Exploit Public-Facing Application | T1190 |
| Exploitation for Privilege Escalation | T1068 |
| Obfuscated Files or Information | T1027 |

### CWE

- **CWE-693:** Protection Mechanism Failure
- **CWE-20:** Improper Input Validation
- **CWE-284:** Improper Access Control

---

> "Hacker thinking is not about the tools; it is about seeing doors where others see walls. The most dangerous vulnerability is the one nobody thought to test, hidden in plain sight behind an assumption."

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
