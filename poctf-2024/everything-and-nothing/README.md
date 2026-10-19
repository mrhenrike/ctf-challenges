# Everything and Nothing

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2024 |
| **Challenge** | Everything and Nothing |
| **Category** | Steganography |
| **Difficulty** | Hard |
| **Points** | 300 |
| **Status** | Solved |

---

## Challenge Overview

A grayscale PNG image (1024x1024, RGBA) contains the flag hidden in the least significant bit of the red channel. Despite the RGBA color space, the image appears grayscale, adding a layer of misdirection.

**File provided:** `Stego300-2.png`

---

## Objective

Extract the LSB-encoded flag from the red channel of the image.

---

## Methodology

### Step 1: File Inspection

```bash
file Stego300-2.png
```

```
Stego300-2.png: PNG image data, 1024 x 1024, 8-bit/color RGBA, non-interlaced
```

The image has an alpha channel (RGBA), which is unusual for a stego challenge. The metadata from exiftool shows no hidden comments or unusual tags.

### Step 2: Steganography Analysis

```bash
zsteg Stego300-2.png
```

Key output:

```
b1,r,lsb,xy         .. text: "poctf{uwsp_n07_4ll_7h053_wh0_w4nd3r}"
```

The flag is embedded in **bit 1 of the red channel only** (`b1,r,lsb,xy`), not across all RGB channels as in the earlier challenges. This is a subtler embedding that requires checking individual channels.

### Step 3: Verification

The flag was confirmed as valid. The title "Everything and Nothing" references the Tolkien quote embedded in the flag: "Not all those who wander are lost."

---

## Flag

```
poctf{uwsp_n07_4ll_7h053_wh0_w4nd3r}
```

---

## Lessons Learned

| # | Insight |
|---|---------|
| 1 | LSB data can be in a single channel (R only), not always spread across RGB |
| 2 | RGBA images with alpha channels add misdirection; always check each channel independently |
| 3 | zsteg's comprehensive analysis checks multiple channel combinations automatically |
| 4 | The difficulty increase comes from the data being in a single channel rather than RGB combined |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | Description |
|--------|-----------|-------------|
| Defense Evasion | T1027.003 - Obfuscated Files: Steganography | Single-channel LSB steganography |
| Exfiltration | T1048 - Exfiltration Over Alternative Protocol | Using grayscale images as covert data carriers |

---

## Remediation

### Technical Fixes

- Steganalysis must inspect individual color channels, not just combined RGB.
- Image re-encoding (e.g., lossy conversion to JPEG and back) destroys single-channel LSB payloads.
- Convert RGBA images to RGB when alpha is unnecessary, reducing the hiding capacity.

### MITRE D3FEND

| ID | Technique |
|----|-----------|
| D3-SFA | Static File Analysis: per-channel steganalysis |
| D3-FCOA | File Content Analysis |

### NIST CSF 2.0

| Function | Category | Action |
|----------|----------|--------|
| Detect | DE.CM | Deploy per-channel steganalysis tools |
| Protect | PR.DS | Normalize image formats to reduce steganographic capacity |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---------|-------------|
| SI-3 | Malicious Code Protection |
| SI-4 | Information System Monitoring |

### C2M2

| Practice | Description |
|----------|-------------|
| DETECT | Enhance steganalysis with per-channel analysis capabilities |

### CWE

| ID | Description |
|----|-------------|
| CWE-506 | Embedded Malicious Code |

---

## References

- [shivang1209-dot POCTF 2024 Writeups](https://github.com/shivang1209-dot/shivang1209-dot) (original reference)
- [zsteg](https://github.com/zed-0xff/zsteg)
- [Pointer Overflow CTF](https://pointeroverflowctf.com/)

---

Thanks guys!! (❍ᴥ❍ʋ)

Nem todos que vagam estao perdidos, mas a flag estava la, escondida em um unico canal de cor. Tolkien ficaria orgulhoso!

[![Instagram](https://img.shields.io/badge/Instagram-%23E4405F.svg?style=for-the-badge&logo=Instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/linkedin-%230077B5.svg?style=for-the-badge&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/X-%23000000.svg?style=for-the-badge&logo=X&logoColor=white)](https://x.com/mrhenrike)
