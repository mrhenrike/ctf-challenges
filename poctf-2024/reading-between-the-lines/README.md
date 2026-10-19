# Reading Between the Lines

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2024 |
| **Challenge** | Reading Between the Lines |
| **Category** | Steganography |
| **Difficulty** | Easy |
| **Points** | 100 |
| **Status** | Solved |

---

## Challenge Overview

A text file contains a personal memoir with invisible Unicode characters (Zero Width Space and Zero Width Non-Joiner) embedded between visible characters. These zero-width characters encode binary data that reveals the flag.

**File provided:** `Stego100-2.txt`

---

## Objective

Extract and decode the hidden zero-width Unicode characters to recover the flag.

---

## Methodology

### Step 1: Identify Hidden Characters

Opening the file in a hex-aware text editor reveals invisible characters between each visible character. A hex dump with `xxd` confirms two distinct patterns:

```bash
xxd Stego100-2.txt | head
```

```
00000000: 0d0a e280 8c4f e280 8b6e e280 8b63 e280  .....O...n...c..
00000010: 8b65 e280 8c20 e280 8c75 e280 8c70 e280  .e... ...u...p..
```

Two Unicode characters are interleaved:
- `e2808b` = Zero Width Space (ZWSP) -> binary `1`
- `e2808c` = Zero Width Non-Joiner (ZWNJ) -> binary `0`

### Step 2: Extract Binary Data

The [decode_zwsp.py](scripts/decode_zwsp.py) script scans the hex dump for these patterns and builds a binary string:

```python
zwsp_hex = 'e2808b'  # maps to 1
zwnj_hex = 'e2808c'  # maps to 0
```

### Step 3: Convert Binary to ASCII

Group the extracted bits into 8-bit chunks and convert each to its ASCII character:

```python
ascii_text = ''.join(chr(int(binary[i:i+8], 2)) for i in range(0, len(binary), 8))
```

---

## Flag

```
poctf{uwsp_b3w4r3_7h3_j4bb3rw0ck}
```

---

## Lessons Learned

| # | Insight |
|---|---------|
| 1 | Zero-width Unicode characters are invisible in standard editors but detectable via hex dump |
| 2 | ZWSP/ZWNJ steganography is a real-world technique used in document watermarking and tracking |
| 3 | Always examine text files at the byte level when steganography is suspected |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | Description |
|--------|-----------|-------------|
| Defense Evasion | T1027.010 - Obfuscated Files: Command Obfuscation | Hiding data in zero-width Unicode characters |
| Exfiltration | T1041 - Exfiltration Over C2 Channel | Covert data embedding in text documents |

---

## Remediation

### Technical Fixes

- Strip zero-width characters from text documents at ingress points (email gateways, upload forms).
- Implement content inspection rules that flag documents containing unusual Unicode control characters.
- Use Unicode normalization (NFC/NFKC) to sanitize text inputs.

### MITRE D3FEND

| ID | Technique |
|----|-----------|
| D3-FCOA | File Content Analysis: detect zero-width character anomalies |
| D3-DA | Data Analysis: inspect for steganographic content |

### NIST CSF 2.0

| Function | Category | Action |
|----------|----------|--------|
| Detect | DE.CM | Monitor for zero-width character injection in documents |
| Protect | PR.DS | Sanitize text inputs by stripping non-printable Unicode |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---------|-------------|
| SI-3 | Malicious Code Protection |
| SI-4 | Information System Monitoring |

### C2M2

| Practice | Description |
|----------|-------------|
| DETECT | Implement content inspection for steganographic markers |

### CWE

| ID | Description |
|----|-------------|
| CWE-116 | Improper Encoding or Escaping of Output |

---

## References

- [shivang1209-dot POCTF 2024 Writeups](https://github.com/shivang1209-dot/shivang1209-dot) (original reference)
- [Zero-Width Characters (Unicode.org)](https://unicode.org/charts/PDF/U200B.pdf)
- [Pointer Overflow CTF](https://pointeroverflowctf.com/)

---

Thanks guys!! (❍ᴥ❍ʋ)

Caracteres invisiveis, dados ocultos: a esteganografia Unicode e uma tecnica elegante e subestimada. Olhos atentos no hex dump!

[![Instagram](https://img.shields.io/badge/Instagram-%23E4405F.svg?style=for-the-badge&logo=Instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/linkedin-%230077B5.svg?style=for-the-badge&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/X-%23000000.svg?style=for-the-badge&logo=X&logoColor=white)](https://x.com/mrhenrike)
