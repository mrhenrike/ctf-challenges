# Return of the Mack

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2024 |
| **Category** | Relevance |
| **Difficulty** | Unknown |
| **Points** | N/A |
| **Flag** | `poctf{uwsp_h34r7_0f_7h3_m4773r}` |
| **Status** | Solved |

---

## Challenge Overview

An RSA decryption challenge themed around the TV show "Archer" and "Sealab 2021." A password-protected RSA private key must be cracked (6-character password, A-Z and 0-9), then used to decrypt an encrypted flag file.

## Objective

Brute-force the passphrase on an RSA private key, then use the decrypted key to decrypt the ciphertext file containing the flag.

## Methodology

### Step 1: Understand the Context

The description references:
- Sterling Archer (code name: Duchess) from the animated series "Archer"
- Sealab 2021 (another Adult Swim show)
- A secret transmission between Mr. Reed and Dr. P. Haze
- Password constraints: **6 characters, A-Z and 0-9 only**

### Step 2: Crack the RSA Key Passphrase

The private key file `keyfile.pem` is protected by a 6-character alphanumeric passphrase.

Given the constraints (uppercase letters and digits, 6 characters), brute-force is feasible:

```bash
# Using john to extract and crack the PEM passphrase
ssh2john keyfile.pem > pem_hash.txt
john --mask='?u?u?u?d?d?d' pem_hash.txt
```

Password: `934TXS`

### Step 3: Decrypt the RSA Key

```bash
openssl rsa -in keyfile.pem -out decrypted_key.pem
# Enter passphrase: 934TXS
```

### Step 4: Decrypt the Flag

```bash
openssl rsautl -decrypt -inkey decrypted_key.pem -in Crack300-2_flag.txt.enc -out decrypted_message.txt
cat decrypted_message.txt
```

```
Flag: poctf{uwsp_h34r7_0f_7h3_m4773r}
```

## Lessons Learned

| # | Lesson | Details |
|---|--------|---------|
| 1 | Short key passphrases are crackable | 6-character alphanumeric passphrase is within brute-force range |
| 2 | Mask attacks | When the password format is known (length, charset), mask attacks are far more efficient than wordlists |
| 3 | RSA key protection | A strong passphrase is the only defense for a private key file at rest |
| 4 | Two-step decryption | Crack the key passphrase first, then use the key to decrypt the actual data |

## MITRE ATT&CK Mapping

| Tactic | Technique | ID | Details |
|--------|-----------|-----|---------|
| Credential Access | Brute Force: Password Cracking | T1110.002 | Brute-forcing 6-char PEM passphrase |
| Credential Access | Unsecured Credentials: Private Keys | T1552.004 | Recovering RSA private key |
| Collection | Data from Local System | T1005 | Decrypting local ciphertext file |

## Remediation

### Technical Fixes

- Use passphrases of 16+ characters for RSA private keys
- Store private keys in HSMs or secure key vaults, not as PEM files
- Consider certificate-based authentication over password-protected keys

### MITRE D3FEND

| Technique | ID | How it applies |
|-----------|-----|----------------|
| Credential Hardening | D3-CH | Enforce long, complex passphrases for cryptographic keys |
| Decoy Environment | D3-DE | Use decoy keys to detect unauthorized access attempts |

### NIST CSF 2.0

| Function | Category | Relevance |
|----------|----------|-----------|
| Protect (PR) | Data Security (PR.DS) | Protect private keys with strong access controls |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---------|-------------|
| SC-12 | Cryptographic Key Establishment and Management |
| SC-17 | Public Key Infrastructure Certificates |
| IA-5 | Authenticator Management: strong passphrases for key protection |

### C2M2

| Practice | Domain | Relevance |
|----------|--------|-----------|
| Cybersecurity Architecture | ARCHITECTURE | Proper key management infrastructure |

### CWE

| CWE ID | Name | Relevance |
|--------|------|-----------|
| CWE-326 | Inadequate Encryption Strength | Short passphrase on RSA private key |
| CWE-522 | Insufficiently Protected Credentials | Private key file with weak passphrase |

## References

- [UWSP Pointer Overflow CTF 2024](https://pointeroverflowctf.com)
- [OpenSSL RSA Key Management](https://www.openssl.org/docs/man1.1.1/man1/rsa.html)
- Based on solve approach from [shivang1209-dot](https://github.com/shivang1209-dot/CTF-Writeup)

---

Thanks guys!! (❍ᴥ❍ʋ)

Private keys are only as safe as their passphrases. Six characters is a speed bump, not a wall.

[![Instagram](https://img.shields.io/badge/Instagram-%23E4405F.svg?style=for-the-badge&logo=Instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/linkedin-%230077B5.svg?style=for-the-badge&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/X-%23000000.svg?style=for-the-badge&logo=X&logoColor=white)](https://x.com/mrhenrike)
