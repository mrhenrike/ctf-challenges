# Rechance Meeting

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2024 |
| **Category** | Unknown |
| **Difficulty** | Unknown |
| **Points** | N/A |
| **Flag** | `poctf{uwsp_w3_c4n_r3m3mb3r_17}` |
| **Status** | Solved |

---

## Challenge Overview

A password-protected ZIP archive contains the flag. The password is formed by concatenating two words from a provided wordlist. A custom hash function is also provided. The challenge description hints at birthdays, pointing toward a **birthday attack** to find hash collisions.

**Files provided:**
- `Crypto200-2_flag.zip` (password-protected archive)
- `Crypto200-2_hashfunc.py` (custom hash function)
- `Crypto200-2_words.txt` (wordlist)

---

## Objective

Find two words in the wordlist that produce a hash collision using the provided hash function, concatenate them, and use the result as the ZIP password.

---

## Methodology

### Step 1: Understand the Hint

The challenge description emphasizes birthdays and probability:

> "You'd think that there would be an equal chance of any given day being someone's birthday"

This is a direct reference to the **birthday paradox/attack**: finding two inputs that hash to the same value is much easier than finding a specific preimage.

### Step 2: Generate Hashes for All Words

Using the provided `hashfunc.py`, compute hashes for every word in the wordlist and store the results.

### Step 3: Find Collisions

The [collisions.py](scripts/collisions.py) script reads the hash/word pairs and identifies all cases where two distinct words share the same hash value.

```python
# Core logic: group words by hash, find duplicates
for hash_value, words in hash_dict.items():
    if len(words) > 1:
        for word1, word2 in combinations(words, 2):
            writer.writerow([word1, word2, hash_value])
```

This detected **78 hash collisions** in the wordlist.

### Step 4: Test Collision Pairs as Passwords

Each pair of colliding words was concatenated (both orderings) and tested against the ZIP archive. After testing with a corrected wordlist (the original had a bug confirmed by the challenge author), the correct pair was found.

**Password:** `Moeso-gothicTarzanish`

### Step 5: Extract the Flag

```bash
7z x Crypto200-2_flag.zip -pMoeso-gothicTarzanish
```

---

## Flag

```
poctf{uwsp_w3_c4n_r3m3mb3r_17}
```

---

## Lessons Learned

| # | Insight |
|---|---------|
| 1 | The birthday paradox makes collision-finding feasible even for large wordlists |
| 2 | Custom hash functions are often weak; always test for collisions before trusting them |
| 3 | Challenge descriptions frequently contain the key insight (birthdays = birthday attack) |
| 4 | When brute force is infeasible, look for mathematical shortcuts |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | Description |
|--------|-----------|-------------|
| Credential Access | T1110.002 - Brute Force: Password Cracking | Testing collision-derived passwords against the archive |
| Defense Evasion | T1140 - Deobfuscate/Decode Files or Information | Extracting encrypted archive contents |

---

## Remediation

### Technical Fixes

- Custom hash functions are prone to collisions. Use proven cryptographic hashes (SHA-256, SHA-3) for integrity verification.
- Password-protected ZIP archives should use AES-256 encryption (not the legacy ZipCrypto).
- Archive passwords should be randomly generated with high entropy, not derived from wordlists.

### MITRE D3FEND

| ID | Technique |
|----|-----------|
| D3-HBPI | Hash-Based Password Integrity |
| D3-FE | File Encryption with strong algorithms |

### NIST CSF 2.0

| Function | Category | Action |
|----------|----------|--------|
| Protect | PR.DS | Use strong, collision-resistant hash functions |
| Protect | PR.AC | Enforce high-entropy passwords for encrypted archives |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---------|-------------|
| IA-5 | Authenticator Management |
| SC-13 | Cryptographic Protection |

### C2M2

| Practice | Description |
|----------|-------------|
| PROTECT | Validate cryptographic implementations against known attack classes |

### CWE

| ID | Description |
|----|-------------|
| CWE-328 | Use of Weak Hash |
| CWE-916 | Use of Password Hash With Insufficient Computational Effort |

---

## References

- [shivang1209-dot POCTF 2024 Writeups](https://github.com/shivang1209-dot/shivang1209-dot) (original reference)
- [Birthday Attack (Wikipedia)](https://en.wikipedia.org/wiki/Birthday_attack)
- [Pointer Overflow CTF](https://pointeroverflowctf.com/)

---

Thanks guys!! (❍ᴥ❍ʋ)

O paradoxo do aniversario nunca decepciona. Quando a matematica trabalha a seu favor, ate 370 mil palavras se curvam!

[![Instagram](https://img.shields.io/badge/Instagram-%23E4405F.svg?style=for-the-badge&logo=Instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/linkedin-%230077B5.svg?style=for-the-badge&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/X-%23000000.svg?style=for-the-badge&logo=X&logoColor=white)](https://x.com/mrhenrike)
