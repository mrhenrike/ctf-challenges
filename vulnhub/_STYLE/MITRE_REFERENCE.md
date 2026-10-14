# MITRE ATT&CK Quick Reference for CTF/VulnHub Writeups

> Use this as a lookup when mapping TTPs to writeups.
> Always check https://attack.mitre.org/ for the most current IDs.

---

## Most Common CTF Techniques Mapped

### Reconnaissance (TA0043)
| Technique | ID | Notes |
|-----------|-----|-------|
| Active Scanning: Scanning IP Blocks | T1595.001 | nmap host discovery |
| Active Scanning: Vulnerability Scanning | T1595.002 | nmap -A, nikto |
| Search Open Websites/Domains | T1593 | Google dorking, Shodan |

### Initial Access (TA0001)
| Technique | ID | Notes |
|-----------|-----|-------|
| Exploit Public-Facing Application | T1190 | Web app exploits (SQLi, RCE, etc.) |
| Valid Accounts | T1078 | Credential reuse, brute-force |
| Phishing | T1566 | (less common in VulnHub) |
| External Remote Services | T1133 | VPN, RDP, SSH with weak creds |

### Execution (TA0002)
| Technique | ID | Notes |
|-----------|-----|-------|
| Command and Scripting Interpreter: Unix Shell | T1059.004 | bash/sh reverse shells |
| Command and Scripting Interpreter: Python | T1059.006 | python -c "import pty..." |
| Exploitation for Client Execution | T1203 | Metasploit payloads |
| Server-Side Template Injection | T1190 | SSTI via Jinja2, Twig |

### Persistence (TA0003)
| Technique | ID | Notes |
|-----------|-----|-------|
| Create Account | T1136 | Adding users in /etc/passwd |
| Scheduled Task/Job: Cron | T1053.003 | Writable cron scripts |
| SSH Authorized Keys | T1098.004 | Adding attacker pub key |
| Web Shell | T1505.003 | PHP/JSP webshells |

### Privilege Escalation (TA0004)
| Technique | ID | Notes |
|-----------|-----|-------|
| Abuse Elevation Control Mechanism: Sudo | T1548.003 | sudo -l exploitation |
| Setuid and Setgid | T1548.001 | SUID binary abuse |
| Exploitation for Privilege Escalation | T1068 | Kernel exploits, DirtyCOW |
| Path Interception by PATH Environment Variable | T1574.007 | PATH hijacking |
| Sudo and Sudo Caching | T1548.003 | GTFOBins sudo escapes |
| Escape to Host | T1611 | Docker/LXD escape |

### Defense Evasion (TA0005)
| Technique | ID | Notes |
|-----------|-----|-------|
| Masquerading | T1036 | Renaming malicious binaries |
| File and Directory Permissions Modification | T1222 | chmod +s |
| Impair Defenses: Disable or Modify Tools | T1562.001 | Disabling firewall, AV |

### Credential Access (TA0006)
| Technique | ID | Notes |
|-----------|-----|-------|
| Brute Force: Password Spraying | T1110.003 | Hydra, Medusa |
| Brute Force: Credential Stuffing | T1110.004 | Reused passwords |
| OS Credential Dumping | T1003 | /etc/shadow, NTDS.dit |
| Unsecured Credentials: Credentials in Files | T1552.001 | wp-config.php, .env |
| Network Sniffing | T1040 | PCAP analysis |

### Discovery (TA0007)
| Technique | ID | Notes |
|-----------|-----|-------|
| Network Service Discovery | T1046 | Port scanning |
| File and Directory Discovery | T1083 | gobuster, dirb, feroxbuster |
| Account Discovery | T1087 | WPScan user enum, LDAP |
| System Information Discovery | T1082 | uname, /etc/os-release |
| Software Discovery | T1518 | whatweb, wappalyzer |
| Permission Groups Discovery | T1069 | id, groups, /etc/group |

### Lateral Movement (TA0008)
| Technique | ID | Notes |
|-----------|-----|-------|
| Remote Services: SSH | T1021.004 | SSH with found credentials |
| Use Alternate Authentication Material: SSH Keys | T1550.004 | SSH key injection |
| Internal Spearphishing | T1534 | (less common) |

### Collection (TA0009)
| Technique | ID | Notes |
|-----------|-----|-------|
| Data from Local System | T1005 | Reading flag files |
| Data from Network Shared Drive | T1039 | SMB shares |

---

## Common Web Vulnerabilities Mapped

