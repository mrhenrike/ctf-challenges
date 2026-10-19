# maq193: Wordpress e seus Plugins

Writeup for the **Wordpress e seus Plugins** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Web Hacking  
> **Difficulty:** Easy  
> **Points:** 193

---

## Overview

A WordPress installation with vulnerable plugins provides multiple attack vectors. Plugin enumeration reveals exploitable components that lead to remote code execution through file upload, SQL injection, or arbitrary file read.

## Reconnaissance

Scan the target:

```bash
nmap -sC -sV -p- <TARGET_IP>
```

Enumerate WordPress and its plugins:

```bash
wpscan --url http://<TARGET_IP> --enumerate ap,at,u --plugins-detection aggressive
```

Identify the WordPress version, active theme, installed plugins, and enumerated usernames.

## Exploitation

### Step 1: Identify Vulnerable Plugins

Cross-reference discovered plugins with WPScan vulnerability database and Exploit-DB. Focus on plugins with known RCE, SQLi, or file upload vulnerabilities.

### Step 2: Exploit the Vulnerable Plugin

Depending on the plugin, common exploitation paths include:

- Unauthenticated file upload
- SQL injection for credential extraction
- Local File Inclusion through plugin parameters
- Arbitrary file read to obtain wp-config.php

### Step 3: Obtain WordPress Admin Access

Use extracted credentials or cracked hashes to access `/wp-admin`. Edit theme files (e.g., 404.php) to inject a PHP reverse shell.

### Step 4: Obtain a Shell

Set up a listener and trigger the modified template:

```bash
nc -lvnp 4444
curl http://<TARGET_IP>/wp-content/themes/<theme>/404.php
```

### Step 5: Retrieve the Flag

Read the flag from the filesystem.

## Privilege Escalation

Enumerate for local privilege escalation:

```bash
sudo -l
cat wp-config.php  # database credentials for reuse
find / -perm -4000 -type f 2>/dev/null
```

## Security Framework Mapping

### MITRE ATT&CK

| Technique                         | ID        |
|-----------------------------------|-----------|
| Exploit Public-Facing Application | T1190     |
| Brute Force                       | T1110     |
| Web Shell                         | T1505.003 |

### CWE

- **CWE-89:** SQL Injection
- **CWE-434:** Unrestricted Upload of File with Dangerous Type
- **CWE-98:** Improper Control of Filename for Include/Require Statement

---

WordPress thrives on its ecosystem of plugins; each one is a door, and an outdated lock on any single door opens the entire house.

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
