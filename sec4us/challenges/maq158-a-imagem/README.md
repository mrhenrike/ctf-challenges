# Maq158: A Imagem

> **Platform:** SEC4US CTF Lab | **Category:** Web Hacking: Medium | **Points:** Dynamic

## Overview

Machine with FTP access to a web data directory, enabling PHP upload for RCE followed by sudo privilege escalation.

---

## Approach

**Technique:** FTP Data Directory + PHP Upload + SSH Sudo

### Reconnaissance

```bash
nmap -sV -sC -p- <TARGET_IP> -oN nmap_full.txt
```

### Exploitation

1. **FTP enumeration:** FTP access reveals a `data/` directory that maps to the web document root
2. **PHP webshell upload:** Upload a PHP reverse shell through FTP into the web-accessible directory
3. **Trigger execution:** Access the uploaded PHP file through the web browser to obtain a shell as www-data
4. **SSH credential discovery:** Enumerate the filesystem to find SSH credentials for the jpeguser account
5. **Sudo privilege escalation:** The jpeguser has sudo permissions allowing escalation to root
6. **Flag retrieval:** Read the flag with root privileges

### Tools Used

nmap, ftp, php-reverse-shell, ssh, sudo

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
| CWE-434 | Unrestricted Upload of File with Dangerous Type |

---

## Author

**Andre Henrike** (@mrhenrike)

When your FTP root meets your web root, every upload becomes a potential shell. Thanks guys!! (❍ᴥ❍ʋ)

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

*For educational purposes only. Do not use any technique shown here against systems you do not own or have explicit permission to test.*
