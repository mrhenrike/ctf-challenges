# I Have Written Down My Secrets

| Property | Value |
|----------|-------|
| **CTF** | Pointer Overflow CTF 2024 (UWSP) |
| **Category** | Crack |
| **Difficulty** | Easy |
| **Points** | 100 |
| **Status** | Solved |

## Challenge Overview

A password-protected PDF containing a Base64-encoded flag. The description heavily references learning French on Duolingo, hinting that the password is a French word related to being "overinvested" in the hobby.

## Objective

Crack the PDF password using contextual clues about French vocabulary, then decode the Base64 string inside.

## Methodology

### Step 1: Analyze the Description

The description is a story about learning too many languages on Duolingo during summer break. Key phrases:
- "over-zealously do extra lessons"
- "over-commit and spread myself thin"
- French phrases like "Occupez-vous de vos oignons" (mind your own business)
- Theme of being "over-invested" in language learning

### Step 2: Extract PDF Hash

```bash
pdf2john Crack100-2.pdf > hashes.txt
```

### Step 3: Crack with French Wordlist

Standard `rockyou.txt` did not work. Given the heavy French theme, tried various French wordlists. The keyword pattern pointed to "overinvested" as a concept, which translates to French as `surinvesti`.

```bash
john --wordlist=french_wordlist.txt hashes.txt
```

Password: `surinvesti`

### Step 4: Extract the Encoded Data

Opening the PDF with the cracked password revealed a Base64-encoded string:

```
cG9jdGZ7dXdzcF9XMW5kNV8wZl9DaDRuZzN9
```

### Step 5: Decode the Flag

```bash
echo 'cG9jdGZ7dXdzcF9XMW5kNV8wZl9DaDRuZzN9' | base64 -d
```

```
Flag: poctf{uwsp_W1nd5_0f_Ch4ng3}
```

## Lessons Learned

| # | Lesson | Details |
|---|--------|---------|
| 1 | Language-specific wordlists | When descriptions reference foreign languages, consider wordlists in that language |
| 2 | Contextual cracking | The thematic clues ("over-commit", "over-zealously") pointed to the French translation |
| 3 | Multi-layer encoding | Cracking the password was only step one; recognizing Base64 encoding was step two |

## MITRE ATT&CK Mapping

| Tactic | Technique | ID | Details |
|--------|-----------|-----|---------|
| Credential Access | Brute Force: Password Cracking | T1110.002 | Cracking PDF password hash with wordlist |
| Defense Evasion | Obfuscated Files or Information: Software Packing | T1027.002 | Flag hidden inside encrypted PDF |
| Defense Evasion | Deobfuscate/Decode Files or Information | T1140 | Base64 decoding the flag string |

## Remediation

### Technical Fixes

- Use randomly generated passwords rather than vocabulary words from any language
- Avoid storing sensitive data as simple Base64 in documents

### MITRE D3FEND

| Technique | ID | How it applies |
|-----------|-----|----------------|
| Credential Hardening | D3-CH | Require non-dictionary passphrases |
| File Encryption | D3-FE | Use strong encryption with random keys |

### NIST CSF 2.0

| Function | Category | Relevance |
|----------|----------|-----------|
| Protect (PR) | Data Security (PR.DS) | Protect sensitive content with strong encryption |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---------|-------------|
| IA-5 | Authenticator Management: avoid dictionary-based passwords |
| SC-28 | Protection of Information at Rest: proper encryption for stored data |

### C2M2

| Practice | Domain | Relevance |
|----------|--------|-----------|
| Access Management | ACCESS | Enforce strong authentication for document encryption |

### CWE

| CWE ID | Name | Relevance |
|--------|------|-----------|
| CWE-521 | Weak Password Requirements | Dictionary word used as encryption password |
| CWE-311 | Missing Encryption of Sensitive Data | Flag only protected by Base64 encoding inside PDF |

## References

- [UWSP Pointer Overflow CTF 2024](https://pointeroverflowctf.com)
- Based on solve approach from [shivang1209-dot](https://github.com/shivang1209-dot/CTF-Writeup)

---

Thanks guys!! (❍ᴥ❍ʋ)

When the description talks a lot about one specific thing, that thing is almost always the password. Read between the lines.

[![Instagram](https://img.shields.io/badge/Instagram-%23E4405F.svg?style=for-the-badge&logo=Instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/linkedin-%230077B5.svg?style=for-the-badge&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/X-%23000000.svg?style=for-the-badge&logo=X&logoColor=white)](https://x.com/mrhenrike)
