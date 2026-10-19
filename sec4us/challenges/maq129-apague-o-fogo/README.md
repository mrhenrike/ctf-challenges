# Maq129: Apague o Fogo

Writeup for the **Apague o Fogo** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Medium
> **Difficulty:** Medium

---

## Overview

A WordPress-based challenge where VPN MTU issues cause large pages to fail loading. After fixing the MSS (Maximum Segment Size) on the VPN route, standard WordPress enumeration and exploitation techniques lead to initial access and privilege escalation.

## Reconnaissance

1. Scan the target to identify WordPress running on the web server.
2. Notice that large pages fail to load or hang indefinitely over the VPN.
3. Diagnose the issue as an MTU/MSS mismatch on the VPN tunnel.
4. Apply the fix: `ip route change <target_network> via <gw> dev tun0 advmss 200`.
5. With connectivity restored, enumerate WordPress with `wpscan` for users, themes, and plugins.

## Exploitation

1. Identify vulnerable WordPress plugins or themes from the scan results.
2. Enumerate valid usernames through author enumeration or login error messages.
3. Perform password brute-force against discovered user accounts.
4. Authenticate to the WordPress admin panel with valid credentials.
5. Upload a malicious plugin or edit a theme PHP file to inject a web shell.
6. Trigger the payload to establish a reverse shell as the web server user.

## Privilege Escalation

1. Enumerate the Linux system for escalation paths: sudo rules, SUID binaries, cron jobs.
2. Check WordPress `wp-config.php` for database credentials that may be reused.
3. Exploit the identified misconfiguration to escalate to root.
4. Retrieve the flag from the root home directory.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Exploit Public-Facing Application | T1190 |
| Brute Force: Password Guessing | T1110.001 |
| Server Software Component: Web Shell | T1505.003 |
| Valid Accounts | T1078 |

### CWE

- **CWE-521:** Weak Password Requirements (brute-forceable WordPress credentials)
- **CWE-434:** Unrestricted Upload of File with Dangerous Type (plugin/theme upload)

---

> "Sometimes the fire is not on the server but on the wire. When packets refuse to arrive, fix the plumbing before reaching for the extinguisher. A misconfigured MSS can hide an entire attack surface."

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
