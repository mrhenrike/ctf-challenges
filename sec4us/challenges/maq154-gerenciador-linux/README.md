# Maq154: Gerenciador de Servicos Linux (Webmin)

> **Platform:** SEC4US CTF Lab | **Category:** Web Hacking: Medium | **Points:** Dynamic

## Overview

Linux machine running Webmin with an old directory traversal vulnerability allowing unauthenticated file access.

---

## Approach

**Technique:** Webmin CVE-2006-3392 (File Disclosure)

### Reconnaissance

```bash
nmap -sV -sC -p- <TARGET_IP> -oN nmap_full.txt
```

Webmin detected on port 10000.

### Exploitation

1. **Vulnerability identification:** Webmin version is vulnerable to CVE-2006-3392 (arbitrary file disclosure)
2. **File read:** Use the directory traversal to read `/etc/shadow` or other sensitive files without authentication
3. **Credential extraction:** Extract password hashes from `/etc/shadow`
4. **Hash cracking:** Crack the hashes with hashcat or john
5. **Direct flag read:** Alternatively, read the flag directly from `/root/` through the traversal

### Tools Used

nmap, curl, Metasploit (webmin_file_disclosure), hashcat

---

## Security Frameworks

### MITRE ATT&CK

| Technique | Description |
|-----------|-------------|
| T1083 | File and Directory Discovery |
| T1552.001 | Credentials In Files |

### CWE

| ID | Description |
|----|-------------|
| CWE-22 | Path Traversal |

---

## Author

**Andre Henrike** (@mrhenrike)

When your management interface has a 20-year-old CVE, maybe it is time for an upgrade. Thanks guys!! (❍ᴥ❍ʋ)

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

*For educational purposes only. Do not use any technique shown here against systems you do not own or have explicit permission to test.*
