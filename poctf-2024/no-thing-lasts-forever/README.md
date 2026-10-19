# No Thing Lasts Forever

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2024 |
| **Category** | Unknown |
| **Difficulty** | Unknown |
| **Points** | N/A |
| **Flag** | `poctf{uwsp_7h3_hum4n_c0nd1710n}` |
| **Status** | Solved |

---

## Challenge Overview

A classic ZIP password cracking challenge. The description ironically comments on how this is a "normal" crack challenge after weeks of oddball cracking puzzles. The password is in the `rockyou.txt` wordlist and cracks in seconds.

## Objective

Extract the password hash from the ZIP file and crack it using a standard wordlist.

## Methodology

### Step 1: Extract the Hash

```bash
zip2john Crack100-1.zip > hash.txt
```

### Step 2: Crack with rockyou.txt

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt hash.txt
```

The password was cracked in under 5 seconds: `lol12345`

### Step 3: Extract the Flag

```bash
unzip -P 'lol12345' Crack100-1.zip
cat flag.txt
```

```
Flag: poctf{uwsp_7h3_hum4n_c0nd1710n}
```

## Lessons Learned

| # | Lesson | Details |
|---|--------|---------|
| 1 | Standard tools first | Always try `zip2john` + `rockyou.txt` before more complex approaches |
| 2 | Weak passwords are common | Even in CTFs, some challenges use intentionally weak passwords |
| 3 | Read the description | The challenge tells you outright it is a standard wordlist crack |

## MITRE ATT&CK Mapping

| Tactic | Technique | ID | Details |
|--------|-----------|-----|---------|
| Credential Access | Brute Force: Password Cracking | T1110.002 | Cracking ZIP password with john + rockyou |
| Collection | Archive Collected Data: Archive via Utility | T1560.001 | Password-protected ZIP archive |

## Remediation

### Technical Fixes

- Never use passwords from common wordlists (rockyou, etc.)
- Use strong, randomly generated passphrases for archive encryption

### MITRE D3FEND

| Technique | ID | How it applies |
|-----------|-----|----------------|
| Credential Hardening | D3-CH | Require strong, non-dictionary passwords |

### NIST CSF 2.0

| Function | Category | Relevance |
|----------|----------|-----------|
| Protect (PR) | Identity Management, Authentication and Access Control (PR.AA) | Enforce password complexity requirements |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---------|-------------|
| IA-5 | Authenticator Management: prohibit common wordlist passwords |

### CWE

| CWE ID | Name | Relevance |
|--------|------|-----------|
| CWE-521 | Weak Password Requirements | Password `lol12345` found in common wordlist |

## References

- [UWSP Pointer Overflow CTF 2024](https://pointeroverflowctf.com)
- Based on solve approach from [shivang1209-dot](https://github.com/shivang1209-dot/CTF-Writeup)

---

Thanks guys!! (❍ᴥ❍ʋ)

Sometimes the simplest approach is the correct one. Keep your wordlists updated and your tools sharp.

[![Instagram](https://img.shields.io/badge/Instagram-%23E4405F.svg?style=for-the-badge&logo=Instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/linkedin-%230077B5.svg?style=for-the-badge&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/X-%23000000.svg?style=for-the-badge&logo=X&logoColor=white)](https://x.com/mrhenrike)
