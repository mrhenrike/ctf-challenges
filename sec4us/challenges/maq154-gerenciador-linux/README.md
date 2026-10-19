# Maq154: Gerenciador de Servicos Linux

Writeup for the **Gerenciador de Servicos Linux** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Medium
> **Difficulty:** Medium

---

## Overview

A Linux system managed through Webmin, an older version vulnerable to CVE-2006-3392. This directory traversal vulnerability in Webmin's `miniserv.pl` allows unauthenticated reading of arbitrary files, leading to credential extraction and full system compromise.

## Reconnaissance

1. Scan the target to identify Webmin (typically on port 10000) and other services.
2. Confirm the Webmin version through the login page or HTTP headers.
3. Research CVE-2006-3392: a directory traversal in Webmin's `miniserv.pl` via the URL path.
4. Identify additional services (SSH, HTTP) for potential lateral entry.

## Exploitation

1. Exploit CVE-2006-3392 by crafting a URL with directory traversal sequences.
2. Read `/etc/shadow` or `/etc/passwd` to extract user account information.
3. Alternatively, read Webmin's own configuration files for stored credentials.
4. Crack extracted password hashes or use discovered plaintext credentials.
5. Authenticate to the target via SSH or Webmin with the recovered credentials.
6. Gain an initial shell on the system.

## Privilege Escalation

1. If initial access is as a non-root user, enumerate sudo permissions and SUID binaries.
2. Check for password reuse between Webmin admin and the root account.
3. Leverage Webmin's own administrative capabilities if authenticated as admin (Webmin can execute commands as root).
4. Achieve root access and retrieve the flag.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Exploit Public-Facing Application | T1190 |
| Unsecured Credentials: Credentials in Files | T1552.001 |
| Valid Accounts | T1078 |

### CWE

- **CWE-22:** Improper Limitation of a Pathname to a Restricted Directory (directory traversal)
- **CWE-200:** Exposure of Sensitive Information to an Unauthorized Actor
- **CWE-916:** Use of Password Hash With Insufficient Computational Effort

---

> "A service manager should protect, not expose. When Webmin's own file server walks backwards through the filesystem, every shadow becomes readable and every secret becomes leverage."

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
