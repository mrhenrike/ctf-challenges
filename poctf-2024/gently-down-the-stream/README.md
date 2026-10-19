# Gently Down the Stream

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2024 |
| **Category** | Relevance |
| **Difficulty** | Unknown |
| **Points** | N/A |
| **Flag** | `poctf{dynamic}` |

## Objective

Identify the RC4 cipher, derive the encryption key using known-plaintext analysis, and decrypt the ciphertext to reveal the flag.

## Methodology

### Step 1: Identify the Cipher

The description provides a diagram and references "ABC" steps:
- **A**: "Always read up on your cipher" (repeated twice: AA)
- **B**: "Be prepared. Download a good wordlist" (twice: BB)
- **C**: "Calibrate your cracking rig" (two rigs mentioned: CC)
- **D**: "Dead chicken" (wave two dead chickens: DD)

The diagram shows an RC4 structure with KSA (Key Scheduling Algorithm) and PRGA (Pseudo-Random Generation Algorithm).

### Step 2: Known-Plaintext Attack

The ciphertext in hex:
```
71 81 13 f7 f7 b2 87 bd c6 77 68 67 25 ae fd 99 00 6e 2e 53 e6 60 50 50 ae a8 0f 9b 0a
```

Using the known flag prefix `poctf{uwsp` and XORing it with the ciphertext bytes, the key pattern `AABBCCDD` emerges. The password uses only A-Z characters as stated in the description.

### Step 3: Decrypt with Script

Using the RC4 decryption script with the derived key `AABBCCDD`:

```python
python3 scripts/decrypt.py
```

The script implements KSA + PRGA and brute-forces using an uppercase wordlist, confirming the key and decrypting the full flag.

```
Flag: poctf{uwsp_l16h7_1n_7h3_d4rk}` |
| **Status** | Solved |

---

## Challenge Overview

An RC4 stream cipher challenge where the ciphertext and a diagram of the cipher are provided. The description uses an ABC mnemonic that hints at the key format (`AABBCCDD`), and a known-plaintext attack using the flag prefix `poctf{uwsp` confirms the key structure.

## Objective

Identify the RC4 cipher, derive the encryption key using known-plaintext analysis, and decrypt the ciphertext to reveal the flag.

## Methodology

### Step 1: Identify the Cipher

The description provides a diagram and references "ABC" steps:
- **A**: "Always read up on your cipher" (repeated twice: AA)
- **B**: "Be prepared. Download a good wordlist" (twice: BB)
- **C**: "Calibrate your cracking rig" (two rigs mentioned: CC)
- **D**: "Dead chicken" (wave two dead chickens: DD)

The diagram shows an RC4 structure with KSA (Key Scheduling Algorithm) and PRGA (Pseudo-Random Generation Algorithm).

### Step 2: Known-Plaintext Attack

The ciphertext in hex:
```
71 81 13 f7 f7 b2 87 bd c6 77 68 67 25 ae fd 99 00 6e 2e 53 e6 60 50 50 ae a8 0f 9b 0a
```

Using the known flag prefix `poctf{uwsp` and XORing it with the ciphertext bytes, the key pattern `AABBCCDD` emerges. The password uses only A-Z characters as stated in the description.

### Step 3: Decrypt with Script

Using the RC4 decryption script with the derived key `AABBCCDD`:

```python
python3 scripts/decrypt.py
```

The script implements KSA + PRGA and brute-forces using an uppercase wordlist, confirming the key and decrypting the full flag.

```
Flag: poctf{uwsp_l16h7_1n_7h3_d4rk}
```

## Lessons Learned

| # | Lesson | Details |
|---|--------|---------|
| 1 | Description as key material | The ABC mnemonic directly encoded the key structure (AA, BB, CC, DD) |
| 2 | Known-plaintext attacks | The predictable flag prefix `poctf{uwsp` enables partial key recovery in stream ciphers |
| 3 | RC4 weakness | RC4's XOR-based encryption makes it trivially vulnerable when any plaintext is known |
| 4 | Diagram analysis | The provided cipher diagram confirmed the algorithm before any cracking attempt |

## MITRE ATT&CK Mapping

| Tactic | Technique | ID | Details |
|--------|-----------|-----|---------|
| Credential Access | Brute Force: Password Cracking | T1110.002 | Brute-force of RC4 key space |
| Defense Evasion | Obfuscated Files or Information | T1027 | Flag encrypted with RC4 stream cipher |
| Defense Evasion | Deobfuscate/Decode Files or Information | T1140 | Decrypting RC4 ciphertext with recovered key |

## Remediation

### Technical Fixes

- RC4 is deprecated; use AES-GCM or ChaCha20-Poly1305 for symmetric encryption
- Never use predictable or short keys for encryption
- Avoid patterns in key generation (repeated character groups)

### MITRE D3FEND

| Technique | ID | How it applies |
|-----------|-----|----------------|
| File Encryption | D3-FE | Use modern AEAD ciphers instead of RC4 |
| Credential Hardening | D3-CH | Generate cryptographically random keys |

### NIST CSF 2.0

| Function | Category | Relevance |
|----------|----------|-----------|
| Protect (PR) | Data Security (PR.DS) | Use approved cryptographic algorithms for data protection |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---------|-------------|
| SC-12 | Cryptographic Key Establishment and Management |
| SC-13 | Cryptographic Protection: use FIPS-validated algorithms |

### C2M2

| Practice | Domain | Relevance |
|----------|--------|-----------|
| Cybersecurity Architecture | ARCHITECTURE | Select modern, vetted cryptographic primitives |

### CWE

| CWE ID | Name | Relevance |
|--------|------|-----------|
| CWE-327 | Use of a Broken or Risky Cryptographic Algorithm | RC4 is considered broken |
| CWE-329 | Generation of Predictable IV/Nonce | Key structure was predictable from description |

## References

- [UWSP Pointer Overflow CTF 2024](https://pointeroverflowctf.com)
- [RC4 Cipher (Wikipedia)](https://en.wikipedia.org/wiki/RC4)
- Based on solve approach from [shivang1209-dot](https://github.com/shivang1209-dot/CTF-Writeup)

---

Thanks guys!! (❍ᴥ❍ʋ)

Stream ciphers are only as strong as their keys. When the key is embedded in the challenge description, the cipher becomes a formality.

[![Instagram](https://img.shields.io/badge/Instagram-%23E4405F.svg?style=for-the-badge&logo=Instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/linkedin-%230077B5.svg?style=for-the-badge&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/X-%23000000.svg?style=for-the-badge&logo=X&logoColor=white)](https://x.com/mrhenrike)
