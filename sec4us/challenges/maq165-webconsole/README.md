# maq165: Webconsole

Writeup for the **Webconsole** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Web Hacking  
> **Difficulty:** Easy  
> **Points:** 165

---

## Overview

A web application exposes an interactive console or debug interface without proper authentication, granting direct remote code execution on the server.

## Reconnaissance

Scan the target for open ports and services:

```bash
nmap -sC -sV -p- <TARGET_IP>
```

Enumerate web directories to discover exposed consoles:

```bash
gobuster dir -u http://<TARGET_IP> -w /usr/share/wordlists/dirb/common.txt
```

Look for endpoints such as `/console`, `/debug`, `/shell`, or framework-specific debug pages (Werkzeug, Rails, etc.).

## Exploitation

### Step 1: Access the Exposed Console

Navigate to the discovered console endpoint. Determine whether it requires a PIN, password, or is completely open.

### Step 2: Execute Commands

If the console is unprotected, execute system commands directly:

```python
import os; os.popen('id').read()
```

### Step 3: Obtain a Reverse Shell

Set up a listener:

```bash
nc -lvnp 4444
```

Use the console to spawn a reverse shell through Python, Bash, or other available interpreters.

### Step 4: Retrieve the Flag

Locate and read the flag file from the server filesystem.

## Privilege Escalation

Enumerate local escalation paths:

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
| Command and Scripting Interpreter | T1059.006 |
| Remote Services                   | T1021     |

### CWE

- **CWE-489:** Active Debug Code
- **CWE-306:** Missing Authentication for Critical Function

---

Debug consoles are windows left open during construction; forgetting to close them before production turns convenience into compromise.

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
