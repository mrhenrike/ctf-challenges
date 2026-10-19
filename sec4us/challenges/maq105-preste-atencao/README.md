# Maq105: Preste Muita Atencao

Writeup for the **Preste Muita Atencao** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Easy
> **Difficulty:** Easy
> **Points:** 105

---

## Overview

"Pay close attention" is the hint. This challenge rewards careful service enumeration. A flag hides behind a detail that careless scanning would miss.

## Reconnaissance

Thorough enumeration is critical. Run a full TCP and UDP scan:

```bash
nmap -sV -sC -p- [TARGET_IP] -oN nmap_tcp.txt
nmap -sU --top-ports 100 [TARGET_IP] -oN nmap_udp.txt
```

Pay attention to unusual ports, non-standard service versions, or banners that contain encoded information. Check HTTP headers carefully:

```bash
curl -v http://[TARGET_IP]/
```

Enumerate web directories if HTTP is present:

```bash
gobuster dir -u http://[TARGET_IP] -w /usr/share/wordlists/dirb/common.txt -o dirs.txt
```

## Exploitation

The flag often hides in plain sight: a comment in an HTML source, a non-standard HTTP header, a service banner, or a file in an unexpected directory. Enumerate every detail:

```bash
nikto -h http://[TARGET_IP]
```

Check for SNMP on UDP 161, uncommon web paths, or credentials embedded in service configurations.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Network Service Discovery | T1046 |
| Software Discovery | T1518 |
| File and Directory Discovery | T1083 |

### CWE

- **CWE-200:** Exposure of Sensitive Information to an Unauthorized Actor
- **CWE-540:** Inclusion of Sensitive Information in Source Code

---

The quietest services whisper the loudest secrets. In security, the difference between seeing and overlooking is simply knowing where to look.

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
