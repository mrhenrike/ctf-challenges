# Planned Obsequence

**Category:** Reverse Engineering
**Challenge:** Planned Obsequence
**CTF:** Pointer Overflow CTF 2024
**Points:** Reverse 200
**Result:** Solved

**Flag:**

~~~text
poctf{uwsp_4_7h1n6_0f_b34u7y}
~~~

---

## 1. Challenge Overview

A binary with the flag redacted from the source code but the obfuscated version still embedded in a variable. The description confirms a two-step encoding process: finding the encoded flag and reversing two operations to recover ASCII.

**Files:** `Reverse200-1` (ELF binary)

---

## 2. Extracting the Obfuscated Flag

Through static analysis (Binary Ninja/Ghidra), the obfuscated flag was found embedded in the binary:

~~~text
2d383c313f2432302c2d08710870356e376f086d3f083b6c713270262a
~~~

---

## 3. Analyzing the Encoding Scheme

The encoding applies two operations sequentially to each byte:

1. **Add 3** to the original byte value
2. **XOR with `0x5A`** on the result

To reverse: subtract 3, then XOR with `0x5A`.

---

## 4. Decoding Script

The [Python script](scripts/script.py) reverses the obfuscation:

~~~python
hex_obfuscated_flag = "2d383c313f2432302c2d08710870356e376f086d3f083b6c713270262a"
obfuscated_flag = bytes.fromhex(hex_obfuscated_flag)

def deobfuscate(flag):
    deobfuscated_flag = ""
    for char in flag:
        original_char = (char - 3) ^ 0x5A
        deobfuscated_flag += chr(original_char)
    return deobfuscated_flag

flag = deobfuscate(obfuscated_flag)
print("Deobfuscated Flag:", flag)
~~~

Output: `poctf{uwsp_4_7h1n6_0f_b34u7y}`

---

## Lessons Learned

| # | Lesson | Detail |
|---|--------|--------|
| 1 | Two-step encoding is still trivially reversible | ADD + XOR is no substitute for real encryption |
| 2 | Redacted source does not protect embedded data | Obfuscated values in the binary are still extractable |
| 3 | Byte-level operations are easy to script | Python makes short work of custom encoding reversal |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID | Context |
|---|---|---|---|
| Defense Evasion | Obfuscated Files or Information | T1027 | Flag encoded with ADD+XOR obfuscation |
| Defense Evasion | Deobfuscate/Decode Files or Information | T1140 | Reversed the two-step encoding to recover plaintext |
| Resource Development | Obtain Capabilities: Tool | T1588.002 | Built custom Python decoder for the encoding scheme |

> **CWE-327:** Use of a Broken or Risky Cryptographic Algorithm. ADD+XOR encoding provides no meaningful security.
> **CWE-311:** Missing Encryption of Sensitive Data. Flag protected only by trivially reversible obfuscation.

---

## Remediation and Containment

### Technical Fixes

1. Replace custom encoding with AES-GCM or other authenticated encryption
2. Store secrets server-side rather than in distributable binaries
3. If client-side storage is required, use hardware-backed key storage
4. Apply multiple independent layers of protection (encryption + integrity + access control)

### MITRE D3FEND Countermeasures

- **D3-FE (File Encryption):** replace custom obfuscation with proper encryption
- **D3-OBF (Obfuscation):** if obfuscation is used, combine with anti-analysis techniques
- **D3-FCOA (File Content Analysis):** scan for known encoding patterns in distributed binaries

### NIST CSF 2.0

- **Protect (PR.DS):** use validated cryptographic algorithms for data protection
- **Detect (DE.CM):** monitor for automated decoding tool usage
- **Respond (RS.MI):** rotate exposed secrets immediately upon discovery

### NIST SP 800-53 Rev. 5

- **SC-13 (Cryptographic Protection):** use FIPS-validated algorithms, not custom schemes
- **SC-28 (Protection of Information at Rest):** encrypt data at rest with proper key management
- **SA-11 (Developer Testing and Evaluation):** test encoded data against reversal attacks

### C2M2

- **THREAT-2:** include custom encoding reversal in security testing
- **RISK-3:** classify custom obfuscation as insufficient for sensitive data protection

---

Thanks guys!! (❍ᴥ❍ʋ)

---

A thing of beauty is a joy forever, and this challenge is a beautiful lesson in why custom encoding schemes never survive analysis. Two operations, one Python script, one flag.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

> **Reference:** Adapted from [shivang1209-dot/CTF-Writeups](https://github.com/shivang1209-dot/CTF-Writeups). Original scripts credited to the author.
