# Maq158: A Imagem

Writeup for the **A imagem** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Medium
> **Difficulty:** Medium

---

## Overview

An image-themed challenge where FTP enumeration reveals a `data/` directory containing web-accessible content. Uploading a PHP webshell through FTP grants initial access as `www-data`, then SSH pivoting and sudo exploitation lead to root.

## Reconnaissance

1. Scan the target to identify FTP, HTTP, and SSH services.
2. Connect to FTP and enumerate directory listings.
3. Discover a `data/` directory on the FTP server.
4. Correlate the FTP `data/` directory with the web server's document root or a web-accessible path.

## Exploitation

1. Upload a PHP reverse shell to the `data/` directory via FTP.
2. Access the uploaded PHP file through the web browser to trigger execution.
3. Catch the reverse shell as `www-data` on the attacker's listener.
4. Enumerate the system from the `www-data` context.
5. Discover SSH credentials for a local user in configuration files or the web application.

## Privilege Escalation

1. SSH into the machine as the discovered local user for a stable, interactive shell.
2. Run `sudo -l` to check sudo permissions for the current user.
3. Identify a command or binary that can be executed with sudo privileges.
4. Exploit the sudo misconfiguration to escalate to root.
5. Retrieve the flag from the root-restricted directory.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Server Software Component: Web Shell | T1505.003 |
| Valid Accounts: Local Accounts | T1078.003 |
| Abuse Elevation Control Mechanism: Sudo | T1548.003 |
| Data from Network Shared Drive | T1039 |

### CWE

- **CWE-434:** Unrestricted Upload of File with Dangerous Type (PHP shell via FTP)
- **CWE-552:** Files or Directories Accessible to External Parties (FTP to web crossover)
- **CWE-269:** Improper Privilege Management (sudo misconfiguration)

---

> "A picture is worth a thousand words, but a PHP file in the wrong directory is worth a shell. When FTP and the web server share the same canvas, every upload paints an exploit."

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
