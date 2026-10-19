# Maq155: Email Break

> **Platform:** SEC4US CTF Lab | **Category:** Web Hacking: Hard | **Points:** Dynamic

## Overview

An email server with a web interface containing authentication bypass or injection vulnerabilities.

---

## Approach

**Technique:** Email Server Exploitation

### Reconnaissance

```bash
nmap -sV -sC -p- <TARGET_IP> -oN nmap_full.txt
```

### Exploitation

1. **Service enumeration:** Identify the email server software and web interface
2. **Authentication testing:** Test for default credentials, authentication bypass, or injection in login forms
3. **Exploitation:** Leverage the identified vulnerability for initial access or information disclosure
4. **Privilege escalation:** Enumerate the system for escalation paths
5. **Flag retrieval:** Access the flag with obtained privileges

### Tools Used

nmap, Burp Suite, curl, searchsploit

---

## Security Frameworks

### MITRE ATT&CK

| Technique | Description |
|-----------|-------------|
| T1190 | Exploit Public-Facing Application |

### CWE

| ID | Description |
|----|-------------|
| CWE-287 | Improper Authentication |

---

## Author

**Andre Henrike** (@mrhenrike)

Email servers: where SMTP meets opportunity and security takes a vacation. Thanks guys!! (❍ᴥ❍ʋ)

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

*For educational purposes only. Do not use any technique shown here against systems you do not own or have explicit permission to test.*
