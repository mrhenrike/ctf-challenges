# Hunter Too

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2024 |
| **Category** | Unknown |
| **Difficulty** | Unknown |
| **Points** | N/A |
| **Flag** | `poctf{uwsp_f4ll3n_fr0m_gr4c3}` |
| **Status** | Solved |

---

## Challenge Overview

A 7z archive protected by a password that is not in any common wordlist. The challenge description is a tongue-in-cheek rant about Crack challenges always being called "pay2win," and the password itself plays directly into that joke.

## Objective

Extract the flag from the password-protected `Crack100-3.7z` archive by identifying the correct password from contextual clues in the description.

## Methodology

### Step 1: Analyze the Description

The challenge description is a humorous monologue about retiring the Crack category. The author repeatedly references people saying "lol pay2win" about every Crack challenge, no matter the format.

Key quotes from the description:
- "Nothing I do is good enough. Throw in hints? lol pay2win."
- "Leave a trail of breadcrumbs? lol pay2win."
- "Well, here's your lol pay2win challenge for the contest."

### Step 2: Identify the Password

The description itself is the hint. The password is the exact phrase that appears throughout: `lol pay2win`.

### Step 3: Extract the Flag

Using the password `lol pay2win` on the 7z archive successfully extracts the contents, revealing the flag.

```
Flag: poctf{uwsp_f4ll3n_fr0m_gr4c3}
```

## Lessons Learned

| # | Lesson | Details |
|---|--------|---------|
| 1 | Context is key | The password was hidden in plain sight within the challenge description itself |
| 2 | Social engineering mindset | Understanding the author's frustration and humor pointed directly to the answer |
| 3 | Non-standard passwords | Not all crack challenges require brute force; sometimes the answer is in the narrative |

## MITRE ATT&CK Mapping

| Tactic | Technique | ID | Details |
|--------|-----------|-----|---------|
| Credential Access | Brute Force: Password Guessing | T1110.001 | Initial assumption of brute-force approach |
| Collection | Archive Collected Data: Archive via Utility | T1560.001 | Extracting data from 7z archive |

## Remediation

### Technical Fixes

- Use cryptographically random passwords instead of contextual phrases
- Avoid embedding password hints in plaintext descriptions

### MITRE D3FEND

| Technique | ID | How it applies |
|-----------|-----|----------------|
| Credential Hardening | D3-CH | Use strong, random passphrases for archive encryption |

### NIST CSF 2.0

| Function | Category | Relevance |
|----------|----------|-----------|
| Protect (PR) | Identity Management, Authentication and Access Control (PR.AA) | Enforce strong password policies |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---------|-------------|
| IA-5 | Authenticator Management: require complexity for encryption passphrases |

### C2M2

| Practice | Domain | Relevance |
|----------|--------|-----------|
| Access Management | ACCESS | Enforce authentication strength for encrypted archives |

### CWE

| CWE ID | Name | Relevance |
|--------|------|-----------|
| CWE-521 | Weak Password Requirements | Password derived from predictable context |

## References

- [UWSP Pointer Overflow CTF 2024](https://pointeroverflowctf.com)
- Based on solve approach from [shivang1209-dot](https://github.com/shivang1209-dot/CTF-Writeup)

---

Thanks guys!! (❍ᴥ❍ʋ)

CTF challenges are like puzzles: the answer is always simpler than you think, but only after you find it.

[![Instagram](https://img.shields.io/badge/Instagram-%23E4405F.svg?style=for-the-badge&logo=Instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/linkedin-%230077B5.svg?style=for-the-badge&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/X-%23000000.svg?style=for-the-badge&logo=X&logoColor=white)](https://x.com/mrhenrike)
