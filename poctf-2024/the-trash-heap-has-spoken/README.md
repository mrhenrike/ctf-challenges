# The Trash Heap Has Spoken

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2024 |
| **Category** | Exploitation |
| **Difficulty** | Hard |
| **Points** | 300 |
| **Flag** | `poctf{uwsp_17_w45_7h3_b357_0f_71m35}` |
| **Status** | Solved |

---

## 1. Challenge Overview

A heap exploitation challenge themed around an Oregon Trail reboot prototype. The binary runs on Debian with GLIBC 2.31 and contains a heap overflow vulnerability exploitable through standard heap manipulation techniques.

**Target:** `34.123.210.162:32017`
**Environment:** Debian GLIBC 2.31-13+deb11u11
**Files:** `Exploit300-2` (ELF binary)

---

## 2. Vulnerability Analysis

The binary implements a game-like interface with memory allocation/deallocation operations. The heap layout is vulnerable to a standard heap overflow, allowing manipulation of heap metadata and adjacent chunk contents.

Key observations:

- GLIBC 2.31 uses tcache bins for small allocations, which have weaker integrity checks than the main arena
- The binary allocates and frees chunks in a pattern that allows controlled heap grooming
- Overflow from one chunk can corrupt the metadata or contents of adjacent chunks

---

## 3. Exploitation Strategy

The exploit ([script.py](scripts/script.py)) performs a standard heap overflow attack:

1. Allocate strategic heap chunks to set up the desired memory layout
2. Trigger the overflow to corrupt adjacent chunk metadata
3. Manipulate the free list to achieve an arbitrary write primitive
4. Overwrite a function pointer or GOT entry to redirect execution
5. Spawn a shell and retrieve the flag

---

## 4. Flag Retrieval

After successful exploitation, shell access was obtained and the flag was read from the filesystem.

---

## Lessons Learned

| # | Lesson | Detail |
|---|--------|--------|
| 1 | Heap exploitation requires understanding allocator internals | GLIBC tcache behavior is critical knowledge |
| 2 | GLIBC version determines available techniques | 2.31 tcache has limited integrity checks vs. newer versions |
| 3 | Heap grooming controls exploitation reliability | Strategic allocation/free patterns create exploitable layouts |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID | Context |
|---|---|---|---|
| Execution | Exploitation for Client Execution | T1203 | Heap overflow to achieve arbitrary code execution |
| Privilege Escalation | Exploitation for Privilege Escalation | T1068 | Shell access via heap metadata corruption |
| Defense Evasion | Process Injection | T1055 | Corrupted heap metadata redirects control flow |

> **CWE-122:** Heap-based Buffer Overflow. Writing beyond allocated heap chunk boundaries corrupts adjacent metadata.
> **CWE-416:** Use After Free. Heap exploitation chains often leverage freed chunk manipulation.

---

## Remediation and Containment

### Technical Fixes

1. Validate all heap allocation sizes and prevent writes beyond chunk boundaries
2. Use hardened allocators (jemalloc, hardened_malloc) that resist heap exploitation
3. Upgrade to modern GLIBC versions with stronger tcache integrity checks
4. Compile with AddressSanitizer during testing to catch heap corruption early

### MITRE D3FEND Countermeasures

- **D3-HBPI (Heap-Based Process Isolation):** use heap canaries and guard pages to detect corruption
- **D3-PSEP (Process Segment Execution Prevention):** prevent execution of data in heap regions
- **D3-DA (Dynamic Analysis):** use fuzzing and sanitizers to discover heap bugs before deployment

### NIST CSF 2.0

- **Protect (PR.DS):** enforce memory safety through allocator hardening and bounds checking
- **Detect (DE.CM):** monitor for heap corruption signals (crashes, anomalous allocations)
- **Respond (RS.MI):** terminate processes exhibiting heap corruption behavior

### NIST SP 800-53 Rev. 5

- **SI-16 (Memory Protection):** deploy exploit mitigations including heap hardening
- **SA-11 (Developer Testing and Evaluation):** mandatory fuzzing with sanitizers in CI pipeline
- **SI-7 (Software, Firmware, and Information Integrity):** validate binary integrity and heap state

### C2M2

- **THREAT-3:** include heap exploitation scenarios in penetration testing scope
- **RISK-4:** classify heap overflow as critical due to direct code execution impact

---

Thanks guys!! (❍ᴥ❍ʋ)

---

The Trash Heap has spoken, and it speaks volumes about the importance of heap hardening. When allocator metadata is your attack surface, understanding the allocator is your weapon.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

> **Reference:** Adapted from [shivang1209-dot/CTF-Writeups](https://github.com/shivang1209-dot/CTF-Writeups). Original scripts credited to the author.
