# Enubox: Mattermost — The Collaboration Platform That Talked Too Much

Alright guys!! Who would have thought a team messaging platform would spill its own credentials? Enubox: Mattermost is a beautifully layered chain: TFTP leaks admin creds, Mattermost's Zoom plugin leaks FTP creds, FTP leaks an SSH password, and a custom binary with a hardcoded hex key asks you to prove you can open Ghidra. Four services, four pivots, one root. Absolutely goated puzzle design, no cap.

| Field | Value |
|---|---|
| **Level** | Medium |
| **Target VM** | Enubox: Mattermost |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/enubox-mattermost,414/ |
| **Techniques** | UDP/TCP nmap, TFTP anonymous read, Mattermost admin panel, plugin credential disclosure, FTP anonymous, binary RE with Ghidra (hex constant), GTFOBins-style key derivation |
| **CVEs** | CWE-200 (Information Exposure via TFTP), CWE-522 (Insufficiently Protected Credentials in plugin config), CWE-798 (Hardcoded credentials in binary) |
| **APT Groups** | APT41: uses collaborative platform credential disclosure for initial access in enterprise intrusions; FIN7: pivots through misconfigured file-transfer services to reach internal systems |

---

## Attack Summary

```
nmap -sT -sU → TFTP/69, FTP/21, SSH/22, HTTP/80, Mattermost/8065
  → TFTP anonymous: get README.md → admin:ComplexPassword0!
  → Mattermost :8065 login → System Console → Zoom plugin
  → change Zoom API URL to target → response leaks FTP creds
  → FTP ftpuser:ftppassword → /users/mattermost/message → SSH pass "Welcome!!"
  → SSH mattermost@target → Desktop/secret binary
  → transfer binary to attacker → Ghidra decompile main()
  → hex constant 0xf447 → decimal 62535
  → ./secret → enter 62535 → uid=0(root)
  → /root/Desktop/local.txt
```

---

## Methodology

1. Full TCP + UDP port scan to surface TFTP (UDP/69) alongside standard services
2. TFTP anonymous read of README.md to obtain Mattermost admin credentials
3. Mattermost admin panel: enable Zoom plugin, manipulate API URL to trigger credential disclosure
4. FTP login with disclosed credentials, retrieve SSH password from mailbox file
5. SSH as mattermost, enumerate Desktop
6. Transfer custom binary to attacker, decompile with Ghidra
7. Extract hardcoded hex key from main(), convert to decimal, supply to binary, obtain root shell

---

## Step 1 — Host Discovery and Full Port Scan

```bash
sudo netdiscover -r 192.168.0.0/24
# Target: 192.168.0.110

nmap -sT -sU -A -p- 192.168.0.110
```

```
PORT     STATE SERVICE  VERSION
21/tcp   open  ftp      vsftpd 3.0.3
22/tcp   open  ssh      OpenSSH 7.x
80/tcp   open  http     Apache httpd 2.4.x
8065/tcp open  http     Mattermost
69/udp   open  tftp     TFTP
```

Five services, legit attack surface. TFTP on UDP is easy to miss without `-sU`. HTTP on 80 and Mattermost on 8065 are both worth visiting. Start with TFTP.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — TFTP Anonymous Read

TFTP has no authentication by default. Any file in the TFTP root is readable:

```bash
tftp 192.168.0.110
tftp> get README.md
tftp> quit
cat README.md
```

```
Mattermost admin credentials
Username: admin
Password: ComplexPassword0!
```

Credentials in a TFTP-accessible file. Wild. This is exactly how real-world TFTP misconfigurations play out.

**Real-world note:** TFTP is still used for PXE booting, network device firmware delivery, and IP phone configuration. Exposing it to the network without IP filtering is a critical finding in any enterprise audit. OceanLotus (APT32) specifically targeted exposed TFTP servers in Southeast Asian government networks to extract device configurations.

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1552.001 — Credentials in Files

---

## Step 3 — Mattermost Admin Panel: Zoom Plugin Credential Disclosure

Navigate to `http://192.168.0.110:8065/login`. Log in as `admin` / `ComplexPassword0!`.

