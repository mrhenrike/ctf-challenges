# Understanding Nonsense

**Category:** Reverse Engineering
**Challenge:** Understanding Nonsense
**CTF:** Pointer Overflow CTF 2024
**Points:** Reverse 100
**Result:** Solved

**Flag:**

~~~text
poctf{uwsp_br3v17y_15_7h3_50u1}
~~~

---

## 1. Challenge Overview

A binary with source code containing an incomplete decoding function. The description says the challenge creator "gave up" before finishing the decode logic. The task is to complete the decoder, run it, and convert the resulting hex output to ASCII.

**Files:** `Reverse100-3` (ELF binary), `Reverse100-3.c` (source code)

---

## 2. Source Code Analysis

The provided `Reverse100-3.c` contains an encoding function and an intentionally incomplete decoding function. Key observations:

- The encoded flag is stored as a hex array
- The encoding uses a seed value (`88974713`) and a reversal process
- The decode function needs to iterate the reversal 10 times
- The length calculation is broken and needs fixing

---

## 3. Fixing the Decoder

Three fixes applied to create [decode.c](scripts/decode.c):

1. **Added iteration loop:** wrap the `print_flag_hex` function call in a loop running 10 times
2. **Fixed length calculation:**

~~~c
int length = sizeof(encoded_flag) / sizeof(encoded_flag[0]);
~~~

3. **Applied correct seed value:** pass `88974713` as the seed parameter

Compiled and executed:

~~~bash
gcc decode.c -o decode
./decode
~~~

---

## 4. Hex to ASCII Conversion

The decoder output after step 10:

~~~text
706f6374667b757773705f627233763137795f31355f3768335f353075317d
~~~

Converting from hex to ASCII:

~~~python
bytes.fromhex("706f6374667b757773705f627233763137795f31355f3768335f353075317d").decode()
# Result: poctf{uwsp_br3v17y_15_7h3_50u1}
~~~

---

## Lessons Learned

| # | Lesson | Detail |
|---|--------|--------|
| 1 | Incomplete code is a valid CTF pattern | Providing broken source forces understanding of the algorithm |
| 2 | Multi-step decoding requires careful tracking | Hex output needs a second conversion to readable text |
| 3 | Seed values are critical to reversible algorithms | Wrong seed produces garbage, correct seed produces the flag |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID | Context |
|---|---|---|---|
| Defense Evasion | Obfuscated Files or Information | T1027 | Flag encoded through multi-step reversal with seed |
| Defense Evasion | Deobfuscate/Decode Files or Information | T1140 | Completed the decoder to reverse the encoding |
| Resource Development | Obtain Capabilities: Tool | T1588.002 | Built custom decoder by fixing provided source code |

> **CWE-327:** Use of a Broken or Risky Cryptographic Algorithm. Custom encoding with a fixed seed is trivially reversible.
> **CWE-321:** Use of Hard-coded Cryptographic Key. The seed value `88974713` is embedded in the source code.

---

## Remediation and Containment

### Technical Fixes

1. Use standard cryptographic primitives (AES-GCM) instead of custom encoding schemes
2. Derive keys from secure sources rather than hardcoding seed values
3. If obfuscation is intended, apply multiple independent layers
4. Do not distribute source code alongside encoded data

### MITRE D3FEND Countermeasures

- **D3-FE (File Encryption):** use proper encryption algorithms instead of custom reversible encoding
- **D3-MFA (Multi-Factor Authentication):** require additional verification beyond decode knowledge
- **D3-FCOA (File Content Analysis):** validate that distributed source does not leak decoding logic

### NIST CSF 2.0

- **Protect (PR.DS):** protect sensitive data with approved cryptographic algorithms
- **Detect (DE.CM):** detect attempts to compile and run custom decoders against protected data
- **Respond (RS.MI):** invalidate exposed secrets after algorithm compromise

### NIST SP 800-53 Rev. 5

- **SC-13 (Cryptographic Protection):** use FIPS-approved cryptographic mechanisms
- **SC-12 (Cryptographic Key Establishment and Management):** properly manage and protect cryptographic keys
- **SA-11 (Developer Testing and Evaluation):** verify that distributed code does not expose recovery paths

### C2M2

- **THREAT-2:** evaluate custom encoding schemes for reversibility risk
- **ACCESS-3:** ensure secrets are protected by validated cryptographic implementations

---

Thanks guys!! (❍ᴥ❍ʋ)

---

Brevity is the soul of wit, and also the soul of this flag. Fixing broken code to understand the algorithm is a satisfying puzzle, and the hex-to-ASCII step keeps you honest about tracking your output format.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

> **Reference:** Adapted from [shivang1209-dot/CTF-Writeups](https://github.com/shivang1209-dot/CTF-Writeups). Original scripts credited to the author.
