# Model E1337 v2 Hardened: Writeup (1/1 flag)

**Difficulty:** Expert | **Category:** Web + Crypto

## Challenge Overview

**Context:** Version 2 "Hardened" of the Model E1337 lock. Same Flask architecture as v1, but with two deliberate hardenings: all configuration endpoints were removed (no XXE available) and the PRNG was strengthened with 3 transformation rounds per bit instead of 1.

**What you face:** Without XXE to read the source code, you must infer the PRNG algorithm from empirical observations of `/unlock` (which still leaks the expected code). With the PRNG outputs, you must recover the seed using linear algebra over GF(2): Z3 still works but is significantly slower.

**Vulnerabilities exploited:**
- Information Leakage via Error Message (CWE-209): `/unlock` with wrong code reveals the expected code
- Weak PRNG / Seed Recovery (CWE-338): 32-bit seed still recoverable, but requires GF(2) or Z3 with larger constraints

**What you learn:**
- Partial "hardening" does not fix the fundamental vulnerability: if the PRNG seed is 32-bit and there is an output oracle, it is still breakable
- GF(2) (linear algebra over binary field) is the correct approach for PRNGs based on XOR/shift operations
- Empirical PRNG analysis without source code: observe outputs to infer the algorithm structure
- The complexity difference between Z3 (generic solving) and GF(2) (exploiting linear structure)

---

## Summary

Same architecture as v1 (Flask + custom PRNG) but with two hardenings:
1. All admin/config endpoints removed (no XXE to read source code)
2. The PRNG uses `next(64)` instead of `next(26)`, and the inner loop runs 3× per bit

The vulnerability remains: `/unlock` reveals the expected code when wrong.

## PRNG Algorithm (v2 Hardened)

```python
# setup: same as v1: 32-bit seed, 64-bit state
def setup(seed):
    state = 0
    for i in range(16):
        cur = seed & 3; seed >>= 2
        state = (state << 4) | ((state & 3) ^ cur)
        state |= cur << 2

# next: 3 transformation rounds per bit (v1 did only 1)
def next(bits):
    ret = 0
    for i in range(bits):
        ret <<= 1
        ret |= state & 1
        for _ in range(3):          # ← DIFFERENCE IN v2
            state = (state << 1) ^ (state >> 61)
            state &= 0xFFFFFFFFFFFFFFFF
            state ^= 0xFFFFFFFFFFFFFFFF
            for j in range(0, 64, 4):
                cur = (state >> j) & 0xF
                cur = (cur>>3)|((cur>>2)&2)|((cur<<3)&8)|((cur<<2)&4)
                state ^= cur << j
    return ret
```

## Why 32-bit brute-force does not work for v2

The PRNG (with 3 rounds/bit) is **linear over GF(2)**. Brute-force tries to recover the seed assuming V1 is the 1st call. Since the server starts before probing (earlier calls not visible), V1 may not be call #1. The GF(2) solver does not depend on position: it recovers the full 64-bit state from any 64-bit output.

## Attack: GF(2) Linear Algebra State Recovery

### Why it works

The PRNG is linear over GF(2): state → next_state is a linear transformation. With 64 bits of output, we have 64 equations in 64 unknowns (the initial state bits) → unique solution via Gaussian elimination.

### Procedure

```bash
BASE="https://<instance>.ctf.hacker101.com"

# Probe 1: get V_n
curl -s "$BASE/unlock" -d "code=0"
# Code incorrect.  Expected 05966999701691202788  → V1=5966999701691202788

# Probe 2: get V_{n+1}
curl -s "$BASE/unlock" -d "code=0"
# Code incorrect.  Expected 03602746079873202915  → V2=3602746079873202915

# (additional probes for verification: V3, V4, V5)
```

### Solver

```python
class RNGState:
    # 1. Represents state as 64 symbolic variables (lists of sets of indices)
    # 2. Symbolically simulates PRNG: each output bit = XOR of initial bits
    # 3. Solves GF(2) equation system via Gaussian elimination
    # 4. Predicts next number by substituting resolved values
    ...

rng = RNGState([V1])  # only 1 output of 64 bits is sufficient
v6  = rng.predict_next_number()  # after advancing 4x to reach call 6
# Submit v6
```

### Verification

| Call | Expected value | Predicted | Match |
|------|----------------|-----------|-------|
| V4 | 545337045656770057 | 545337045656770057 | ✓ |
| V5 | 14622965117510836930 | 14622965117510836930 | ✓ |
| V6 | (unknown) | 10322713006950444088 | ✓ submit |

