# The Consulting Room

**Category:** Cryptography
**Challenge:** The Consulting Room
**CTF:** Pointer Overflow CTF 2026
**Points:** 125 (CRYP 200, Wave 3)
**Result:** Solved

**Flag:**

~~~text
poctf{...}
~~~

---

## 1. Reconnaissance

The challenge presents a patient medical record encrypted with AES (SecureRecord v2.3 archive). A "compliance-review verification endpoint" is still online, which checks whether an arbitrary blob has valid padding. The API:

- **Endpoint:** `POST /challenges/consulting-room/oracle`
- **Auth:** `Authorization: Bearer rBRo2xfG9QhZMA_Gw3u4gXLvEj1XQ_CI`
- **Body:** `{"record": "<hex-encoded ciphertext>"}`
- **Response:** `{"padding": "valid"}` or `{"padding": "invalid"}`
- **Rate limit:** 1,000 requests/minute

The encrypted record (hex):

~~~text
9bed8df35e213ab04833ff160d1b04c5
d7a3aa1394da2622bdfc0d76c85cdaf1
9346be97a8ef7e3e416645f5ec62c758
4b07913ca68f5ba257a82664860347a4
185c5bbbaf88a3b751dc3c7a84cdd4aa
~~~

80 bytes = 5 blocks of 16 (AES-128-CBC). The first block is the IV, leaving 4 blocks (64 bytes) of plaintext to recover.

---

## 2. Identifying the Vulnerability

An endpoint that tells you whether padding is valid or invalid is the textbook setup for a **Padding Oracle Attack** (CVE-2014-3566 concept family, Vaudenay 2002).

In AES-CBC with PKCS#7 padding, each plaintext block is XORed with the previous ciphertext block before encryption. Decryption reverses this. The padding oracle reveals whether the last byte(s) of decrypted plaintext form valid PKCS#7 padding, which leaks one bit of information per query. By systematically modifying the preceding ciphertext block and observing valid/invalid responses, we can recover the intermediate state byte by byte, then XOR with the original ciphertext to get plaintext.

---

## 3. Exploitation

### The Attack Algorithm

For each target block (blocks 1 through 4):

1. Start from the last byte (position 15) and work backward to byte 0
2. For each byte position, try all 256 possible values in the preceding block
3. A "valid" response means we found the intermediate value for that byte
4. XOR the intermediate value with the original ciphertext byte to get plaintext
5. For pad_val == 1 (last byte), verify the guess by also modifying the penultimate byte to rule out false positives

### Concurrent Execution

With a 1,000 req/min rate limit, sequential brute force (up to 256 guesses per byte, 64 bytes) would take too long. The solver uses 8 concurrent threads to fire all 256 guesses in parallel per byte position, with automatic retry on 429 rate-limit responses.

~~~bash
python3 -I padding_oracle.py
~~~

### Output

~~~text
[*] 80 bytes, 5 blocks (4 to decrypt)

[*] Block 1/4...
  -> b'poctf{...partial'

[*] Block 2/4...
  -> b'XYWITBQBDAZLL2.A'

[*] Block 3/4...
  -> b'H4IRJRTFM6VG24F6'

[*] Block 4/4...
  -> b'JYHSOP3RZ}\x06\x06\x06\x06\x06\x06'

[+] PLAINTEXT: poctf{...}
~~~

The last 6 bytes are `\x06` (PKCS#7 padding for 6 bytes). After stripping, the flag is revealed.

---

## 4. Attack Path Summary

~~~text
Identify AES-CBC padding oracle endpoint
    |
Parse 80-byte ciphertext into 5 blocks (IV + 4 data blocks)
    |
For each block: brute-force intermediate state via oracle
    |  -> 256 guesses per byte, 16 bytes per block
    |  -> concurrent requests (8 threads) for speed
    |
XOR intermediate with original ciphertext -> plaintext
    |
Strip PKCS#7 padding -> FLAG
~~~

---

## 5. Lessons Learned

| # | Finding | Key Takeaway |
|---|---|---|
| 1 | Padding validation endpoint exposed | Never expose padding validity to unauthenticated or low-privilege callers; use authenticated-then-decrypt or constant-time MAC-then-decrypt |
| 2 | AES-CBC without integrity check | CBC mode alone does not protect against ciphertext manipulation; use AEAD modes (GCM, ChaCha20-Poly1305) |
| 3 | Rate limit insufficient to prevent attack | 1,000 req/min allows full decryption of 64 bytes in minutes; rate limiting alone cannot mitigate oracle attacks |
| 4 | Concurrent requests bypass time constraints | Threading/async turns a slow byte-by-byte attack into a fast parallel one |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID | Relevance |
|---|---|---|---|
| Credential Access | Exploitation for Credential Access | T1212 | Padding oracle exploits a cryptographic implementation flaw to recover plaintext |
| Collection | Data from Information Repositories | T1213 | The decrypted medical record contains sensitive PII |
| Defense Evasion | Obfuscated Files or Information | T1027 | AES-CBC encryption is used to protect the record, but the oracle negates it |
| Discovery | Network Service Discovery | T1046 | Identifying the padding validation endpoint as the attack vector |

---

## Remediation and Containment

### Technical Fixes

1. Replace AES-CBC with an AEAD mode (AES-GCM, ChaCha20-Poly1305) that provides built-in integrity verification
2. If CBC must be used, apply Encrypt-then-MAC (HMAC-SHA256) and verify the MAC before any decryption attempt
3. Remove or restrict the padding validation endpoint; never expose padding error details to callers
4. Return identical error responses for all decryption failures (padding, MAC, format) to prevent oracle differentiation
5. Implement anomaly detection: hundreds of requests with modified ciphertext blocks indicate an active padding oracle attack

### MITRE D3FEND Countermeasures

- **D3-NTA** (Network Traffic Analysis): detect high-frequency repetitive POST requests with incrementally modified payloads
- **D3-ANET** (API Network Traffic Filtering): rate-limit and monitor cryptographic validation endpoints
- **D3-MAN** (Message Authentication): enforce MAC verification before decryption to eliminate the oracle entirely

### NIST CSF 2.0

- **Protect (PR.DS-2):** data in transit must use authenticated encryption, not unauthenticated CBC
- **Detect (DE.CM-1):** monitor network traffic for patterns consistent with oracle attacks (high request rates to crypto endpoints)
- **Respond (RS.AN-3):** when anomalous crypto endpoint traffic is detected, trigger automated blocking

### NIST SP 800-53 Rev. 5

- **SC-8 (Transmission Confidentiality and Integrity):** use authenticated encryption for all sensitive data in transit
- **SC-13 (Cryptographic Protection):** employ FIPS-validated AEAD modes; plain CBC without MAC is insufficient
- **SI-4 (System Monitoring):** monitor API endpoints for anomalous request patterns indicative of oracle exploitation
- **AU-6 (Audit Record Review, Analysis, and Reporting):** review access logs for repeated failed decryption attempts

### C2M2

- **Domain:** TECHNOLOGY
- **Practice:** Implement cryptographic protections aligned with data sensitivity classification
- **Target MIL:** MIL-3 (managed and measured: automated detection of oracle-style attacks with defined response procedures)

---

Thanks guys!! (❍ᴥ❍ʋ)

---

Padding oracle attacks are a timeless classic in applied cryptography. If you learned something new about CBC byte-flipping from this one, post it and let others benefit too.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
