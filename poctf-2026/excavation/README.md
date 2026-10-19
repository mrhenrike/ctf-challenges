# Excavation

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2026 |
| **Category** | Reverse Engineering |
| **Difficulty** | Easy |
| **Points** | 100 |
| **Flag** | `poctf{dynamic}` |
| **Status** | Solved |

---

## 1. Reconnaissance

The challenge provides save files from a fictional dark-fantasy RPG called "Sepulchure of the Undying." Three reference saves (`sample1.sav`, `sample2.sav`, `sample3.sav`) come from canonical playthroughs, and a fourth team-specific file (`team.sav`) contains the flag. The file format is undocumented, and the objective is a 16-character alphanumeric token.

All four files share a 12-byte binary header:

~~~text
9e e1 c7 21 | 02 00 02 00 | <u32LE total_len>
~~~

The first 4 bytes are a magic number, the next 4 are a version tag, and the final field is the total file size as a little-endian 32-bit integer. Everything after byte 12 is payload.

---

## 2. Byte-Level Analysis

The payload bytes have high entropy but are not uniformly distributed. Index of Coincidence (IOC) values ranged from 0.008 to 0.010 across the files, well above the 0.0039 expected for truly random data. This suggested lightweight obfuscation rather than proper encryption or compression.

A search for repeated byte sequences in the payload turned up identical 46-byte regions separated by exactly 48 bytes in `sample2` and `sample3`. The greatest common divisor of all observed repeat distances was:

~~~text
gcd(48, 48, 304, 24, 56) = 8
~~~

This eliminated CBC, CFB, ECB, CTR, and position-dependent stream ciphers. Identical plaintext blocks producing identical ciphertext at different positions can only happen with a repeating-key transform.

---

## 3. Key Recovery

The cipher was a simple repeating XOR:

~~~text
C[i] = P[i] XOR K[i mod 8]
~~~

Key recovery required only 8 x 256 = 2048 frequency-scored candidates per file. For each residue position `r` (0 through 7), the key byte was the one that maximized an English plaintext score when XOR'd against every 8th byte of the payload:

~~~python
for r in range(8):
    chunk = payload[r::8]
    key[r] = max(range(256), key=lambda k: score(bytes(b ^ k for b in chunk)))
~~~

The scoring function weighted common ASCII characters: space scored highest (18.0), then `e`, `t`, `a`, and so on, with non-printable bytes scoring negative. This simple heuristic produced clean plaintext on every file.

Recovered key for the team save:

~~~text
f44d2667d1c07841
~~~

---

## 4. Save Format Reversing

Decrypted payload contained readable game data: player names, item names, item descriptions, and stat fields. Each inventory item followed a binary record format:

~~~text
0x10 | item_index | field_1 | field_2 | name_len | name_bytes | suffix | 0x00 | description
~~~

The sample saves contained 5, 10, and 13 items respectively; the team save had exactly 16, matching the expected token length.

---

## 5. Acrostic Extraction

The sample saves provided confirmation: their item names spelled out coherent words when you took the first character of each name in stored index order:

~~~text
sample1 (5 items):  TORCH
sample2 (10 items): SILVERMOON
sample3 (13 items): NIGHTENDSSOON
~~~

Applying the same technique to the team file's 16 items:

~~~text
Jarful of teeth       -> J
Quartering blade      -> Q
2-star runic band     -> 2
Marrow-quill pen      -> M
3-pronged rowan fork  -> 3
Lead-bound envelope   -> L
7-day candle          -> 7
Ash-glazed lantern    -> A
Doubling mirror       -> D
Blackbone flute       -> B
7-day candle          -> 7
Zinc-etched sigil     -> Z
4-quadrant ephemeris  -> 4
Zinc-etched sigil     -> Z
Ghost-key             -> G
Xylophone plate       -> X
~~~

Token:

~~~text
JQ2M3L7ADB7Z4ZGX
~~~

---

## 6. Verification

The full pipeline was deterministic from the raw `.sav` file:

1. Parse the 12-byte header
2. Extract the encrypted payload
3. Recover the 8-byte XOR key via frequency analysis
4. Decrypt with repeating XOR
5. Locate 0x10 item markers, parse `name_len` and `name`
6. Sort items by stored index
7. Concatenate first characters

Running the pipeline produced `JQ2M3L7ADB7Z4ZGX` consistently.

---

## 7. Flag Submission

The challenge accepted both the raw 16-character token and the wrapped form. Submitted `JQ2M3L7ADB7Z4ZGX` and received:

~~~text
>> ACK :: Correct.
~~~

---

## MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID | Context |
|---|---|---|---|
| Defense Evasion | Obfuscated Files or Information | T1027 | Save file payload XOR-encrypted with repeating 8-byte key |
| Defense Evasion | Deobfuscate/Decode Files or Information | T1140 | Frequency analysis recovers XOR key from ciphertext statistics |
| Collection | Data from Local System | T1005 | Structured game data (inventory items) extracted from save file |
| Resource Development | Obtain Capabilities: Tool | T1588.002 | Custom Python solver built for key recovery and save parsing |

> **CWE-327:** Use of a Broken or Risky Cryptographic Algorithm. Repeating-key XOR provides no real confidentiality; identical plaintext blocks produce identical ciphertext regardless of position.
> **CWE-321:** Use of Hard-coded Cryptographic Key. The 8-byte key was static per save file with no key derivation function.

---

## Remediation and Containment

### Technical Fixes

1. Replace repeating-key XOR with authenticated encryption (AES-GCM or ChaCha20-Poly1305) for save file protection
2. Derive per-file encryption keys using a KDF (PBKDF2, Argon2) with a unique salt
3. Add HMAC integrity checks to detect save file tampering
4. Store sensitive data (flags, tokens) server-side rather than in client save files

### MITRE D3FEND Countermeasures

- **D3-FE (File Encryption):** use modern symmetric encryption instead of XOR obfuscation
- **D3-DA (Dynamic Analysis):** monitor for automated save file parsing tools in runtime
- **D3-FCOA (File Content Analysis):** validate save file integrity before loading

### NIST CSF 2.0

- **Protect (PR.DS):** encrypt data at rest using approved cryptographic algorithms, not custom XOR
- **Detect (DE.CM):** detect tampering with save file integrity (hash comparison)
- **Respond (RS.MI):** invalidate save files that fail integrity checks

### NIST SP 800-53 Rev. 5

- **SC-13 (Cryptographic Protection):** use FIPS-approved or recommended cryptographic algorithms
- **SC-28 (Protection of Information at Rest):** protect stored data with authenticated encryption
- **SI-7 (Software, Firmware, and Information Integrity):** verify save file integrity before processing

---

Thanks guys!! (❍ᴥ❍ʋ)

---

Reverse engineering save files and cracking XOR keys is peak puzzle energy. If this one clicked for you, hit me up on socials. Love hearing how other people approach these challenges.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
