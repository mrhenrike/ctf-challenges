# Letters Never Sent: Variant 088

**Category:** Crypto / Visual Stego / Classical Cipher
**Challenge:** Letters Never Sent
**Variant:** `variant_088`
**Points:** CRYP 100 (Wave 1)
**Result:** Solved

**Recovered key:** `WITHER`

**Flag:**

~~~text
poctf{...}
~~~

---

## 1. Reconnaissance

The challenge provides a scanned Victorian letter and a ciphertext that already resembles a flag:

~~~text
HUROZ{2.1391.4EPNB27L3IBRG6E3.A3CJZ3QQS37EWMB5YVGO5X42WR}
~~~

The image (`variant_088.png`, 820x1120 PNG, 8-bit RGB) shows a letter from Dr. H. Aldous Whitmore, Fellow of the Liminal Society for Spectral Fellowship, dated November 1887.

The letter is addressed to:

> To Admiral Sir Francis Beaufort, K.C.B. / Hydrographer to the Navy

The strongest clue is in the body:

> "that reciprocal tableau which bears your name"

That immediately points toward the **Beaufort cipher**, and the word **reciprocal** helps distinguish Standard Beaufort from Vigenère and Variant Beaufort.

The ciphertext also suggests normal flag-format handling: braces, dots, and digits should remain untouched while alphabetic characters are transformed.

The remaining question is therefore: **where is the key?**

---

## 2. Image Enumeration: Finding the Hidden Key

The border of the letter contains very small words printed around the decorative frame, with several of them marked by red five-pointed stars (★).

At native resolution the text is too small to read reliably, so I cropped each side and upscaled it roughly 5-6x before transcribing it.

The border contains **24 labels** (plant, flower, bird, and instrument names) distributed across all four sides. **6 of them carry red stars.**

### Starred Labels in Variant 088 (Clockwise Traversal)

| Side | Label | Star |
|---|---|---|
| Top | **Willow** | ★ |
| Top | **Iris** | ★ |
| Right | **Tulip** | ★ |
| Bottom | **Harp** | ★ |
| Bottom | **Elder** | ★ |
| Left | **Rose** | ★ |

Reading their initials **clockwise** (top left-to-right, right top-to-bottom, bottom right-to-left, left bottom-to-top):

~~~text
W - I - T - H - E - R
~~~

### Recovered Key: `WITHER`

The word "wither" (to dry up, decay, fade away) fits perfectly with the letter's theme of death, the boundary between the living and the departed, and occult societies.

---

## 3. Cipher Identification: Why Standard Beaufort?

There are three closely related classical ciphers worth separating here.

### Vigenère

~~~text
C = (P + K) mod 26
P = (C - K) mod 26
~~~

### Standard Beaufort

~~~text
C = (K - P) mod 26
P = (K - C) mod 26
~~~

The same operation works in both directions, which is the **reciprocal** property hinted at by the challenge text.

### Variant Beaufort

~~~text
C = (P - K) mod 26
P = (C + K) mod 26
~~~

So the clue combination:

~~~text
Beaufort + reciprocal tableau
~~~

maps specifically to **Standard Beaufort**.

The decryption rule we need is therefore:

~~~text
P = (K - C) mod 26
~~~

---

## 4. Key Handling

The ciphertext contains both alphabetic and non-alphabetic characters:

~~~text
A-Z
0-9
.
{ }
~~~

For this kind of flag-format classical cipher, the correct approach is to:

1. Decrypt only `A-Z`
2. Preserve digits, dots, and braces
3. Advance the repeating key only when a letter is processed

If the key advanced across every character, the first `.` or digit would shift the key alignment and corrupt the rest of the message.

---

## 5. Header Validation: The 5-Character Oracle

Before decrypting the entire string, the first five characters are enough to validate the key and cipher.

Using `P = (K - C) mod 26`:

| Cipher | Key | Computation | Plain |
|---|---|---|---|
| H (7) | W (22) | (22 - 7) = 15 | P |
| U (20) | I (8) | (8 - 20 + 26) = 14 | O |
| R (17) | T (19) | (19 - 17) = 2 | C |
| O (14) | H (7) | (7 - 14 + 26) = 19 | T |
| Z (25) | E (4) | (4 - 25 + 26) = 5 | F |

So:

~~~text
HUROZ -> POCTF  ✓
~~~

This is a very strong oracle. A correct key/cipher combination immediately produces the expected challenge prefix.

**Rabbit hole note:** during the solve, we first tested the key `WITHE` (5 letters, from only 4 visible stars). It also produces `POCTF` for the header since its first 5 characters match WITHER. However, the full flag with WITHE was rejected by the server. The correct key is `WITHER` (6 letters), which requires finding **all 6 starred labels** in the border.

---

## 6. Exploitation: Beaufort Decryption

No external dependency is required.

~~~python
#!/usr/bin/env python3
ct = 'HUROZ{2.1391.4EPNB27L3IBRG6E3.A3CJZ3QQS37EWMB5YVGO5X42WR}'
key = 'WITHER'

def beaufort(s, k):
    result = ''
    key_index = 0
    for ch in s:
        if 'A' <= ch <= 'Z':
            c = ord(ch) - 65
            kk = ord(k[key_index % len(k)]) - 65
            result += chr((kk - c) % 26 + 65)
            key_index += 1
        else:
            result += ch
    return result

pt = beaufort(ct, key)
print(pt)

assert beaufort(pt, key) == ct
~~~

Output:

~~~text
poctf{...}
~~~

---

## 7. Verification

Several independent checks confirm the solution.

### Reciprocity check

Beaufort is reciprocal, so applying the same transformation to the plaintext must recreate the original ciphertext:

~~~text
beaufort(plaintext, key) == ciphertext  →  True ✓
~~~

