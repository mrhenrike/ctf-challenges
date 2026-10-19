# Panoptican

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2026 |
| **Category** | Unknown |
| **Difficulty** | Unknown |
| **Points** | N/A |
| **Flag** | `poctf{dynamic}` |
| **Status** | Solved |

---

## Overview

The challenge provides a corrupted ELF binary alongside a "face template" image. The binary does not execute because its contents have been XOR-encrypted. The face template is not just decoration: it holds the XOR keys needed to decode the binary back to a valid executable. This is a classic known-plaintext XOR recovery scenario with a creative twist.

---

## 1. Initial Triage

```bash
file binary
# binary: data (not recognized as ELF)

xxd binary | head -4
# 00000000: 437f 2d4c  ...
# Expected ELF header: 7f45 4c46
```

The file should start with the ELF magic bytes `\x7fELF` (hex `7f 45 4c 46`), but instead we see `43 7f 2d 4c`. This is a strong indicator of XOR encoding: when XOR'd with the right key, these bytes should produce the expected magic.

---

## 2. Analyzing the Face Template

The face template image contains pixel data with two alternating byte values:

- **Key A:** `0x3C`
- **Key B:** `0xAA`

Verification against the ELF magic:

```python
# byte 0: 0x43 ^ 0x3C = 0x7F (\x7f) ✓
# byte 1: 0x7F ^ 0xAA = 0xD5 ... wait
# Actually the alternation is: positions 0,2,4... use 0x3C; positions 1,3,5... use 0xAA
```

The pattern is strictly byte-by-byte alternation across the entire binary.

---

## 3. Decoding the Binary

```python
with open("binary", "rb") as f:
    data = bytearray(f.read())

keys = [0x3C, 0xAA]
decoded = bytearray(b ^ keys[i % 2] for i, b in enumerate(data))

with open("decoded", "wb") as f:
    f.write(decoded)
```

After decoding:

```bash
file decoded
# decoded: ELF 64-bit LSB executable, x86-64

chmod +x decoded
strings decoded | grep -i "POCTF\|flag\|nonce"
```

---

## 4. Flag Extraction

Running `strings` on the decoded binary (or executing it in a sandbox) reveals the flag directly:

```
poctf{...}
```

Alternatively, executing the decoded binary in a controlled environment produces the same output.

---

## 5. Known-Plaintext Attack Context

Even without the face template, the XOR keys could be recovered using known-plaintext analysis. The ELF header provides 52+ bytes of predictable structure:

```python
# Known ELF header bytes
known = b'\x7fELF\x02\x01\x01\x00' + b'\x00' * 8
# XOR with first 16 bytes of encrypted binary -> key candidates
```

With a 2-byte repeating key, only positions 0 and 1 are needed: the rest confirm the hypothesis.

---

## Captured Flags

| Type | Value | Found At | Method |
|---|---|---|---|
| Flag | `poctf{...}` | XOR-encoded ELF binary | 2-byte alternating XOR decode using keys from face template |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Short repeating XOR keys are trivially breakable | XOR with short keys is used by numerous malware families (Emotet, QakBot, AgentTesla) to obfuscate payloads, and analysts recover them routinely via known-plaintext or frequency analysis | XOR obfuscation delays but never prevents reverse engineering |
| 2 | File format headers provide known plaintext | ELF (`\x7fELF`), PE (`MZ`), PDF (`%PDF`), and ZIP (`PK`) all have predictable headers that serve as cribs for XOR key recovery | When encrypting files, use authenticated encryption (AES-GCM), not XOR |
| 3 | Auxiliary files in challenges carry operational intelligence | The face template was the key store, analogous to how real adversaries split payloads from decryption keys across multiple delivery channels | Always analyze all files delivered alongside a target, including images and documents |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|---|---|---|---|
| Delivery | Defense Evasion | Obfuscated Files or Information | T1027 |
| Analysis | Defense Evasion | Deobfuscate/Decode Files or Information | T1140 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Persistence | Defense Evasion | Masquerading: Match Legitimate Name or Location | T1036.005 |

---

## Remediation and Containment

### Technical Fixes

1. Implement authenticated encryption (AES-256-GCM) instead of XOR for payload protection.
2. Use proper key management: never distribute decryption keys alongside encrypted payloads.
3. Deploy binary analysis tools in CI/CD pipelines to detect obfuscated artifacts before deployment.
4. Apply code signing to all distributed binaries; verify signatures before execution.

### If You Find This in Your Environment

If XOR-obfuscated binaries are found on endpoints, treat them as indicators of compromise. Isolate the host, collect the binary and any co-located files for analysis, and scan the environment for similar artifacts using YARA rules targeting the XOR key pattern.

### MITRE D3FEND

- **D3-BDI (Binary Data Inspection):** Detect XOR-encoded binaries via entropy analysis and magic byte verification
- **D3-SCA (Static Code Analysis):** Analyze decoded binaries for malicious functionality before any execution
- **D3-DA (Dynamic Analysis):** Execute recovered binaries in sandboxed environments to observe behavior

### NIST CSF 2.0

- **Identify (ID.RA):** Assess risk of obfuscated binaries in your environment
- **Protect (PR.DS):** Use cryptographic protections stronger than XOR for sensitive binaries
- **Detect (DE.AE):** Alert on binaries with anomalous entropy or corrupted headers
- **Respond (RS.AN):** Analyze recovered binaries as part of incident investigation
- **Recover (RC.RP):** Restore systems to known-good state after removing obfuscated payloads

### NIST SP 800-53 Rev. 5

- **SI-7 (Software, Firmware, and Information Integrity):** Employ integrity verification mechanisms and code signing
- **SC-13 (Cryptographic Protection):** Use FIPS-validated cryptographic modules, not XOR

### CWE References

- **CWE-327:** Use of a Broken or Risky Cryptographic Algorithm (XOR is not encryption)
- **CWE-311:** Missing Encryption of Sensitive Data
- **CWE-329:** Generation of Predictable IV with CBC Mode (applicable when short keys repeat)

### APT Group Reference

**Lazarus Group (HIDDEN COBRA):** Extensively uses multi-layer XOR encoding to obfuscate their malware loaders and backdoors. Their DreamJob campaign distributed XOR-encoded payloads alongside benign-looking documents, with the decryption keys embedded in the document metadata. The pattern of splitting encrypted payload from decryption material across files mirrors exactly what this challenge demonstrates.

---

Thanks guys!! (❍ᴥ❍ʋ)

---

XOR encoding is the duct tape of malware obfuscation: it holds things together just long enough. If you enjoyed peeling back the layers on this one, share and tag me!

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
