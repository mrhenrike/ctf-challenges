# To Finish and Flounder

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

A binary is provided that asks for a password to grant shell access. Decompiling the binary reveals the password hardcoded in the source, making static analysis the path to the flag.

---

## Objective

Reverse engineer the binary to find the hardcoded password, authenticate, and retrieve the flag from the remote server.

---

## Methodology

### Step 1: Binary Analysis

Running basic reconnaissance on the binary:

```bash
file challenge
checksec --file=challenge
strings challenge | grep -i pass
```

### Step 2: Decompilation

Opening the binary in Ghidra or IDA reveals the `main` function with a string comparison:

```c
if (strcmp(user_input, "hardcoded_password") == 0) {
    system("/bin/sh");
}
```

The password is stored as a plaintext string in the binary.

### Step 3: Authenticate and Capture

Connecting to the remote service and entering the discovered password grants a shell:

```bash
nc challenge.pointeroverflowctf.com PORT
Password: [hardcoded_password]
$ cat flag.txt
poctf{uwsp_...}
```

---

## Lessons Learned

| # | Insight |
|---|---------|
| 1 | Hardcoded credentials in binaries are trivially extractable with decompilation |
| 2 | Even compiled code offers no protection for embedded secrets |
| 3 | `strings` alone can sometimes reveal passwords without full decompilation |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | Description |
|--------|-----------|-------------|
| Credential Access | T1552.001 - Credentials In Files | Password stored in the binary itself |
| Execution | T1059 - Command and Scripting Interpreter | Shell access obtained via hardcoded credential |

---

## Remediation

### Technical Fixes

- Never store passwords or secrets in compiled binaries; use secure vaults or environment variables.
- Implement proper authentication mechanisms instead of simple string comparisons.
- Strip debug symbols and apply obfuscation as a defense-in-depth measure.

### MITRE D3FEND

| ID | Technique |
|----|-----------|
| D3-CR | Credential Rotation: regularly rotate credentials and avoid static secrets |

### NIST CSF 2.0

| Function | Category | Action |
|----------|----------|--------|
| Protect | PR.AA | Implement strong authentication; never hardcode credentials |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---------|-------------|
| IA-5 | Authenticator Management: protect authenticator content from unauthorized access |
| SC-28 | Protection of Information at Rest: encrypt stored credentials |

### C2M2

| Practice | Description |
|----------|-------------|
| ACCESS | Use secrets management solutions to handle credentials securely |

### CWE

| ID | Description |
|----|-------------|
| CWE-798 | Use of Hard-coded Credentials |
| CWE-259 | Use of Hard-coded Password |

---

## References

- [yocchin POCTF 2024 Writeup](https://yocchin.hatenablog.com/entry/2025/01/23/140330) (original reference)
- [Pointer Overflow CTF](https://pointeroverflowctf.com/)

---

Thanks guys!! (❍ᴥ❍ʋ)

Hardcoded passwords are a developer's shortcut and a hacker's delight. Never trust compiled code to keep secrets!

[![Instagram](https://img.shields.io/badge/Instagram-%23E4405F.svg?style=for-the-badge&logo=Instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/linkedin-%230077B5.svg?style=for-the-badge&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/X-%23000000.svg?style=for-the-badge&logo=X&logoColor=white)](https://x.com/mrhenrike)