### Length preservation

The ciphertext and plaintext remain the same length (60 characters). Non-letter characters stay in the same positions.

### Key alignment

The plaintext only comes out correctly when the key advances over alphabetic characters rather than every byte/character.

### Alternative hypotheses tested and rejected

| Key | Cipher | Header Result | Verdict |
|---|---|---|---|
| WITHE | Beaufort | POCTF ✓ | Full flag **rejected** (5-letter key, missing 6th star) |
| WHITE | Beaufort | PNRFF | Wrong header |
| WHITMORE | Beaufort | PNRFN | Wrong header |
| BEAUFORT | Beaufort | UKJGG | Wrong header |
| SPECTRAL | Beaufort | LVNOU | Wrong header |
| WITHE | Vigenère | LMYHV | Wrong header |
| **WITHER** | **Beaufort** | **POCTF ✓** | **Correct** |

---

## 8. Flag Discovery

The recovered plaintext is:

~~~text
poctf{...}
~~~

Submitted via the challenge API and confirmed correct.

---

## 9. Attack Path Summary

~~~text
Image Recon
    ↓
Border Microtext Extraction (zoom 5-6x)
    ↓
Starred-Label Enumeration (6 stars found)
    ↓
Clockwise Traversal: W-I-T-H-E-R
    ↓
Key = WITHER
    ↓
"Beaufort" + "reciprocal tableau" → Standard Beaufort
    ↓
A-Z-only key progression, preserve digits/dots/braces
    ↓
HUROZ -> POCTF (5-char oracle validation)
    ↓
Full Decryption
    ↓
Reciprocity Verification
    ↓
Flag Submitted ✓
~~~

---

## 10. Lessons Learned

| # | Finding | Key Takeaway |
|---|---|---|
| 1 | The key was in the border decorations, not in the letter text | Always inspect the ENTIRE image, not just the text content |
| 2 | Microtext required 5-6x zoom to read reliably | Crop and upscale each side of the border individually |
| 3 | WITHE (5 letters) passed the header oracle but failed the full flag | Count ALL starred labels; a partial key can look correct for the first 5 chars |
| 4 | The word "reciprocal" specifically distinguishes Standard Beaufort | Know the differences between Vigenère, Beaufort, and Variant Beaufort |
| 5 | Key must advance only on alphabetic characters | Digits and punctuation are transparent to the cipher |
| 6 | 5-character oracle is a powerful fast-validation tool | Test key + cipher against the known flag prefix before full decryption |

---

## Reproduction Checklist

- [x] Download `variant_088.png` from the challenge page
- [x] Crop and upscale the border microtext
- [x] Transcribe the 24 labels
- [x] Identify the 6 starred labels
- [x] Traverse the border clockwise
- [x] Recover `WITHER`
- [x] Apply Standard Beaufort: `P = (K - C) mod 26`
- [x] Preserve digits, dots, and braces
- [x] Advance the key only over `A-Z`
- [x] Validate `HUROZ -> POCTF`
- [x] Verify reciprocity
- [x] Submit the recovered flag

---

*Variant-specific: this writeup applies to `variant_088`. Other variants use different star placements and produce different keys (e.g., variant 082 uses `REPOSE`), but the same border-traversal methodology applies.*

---

## 11. MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID | Relevance |
|---|---|---|---|
| Defense Evasion | Obfuscated Files or Information | T1027 | Flag encrypted with classical cipher, requiring key recovery to read |
| Defense Evasion | Hide Artifacts | T1564 | Encryption key hidden as microtext in image border decorations |
| Command and Control | Data Obfuscation: Steganography | T1001.002 | Key embedded visually in image metadata (starred labels in border) |
| Command and Control | Encrypted Channel: Symmetric Cryptography | T1573.001 | Beaufort cipher is a symmetric substitution scheme |
| Credential Access | Unsecured Credentials | T1552 | The cipher key is recoverable from the same artifact that carries the ciphertext |

---

## 12. Remediation and Containment

### Technical Fixes

1. Never distribute the decryption key alongside the ciphertext, even in an obfuscated form
2. Replace classical ciphers (Beaufort, Vigenere, Caesar) with modern authenticated encryption (AES-GCM, ChaCha20-Poly1305) for any real confidentiality requirement
3. Use key management systems (KMS, HSM) to store and distribute encryption keys separately from encrypted data
4. Apply visual watermarking detection to identify steganographic payloads in images processed by the application

### MITRE D3FEND Countermeasures

- **D3-DENCR Data Encryption:** use modern symmetric encryption rather than classical substitution ciphers
- **D3-CKMS Credential Key Management System:** separate key storage from ciphertext delivery
- **D3-SFA Static File Analysis:** detect steganographic content in images via statistical analysis (chi-square, RS analysis)

### NIST CSF 2.0

- **Protect (PR.DS):** encrypt sensitive data with approved cryptographic algorithms (FIPS 140-3 validated)
- **Protect (PR.AA):** manage cryptographic keys through a dedicated key lifecycle process
- **Detect (DE.CM):** monitor for known weak or classical cipher usage in application traffic

### NIST SP 800-53 Rev. 5

- **SC-12 Cryptographic Key Establishment and Management:** implement key management practices that prevent co-location of keys and ciphertext
- **SC-13 Cryptographic Protection:** use FIPS-approved algorithms; classical ciphers do not meet this standard
- **SI-7 Software, Firmware, and Information Integrity:** validate image integrity to detect steganographic modifications
- **SC-28 Protection of Information at Rest:** encrypt stored sensitive data with modern algorithms

---

Thanks guys!! (❍ᴥ❍ʋ)

---

Classical ciphers combined with visual stego make for an incredibly satisfying solve. If this Beaufort cipher walkthrough leveled up your crypto game, share it and connect with me.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
