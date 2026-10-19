# Constructed Languages

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2024 |
| **Challenge** | Constructed Languages |
| **Category** | Reverse Engineering |
| **Difficulty** | Medium |
| **Points** | 200 |
| **Status** | Solved |

---

## Challenge Overview

A binary contains the flag encoded through a pairwise byte swap transformation. Reversing the swap operation on the embedded data recovers the original flag.

---

## Objective

Analyze the binary, identify the encoding transformation, and reverse it to recover the flag.

---

## Methodology

### Step 1: Static Analysis

Loading the binary in Ghidra reveals a data section containing an encoded string and a transformation function that performs pairwise byte swaps.

### Step 2: Understand the Transformation

The encoding function swaps adjacent pairs of bytes:

```
Original:  [A][B][C][D][E][F]...
Encoded:   [B][A][D][C][F][E]...
```

Each pair of consecutive bytes is transposed. The transformation is its own inverse: applying it twice returns the original data.

### Step 3: Extract and Reverse

Extracting the encoded data from the binary and applying the same pairwise swap:

```python
encoded = extract_data_from_binary()
decoded = bytearray()
for i in range(0, len(encoded), 2):
    decoded.append(encoded[i+1])
    decoded.append(encoded[i])
print(decoded.decode())
```

### Step 4: Recover the Flag

The decoded output is the flag in `poctf{uwsp_...}` format.

---

## Lessons Learned

| # | Insight |
|---|---------|
| 1 | Involutory transformations (self-inverse) are common in simple obfuscation |
| 2 | Pairwise byte swapping is a minimal encoding that adds no real security |
| 3 | Static analysis tools quickly reveal the transformation logic in compiled code |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | Description |
|--------|-----------|-------------|
| Defense Evasion | T1027 - Obfuscated Files or Information | Data encoded with byte-level transposition |
| Defense Evasion | T1140 - Deobfuscate/Decode Files or Information | Reversing the transformation to recover plaintext |

---

## Remediation

### Technical Fixes

- Byte transposition is trivially reversible; use authenticated encryption for actual data protection.
- If obfuscation is needed for anti-reverse-engineering, combine multiple techniques with integrity checks.

### MITRE D3FEND

| ID | Technique |
|----|-----------|
| D3-DA | Dynamic Analysis: trace execution to identify encoding routines |

### NIST CSF 2.0

| Function | Category | Action |
|----------|----------|--------|
| Protect | PR.DS | Apply strong encryption rather than simple byte manipulation |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---------|-------------|
| SC-13 | Cryptographic Protection: use approved cryptographic algorithms |

### C2M2

| Practice | Description |
|----------|-------------|
| PROTECT | Protect embedded data with encryption, not transposition |

### CWE

| ID | Description |
|----|-------------|
| CWE-311 | Missing Encryption of Sensitive Data |
| CWE-327 | Use of a Broken or Risky Cryptographic Algorithm |

---

## References

- [yocchin POCTF 2024 Writeup](https://yocchin.hatenablog.com/entry/2025/01/23/140330) (original reference)
- [Pointer Overflow CTF](https://pointeroverflowctf.com/)

---

Thanks guys!! (❍ᴥ❍ʋ)

Like learning a constructed language, reversing a binary is about understanding the grammar of the machine. Flag decoded!

[![Instagram](https://img.shields.io/badge/Instagram-%23E4405F.svg?style=for-the-badge&logo=Instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/linkedin-%230077B5.svg?style=for-the-badge&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/X-%23000000.svg?style=for-the-badge&logo=X&logoColor=white)](https://x.com/mrhenrike)
