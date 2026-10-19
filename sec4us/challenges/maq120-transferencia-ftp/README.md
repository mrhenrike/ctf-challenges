# Maq120: Transferencia de Arquivo FTP

Writeup for the **Transferencia de Arquivo FTP** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Medium
> **Difficulty:** Medium

---

## Overview

An FTP-focused challenge where file transfer capabilities expose sensitive information that enables initial access, followed by a privilege escalation path through system misconfigurations.

## Reconnaissance

1. Run a full port scan to enumerate open services on the target.
2. Identify FTP service and its version for known vulnerability research.
3. Test for anonymous FTP access and list available directories.
4. Enumerate any additional services (SSH, HTTP) that may complement the attack path.

## Exploitation

1. Connect to the FTP service and explore accessible directories.
2. Download files of interest containing configuration data or credentials.
3. Analyze retrieved files for usernames, passwords, or system information.
4. Use discovered credentials to authenticate via SSH or another available service.
5. Gain a low-privilege shell on the target system.

## Privilege Escalation

1. Enumerate the system for privilege escalation vectors: SUID binaries, sudo permissions, cron jobs.
2. Identify a misconfigured service or binary that runs with elevated privileges.
3. Exploit the misconfiguration to escalate from the initial user to root.
4. Access the restricted flag file to complete the challenge.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Valid Accounts | T1078 |
| Unsecured Credentials: Credentials in Files | T1552.001 |
| Exploitation for Privilege Escalation | T1068 |
| Data from Network Shared Drive | T1039 |

### CWE

- **CWE-312:** Cleartext Storage of Sensitive Information (credentials on FTP)
- **CWE-276:** Incorrect Default Permissions (misconfigured privilege escalation vector)

---

> "File transfers should move data, not hand out keys. When credentials travel unencrypted over FTP, every packet on the wire becomes an open invitation."

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
