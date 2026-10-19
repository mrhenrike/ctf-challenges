# Guffaw of the Jackdaw

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2024 |
| **Category** | Relevance |
| **Difficulty** | Unknown |
| **Points** | N/A |
| **Flag** | `poctf{uwsp_p4r7_0f_7h3_m4ch1n3}` |
| **Status** | Solved |

---

## Challenge Overview

A steganography challenge disguised as a crack problem. The challenge introduces "Jack," a monster truck enthusiast whose password preferences (all uppercase, incrementing numbers) combined with OpenStego steganography yield the hidden flag.

## Objective

Build a custom wordlist based on Jack's personality profile, crack the OpenStego password, and extract the hidden flag from the steganographic image.

## Methodology

### Step 1: Identify the Tool

The challenge provides an icon image that matches **OpenStego**, a steganography tool used for hiding text inside images.

![OpenStego Icon](images/Crack300-1.png)

### Step 2: Profile the Target

From the description, Jack's characteristics:
- Loves **monster trucks** (daily driver, attends jams and exhibitions)
- Likes **BIG things only** (everything uppercase)
- Changes password yearly by **adding/incrementing numbers at the end**

### Step 3: Build a Custom Wordlist

1. Scraped monster truck names from the Monster Jam website using `cewl`
2. Converted all words to **UPPERCASE** (Jack likes "BIG things")
3. Appended numbers `1` through `25` to simulate yearly increments

```bash
cewl https://www.monsterjam.com/en-us/trucks -d 1 -m 3 > trucks.txt
# Convert to uppercase and append year numbers
awk '{print toupper($0)}' trucks.txt | while read w; do
  for i in $(seq 1 25); do echo "${w}${i}"; done
done > custom_wordlist.txt
```

### Step 4: Crack the OpenStego Password

Ran the custom wordlist against the OpenStego file.

Password: `MONSTERJAM24`

### Step 5: Extract the Flag

Used OpenStego to extract the hidden text from the image:

```bash
openstego extract -sf challenge_image -p MONSTERJAM24
```

```
Flag: poctf{uwsp_p4r7_0f_7h3_m4ch1n3}
```

## Lessons Learned

| # | Lesson | Details |
|---|--------|---------|
| 1 | OSINT-driven wordlists | Profiling a target's interests yields effective custom wordlists |
| 2 | Password mutation rules | Real users add incremental numbers; this is a standard mutation rule in hashcat/john |
| 3 | Tool identification | Recognizing the OpenStego icon was crucial to understanding the challenge type |
| 4 | Case sensitivity matters | "BIG things" was a direct hint to use uppercase-only passwords |

## MITRE ATT&CK Mapping

| Tactic | Technique | ID | Details |
|--------|-----------|-----|---------|
| Credential Access | Brute Force: Password Guessing | T1110.001 | Custom wordlist based on target profile |
| Defense Evasion | Obfuscated Files or Information: Steganography | T1027.003 | Flag hidden inside image using OpenStego |
| Reconnaissance | Gather Victim Identity Information | T1589 | Profiling Jack's interests to build wordlist |

## Remediation

### Technical Fixes

- Do not use personal interests as password base words
- Avoid simple incrementing patterns for password rotation
- Steganography is not encryption; it provides obscurity, not security

### MITRE D3FEND

| Technique | ID | How it applies |
|-----------|-----|----------------|
| Credential Hardening | D3-CH | Enforce non-predictable password rotation policies |
| File Content Rules | D3-FCR | Detect steganographic content in image files |

### NIST CSF 2.0

| Function | Category | Relevance |
|----------|----------|-----------|
| Protect (PR) | Identity Management, Authentication and Access Control (PR.AA) | Prohibit predictable password patterns |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---------|-------------|
| IA-5 | Authenticator Management: enforce non-trivial password complexity |
| IA-5(1) | Password-Based Authentication: minimum requirements beyond dictionary words |

### CWE

| CWE ID | Name | Relevance |
|--------|------|-----------|
| CWE-521 | Weak Password Requirements | Predictable pattern: UPPERCASE + incremented number |
| CWE-656 | Reliance on Security Through Obscurity | Steganography used as sole protection |

## References

- [UWSP Pointer Overflow CTF 2024](https://pointeroverflowctf.com)
- [OpenStego](https://www.openstego.com/)
- [Monster Jam Trucks](https://www.monsterjam.com/en-us/trucks)
- Based on solve approach from [shivang1209-dot](https://github.com/shivang1209-dot/CTF-Writeup)

---

Thanks guys!! (❍ᴥ❍ʋ)

People are creatures of habit. Their passwords reflect what they love, and their rotation policies are predictable. Think like a social engineer, not just a brute forcer.

[![Instagram](https://img.shields.io/badge/Instagram-%23E4405F.svg?style=for-the-badge&logo=Instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/linkedin-%230077B5.svg?style=for-the-badge&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/X-%23000000.svg?style=for-the-badge&logo=X&logoColor=white)](https://x.com/mrhenrike)
