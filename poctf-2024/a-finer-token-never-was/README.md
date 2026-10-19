# A Finer Token Never Was

**Category:** Exploitation
**Challenge:** A Finer Token Never Was
**CTF:** Pointer Overflow CTF 2024
**Points:** Exploit 100
**Result:** Solved

**Flag:**

~~~text
poctf{uwsp_411_4n1m4l5_4r3_3qu41}
~~~

---

## 1. Challenge Overview

A straightforward buffer overflow challenge with source code provided. The binary contains a `pop_shell()` function that calls `system("/bin/sh")`, and the goal is to redirect execution to it by overwriting the return address through a `gets()` vulnerability.

**Target:** `35.184.182.18:32002`
**Files:** `Exploit100-1` (ELF binary), `Exploit100-1.c` (source code)

---

## 2. Source Code Analysis

The source code reveals a classic buffer overflow scenario:

- A 64-byte local buffer read with `gets()` (no bounds checking)
- A `pop_shell()` function at a fixed address that spawns a shell via `system("/bin/sh")`

The attack surface is clear: overflow the buffer, overwrite the saved return address on the stack, and redirect execution to `pop_shell()`.

---

## 3. Finding the Target Address

Loaded the binary in GDB to locate the `pop_shell()` function address:

~~~bash
gdb Exploit100-1
(gdb) disassemble pop_shell
~~~

Result: `pop_shell()` is at `0x0000000000401152`.

---

## 4. Payload Construction

Calculated the offset to the return address:

- Buffer: 64 bytes
- Saved RBP: 8 bytes
- Total padding: 72 bytes

Payload structure: `[64 bytes padding][8 bytes RBP][address of pop_shell in little-endian]`

The exploit script ([payload.py](scripts/payload.py)) sends the crafted payload to the remote target and spawns an interactive shell.

---

## 5. Exploitation and Flag Retrieval

After gaining shell access through the overflow:

~~~bash
ls
cd home/Exploit100-1
cat Exploit100-1.txt
~~~

Output: `poctf{uwsp_411_4n1m4l5_4r3_3qu41}`

---

## Lessons Learned

| # | Lesson | Detail |
|---|--------|--------|
| 1 | `gets()` is inherently dangerous | No length validation, direct stack overflow vector |
| 2 | Fixed function addresses simplify exploitation | Without ASLR/PIE, ret2func is trivial |
| 3 | Source code accelerates analysis | Offset calculation from source is faster than fuzzing |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID | Context |
|---|---|---|---|
| Execution | Exploitation for Client Execution | T1203 | Buffer overflow via `gets()` to redirect execution |
| Privilege Escalation | Exploitation for Privilege Escalation | T1068 | Overwrite return address to gain shell |
| Defense Evasion | Abuse Elevation Control Mechanism | T1548 | Bypass normal control flow via stack smashing |

> **CWE-120:** Buffer Copy without Checking Size of Input. The `gets()` function writes beyond the allocated buffer, enabling stack-based overflow.
> **CWE-676:** Use of Potentially Dangerous Function. The `gets()` function is banned in secure coding standards due to inherent overflow risk.

---

## Remediation and Containment

### Technical Fixes

1. Replace `gets()` with `fgets()` or similar bounded input functions
2. Enable stack canaries (`-fstack-protector-strong`) to detect overflows at runtime
3. Compile with PIE (`-fPIE -pie`) and ASLR to randomize function addresses
4. Use NX bit (non-executable stack) and RELRO protections

### MITRE D3FEND Countermeasures

- **D3-PSEP (Process Segment Execution Prevention):** enforce W^X memory policy to prevent stack code execution
- **D3-SEA (Stack Frame Canary Validation):** detect stack corruption before return
- **D3-ASLR (Address Space Layout Randomization):** randomize memory layout to prevent hardcoded address exploitation

### NIST CSF 2.0

- **Protect (PR.DS):** enforce memory safety controls in compiled binaries
- **Detect (DE.CM):** monitor for anomalous process spawning from binary exploitation
- **Respond (RS.MI):** deploy crash reporting for segfault-triggered shell spawns

### NIST SP 800-53 Rev. 5

- **SI-16 (Memory Protection):** employ hardware and software mechanisms to prevent buffer overflow
- **CM-7 (Least Functionality):** remove unnecessary functions like `pop_shell()` from production code
- **SA-11 (Developer Testing and Evaluation):** perform static analysis to detect dangerous function usage

### C2M2

- **THREAT-3:** assess exploitation risk of memory-unsafe code in deployed applications
- **RISK-4:** classify buffer overflow as high-impact vulnerability requiring immediate remediation

---

Thanks guys!! (❍ᴥ❍ʋ)

---

Classic buffer overflow, classic ret2func. When the source code hands you `gets()` and a shell function, you just measure the padding and fire. Simplicity at its finest.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

> **Reference:** Adapted from [shivang1209-dot/CTF-Writeups](https://github.com/shivang1209-dot/CTF-Writeups). Original scripts credited to the author.
