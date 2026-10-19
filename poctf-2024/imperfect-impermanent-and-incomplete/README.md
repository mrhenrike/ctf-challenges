# Imperfect, Impermanent, and Incomplete

**Category:** Exploitation
**Challenge:** Imperfect, Impermanent, and Incomplete
**CTF:** Pointer Overflow CTF 2024
**Points:** Exploit 400
**Result:** Solved

**Flag:**

~~~text
poctf{uwsp_7h3_unb34r4bl3_l1gh7n355}
~~~

---

## 1. Challenge Overview

An advanced heap exploitation challenge featuring an off-by-one vulnerability in a "Secret-Keeper" application. The binary runs on Ubuntu with GLIBC 2.39 and requires manipulating tcache bins to overwrite a filename, achieving arbitrary file read.

**Target:** `35.184.182.18:32005`
**Environment:** Ubuntu GLIBC 2.39-0ubuntu8.3
**Files:** `Exploit400.c` (source code)

---

## 2. Vulnerability Analysis

The source code (`Exploit400.c`) reveals:

- An **off-by-one vulnerability** in the memory allocation logic
- The ability to allocate, write, free, and read named "secret" blocks
- A filename block stored adjacent to user-controlled data blocks
- The off-by-one allows overwriting metadata of the next chunk by exactly one byte

---

## 3. Exploitation Strategy

The attack leverages the off-by-one to manipulate tcache chunk metadata:

1. **Allocate two small blocks** (`a` and `b`) plus a filename block
2. **Free block `a`** and reclaim it, writing a payload that overflows by one byte into block `b`'s size metadata
3. **Modify `b`'s chunk size** to be larger than its actual allocation
4. **Free `b`** so it enters a tcache bin for a larger size class
5. **Reallocate `b`** at the larger size, causing it to overlap with the filename block
6. **Overwrite the filename** to point to the flag file:

~~~python
fake_filename = b"/home/challenge/flag.txt\0"
~~~

7. **Trigger the read operation**, which now reads the flag file instead of the original file

The full exploit is in [script.py](scripts/script.py).

---

## 4. Flag Retrieval

After the filename overwrite, the program's normal read functionality retrieves the contents of the flag file:

~~~text
poctf{uwsp_7h3_unb34r4bl3_l1gh7n355}
~~~

---

## Lessons Learned

| # | Lesson | Detail |
|---|--------|--------|
| 1 | Off-by-one errors in heap allocators are exploitable | A single byte can corrupt chunk metadata |
| 2 | Tcache poisoning enables overlapping chunks | Size manipulation creates controlled overlaps |
| 3 | Arbitrary file read through filename overwrite | Indirect exploitation via data, not code execution |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID | Context |
|---|---|---|---|
| Execution | Exploitation for Client Execution | T1203 | Off-by-one heap corruption to manipulate program state |
| Collection | Data from Local System | T1005 | Read arbitrary files by overwriting filename pointer |
| Defense Evasion | Abuse Elevation Control Mechanism | T1548 | Bypassed intended file access controls through heap corruption |

> **CWE-193:** Off-by-One Error. Writing one byte past the allocation corrupts adjacent chunk metadata.
> **CWE-122:** Heap-based Buffer Overflow. Exploited through tcache bin manipulation after metadata corruption.
> **CWE-22:** Improper Limitation of a Pathname to a Restricted Directory. Filename overwrite enables arbitrary file access.

---

## Remediation and Containment

### Technical Fixes

1. Fix the off-by-one in allocation size calculation (allocate `n+1` bytes or validate boundary)
2. Use a hardened allocator with chunk header integrity checks
3. Validate filenames against an allowlist of permitted paths
4. Implement sandbox/seccomp to restrict file access to designated directories

### MITRE D3FEND Countermeasures

- **D3-HBPI (Heap-Based Process Isolation):** guard pages between heap chunks to detect single-byte overflows
- **D3-ACL (Access Control List):** restrict file operations to a whitelist of permitted paths
- **D3-SBX (Sandbox):** confine the process to prevent arbitrary filesystem access

### NIST CSF 2.0

- **Protect (PR.DS):** enforce strict bounds checking on all memory operations
- **Protect (PR.AC):** restrict file access through kernel-level mandatory access controls
- **Detect (DE.CM):** monitor for anomalous file read patterns outside expected paths

### NIST SP 800-53 Rev. 5

- **SI-16 (Memory Protection):** deploy heap protection mechanisms against metadata corruption
- **AC-6 (Least Privilege):** restrict process file access to minimum required paths
- **SA-11 (Developer Testing and Evaluation):** fuzz with AddressSanitizer to catch off-by-one errors

### C2M2

- **THREAT-3:** include off-by-one heap exploitation in advanced penetration testing
- **RISK-4:** classify arbitrary file read as high-impact vulnerability

---

Thanks guys!! (❍ᴥ❍ʋ)

---

The unbearable lightness of a single byte. Off-by-one errors seem minor until they give you full filesystem access through a tcache size inflation trick. Heap metadata integrity is everything.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

> **Reference:** Adapted from [shivang1209-dot/CTF-Writeups](https://github.com/shivang1209-dot/CTF-Writeups). Original scripts credited to the author.
