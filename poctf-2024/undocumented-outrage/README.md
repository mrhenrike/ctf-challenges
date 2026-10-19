# Undocumented Outrage

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2024 |
| **Category** | Unknown |
| **Difficulty** | Unknown |
| **Points** | N/A |
| **Flag** | `poctf{uwsp_wh15p3r5_1n_7h3_d4rk}` |
| **Status** | Solved |

---

## Challenge Overview

A password-protected `.docx` file where the password is a Russian word. The description references the author's years of learning Russian and complains about cold weather, hinting at the concept of "cold rolled" steel, which translates to Russian as the password.

## Objective

Crack the password of an encrypted DOCX file using a Russian wordlist and contextual clues from the description.

## Methodology

### Step 1: Analyze the Description Clues

The description contains several key hints:
- Extensive mention of learning **Russian** for six years (two in high school, four in university)
- References to extreme cold: "below zero for many weeks"
- Specific mention: "no one likes cold rolls. Cold rolls steal all the joy warm bread brings."
- The phrase "stay cool under pressure"

The concept of **"cold rolled"** is a metallurgical term, and in Russian it translates to `холоднокатаного`.

### Step 2: Extract the DOCX Hash

```bash
office2john Crack200-2.docx > hash.txt
```

### Step 3: Crack with Russian Wordlist

Attempted `rockyou.txt` first with no success. Then shifted to Russian wordlists and transliteration tools.

Used the CRWG tool (Custom Russian Wordlist Generator) to generate transliterated wordlists based on how Russian speakers create passwords.

```bash
john --wordlist=russian_transliterated.txt hash.txt
```

Password: `холоднокатаного` (cold-rolled)

### Step 4: Extract the Flag

Opened the DOCX file with the cracked password and retrieved the flag.

```
Flag: poctf{uwsp_wh15p3r5_1n_7h3_d4rk}
```

## Lessons Learned

| # | Lesson | Details |
|---|--------|---------|
| 1 | Language-specific attacks | When a challenge references a specific language, create or find wordlists in that language |
| 2 | Contextual wordplay | "Cold rolls" is a double entendre: bread rolls and cold-rolled metal, both connecting to Russian vocabulary |
| 3 | Transliteration awareness | Russian passwords may use Cyrillic characters, requiring specialized tools like CRWG |
| 4 | Cultural OSINT | Researching the teacher "Госпожа Демовидова" and related content can yield additional wordlist material |

## MITRE ATT&CK Mapping

| Tactic | Technique | ID | Details |
|--------|-----------|-----|---------|
| Credential Access | Brute Force: Password Cracking | T1110.002 | Cracking DOCX encryption with language-specific wordlist |
| Resource Development | Obtain Capabilities: Tool | T1588.002 | Using office2john and CRWG for hash extraction and wordlist generation |

## Remediation

### Technical Fixes

- Use randomly generated passwords for document encryption
- Do not use natural-language words from any language as passwords
- Consider using certificate-based document protection instead of passwords

### MITRE D3FEND

| Technique | ID | How it applies |
|-----------|-----|----------------|
| Credential Hardening | D3-CH | Enforce non-dictionary passphrases across all languages |
| File Encryption | D3-FE | Use strong, key-based encryption for sensitive documents |

### NIST CSF 2.0

| Function | Category | Relevance |
|----------|----------|-----------|
| Protect (PR) | Data Security (PR.DS) | Protect documents with strong encryption and random keys |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---------|-------------|
| IA-5 | Authenticator Management: prohibit dictionary words in any language |
| SC-28 | Protection of Information at Rest |

### C2M2

| Practice | Domain | Relevance |
|----------|--------|-----------|
| Access Management | ACCESS | Multi-language password policy enforcement |

### CWE

| CWE ID | Name | Relevance |
|--------|------|-----------|
| CWE-521 | Weak Password Requirements | Single dictionary word (Russian) as document password |

## References

- [UWSP Pointer Overflow CTF 2024](https://pointeroverflowctf.com)
- [CRWG: Custom Russian Wordlist Generator](https://github.com/topics/russian-wordlist)
- Based on solve approach from [shivang1209-dot](https://github.com/shivang1209-dot/CTF-Writeup)

---

Thanks guys!! (❍ᴥ❍ʋ)

Passwords do not have to be in English. A good cracker thinks in every language the target might speak.

[![Instagram](https://img.shields.io/badge/Instagram-%23E4405F.svg?style=for-the-badge&logo=Instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/linkedin-%230077B5.svg?style=for-the-badge&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/X-%23000000.svg?style=for-the-badge&logo=X&logoColor=white)](https://x.com/mrhenrike)
