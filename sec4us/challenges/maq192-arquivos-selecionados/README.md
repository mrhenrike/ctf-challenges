# Maq192: Arquivos Selecionados

> **Platform:** SEC4US CTF Lab | **Category:** Hacking: Easy | **Points:** Dynamic

## Overview

A challenge requiring careful analysis of specific files to extract hidden information and the flag.

---

## Approach

**Technique:** File Analysis and Extraction

### Reconnaissance

```bash
nmap -sV -sC -p- <TARGET_IP> -oN nmap_full.txt
```

### Exploitation

1. **Service enumeration:** Identify accessible file services (FTP, SMB, HTTP)
2. **File discovery:** Download or access the target files through the available service
3. **File analysis:** Examine file metadata, hidden content, or embedded data
4. **Flag extraction:** Extract the flag from the analyzed files

### Tools Used

nmap, file, strings, binwalk, exiftool

---

## Security Frameworks

### MITRE ATT&CK

| Technique | Description |
|-----------|-------------|
| T1083 | File and Directory Discovery |

### CWE

| ID | Description |
|----|-------------|
| CWE-200 | Exposure of Sensitive Information |

---

## Author

**Andre Henrike** (@mrhenrike)

Every file has a story. Your job is to read between the bytes. Thanks guys!! (❍ᴥ❍ʋ)

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

*For educational purposes only. Do not use any technique shown here against systems you do not own or have explicit permission to test.*
