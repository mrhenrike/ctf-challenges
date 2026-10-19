# Maq127: Tudo Esta na Memoria

Writeup for the **Tudo Esta na Memoria** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Easy
> **Difficulty:** Easy
> **Points:** 127

---

## Overview

"Everything is in memory." This challenge provides a memory dump that must be analyzed to extract the flag. Classic memory forensics using Volatility.

## Reconnaissance

Identify the memory image profile:

```bash
volatility -f memory.raw imageinfo
```

Or with Volatility 3:

```bash
vol -f memory.raw windows.info
```

Note the suggested profile (e.g., Win7SP1x64) for further analysis.

## Analysis

**List running processes:**

```bash
volatility -f memory.raw --profile=[PROFILE] pslist
volatility -f memory.raw --profile=[PROFILE] pstree
```

**Search for interesting strings:**

```bash
strings memory.raw | grep -i "flag\|password\|secret"
```

**Dump process memory for suspicious processes:**

```bash
volatility -f memory.raw --profile=[PROFILE] memdump -p [PID] -D dump/
```

**Check clipboard, notepad, or command history:**

```bash
volatility -f memory.raw --profile=[PROFILE] clipboard
volatility -f memory.raw --profile=[PROFILE] cmdscan
volatility -f memory.raw --profile=[PROFILE] consoles
```

**Extract files from memory:**

```bash
volatility -f memory.raw --profile=[PROFILE] filescan | grep -i "flag\|txt\|secret"
volatility -f memory.raw --profile=[PROFILE] dumpfiles -Q [OFFSET] -D dump/
```

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| OS Credential Dumping: LSASS Memory | T1003.001 |
| Unsecured Credentials: Credentials in Files | T1552.001 |

### CWE

- **CWE-316:** Cleartext Storage of Sensitive Information in Memory
- **CWE-312:** Cleartext Storage of Sensitive Information

### MITRE D3FEND

- **D3-MA:** Memory Analysis

---

RAM is the ultimate tell-all witness: volatile, ephemeral, yet faithfully recording every secret a running system holds. The trick is knowing which page to read before the power fades.

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
