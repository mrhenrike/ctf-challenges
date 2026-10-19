# Deceived by Touch

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2024 |
| **Challenge** | Deceived by Touch |
| **Category** | Miscellaneous |
| **Difficulty** | Hard |
| **Points** | 300 |
| **Status** | Solved |

---

## Challenge Overview

The challenge presents text encoded with a Baconian cipher. Francis Bacon's biliteral cipher uses two typefaces (or two symbols) to encode each letter in groups of five characters.

---

## Objective

Identify the Baconian cipher pattern, decode the groups, and recover the flag.

---

## Methodology

### Step 1: Recognize the Cipher

The provided text uses two distinct character styles (e.g., uppercase/lowercase, bold/normal, or two different letters). Groups of five characters each encode one letter.

### Step 2: Map to Binary

In Bacon's cipher, each group of five characters maps to a binary pattern:
- Style A = 0
- Style B = 1

Each five-bit group corresponds to a letter:

| Binary | Letter |
|--------|--------|
| 00000 | A |
| 00001 | B |
| 00010 | C |
| ... | ... |
| 11001 | Z |

### Step 3: Decode All Groups

Processing each five-character group through the Baconian lookup table produces the plaintext letters.

### Step 4: Assemble the Flag

The decoded text, formatted as `poctf{uwsp_...}`, is the final flag.

---

## Lessons Learned

| # | Insight |
|---|---------|
| 1 | Baconian cipher is a classic steganographic technique using two distinct symbols |
| 2 | Recognizing the two-symbol pattern is the key insight for this cipher type |
| 3 | Historical ciphers remain popular in CTF challenges as educational exercises |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | Description |
|--------|-----------|-------------|
| Defense Evasion | T1001 - Data Obfuscation | Message concealed within seemingly normal text |
| Defense Evasion | T1027 - Obfuscated Files or Information | Content encoded using a classical cipher |

---

## Remediation

### Technical Fixes

- Baconian cipher is a 400-year-old encoding scheme with no cryptographic strength.
- For secure communication, replace classical ciphers with authenticated encryption (AES-GCM, ChaCha20-Poly1305).

### MITRE D3FEND

| ID | Technique |
|----|-----------|
| D3-DA | Dynamic Analysis: apply known classical cipher decoding to suspect text |

### NIST CSF 2.0

| Function | Category | Action |
|----------|----------|--------|
| Protect | PR.DS | Use modern encryption standards for data confidentiality |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---------|-------------|
| SC-13 | Cryptographic Protection: employ FIPS-validated cryptographic modules |

### C2M2

| Practice | Description |
|----------|-------------|
| PROTECT | Replace legacy encoding with modern cryptographic controls |

### CWE

| ID | Description |
|----|-------------|
| CWE-327 | Use of a Broken or Risky Cryptographic Algorithm |

---

## References

- [yocchin POCTF 2024 Writeup](https://yocchin.hatenablog.com/entry/2025/01/23/140330) (original reference)
- [Francis Bacon's Cipher](https://en.wikipedia.org/wiki/Bacon%27s_cipher)
- [Pointer Overflow CTF](https://pointeroverflowctf.com/)

---

Thanks guys!! (❍ᴥ❍ʋ)

Sir Francis would be proud: his 400-year-old cipher still teaches us about hidden messages. The flag is decoded!

[![Instagram](https://img.shields.io/badge/Instagram-%23E4405F.svg?style=for-the-badge&logo=Instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/linkedin-%230077B5.svg?style=for-the-badge&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/X-%23000000.svg?style=for-the-badge&logo=X&logoColor=white)](https://x.com/mrhenrike)
