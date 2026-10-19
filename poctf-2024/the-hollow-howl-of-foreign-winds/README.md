# The Hollow Howl of Foreign Winds

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

The challenge provides a bar chart image. Each bar encodes a letter position that, when read in sequence, spells out the flag.

---

## Objective

Read the bar chart values, map them to letter positions, and assemble the flag.

---

## Methodology

### Step 1: Analyze the Bar Chart

The chart displays a series of bars with varying heights. Each bar represents one character of the flag.

### Step 2: Extract Values

Carefully measuring each bar's height against the Y-axis yields a series of numeric values. These values correspond to positions in the alphabet (1=A, 2=B, ... 26=Z) or to specific character codes.

### Step 3: Map to Characters

Converting each value to its corresponding letter:

| Bar | Value | Character |
|-----|-------|-----------|
| 1 | ... | ... |
| 2 | ... | ... |
| ... | ... | ... |

### Step 4: Assemble the Flag

Reading the characters in order and formatting as `poctf{uwsp_...}` produces the flag.

---

## Lessons Learned

| # | Insight |
|---|---------|
| 1 | Data visualization can serve as an encoding channel for hidden messages |
| 2 | Precise measurement of chart values is critical for accurate decoding |
| 3 | Bar chart steganography is a creative CTF technique that tests attention to detail |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | Description |
|--------|-----------|-------------|
| Defense Evasion | T1027.003 - Steganography | Data concealed in a visual representation |
| Exfiltration | T1048 - Exfiltration Over Alternative Protocol | Using non-standard channels to transmit data |

---

## Remediation

### Technical Fixes

- Chart-based encoding is trivially decoded once the scheme is identified.
- For legitimate covert communication, use end-to-end encrypted channels rather than visual encoding.

### MITRE D3FEND

| ID | Technique |
|----|-----------|
| D3-SDA | Static Document Analysis: inspect visual files for encoded data |

### NIST CSF 2.0

| Function | Category | Action |
|----------|----------|--------|
| Detect | DE.CM | Monitor data flows for unusual encoding in document attachments |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---------|-------------|
| SI-4 | Information System Monitoring: detect covert data channels |

### C2M2

| Practice | Description |
|----------|-------------|
| DETECT | Analyze outbound documents for potential covert data exfiltration |

### CWE

| ID | Description |
|----|-------------|
| CWE-311 | Missing Encryption of Sensitive Data |

---

## References

- [yocchin POCTF 2024 Writeup](https://yocchin.hatenablog.com/entry/2025/01/23/140330) (original reference)
- [Pointer Overflow CTF](https://pointeroverflowctf.com/)

---

Thanks guys!! (❍ᴥ❍ʋ)

Foreign winds carry whispers of data, and every bar tells a story. Listen carefully, and the flag reveals itself!

[![Instagram](https://img.shields.io/badge/Instagram-%23E4405F.svg?style=for-the-badge&logo=Instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/linkedin-%230077B5.svg?style=for-the-badge&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/X-%23000000.svg?style=for-the-badge&logo=X&logoColor=white)](https://x.com/mrhenrike)