| Vulnerability | MITRE ID | CWE | OWASP |
|--------------|----------|-----|-------|
| SQL Injection | T1190 | CWE-89 | A03:2021 |
| Local File Inclusion (LFI) | T1190 | CWE-98 | A01:2021 |
| Remote File Inclusion (RFI) | T1190 | CWE-98 | A01:2021 |
| Command Injection | T1059.004 | CWE-78 | A03:2021 |
| SSTI (Server-Side Template Injection) | T1190 | CWE-94 | A03:2021 |
| XXE | T1190 | CWE-611 | A05:2021 |
| SSRF | T1190 | CWE-918 | A10:2021 |
| Broken Access Control | T1078 | CWE-284 | A01:2021 |
| Insecure Deserialization | T1190 | CWE-502 | A08:2021 |
| Path Traversal | T1190 | CWE-22 | A01:2021 |
| XSS | T1059.007 | CWE-79 | A03:2021 |

---

## MITRE D3FEND Common Countermeasures

| Attack Technique | D3FEND Countermeasure | D3-ID |
|-----------------|----------------------|-------|
| Brute Force (T1110) | Credential Hardening: Multi-factor Auth | D3-MFA |
| Web App Exploit (T1190) | Application Hardening: Input Validation | D3-IVA |
| SUID Abuse (T1548) | Execution Isolation: OS Process Sandboxing | D3-OPS |
| Cron Persistence (T1053) | Process Analysis: Scheduled Job Analysis | D3-SJA |
| Path Hijacking (T1574) | File Analysis: Dynamic Analysis | D3-DA |
| Credential in Files (T1552) | Credential Hardening: Credential Transmission Scoping | D3-CTS |

---

## NIST SP 800-53 Rev. 5 Quick Reference

| Finding Type | Relevant Controls |
|-------------|------------------|
| Weak/default credentials | IA-5, IA-8 |
| Least privilege violation | AC-6 |
| Unpatched software | SI-2, CM-8 |
| Missing input validation | SI-10 |
| Insecure file permissions | AC-3, AU-9 |
| Sensitive data exposure | SC-28, AC-4 |
| Missing logging | AU-2, AU-3 |
| Writable cron/scripts | CM-7, AC-6 |
| SUID misconfiguration | CM-7, CM-6 |

---

## C2M2 Domain Quick Reference

| CTF Finding | C2M2 Domain | Practice | Target MIL |
|------------|-------------|----------|-----------|
| No asset inventory | ASSET | Asset Inventory | MIL-1 |
| Unpatched services | ASSET | Asset Management | MIL-2 |
| Weak credentials | ACCESS | Identity Management | MIL-2 |
| No MFA | ACCESS | Access Management | MIL-2 |
| No monitoring | SITUATIONAL AWARENESS | Logging & Monitoring | MIL-2 |
| No incident response | EVENT | Incident Response | MIL-2 |
| Insecure configuration | TECHNOLOGY | Configuration Management | MIL-2 |

---

## CISA KEV — Known Exploited Vulnerabilities (Common in VulnHub)

| CVE | Product | Notes |
|-----|---------|-------|
| CVE-2003-0201 | Samba | trans2open (Kioptrix 1) |
| CVE-2014-6271 | Bash | Shellshock (SickOs, Tr0ll) |
| CVE-2016-5195 | Linux Kernel | DirtyCOW |
| CVE-2016-10033 | PHPMailer | RCE via email |
| CVE-2019-19634 | sar2HTML | RCE |
| CVE-2019-10149 | Exim | RCE (DC-8) |
| CVE-2019-15107 | Webmin | RCE |
| CVE-2018-7600 | Drupal | drupalgeddon2 |

---

## Real-World Incident References (for writeup notes)

| Technique | Real Incident | Reference |
|-----------|--------------|-----------|
| WordPress brute-force | Panama Papers breach (2016) | Mossack Fonseca WP vuln |
| Shellshock | Multiple 2014 attacks | US-CERT Alert TA14-268A |
| SQLi | Yahoo! breach (2012) | D33Ds Company dump |
| DirtyCOW | Widespread Linux privilege escalation 2016 | CVE-2016-5195 |
| Credential stuffing | Spotify, Netflix (2019-2020) | Multiple breach reports |
| Default credentials | Mirai botnet (2016) | IoT devices, Dyn DDoS |
| Exposed .git repos | Multiple companies (ongoing) | GitGuardian reports |
| Path hijacking | APT campaigns (ongoing) | MITRE ATT&CK case studies |
| SUID abuse | Linux server compromises (ongoing) | Multiple DFIR reports |
| sudo misconfiguration | Common in enterprise audits | CIS Benchmark violations |

---

> Reference: https://attack.mitre.org/
> D3FEND: https://d3fend.mitre.org/
> NIST CSF: https://www.nist.gov/cyberframework
> NIST 800-53: https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final
> CISA KEV: https://www.cisa.gov/known-exploited-vulnerabilities-catalog
> C2M2: https://www.energy.gov/ceser/cybersecurity-capability-maturity-model-c2m2
> CIS Controls: https://www.cisecurity.org/controls
