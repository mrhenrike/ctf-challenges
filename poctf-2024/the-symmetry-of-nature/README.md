# The Symmetry of Nature

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2024 |
| **Category** | Unknown |
| **Difficulty** | Unknown |
| **Points** | N/A |
| **Flag** | `poctf{uwsp_un57Opp4bl3_f0rc3}` |
| **Status** | Solved |

---

## Challenge Overview

The challenge provides a numeric ciphertext and references to Castor and Pollux, hinting at the Pollux cipher (a Morse code variant where digits map to dots, dashes, and spaces).

**Ciphertext:**

```
84150717615789492248{688795176222681450_8273783252253178253147624750271202558794588687556525149_25153414179812378489258473}
```

---

## Objective

Decode the numeric ciphertext using the Pollux cipher to recover the Morse-encoded flag.

---

## Methodology

### Step 1: Identify the Cipher

The challenge description mentions Castor and Pollux (from Gemini mythology and the film Face/Off). This is a strong hint toward the **Pollux cipher**, where each digit maps to a Morse code symbol:
- **Dot (.)**: 2, 5, 8
- **Dash (-)**: 1, 4, 7
- **Space**: 0, 6, 9

### Step 2: Validate with Known Prefix

The first segment `84150717615789492248` should decode to `POCTF`:

```
8(.) 4(-) 1(-) 5(.) 0( ) 7(-) 1(-) 7(-) 6( ) 1(-) 5(.) 7(-) 8(.) 9( ) 4(-) 9( ) 2(.) 2(.) 4(-) 8(.)
.--. --- -.-. - ..-.
P    O   C    T F
```

Confirmed: the mapping is correct.

### Step 3: Decode Remaining Segments

For the third and fourth segments, an additional digit `3` appears, mapping to **space**:

Updated mapping:
- **Dot (.)**: 2, 5, 8
- **Dash (-)**: 1, 4, 7
- **Space**: 0, 3, 6, 9

Applying this mapping to the full ciphertext and converting Morse to ASCII reveals the flag.

---

## Flag

```
poctf{uwsp_un57Opp4bl3_f0rc3}
```

---

## Lessons Learned

| # | Insight |
|---|---------|
| 1 | Challenge descriptions often contain cipher identification hints through cultural references |
| 2 | The Pollux cipher maps digits to Morse symbols; validate mappings with known plaintext |
| 3 | When new digits appear in later segments, the mapping may need expansion |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | Description |
|--------|-----------|-------------|
| Defense Evasion | T1001.001 - Data Obfuscation: Junk Data | Encoding messages in numeric form to obscure content |
| Defense Evasion | T1140 - Deobfuscate/Decode Files or Information | Reversing numeric-to-Morse encoding |

---

## Remediation

### Technical Fixes

- The Pollux cipher is a toy encoding, not encryption. Never rely on obscurity-based schemes for real communications.
- For secure message exchange, use authenticated encryption (AES-GCM, ChaCha20-Poly1305).

### MITRE D3FEND

| ID | Technique |
|----|-----------|
| D3-DNSA | DNS Traffic Analysis: inspect for covert channels using numeric encoding |

### NIST CSF 2.0

| Function | Category | Action |
|----------|----------|--------|
| Protect | PR.DS | Use standards-based encryption rather than encoding for data confidentiality |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---------|-------------|
| SC-13 | Cryptographic Protection |
| SC-8 | Transmission Confidentiality and Integrity |

### C2M2

| Practice | Description |
|----------|-------------|
| PROTECT | Apply authenticated encryption to communications channels |

### CWE

| ID | Description |
|----|-------------|
| CWE-311 | Missing Encryption of Sensitive Data |
| CWE-327 | Use of a Broken or Risky Cryptographic Algorithm |

---

## References

- [shivang1209-dot POCTF 2024 Writeups](https://github.com/shivang1209-dot/shivang1209-dot) (original reference)
- [Pollux Cipher on dCode](https://www.dcode.fr/pollux-cipher)
- [Pointer Overflow CTF](https://pointeroverflowctf.com/)

---

Thanks guys!! (❍ᴥ❍ʋ)

Morse em forma de numeros: quando o CTF mistura historia com criptografia classica, a diversao e garantida. Bora pro proximo!

[![Instagram](https://img.shields.io/badge/Instagram-%23E4405F.svg?style=for-the-badge&logo=Instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/linkedin-%230077B5.svg?style=for-the-badge&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/X-%23000000.svg?style=for-the-badge&logo=X&logoColor=white)](https://x.com/mrhenrike)
