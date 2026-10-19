# Maq124: Veneno Mortal em 32 bits

Writeup for the **Veneno Mortal em 32 bits** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Medium
> **Difficulty:** Medium

---

## Overview

A binary exploitation challenge targeting a 32-bit application vulnerable to buffer overflow. The exercise emulates a Poison Ivy-style scenario where stack-based overflow leads to control of the instruction pointer and arbitrary code execution.

## Reconnaissance

1. Scan the target to identify the vulnerable service and its listening port.
2. Connect to the service and observe its behavior with normal input.
3. Identify the service binary or version if accessible for offline analysis.
4. Determine the architecture: x86 (32-bit) Linux or Windows target.

## Exploitation

1. Fuzz the target service to determine the crash point and buffer size.
2. Generate a cyclic pattern to calculate the exact EIP offset.
3. Identify bad characters that are filtered or truncated by the application.
4. Locate a suitable return address (JMP ESP or equivalent) in loaded modules.
5. Generate shellcode (reverse shell) avoiding identified bad characters.
6. Construct the final payload: padding + EIP overwrite + NOP sled + shellcode.
7. Send the exploit and receive a reverse shell on the attacker machine.

## Privilege Escalation

1. The buffer overflow grants code execution at the service's privilege level.
2. If the service runs as a privileged user, no further escalation is needed.
3. Otherwise, enumerate and exploit additional local vulnerabilities for root access.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Exploitation of Remote Services | T1210 |
| Command and Scripting Interpreter: Unix Shell | T1059.004 |

### CWE

- **CWE-120:** Buffer Copy without Checking Size of Input (classic buffer overflow)
- **CWE-121:** Stack-based Buffer Overflow
- **CWE-676:** Use of Potentially Dangerous Function

---

> "In 32 bits of address space, there is no room for mistakes; one unchecked buffer and the poison flows straight to EIP. The antidote? Bounds checking and stack canaries."

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
