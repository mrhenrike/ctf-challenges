# Things Seen and Unseen

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2024 |
| **Challenge** | Things Seen and Unseen |
| **Category** | Steganography |
| **Difficulty** | Easy |
| **Points** | 100 |
| **Status** | Solved |

---

## Challenge Overview

A DALL-E generated PNG image contains a flag hidden in the least significant bits (LSB) of the RGB channels. The challenge description references "least significant bits" through an allegory about a programmer who "only did code reviews on the least significant bits."

**File provided:** `Stego100-1.png`

---

## Objective

Extract the LSB-encoded flag from the PNG image.

---

## Methodology

### Step 1: Identify the Technique

The challenge description drops multiple hints:
- "least significant bits" (directly names the technique)
- Reference to Cobol and maintaining legacy systems (the image harbors a hidden legacy)
- DALL-E generated image (AI-generated images are clean canvases for LSB embedding)

### Step 2: Run zsteg

```bash
zsteg -a Stego100-1.png
```

```
b1,g,lsb,xy         .. file: OpenPGP Public Key
b1,g,msb,xy         .. file: OpenPGP Public Key
b1,rgb,lsb,xy       .. text: "poctf{uwsp_wh47_15_d34d_m4y_n3v3r_d13}"
```

The flag is embedded in the LSB of the RGB channels (`b1,rgb,lsb,xy`).

### Step 3: Extract

The flag is directly readable from the zsteg output. No additional processing is needed.

---

## Flag

```
poctf{uwsp_wh47_15_d34d_m4y_n3v3r_d13}
```

---

## Lessons Learned

| # | Insight |
|---|---------|
| 1 | LSB steganography is the most common PNG stego technique in CTFs |
| 2 | zsteg is the go-to tool for PNG steganography analysis |
| 3 | Challenge descriptions often contain direct hints about the technique used |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | Description |
|--------|-----------|-------------|
| Defense Evasion | T1027.003 - Obfuscated Files: Steganography | Data hidden in image LSB channels |
| Exfiltration | T1048 - Exfiltration Over Alternative Protocol | Covert data channel via image steganography |

---

## Remediation

### Technical Fixes

- Implement image re-encoding (lossy conversion) at upload points to destroy LSB payloads.
- Deploy steganalysis tools (zsteg, StegExpose) in DLP pipelines to detect anomalous LSB patterns.
- For sensitive environments, strip image metadata and re-compress images before distribution.

### MITRE D3FEND

| ID | Technique |
|----|-----------|
| D3-SFA | Static File Analysis: steganalysis on image files |
| D3-FCOA | File Content Analysis |

### NIST CSF 2.0

| Function | Category | Action |
|----------|----------|--------|
| Detect | DE.CM | Deploy steganalysis tools for image inspection |
| Protect | PR.DS | Re-encode images to neutralize LSB steganography |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---------|-------------|
| SI-3 | Malicious Code Protection |
| SI-4 | Information System Monitoring |

### C2M2

| Practice | Description |
|----------|-------------|
| DETECT | Include steganalysis in data loss prevention workflows |

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

LSB classico: quando a imagem esconde segredos nos bits menos significativos, o zsteg resolve em segundos. Ferramenta obrigatoria no kit de stego!

[![Instagram](https://img.shields.io/badge/Instagram-%23E4405F.svg?style=for-the-badge&logo=Instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/linkedin-%230077B5.svg?style=for-the-badge&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/X-%23000000.svg?style=for-the-badge&logo=X&logoColor=white)](https://x.com/mrhenrike)
