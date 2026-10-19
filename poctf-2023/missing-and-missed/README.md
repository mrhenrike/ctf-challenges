# Missing and Missed

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2023 |
| **Challenge** | Missing and Missed |
| **Category** | Cryptography |
| **Difficulty** | Easy |
| **Points** | 100 |
| **Status** | Solved |

---

## 1. Challenge Overview

The challenge provides a block of seemingly random characters that form a Brainfuck program. The task is to identify the esoteric programming language and execute the code to obtain the flag.

**Provided data:** a text file containing Brainfuck source code made up of `+`, `-`, `>`, `<`, `.`, `,`, `[`, `]` characters.

---

## 2. Identifying the Language

The character set is immediately recognizable as Brainfuck, one of the most well-known esoteric programming languages. Brainfuck operates on a tape of memory cells, using only eight commands to manipulate a pointer and output ASCII values.

Key identifiers:
- Only uses `+-><.,[]` characters
- Repeated sequences of `+` and `-` suggest ASCII value construction
- `.` characters indicate output operations

---

## 3. Executing the Program

Running the code through any Brainfuck interpreter (dCode, online BF interpreters, or a local implementation) produces the flag directly:

~~~text
poctf{uwsp_m155_m3_w17h_7h053_cr4zy_ch4r5}
~~~

Using dCode's Brainfuck decoder:

1. Navigate to dCode Brainfuck Interpreter
2. Paste the program source
3. Click "Execute"
4. The output is the flag in plaintext

---

## 4. Attack Path Summary

~~~text
Challenge file (Brainfuck source)
    |
Identify language by character set
    |
Execute in BF interpreter
    |
FLAG: poctf{uwsp_m155_m3_w17h_7h053_cr4zy_ch4r5}
~~~

---

## 5. Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|--------------|
| 1 | Esoteric languages can obfuscate code | Threat actors have used esoteric or uncommon languages to evade signature-based detection | Recognizing obscure language patterns is a valuable analyst skill |
| 2 | Brainfuck is Turing-complete | Despite its minimal instruction set, BF can encode any computation, including malicious logic | Simplicity of syntax does not mean simplicity of capability |
| 3 | Pattern recognition speeds identification | The restricted character set `+-><.,[]` is a dead giveaway for Brainfuck | Build a mental catalog of encoding and language fingerprints for rapid triage |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Defense Evasion | TA0005 | Obfuscated Files or Information | T1027 |
| Defense Evasion | TA0005 | Obfuscated Files or Information: Software Packing | T1027.002 |
| Execution | TA0002 | Command and Scripting Interpreter | T1059 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediation and Containment

### Technical Fixes

1. Implement content inspection that can detect and flag esoteric programming languages in uploaded files
2. Sandbox execution environments for unknown code to prevent arbitrary code execution
3. Use entropy and character frequency analysis to identify obfuscated scripts

### MITRE D3FEND Countermeasures

- **D3-FCR File Content Rules** for detecting esoteric language patterns in uploaded files (counters T1027)
- **D3-EFA Emulated File Analysis** to safely execute suspicious scripts in isolated environments (counters T1059)

### NIST CSF 2.0

- **Detect (DE.CM-1):** Monitor for unusual file patterns that may indicate obfuscated code
- **Protect (PR.DS-5):** Implement controls to prevent execution of unrecognized script types

### NIST SP 800-53 Rev. 5

- **SI-3: Malicious Code Protection** (detect obfuscated scripts and esoteric language payloads)
- **CM-7: Least Functionality** (restrict execution of unnecessary scripting interpreters)

### CWE

- **CWE-116: Improper Encoding or Escaping of Output** (using esoteric encoding to hide intent)

---

## References

- Brainfuck language reference: https://esolangs.org/wiki/Brainfuck
- Solve approach based on research from [Jihun Hwang's POCTF 2023 writeup](https://jihunhwang.github.io/UWSP_CTF_2023_writeup/)

---

Thanks guys!! (❍ᴥ❍ʋ)

---

Brainfuck might look like keyboard noise, but it hides a Turing-complete language under eight simple characters. If you thought esoteric languages were just a curiosity, this challenge proves they belong in your analyst toolkit.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
