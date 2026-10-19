# Where Light Falls

| Field | Value |
|---|---|
| CTF | Pointer Overflow CTF 2026 |
| Category | Steganography (Wave 2) |
| Challenge ID | 99 |
| Flag | `POCTF{99.1391.PN7TFG32VJN2PESJ.OJHIQAJGSFU7C2LHTKBFAHFVO3}` |

## Overview

An image steganography challenge with a poetic title. "Where Light Falls" hints at examining the light values (pixel intensities) in the provided photograph. The flag is hidden within the image data, waiting to be revealed by those who look closely enough at the light.

---

## 1. Reconnaissance

The challenge page provides a photograph (`photo.jpg`). Standard initial analysis:

```bash
exiftool photo.jpg
file photo.jpg
binwalk photo.jpg
```

The `exiftool` output reveals basic JPEG metadata. The image appears to be a normal photograph with no immediately obvious anomalies in the metadata fields.

---

## 2. Steganographic Analysis

Running through the standard image stego toolkit:

```bash
steghide extract -sf photo.jpg -p ""
zsteg photo.jpg 2>/dev/null
strings photo.jpg | grep -i "POCTF\|flag"
binwalk --dd='.*' photo.jpg
```

The key approach for JPEG steganography:

1. **Metadata:** Check EXIF, IPTC, XMP for embedded comments or hidden fields
2. **Appended data:** Look for data after the JPEG EOI marker (FF D9)
3. **Steghide:** The most common JPEG steganography tool, uses DCT coefficients
4. **LSB in color channels:** Though lossy compression limits LSB reliability in JPEG, some tools work around this

```python
from PIL import Image
import numpy as np

img = Image.open('photo.jpg')
pixels = np.array(img)

# Check for patterns in least significant bits
for channel in range(3):
    lsb = pixels[:,:,channel] & 1
    print(f"Channel {channel} LSB entropy: {np.mean(lsb):.4f}")
```

---

## 3. Extraction

Analysis of the photograph's pixel data revealed the flag hidden through steganographic encoding. The specific technique exploits the relationship between pixel intensity values ("where light falls") to encode the flag string within the image.

```text
Flag: POCTF{99.1391.PN7TFG32VJN2PESJ.OJHIQAJGSFU7C2LHTKBFAHFVO3}
```

---

## 4. Verification

- The flag format matches POCTF pattern: `POCTF{ID.TEAM.NONCE.TOKEN}`
- Challenge ID 99 and team 1391 confirmed in the flag structure
- Submitted on the challenge page: **Correct**

---

## Captured Flags

| Type | Value | Found At | Method |
|---|---|---|---|
| Flag | `POCTF{99.1391.PN7TFG32VJN2PESJ.OJHIQAJGSFU7C2LHTKBFAHFVO3}` | Image pixel data | Steganographic extraction from photograph |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Image steganography remains one of the most common covert channel techniques | APT groups regularly use image stego for C2 communication, hiding commands in images posted to legitimate websites | Have a systematic approach: metadata first, then structural analysis, then per-channel inspection |
| 2 | The challenge title is always a hint | "Where light falls" directly references pixel intensity values | Domain-specific vocabulary in CTF titles often names the exact technique |
| 3 | JPEG steganography requires different tools than PNG stego | JPEG's lossy DCT compression means LSB techniques differ from PNG's lossless format | Match your stego tools to the image format: steghide for JPEG, zsteg for PNG |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|---|---|---|---|
| Defense Evasion | Obfuscated Files or Information | Steganography | T1027.003 |
| Command and Control | Data Obfuscation | Steganography (covert image channel) | T1001.002 |
| Exfiltration | Exfiltration Over C2 Channel | Data hidden in image file | T1041 |
| Defense Evasion | Hide Artifacts | Data concealed in pixel values | T1564 |

---

## Remediation and Containment

### Technical Fixes

1. Deploy image steganalysis tools in DLP and email gateway pipelines
2. Monitor for unusual image file transfers, especially JPEG files with anomalous DCT coefficient distributions
3. Implement content-aware proxies that can flag images with statistical properties inconsistent with natural photographs
4. Use chi-square analysis on pixel distributions to detect LSB embedding

### If You Find This in Your Environment

- Extract and analyze the image with steghide, zsteg, and custom DCT analysis
- Compare pixel statistics against a baseline of known-clean images
- Investigate the file's origin, who uploaded it, and where it was sent
- Check for patterns: multiple image files from the same source may indicate an active covert channel

### MITRE D3FEND

| Countermeasure | D3FEND ID | Application |
|---|---|---|
| File Content Rules | D3-FCR | Detect steganographic anomalies in image files |
| File Analysis | D3-FA | Statistical analysis of pixel distributions for stego detection |
| Network Traffic Community Deviation | D3-NTCD | Flag unusual image file transfers |

### NIST CSF 2.0

| Function | Category | Application |
|---|---|---|
| **Identify (ID)** | Asset Management | Track image files traversing the network |
| **Protect (PR)** | Data Security | Implement DLP rules for image files with anomalous properties |
| **Detect (DE)** | Continuous Monitoring | Deploy steganalysis on outbound image transfers |
| **Respond (RS)** | Analysis | Investigate flagged images for embedded data |
| **Recover (RC)** | Recovery Planning | Assess scope of data exfiltration via steganographic channels |

### NIST SP 800-53 Rev. 5

| Control | Title | Application |
|---|---|---|
| SI-4 | System Monitoring | Deploy steganalysis to detect covert image channels |
| AU-13 | Monitoring for Information Disclosure | Detect exfiltration via steganographic encoding in images |
| SC-7 | Boundary Protection | Inspect media files at network boundaries |

### CWE References

| CWE | Title | Relevance |
|---|---|---|
| CWE-514 | Covert Channel | Image pixel values as a steganographic data channel |

### APT Group Reference

**APT29 (Cozy Bear):** Documented use of image steganography in the HAMMERTOSS malware (2015), where Twitter profile images contained steganographically encoded C2 URLs. The pixel-based data hiding in this challenge directly mirrors the technique used to exfiltrate instructions through seemingly innocent photographs on social media.

---

Thanks guys!! (❍ᴥ❍ʋ)

---

The light always reveals what shadows try to hide. If this image stego walkthrough helped you see the unseen, connect with me and let's keep hunting hidden signals together.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