Go to: **System Console > Plugins > Zoom**. Enable the Zoom plugin. Open its configuration. Change the Zoom API URL from `localhost` to the target IP `192.168.0.110`. Save configuration.

The plugin attempts a callback to the URL and the error response leaks the FTP credentials configured in the backend:

```
FTP User: ftpuser
FTP Pass: ftppassword
```

**Why does this happen?** Plugin integrations that echo backend service credentials in API error responses are a classic misconfiguration. The Zoom plugin was designed for an internal Zoom server; repurposing the callback URL triggers an unexpected code path that dumps the FTP credentials to the admin UI.

**Alternatively:** Check the Mattermost configuration files directly if you already have RCE or a filesystem read primitive.

**MITRE ATT&CK:** T1078.001 — Valid Accounts: Default Accounts; T1552.001 — Credentials in Files

---

## Step 4 — FTP Access: Retrieve SSH Password

```bash
ftp 192.168.0.110
Name: ftpuser
Password: ftppassword
ftp> ls -la
ftp> cd users/mattermost
ftp> get message
ftp> bye
cat message
```

```
Dear mattermost,
Your SSH temporary password is: Welcome!!
```

Credential chain complete: TFTP → Mattermost admin → FTP → SSH password.

**MITRE ATT&CK:** T1021.003 — Remote Services: FTP; T1552.001 — Credentials in Files

---

## Step 5 — SSH Access and Binary Discovery

```bash
ssh mattermost@192.168.0.110
# Password: Welcome!!

ls
cd Desktop/
ls -la
cat README.md
./secret
```

The `README.md` on the Desktop contains a key string that appears to work but the binary returns "expired." The binary requires reverse engineering.

Transfer to attacker machine:

```bash
# On target (start HTTP server)
python3 -m http.server 8080

# On attacker
wget http://192.168.0.110:8080/secret
chmod +x secret
```

**MITRE ATT&CK:** T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 6 — Binary Reverse Engineering with Ghidra

Open the binary in Ghidra. Create a new project, import `secret`, let auto-analysis run, then open the **CodeBrowser**.

Navigate to `main()` in the decompiler view. The function reads user input and compares it against a hexadecimal constant:

```c
if (input == 0xf447) {
    // spawn shell
}
```

Convert the hex to decimal:

```bash
python3 -c "print(0xf447)"
# 62535
```

**Alternative (no Ghidra):** Use radare2 or strings:

```bash
strings secret | grep -E '^[0-9]+$'
# May not surface the constant directly, but radare2 will:
r2 secret
[0x00400550]> aaa
[0x00400550]> pdf @ main
# Look for the CMP instruction operand
```

**MITRE ATT&CK:** T1027 — Obfuscated Files or Information (hardcoded constant)

---

## Step 7 — Root Shell via Binary Key

```bash
./secret
Enter key: 62535

whoami
# root

cd /root/Desktop
cat local.txt
```

Root obtained. The binary was a SUID binary that spawned a root shell on correct key input.