## Result

```
curl -s "$BASE/unlock" -d "code=10322713006950444088"
# Unlocked successfully.  Flag: ^FLAG^01a30081fa302d4743705cd9239a9a1a7e98acf3456aa7f1b4ca432076b06787$FLAG$
```

**Flag:** `01a30081fa302d4743705cd9239a9a1a7e98acf3456aa7f1b4ca432076b06787`

---

## Lessons Learned

1. Partial hardening (removing XXE, adding rounds) does not fix the fundamental vulnerability if the seed space is small
2. GF(2) linear algebra is the correct tool for XOR/shift-based PRNGs: one 64-bit output is sufficient to recover the full state
3. Error messages that leak expected values create an oracle that invalidates any PRNG-based authentication
4. 32-bit seeds are always brute-forceable regardless of the number of transformation rounds

---

## MITRE ATT&CK Mapping

| ID | Technique | Tactic | How it was used |
|----|-----------|--------|----------------|
| T1190 | Exploit Public-Facing Application | Initial Access | Information leakage via `/unlock` error responses |
| T1588.005 | Obtain Capabilities: Exploits | Resource Development | GF(2) solver for 64-bit PRNG state recovery from outputs |
| T1040 | Network Sniffing | Collection | Captured PRNG outputs via repeated probes to `/unlock` |

## Remediation and Containment

### Technical Fixes

1. **Error leakage:** Never reveal the expected code; return only "incorrect" or "correct"
2. **PRNG:** Replace with CSPRNG (`secrets.token_bytes()` or HMAC-OTP)
3. **Rate limiting:** Limit `/unlock` attempts per session to prevent output harvesting
4. **Seed size:** Even with stronger PRNG rounds, 32-bit seed = brute-forceable; use 128+ bits

### OWASP Top 10 2021

| ID | Category | Relevance |
|----|----------|-----------|
| A02:2021 | Cryptographic Failures | 32-bit PRNG seed; linear (GF(2)) structure allows algebraic recovery |
| A04:2021 | Insecure Design | Error response leaks the expected code, creating an output oracle |

### CWE

| ID | Name | Relevance |
|----|------|-----------|
| CWE-338 | Use of Cryptographically Weak PRNG | 32-bit seed; custom non-cryptographic generator |
| CWE-209 | Error Message Containing Sensitive Information | `/unlock` reveals the expected code |

### MITRE D3FEND Countermeasures

| ID | Technique | Application |
|----|-----------|-------------|
| D3-MFA | Multi-factor Authentication | Replace custom rolling code with HMAC-OTP (RFC 6238) |
| D3-AL | Audit Logging | Log all unlock attempts; alert on repeated failures from same source |
| D3-SPP | Strong Password Policy | Enforce minimum entropy for authentication secrets (128+ bits) |

### NIST CSF 2.0

| Function | Category | Application |
|----------|----------|-------------|
| PR (Protect) | PR.DS | Use cryptographically secure random number generators |
| PR (Protect) | PR.AC | Rate-limit unlock attempts; lock out after threshold |
| DE (Detect) | DE.CM | Detect patterns of systematic code probing |

### NIST SP 800-53 Rev. 5

| Control | Title | Application |
|---------|-------|-------------|
| SC-13 | Cryptographic Protection | CSPRNG with 128+ bit seeds; HMAC-OTP for rolling codes |
| SI-11 | Error Handling | Generic error responses; never reveal expected values |
| AC-7 | Unsuccessful Logon Attempts | Lock account or endpoint after repeated failed unlock attempts |
| IA-5 | Authenticator Management | Manage authenticators with sufficient entropy |

### C2M2

| Domain | Practice | MIL | Application |
|--------|----------|-----|-------------|
| ACCESS | Access Control Management | MIL-2 | Rate limiting and lockout on authentication endpoints |
| ASSET | Asset, Change, and Configuration Management | MIL-2 | Review cryptographic implementations for adequate key sizes |

---

## Final Thoughts

Thanks guys!! (❍ᴥ❍ʋ)

---

Model E1337 v2 "Hardened" proves that hardening without addressing the root cause is theater: adding more PRNG rounds and removing XXE still leaves a 32-bit seed and an output oracle. The correct fix is not to make the PRNG harder to break; it is to use a cryptographically secure one and stop leaking expected codes. GF(2) linear algebra makes the "hardened" version just as trivial to solve as v1.

Follow along for more advanced crypto and web exploitation writeups:

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
