# maq108: Servidor de Comandos

Writeup for the **Servidor de Comandos** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Web Hacking  
> **Difficulty:** Easy  
> **Points:** 108

---

## Overview

A web application exposes a form that executes system commands on the server. The input lacks proper sanitization, allowing OS command injection to gain remote code execution.

## Reconnaissance

Start with a port scan to identify services:

```bash
nmap -sC -sV -p- <TARGET_IP>
```

Access the web application and locate the command execution form. Observe how user input is passed to the server and reflected in the output.

## Exploitation

### Step 1: Identify Injection Point

The web form sends user input directly to a backend function that calls a system shell. Test with basic command separators:

```
; id
| whoami
&& cat /etc/passwd
```

### Step 2: Confirm Code Execution

Use a semicolon or pipe to chain commands and confirm arbitrary execution. Observe the output returned by the application.

### Step 3: Obtain a Reverse Shell

Set up a listener:

```bash
nc -lvnp 4444
```

Inject a reverse shell payload through the form input using bash, netcat, or Python one-liners.

### Step 4: Retrieve the Flag

Navigate the filesystem to locate and read the flag file.

## Privilege Escalation

Check for SUID binaries, sudo permissions, or misconfigured services:

```bash
sudo -l
find / -perm -4000 -type f 2>/dev/null
```

## Security Framework Mapping

### MITRE ATT&CK

| Technique                        | ID        |
|----------------------------------|-----------|
| Exploitation for Client Execution | T1203     |
| Command and Scripting Interpreter | T1059     |
| OS Credential Dumping            | T1003     |

### CWE

- **CWE-78:** Improper Neutralization of Special Elements used in an OS Command (OS Command Injection)
- **CWE-20:** Improper Input Validation

---

Every locked door has a key; sometimes the application hands it to you through the terminal prompt itself.

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
