# Could It Be the Winter

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2024 |
| **Challenge** | Could It Be the Winter |
| **Category** | Miscellaneous |
| **Difficulty** | Easy |
| **Points** | 100 |
| **Status** | Solved |

---

## Challenge Overview

The challenge presents 12 logic and math puzzles. Each puzzle produces a numeric result that maps to a character, and combining all 12 characters in order reveals the flag.

---

## Objective

Solve each of the 12 puzzles, convert the answers to characters, and assemble the flag.

---

## Methodology

### Step 1: Solve Individual Puzzles

Each puzzle is a self-contained logic or arithmetic problem. Examples of puzzle types encountered:

- Simple arithmetic with constraints
- Pattern recognition in number sequences
- Logical deductions from given clues
- Mathematical word problems

### Step 2: Map Results to Characters

Each numeric answer corresponds to a character. The mapping follows a consistent scheme (e.g., position in the alphabet, ASCII value offset, or a provided lookup table).

### Step 3: Assemble the Flag

Reading the 12 characters in order and wrapping in the flag format `poctf{uwsp_...}` produces the final flag.

---

## Lessons Learned

| # | Insight |
|---|---------|
| 1 | Multi-stage puzzles require systematic tracking of intermediate results |
| 2 | Each sub-puzzle may use a different solving technique; flexibility is key |
| 3 | Mapping numeric results to characters is a common CTF encoding pattern |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | Description |
|--------|-----------|-------------|
| Defense Evasion | T1027 - Obfuscated Files or Information | Data hidden across multiple encoded layers |
| Collection | T1005 - Data from Local System | Extracting meaningful data from disparate sources |

---

## Remediation

### Technical Fixes

- Multi-layer encoding does not substitute for encryption; each layer adds complexity but not security.
- Puzzle-based access controls are novelty mechanisms, not security boundaries.

### MITRE D3FEND

| ID | Technique |
|----|-----------|
| D3-DA | Dynamic Analysis: solve each component independently to recover the complete message |

### NIST CSF 2.0

| Function | Category | Action |
|----------|----------|--------|
| Protect | PR.DS | Apply defense-in-depth with real cryptographic controls, not puzzles |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---------|-------------|
| SC-13 | Cryptographic Protection: use validated modules rather than custom encoding |

### C2M2

| Practice | Description |
|----------|-------------|
| PROTECT | Ensure data protection relies on cryptographic strength, not obscurity |

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

Twelve puzzles, twelve answers, one flag. Winter may be cold, but the victory is warm!

[![Instagram](https://img.shields.io/badge/Instagram-%23E4405F.svg?style=for-the-badge&logo=Instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/linkedin-%230077B5.svg?style=for-the-badge&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/X-%23000000.svg?style=for-the-badge&logo=X&logoColor=white)](https://x.com/mrhenrike)
