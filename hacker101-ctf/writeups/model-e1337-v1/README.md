# Model E1337 v1 — Rolling Code Lock — Writeup (2/2)

**Difficulty:** Hard  
**Category:** Web (XXE, PRNG Seed Recovery)  
**Flags:** 2/2 (complete)  
**Platform:** Hacker101 CTF

> **Note:** The full writeup is in `model-e1337/WRITEUP.md` (the folder with the developed solution).
> This folder has `PATH.md` with the external references used to solve the challenge.

---

## Challenge Overview

**Context:** Version 1 of the Model E1337 Rolling Code Lock. A Flask application simulating an electronic lock: accepts XML configuration via `/set-config` and validates numeric codes at `/unlock`. The correct code changes on every attempt using a custom PRNG with a 32-bit seed.

**What you face:** A lock that requires the right code to open, but the code changes constantly. To solve it: (1) exfiltrate the source code via XXE on the XML configuration endpoint, (2) analyze the custom PRNG and recover the seed from two consecutive outputs using the Z3 SMT solver.

**Vulnerabilities exploited:**
- XXE (CWE-611) — `/set-config` uses `xml.sax` without disabling external entities; exfiltrates `main.py` and `rng.py`
- Weak PRNG / Seed Recovery (CWE-338) — 32-bit seed recoverable via Z3 SMT solver or linear algebra over GF(2)
- Information Leakage via Error Message — `/unlock` with wrong code reveals the expected code

**What you learn:**
- XXE is not just SSRF: it can exfiltrate local server files
- Custom PRNGs with small seeds are vulnerable to state recovery
- Z3 SMT solver for solving equations over PRNG bits
- "Rolling code" provides no security if the PRNG is weak and previous outputs are observable

---

## Summary

### Flag 0 — XXE via /set-config

1. Recon at `/unlock`, `/admin`; HTML comment points to `/get-config`
2. `GET /get-config` → returns configuration XML
3. Send XML with XXE to `/set-config?data=`:
   ```xml
   <?xml version="1.0"?>
   <!DOCTYPE foo [<!ENTITY xxe SYSTEM "main.py">]>
   <Config><name>&xxe;</name></Config>
   ```
4. Admin panel displays content of `main.py` with the embedded flag

### Flag 1 — PRNG rolling code via seed recovery

1. XXE to exfiltrate `rng.py` (code generator logic)
2. Send wrong codes to `/unlock` → response includes expected codes
3. Recover the seed using Z3 (SMT solver) on the bitwise operations
4. Re-execute PRNG locally to predict the next valid code
5. `POST /unlock` with correct code → flag

**Technical references:**
- [gus3rmr — Medium (Z3 approach)](https://medium.com/@gus3rmr/hacker101ctf-model-e1337-rolling-code-lock-2-2-flags-f5a279dcd433)
- [7Rocky (GF(2) approach)](https://7rocky.github.io/en/ctf/hacker101ctf/model-e1337---rolling-code-lock/)
- See `PATH.md` in this folder for complete list of references

---

See also `../model-e1337/WRITEUP.md` for the complete implementation with scripts.
