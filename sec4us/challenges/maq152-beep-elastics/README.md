# Maq152: Beep Beep Elastics

Writeup for the **Beep Beep Elastics** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Medium
> **Difficulty:** Medium

---

## Overview

An Elastix PBX system exposing multiple attack surfaces. The exploitation chain leverages vtiger CRM's Local File Inclusion vulnerability to extract credentials, a SOAP-based file upload for code execution, and sudo chmod misconfiguration for root escalation.

## Reconnaissance

1. Scan the target to discover multiple web services, VoIP (SIP), and SMTP.
2. Access the Elastix web interface and identify the platform version.
3. Enumerate web directories to discover vtiger CRM and FreePBX admin panels.
4. Research known Elastix and vtiger CRM vulnerabilities.

## Exploitation

1. Exploit the vtiger CRM Local File Inclusion (LFI) vulnerability to read sensitive server files.
2. Extract Elastix configuration files containing database or admin credentials via LFI.
3. Use the SOAP interface to upload a malicious file (PHP shell) to the web-accessible directory.
4. Trigger the uploaded shell to gain a reverse connection as the web server user.
5. Alternatively, use extracted credentials to access the FreePBX or Elastix admin panel directly.

## Privilege Escalation

1. Enumerate sudo permissions for the current user: `sudo -l`.
2. Discover that `chmod` can be executed with sudo without a password.
3. Use `sudo chmod` to make sensitive files readable or to set SUID on `/bin/bash`.
4. Example: `sudo chmod u+s /bin/bash` then `/bin/bash -p` for a root shell.
5. Retrieve the flag from the root directory.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Exploit Public-Facing Application | T1190 |
| Unsecured Credentials: Credentials in Files | T1552.001 |
| Abuse Elevation Control Mechanism: Sudo | T1548.003 |
| Server Software Component: Web Shell | T1505.003 |

### CWE

- **CWE-98:** Improper Control of Filename for Include (LFI in vtiger CRM)
- **CWE-434:** Unrestricted Upload of File with Dangerous Type (SOAP file upload)
- **CWE-269:** Improper Privilege Management (sudo chmod without restriction)

---

> "Beep beep, the road runner escapes again. But in Elastix, every protocol is a lane: LFI reads the map, SOAP uploads the trap, and sudo chmod opens every gate."

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
