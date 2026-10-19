# Between Secrets and Lies

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2023 |
| **Category** | Steganography |
| **Difficulty** | Hard |
| **Points** | 300 |
| **Flag** | `poctf{uwsp_83tw33n_53cr375_4nd_l135}` |
| **Status** | Solved |

---

## 1. Challenge Overview

The challenge provides an image with the flag encoded in colored pixels located in the corner of the image. Red pixels in a specific region encode binary data that, when extracted and converted, reveals the flag.

---

## 2. Initial Analysis

Opening the image in a standard viewer shows what appears to be a normal photograph. However, careful examination of the corners reveals a cluster of colored pixels that differ from the surrounding area.

Using Stegsolve to inspect individual bit planes:

1. Open the image in **Stegsolve**
2. Navigate through the bit planes using the arrow controls
3. On the **Red plane 0 (LSB)**, a distinct pattern of pixels becomes visible in the corner region

---

## 3. Extracting the Binary Data

The red pixels in the corner encode binary data: red = 1, no red = 0. Reading the pixel values left-to-right, top-to-bottom:

~~~python
from PIL import Image

img = Image.open("challenge.png")
pixels = img.load()

binary = ""
for y in range(0, 8):
    for x in range(0, img.width):
        r, g, b = pixels[x, y][:3]
        if r > 200 and g < 50 and b < 50:
            binary += "1"
        else:
            binary += "0"

text = ""
for i in range(0, len(binary), 8):
    byte = binary[i:i+8]
    if len(byte) == 8:
        char = chr(int(byte, 2))
        if char.isprintable():
            text += char

print(text)
~~~

The extracted binary decodes to ASCII, revealing the flag:

~~~text
poctf{uwsp_83tw33n_53cr375_4nd_l135}
~~~

---

## 4. Attack Path Summary

~~~text
Challenge image
    |
Stegsolve bit-plane analysis (Red LSB)
    |
Corner pixels: red = 1, other = 0
    |
Binary to ASCII conversion
    |
FLAG: poctf{uwsp_83tw33n_53cr375_4nd_l135}
~~~

---

## 5. Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|--------------|
| 1 | Bit-plane analysis reveals hidden patterns | Malware has used LSB encoding in images to exfiltrate data past DLP systems | Stegsolve and similar tools should be standard in forensic toolkits |
| 2 | Specific image regions can carry encoded messages | Corners and edges are common hiding spots because changes there are less noticeable | Always examine all regions of an image, especially low-attention areas |
| 3 | Color-based binary encoding is a practical stego method | Using a single color channel to encode bits is a simple but effective technique | Check each RGB channel independently for anomalous pixel patterns |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Defense Evasion | TA0005 | Obfuscated Files or Information: Steganography | T1027.003 |
| Command and Control | TA0011 | Data Obfuscation: Steganography | T1001.002 |
| Collection | TA0009 | Data Staged: Local Data Staging | T1074.001 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediation and Containment

### Technical Fixes

1. Re-encode images at trust boundaries to destroy LSB-based stego payloads
2. Deploy statistical stego analysis tools (chi-square, RS analysis) on images leaving the network
3. Implement content sanitization policies that strip metadata and normalize pixel values

### MITRE D3FEND Countermeasures

- **D3-FCR File Content Rules** for detecting LSB anomalies in image files (counters T1027.003)
- **D3-DA Data Analysis** using statistical methods to identify non-random bit distributions (counters T1001.002)

### NIST CSF 2.0

- **Detect (DE.AE-1):** Establish baselines for normal image file characteristics
- **Protect (PR.DS-5):** Sanitize media files to remove potential stego payloads

### NIST SP 800-53 Rev. 5

- **SI-3: Malicious Code Protection** (detect LSB steganography in image files)
- **SC-7: Boundary Protection** (sanitize images at network boundaries)

### CWE

- **CWE-353: Missing Support for Integrity Check** (no pixel-level validation of image content)

---

## References

- Solve approach based on research from [Jihun Hwang's POCTF 2023 writeup](https://jihunhwang.github.io/UWSP_CTF_2023_writeup/) and [Joooook's blog](https://joooook.github.io/2024/02/05/UWSP%20Pointer%20Overflow%20CTF/)

---

Thanks guys!! (❍ᴥ❍ʋ)

---

Between the secrets hidden in pixels and the lies told by an image that "looks normal," a few red dots in the corner carried the truth all along. Stegsolve strips away the disguise one bit plane at a time.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
