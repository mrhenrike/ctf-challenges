# Maq115: Abra o Olho (Tr0ll)

Writeup for the **Abra o Olho (Tr0ll)** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Medium
> **Difficulty:** Medium

---

## Overview

A classic Tr0ll-style machine where FTP anonymous access leaks credentials, leading to SSH access and privilege escalation through a cron job running a writable Python script with elevated privileges.

## Reconnaissance

1. Run a full port scan to discover open services.
2. Identify FTP (port 21) with anonymous login enabled.
3. Enumerate FTP contents to find a `Pass.txt` file containing potential credentials.
4. Identify SSH (port 22) as the next pivot point.

## Exploitation

1. Connect to FTP using anonymous credentials.
2. Download the `Pass.txt` file from the FTP server.
3. Parse the password list and attempt SSH brute-force against the target.
4. Authenticate to SSH as user `overflow` using a password from the retrieved list.
5. Gain an initial shell with low-privilege user access.

## Privilege Escalation

1. Enumerate scheduled tasks and cron jobs on the system.
2. Discover `cleaner.py` running as a cron job with root privileges.
3. Confirm that the script is world-writable or owned by the current user.
4. Modify `cleaner.py` to inject a reverse shell payload or copy `/bin/bash` with SUID permissions.
5. Wait for the cron job to trigger execution.
6. Execute the SUID shell to escalate to root and retrieve the final flag.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Valid Accounts | T1078 |
| Brute Force: Password Spraying | T1110.003 |
| Scheduled Task/Job: Cron | T1053.003 |
| Abuse Elevation Control Mechanism: SUID/SGID | T1548.001 |

### CWE

- **CWE-284:** Improper Access Control (FTP anonymous access exposing credentials)
- **CWE-732:** Incorrect Permission Assignment for Critical Resource (writable cron script)

---

> "Open your eyes, and you will see: the simplest paths are often the most dangerous. A password left in plain sight on an FTP server is a welcome mat for uninvited guests."

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
