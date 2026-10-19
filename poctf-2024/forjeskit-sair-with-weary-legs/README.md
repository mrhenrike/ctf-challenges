# Forjeskit Sair with Weary Legs

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2024 |
| **Category** | Reverse Engineering |
| **Difficulty** | Expert |
| **Points** | 400 |
| **Flag** | `poctf{uwsp_4ll_7h47_gl1773r5}` |
| **Status** | Solved |

---

## 1. Challenge Overview

A PyInstaller-packed Windows executable that prints an encrypted flag hash (`bd7e9dad4a5fe0e7911f93cb1bf5a321`). The packed Python script uses multiple layers of obfuscation and AES-CBC encryption. Recovery requires unpacking the binary, deobfuscating the Python code, and implementing the decryption chain.

**Files:** `Reverse400.exe` (Windows PyInstaller binary)

---

## 2. Unpacking PyInstaller

Extracted the binary contents using [pyinstxtractor](https://github.com/extremecoders-re/pyinstxtractor):

~~~bash
python pyinstxtractor.py Reverse400.exe
~~~

Found `Reverse400.pyc` among the extracted files. Decompiled the `.pyc` bytecode using [pycdc](https://github.com/zrax/pycdc).

---

## 3. Deobfuscation

The decompiled Python code is heavily obfuscated with:

- Lambda-based `setattr` on `__builtins__` for name mangling
- Variable names like `IIlII`, `lIlIl`, `lllllllllllllll`
- Recursion limit set to 100,000,000
- Multiple import indirections

After manual deobfuscation, the core operations became clear:

1. **XOR with 42:** a byte-by-byte XOR operation
2. **Bit-shift transformation:** rotation based on key and IV values
3. **AES-CBC decryption:** standard AES with a 16-byte key
4. **Final XOR pass:** another round of XOR with 42

---

## 4. Decryption Parameters

Extracted from the deobfuscated code:

- **Encrypted flag:** `fa21c9c2596099915dbc7845c941c14e81594b5c4f69177cc4059da11e782e0b`
- **Key (hex):** `504f43544632303234` ("POCTF2024", padded to 16 bytes)
- **IV (hex):** `437261636b3430302d58` ("Crack400-X", padded to 16 bytes)

---

## 5. Decryption Implementation

The [solve script](scripts/script.py) chains the operations in reverse:

~~~python
from Crypto.Cipher import AES

def xor_42(data):
    return ''.join(chr(byte ^ 42) for byte in data)

def transform(letter, key):
    return (letter >> key) | (letter << (8 - key)) & 255

def process(text, key, iv):
    result = bytearray()
    for index, letter in enumerate(text):
        shift_value = (key[index % len(key)] + iv[index % len(iv)]) % 8
        result.append(transform(letter, shift_value))
    return result

def decrypt(ciphertext, key, iv):
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return cipher.decrypt(ciphertext)

encrypted_flag = bytes.fromhex('fa21c9c2596099915dbc7845c941c14e81594b5c4f69177cc4059da11e782e0b')
key = bytes.fromhex('504f43544632303234').ljust(16, b'\x00')
iv = bytes.fromhex('437261636b3430302d58'.ljust(32, '0'))

decrypted_data = decrypt(encrypted_flag, key, iv)
processed_data = process(decrypted_data, key, iv)
final_result = xor_42(processed_data)
print(final_result)
~~~

Output: `poctf{uwsp_4ll_7h47_gl1773r5}`

---

## Lessons Learned

| # | Lesson | Detail |
|---|--------|--------|
| 1 | PyInstaller binaries are fully recoverable | pyinstxtractor + pycdc recovers the original Python |
| 2 | Python obfuscation slows but does not prevent analysis | Manual deobfuscation reveals the algorithm |
| 3 | Multi-layer crypto chains require ordered reversal | XOR, transform, AES must be reversed in correct sequence |
| 4 | Key material derived from challenge context | "POCTF2024" and "Crack400" provide strong hints |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID | Context |
|---|---|---|---|
| Defense Evasion | Obfuscated Files or Information: Software Packing | T1027.002 | Python script packed with PyInstaller |
| Defense Evasion | Obfuscated Files or Information | T1027 | Multi-layer obfuscation (name mangling, lambda abuse) |
| Defense Evasion | Deobfuscate/Decode Files or Information | T1140 | Unpacking, decompiling, deobfuscating, and decrypting |

> **CWE-321:** Use of Hard-coded Cryptographic Key. AES key and IV are embedded in the script as hex constants.
> **CWE-327:** Use of a Broken or Risky Cryptographic Algorithm. AES-CBC is used correctly but the key is exposed.

---

## Remediation and Containment

### Technical Fixes

1. Do not embed encryption keys in client-side code, even when packed/obfuscated
2. Use server-side decryption with proper authentication
3. If client-side crypto is required, derive keys from hardware tokens or secure enclaves
4. Apply native code compilation instead of Python packaging for stronger obfuscation

### MITRE D3FEND Countermeasures

- **D3-OBF (Obfuscation):** use native code obfuscation (LLVM-based) instead of Python name mangling
- **D3-FE (File Encryption):** implement proper key management external to the application
- **D3-DA (Dynamic Analysis):** detect unpacking tools and decompilers through anti-analysis

### NIST CSF 2.0

- **Protect (PR.DS):** manage encryption keys through external key management systems
- **Protect (PR.AC):** require authentication before key material is accessible
- **Detect (DE.CM):** detect PyInstaller unpacking and bytecode decompilation attempts

### NIST SP 800-53 Rev. 5

- **SC-12 (Cryptographic Key Establishment and Management):** use external key management, not embedded keys
- **SC-13 (Cryptographic Protection):** while AES is approved, key exposure negates the protection
- **SA-11 (Developer Testing and Evaluation):** test packed applications against unpacking attack chains

### C2M2

- **THREAT-3:** include PyInstaller unpacking in application security assessments
- **RISK-4:** classify embedded key material as critical exposure requiring remediation

---

Thanks guys!! (❍ᴥ❍ʋ)

---

All that glitters is not gold, but sometimes it is a well-hidden flag behind layers of Python obfuscation, PyInstaller packing, and AES-CBC. The journey from packed .exe to plaintext flag is what makes RE 400 challenges rewarding.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

> **Reference:** Adapted from [shivang1209-dot/CTF-Writeups](https://github.com/shivang1209-dot/CTF-Writeups). Original scripts credited to the author.
