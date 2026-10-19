# We Do It Live

**Category:** Reverse Engineering
**Challenge:** We Do It Live
**CTF:** Pointer Overflow CTF 2024
**Points:** Reverse 200
**Result:** Solved

**Flag:**

~~~text
poctf{uwsp_7h3_n16h7_15_d4rk}
~~~

---

## 1. Challenge Overview

A binary with a `check_input` function that transforms user input and compares it against a known value. The task is to reverse the transformation to recover the original input (the flag).

**Files:** `Reverse200-2` (ELF binary)

---

## 2. Decompiled Logic Analysis

The `check_input` function reveals:

1. A target string `var_28 = "TUaP^IOM"` (first 8 bytes of the expected transformed input)
2. Additional encoded bytes stored as `var_20`:

~~~text
\x51\x54\x65\x0d\x5c\x11\x65\x56\x13\x0e\x5c\x0d\x65\x13\x0f\x65\x60\x10\x52\x59\x47
~~~

3. A `transform` function applied to user input before comparison

The `transform` function performs: for each character, XOR with a constant and add 5.

---

## 3. Reversing the Transformation

To reverse: subtract 5, then XOR with 63 (`0x3F`).

The [Python script](scripts/script.py) handles both parts:

- **Part 1:** reverse the ASCII string `"TUaP^IOM"`
- **Part 2:** reverse the encoded byte sequences stored as unsigned long integers

~~~python
import struct

def reverse_transform(v2):
    return ''.join(chr((ord(c) - 5) ^ 63) for c in v2)

def ulong_to_ascii_values(value):
    return [b for b in struct.pack('<Q', value)]

def transform_ascii_values(ascii_values):
    return ''.join(chr((v - 5) ^ 63) for v in ascii_values)

v2 = "TUaP^IOM"
flag_part_1 = reverse_transform(v2)

v3 = 6225401146968986705
v4 = 7281577388051686673
v5 = 5141230679910321939
all_values = ulong_to_ascii_values(v3) + ulong_to_ascii_values(v4) + ulong_to_ascii_values(v5)
flag_part_2 = transform_ascii_values(all_values)

flag = flag_part_1 + flag_part_2
~~~

---

## 4. Flag Correction

The script initially produces `poctf{uwsp_7h3_n3_n16h7_15_d4rk}`, which contains an extra `n3_` segment due to padding in the encoded data. Removing the artifact yields the correct flag matching the quote "The Night Is Dark":

~~~text
poctf{uwsp_7h3_n16h7_15_d4rk}
~~~

---

## Lessons Learned

| # | Lesson | Detail |
|---|--------|--------|
| 1 | XOR+ADD transformations are easily reversible | Subtract and XOR in reverse order recovers the original |
| 2 | Integer storage requires endianness awareness | `struct.pack` with '<Q' handles little-endian conversion |
| 3 | Decoder output may need manual cleanup | Padding artifacts in decoded output are common |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID | Context |
|---|---|---|---|
| Defense Evasion | Obfuscated Files or Information | T1027 | Input transformed via XOR+ADD before comparison |
| Defense Evasion | Deobfuscate/Decode Files or Information | T1140 | Reversed the transformation to recover the flag |
| Resource Development | Obtain Capabilities: Tool | T1588.002 | Custom solver to reverse multi-part encoded values |

> **CWE-327:** Use of a Broken or Risky Cryptographic Algorithm. XOR+ADD transformation is trivially reversible.
> **CWE-261:** Weak Encoding for Password. Password validation relies on reversible encoding.

---

## Remediation and Containment

### Technical Fixes

1. Use one-way hash functions (bcrypt, Argon2) for password verification instead of reversible transforms
2. Never store the expected value in a form that can be reversed to plaintext
3. Implement rate limiting and lockout for failed authentication attempts
4. Move authentication to a server-side component

### MITRE D3FEND Countermeasures

- **D3-CH (Credential Hardening):** use irreversible hashing for credential storage
- **D3-OBF (Obfuscation):** apply deeper obfuscation to comparison functions
- **D3-DA (Dynamic Analysis):** detect automated solving attempts through anti-debug

### NIST CSF 2.0

- **Protect (PR.AC):** implement proper authentication using industry-standard algorithms
- **Protect (PR.DS):** protect credential verification data from extraction
- **Respond (RS.MI):** revoke credentials exposed through reverse engineering

### NIST SP 800-53 Rev. 5

- **IA-5 (Authenticator Management):** use one-way functions for password storage
- **SC-13 (Cryptographic Protection):** apply FIPS-approved algorithms for all cryptographic operations
- **SA-11 (Developer Testing and Evaluation):** test authentication logic against reversal attacks

### C2M2

- **ACCESS-3:** audit all authentication flows for reversible credential storage
- **THREAT-2:** include reverse engineering of authentication logic in testing scope

---

Thanks guys!! (❍ᴥ❍ʋ)

---

The night is dark and full of XOR operations. When the transformation is two arithmetic steps, a Python one-liner brings the light.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

> **Reference:** Adapted from [shivang1209-dot/CTF-Writeups](https://github.com/shivang1209-dot/CTF-Writeups). Original scripts credited to the author.
