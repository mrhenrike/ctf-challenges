# Separating the Firmament

**Category:** Reverse Engineering
**Challenge:** Separating the Firmament
**CTF:** Pointer Overflow CTF 2024
**Points:** Reverse 300
**Result:** Solved

**Flag:**

~~~text
poctf{uwsp_7h3_w0rlB5_4_57463}
~~~

---

## 1. Challenge Overview

A binary that encrypts a flag using a reconstructed key and XOR encryption. The user must provide the correct 22-character key to decrypt the flag. The key can be recovered by reversing the `reconstruct_key()` function rather than brute-forcing the 22-character keyspace.

**Files:** `Reverse300-1` (ELF binary)

---

## 2. Program Flow Analysis

The `main()` function:

1. Prompts for a 22-character key
2. Validates length (must be exactly 22)
3. Calls `reconstruct_key()` to generate the expected key
4. Compares user input against the reconstructed key
5. If matched, calls `decrypt_flag()` to reveal the flag

---

## 3. Key Reconstruction Analysis

The `reconstruct_key()` function builds the key in four segments through XOR operations:

**Segment 1** (bytes 0-4): `"tsxvg"` XORed with `0x10`
**Segment 2** (bytes 5-9): `0x3d3b1f08` + `0x2f` XORed with `0x5A`
**Segment 3** (bytes 10-14): `0x1186a70` + `0x50` XORed with `0x20`
**Segment 4** (bytes 15-21): `0x734d1665` XORed with `0x30` (first 5 bytes) then `0x00` (last 2 bytes)

---

## 4. Decrypt Flag Logic

The `decrypt_flag()` function:

- Stores an encrypted flag as 32 bytes of predefined ciphertext
- Calls `xor_encrypt()` which performs cyclic XOR: `plaintext[i] = ciphertext[i] ^ key[i % key_len]`
- Prints the decrypted result

---

## 5. Automated Solution

The [Python script](scripts/script.py) reconstructs the key by replicating the XOR operations, then decrypts the flag using the same cyclic XOR:

~~~text
poctf{uwsp_7h3_w0rlB5_4_57463}
~~~

---

## Lessons Learned

| # | Lesson | Detail |
|---|--------|--------|
| 1 | Key reconstruction functions expose the key | Reversing the builder is faster than brute force |
| 2 | Cyclic XOR is symmetric | The same function encrypts and decrypts |
| 3 | Multi-segment key construction adds complexity but not security | Each segment can be reversed independently |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID | Context |
|---|---|---|---|
| Defense Evasion | Obfuscated Files or Information | T1027 | Flag encrypted with XOR using a reconstructed key |
| Defense Evasion | Deobfuscate/Decode Files or Information | T1140 | Reversed key reconstruction and XOR decryption |
| Credential Access | Unsecured Credentials: Credentials in Files | T1552.001 | Key material derivable from embedded constants |

> **CWE-321:** Use of Hard-coded Cryptographic Key. Key reconstructed from static values embedded in the binary.
> **CWE-327:** Use of a Broken or Risky Cryptographic Algorithm. Cyclic XOR is not a secure cipher.

---

## Remediation and Containment

### Technical Fixes

1. Use AES-GCM or ChaCha20-Poly1305 instead of cyclic XOR encryption
2. Derive keys from user input using a proper KDF (PBKDF2, Argon2), not static reconstruction
3. Do not embed key material or reconstruction logic in client binaries
4. Implement server-side key validation with challenge-response

### MITRE D3FEND Countermeasures

- **D3-FE (File Encryption):** use authenticated encryption with proper key management
- **D3-CH (Credential Hardening):** derive keys from secure external sources
- **D3-OBF (Obfuscation):** apply code obfuscation to key reconstruction logic if client-side is required

### NIST CSF 2.0

- **Protect (PR.DS):** use approved encryption algorithms with secure key management
- **Detect (DE.CM):** detect reverse engineering attempts through anti-tamper mechanisms
- **Respond (RS.MI):** rotate encryption keys if binary analysis is detected

### NIST SP 800-53 Rev. 5

- **SC-12 (Cryptographic Key Establishment and Management):** use secure key derivation, not static reconstruction
- **SC-13 (Cryptographic Protection):** use FIPS-approved algorithms for data encryption
- **SA-11 (Developer Testing and Evaluation):** test key derivation logic for recoverability

### C2M2

- **THREAT-3:** include key extraction from binaries in penetration testing scope
- **ACCESS-3:** audit all key generation and storage mechanisms for static recovery risk

---

Thanks guys!! (❍ᴥ❍ʋ)

---

The world's a stage, and this key reconstruction function is center spotlight. When the binary builds its own key from XOR operations on constants, reversing is just math homework.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

> **Reference:** Adapted from [shivang1209-dot/CTF-Writeups](https://github.com/shivang1209-dot/CTF-Writeups). Original scripts credited to the author.
