# Maq171: IWEB

> **Platform:** SEC4US CTF Lab | **Category:** Web Hacking: Medium | **Points:** Dynamic

## Overview

Windows machine running iWeb (iws.exe) web server with path traversal vulnerability, combined with a Windows kernel exploit for SYSTEM.

---

## Approach

**Technique:** iWeb (iws.exe) Path Traversal + MS15-051 SYSTEM

### Reconnaissance

```bash
nmap -sV -sC -p- <TARGET_IP> -oN nmap_full.txt
```

### Exploitation

1. **Path traversal:** The iWeb server (iws.exe) is vulnerable to directory traversal, allowing reading of files outside the webroot
2. **Information gathering:** Read sensitive Windows files through the traversal (SAM, system info, user files)
3. **Initial access:** Obtain credentials or use another vector for shell access
4. **MS15-051 escalation:** The Windows kernel is vulnerable to CVE-2015-1701 (Client/Server Runtime Subsystem)
5. **SYSTEM access:** Execute the MS15-051 exploit for SYSTEM privileges
6. **Flag access:** Use `takeown` and `icacls` to access the flag on the Admin desktop

### Tools Used

curl, MS15-051 exploit, takeown, icacls, netcat

---

## Security Frameworks

### MITRE ATT&CK

| Technique | Description |
|-----------|-------------|
| T1083 | File and Directory Discovery |
| T1068 | Exploitation for Privilege Escalation |

### CWE

| ID | Description |
|----|-------------|
| CWE-22 | Path Traversal |

---

## Author

**Andre Henrike** (@mrhenrike)

Path traversal on Windows: because backslashes and dots have always been a dangerous combination. Thanks guys!! (❍ᴥ❍ʋ)

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

*For educational purposes only. Do not use any technique shown here against systems you do not own or have explicit permission to test.*
