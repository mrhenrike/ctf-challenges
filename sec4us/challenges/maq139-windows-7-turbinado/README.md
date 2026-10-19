# Maq139: Windows 7 Turbinado

Writeup for the **Windows 7 turbinado** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Medium
> **Difficulty:** Medium

---

## Overview

A Windows 7 target running Konica Minolta FTP Utility, which is vulnerable to CVE-2015-7603: a directory traversal flaw that allows reading arbitrary files from the system. This information leak enables further exploitation and full system compromise.

## Reconnaissance

1. Run a port scan to identify services, noting FTP on the target.
2. Banner-grab the FTP service to identify Konica Minolta FTP Utility.
3. Research CVE-2015-7603 for the Konica FTP directory traversal vulnerability.
4. Enumerate any additional services (SMB, RDP, HTTP) on the Windows 7 host.

## Exploitation

1. Connect to the Konica FTP service.
2. Exploit CVE-2015-7603 by crafting directory traversal sequences in FTP commands (e.g., `CWD ../../../`).
3. Navigate outside the FTP root to access arbitrary filesystem locations.
4. Retrieve sensitive files: configuration files, SAM/SYSTEM hives, or application credentials.
5. Use extracted information to gain authenticated access via SMB or RDP.
6. Establish an interactive shell on the target system.

## Privilege Escalation

1. Enumerate the Windows 7 system for missing patches and local vulnerabilities.
2. Check for stored credentials, token impersonation opportunities, or unquoted service paths.
3. Exploit the identified weakness to escalate to Administrator or SYSTEM.
4. Retrieve the flag from the privileged user's directory.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Exploit Public-Facing Application | T1190 |
| Unsecured Credentials: Credentials in Files | T1552.001 |
| Valid Accounts: Local Accounts | T1078.003 |

### CWE

- **CWE-22:** Improper Limitation of a Pathname to a Restricted Directory (directory traversal)
- **CWE-200:** Exposure of Sensitive Information to an Unauthorized Actor

---

> "A turbocharged Windows means nothing when the FTP service lets you walk through every directory on disk. Konica printed a path straight past security, and CVE-2015-7603 was the ink."

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
