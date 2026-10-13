# Model E1337 v2 Hardened — Writeup (1/1 flag)

**Difficulty:** Expert | **Category:** Web + Crypto

## Challenge Overview

**Context:** Version 2 "Hardened" of the Model E1337 lock. Same Flask architecture as v1, but with two deliberate hardenings: all configuration endpoints were removed (no XXE available) and the PRNG was strengthened with 3 transformation rounds per bit instead of 1.

**What you face:** Without XXE to read the source code, you must infer the PRNG algorithm from empirical observations of `/unlock` (which still leaks the expected code). With the PRNG outputs, you must recover the seed using linear algebra over GF(2) — Z3 still works but is significantly slower.

**Vulnerabilities exploited:**
- Information Leakage via Error Message (CWE-209) — `/unlock` with wrong code reveals the expected code
- Weak PRNG / Seed Recovery (CWE-338) — 32-bit seed still recoverable, but requires GF(2) or Z3 with larger constraints

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
# setup: same as v1 — 32-bit seed, 64-bit state
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

The PRNG (with 3 rounds/bit) is **linear over GF(2)**. Brute-force tries to recover the seed assuming V1 is the 1st call. Since the server starts before probing (earlier calls not visible), V1 may not be call #1. The GF(2) solver does not depend on position — it recovers the full 64-bit state from any 64-bit output.

## Attack — GF(2) Linear Algebra State Recovery

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
