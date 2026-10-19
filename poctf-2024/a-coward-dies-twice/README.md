# A Coward Dies Twice

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2024 |
| **Category** | Cracking |
| **Difficulty** | Hard |
| **Points** | 300 |
| **Flag** | `poctf{uwsp_7h3_r04d_n07_74k3n}` |
| **Status** | Solved |

---

## Challenge Overview

A miscellaneous challenge involving an anagram puzzle. The string "A Denk Rotton Hate" must be rearranged into the name of a poem, then converted to leetspeak to form the flag. The answer is Robert Frost's "The Road Not Taken."

---

## Objective

Solve the anagram using the provided constraints and convert the result to leetspeak format.

---

## Methodology

### Step 1: Analyze the constraints

The challenge provides:
- Anagram: **A Denk Rotton Hate**
- The answer is the name of a poem
- Four words in the flag
- No word uses the same letter twice
- No word has more than five letters or fewer than three
- The first word is "the"

### Step 2: Solve the anagram

Given the constraints:
- First word: "the" (3 letters, confirmed)
- Remaining letters after removing T, H, E: A, D, E, N, K, R, O, T, T, O, N, A, T
- Wait: rearranging "A Denk Rotton Hate" with the constraint of four unique-letter words of 3-5 chars

The answer is the famous Robert Frost poem: **The Road Not Taken**

Verification:
- "the" (3 letters, no repeats)
- "road" (4 letters, no repeats)
- "not" (3 letters, no repeats)
- "taken" (5 letters, no repeats)

### Step 3: Convert to leetspeak

Applying the standard leetspeak mapping:

| Letter | Leet |
|--------|------|
| a      | 4    |
| e      | 3    |
| o      | 0    |
| t      | 7    |

Result: `7h3_r04d_n07_74k3n`

### Step 4: Assemble the flag

```
poctf{uwsp_7h3_r04d_n07_74k3n}
```

---

## Flag

```
poctf{uwsp_7h3_r04d_n07_74k3n}
```

---

## Lessons Learned

| # | Lesson | Detail |
|---|--------|--------|
| 1 | Constraints narrow possibilities | Word length and uniqueness constraints drastically reduce the solution space |
| 2 | Cultural knowledge helps | Recognizing famous poem titles speeds up the solve |
| 3 | Leetspeak mapping is consistent | Standard substitutions (a=4, e=3, o=0, t=7) apply throughout POCTF |
| 4 | Anagrams can be systematic | Removing confirmed letters progressively simplifies the puzzle |

---

## MITRE ATT&CK Mapping

| Tactic          | Technique                      | ID        |
|-----------------|--------------------------------|-----------|
| Defense Evasion | Obfuscated Files or Information| T1027     |
| Collection      | Data Obfuscation               | T1001     |

---

## Remediation

### Technical Fixes
- Encoding and obfuscation (including leetspeak) do not provide security
- Use proper encryption for sensitive data, not character substitution
- Implement layered access controls rather than security through obscurity

### D3FEND Countermeasures
| Technique             | ID        |
|-----------------------|-----------|
| File Content Rules    | D3-FCR    |

### NIST CSF 2.0
| Function | Category                | Subcategory |
|----------|------------------------|-------------|
| Protect  | Data Security          | PR.DS-01    |

### NIST SP 800-53 Rev. 5
| Control     | Description                          |
|-------------|--------------------------------------|
| SC-28       | Protection of Information at Rest    |

### C2M2
| Practice Area               | MIL |
|-----------------------------|-----|
| Asset, Change and Configuration Management | MIL1 |

### CWE
| ID      | Name                                     |
|---------|------------------------------------------|
| CWE-261 | Weak Encoding for Password               |

---

## References

- Based on solve approach from [Jdwalli](https://github.com/Jdwalli/ctf-writeups)
- Robert Frost, "The Road Not Taken" (1916)

---

## Closing

Thanks guys!! (❍ᴥ❍ʋ)

Two roads diverged in a yellow wood, and we took the one with the anagram. It made all the difference. Sometimes the path to the flag is through poetry, not code.

[![Instagram](https://img.shields.io/badge/-Instagram-E4405F?style=flat&logo=instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/-LinkedIn-0077B5?style=flat&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/-X-000000?style=flat&logo=x&logoColor=white)](https://x.com/mrhenrike)
