# Beef-Witted Mushrumps

**Category:** Reverse Engineering
**Challenge:** Beef-Witted Mushrumps
**CTF:** Pointer Overflow CTF 2024
**Points:** Reverse 300
**Result:** Solved

**Flag:**

~~~text
poctf{uwsp_7h3_g4m3_15_4f007}
~~~

---

## 1. Challenge Overview

A binary implementing a custom virtual machine with bytecode instructions that decode an encoded flag stored in memory. The VM supports load, store, add, subtract, XOR, and print operations. The challenge requires understanding the VM's execution to reverse the encoding.

**Files:** `Reverse300-3` (ELF binary)

---

## 2. Virtual Machine Architecture

Decompiled pseudocode reveals a simple register-based VM:

| Opcode | Operation | Description |
|--------|-----------|-------------|
| 1 | LOAD | `acc = memory[operand]` |
| 2 | STORE | `memory[operand] = acc` |
| 3 | ADD | `acc = acc + memory[operand]` |
| 4 | SUB | `acc = acc - memory[operand]` |
| 5 | XOR | `acc = acc ^ memory[operand]` |
| 6 | PRINT | `putchar(acc)` |
| 0xFF | HALT | Stop execution |

The VM reads instruction pairs (opcode, operand) from a bytecode array and operates on a 256-byte memory region.

---

## 3. Memory Analysis with GDB

Set a breakpoint after `initialize_memory()` and examined the memory contents:

~~~text
0x404080 <memory>:      0x1760156e087c1f70      0x1f7827147c4b1464
0x404090 <memory+16>:   0x45712e1b2a75462b      0x0000006914231323
~~~

Converted from little-endian to the encoded flag bytes:

~~~text
701f7c086e156017 64144b7c1427781f 2b46752a1b2e7145 2313231469
~~~

---

## 4. Understanding the Encoding

Analysis of the VM bytecode reveals the decoding operation: each byte is XORed with the previous byte (shifted by one position). The first byte is XORed with `0x00` (null), which means it gets its original value but prints the second character first.

When run normally, the binary outputs `octf{` instead of `poctf` because the null-XOR skips the first character.

---

## 5. Reversing the XOR Chain

To decode: XOR the encoded flag with itself shifted by one byte, prepending `0x00`:

~~~text
Encoded: 701f7c086e15601764144b7c1427781f2b46752a1b2e71452313231469
Key:     00701f7c086e15601764144b7c1427781f2b46752a1b2e714523132314

Result:  poctf{uwsp_7h3_g4m3_15_4f007}
~~~

---

## Lessons Learned

| # | Lesson | Detail |
|---|--------|--------|
| 1 | Custom VMs are a common RE obfuscation technique | Understanding the ISA is key to solving |
| 2 | GDB memory examination reveals encoded data | Breakpoints after initialization expose loaded values |
| 3 | XOR chains unravel with shifted self-XOR | The null byte at position 0 is the anchor point |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID | Context |
|---|---|---|---|
| Defense Evasion | Obfuscated Files or Information: Software Packing | T1027.002 | Flag processed through custom VM bytecode |
| Defense Evasion | Deobfuscate/Decode Files or Information | T1140 | Reversed XOR chain encoding to recover plaintext |
| Defense Evasion | Virtualization/Sandbox Evasion | T1497 | Custom VM adds analysis complexity |

> **CWE-327:** Use of a Broken or Risky Cryptographic Algorithm. Chained XOR with no independent key is trivially reversible.
> **CWE-330:** Use of Insufficiently Random Values. The XOR key is derived from the data itself, providing no independent randomness.

---

## Remediation and Containment

### Technical Fixes

1. Use independent cryptographic keys, not self-referential XOR chains
2. If a VM-based approach is desired for obfuscation, combine with proper encryption
3. Implement anti-debugging techniques to prevent memory inspection at runtime
4. Use ASLR and PIE to complicate static address analysis

### MITRE D3FEND Countermeasures

- **D3-FE (File Encryption):** protect data with encryption using independent keys
- **D3-DA (Dynamic Analysis):** detect GDB/debugger attachment and alter behavior
- **D3-PSEP (Process Segment Execution Prevention):** prevent memory dumping of sensitive regions

### NIST CSF 2.0

- **Protect (PR.DS):** encrypt data with keys independent of the data itself
- **Detect (DE.CM):** monitor for debugging tools attached to protected processes
- **Respond (RS.MI):** zeroize sensitive memory regions on tamper detection

### NIST SP 800-53 Rev. 5

- **SC-13 (Cryptographic Protection):** use algorithms with independent key material
- **SC-28 (Protection of Information at Rest):** protect encoded data with validated encryption
- **SI-7 (Software, Firmware, and Information Integrity):** detect binary analysis and tampering

### C2M2

- **THREAT-3:** include VM-based obfuscation reversal in advanced testing methodology
- **RISK-3:** assess custom VM protections for resistance to systematic analysis

---

Thanks guys!! (❍ᴥ❍ʋ)

---

The game is afoot. Custom bytecode VMs are one of the most interesting reverse engineering challenges because you have to learn an entirely new instruction set before you can even start attacking the data. The XOR chain trick is elegant but fragile.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

> **Reference:** Adapted from [shivang1209-dot/CTF-Writeups](https://github.com/shivang1209-dot/CTF-Writeups). Original scripts credited to the author.
