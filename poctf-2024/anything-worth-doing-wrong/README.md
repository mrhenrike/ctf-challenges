# Anything Worth Doing Wrong

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

The challenge provides an image of a maze. Tracing the correct path through the maze reveals hidden text that forms the flag.

---

## Objective

Navigate the maze from start to finish and read the characters embedded along the solution path.

---

## Methodology

### Step 1: Analyze the Maze Image

Opening the image reveals a standard maze grid with a marked entry and exit point. The walls and paths contain subtle character markings.

### Step 2: Solve the Maze

Using either manual tracing or a maze-solving approach (wall-following or backtracking), find the unique path from start to finish.

### Step 3: Extract the Hidden Text

Following the solution path in order, read the characters printed along it. These characters spell out the flag content when combined.

### Step 4: Construct the Flag

Wrapping the extracted text in the standard `poctf{uwsp_...}` format produces the final flag.

---

## Lessons Learned

| # | Insight |
|---|---------|
| 1 | Visual puzzles in CTFs often hide data along the solution path |
| 2 | Image analysis tools can help identify subtle text embedded in complex images |
| 3 | Systematic maze-solving algorithms prevent missing the correct route |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | Description |
|--------|-----------|-------------|
| Defense Evasion | T1027.003 - Steganography | Information concealed within a visual medium |
| Collection | T1113 - Screen Capture | Extracting visual data for analysis |

---

## Remediation

### Technical Fixes

- Steganographic concealment within visual puzzles provides no real security.
- Data hiding in images should use established steganographic tools with encryption for any serious application.

### MITRE D3FEND

| ID | Technique |
|----|-----------|
| D3-SDA | Static Document Analysis: examine visual files for hidden content |

### NIST CSF 2.0

| Function | Category | Action |
|----------|----------|--------|
| Detect | DE.AE | Monitor for data concealment techniques in transmitted files |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---------|-------------|
| SI-3 | Malicious Code Protection: scan files for hidden payloads |

### C2M2

| Practice | Description |
|----------|-------------|
| DETECT | Implement content inspection for steganographic techniques |

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

Sometimes doing it wrong is the only way to find what's right. The maze is solved, the flag is ours!

[![Instagram](https://img.shields.io/badge/Instagram-%23E4405F.svg?style=for-the-badge&logo=Instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/linkedin-%230077B5.svg?style=for-the-badge&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/X-%23000000.svg?style=for-the-badge&logo=X&logoColor=white)](https://x.com/mrhenrike)
