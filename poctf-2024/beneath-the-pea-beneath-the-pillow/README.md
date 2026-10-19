# Beneath the Pea Beneath the Pillow

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

Similar to other chart-based challenges, this one provides a bar chart where each bar height maps to an alphabet index. The challenge requires precise measurement and careful decoding.

---

## Objective

Extract numeric values from bar heights, convert them to alphabet characters, and recover the flag.

---

## Methodology

### Step 1: Inspect the Bar Chart

The challenge image shows a series of vertical bars. The Y-axis contains a numeric scale that must be read carefully to determine each bar's value.

### Step 2: Map Heights to Indices

Each bar height corresponds to a position in the English alphabet:

- Height 1 = A
- Height 2 = B
- Height 26 = Z

### Step 3: Read the Sequence

Processing each bar from left to right and converting its height to the corresponding letter yields the flag content.

### Step 4: Construct the Flag

Combine the letters into the `poctf{uwsp_...}` format to produce the flag.

---

## Lessons Learned

| # | Insight |
|---|---------|
| 1 | Pixel-level precision matters when reading chart values from images |
| 2 | Image zoom and grid overlay tools help minimize measurement errors |
| 3 | Cross-referencing extracted text against known flag format validates the decode |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | Description |
|--------|-----------|-------------|
| Defense Evasion | T1027.003 - Steganography | Encoding information within graphical elements |
| Collection | T1113 - Screen Capture | Analyzing visual data to extract hidden information |

---

## Remediation

### Technical Fixes

- Visual encoding in charts is easily reversed with image analysis tools.
- Do not use visual representations as a data protection mechanism.

### MITRE D3FEND

| ID | Technique |
|----|-----------|
| D3-SDA | Static Document Analysis: analyze visual media for encoded content |

### NIST CSF 2.0

| Function | Category | Action |
|----------|----------|--------|
| Detect | DE.AE | Establish baselines for normal document formats to identify anomalies |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---------|-------------|
| SC-28 | Protection of Information at Rest: use encryption, not visual encoding |

### C2M2

| Practice | Description |
|----------|-------------|
| DETECT | Monitor for covert channels within document attachments |

### CWE

| ID | Description |
|----|-------------|
| CWE-311 | Missing Encryption of Sensitive Data |
| CWE-656 | Reliance on Security Through Obscurity |

---

## References

- [yocchin POCTF 2024 Writeup](https://yocchin.hatenablog.com/entry/2025/01/23/140330) (original reference)
- [Pointer Overflow CTF](https://pointeroverflowctf.com/)

---

Thanks guys!! (❍ᴥ❍ʋ)

Like the princess and the pea, sensitivity to small details makes all the difference. Another flag secured!

[![Instagram](https://img.shields.io/badge/Instagram-%23E4405F.svg?style=for-the-badge&logo=Instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/linkedin-%230077B5.svg?style=for-the-badge&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/X-%23000000.svg?style=for-the-badge&logo=X&logoColor=white)](https://x.com/mrhenrike)
