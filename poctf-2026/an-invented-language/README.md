# An Invented Language

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

A custom virtual machine reverse engineering challenge. The challenge provides the VM's source code (`vm.c`) alongside a compiled program (`prog.bin`). Your objective: understand the instruction set architecture defined in `vm.c`, then either execute or statically analyze the bytecode in `prog.bin` to extract the flag. The title "An Invented Language" refers to the custom ISA itself: a language that exists only within this challenge.

---

## 1. Analyzing the VM Source

The first step is reading `vm.c` to build a mental model of the ISA:

```bash
# Get a high-level overview
wc -l vm.c
grep -n "case\|OP_\|opcode" vm.c | head -30
```

Key elements to identify:
- **Opcode encoding:** how bytes map to instructions (fixed-width vs variable)
- **Memory model:** stack-based, register-based, or hybrid
- **I/O operations:** which instructions produce output (the flag comes from here)
- **Control flow:** jumps, calls, conditionals

The VM defines a set of opcodes, each handled by a `case` in a dispatch loop. Understanding the operand format (immediate values, register indices, memory addresses) is critical for correct disassembly.

---

## 2. Disassembling prog.bin

Using the opcode table from `vm.c`, we can build a disassembler or manually trace the bytecode:

```bash
# Hex dump for manual analysis
xxd prog.bin | head -20
```

Each instruction consists of an opcode byte followed by zero or more operand bytes (format defined in `vm.c`). Walking through the binary from offset 0, decoding each instruction, produces a readable assembly listing.

---

## 3. Execution

The straightforward approach: compile the VM and run the program through it.

```bash
gcc -o vm vm.c -Wall -Wextra
./vm prog.bin
```

The program outputs the flag (or the nonce portion) to stdout. If the output includes a raw nonce, wrap it in the POCTF flag format with the challenge ID and team number.

---

## 4. Static Analysis Alternative

For cases where executing the binary is undesirable (potential anti-analysis traps), static analysis of the disassembled code reveals the output:

- Trace which values are pushed onto the stack or loaded into registers
- Follow the control flow to the I/O (print) instructions
- Reconstruct the output string from the intermediate values

This is slower but safer, and builds a deeper understanding of the VM's behavior.

**Flag:** `poctf{...}`

---

## Captured Flags

| Type | Value | Found At | Method |
|---|---|---|---|
| Flag | `poctf{...}` | prog.bin | Custom VM execution and bytecode analysis |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Custom VMs are a powerful obfuscation layer | Malware families like VMProtect, Themida, and Code Virtualizer convert x86 code into custom bytecode that runs on an embedded interpreter, making static analysis significantly harder | Analysts must be able to rapidly learn new ISAs; focus on the dispatch loop and opcode table |
| 2 | Source availability changes the analysis entirely | Having `vm.c` is analogous to having documentation or a leaked SDK; without it, the challenge would require opcode inference from execution traces | Always look for documentation, debug symbols, or leaked source before brute-forcing RE |
| 3 | Execution vs static analysis is a strategic choice | Running untrusted bytecode risks triggering anti-analysis, environment checks, or destructive payloads | Prefer static analysis for untrusted code; use sandboxed execution for validation |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|---|---|---|---|
| Execution | Execution | Command and Scripting Interpreter | T1059 |
| Evasion | Defense Evasion | Obfuscated Files or Information: Software Packing | T1027.002 |
| Evasion | Defense Evasion | Virtualization/Sandbox Evasion | T1497 |
| Analysis | Defense Evasion | Deobfuscate/Decode Files or Information | T1140 |

---

## Remediation and Containment

### Technical Fixes

1. Monitor for custom interpreters and VM-based packers in endpoint telemetry; they are strong indicators of obfuscated malware.
2. Deploy YARA rules targeting common VM dispatcher patterns (large switch-case structures, opcode fetch loops).
3. Use automated sandbox analysis (ANY.RUN, Cape Sandbox) to execute suspicious bytecode safely and capture behavioral indicators.
4. Implement application whitelisting to prevent execution of unknown interpreters.

### If You Find This in Your Environment

If a custom VM interpreter is found executing unknown bytecode, isolate the host immediately. Capture the interpreter binary and bytecode files for analysis. Check for persistence mechanisms, as VM-protected malware often unpacks additional stages after the initial bytecode runs.

### MITRE D3FEND

- **D3-SCA (Static Code Analysis):** Analyze VM source or disassembly to understand the instruction set
- **D3-BDI (Binary Data Inspection):** Inspect bytecode files for known opcode patterns
- **D3-DA (Dynamic Analysis):** Execute bytecode in instrumented VM instances to capture behavior

### NIST CSF 2.0

- **Identify (ID.AM):** Catalog all interpreters and runtime environments in the asset inventory
- **Protect (PR.AC):** Restrict execution of non-standard interpreters via application control
- **Detect (DE.CM):** Monitor for process creation patterns consistent with custom VM execution
- **Respond (RS.AN):** Analyze captured bytecode as part of incident forensics
- **Recover (RC.RP):** Remove custom interpreters and associated bytecode from compromised hosts

### NIST SP 800-53 Rev. 5

- **CM-7 (Least Functionality):** Restrict execution of non-essential interpreters and runtime environments
- **SI-3 (Malicious Code Protection):** Deploy detection capabilities for VM-protected malware

### CWE References

- **CWE-506:** Embedded Malicious Code (bytecode executing hidden logic)
- **CWE-829:** Inclusion of Functionality from Untrusted Control Sphere (executing untrusted bytecode)

### APT Group Reference

**APT32 (OceanLotus):** Known for using custom bytecode interpreters in their multi-stage loaders. Their Ratsnif backdoor family uses a custom VM to execute network reconnaissance commands, making static analysis of the payload significantly more difficult without first understanding the bespoke instruction set.

---

Thanks guys!! (❍ᴥ❍ʋ)

---

Custom VMs are one of those RE challenges that reward patience over brute force. If this walkthrough helped you crack the invented language, come chat with me about it!

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
