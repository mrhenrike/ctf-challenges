# Tr0ll 3 — Writeup

**Difficulty:** Intermediate  
**Category:** VulnHub — Boot2Root  
**OS:** Ubuntu 14.04/16.04 LTS  
**Platform:** [VulnHub](https://www.vulnhub.com/entry/tr0ll-3,340/)  
**Status:** Partial — attack chain reconstructed from loot artifacts (no NOTES.md available)

---

## Overview

Tr0ll 3 continues the series with a multi-user credential chain and RSA key-based access. The VM requires moving through several user accounts — `start`, `wytshadow`, `genphlux`, `maleus` — before reaching root. The FTP service exposes a wireless capture file (`wytshadow.cap`) and an RSA private key for the `maleus` account.

**Artifacts recovered:**
- `/etc/passwd` and `/etc/shadow` (full dump)
- Credentials: `start:here`, `wytshadow:gaUoCe34t1`, `genphlux:HF9nd0cR!`
- RSA private key for `maleus` (from FTP)
- Root flag from `/root/Proof.txt`

---

## Prerequisites

- VirtualBox or VMware
- Kali Linux (attacker)
- Tools: `nmap`, `ftp`, `aircrack-ng`, `ssh`, `john`/`hashcat`

---

## Attack Summary

```
FTP (anonymous or start:here) → wytshadow.cap (WPA handshake)
→ aircrack-ng → wytshadow:gaUoCe34t1 → SSH
→ genphlux:HF9nd0cR! → SSH
→ maleus RSA key → SSH → privilege escalation → root
```

---

## Enumeration

### Host Discovery

```bash
nmap -sn 192.168.56.0/24
```

### Port Scan

```bash
nmap -sV -A -p- <TARGET_IP>
```

Expected services (based on series pattern): FTP (21), SSH (22), HTTP (80)

### Users on the System

From `/etc/passwd`:

| User | UID | Shell |
|------|-----|-------|
| maleus | 1000 | /bin/bash |
| start | 1001 | /bin/bash |
| eagle | 1002 | /bin/bash |
| wytshadow | 1003 | /bin/bash |
| genphlux | 1004 | /bin/bash |
| fido | 1005 | /bin/bash |
| step2 | 1006 | /bin/bash |

---

## Exploitation

### Step 1: FTP Access

```bash
ftp <TARGET_IP>
# Try: anonymous / anonymous
# Or: start / here
```

Files available via FTP:
```
maleus_id_rsa    ← RSA private key for maleus
wytshadow.cap    ← wireless capture (WPA handshake)
```

Download both:
```bash
ftp> get maleus_id_rsa
ftp> get wytshadow.cap
ftp> bye
```

### Step 2: Crack wytshadow.cap (WPA Handshake)

```bash
aircrack-ng -w /usr/share/wordlists/rockyou.txt wytshadow.cap
# KEY FOUND! [ gaUoCe34t1 ]
```

Credential: `wytshadow` / `gaUoCe34t1`

### Step 3: SSH as wytshadow

```bash
ssh wytshadow@<TARGET_IP>
# Password: gaUoCe34t1

wytshadow@Tr0ll3:~$ id
# uid=1003(wytshadow) gid=1003(wytshadow)
```

### Step 4: Lateral Movement to genphlux

Once on the system, enumerate files in other home directories or sudoers:

```bash
sudo -l
# or check readable files in /home/
cat /home/genphlux/.something
# Credential hint: genphlux:HF9nd0cR!
```

```bash
su genphlux
# Password: HF9nd0cR!
# or
ssh genphlux@localhost
```

### Step 5: SSH as maleus via RSA Key

```bash
chmod 600 maleus_id_rsa
ssh -i maleus_id_rsa maleus@<TARGET_IP>

maleus@Tr0ll3:~$ id
# uid=1000(maleus) gid=1000(maleus)
```

---

## Privilege Escalation

### Step 6: Enumerate Path to Root

From the `maleus` account, check:

```bash
sudo -l
# Check for NOPASSWD entries

find / -perm -4000 -type f 2>/dev/null
# Look for SUID binaries

ls -la /etc/cron*
# Check cron jobs owned/writable by maleus

find / -writable -not -path "/proc/*" -type f 2>/dev/null 2>&1 | grep -v "Permission denied"
```

> **Note:** The exact privilege escalation path was not captured in the available artifacts. Based on the Tr0ll series pattern and the user structure (`start`, `step2`, `fido` suggest a sequential chain), the likely path involves: `maleus → sudoers entry or world-writable script → root`.

---

## Root Flag

```bash
cat /root/Proof.txt
```

```
You are truly a Jedi!

Twitter Proof:

Pr00fThatTh3L33tHax0rG0tTheFl@g!!

@Maleus21
```

---

## Credentials Summary

| User | Credential | Source |
|------|-----------|--------|
| start | `here` | FTP hint |
| wytshadow | `gaUoCe34t1` | aircrack-ng on wytshadow.cap |
| genphlux | `HF9nd0cR!` | Lateral enumeration |
| maleus | RSA private key | FTP (maleus_id_rsa) |

---

## Lessons Learned

- WPA handshake captures in FTP are a critical information disclosure — `aircrack-ng` with `rockyou.txt` cracks weak passphrases in seconds
- Multi-user credential chains require methodical enumeration of each account before escalating
- RSA private keys stored in world-readable FTP directories eliminate the security of key-based authentication
- Sequential user accounts (`start`, `step2`, `fido`) often hint at the intended path order

## Remediation

- Never store WPA captures, private keys, or credential files in FTP-accessible directories
- Enforce strong WPA2/WPA3 passphrases (≥ 20 random characters)
- Rotate SSH keys; never reuse or expose private keys
- Apply least-privilege principles: users should not have read access to other users' home directories
