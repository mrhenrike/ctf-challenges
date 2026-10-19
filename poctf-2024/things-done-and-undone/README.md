# Things Done and Undone

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2024 |
| **Category** | Unknown |
| **Difficulty** | Unknown |
| **Points** | N/A |
| **Flag** | `poctf{uwsp_70_b3_0r_n07_70_b3}` |
| **Status** | Solved |

---

## Challenge Overview

A PNG image contains the flag hidden in the least significant bits of the RGB channels. The challenge description hints at "unfinished business" and things left "undone," referencing how earlier stego challenges hinted at LSB but used different methods.

**File provided:** `Stego200-3.png` (1024x1024, 8-bit RGB)

---

## Objective

Extract the LSB-encoded flag from the PNG image.

---

## Methodology

### Step 1: File Verification

```bash
file Stego200-3.png
```

```
Stego200-3.png: PNG image data, 1024 x 1024, 8-bit/color RGB, non-interlaced
```

Valid PNG, 1024x1024, RGB. No suspicious metadata in exiftool output.

### Step 2: LSB Analysis with zsteg

```bash
zsteg Stego200-3.png
```

```
imagedata           .. text: "=83XZJ$\""
b1,r,msb,xy         .. text: "S`\trQlmU1"
b1,g,lsb,xy         .. file: OpenPGP Public Key
b1,g,msb,xy         .. file: OpenPGP Public Key
b1,rgb,lsb,xy       .. text: "poctf{uwsp_70_b3_0r_n07_70_b3}"
```

The flag is in `b1,rgb,lsb,xy` (bit 1, RGB channels, LSB, x-y ordering).

---

## Flag

```
poctf{uwsp_70_b3_0r_n07_70_b3}
```

---

## Lessons Learned

| # | Insight |
|---|---------|
| 1 | When a challenge says previous stego hints were misleading, it is confirming the "obvious" method this time |
| 2 | zsteg on PNG should always be the first step in a stego challenge |
| 3 | The Shakespeare reference in the flag ("to be or not to be") matches the "done and undone" theme |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | Description |
|--------|-----------|-------------|
| Defense Evasion | T1027.003 - Obfuscated Files: Steganography | Data embedded in image LSB channels |
| Exfiltration | T1048 - Exfiltration Over Alternative Protocol | Using image steganography as a covert channel |

---

## Remediation

### Technical Fixes

- Re-encode uploaded images through lossy pipelines to destroy LSB payloads.
- Deploy automated steganalysis at file upload and email gateway points.
- Monitor for high-frequency image transfers that could indicate steganographic exfiltration.

### MITRE D3FEND

| ID | Technique |
|----|-----------|
| D3-SFA | Static File Analysis: steganalysis detection |
| D3-FCOA | File Content Analysis |

### NIST CSF 2.0

| Function | Category | Action |
|----------|----------|--------|
| Detect | DE.CM | Integrate steganalysis into content monitoring |
| Protect | PR.DS | Re-encode images to strip covert channels |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---------|-------------|
| SI-3 | Malicious Code Protection |
| SI-4 | Information System Monitoring |

### C2M2

| Practice | Description |
|----------|-------------|
| DETECT | Include image steganalysis in data loss prevention |

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

To be or not to be: a eterna questao shakespeariana, agora respondida nos bits menos significativos de um PNG. Poesia em pixels!

[![Instagram](https://img.shields.io/badge/Instagram-%23E4405F.svg?style=for-the-badge&logo=Instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/linkedin-%230077B5.svg?style=for-the-badge&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/X-%23000000.svg?style=for-the-badge&logo=X&logoColor=white)](https://x.com/mrhenrike)
