# Honor the Carneia

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

A service encrypts user-supplied plaintext using AES-CBC and returns the ciphertext. By exploiting the padding oracle vulnerability, it is possible to decrypt the target ciphertext block by block. The first block requires knowledge of a known phrase to reconstruct.

---

## Objective

Exploit the padding oracle to decrypt the ciphertext, reconstruct the first block from a known phrase, and recover the flag.

---

## Methodology

### Step 1: Identify the Oracle

Sending modified ciphertext to the service produces different error responses depending on whether the padding is valid:

- **Valid padding:** normal response or specific message
- **Invalid padding:** distinct error message or HTTP status

This differential response constitutes a padding oracle.

### Step 2: Understand AES-CBC Decryption

In CBC mode, each plaintext block depends on the previous ciphertext block:

```
P[i] = Decrypt(C[i]) XOR C[i-1]
```

By manipulating `C[i-1]`, an attacker can probe the intermediate decryption state byte by byte.

### Step 3: Byte-by-Byte Recovery

For each byte position (from the last byte backward):

1. Set the target padding value (0x01 for last byte, 0x02 for second-to-last, etc.)
2. Brute-force the corresponding byte of `C[i-1]` until the oracle reports valid padding
3. XOR the successful value with the padding byte to recover the intermediate state
4. XOR with the original `C[i-1]` byte to get the plaintext byte

```python
for byte_pos in range(15, -1, -1):
    pad_val = 16 - byte_pos
    for guess in range(256):
        modified_block[byte_pos] = guess
        if oracle_returns_valid(modified_block + target_block):
            intermediate[byte_pos] = guess ^ pad_val
            plaintext[byte_pos] = intermediate[byte_pos] ^ original_prev[byte_pos]
            break
```

### Step 4: Reconstruct the First Block

The first plaintext block depends on the IV: `P[0] = Decrypt(C[0]) XOR IV`. The challenge hints at a known phrase that constitutes the first block content. Using this known plaintext, the first block is recovered by XOR with the intermediate state.

### Step 5: Assemble the Flag

Concatenating all recovered plaintext blocks and stripping PKCS#7 padding yields the flag in `poctf{uwsp_...}` format.

---

## Lessons Learned

| # | Insight |
|---|---------|
| 1 | Padding oracle attacks turn a minor information leak into full plaintext recovery |
| 2 | AES-CBC without authenticated encryption (MAC) is vulnerable to ciphertext manipulation |
| 3 | Known plaintext for the first block reduces the attack complexity significantly |
| 4 | Each block requires up to 256 x 16 = 4,096 oracle queries in the worst case |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | Description |
|--------|-----------|-------------|
| Credential Access | T1557 - Adversary-in-the-Middle | Manipulating ciphertext between client and server |
| Collection | T1557 - Adversary-in-the-Middle | Recovering plaintext through oracle responses |

---

## Remediation

### Technical Fixes

- Use authenticated encryption modes (AES-GCM, ChaCha20-Poly1305) instead of unauthenticated CBC.
- If CBC must be used, apply HMAC-then-encrypt or encrypt-then-MAC to detect ciphertext tampering.
- Return identical error responses for all decryption failures to eliminate the oracle.

### MITRE D3FEND

| ID | Technique |
|----|-----------|
| D3-MAN | Message Authentication: verify ciphertext integrity before decryption |

### NIST CSF 2.0

| Function | Category | Action |
|----------|----------|--------|
| Protect | PR.DS | Use AEAD ciphers to ensure both confidentiality and integrity |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---------|-------------|
| SC-13 | Cryptographic Protection: use approved authenticated encryption |
| SC-8 | Transmission Confidentiality and Integrity: protect data in transit |

### C2M2

| Practice | Description |
|----------|-------------|
| PROTECT | Enforce authenticated encryption for all sensitive data channels |

### CWE

| ID | Description |
|----|-------------|
| CWE-209 | Generation of Error Message Containing Sensitive Information |
| CWE-347 | Improper Verification of Cryptographic Signature |
| CWE-649 | Reliance on Obfuscation or Protection Mechanism that is not Constant-Time |

---

## References

- [yocchin POCTF 2024 Writeup](https://yocchin.hatenablog.com/entry/2025/01/23/140330) (original reference)
- [Padding Oracle Attack (Wikipedia)](https://en.wikipedia.org/wiki/Padding_oracle_attack)
- [Pointer Overflow CTF](https://pointeroverflowctf.com/)

---

Thanks guys!! (❍ᴥ❍ʋ)

The Spartans honored the Carneia with discipline; we honored this challenge with patience, one byte at a time. Padding oracle conquered!

[![Instagram](https://img.shields.io/badge/Instagram-%23E4405F.svg?style=for-the-badge&logo=Instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/linkedin-%230077B5.svg?style=for-the-badge&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/X-%23000000.svg?style=for-the-badge&logo=X&logoColor=white)](https://x.com/mrhenrike)
