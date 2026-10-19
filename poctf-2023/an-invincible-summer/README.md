# An Invincible Summer

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2023 |
| **Challenge** | An Invincible Summer |
| **Category** | Steganography |
| **Difficulty** | Medium |
| **Points** | 200 |
| **Status** | Solved |

---

## 1. Challenge Overview

The challenge provides two image files in different formats (e.g., PNG and BMP) that appear visually identical. The flag is hidden in the pixel-level differences between the two images, specifically encoded in the red channel.

---

## 2. Analyzing the Images

Both images look the same to the naked eye. Running basic checks:

~~~bash
file image1.png image2.bmp
identify -verbose image1.png | head -20
identify -verbose image2.bmp | head -20
~~~

The file sizes differ despite identical visual content, suggesting data is embedded in the pixel values of one or both images.

---

## 3. Extracting the Hidden Data

Using a Steganographic Comparator or Aperi'Solve to compare the images pixel by pixel:

1. **Upload both images** to Aperi'Solve or use a manual comparison script
2. **Compute the pixel difference** between the two images
3. **Examine the red channel** specifically, where differences encode the flag

A Python approach:

~~~python
from PIL import Image

img1 = Image.open("image1.png")
img2 = Image.open("image2.bmp")

pixels1 = img1.load()
pixels2 = img2.load()

result = ""
for y in range(img1.height):
    for x in range(img1.width):
        r1, g1, b1 = pixels1[x, y][:3]
        r2, g2, b2 = pixels2[x, y][:3]
        diff = abs(r1 - r2)
        if diff > 0:
            result += chr(diff)

print(result)
~~~

The difference in the red channel values decodes to ASCII characters forming the flag:

~~~text
poctf{uwsp_1nv1nc18l3_5umm3r_r3v34l3d}
~~~

---

## 4. Attack Path Summary

~~~text
Two images (PNG + BMP), visually identical
    |
Pixel-by-pixel comparison
    |
Red channel difference extraction
    |
ASCII decode of difference values
    |
FLAG: poctf{uwsp_1nv1nc18l3_5umm3r_r3v34l3d}
~~~

---

## 5. Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|--------------|
| 1 | Dual-image steganography hides data in pixel differences | APT groups have used image comparison techniques to exchange covert messages | Always compare related images for subtle channel-level differences |
| 2 | Format conversion can expose or hide data | Converting between PNG and BMP changes compression but may preserve stego payloads | Analyze images in their original and converted forms for discrepancies |
| 3 | Red channel is a common hiding spot | Single-channel encoding is less visually detectable than modifying all RGB channels | Check each channel independently with tools like Stegsolve or Aperi'Solve |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Defense Evasion | TA0005 | Obfuscated Files or Information: Steganography | T1027.003 |
| Command and Control | TA0011 | Data Obfuscation: Steganography | T1001.002 |
| Exfiltration | TA0010 | Exfiltration Over C2 Channel | T1041 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediation and Containment

### Technical Fixes

1. Implement image re-encoding at network boundaries to strip pixel-level stego payloads
2. Deploy stego detection tools that compare uploaded images against known clean versions
3. Monitor for unusual patterns of image file pairs being transferred together

### MITRE D3FEND Countermeasures

- **D3-FCR File Content Rules** to detect image files with statistically anomalous pixel distributions (counters T1027.003)
- **D3-NTA Network Traffic Analysis** for detecting covert data transfer via image steganography (counters T1001.002)

### NIST CSF 2.0

- **Detect (DE.CM-1):** Monitor for image-based data exfiltration patterns
- **Protect (PR.DS-5):** Re-encode media files at trust boundaries to neutralize stego payloads

### NIST SP 800-53 Rev. 5

- **SI-3: Malicious Code Protection** (detect steganographic content in media files)
- **SC-7: Boundary Protection** (inspect and sanitize images at network perimeters)

### CWE

- **CWE-502: Deserialization of Untrusted Data** (image processing without stego validation)

---

## References

- Solve approach based on research from [Jihun Hwang's POCTF 2023 writeup](https://jihunhwang.github.io/UWSP_CTF_2023_writeup/) and [Joooook's blog](https://joooook.github.io/2024/02/05/UWSP%20Pointer%20Overflow%20CTF/)

---

Thanks guys!! (❍ᴥ❍ʋ)

---

In the middle of winter, Camus found an invincible summer. In the middle of two identical images, we found a hidden flag. Both require looking deeper than what appears on the surface.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
