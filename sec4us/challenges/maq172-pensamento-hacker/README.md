# Maq172: Pensamento Hacker (BlueKeep)

> **Platform:** SEC4US CTF Lab | **Category:** Hacking: Medium | **Points:** Dynamic

## Overview

Windows machine vulnerable to the BlueKeep RDP vulnerability (CVE-2019-0708). Requires precise target configuration in Metasploit.

---

## Approach

**Technique:** BlueKeep CVE-2019-0708 RDP RCE

### Reconnaissance

```bash
nmap -sV -sC -p- <TARGET_IP> -oN nmap_full.txt
```

RDP service detected on port 3389. Version check confirms vulnerability to BlueKeep.

### Exploitation

1. **Vulnerability verification:** Confirm BlueKeep vulnerability with the Metasploit scanner module
2. **Target configuration:** Set the appropriate Metasploit target (architecture-specific) and GROOMBASE value for the lab environment
3. **Exploit execution:** Run the `exploit/windows/rdp/cve_2019_0708_bluekeep_rce` module
4. **SYSTEM shell:** Successful exploitation provides SYSTEM-level access immediately
5. **Flag retrieval:** Read the flag from the filesystem

> **Note:** BlueKeep exploitation can be unreliable. Multiple attempts with different GROOMBASE values may be required.

### Tools Used

nmap, Metasploit (cve_2019_0708_bluekeep_rce)

---

## Security Frameworks

### MITRE ATT&CK

| Technique | Description |
|-----------|-------------|
| T1210 | Exploitation of Remote Services |

### CWE

| ID | Description |
|----|-------------|
| CWE-416 | Use After Free |

---

## Author

**Andre Henrike** (@mrhenrike)

BlueKeep: a reminder that RDP was never meant to be internet-facing. Thanks guys!! (❍ᴥ❍ʋ)

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

*For educational purposes only. Do not use any technique shown here against systems you do not own or have explicit permission to test.*
