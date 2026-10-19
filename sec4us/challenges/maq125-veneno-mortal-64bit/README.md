# Maq125: Veneno Mortal em 64 bits

Writeup for the **Veneno Mortal em 64 bits** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Medium
> **Difficulty:** Medium

---

## Overview

A 64-bit buffer overflow challenge in the Poison Ivy BOF series. Exploitation requires adapting the approach to x64 calling conventions while using Metasploit TARGET 2 configuration and an x86 `shell_reverse_tcp` payload for the final shell.

## Reconnaissance

1. Scan the target to identify the vulnerable service and its port.
2. Probe the service with crafted input to understand its behavior and response patterns.
3. Determine the target architecture (x64) and operating system version.
4. Retrieve or analyze the vulnerable binary for offline reverse engineering if possible.

## Exploitation

1. Fuzz the service to trigger a crash and identify the buffer length.
2. Use a cyclic pattern to calculate the exact offset to the return pointer.
3. Note the x64 differences: 8-byte addresses, register-based calling convention, canonical address requirements.
4. Identify bad characters by iterating through the byte range.
5. In Metasploit, configure TARGET 2 for the appropriate exploit module.
6. Generate an x86 `shell_reverse_tcp` payload (compatible with the service context).
7. Build the exploit: buffer padding + return address overwrite + NOP sled + shellcode.
8. Execute the exploit to land a reverse shell on the attacker's listener.

## Privilege Escalation

1. Assess the privilege level of the compromised service account.
2. Enumerate the system for local escalation vectors.
3. If needed, exploit a local vulnerability to escalate to root or SYSTEM.
4. Retrieve the flag from the privileged directory.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Exploitation of Remote Services | T1210 |
| Command and Scripting Interpreter | T1059 |

### CWE

- **CWE-120:** Buffer Copy without Checking Size of Input
- **CWE-121:** Stack-based Buffer Overflow
- **CWE-787:** Out-of-bounds Write

---

> "Doubling the word size doubles the complexity, but the fundamental sin remains the same: trusting user input to fit where it does not belong. Sixty-four bits of address space cannot protect a careless `strcpy`."

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
