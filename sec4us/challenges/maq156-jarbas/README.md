# Maq156: Jarbas

Writeup for the **Jarbas** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Medium
> **Difficulty:** Medium

---

## Overview

A Jenkins server where credentials are discovered through web enumeration. The Jenkins Script Console accepts Groovy code for remote command execution, and a writable cron job provides the path to root.

## Reconnaissance

1. Scan the target to discover Jenkins (typically on port 8080) and other services.
2. Enumerate the web server for hidden directories, files, and backup pages.
3. Discover a page or file containing Jenkins credentials (e.g., an exposed HTML page with hashed or plaintext credentials).
4. Crack any discovered hashes to obtain login credentials.

## Exploitation

1. Authenticate to Jenkins with the discovered credentials.
2. Navigate to "Manage Jenkins" > "Script Console".
3. Execute Groovy code to run OS commands on the underlying server.
4. Use the Groovy Script Console to establish a reverse shell.
5. Catch the reverse shell as the Jenkins service user.

## Privilege Escalation

1. Enumerate scheduled tasks: `cat /etc/crontab` and `ls -la /etc/cron.*`.
2. Identify a cron job running as root that references a writable script.
3. Modify the cron script to inject a reverse shell or add a SUID backdoor.
4. Wait for the cron job to execute with root privileges.
5. Escalate to root and retrieve the flag.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Unsecured Credentials: Credentials in Files | T1552.001 |
| Command and Scripting Interpreter | T1059 |
| Scheduled Task/Job: Cron | T1053.003 |
| Valid Accounts | T1078 |

### CWE

- **CWE-312:** Cleartext Storage of Sensitive Information (exposed credentials)
- **CWE-94:** Improper Control of Generation of Code (Groovy script execution)
- **CWE-732:** Incorrect Permission Assignment for Critical Resource (writable cron script)

---

> "Jarbas, the butler, left the keys on the counter and the schedule on the fridge. A Script Console with valid credentials is not a feature; it is an open door. And a writable cron job? That is the welcome mat."

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
