# Maq153: Mr.Sean

Writeup for the **Mr.Sean** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Medium
> **Difficulty:** Medium

---

## Overview

A WordPress site with the WP-Forum plugin, which is vulnerable to SQL injection. The attack chain progresses from SQLi to admin access, plugin-based RCE for initial shell, SSH lateral movement as user "sean", and sudo misconfiguration for root.

## Reconnaissance

1. Scan the target to identify WordPress and SSH services.
2. Run `wpscan` to enumerate WordPress plugins, themes, and users.
3. Identify the WP-Forum plugin as an installed and potentially vulnerable component.
4. Research WP-Forum SQL injection vulnerabilities and available exploits.

## Exploitation

1. Exploit the SQL injection vulnerability in the WP-Forum plugin.
2. Extract WordPress admin password hashes from the database via SQLi.
3. Crack the admin hash or use the SQLi to update the admin password directly.
4. Authenticate to the WordPress admin panel.
5. Install a malicious plugin or edit a PHP theme file to inject a reverse shell.
6. Trigger the payload and catch the shell as the web server user.

## Privilege Escalation

1. Enumerate users on the system and identify the "sean" account.
2. Find credentials for "sean" in WordPress configuration, database, or local files.
3. SSH into the machine as user "sean" for a stable shell.
4. Check sudo permissions: `sudo -l`.
5. Exploit the sudo misconfiguration to escalate to root.
6. Retrieve the root flag.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Exploit Public-Facing Application | T1190 |
| Server Software Component: Web Shell | T1505.003 |
| Valid Accounts: Local Accounts | T1078.003 |
| Abuse Elevation Control Mechanism: Sudo | T1548.003 |

### CWE

- **CWE-89:** Improper Neutralization of SQL Commands (WP-Forum SQLi)
- **CWE-434:** Unrestricted Upload of File with Dangerous Type (plugin upload RCE)
- **CWE-269:** Improper Privilege Management (sudo misconfiguration)

---

> "Mr. Sean trusted a forum plugin with his kingdom. SQL spoke first, WordPress answered, and sudo handed over the crown. Chain your kills, not your trust."

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
