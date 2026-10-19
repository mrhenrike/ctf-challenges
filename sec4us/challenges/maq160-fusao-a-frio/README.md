# Maq160: Fusao a Frio (ColdFusion)

> **Platform:** SEC4US CTF Lab | **Category:** Web Hacking: Medium | **Points:** Dynamic

## Overview

Adobe ColdFusion 8 on Windows with an accessible admin panel. Exploitation through Task Scheduler for webshell deployment.

---

## Approach

**Technique:** ColdFusion Admin Task Scheduler + CFM RCE

### Reconnaissance

```bash
nmap -sV -sC -p- <TARGET_IP> -oN nmap_full.txt
```

ColdFusion administrator panel accessible on port 8500.

### Exploitation

1. **Admin access:** Obtain ColdFusion admin credentials through directory traversal or default configuration
2. **Task Scheduler abuse:** Use the ColdFusion Task Scheduler to write a CFM webshell to the webroot
3. **Command execution:** Execute commands through the CFM webshell using `cfexecute`
4. **Flag retrieval:** Read the flag from the Windows filesystem

```
http://<TARGET>:8500/CFIDE/administrator/
```

The Task Scheduler allows downloading remote files to arbitrary paths on the server, effectively creating a webshell.

### Tools Used

nmap, curl, Burp Suite, Metasploit (coldfusion_fckeditor)

---

## Security Frameworks

### MITRE ATT&CK

| Technique | Description |
|-----------|-------------|
| T1190 | Exploit Public-Facing Application |
| T1059.003 | Windows Command Shell |

### CWE

| ID | Description |
|----|-------------|
| CWE-22 | Path Traversal |
| CWE-798 | Use of Hard-coded Credentials |

---

## Author

**Andre Henrike** (@mrhenrike)

ColdFusion: still serving webshells from the admin panel since 2009. Thanks guys!! (❍ᴥ❍ʋ)

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

*For educational purposes only. Do not use any technique shown here against systems you do not own or have explicit permission to test.*
