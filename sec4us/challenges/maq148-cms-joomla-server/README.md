# maq148: CMS Joomla Server

Writeup for the **CMS Joomla Server** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Web Hacking  
> **Difficulty:** Easy  
> **Points:** 148

---

## Overview

A Joomla CMS instance runs an outdated version with known vulnerabilities. Exploitation involves enumerating the CMS version, discovering vulnerable components or extensions, and leveraging them for remote code execution.

## Reconnaissance

Scan the target and enumerate the web application:

```bash
nmap -sC -sV -p- <TARGET_IP>
```

Identify Joomla and its version:

```bash
joomscan -u http://<TARGET_IP>
curl http://<TARGET_IP>/administrator/manifests/files/joomla.xml
```

Enumerate installed extensions and plugins for known CVEs.

## Exploitation

### Step 1: Version Identification

Confirm the Joomla version from the manifest XML or README.txt. Cross-reference with public vulnerability databases.

### Step 2: Exploit Known Vulnerability

Depending on the version, common attack vectors include:

- SQL injection in core components (CVE-2017-8917)
- Object injection via session handling
- Unauthenticated RCE in specific extensions

### Step 3: Gain Administrative Access

Use extracted credentials or SQLi to authenticate to `/administrator`. Edit a template PHP file to inject a webshell.

### Step 4: Obtain a Shell

Access the webshell or use the template editor to execute a reverse shell payload:

```bash
nc -lvnp 4444
```

### Step 5: Retrieve the Flag

Read the flag from the filesystem with the obtained shell access.

## Privilege Escalation

Enumerate the system for escalation paths:

```bash
sudo -l
cat /etc/crontab
find / -writable -type f 2>/dev/null
```

## Security Framework Mapping

### MITRE ATT&CK

| Technique                         | ID        |
|-----------------------------------|-----------|
| Exploit Public-Facing Application | T1190     |
| Valid Accounts                    | T1078     |
| Web Shell                         | T1505.003 |

### CWE

- **CWE-89:** SQL Injection
- **CWE-502:** Deserialization of Untrusted Data

---

A CMS that manages content for thousands can also serve a shell for one; the admin panel is only as secure as the version behind it.

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
