# I Never Knew Glory

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2024 |
| **Category** | Unknown |
| **Difficulty** | Unknown |
| **Points** | N/A |
| **Flag** | `poctf{dynamic}` |
| **Status** | Solved |

---

## Challenge Overview

The challenge provides a quote from a theatrical play and asks for the flag. The hint suggests converting the answer into a "digital dialect," pointing toward leet speak (l33t) transformation.

---

## Objective

Identify the source phrase from the play text, then apply leet speak encoding to produce the flag.

---

## Methodology

### Step 1: Identify the Source Text

The challenge description references a well-known theatrical work. Searching online for the exact quote leads to the original play and the specific passage being referenced.

### Step 2: Extract the Key Phrase

The relevant phrase from the play forms the core of the flag. The challenge instructions indicate that the answer should be wrapped in the standard `poctf{uwsp_...}` format.

### Step 3: Apply Leet Speak Transformation

Converting the phrase to leet speak following standard substitutions:

| Letter | Leet |
|--------|------|
| a | 4 |
| e | 3 |
| i | 1 |
| o | 0 |
| s | 5 |
| t | 7 |

The transformed phrase, wrapped in the flag format, produces the final answer.

---

## Lessons Learned

| # | Insight |
|---|---------|
| 1 | Misc challenges often require lateral thinking rather than technical exploitation |
| 2 | Leet speak substitution is a recurring CTF pattern for encoding readable text |
| 3 | Literary references in CTFs reward general knowledge and research skills |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | Description |
|--------|-----------|-------------|
| Defense Evasion | T1027 - Obfuscated Files or Information | Data encoded using character substitution |
| Collection | T1119 - Automated Collection | Extracting specific data from provided materials |

---

## Remediation

### Technical Fixes

- Leet speak is not an encryption method; it provides no meaningful obfuscation for sensitive data.
- Any encoding scheme that relies on simple character substitution is trivially reversible.

### MITRE D3FEND

| ID | Technique |
|----|-----------|
| D3-DA | Dynamic Analysis: inspect encoded content by applying known substitution patterns |

### NIST CSF 2.0

| Function | Category | Action |
|----------|----------|--------|
| Identify | ID.AM | Maintain awareness of data encoding schemes used in the environment |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---------|-------------|
| SC-28 | Protection of Information at Rest: do not rely on encoding as a security control |

### C2M2

| Practice | Description |
|----------|-------------|
| PROTECT | Distinguish between encoding (reversible) and encryption (key-dependent) |

### CWE

| ID | Description |
|----|-------------|
| CWE-311 | Missing Encryption of Sensitive Data |
| CWE-261 | Weak Encoding for Password |

---

## References

- [yocchin POCTF 2024 Writeup](https://yocchin.hatenablog.com/entry/2025/01/23/140330) (original reference)
- [Pointer Overflow CTF](https://pointeroverflowctf.com/)

---

Thanks guys!! (❍ᴥ❍ʋ)

The stage is set, the lines are memorized, and the flag is captured. On to the next act!

[![Instagram](https://img.shields.io/badge/Instagram-%23E4405F.svg?style=for-the-badge&logo=Instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/linkedin-%230077B5.svg?style=for-the-badge&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/X-%23000000.svg?style=for-the-badge&logo=X&logoColor=white)](https://x.com/mrhenrike)
