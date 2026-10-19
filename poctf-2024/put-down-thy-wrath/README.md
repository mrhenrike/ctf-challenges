# Put Down Thy Wrath

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2024 |
| **Challenge** | Put Down Thy Wrath |
| **Category** | Cryptography |
| **Difficulty** | Hard |
| **Points** | 300 |
| **Status** | Solved |

---

## Challenge Overview

The challenge provides a ciphertext, a public key, and an encryption script implementing a "homomorphic encryption" scheme. The goal is to analyze the script and decrypt the message. However, the script itself contains a critical flaw.

**Provided data:**
- Ciphertext (hex): `79,74,3f,0f,5a,27,21,3a,36,48,64,51,64,0f,79,7e,1a,64,64,03,33,0f,64,64,57,21,27,3f,0f,7e,64,79,1a,64,2c`
- Public Key: `3233`
- Script: [homomorphic_encryption.py](scripts/homomorphic_encryption.py)

---

## Objective

Analyze the provided encryption script, identify weaknesses, and recover the flag.

---

## Methodology

### Step 1: Examine the Encryption Script

Upon careful inspection of the `homomorphic_encryption.py` script, a critical implementation error was discovered: the flag was **directly embedded in the source code** as a plaintext string.

### Step 2: Extract the Flag

The flag was recovered directly from the script without any cryptanalysis required. The author accidentally left the plaintext flag in the encryption code, making the cryptographic analysis unnecessary.

This is a realistic scenario: source code leaking secrets is a common vulnerability in production systems.

---

## Flag

```
poctf{uwsp_T3mp357_4nd_7urnm01l}
```

---

## Lessons Learned

| # | Insight |
|---|---------|
| 1 | Always inspect provided source code thoroughly before attempting complex cryptanalysis |
| 2 | Hardcoded secrets in source code are a critical and common vulnerability |
| 3 | The simplest path to the flag is often the correct one |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | Description |
|--------|-----------|-------------|
| Credential Access | T1552.001 - Unsecured Credentials: Credentials in Files | Flag/secret embedded directly in source code |
| Reconnaissance | T1592.004 - Gather Victim Host Information: Client Configurations | Reviewing source code for leaked secrets |

---

## Remediation

### Technical Fixes

- Never embed secrets, keys, or sensitive data in source code. Use environment variables or secret management systems (HashiCorp Vault, AWS Secrets Manager).
- Implement pre-commit hooks with tools like `gitleaks` or `trufflehog` to catch secrets before they are committed.
- Conduct code reviews specifically targeting hardcoded credentials.

### MITRE D3FEND

| ID | Technique |
|----|-----------|
| D3-CSPP | Credential Scanning and Protection Process |
| D3-SCA | Source Code Analysis |

### NIST CSF 2.0

| Function | Category | Action |
|----------|----------|--------|
| Protect | PR.DS | Remove secrets from source code; use dedicated secret stores |
| Detect | DE.CM | Scan repositories for exposed credentials |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---------|-------------|
| IA-5 | Authenticator Management |
| SA-15 | Development Process, Standards, and Tools |

### C2M2

| Practice | Description |
|----------|-------------|
| PROTECT | Enforce secret management policies across development pipelines |

### CWE

| ID | Description |
|----|-------------|
| CWE-798 | Use of Hard-coded Credentials |
| CWE-540 | Inclusion of Sensitive Information in Source Code |

---

## References

- [shivang1209-dot POCTF 2024 Writeups](https://github.com/shivang1209-dot/shivang1209-dot) (original reference)
- [Pointer Overflow CTF](https://pointeroverflowctf.com/)

---

Thanks guys!! (❍ᴥ❍ʋ)

As vezes a flag esta ali, na cara, dentro do codigo. Antes de mergulhar na criptanalise, leia o source!

[![Instagram](https://img.shields.io/badge/Instagram-%23E4405F.svg?style=for-the-badge&logo=Instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/linkedin-%230077B5.svg?style=for-the-badge&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/X-%23000000.svg?style=for-the-badge&logo=X&logoColor=white)](https://x.com/mrhenrike)
