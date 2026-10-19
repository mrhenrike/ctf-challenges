# Maq150: Estatisticas

> **Platform:** SEC4US CTF Lab | **Category:** Web Hacking: Hard | **Points:** Dynamic

## Overview

A statistics web application requiring multiple chained vulnerabilities to reach the flag. Multi-step exploitation through the web interface.

---

## Approach

**Technique:** Web Application Chain Exploitation

### Reconnaissance

```bash
nmap -sV -sC -p- <TARGET_IP> -oN nmap_full.txt
gobuster dir -u http://<TARGET_IP> -w /usr/share/wordlists/dirb/common.txt
```

### Exploitation

1. **Web enumeration:** Identify the statistics application and its exposed functionality
2. **Vulnerability chaining:** Discover and chain multiple vulnerabilities (authentication bypass, file inclusion, or injection)
3. **Initial access:** Obtain command execution through the web application
4. **Privilege escalation:** Enumerate the system for escalation vectors
5. **Flag retrieval:** Access the flag file with elevated privileges

### Tools Used

nmap, gobuster, Burp Suite, curl, netcat

---

## Security Frameworks

### MITRE ATT&CK

| Technique | Description |
|-----------|-------------|
| T1190 | Exploit Public-Facing Application |
| T1068 | Exploitation for Privilege Escalation |

### CWE

| ID | Description |
|----|-------------|
| CWE-200 | Exposure of Sensitive Information |

---

## Author

**Andre Henrike** (@mrhenrike)

Statistics never lie, but sometimes they hide the truth in plain sight. Thanks guys!! (❍ᴥ❍ʋ)

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

*For educational purposes only. Do not use any technique shown here against systems you do not own or have explicit permission to test.*
