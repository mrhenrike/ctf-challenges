# MAQ151: Desenjaule se for Capaz

Writeup for the **Desenjaule se for Capaz** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Hard
> **Difficulty:** Hard
> **Points:** 151

---

## Overview

This challenge presents a Linux host running WebCalendar with a known remote code execution vulnerability. After gaining initial access, privilege escalation is achieved through the mempodipper kernel exploit (CVE-2012-0056), which abuses `/proc/pid/mem` to escalate to root.

## Reconnaissance

```bash
nmap -sC -sV -p- [TARGET_IP]
```

The scan reveals an HTTP service hosting WebCalendar. Version fingerprinting confirms a release affected by authenticated RCE.

```bash
nikto -h http://[TARGET_IP]
searchsploit webcalendar
```

## Exploitation

1. Browse the WebCalendar login page and test default or weak credentials: `[FOUND_CREDS]`.
2. Once authenticated, locate the settings import functionality vulnerable to PHP code injection.
3. Inject a reverse shell payload through the vulnerable parameter.
4. Catch the incoming connection on the attacker machine.

```bash
nc -lvnp 4444
```

The shell lands as the web service user (low-privilege account).

## Privilege Escalation

Enumerate the kernel version to confirm it is vulnerable to CVE-2012-0056 (mempodipper).

```bash
uname -r
cat /etc/issue
```

Compile and execute the mempodipper exploit, which exploits improper access control in `/proc/pid/mem` to write arbitrary data and gain root privileges.

```bash
gcc mempodipper.c -o mempodipper
./mempodipper
whoami  # root
```

Retrieve the flag from the root home directory.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Exploit Public-Facing Application | T1190 |
| Exploitation for Privilege Escalation | T1068 |
| Command and Scripting Interpreter: Unix Shell | T1059.004 |
| OS Credential Dumping | T1003 |

### CWE

- **CWE-94:** Improper Control of Generation of Code (Code Injection)
- **CWE-269:** Improper Privilege Management
- **CWE-264:** Permissions, Privileges, and Access Controls

### D3FEND

- **D3-PSA:** Process Spawn Analysis
- **D3-SFA:** System File Analysis

---

Some cages are only as strong as the kernel holding them together; when the bars are made of outdated memory protections, escaping is just a matter of knowing where to push.

(❍ᴥ❍ʋ)

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
