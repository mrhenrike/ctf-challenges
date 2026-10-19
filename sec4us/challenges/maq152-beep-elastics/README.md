# Maq152: Beep Beep Elastics (Elastix)

> **Platform:** SEC4US CTF Lab | **Category:** Web Hacking: Medium | **Points:** Dynamic

## Overview

Elastix PBX system with multiple attack vectors: LFI through VTiger CRM, Webmin file disclosure, and Shellshock. The primary path exploits configuration file exposure.

---

## Approach

**Technique:** LFI + VTiger CRM + Credential Reuse

### Reconnaissance

```bash
nmap -sV -sC -p- <TARGET_IP> -oN nmap_full.txt
```

Multiple services exposed: HTTPS (443), Webmin (10000), and the Elastix PBX interface.

### Exploitation

1. **LFI via VTiger CRM:** The VTiger CRM module included with Elastix is vulnerable to Local File Inclusion
2. **Configuration disclosure:** Read `amportal.conf` through the LFI, exposing database and admin passwords stored in plaintext
3. **Credential reuse:** The admin password from the configuration file works for SSH root access
4. **Alternative path:** If SSH fails, a SOAP file upload combined with sudo chmod provides privilege escalation
5. **Flag retrieval:** Read the flag from the filesystem with root access

### Tools Used

nmap, curl, Burp Suite, searchsploit, ssh

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
| CWE-256 | Plaintext Storage of a Password |

---

## Author

**Andre Henrike** (@mrhenrike)

A PBX system is only as secure as its configuration files. Always encrypt stored credentials. Thanks guys!! (❍ᴥ❍ʋ)

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

*For educational purposes only. Do not use any technique shown here against systems you do not own or have explicit permission to test.*
