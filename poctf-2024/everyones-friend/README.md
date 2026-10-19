# Everyone's Friend

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2024 |
| **Challenge** | Everyone's Friend |
| **Category** | Cryptography |
| **Difficulty** | Medium |
| **Points** | 200 |
| **Status** | Solved |

---

## Challenge Overview

A textbook RSA challenge with all parameters provided: small primes `p` and `q`, public exponent `e`, and ciphertext in hexadecimal. The title "Everyone's Friend" references RSA being a well-known, commonly taught algorithm.

**Given parameters:**

```
p = 61
q = 53
n = 3233
e = 17
c = 264,889,119,374,559,357,870,453,4ce,264,77,a5d,87a,170,77,87a,b5a,a5d,119,87a,87a,b5a,2b2,170,96c,70a,77,7aa,870,b5a,6ed,170,5ec
```

---

## Objective

Compute the RSA private key from the given parameters and decrypt the hex-encoded ciphertext.

---

## Methodology

### Step 1: Compute the Private Key

Calculate Euler's totient:

```
phi(n) = (p - 1) * (q - 1) = 60 * 52 = 3120
```

Find the modular inverse of `e` modulo `phi(n)` using the Extended Euclidean Algorithm:

```
d = e^(-1) mod phi(n)
d = 17^(-1) mod 3120
d = 2753
```

### Step 2: Decrypt Each Block

Each hex value in the ciphertext represents an independently encrypted character. Convert hex to decimal, then apply RSA decryption:

```
m = c^d mod n
```

For example:
- `264` (hex) = `612` (dec) -> `pow(612, 2753, 3233)` = `112` -> `'p'`
- `889` (hex) = `2185` (dec) -> `pow(2185, 2753, 3233)` = `111` -> `'o'`

### Step 3: Automated Decryption

The [decrypt.py](scripts/decrypt.py) script automates the process:

```python
d = 2753
n = 3233
ciphertext_hex = ["264","889","119","374","559","357","870","453","4ce",...]
plaintext = [chr(pow(int(c, 16), d, n)) for c in ciphertext_hex]
```

Running the script produces the complete flag.

---

## Flag

```
poctf{uwsp_7h3_h17chh1k3r5_6u1d3}
```

---

## Lessons Learned

| # | Insight |
|---|---------|
| 1 | RSA with small primes is trivially breakable; factoring `n = 3233` is instant |
| 2 | When all RSA parameters are given, computing `d` is straightforward algebra |
| 3 | Hex-encoded ciphertext blocks map 1:1 to plaintext characters in textbook RSA |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | Description |
|--------|-----------|-------------|
| Credential Access | T1552.004 - Unsecured Credentials: Private Keys | Weak key generation enables private key recovery |
| Defense Evasion | T1140 - Deobfuscate/Decode Files or Information | Decrypting RSA-encrypted content |

---

## Remediation

### Technical Fixes

- RSA key sizes must be at least 2048 bits (NIST recommendation). Keys with small primes like 61 and 53 are trivially factorable.
- Never use textbook RSA (no padding). Use OAEP padding (PKCS#1 v2.2) for encryption.
- Prefer ephemeral key exchange (ECDHE) with authenticated encryption over RSA for modern applications.

### MITRE D3FEND

| ID | Technique |
|----|-----------|
| D3-PSEP | Public Key Security Enhancement Process |
| D3-CH | Certificate Hygiene: ensure proper key sizes |

### NIST CSF 2.0

| Function | Category | Action |
|----------|----------|--------|
| Protect | PR.DS | Enforce minimum 2048-bit RSA keys across all systems |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---------|-------------|
| SC-12 | Cryptographic Key Establishment and Management |
| SC-13 | Cryptographic Protection |

### C2M2

| Practice | Description |
|----------|-------------|
| PROTECT | Enforce cryptographic standards and key management policies |

### CWE

| ID | Description |
|----|-------------|
| CWE-326 | Inadequate Encryption Strength |
| CWE-327 | Use of a Broken or Risky Cryptographic Algorithm |

---

## References

- [shivang1209-dot POCTF 2024 Writeups](https://github.com/shivang1209-dot/shivang1209-dot) (original reference)
- [RSA Algorithm (Wikipedia)](https://en.wikipedia.org/wiki/RSA_(cryptosystem))
- [Pointer Overflow CTF](https://pointeroverflowctf.com/)

---

Thanks guys!! (❍ᴥ❍ʋ)

RSA com primos de dois digitos: o classico dos classicos em CTF. A beleza esta na simplicidade!

[![Instagram](https://img.shields.io/badge/Instagram-%23E4405F.svg?style=for-the-badge&logo=Instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/linkedin-%230077B5.svg?style=for-the-badge&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/X-%23000000.svg?style=for-the-badge&logo=X&logoColor=white)](https://x.com/mrhenrike)
