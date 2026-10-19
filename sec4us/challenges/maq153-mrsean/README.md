# Maq153: Mr.Sean

> **Platform:** SEC4US CTF Lab | **Category:** Hacking: Medium | **Points:** Dynamic

## Overview

WordPress with a vulnerable forum plugin susceptible to SQL injection, leading to admin access and code execution.

---

## Approach

**Technique:** WordPress Forum SQLi + Plugin RCE + SSH Sudo

### Reconnaissance

```bash
nmap -sV -sC -p- <TARGET_IP> -oN nmap_full.txt
wpscan --url http://<TARGET_IP> --enumerate p,u
```

### Exploitation

1. **Plugin enumeration:** WPScan reveals a forum plugin with known SQL injection vulnerability
2. **SQL Injection:** Extract admin credentials from the WordPress database through the forum parameter
3. **Admin access:** Log in to `/wp-admin/` with the extracted credentials
4. **RCE via theme/plugin editor:** Inject PHP reverse shell code through the theme editor or upload a malicious plugin
5. **SSH credential discovery:** Find SSH credentials in the WordPress configuration or filesystem
6. **Privilege escalation:** The SSH user has sudo privileges allowing root shell access

### Tools Used

wpscan, sqlmap, Burp Suite, ssh, netcat

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
| CWE-89 | SQL Injection |

---

## Author

**Andre Henrike** (@mrhenrike)

WordPress plugins: the gift that keeps on giving to penetration testers worldwide. Thanks guys!! (❍ᴥ❍ʋ)

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

*For educational purposes only. Do not use any technique shown here against systems you do not own or have explicit permission to test.*
