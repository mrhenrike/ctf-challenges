# Maq138: CMS das Profundezas

Writeup for the **CMS das Profundezas** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Medium
> **Difficulty:** Medium

---

## Overview

A Linux target running kernel 2.6.32 with an exploitable CMS. After gaining initial access through the web application, privilege escalation is achieved via CVE-2010-3904, a local privilege escalation in the RDS (Reliable Datagram Sockets) protocol implementation.

## Reconnaissance

1. Perform a full port scan to discover web and other services.
2. Access the web application and identify the CMS platform and version.
3. Enumerate CMS users, plugins, themes, and known vulnerabilities.
4. Research the CMS version for public exploits or default credentials.

## Exploitation

1. Exploit the identified CMS vulnerability to gain authenticated access or direct code execution.
2. If authentication is obtained first, use CMS admin features to upload or inject a web shell.
3. Establish a reverse shell from the web server.
4. Confirm the kernel version: Linux 2.6.32.
5. Verify that the RDS kernel module is loaded (`lsmod | grep rds`).

## Privilege Escalation

1. Research CVE-2010-3904: a vulnerability in the Linux kernel's RDS socket implementation allowing local users to escalate privileges.
2. Transfer the exploit to the target machine (compile on target or transfer pre-compiled binary).
3. Execute the RDS socket exploit to gain root privileges.
4. Read the flag from the root-restricted location.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Exploit Public-Facing Application | T1190 |
| Exploitation for Privilege Escalation | T1068 |
| Server Software Component: Web Shell | T1505.003 |

### CWE

- **CWE-416:** Use After Free (CVE-2010-3904 kernel vulnerability)
- **CWE-269:** Improper Privilege Management (unpatched kernel)

---

> "From the depths of an ancient kernel, a forgotten socket protocol surfaces to grant root. CMS das Profundezas reminds us: the deepest vulnerabilities are not always in the application layer."

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
