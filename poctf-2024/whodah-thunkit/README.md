# Whodah Thunkit

| Property | Value |
|----------|-------|
| **CTF** | Pointer Overflow CTF 2024 (UWSP) |
| **Category** | Crack |
| **Difficulty** | Hard |
| **Points** | 300 |
| **Status** | Solved |

## Challenge Overview

A network service running a custom application that prompts for a 32-character MD5-like hash. The application provides Wordle-style feedback (correct characters and correct positions), enabling a systematic approach to reconstruct the target hash character by character.

## Objective

Connect to the remote service, use the positional feedback mechanism to reconstruct the target hash, and submit it to retrieve the flag.

## Methodology

### Step 1: Understand the Application

Connecting to the service at `34.123.210.162:32320` reveals:
- The application prompts for a 32-character password (hex characters only: 0-9, a-f)
- After each guess, it returns two values:
  - **Correct Characters**: how many characters from the guess appear in the target
  - **Correct Positions**: how many characters are in their exact positions

### Step 2: Character Frequency Analysis

First, determine which hex characters appear in the hash and how many times. The character `e` has zero occurrences, making it useful as padding when testing other characters.

By submitting 32 copies of each hex character (e.g., `aaaaaaaa...` for 32 chars), the "Correct Characters" count reveals the frequency:

| Character | Count | Character | Count |
|-----------|-------|-----------|-------|
| a | 6 | 0 | 2 |
| b | 1 | 1 | 1 |
| c | 5 | 2 | 1 |
| d | 2 | 3 | 1 |
| f | 2 | 4 | 2 |
| e | 0 | 5 | 3 |
| | | 6 | 1 |
| | | 7 | 3 |
| | | 8 | 1 |
| | | 9 | 1 |

### Step 3: Position Determination

With `e` as a known non-present character, test each real character at each position. Place the target character at one position and fill the rest with `e`. The "Correct Positions" feedback reveals exactly where each character belongs.

### Step 4: Reconstruct the Hash

Iteratively determining all positions yields the target hash:

```
aac56acc457c9cf0f15ad8d20347b7aa
```

### Step 5: Submit and Retrieve Flag

Sending the correct hash to the service reveals the flag.

```
Flag: poctf{uwsp_l0n3ly_4nd_f0r70rn}
```

## Lessons Learned

| # | Lesson | Details |
|---|--------|---------|
| 1 | Information leakage | The Wordle-style feedback mechanism leaks enough information to reconstruct the password |
| 2 | Oracle attacks | Any system that provides differential feedback on guesses can be exploited systematically |
| 3 | Scripting is essential | Manual guessing would be impractical; scripted interaction reduces the problem to ~500 queries |
| 4 | Side-channel thinking | The feedback is a side channel that reveals the secret without brute-forcing the full space |

## MITRE ATT&CK Mapping

| Tactic | Technique | ID | Details |
|--------|-----------|-----|---------|
| Credential Access | Brute Force: Password Spraying | T1110.003 | Systematic hash reconstruction via feedback oracle |
| Discovery | Network Service Discovery | T1046 | Connecting to remote service on non-standard port |
| Execution | Command and Scripting Interpreter: Python | T1059.006 | Automated script for hash reconstruction |

## Remediation

### Technical Fixes

- Never provide differential feedback on authentication attempts (correct characters, positions, etc.)
- Implement account lockout or rate limiting after failed attempts
- Use constant-time comparison for authentication checks
- Return only generic "success" or "failure" responses

### MITRE D3FEND

| Technique | ID | How it applies |
|-----------|-----|----------------|
| Authentication Event Thresholding | D3-AET | Rate-limit authentication attempts |
| Credential Hardening | D3-CH | Do not leak partial match information |

### NIST CSF 2.0

| Function | Category | Relevance |
|----------|----------|-----------|
| Protect (PR) | Identity Management, Authentication and Access Control (PR.AA) | Implement secure authentication feedback |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---------|-------------|
| AC-7 | Unsuccessful Logon Attempts: lockout after threshold |
| IA-5 | Authenticator Management: constant-time comparison |
| SI-11 | Error Handling: do not reveal authentication details in error messages |

### CWE

| CWE ID | Name | Relevance |
|--------|------|-----------|
| CWE-209 | Generation of Error Message Containing Sensitive Information | Feedback reveals password structure |
| CWE-307 | Improper Restriction of Excessive Authentication Attempts | No rate limiting on guesses |

## References

- [UWSP Pointer Overflow CTF 2024](https://pointeroverflowctf.com)
- Based on solve approach from [shivang1209-dot](https://github.com/shivang1209-dot/CTF-Writeup)

---

Thanks guys!! (❍ᴥ❍ʋ)

An authentication oracle that tells you "how wrong" you are is the same as telling you how to be right. Feedback should be binary: yes or no, nothing in between.

[![Instagram](https://img.shields.io/badge/Instagram-%23E4405F.svg?style=for-the-badge&logo=Instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/linkedin-%230077B5.svg?style=for-the-badge&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/X-%23000000.svg?style=for-the-badge&logo=X&logoColor=white)](https://x.com/mrhenrike)
