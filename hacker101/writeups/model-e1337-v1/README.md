# Model E1337 v1: Rolling Code Lock: Writeup (2/2)

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
- XXE (CWE-611): `/set-config` uses `xml.sax` without disabling external entities; exfiltrates `main.py` and `rng.py`
- Weak PRNG / Seed Recovery (CWE-338): 32-bit seed recoverable via Z3 SMT solver or linear algebra over GF(2)
- Information Leakage via Error Message: `/unlock` with wrong code reveals the expected code

**What you learn:**
- XXE is not just SSRF: it can exfiltrate local server files
- Custom PRNGs with small seeds are vulnerable to state recovery
- Z3 SMT solver for solving equations over PRNG bits
- "Rolling code" provides no security if the PRNG is weak and previous outputs are observable

---

## Summary

### Flag 0: XXE via /set-config

1. Recon at `/unlock`, `/admin`; HTML comment points to `/get-config`
2. `GET /get-config` → returns configuration XML
3. Send XML with XXE to `/set-config?data=`:
   ```xml
   <?xml version="1.0"?>
   <!DOCTYPE foo [<!ENTITY xxe SYSTEM "main.py">]>
   <Config><name>&xxe;</name></Config>
   ```
4. Admin panel displays content of `main.py` with the embedded flag

### Flag 1: PRNG rolling code via seed recovery

1. XXE to exfiltrate `rng.py` (code generator logic)
2. Send wrong codes to `/unlock` → response includes expected codes
3. Recover the seed using Z3 (SMT solver) on the bitwise operations
4. Re-execute PRNG locally to predict the next valid code
5. `POST /unlock` with correct code → flag

**Technical references:**
- [gus3rmr: Medium (Z3 approach)](https://medium.com/@gus3rmr/hacker101ctf-model-e1337-rolling-code-lock-2-2-flags-f5a279dcd433)
- [7Rocky (GF(2) approach)](https://7rocky.github.io/en/ctf/hacker101ctf/model-e1337---rolling-code-lock/)
- See `PATH.md` in this folder for complete list of references

---

See also `../model-e1337/README.md` for the complete implementation with scripts.

## MITRE ATT&CK Mapping

| ID | Technique | Tactic | How it was used |
|----|-----------|--------|----------------|
| T1190 | Exploit Public-Facing Application | Initial Access | XXE on `/set-config` to exfiltrate application source code |
| T1005 | Data from Local System | Collection | Read `main.py` (flag in comment) and `rng.py` via XXE |
| T1588.005 | Obtain Capabilities: Exploits | Resource Development | Z3 SMT solver for PRNG seed recovery from observed outputs |

## Remediation and Containment

### Technical Fixes

1. **XXE:** Disable external entity resolution (`setFeature(feature_external_ges, False)`)
2. **PRNG:** Use `secrets` module or OS-level CSPRNG instead of 32-bit custom seed
3. **Error leakage:** Never reveal expected unlock codes in error responses
4. **Configuration endpoints:** Authenticate and rate-limit `/set-config` and `/get-config`

### OWASP Top 10 2021

| ID | Category | Relevance |
|----|----------|-----------|
| A05:2021 | Security Misconfiguration | XML parser allows external entities; error messages leak expected codes |
| A02:2021 | Cryptographic Failures | 32-bit seed space; custom non-cryptographic PRNG |

### MITRE D3FEND Countermeasures

| ID | Technique | Application |
|----|-----------|-------------|
| D3-CSPP | Content Security Policy Pinning | Restrict XML processing capabilities |
| D3-MFA | Multi-factor Authentication | Replace rolling code with HMAC-OTP (RFC 6238) |

### NIST CSF 2.0

| Function | Category | Application |
|----------|----------|-------------|
| PR (Protect) | PR.DS | Disable external entities in XML parsers |
| PR (Protect) | PR.AC | Authenticate configuration endpoints; rate-limit unlock |
| DE (Detect) | DE.CM | Monitor for XXE probes and brute-force on `/unlock` |

### NIST SP 800-53 Rev. 5

| Control | Title | Application |
|---------|-------|-------------|
| SC-13 | Cryptographic Protection | Use CSPRNG with adequate seed size (128+ bits) |
| SI-10 | Information Input Validation | Disable DTD and external entity processing in XML |
| SI-11 | Error Handling | Return generic errors; do not leak internal state |

### C2M2

| Domain | Practice | MIL | Application |
|--------|----------|-----|-------------|
| ACCESS | Access Control Management | MIL-2 | Restrict configuration endpoints; enforce authentication |
| ASSET | Asset, Change, and Configuration Management | MIL-2 | Enforce secure XML parser defaults across all components |

---

## Final Thoughts

Thanks guys!! (❍ᴥ❍ʋ)

---

Model E1337 v1 demonstrates the power of XXE beyond SSRF: using it as a source code reader gives you everything needed to reverse-engineer the application logic. Once you have the PRNG algorithm and a 32-bit keyspace, it is a math problem, not a security problem.

Connect and share your approach to crypto challenges:

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
