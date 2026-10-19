# Heroes and Zeros

**Category:** Exploitation
**Challenge:** Heroes and Zeros
**CTF:** Pointer Overflow CTF 2024
**Points:** Exploit 100
**Result:** Solved

**Flag:**

~~~text
poctf{uwsp_w3ll_d0n3_15_b3773r_7h4n_w3ll_541d}
~~~

---

## 1. Challenge Overview

A game binary where clicking a moving diamond earns power points. The challenge requires accumulating 10,000 points to unlock the flag. Rather than playing manually, the binary can be analyzed to extract the flag directly.

**Target:** `35.184.182.18:32002`
**Files:** Windows and Linux versions of the game binary

---

## 2. Initial Analysis

Running the binary presents a game interface with a moving diamond. Each click awards one point. Reaching 10,000 points manually is impractical and clearly not the intended approach for a CTF.

---

## 3. Static Analysis with Strings

Before diving into Ghidra, ran `strings` to check for embedded plaintext:

~~~bash
strings ./Exploit100-2 | grep -a "poctf{.*}"
~~~

The flag was stored as a plaintext string directly in the binary, with no encryption or obfuscation.

---

## 4. Flag Extraction

The `strings` command immediately revealed:

~~~text
poctf{uwsp_w3ll_d0n3_15_b3773r_7h4n_w3ll_541d}
~~~

No reverse engineering or exploitation was required beyond basic static analysis.

---

## Lessons Learned

| # | Lesson | Detail |
|---|--------|--------|
| 1 | Always try `strings` first | Plaintext secrets in binaries are surprisingly common |
| 2 | Hardcoded flags are a security anti-pattern | Sensitive data should never be embedded in client-side binaries |
| 3 | Client-side validation is easily bypassed | Game score validation occurs locally, not server-side |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID | Context |
|---|---|---|---|
| Collection | Data from Local System | T1005 | Flag extracted directly from the binary file |
| Defense Evasion | Obfuscated Files or Information | T1027 | Flag stored in plaintext, no obfuscation applied |
| Credential Access | Unsecured Credentials: Credentials in Files | T1552.001 | Sensitive token embedded in distributable binary |

> **CWE-798:** Use of Hard-coded Credentials. The flag is embedded as a plaintext string in the binary, recoverable with basic tooling.
> **CWE-312:** Cleartext Storage of Sensitive Information. No encryption protects the flag within the binary.

---

## Remediation and Containment

### Technical Fixes

1. Store flags server-side and validate completion state on the server
2. If secrets must be in the binary, encrypt them with a key derived from valid game state
3. Strip debugging symbols and apply binary obfuscation to raise the analysis bar
4. Implement server-side score validation rather than client-side checks

### MITRE D3FEND Countermeasures

- **D3-FE (File Encryption):** encrypt sensitive strings within binaries at rest
- **D3-DA (Dynamic Analysis):** detect automated extraction tools targeting binary strings
- **D3-FCOA (File Content Analysis):** scan builds for embedded plaintext credentials before distribution

### NIST CSF 2.0

- **Protect (PR.DS):** protect sensitive data at rest using encryption, even in client binaries
- **Detect (DE.CM):** detect unauthorized binary analysis through anti-tamper mechanisms
- **Respond (RS.MI):** rotate flags if binary analysis is detected or suspected

### NIST SP 800-53 Rev. 5

- **SC-28 (Protection of Information at Rest):** encrypt all sensitive data stored in distributed files
- **IA-5 (Authenticator Management):** do not embed static credentials in client software
- **SA-15 (Development Process, Standards, and Tools):** enforce pre-release scanning for hardcoded secrets

### C2M2

- **ASSET-3:** classify game binaries as potential secret vectors requiring pre-distribution review
- **ACCESS-2:** implement server-side gating for flag delivery tied to validated game state

---

Thanks guys!! (❍ᴥ❍ʋ)

---

Sometimes the answer is hiding in plain sight. A quick `strings | grep` saves hours of reverse engineering. Always start simple before reaching for the decompiler.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

> **Reference:** Adapted from [shivang1209-dot/CTF-Writeups](https://github.com/shivang1209-dot/CTF-Writeups). Original scripts credited to the author.
