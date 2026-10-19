# maq123: Sistema de Cadastro XML

Writeup for the **Sistema de Cadastro XML** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Web Hacking  
> **Difficulty:** Easy  
> **Points:** 123

---

## Overview

A registration system processes user-submitted XML data without disabling external entity resolution, making it vulnerable to XML External Entity (XXE) injection for file disclosure and potential remote code execution.

## Reconnaissance

Scan and enumerate the target:

```bash
nmap -sC -sV -p- <TARGET_IP>
```

Access the web application and identify forms or endpoints that accept XML input. Inspect requests with Burp Suite to confirm the Content-Type and XML structure.

## Exploitation

### Step 1: Identify XML Processing

Submit a valid XML payload through the registration form and observe the server response. Confirm the backend parses XML.

### Step 2: Test XXE File Read

Craft an XXE payload to read local files:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<registration>
  <name>&xxe;</name>
</registration>
```

### Step 3: Extract Sensitive Data

Use the XXE vector to read configuration files, SSH keys, or application source code:

```xml
<!ENTITY xxe SYSTEM "file:///etc/shadow">
```

### Step 4: Retrieve the Flag

Read the flag file path through the XXE entity resolution.

## Privilege Escalation

If initial access is limited, leverage disclosed credentials or SSH keys found via XXE to escalate privileges on the target system.

## Security Framework Mapping

### MITRE ATT&CK

| Technique                         | ID        |
|-----------------------------------|-----------|
| Exploit Public-Facing Application | T1190     |
| Data from Local System            | T1005     |
| Unsecured Credentials: Files      | T1552.001 |

### CWE

- **CWE-611:** Improper Restriction of XML External Entity Reference
- **CWE-776:** Improper Restriction of Recursive Entity References in DTDs

---

When a parser trusts every entity you define, the filesystem becomes an open library; the catalog is yours to browse.

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
