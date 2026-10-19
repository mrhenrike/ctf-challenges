# maq186: Web Dev

Writeup for the **Web Dev** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Web Hacking  
> **Difficulty:** Easy  
> **Points:** 186

---

## Overview

A web application exposes source code, backup files, or development artifacts that reveal sensitive information such as credentials, internal paths, or application logic, leading to unauthorized access.

## Reconnaissance

Scan the target:

```bash
nmap -sC -sV -p- <TARGET_IP>
```

Perform directory and file enumeration looking for development leftovers:

```bash
gobuster dir -u http://<TARGET_IP> -w /usr/share/wordlists/dirb/common.txt \
  -x php,bak,old,txt,zip,tar.gz,git,swp
```

Check for exposed version control:

```bash
curl http://<TARGET_IP>/.git/HEAD
curl http://<TARGET_IP>/.svn/entries
```

## Exploitation

### Step 1: Discover Source Code Disclosure

Identify accessible files such as `.git/`, backup archives, `.swp` files, or commented credentials in HTML source.

### Step 2: Extract Sensitive Information

Download and analyze exposed files:

```bash
git-dumper http://<TARGET_IP>/.git/ ./repo
```

Review source code for hardcoded credentials, API keys, database connection strings, or hidden endpoints.

### Step 3: Authenticate or Access Hidden Functionality

Use discovered credentials to log in or access restricted areas of the application.

### Step 4: Achieve Remote Code Execution

Leverage authenticated access to upload a webshell, exploit an admin function, or chain additional vulnerabilities for shell access.

### Step 5: Retrieve the Flag

Read the flag from the server filesystem.

## Privilege Escalation

After gaining initial access, enumerate for escalation:

```bash
sudo -l
cat /etc/crontab
find / -perm -4000 -type f 2>/dev/null
```

## Security Framework Mapping

### MITRE ATT&CK

| Technique                         | ID        |
|-----------------------------------|-----------|
| Exploit Public-Facing Application | T1190     |
| Unsecured Credentials: Files      | T1552.001 |
| Valid Accounts                    | T1078     |

### CWE

- **CWE-538:** Insertion of Sensitive Information into Externally-Accessible File or Directory
- **CWE-200:** Exposure of Sensitive Information to an Unauthorized Actor
- **CWE-540:** Inclusion of Sensitive Information in Source Code

---

Developers leave breadcrumbs in every commit, every backup, every swap file; an attacker only needs to follow the trail to find what was never meant to be public.

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
