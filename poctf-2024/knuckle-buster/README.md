# Knuckle Buster

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2024 |
| **Challenge** | Knuckle Buster |
| **Category** | Cryptography |
| **Difficulty** | Medium |
| **Points** | 200 |
| **Status** | Solved |

---

## Challenge Overview

Alice and Bob communicate using the Diffie-Hellman key exchange protocol. We are provided with Alice's public key, Bob's private key, and the DH parameters. An encrypted file (AES-256-CBC with SHA-256 key derivation and a prepended 16-byte IV) contains the flag.

---

## Objective

Compute the DH shared secret from the provided keys, derive the AES key, and decrypt the flag file.

---

## Methodology

### Step 1: Load the Cryptographic Material

Three PEM-encoded components are provided:
- **DH Parameters**: the prime `p` and generator `g`
- **Alice's Public Key**: her DH public value
- **Bob's Private Key**: his DH private exponent

### Step 2: Compute the Shared Secret

Using Bob's private key and Alice's public key, the Diffie-Hellman shared secret is calculated:

```
shared_secret = Alice_public ^ Bob_private mod p
```

### Step 3: Derive the AES Key

The shared secret is hashed with SHA-256 to produce a 256-bit AES key:

```python
digest = hashes.Hash(hashes.SHA256())
digest.update(shared_secret)
aes_key = digest.finalize()
```

### Step 4: Decrypt the File

The encrypted file has the IV prepended (first 16 bytes), followed by the AES-256-CBC ciphertext:

```python
iv = file_content[:16]
encrypted_flag = file_content[16:]
cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
decrypted = decryptor.update(encrypted_flag) + decryptor.finalize()
```

The [dh_decrypt.py](scripts/dh_decrypt.py) script automates this entire process.

---

## Flag

```
poctf{uwsp_f1r3_4nd_br1m570n3}
```

---

## Lessons Learned

| # | Insight |
|---|---------|
| 1 | If Bob's private key is leaked, the entire DH exchange is compromised |
| 2 | DH parameters, public keys, and the encrypted file together are sufficient for full decryption |
| 3 | AES-256-CBC with a prepended IV is a common real-world pattern |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | Description |
|--------|-----------|-------------|
| Credential Access | T1552.004 - Unsecured Credentials: Private Keys | Private key disclosure compromises the key exchange |
| Collection | T1557 - Adversary-in-the-Middle | Intercepting DH parameters enables session decryption |

---

## Remediation

### Technical Fixes

- Never expose private keys. Store them in HSMs or secure key stores with strict access controls.
- Use ephemeral Diffie-Hellman (DHE/ECDHE) to provide forward secrecy; static DH keys mean one compromise decrypts all past sessions.
- Validate DH parameters (safe primes, adequate key size) to prevent small-subgroup attacks.

### MITRE D3FEND

| ID | Technique |
|----|-----------|
| D3-PSEP | Public Key Security Enhancement Process |
| D3-SPP | Strong Password Policy (protecting key material) |

### NIST CSF 2.0

| Function | Category | Action |
|----------|----------|--------|
| Protect | PR.DS | Protect cryptographic keys with hardware security modules |
| Protect | PR.AC | Enforce least-privilege access to key material |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---------|-------------|
| SC-12 | Cryptographic Key Establishment and Management |
| SC-17 | Public Key Infrastructure Certificates |

### C2M2

| Practice | Description |
|----------|-------------|
| PROTECT | Implement key lifecycle management with rotation and secure storage |

### CWE

| ID | Description |
|----|-------------|
| CWE-321 | Use of Hard-coded Cryptographic Key |
| CWE-522 | Insufficiently Protected Credentials |

---

## References

- [shivang1209-dot POCTF 2024 Writeups](https://github.com/shivang1209-dot/shivang1209-dot) (original reference)
- [Diffie-Hellman Key Exchange (Wikipedia)](https://en.wikipedia.org/wiki/Diffie%E2%80%93Hellman_key_exchange)
- [Pointer Overflow CTF](https://pointeroverflowctf.com/)

---

Thanks guys!! (❍ᴥ❍ʋ)

Diffie-Hellman com chave privada vazada: na vida real, protejam suas chaves como se fossem ouro. No CTF, agradecemos a generosidade!

[![Instagram](https://img.shields.io/badge/Instagram-%23E4405F.svg?style=for-the-badge&logo=Instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/linkedin-%230077B5.svg?style=for-the-badge&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/X-%23000000.svg?style=for-the-badge&logo=X&logoColor=white)](https://x.com/mrhenrike)
