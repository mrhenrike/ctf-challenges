# A Question of Perspective

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2024 |
| **Category** | Unknown |
| **Difficulty** | Unknown |
| **Points** | N/A |
| **Flag** | `poctf{dynamic}` |

```python
known = b'poctf{uwsp_'
encrypted = [0x23, 0x59, 0x86, 0x1e, 0x60, 0xcf, 0xdc, 0x4e, 0x6a, 0x0b, 0x0c]
key_bits = bytes(a ^ b for a, b in zip(known, encrypted))
```

This reveals the first 88 bits of the repeating key.

### Step 3: Determine Key Length and Pattern

The total key (confirmed + resolved bits) is at most 57 bits. The encrypted message is 256 bits. The key repeats to match the ciphertext length. After 80 bits the key pattern wraps, confirming the repetition structure.

### Step 4: Full Decryption

Extend the key to match the ciphertext length and XOR:

```python
full_key = (key_bytes * ((len(ciphertext) // len(key_bytes)) + 1))[:len(ciphertext)]
plaintext = bytes(a ^ b for a, b in zip(ciphertext, full_key))
```

---

## Flag

```
poctf{uwsp_f10w3r5_f0r_41g3rn0n}` |

```python
known = b'poctf{uwsp_'
encrypted = [0x23, 0x59, 0x86, 0x1e, 0x60, 0xcf, 0xdc, 0x4e, 0x6a, 0x0b, 0x0c]
key_bits = bytes(a ^ b for a, b in zip(known, encrypted))
```

This reveals the first 88 bits of the repeating key.

### Step 3: Determine Key Length and Pattern

The total key (confirmed + resolved bits) is at most 57 bits. The encrypted message is 256 bits. The key repeats to match the ciphertext length. After 80 bits the key pattern wraps, confirming the repetition structure.

### Step 4: Full Decryption

Extend the key to match the ciphertext length and XOR:

```python
full_key = (key_bytes * ((len(ciphertext) // len(key_bytes)) + 1))[:len(ciphertext)]
plaintext = bytes(a ^ b for a, b in zip(ciphertext, full_key))
```

---

## Flag

```
poctf{uwsp_f10w3r5_f0r_41g3rn0n}` |
| **Status** | Solved |

---

## Challenge Overview

A quantum cryptography challenge based on the BB84 protocol. We are given intercepted qubits, measurement bases, partial measurements (every third is corrupted by eavesdropping), and an AES-encrypted message. The seed space is restricted to integers 1-100.

**Provided data:**
- 80 qubits, 80 bases (R/D), 80 measurements (every 3rd is `?`)
- 32-byte encrypted message (hex)

---

## Objective

Reconstruct the BB84 shared key by resolving the corrupted measurements, then XOR-decrypt the message.

---

## Methodology

### Step 1: Identify Known and Unknown Bits

Align the known measurements with qubits. Positions where Alice's base matches Bob's base and the measurement is not `?` contribute confirmed key bits. Every third position is unknown (`?`).

Confirmed bits (with `?` retained):

```
01?0?11?1?0?0?10?0?01?0?1????11?10?0??0?01?0?0??0?01?11?1
```

The 26 `?` values correspond to every third qubit sent by Alice:

```
[0, 0, 0, 1, 1, 1, 0, 1, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 1, 1, 0]
```

### Step 2: Known Plaintext Attack

Since the encrypted message starts with `poctf{uwsp_` (known plaintext), convert it to binary and XOR with the first portion of the ciphertext to recover key bits:

```python
known = b'poctf{uwsp_'
encrypted = [0x23, 0x59, 0x86, 0x1e, 0x60, 0xcf, 0xdc, 0x4e, 0x6a, 0x0b, 0x0c]
key_bits = bytes(a ^ b for a, b in zip(known, encrypted))
```

This reveals the first 88 bits of the repeating key.

### Step 3: Determine Key Length and Pattern

The total key (confirmed + resolved bits) is at most 57 bits. The encrypted message is 256 bits. The key repeats to match the ciphertext length. After 80 bits the key pattern wraps, confirming the repetition structure.

### Step 4: Full Decryption

Extend the key to match the ciphertext length and XOR:

```python
full_key = (key_bytes * ((len(ciphertext) // len(key_bytes)) + 1))[:len(ciphertext)]
plaintext = bytes(a ^ b for a, b in zip(ciphertext, full_key))
```

---

## Flag

```
poctf{uwsp_f10w3r5_f0r_41g3rn0n}
```

---

## Lessons Learned

| # | Insight |
|---|---------|
| 1 | BB84 protocol weaknesses arise when eavesdropping corrupts measurements predictably |
| 2 | Known plaintext attacks remain devastating against XOR-based encryption, even in quantum contexts |
| 3 | Restricted seed spaces (1-100) make brute force feasible as a fallback |
| 4 | Understanding the key repetition pattern is crucial for full decryption |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | Description |
|--------|-----------|-------------|
| Collection | T1557 - Adversary-in-the-Middle | Intercepting quantum key distribution exchange |
| Credential Access | T1110 - Brute Force | Small seed space enables exhaustive key search |

---

## Remediation

### Technical Fixes

- BB84 implementations must detect eavesdropping through error rate analysis on the quantum channel (QBER threshold typically ~11%).
- Never use a small, restricted seed space for cryptographic key generation; use cryptographically secure random number generators.
- XOR with a repeating key shorter than the message is vulnerable; use proper authenticated encryption (AES-GCM).

### MITRE D3FEND

| ID | Technique |
|----|-----------|
| D3-EAL | Encrypted Authentication Lifecycle |
| D3-NTA | Network Traffic Analysis: detect anomalous key exchange patterns |

### NIST CSF 2.0

| Function | Category | Action |
|----------|----------|--------|
| Protect | PR.DS | Use quantum-resistant key exchange with proper error detection |
| Detect | DE.AE | Monitor for anomalous error rates in quantum channels |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---------|-------------|
| SC-12 | Cryptographic Key Establishment and Management |
| SC-13 | Cryptographic Protection |

### C2M2

| Practice | Description |
|----------|-------------|
| PROTECT | Evaluate and prepare for post-quantum cryptography migration |

### CWE

| ID | Description |
|----|-------------|
| CWE-330 | Use of Insufficiently Random Values |
| CWE-327 | Use of a Broken or Risky Cryptographic Algorithm |

---

## References

- [shivang1209-dot POCTF 2024 Writeups](https://github.com/shivang1209-dot/shivang1209-dot) (original reference)
- [BB84 Protocol (Wikipedia)](https://en.wikipedia.org/wiki/BB84)
- [Pointer Overflow CTF](https://pointeroverflowctf.com/)

---

Thanks guys!! (❍ᴥ❍ʋ)

Criptografia quantica em CTF: mesmo com qubits e bases, a boa e velha analise de criptanalise classica resolve. O futuro ja chegou, mas o XOR continua fragil!

[![Instagram](https://img.shields.io/badge/Instagram-%23E4405F.svg?style=for-the-badge&logo=Instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/linkedin-%230077B5.svg?style=for-the-badge&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/X-%23000000.svg?style=for-the-badge&logo=X&logoColor=white)](https://x.com/mrhenrike)
