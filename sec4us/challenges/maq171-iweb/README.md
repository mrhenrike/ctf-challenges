# Maq171: IWEB

Writeup for the **IWEB** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Medium
> **Difficulty:** Medium

---

## Overview

A Windows target running iWeb (iws.exe) web server, vulnerable to directory traversal. After extracting sensitive files, exploitation of MS15-051 provides SYSTEM-level access, and `takeown` is used to claim ownership of the restricted flag file.

## Reconnaissance

1. Scan the target to identify the iWeb (iws.exe) HTTP server and its port.
2. Banner-grab to confirm the server software and version.
3. Research known vulnerabilities in iWeb/iws.exe, specifically directory traversal flaws.
4. Enumerate additional Windows services (SMB, RDP) for complementary attack vectors.

## Exploitation

1. Exploit the iWeb directory traversal vulnerability by crafting path traversal sequences in HTTP requests.
2. Read sensitive Windows files: `C:\Windows\System32\config\SAM`, `boot.ini`, or user files.
3. Extract credentials or configuration data from traversed files.
4. Use discovered information to gain authenticated access (SMB, RDP, or other service).
5. Establish an interactive shell on the Windows target.

## Privilege Escalation

1. Enumerate the Windows system for missing patches using `systeminfo`.
2. Identify vulnerability to MS15-051 (Windows Client/Server Runtime Subsystem privilege escalation).
3. Transfer and execute the MS15-051 exploit to elevate to SYSTEM privileges.
4. The flag file may have restricted ownership; use `takeown /f <flag_path>` to claim it.
5. After taking ownership, grant read permissions with `icacls` and read the flag.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Exploit Public-Facing Application | T1190 |
| Exploitation for Privilege Escalation | T1068 |
| File and Directory Permissions Modification: Windows File and Directory Permissions | T1222.001 |

### CWE

- **CWE-22:** Improper Limitation of a Pathname to a Restricted Directory (iWeb directory traversal)
- **CWE-269:** Improper Privilege Management (MS15-051 kernel vulnerability)
- **CWE-732:** Incorrect Permission Assignment for Critical Resource

---

> "iWeb served more than web pages; it served the entire filesystem. When directory traversal meets an unpatched Windows kernel, SYSTEM is just an exploit away, and takeown claims what remains."

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
