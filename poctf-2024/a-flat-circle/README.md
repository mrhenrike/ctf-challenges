# A Flat Circle

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2024 |
| **Category** | Digital Forensics |
| **Difficulty** | Expert |
| **Points** | 400 |
| **Flag** | `poctf{uwsp_7h3_m4n_1n_7h3_h16h_c457l3}` |
| **Status** | Solved |

---

## 1. Challenge Overview

A steganography-forensics hybrid: a PNG image containing an optical illusion that hides the flag in a specific bit plane. The challenge description references cyclical patterns and hidden truths, hinting at layer-by-layer analysis.

**Files:** `DF100-2.png` (PNG image with optical illusion)

![Challenge image](images/DF100-2.png)

---

## 2. Initial Analysis

Confirmed the file type and checked for obvious anomalies:

~~~bash
file DF100-2.png
exiftool DF100-2.png
~~~

The file is a valid PNG created with GIMP (version 2.10.36, dated 2024-10-31).

---

## 3. Steganographic Analysis

Ran `zsteg -a` to scan all bit planes and encoding methods:

~~~bash
zsteg -a DF100-2.png
~~~

Found a hex string in one of the channels containing EXIF-like metadata with GIMP references and a timestamp. This was a red herring pointing to the creation tool.

---

## 4. Bit Plane Analysis with Stegsolve

Opened the image in **Stegsolve** and cycled through color channels and bit planes:

- Red/Green/Blue planes: no visible data
- **Gray bits plane:** the flag text became visible, embedded as contrasting pixels within the image

The flag `poctf{uwsp_7h3_m4n_1n_7h3_h16h_c457l3}` was readable directly from the gray bits visualization.

---

## Lessons Learned

| # | Lesson | Detail |
|---|--------|--------|
| 1 | Stegsolve is essential for image forensics | Bit plane analysis reveals data invisible to the eye |
| 2 | EXIF metadata can be a deliberate red herring | Creation tool info does not always lead to the flag |
| 3 | Gray channel analysis covers combined RGB patterns | Some steganographic methods are only visible in composite views |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID | Context |
|---|---|---|---|
| Defense Evasion | Obfuscated Files or Information: Steganography | T1027.003 | Flag hidden in image bit planes |
| Defense Evasion | Obfuscated Files or Information | T1027 | Data concealed in visual noise of an optical illusion |
| Collection | Data Staged: Local Data Staging | T1074.001 | Sensitive data embedded within an image file for exfiltration |

> **CWE-311:** Missing Encryption of Sensitive Data. The flag is encoded in bit planes without encryption, recoverable with standard tools.

---

## Remediation and Containment

### Technical Fixes

1. Encrypt data before embedding in steganographic carriers
2. Use advanced steganographic methods resistant to statistical analysis (e.g., adaptive steganography)
3. Apply DLP solutions that scan images for hidden data before exfiltration
4. Monitor for steganography tools (Stegsolve, zsteg, steghide) in endpoint telemetry

### MITRE D3FEND Countermeasures

- **D3-FCOA (File Content Analysis):** scan images for steganographic content before transmission
- **D3-DA (Dynamic Analysis):** detect steganography tools in endpoint process monitoring
- **D3-NTA (Network Traffic Analysis):** inspect image files leaving the network for anomalous bit patterns

### NIST CSF 2.0

- **Protect (PR.DS):** implement DLP controls for image-based data exfiltration
- **Detect (DE.CM):** deploy steganalysis tools on network egress points
- **Respond (RS.MI):** quarantine images flagged by steganalysis for manual review

### NIST SP 800-53 Rev. 5

- **SC-8 (Transmission Confidentiality and Integrity):** inspect transmitted media for covert channels
- **AU-13 (Monitoring for Information Disclosure):** monitor for steganographic exfiltration patterns
- **SI-4 (Information System Monitoring):** detect steganography tool execution

### NIST SP 800-86

- **Media Analysis:** apply bit-level forensic examination to image evidence
- **Evidence Handling:** preserve original image files with hash verification before analysis

### C2M2

- **THREAT-3:** include steganographic exfiltration in threat modeling
- **SITUATION-2:** monitor for covert channel indicators in DLP alerts

---

Thanks guys!! (❍ᴥ❍ʋ)

---

Time is a flat circle, and so is the journey through image bit planes until the flag appears. The Man in the High Castle was hiding in the gray bits all along.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

> **Reference:** Adapted from [shivang1209-dot/CTF-Writeups](https://github.com/shivang1209-dot/CTF-Writeups). Original scripts credited to the author.
