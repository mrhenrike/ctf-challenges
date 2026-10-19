# Hooper Hollar

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2024 |
| **Category** | Digital Forensics |
| **Difficulty** | Medium |
| **Points** | 200 |
| **Flag** | `poctf{uwsp_l3553r_b31ng5}` |
| **Status** | Solved |

---

## 1. Challenge Overview

A memory dump file requiring forensic analysis. The challenge emphasizes stepping back to see the big picture before diving into detailed analysis.

**Files:** `DF200-1.mem` (memory dump)

---

## 2. Initial Approach

Started with automated extraction tools:

~~~bash
foremost -i DF200-1.mem
exiftool DF200-1.mem
~~~

Extracted several JPEG files but none contained the flag or useful leads.

---

## 3. String Search

Took the simpler approach of extracting and filtering strings:

~~~bash
strings DF200-1.mem | grep "uwsp"
~~~

The flag appeared directly in the output:

~~~text
poctf{uwsp_l3553r_b31ng5}
~~~

---

## 4. Reflection

The flag was hiding in plaintext within the memory dump. This challenge reinforces the principle of starting with the simplest analysis methods before deploying complex tools. Memory dumps often contain plaintext remnants of processed data.

---

## Lessons Learned

| # | Lesson | Detail |
|---|--------|--------|
| 1 | Start with `strings` for memory dumps | Plaintext artifacts are often preserved in RAM |
| 2 | Simple tools before complex analysis | grep + strings beats Volatility when the data is in plaintext |
| 3 | Memory is a rich forensic source | Running processes leave string artifacts in heap and stack |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID | Context |
|---|---|---|---|
| Credential Access | OS Credential Dumping | T1003 | Sensitive data recovered from a memory dump |
| Collection | Data from Local System | T1005 | Flag extracted from volatile memory contents |
| Defense Evasion | Obfuscated Files or Information | T1027 | Data not obfuscated, preserved as plaintext in RAM |

> **CWE-316:** Cleartext Storage of Sensitive Information in Memory. The flag persists as a readable string in process memory.

---

## Remediation and Containment

### Technical Fixes

1. Zeroize sensitive data in memory immediately after use
2. Use secure memory allocation (mlock + madvise MADV_DONTDUMP) for secrets
3. Implement memory encryption (AMD SME/SEV, Intel TME) for sensitive workloads
4. Restrict physical access and disable memory dump capabilities in production

### MITRE D3FEND Countermeasures

- **D3-MEM (Memory Encryption):** encrypt memory regions containing sensitive data
- **D3-PSEP (Process Segment Execution Prevention):** protect memory pages from unauthorized reads
- **D3-PCE (Process Code Encryption):** encrypt process memory to prevent dump analysis

### NIST CSF 2.0

- **Protect (PR.DS):** protect data in use through memory encryption and secure allocation
- **Detect (DE.CM):** detect unauthorized memory dump creation
- **Respond (RS.MI):** invalidate secrets potentially exposed through memory dumps

### NIST SP 800-53 Rev. 5

- **SC-28 (Protection of Information at Rest):** extend protection to data in memory
- **SC-39 (Process Isolation):** prevent cross-process memory access
- **MP-6 (Media Sanitization):** securely wipe memory dumps after forensic analysis

### NIST SP 800-86

- **Volatile Data Collection:** acquire memory dumps using validated tools (LiME, WinPmem)
- **Memory Analysis:** apply string extraction and pattern matching as first-pass techniques

### C2M2

- **SITUATION-2:** include memory forensics in incident response toolkit
- **THREAT-2:** assess memory exposure risk for applications handling sensitive data

---

Thanks guys!! (❍ᴥ❍ʋ)

---

Lesser beings might overthink this one. Sometimes the best forensic technique is grep. Memory dumps are goldmines of plaintext secrets for anyone who knows where to look.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

> **Reference:** Adapted from [shivang1209-dot/CTF-Writeups](https://github.com/shivang1209-dot/CTF-Writeups). Original scripts credited to the author.
