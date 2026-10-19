# Embrace the Suck

| Detail      | Value                                      |
|-------------|--------------------------------------------|
| CTF         | Pointer Overflow CTF 2024                  |
| Category    | Misc                                       |
| Difficulty  | Medium                                     |
| Points      | 200                                        |
| Flag        | `poctf{uwsp_7h3_n33d5_0f_7h3_m4ny}`      |
| Status      | Solved                                     |

---

## Challenge Overview

A miscellaneous challenge presented through a text message conversation between "Ben" and "Lily." The encrypted text `hub 0bbv1 cw hub jr0n` uses a substitution cipher. Frequency analysis reveals the plaintext "the needs of the many," which must be converted to leetspeak for the flag.

---

## Objective

Decrypt the substitution cipher and convert the resulting phrase to leetspeak format.

---

## Methodology

### Step 1: Identify the cipher text

From the conversation, the encrypted flag is: `hub 0bbv1 cw hub jr0n`

### Step 2: Replace numbers with letters

The numbers in the cipher text correspond to their letter equivalents:
- `0` maps to `o`
- `1` maps to a letter (determined by context)

Intermediate: `hub obbvi cw hub jron`

### Step 3: Apply frequency analysis

Using a tool like [quipqiup](https://quipqiup.com/) with the pattern `hub obbvi cw hub jron`, the substitution cipher solves to:

**the needs of the many**

This is a reference to the famous Spock quote from Star Trek: "The needs of the many outweigh the needs of the few."

### Step 4: Convert to leetspeak

Using the standard POCTF leetspeak mapping:

```python
char_set = '4bcd3f6h1jklmn0pqr57uvwxyz'
text = "the needs of the many"
mapping = dict(zip("abcdefghijklmnopqrstuvwxyz", char_set))
flag = ""
for char in text:
    if char == " ":
        flag += "_"
    else:
        flag += str(mapping[char.lower()])
print(f"poctf{{uwsp_{flag}}}")
```

Output: `poctf{uwsp_7h3_n33d5_0f_7h3_m4ny}`

---

## Flag

```
poctf{uwsp_7h3_n33d5_0f_7h3_m4ny}
```

---

## Lessons Learned

| # | Lesson | Detail |
|---|--------|--------|
| 1 | Numbers can be letter substitutes | Hybrid ciphers mix digits and character substitution |
| 2 | Frequency analysis breaks simple ciphers | Repeated patterns like "hub" = "the" crack the cipher |
| 3 | Pop culture references are common | Star Trek quotes appear frequently in CTF challenges |
| 4 | Automated tools accelerate decryption | quipqiup solves simple substitution ciphers in seconds |

---

## MITRE ATT&CK Mapping

| Tactic          | Technique                      | ID        |
|-----------------|--------------------------------|-----------|
| Defense Evasion | Obfuscated Files or Information| T1027     |
| Command and Control | Data Encoding              | T1132     |

---

## Remediation

### Technical Fixes
- Simple substitution ciphers are trivially broken with frequency analysis
- Use established encryption algorithms (AES, ChaCha20) for confidentiality
- Do not rely on character substitution for data protection

### D3FEND Countermeasures
| Technique             | ID        |
|-----------------------|-----------|
| File Content Rules    | D3-FCR    |
| Message Analysis      | D3-MA     |

### NIST CSF 2.0
| Function | Category                | Subcategory |
|----------|------------------------|-------------|
| Protect  | Data Security          | PR.DS-01    |

### NIST SP 800-53 Rev. 5
| Control     | Description                          |
|-------------|--------------------------------------|
| SC-13       | Cryptographic Protection             |
| SC-28       | Protection of Information at Rest    |

### C2M2
| Practice Area               | MIL |
|-----------------------------|-----|
| Asset, Change and Configuration Management | MIL1 |

### CWE
| ID      | Name                                     |
|---------|------------------------------------------|
| CWE-327 | Use of a Broken or Risky Cryptographic Algorithm |
| CWE-261 | Weak Encoding for Password               |

---

## References

- Based on solve approach from [Jdwalli](https://github.com/Jdwalli/ctf-writeups)
- [quipqiup](https://quipqiup.com/)
- Star Trek II: The Wrath of Khan (1982)

---

## Closing

Thanks guys!! (❍ᴥ❍ʋ)

The needs of the many outweigh the needs of the few, or the one. In CTFs, the need to check every cipher type outweighs the desire to overthink it. Sometimes it really is just a substitution cipher.

[![Instagram](https://img.shields.io/badge/-Instagram-E4405F?style=flat&logo=instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/-LinkedIn-0077B5?style=flat&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/-X-000000?style=flat&logo=x&logoColor=white)](https://x.com/mrhenrike)
