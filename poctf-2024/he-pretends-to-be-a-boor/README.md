# He Pretends To Be A Boor

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2024 |
| **Challenge** | He Pretends To Be A Boor |
| **Category** | Steganography |
| **Difficulty** | Expert |
| **Points** | 400 |
| **Status** | Solved |

---

## Challenge Overview

A JPEG image contains the flag embedded in its **quantization tables** (the metadata region used by JPEG's Discrete Cosine Transform compression algorithm). Standard stego tools fail to detect it because the data is stored in the image's structural metadata rather than pixel data.

**File provided:** `Stego400.jpg`

**Note:** The flag is fragile. The image must match its original checksum for recovery.

---

## Objective

Analyze the JPEG file structure, identify data hidden in the quantization tables, and decode the ASCII values to recover the flag.

---

## Methodology

### Step 1: Initial Reconnaissance

Standard tools yield nothing:

```bash
file Stego400.jpg
# JPEG image data, JFIF standard 1.01, baseline, 1024x1024

exiftool Stego400.jpg
# No unusual metadata

stegseek Stego400.jpg
# No valid passphrase found

binwalk Stego400.jpg
# Only JFIF data
```

### Step 2: Hex Dump Analysis

Examining the hex dump reveals interesting ASCII-like values just after the JFIF header, enclosed between `ffdb` markers:

```bash
xxd Stego400.jpg | head -20
```

The `ffdb` markers define **JPEG Quantization Tables**: metadata that controls DCT compression levels. The values between these markers look like they could be ASCII character codes.

### Step 3: Extract Quantization Table Values

Using Python with PIL to extract the quantization tables:

```python
from PIL import Image

img = Image.open('Stego400.jpg')
quant_tables = img.quantization
```

This extracts two quantization tables (Table 0 and Table 1). Table 0 contains the flag data.

### Step 4: Convert Decimal to ASCII

The [decode_quantization.py](scripts/decode_quantization.py) script extracts Table 0 values and converts printable decimal values to ASCII:

```python
for value in first_table:
    if chr(value) in string.printable and not chr(value).isspace():
        result.append(chr(value))
```

Alternatively, copy the decimal values from the table and use an online converter (e.g., Rapid Tables ASCII converter).

### Step 5: Recover the Flag

The initial extraction may produce a jumbled string: `pos_pct1p057f{h_0nn3uwr0}_3s`. This is because the quantization table values are stored in zigzag order. Reading them in the correct order reveals the flag.

---

## Flag

```
poctf{uwsp_7h3r3_15_n0_sp00n}
```

---

## Lessons Learned

| # | Insight |
|---|---------|
| 1 | JPEG quantization tables are an unconventional but effective hiding spot for data |
| 2 | Standard stego tools focus on pixel data and may miss structural metadata hiding |
| 3 | Understanding file format internals (JPEG markers like `ffdb`) is crucial for advanced stego |
| 4 | The flag's fragility warning hints at metadata-based hiding (modifying pixels would break it) |
| 5 | The Matrix reference ("there is no spoon") matches the theme of seeing beyond appearances |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | Description |
|--------|-----------|-------------|
| Defense Evasion | T1027.003 - Obfuscated Files: Steganography | Data hidden in JPEG quantization table metadata |
| Defense Evasion | T1036 - Masquerading | File appears as a normal JPEG with valid image data |

---

## Remediation

### Technical Fixes

- Implement JPEG structure validation that checks quantization table values against expected ranges for real images.
- Re-encode JPEG files with fresh quantization tables to strip metadata-based payloads.
- Validate JPEG files by comparing quantization table entropy against known profiles.

### MITRE D3FEND

| ID | Technique |
|----|-----------|
| D3-SFA | Static File Analysis: JPEG structure inspection |
| D3-FCR | File Content Rules: anomalous quantization table detection |

### NIST CSF 2.0

| Function | Category | Action |
|----------|----------|--------|
| Detect | DE.CM | Inspect JPEG metadata structures for anomalous values |
| Protect | PR.DS | Re-encode images to neutralize metadata-based steganography |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---------|-------------|
| SI-3 | Malicious Code Protection |
| SI-4 | Information System Monitoring |

### C2M2

| Practice | Description |
|----------|-------------|
| DETECT | Extend steganalysis to cover file format structural metadata |

### CWE

| ID | Description |
|----|-------------|
| CWE-506 | Embedded Malicious Code |
| CWE-116 | Improper Encoding or Escaping of Output |

---

## References

- [shivang1209-dot POCTF 2024 Writeups](https://github.com/shivang1209-dot/shivang1209-dot) (original reference)
- [JPEG File Format Structure](https://en.wikipedia.org/wiki/JPEG#Syntax_and_structure)
- [Pointer Overflow CTF](https://pointeroverflowctf.com/)

---

Thanks guys!! (❍ᴥ❍ʋ)

Nao existe colher, e tambem nao existe limite para onde esconder dados em um JPEG. Tabelas de quantizacao: quem diria que os metadados de compressao guardariam a flag!

[![Instagram](https://img.shields.io/badge/Instagram-%23E4405F.svg?style=for-the-badge&logo=Instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/linkedin-%230077B5.svg?style=for-the-badge&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/X-%23000000.svg?style=for-the-badge&logo=X&logoColor=white)](https://x.com/mrhenrike)
