# For All the World to See

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2024 |
| **Challenge** | For All the World to See |
| **Category** | Cryptography |
| **Difficulty** | Easy |
| **Points** | 100 |
| **Status** | Solved |

---

## Challenge Overview

A ciphertext produced by a substitution cipher must be decoded to reveal a passphrase. That passphrase unlocks a VeraCrypt encrypted volume containing the flag file.

---

## Objective

Break the substitution cipher, recover the passphrase, mount the VeraCrypt volume, and extract the flag.

---

## Methodology

### Step 1: Identify the Cipher

The provided ciphertext shows letter-frequency patterns consistent with a monoalphabetic substitution cipher. No polyalphabetic indicators (e.g., repeated key-length patterns) are present.

### Step 2: Frequency Analysis

Using frequency analysis on the ciphertext and comparing against standard English letter distribution:

```
E (12.7%) → most frequent ciphertext letter
T (9.1%)  → second most frequent
A (8.2%)  → third most frequent
...
```

Online tools such as quipqiup or dCode's substitution solver accelerate the process.

### Step 3: Decode the Substitution

After mapping all letters, the plaintext reveals a readable English sentence containing the passphrase for the encrypted volume.

### Step 4: Mount the VeraCrypt Volume

```bash
veracrypt --text --mount volume.tc /mnt/ctf
# Enter the recovered passphrase when prompted
cat /mnt/ctf/flag.txt
```

### Step 5: Capture the Flag

The mounted volume contains a text file with the flag in `poctf{uwsp_...}` format.

---

## Lessons Learned

| # | Insight |
|---|---------|
| 1 | Monoalphabetic substitution ciphers are vulnerable to frequency analysis |
| 2 | Multi-stage challenges combine different skills: cryptanalysis and disk forensics |
| 3 | VeraCrypt volumes require the exact passphrase, including case and special characters |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | Description |
|--------|-----------|-------------|
| Defense Evasion | T1027 - Obfuscated Files or Information | Passphrase concealed through substitution cipher |
| Collection | T1005 - Data from Local System | Flag stored inside an encrypted container |

---

## Remediation

### Technical Fixes

- Monoalphabetic substitution provides no real security; use AES-256 or ChaCha20 for encryption.
- VeraCrypt with a strong passphrase is robust, but the passphrase generation method must also be secure.
- Avoid deriving encryption keys from easily reversible encodings.

### MITRE D3FEND

| ID | Technique |
|----|-----------|
| D3-FCA | File Content Analysis: inspect encrypted containers for hidden data |

### NIST CSF 2.0

| Function | Category | Action |
|----------|----------|--------|
| Protect | PR.DS | Use strong, modern encryption for data at rest |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---------|-------------|
| SC-13 | Cryptographic Protection: use FIPS-validated algorithms |
| SC-28 | Protection of Information at Rest: encrypt sensitive stored data |

### C2M2

| Practice | Description |
|----------|-------------|
| PROTECT | Apply encryption with keys derived from strong passphrases or key management systems |

### CWE

| ID | Description |
|----|-------------|
| CWE-327 | Use of a Broken or Risky Cryptographic Algorithm |
| CWE-328 | Use of Weak Hash |

---

## References

- [yocchin POCTF 2024 Writeup](https://yocchin.hatenablog.com/entry/2025/01/23/140330) (original reference)
- [VeraCrypt Documentation](https://veracrypt.fr/en/Documentation.html)
- [Pointer Overflow CTF](https://pointeroverflowctf.com/)

---

Thanks guys!! (❍ᴥ❍ʋ)

A substitution cipher guarding a VeraCrypt vault: two layers of secrecy, but only one with real teeth. Frequency analysis for the win!

[![Instagram](https://img.shields.io/badge/Instagram-%23E4405F.svg?style=for-the-badge&logo=Instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/linkedin-%230077B5.svg?style=for-the-badge&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/X-%23000000.svg?style=for-the-badge&logo=X&logoColor=white)](https://x.com/mrhenrike)
