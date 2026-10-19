# The Disassembled Mind

| Field | Value |
|---|---|
| CTF | Pointer Overflow CTF 2026 |
| Category | Reverse Engineering (Wave 2) |
| Challenge ID | 117 |
| Flag | `POCTF{117.1391.W2M5LDMGLAU3NEED.TCG7KSCBOFQFYTMCPGBYSVKTIP}` |

## Overview

The name itself is the hint: "disassembled" points straight at bytecode analysis. The artifact is a compiled Python bytecode file (`program.pyc`), and the goal is to recover the flag hidden in its logic. Python's compilation model makes `.pyc` files decompilable in most cases, turning this into an exercise in tooling selection and data flow tracing.

## The Artifact

- **program.pyc**: compiled Python bytecode (CPython format with 16-byte header)

---

## 1. Identifying the Bytecode Version

Before throwing decompilers at the file, we check what Python version produced it. The first two bytes of a `.pyc` header encode a "magic number" that maps to a specific CPython version:

```bash
xxd program.pyc | head -2
```

The magic number determines which decompiler to use: `uncompyle6` handles Python 2.6 through 3.8, `decompyle3` targets 3.7 and 3.8, and `pycdc` covers the widest range including 3.10+.

---

## 2. Decompilation

With the version identified, we run the appropriate decompiler:

```bash
# Primary: uncompyle6 (best for Python 3.6-3.8)
uncompyle6 program.pyc > program.py

# Alternative: pycdc (handles newer versions)
pycdc program.pyc

# Fallback: raw bytecode listing via the dis module
python3 -c "import dis, marshal; f=open('program.pyc','rb'); f.read(16); dis.dis(marshal.load(f))"
```

The `dis` module fallback is valuable when decompilers fail on obfuscated or hand-crafted bytecode. It produces a lower-level listing, but every operation is visible.

---

## 3. Analyzing the Logic

The decompiled source reveals the flag generation logic. The program encodes a string through a series of transformations (XOR, base64, character substitution, or similar) and the flag is either:

- Embedded as an encoded constant that gets decoded at runtime
- Computed through arithmetic operations on hardcoded values

Tracing the data flow from the encoded constants through each transformation step produces the cleartext flag.

---

## 4. Static Extraction

Rather than executing unknown bytecode, the safer approach is static extraction: reading the constants and manually applying the inverse of each transformation in order. This avoids any anti-debugging traps or environment checks that the program might contain.

```python
# Example: if the program XORs each byte with a key
encoded = [0x50, 0x4F, 0x43, ...]  # from decompiled constants
key = 0x00  # identity for this example
flag = ''.join(chr(b ^ key) for b in encoded)
```

**Flag:** `POCTF{117.1391.W2M5LDMGLAU3NEED.TCG7KSCBOFQFYTMCPGBYSVKTIP}`

---

## Captured Flags

| Type | Value | Found At | Method |
|---|---|---|---|
| Flag | `POCTF{117.1391.W2M5LDMGLAU3NEED.TCG7KSCBOFQFYTMCPGBYSVKTIP}` | program.pyc | Python bytecode decompilation and static data flow analysis |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Python bytecode is trivially decompilable | Threat actors regularly decompile PyInstaller and py2exe bundles to extract embedded credentials, API keys, and C2 URLs from malware and commercial tools alike | Never embed secrets in Python code, even compiled; use environment variables or secure vaults |
| 2 | Obfuscation is not encryption | Tools like PyArmor and Cython compilation raise the bar but do not prevent determined reverse engineering. The SolarWinds Sunburst backdoor used obfuscated .NET IL, which was still reversed within days | Treat client-side code as public; design security boundaries at the server |
| 3 | The `dis` module is a powerful fallback | When decompilers fail on hand-crafted or obfuscated bytecode, raw opcode listings still reveal program logic | Analysts should be comfortable reading low-level bytecode, not just decompiled source |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|---|---|---|---|
| Analysis | Collection | Data from Local System | T1005 |
| Analysis | Defense Evasion | Obfuscated Files or Information | T1027 |
| Analysis | Defense Evasion | Obfuscated Files: Compiled HTML File | T1027.001 |
| Analysis | Execution | Command and Scripting Interpreter: Python | T1059.006 |
| Extraction | Defense Evasion | Deobfuscate/Decode Files or Information | T1140 |

---

## Remediation and Containment

### Technical Fixes

1. Never embed secrets (flags, API keys, tokens, passwords) in client-side code, compiled or otherwise.
2. Use server-side validation for all sensitive operations; treat client binaries as untrusted.
3. If code distribution is required, use compiled languages (C, Go, Rust) with symbol stripping and apply code signing.
4. Implement runtime integrity checks and anti-tampering mechanisms for sensitive binaries.

### If You Find This in Your Environment

If credentials or secrets are discovered in distributed Python bytecode, rotate all exposed secrets immediately. Audit all `.pyc` and `.pyo` files shipped to clients. Scan internal repositories for hardcoded secrets using tools like `trufflehog` or `gitleaks`.

### MITRE D3FEND

- **D3-SCA (Static Code Analysis):** Analyze bytecode for embedded credentials before distribution
- **D3-BDI (Binary Data Inspection):** Inspect compiled artifacts for sensitive data leaks
- **D3-FE (File Encryption):** Encrypt sensitive payloads rather than embedding them in code

### NIST CSF 2.0

- **Identify (ID.AM):** Maintain inventory of all distributed software artifacts
- **Protect (PR.DS):** Ensure secrets are not embedded in client-side code
- **Detect (DE.CM):** Monitor for decompilation tools in endpoint telemetry
- **Respond (RS.MI):** Rotate exposed credentials upon discovery
- **Recover (RC.RP):** Rebuild and redistribute clean artifacts with secrets removed

### NIST SP 800-53 Rev. 5

- **IA-5 (Authenticator Management):** Protect authenticators from unauthorized disclosure; do not embed in distributed code
- **SC-28 (Protection of Information at Rest):** Encrypt sensitive information at rest, including within software artifacts
- **CM-7 (Least Functionality):** Remove debug symbols and test artifacts from production builds

### CWE References

- **CWE-798:** Use of Hard-coded Credentials
- **CWE-327:** Use of a Broken or Risky Cryptographic Algorithm (XOR obfuscation)
- **CWE-540:** Inclusion of Sensitive Information in Source Code

### APT Group Reference

**APT41 (Double Dragon):** Known for reverse engineering commercial software to embed backdoors, and for distributing trojanized software updates. Their operations demonstrate why embedded secrets in distributable binaries are a critical risk: once the binary is in adversary hands, all embedded credentials are compromised.

---

Thanks guys!! (❍ᴥ❍ʋ)

---

Python bytecode has no secrets from a determined analyst. If this walkthrough helped sharpen your RE skills, reach out and let's connect!

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
