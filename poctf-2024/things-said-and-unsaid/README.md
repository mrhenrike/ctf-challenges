# Things Said and Unsaid

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2024 |
| **Challenge** | Things Said and Unsaid |
| **Category** | Steganography |
| **Difficulty** | Easy |
| **Points** | 100 |
| **Status** | Solved |

---

## Challenge Overview

A JPEG image has a ZIP archive appended after its footer. The ZIP is password-protected and contains the flag. The password is hidden in the JPEG file itself, after the ZIP footer.

**File provided:** `Stego100-3.jpeg`

---

## Objective

Extract the embedded ZIP, find the password hidden in the file, and recover the flag.

---

## Methodology

### Step 1: Analyze with binwalk

```bash
binwalk Stego100-3.jpeg
```

```
0             0x0             JPEG image data, JFIF standard 1.01
562069        0x89395         Zip archive data, encrypted compressed size: 57
562298        0x8947A         End of Zip archive, footer length: 22
```

A ZIP archive is embedded at offset `0x89395`.

### Step 2: Extract the ZIP

```bash
binwalk -e Stego100-3.jpeg
```

This extracts `89395.zip` containing `Stego100-3_flag.txt`, but it is password-protected.

### Step 3: Find the Password

Examining the hex dump after the ZIP footer reveals a plaintext string: `probably_improbable`.

Confirming with exiftool:

```bash
exiftool 89395.zip
```

The `Zip File Name` field shows `probably_improbable`, which doubles as the password.

### Step 4: Extract the Flag

```bash
7z x 89395.zip -pprobably_improbable
```

The extracted `Stego100-3_flag.txt` contains the flag.

---

## Flag

```
poctf{uwsp_w3_4r3_such_57uff}
```

---

## Lessons Learned

| # | Insight |
|---|---------|
| 1 | JPEG files can have arbitrary data appended after the EOI marker |
| 2 | binwalk is essential for detecting embedded files within images |
| 3 | Passwords may be hidden in the same file as the encrypted data |
| 4 | Always examine data after the expected file footer |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | Description |
|--------|-----------|-------------|
| Defense Evasion | T1027.003 - Obfuscated Files: Steganography | Hiding a ZIP archive inside a JPEG |
| Defense Evasion | T1036 - Masquerading | File appears as a normal image while containing hidden data |

---

## Remediation

### Technical Fixes

- Implement file format validation that rejects files with unexpected data after the format footer.
- Use content-aware proxies and DLP solutions that inspect files for appended data.
- Validate file size consistency between declared format and actual file size.

### MITRE D3FEND

| ID | Technique |
|----|-----------|
| D3-FCR | File Content Rules: detect data appended after file markers |
| D3-SFA | Static File Analysis |

### NIST CSF 2.0

| Function | Category | Action |
|----------|----------|--------|
| Detect | DE.CM | Inspect uploaded files for appended or embedded data |
| Protect | PR.DS | Validate file integrity at upload and transit points |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---------|-------------|
| SI-3 | Malicious Code Protection |
| SC-4 | Information in Shared System Resources |

### C2M2

| Practice | Description |
|----------|-------------|
| DETECT | Deploy file analysis tools to identify steganographic payloads |

### CWE

| ID | Description |
|----|-------------|
| CWE-434 | Unrestricted Upload of File with Dangerous Type |

---

## References

- [shivang1209-dot POCTF 2024 Writeups](https://github.com/shivang1209-dot/shivang1209-dot) (original reference)
- [binwalk](https://github.com/ReFirmLabs/binwalk)
- [Pointer Overflow CTF](https://pointeroverflowctf.com/)

---

Thanks guys!! (❍ᴥ❍ʋ)

ZIP escondido dentro de JPEG com a senha logo ali do lado: esteganografia classica que nunca sai de moda. Sempre olhem alem do footer!

[![Instagram](https://img.shields.io/badge/Instagram-%23E4405F.svg?style=for-the-badge&logo=Instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/linkedin-%230077B5.svg?style=for-the-badge&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/X-%23000000.svg?style=for-the-badge&logo=X&logoColor=white)](https://x.com/mrhenrike)
