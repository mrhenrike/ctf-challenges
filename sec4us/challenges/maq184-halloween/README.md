# Maq184: Halloween SEC4US Trick or Treat

> **Platform:** SEC4US CTF Lab | **Category:** Web Hacking: Medium | **Points:** Dynamic

## Overview

A Halloween-themed web challenge from SEC4US with hidden vulnerabilities in the seasonal application.

---

## Approach

**Technique:** Web Application Exploitation

### Reconnaissance

```bash
nmap -sV -sC -p- <TARGET_IP> -oN nmap_full.txt
gobuster dir -u http://<TARGET_IP> -w /usr/share/wordlists/dirb/common.txt
```

### Exploitation

1. **Theme analysis:** The Halloween-themed web application contains hidden endpoints and parameters
2. **Vulnerability discovery:** Identify the exploitable vulnerability through careful enumeration
3. **Exploitation:** Leverage the vulnerability for code execution or information disclosure
4. **Flag retrieval:** Navigate to the flag location

### Tools Used

Burp Suite, gobuster, curl, nmap

---

## Security Frameworks

### MITRE ATT&CK

| Technique | Description |
|-----------|-------------|
| T1190 | Exploit Public-Facing Application |

### CWE

| ID | Description |
|----|-------------|
| CWE-200 | Exposure of Sensitive Information |

---

## Author

**Andre Henrike** (@mrhenrike)

The scariest thing on Halloween is not the monsters; it is the unpatched web applications. Thanks guys!! (❍ᴥ❍ʋ)

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

*For educational purposes only. Do not use any technique shown here against systems you do not own or have explicit permission to test.*
