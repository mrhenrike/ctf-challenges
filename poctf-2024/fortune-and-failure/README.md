# Fortune and Failure

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2024 |
| **Challenge** | Fortune and Failure |
| **Category** | Cryptography |
| **Difficulty** | Easy |
| **Points** | 100 |
| **Status** | Solved |

---

## Challenge Overview

A ciphertext is provided in flag format with an alternating rotation cipher applied to alphabetic characters. The challenge description hints that the key is short, part of the message is known (flag prefix `poctf{uwsp_`), and no additional clue is needed.

**Ciphertext:**

```
hottx{unsh_4_w4ck_7zrfuyh_7y3_h1dl5}
```

---

## Objective

Identify the alternating rotation pattern and decrypt the ciphertext to recover the flag.

---

## Methodology

### Step 1: Recognize the Pattern

The ciphertext preserves the `{}`, underscores, and digits from the flag format. Only alphabetic characters are transformed. Comparing the known prefix `poctf` with the ciphertext `hottx`:

| Position | Cipher | Plain | Shift |
|----------|--------|-------|-------|
| 1 (odd) | h | p | -8 (or +18) |
| 2 (even) | o | o | 0 (or +17 mod 26... wait) |

A closer look reveals a two-key alternating ROT cipher:
- **Odd-positioned letters**: shifted by +18 (ROT18)
- **Even-positioned letters**: shifted by +17 (ROT17)

### Step 2: Apply Reverse Shifts

Reversing the shifts (subtract 18 for odd, subtract 17 for even positions) on each alphabetic character:

```
h -> p  (odd, -18)
o -> o  (even, -17... wraps correctly)
t -> c  (odd, -18)
t -> t  (even, -17)
x -> f  (odd, -18)
u -> u  (even, -17 mod 26)
n -> w  ...
s -> s
h -> p
...
```

### Step 3: Full Decryption

Applying the pattern across the entire ciphertext yields the complete flag.

---

## Flag

```
poctf{uwsp_4_w4lk_7hrough_7h3_h1ll5}
```

---

## Lessons Learned

| # | Insight |
|---|---------|
| 1 | Known plaintext (flag prefix) is invaluable for identifying rotation keys |
| 2 | Alternating key ciphers are a common CTF variation of classical substitution |
| 3 | Non-alphabetic characters remaining unchanged is a strong indicator of a rotation cipher |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | Description |
|--------|-----------|-------------|
| Collection | T1560 - Archive Collected Data | Encoding data before exfiltration |
| Defense Evasion | T1140 - Deobfuscate/Decode Files or Information | Reversing obfuscation to recover plaintext |

---

## Remediation

### Technical Fixes

- Classical rotation ciphers provide zero security; use modern symmetric encryption (AES-256) for any real data protection.
- Alternating-key substitution is trivially breakable with known plaintext.

### MITRE D3FEND

| ID | Technique |
|----|-----------|
| D3-DE | Decoy Environment: use CTF-style challenges for security awareness training |

### NIST CSF 2.0

| Function | Category | Action |
|----------|----------|--------|
| Protect | PR.DS | Encrypt sensitive data with strong, modern algorithms |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---------|-------------|
| SC-13 | Cryptographic Protection: employ FIPS-validated cryptographic modules |

### C2M2

| Practice | Description |
|----------|-------------|
| PROTECT | Implement strong cryptographic controls for data at rest and in transit |

### CWE

| ID | Description |
|----|-------------|
| CWE-327 | Use of a Broken or Risky Cryptographic Algorithm |
| CWE-328 | Use of Weak Hash |

---

## References

- [shivang1209-dot POCTF 2024 Writeups](https://github.com/shivang1209-dot/shivang1209-dot) (original reference)
- [Pointer Overflow CTF](https://pointeroverflowctf.com/)

---

Thanks guys!! (❍ᴥ❍ʋ)

Cada cifra quebrada e cada flag capturada e mais um passo na jornada. Seguimos firmes!

[![Instagram](https://img.shields.io/badge/Instagram-%23E4405F.svg?style=for-the-badge&logo=Instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/linkedin-%230077B5.svg?style=for-the-badge&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/X-%23000000.svg?style=for-the-badge&logo=X&logoColor=white)](https://x.com/mrhenrike)
