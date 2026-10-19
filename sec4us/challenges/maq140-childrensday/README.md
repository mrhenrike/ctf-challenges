# Maq140: ChildrensDay

Writeup for the **ChildrensDay** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Medium
> **Difficulty:** Medium

---

## Overview

A multi-vector challenge combining FTP enumeration, Apache path traversal leading to remote code execution, and privilege escalation via Dirty Pipe (CVE-2022-0847), a Linux kernel vulnerability allowing arbitrary overwrite of read-only files.

## Reconnaissance

1. Run a comprehensive port scan to discover FTP, HTTP/Apache, and other services.
2. Connect to FTP and enumerate accessible directories and files.
3. Investigate the Apache web server for directory listings, virtual hosts, and hidden paths.
4. Identify the Linux kernel version for local privilege escalation research.

## Exploitation

1. Explore the FTP service for useful files, configuration data, or hints.
2. Discover an Apache path traversal vulnerability that allows reading or writing server-side files.
3. Chain the path traversal with a file write to achieve remote code execution.
4. Upload or write a reverse shell payload to an executable location on the web server.
5. Trigger the payload and catch the reverse shell as the Apache service user.

## Privilege Escalation

1. Check the kernel version and confirm vulnerability to CVE-2022-0847 (Dirty Pipe).
2. Dirty Pipe allows unprivileged users to overwrite data in read-only files by abusing the pipe buffer mechanism.
3. Transfer and compile the Dirty Pipe exploit on the target.
4. Use the exploit to overwrite `/etc/passwd` (setting root with no password) or a SUID binary.
5. Authenticate as root or execute the modified SUID binary to gain root access.
6. Retrieve the final flag.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Exploit Public-Facing Application | T1190 |
| Exploitation for Privilege Escalation | T1068 |
| Server Software Component: Web Shell | T1505.003 |
| Data from Network Shared Drive | T1039 |

### CWE

- **CWE-22:** Improper Limitation of a Pathname to a Restricted Directory (path traversal)
- **CWE-281:** Improper Preservation of Permissions (Dirty Pipe kernel flaw)

---

> "On Children's Day, even the kernel plays with pipes. CVE-2022-0847 proved that sometimes the youngest vulnerabilities are the most dangerous: a pipe left open can flood the entire system."

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
