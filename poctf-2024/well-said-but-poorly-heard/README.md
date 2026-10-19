# Well Said but Poorly Heard

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2024 |
| **Category** | Reverse Engineering |
| **Difficulty** | Easy |
| **Points** | 100 |
| **Flag** | `poctf{dynamic}` |

---

## 3. Static Analysis

Opening the binary in Binary Ninja reveals the main function logic:

~~~c
__builtin_strcpy(dest: &var_38, src: "poctf{uwsp_1n_w1n3_7h3r3_15_7ru7h}` |
| **Status** | Solved |

---

## 1. Challenge Overview

An ELF binary that outputs an "encoded" flag when executed. The encoding is a simple obfuscation function that can be reversed through static analysis. The description's riddle hints at a NOT/inversion operation: "True to false and false to true."

**Files:** `Reverse100-1` (ELF binary)

---

## 2. Initial Analysis

Running the binary produces an encoded string:

~~~bash
chmod +x Reverse100-1
./Reverse100-1
# Output: Encoded flag: <obfuscated string>
~~~

A `hexdump` with `xxd` shows partial flag fragments (`poctf{uw...`) mixed with encoded data.

---

## 3. Static Analysis

Opening the binary in Binary Ninja reveals the main function logic:

~~~c
__builtin_strcpy(dest: &var_38, src: "poctf{uwsp_1n_w1n3_7h3r3_15_7ru7h}")
obfuscate(&var_38)
printf(format: "Encoded flag: %s\n", &var_38)
~~~

The flag is loaded in plaintext, then passed through an `obfuscate()` function before printing. The plaintext flag is visible directly in the decompiled pseudocode.

---

## 4. Flag Extraction

The flag is embedded as a string literal loaded into a stack variable before obfuscation:

~~~text
poctf{uwsp_1n_w1n3_7h3r3_15_7ru7h}
~~~

No need to reverse the `obfuscate()` function since the input is visible in the decompilation.

---

## Lessons Learned

| # | Lesson | Detail |
|---|--------|--------|
| 1 | Obfuscation is not encryption | If the plaintext is loaded before transformation, it is recoverable |
| 2 | Decompilers show data flow | Following data from initialization to output reveals secrets |
| 3 | Riddles often hint at the technique | "True to false" suggests bit inversion (NOT/XOR) |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID | Context |
|---|---|---|---|
| Defense Evasion | Obfuscated Files or Information | T1027 | Flag obfuscated at runtime but loaded as plaintext first |
| Defense Evasion | Deobfuscate/Decode Files or Information | T1140 | Static analysis recovers the pre-obfuscation plaintext |
| Collection | Data from Local System | T1005 | Sensitive string extracted from binary analysis |

> **CWE-312:** Cleartext Storage of Sensitive Information. The flag is loaded as plaintext in the binary before obfuscation.
> **CWE-693:** Protection Mechanism Failure. Obfuscation applied after plaintext initialization provides no protection.

---

## Remediation and Containment

### Technical Fixes

1. Never load sensitive data as plaintext, even temporarily; use encrypted storage with runtime decryption
2. Derive secrets from external inputs (server challenge, hardware token) rather than embedding them
3. Apply control flow obfuscation to complicate decompilation
4. Use anti-debugging techniques to hinder dynamic analysis

### MITRE D3FEND Countermeasures

- **D3-FE (File Encryption):** encrypt sensitive strings at rest within binaries
- **D3-OBF (Obfuscation):** apply multi-layer obfuscation to prevent straightforward decompilation
- **D3-DA (Dynamic Analysis):** detect debugger attachment and alter behavior

### NIST CSF 2.0

- **Protect (PR.DS):** protect data at rest through encryption, including embedded binary strings
- **Detect (DE.CM):** detect reverse engineering attempts through integrity monitoring
- **Respond (RS.MI):** rotate secrets if binary analysis is suspected

### NIST SP 800-53 Rev. 5

- **SC-28 (Protection of Information at Rest):** encrypt sensitive values within distributed binaries
- **SC-13 (Cryptographic Protection):** use approved algorithms for data protection, not custom obfuscation
- **SA-15 (Development Process, Standards, and Tools):** review build artifacts for exposed secrets

### C2M2

- **ASSET-3:** classify binaries containing secrets as sensitive assets requiring protection
- **THREAT-2:** include reverse engineering resistance in software security requirements

---

Thanks guys!! (❍ᴥ❍ʋ)

---

In wine there is truth, and in decompiled pseudocode there is the flag. When the plaintext is loaded before obfuscation, the decompiler catches it in transit.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

> **Reference:** Adapted from [shivang1209-dot/CTF-Writeups](https://github.com/shivang1209-dot/CTF-Writeups). Original scripts credited to the author.
