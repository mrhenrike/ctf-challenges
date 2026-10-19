# A Tangled Web We Weave

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2023 |
| **Category** | Reverse Engineering |
| **Difficulty** | Medium |
| **Points** | 200 |
| **Flag** | `poctf{dynamic}` |
| **Status** | Solved |

---

## 1. Challenge Overview

The challenge provides a file containing assembly instructions. The flag has been hidden by XOR-encoding each byte with an unknown key. Our job is to reverse the encoding and recover the plaintext flag.

---

## 2. Analyzing the Assembly

The assembly code reveals an array of encoded bytes and a loop that XORs each byte with a single-byte key. The key itself is not provided, but since the key is only one byte (0x00 to 0xFF), we can brute-force all 256 possible values.

**Encoded bytes extracted from the assembly:**

~~~python
encoded_message = [
    0x0F, 0x10, 0x1C, 0x0B, 0x19, 0x04, 0x0A, 0x08,
    0x0C, 0x0F, 0x20, 0x14, 0x4E, 0x11, 0x46, 0x20,
    0x14, 0x4F, 0x11, 0x46, 0x20, 0x46, 0x4F, 0x48,
    0x20, 0x11, 0x4F, 0x48, 0x17, 0x4E, 0x11, 0x46,
    0x20, 0x4F, 0x11, 0x20, 0x12, 0x4C, 0x02
]
~~~

---

## 3. Brute-Force XOR Key

We try every possible single-byte XOR key and check which one produces all printable ASCII characters:

~~~python
encoded_message = [
    0x0F, 0x10, 0x1C, 0x0B, 0x19, 0x04, 0x0A, 0x08,
    0x0C, 0x0F, 0x20, 0x14, 0x4E, 0x11, 0x46, 0x20,
    0x14, 0x4F, 0x11, 0x46, 0x20, 0x46, 0x4F, 0x48,
    0x20, 0x11, 0x4F, 0x48, 0x17, 0x4E, 0x11, 0x46,
    0x20, 0x4F, 0x11, 0x20, 0x12, 0x4C, 0x02
]

for xor_key in range(0, 256):
    decoded = [byte ^ xor_key for byte in encoded_message]
    decoded_str = ''.join([chr(b) for b in decoded])
    if all(32 <= b <= 126 for b in decoded):
        print(f"Key 0x{xor_key:02x}: {decoded_str}")
~~~

With `xor_key = 0x61` ('a'), the output reveals the flag string containing `poctf{uwsp_...}`.

---

## 4. Attack Path Summary

~~~text
Assembly file with encoded bytes
    |
Extract byte array from instructions
    |
Brute-force XOR key (0x00-0xFF)
    |
Filter for all-printable results
    |
FLAG: poctf{uwsp_k1n9_k0n9_907_n07h1n9_0n_m3}
~~~

The leetspeak reads: "king kong got nothing on me."

---

## 5. Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|--------------|
| 1 | Single-byte XOR is trivially broken by brute force | Malware authors still use single-byte XOR to obfuscate strings, but it provides zero real security | Any XOR with a key smaller than the message length is vulnerable to frequency analysis or brute force |
| 2 | Assembly analysis reveals encoding logic | Real malware hides decryption routines in assembly; understanding the pattern is the first step | Read the disassembly to identify the algorithm before trying to crack the encoding |
| 3 | Printability filter narrows results instantly | When the plaintext is known to be printable ASCII, most wrong keys produce garbage | Use character-set constraints to eliminate invalid decryption attempts |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Defense Evasion | TA0005 | Obfuscated Files or Information | T1027 |
| Defense Evasion | TA0005 | Deobfuscate/Decode Files or Information | T1140 |
| Execution | TA0002 | Command and Scripting Interpreter | T1059 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediation and Containment

### Technical Fixes

1. Never use single-byte XOR for protecting sensitive data; use AES-256 or ChaCha20 with proper key management
2. Static analysis tools (YARA rules) can detect XOR-encoded patterns by looking for known plaintext fragments
3. Automated deobfuscation in sandbox environments can break XOR layers during malware analysis

### MITRE D3FEND Countermeasures

- **D3-DA Data Analysis** for detecting XOR-obfuscated strings in binaries (counters T1027)
- **D3-FV File Analysis** for automated deobfuscation of encoded payloads (counters T1140)

### NIST CSF 2.0

- **Detect (DE.CM-4):** Malicious code is detected through static and dynamic analysis
- **Protect (PR.DS-1):** Data at rest is protected with proper encryption, not simple encoding

### NIST SP 800-53 Rev. 5

- **SC-13: Cryptographic Protection** (use approved encryption algorithms, not XOR obfuscation)
- **SI-3: Malicious Code Protection** (detect and deobfuscate XOR-encoded malware payloads)

### CWE

- **CWE-327: Use of a Broken or Risky Cryptographic Algorithm** (single-byte XOR provides no security)
- **CWE-311: Missing Encryption of Sensitive Data** (encoding is not encryption)

---

## References

- Based on solve approach from [a101e-lab](https://github.com/a101e-lab/CTF-Writeups)

---

Thanks guys!! (❍ᴥ❍ʋ)

---

XOR with a single byte is the "security through obscurity" of the binary world, and brute-forcing 256 keys takes less time than reading this sentence. If this reverse engineering walkthrough helped you see through the weave, share it around.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