**MITRE ATT&CK:** T1548.001 — Abuse Elevation Control Mechanism: Setuid and Setgid

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|---|---|---|---|
| Credential | admin:ComplexPassword0! | TFTP README.md | Mattermost admin login |
| Credential | ftpuser:ftppassword | Mattermost Zoom plugin disclosure | FTP login |
| Credential | mattermost:Welcome!! | FTP /users/mattermost/message | SSH login |
| Binary key | 62535 (0xf447) | Ghidra decompile of `secret` binary | Root shell |
| Root flag | local.txt | /root/Desktop/local.txt | Captured |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | TFTP exposes credentials in anonymous-readable file | TFTP still runs on thousands of enterprise networks for PXE boot and VOIP phone config; files in TFTP root are readable by anyone on the network | Disable TFTP or restrict to specific IP ranges; never store credentials in TFTP-accessible paths |
| 2 | Collaboration platform plugin leaks downstream service credentials in error response | SaaS platforms with plugin ecosystems regularly expose credentials through misconfigured integration callbacks | Sanitize all plugin configuration responses; credentials must never appear in API error output |
| 3 | Credential chain: TFTP → Mattermost → FTP → SSH | Real APT intrusions often chain three to four credential pivots across services; each service trusts credentials from the previous one | Segment credential stores; rotate credentials independently per service |
| 4 | Hardcoded numeric key in SUID binary | Developers embed "security" checks in binaries assuming users cannot reverse-engineer them; this is security through obscurity | Never use hardcoded secrets for privilege elevation; use PAM or proper authentication |
| 5 | Python3 HTTP server for binary transfer | Legitimate built-in tools enable file transfer without installing additional software | Baseline and monitor ad-hoc HTTP services on endpoints (T1105 Ingress Tool Transfer) |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | File and Directory Discovery | T1083 |
| Initial Access | Credential Access | Credentials in Files (TFTP) | T1552.001 |
| Initial Access | Initial Access | Valid Accounts: Default Accounts | T1078.001 |
| Lateral Movement | Lateral Movement | Remote Services: FTP | T1021.003 |
| Credential Access | Credential Access | Credentials in Files (FTP message) | T1552.001 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Collection | Collection | Data from Local System | T1005 |
| Defense Evasion | Defense Evasion | Obfuscated Files or Information | T1027 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Setuid | T1548.001 |

---

## Remediation and Containment

### Technical Fixes

1. **Disable TFTP or restrict by IP** — TFTP should never be accessible from workstations; restrict to management VLAN; never store credentials in TFTP root
2. **Sanitize plugin configuration responses** — plugin integrations must not echo backend credentials in any response visible to admin users
3. **Rotate credentials per service** — each service (FTP, SSH, Mattermost) must use independent credentials; credential sharing enables the entire chain
4. **Remove SUID from the custom binary** — if privilege elevation is intended, use sudo with a specific allowlist entry; never embed keys in SUID binaries
5. **Enforce SSH key-based authentication** — disable password authentication in sshd\_config

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all TFTP and FTP services; document purpose and access controls |
| Protect | Access Control | Restrict TFTP to management VLAN; disable anonymous FTP access |
| Protect | Data Security | Remove credentials from TFTP-accessible files; sanitize plugin responses |
| Detect | Anomalies and Events | Alert on TFTP reads, FTP logins, and ad-hoc HTTP servers on endpoints |
| Respond | Response Planning | Rotate all credentials in the chain; disable TFTP and FTP if not needed |
| Recover | Recovery Planning | Audit all SUID binaries; rebuild compromised host |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Restrict TFTP and FTP to authorized hosts only |
| AC-6 | Least Privilege | Remove SUID from non-essential binaries |
| IA-5 | Authenticator Management | Rotate all credentials; do not reuse across services |
| SC-28 | Protection of Information at Rest | No credentials stored in TFTP-accessible files |
| CM-7 | Least Functionality | Disable TFTP if not required; restrict FTP to specific accounts |
| SA-11 | Developer Security Testing | Security code review for hardcoded secrets in binaries |

### CISA KEV

The TFTP anonymous access pattern and credential-in-plugin-response disclosure map to patterns documented in CISA Alert AA22-074A (threat actor use of misconfigured services for initial access). Organizations are advised to audit all UDP services for anonymous access per CISA guidance.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Threat and Vulnerability Management (THREAT) | Manage Vulnerabilities | MIL2 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT Asset Inventory | MIL2 |

### MITRE D3FEND Countermeasures

- **D3-ACH** — Application Configuration Hardening (sanitize plugin responses; restrict TFTP)
- **D3-OAM** — Operating System Administrative Management (audit SUID binaries; restrict sudo)
- **D3-NTF** — Network Traffic Filtering (block TFTP from workstation segments)

---

## Final Thoughts

Enubox: Mattermost is a masterclass in credential chaining. Each service hands you the key to the next one, and the binary RE step at the end is a great introduction to Ghidra for players who have never reverse-engineered anything. The lesson is real: collaboration platforms, messaging tools, and their plugin ecosystems are increasingly high-value attack surfaces in enterprise environments. APT41 and FIN7 have both targeted similar misconfigurations in real-world intrusions. Legit machine, fr fr.

Thanks guys!! (❍ᴥ❍ʋ)
