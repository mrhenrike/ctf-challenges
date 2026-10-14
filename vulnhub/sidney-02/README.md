# Sidney: 0.2 — Writeup

<!-- generated from known techniques; verify against live VM -->

| | |
|-|-|
| **Target IP** | 192.168.56.X (host-only) |
| **Difficulty** | Easy |
| **OS** | Linux |
| **Root Flag** | /root/flag.txt |
| **Source** | [VulnHub](https://www.vulnhub.com/entry/sidney-02,210/) |

## Attack Summary

nmap → web enumeration + FTP anonymous → steganography/source code creds → SSH → SUID/sudo privesc → root

## Methodology

1. Network discovery + port scan
2. FTP anonymous login — collect files
3. Web source code / hidden files → credentials
4. SSH login
5. SUID binary or sudo misconfiguration → root

---

## Step 1: Network Discovery

```bash
sudo netdiscover -i eth1 -r 192.168.56.0/24
nmap -sV -sC -p- <TARGET_IP>
```

Expected open ports: 21 (FTP), 22 (SSH), 80 (HTTP).

---

## Step 2: FTP Anonymous Login

```bash
ftp <TARGET_IP>
# User: anonymous / Password: (blank)
ls -al
# Download all files
mget *
```

Inspect downloaded files for credentials or hidden data.

---

## Step 3: Web Enumeration

```bash
gobuster dir -u http://<TARGET_IP>/ \
  -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt \
  -x php,txt,html -t 50
```

Check page source for commented credentials. Check robots.txt and any config files.

---

## Step 4: Steganography (if image files found)

```bash
steghide extract -sf <image_file>
# Try blank passphrase first
exiftool <image_file>
strings <image_file>
```

---

## Step 5: SSH Login

Use credentials found in FTP files, web source, or steganography:

```bash
ssh <user>@<TARGET_IP>
```

---

## Step 6: Privilege Escalation

```bash
sudo -l
find / -perm -u=s -type f 2>/dev/null
```

Common escalation paths on this VM:
- SUID binary → shell escape
- sudo NOPASSWD misconfiguration

```bash
whoami
# root
cat /root/flag.txt
```

---

## Lessons Learned

1. **Anonymous FTP** with sensitive files enables unauthenticated credential retrieval
2. **Credentials in web source** or embedded in images are easily extracted with basic tools
3. **SUID misconfigurations** remain the most common Linux privesc vector

## Remediation

| Vulnerability | Fix |
|---------------|-----|
| Anonymous FTP | Disable anonymous login; use authenticated access only |
| Credentials in source/images | Never embed credentials in client-visible assets |
| SUID misconfigurations | Audit with `find / -perm -u=s` and remove unnecessary SUID bits |
