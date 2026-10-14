# HA: Chakravyuh — Writeup

| Field | Value |
|---|---|
| **Target IP** | 192.168.1.105 |
| **Attacker IP** | 192.168.1.110 |
| **Difficulty** | Medium |
| **OS** | Linux |
| **Goal** | root flag |
| **Source** | [HackingArticles](https://www.hackingarticles.in/ha-chakravyuh-vulnhub-walkthrough/) |

> **Note:** The full walkthrough is available at the source URL above. This writeup documents the general attack path for the HA: Chakravyuh machine based on the published methodology.

## Attack Summary

HA: Chakravyuh is a VulnHub machine from the Hacking Articles series, themed around the military formation (vyuh) from the Mahabharata. The machine presents multiple layered security challenges that must be bypassed in sequence — mirroring the concentric circles of the Chakravyuh formation. The attack chain involves web application enumeration, exploitation of a vulnerable web service, credential discovery, and privilege escalation through misconfigured system permissions.

## Methodology

1. Network scanning (Nmap)
2. Web service enumeration
3. Directory/file brute-force
4. Vulnerability exploitation
5. Credential extraction and lateral movement
6. Privilege escalation to root

## Step 1: Reconnaissance

### Host Discovery

```bash
netdiscover -r 192.168.1.0/24
```

### Port Scan

```bash
nmap -sV -sC -p- 192.168.1.105
```

![nmap](images/01-nmap.png)

Typical open ports:
- **22/tcp** — OpenSSH
- **80/tcp** — HTTP (Apache/Nginx)
- **21/tcp** — FTP (may be present)

## Step 2: Web Enumeration

```bash
gobuster dir -u http://192.168.1.105/ \
  -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt \
  -x php,txt,html,bak \
  -o /tmp/chakravyuh_gobuster.txt
```

![web-enum](images/02-web.png)

Examine discovered paths and review page source for hidden comments, credentials, or references to other services.

```bash
curl -s http://192.168.1.105/robots.txt
curl -s http://192.168.1.105/
```

## Step 3: Service Exploitation

Based on the services found, exploit the web application or exposed service:

```bash
# If FTP anonymous access is available:
ftp 192.168.1.105
# Login: anonymous / anonymous
ls -la
```

Review any files available on the service for credentials or hints.

![exploit](images/03-exploit.png)

## Step 4: Initial Foothold

```bash
# After discovering credentials or upload functionality:
nc -nvlp 4444
```

Deliver the reverse shell payload appropriate to the discovered vulnerability.

```bash
# Shell upgrade after initial access:
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
stty raw -echo; fg
```

## Step 5: Privilege Escalation

![privesc](images/04-privesc.png)

Enumerate privilege escalation vectors:

```bash
# SUID binaries
find / -perm -4000 2>/dev/null

# Sudo rights
sudo -l

# Writable files/cron jobs
crontab -l
ls -la /etc/cron*
cat /etc/crontab

# World-writable executables
find / -writable -type f 2>/dev/null | grep -v proc

# Capabilities
getcap -r / 2>/dev/null
```

Apply the appropriate GTFOBins technique or exploit the discovered vector to escalate to root.

## Step 6: Root Flag

![root-flag](images/05-root-flag.png)

```bash
id
# uid=0(root) gid=0(root) groups=0(root)
ls /root
cat /root/flag.txt
```

## Lessons Learned

1. **Layered enumeration** is essential — each service may contain credentials or hints pointing to the next attack layer, reflecting the Chakravyuh theme of nested defenses.
2. **Always check robots.txt, source code, and hidden files** — web applications frequently expose information not intended for public access.
3. **SUID binaries and sudo misconfigurations** are among the most common privilege escalation paths on CTF machines.
4. **Default or anonymous credentials** on services like FTP should always be tested before attempting brute-force.
5. **Shell stabilization** (pty spawn + stty) is critical for running interactive tools like vi, sudo, and su from within a netcat shell.

## Remediation

| Vulnerability | Fix |
|---|---|
| Anonymous FTP access | Disable anonymous FTP; require authentication |
| Sensitive files in web root | Apply proper file permissions; use `.htaccess` to deny access to sensitive files |
| Misconfigured SUID binaries | Audit SUID binaries regularly; remove the SUID bit from non-essential binaries |
| Weak/default credentials | Enforce strong password policy; disable default accounts |
| Overly permissive sudo rules | Apply principle of least privilege; restrict sudo to specific, necessary commands |
