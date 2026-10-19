# Absence Makes Hearts Go Yonder

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2023 |
| **Challenge** | Absence Makes Hearts Go Yonder |
| **Category** | Steganography |
| **Difficulty** | Easy |
| **Points** | 100 |
| **Status** | Solved |

---

## 1. Challenge Overview

The challenge provides a GIF image file. The flag is hidden by appending it after the GIF file's termination marker, a straightforward steganography technique that exploits how image viewers ignore trailing data.

---

## 2. Analyzing the File

GIF files have a well-defined structure ending with a trailer byte (`0x3B`). Any data appended after this marker is ignored by image viewers but remains readable in the raw file.

Checking the file with `strings`:

~~~bash
strings challenge.gif | grep poctf
~~~

**Output:**

~~~text
poctf{uwsp_4853nc3_m4k35_h34275_90_y0nd3r}
~~~

Alternatively, using `xxd` to examine the end of the file:

~~~bash
xxd challenge.gif | tail -20
~~~

The hex dump shows the GIF trailer (`3b`) followed by the ASCII flag text appended directly after.

---

## 3. Attack Path Summary

~~~text
challenge.gif
    |
strings / hexdump to inspect trailing data
    |
Flag appended after GIF trailer (0x3B)
    |
FLAG: poctf{uwsp_4853nc3_m4k35_h34275_90_y0nd3r}
~~~

---

## 4. Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|--------------|
| 1 | File format trailers are not enforced boundaries | Data appended after a format's end marker persists silently in the file | Always check beyond format boundaries for hidden data |
| 2 | GIF steganography is a classic hiding technique | Attackers use trailing data in images to exfiltrate secrets or embed C2 payloads | Stego detection tools and file carving utilities catch appended data |
| 3 | `strings` is a powerful first-pass triage tool | Running strings on binary files quickly surfaces embedded text without specialized tools | Start simple: strings, file, xxd, then escalate to format-specific analyzers |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Defense Evasion | TA0005 | Obfuscated Files or Information: Steganography | T1027.003 |
| Exfiltration | TA0010 | Exfiltration Over C2 Channel | T1041 |
| Command and Control | TA0011 | Data Obfuscation: Steganography | T1001.002 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediation and Containment

### Technical Fixes

1. Implement file integrity checks that validate media files conform to their format specification without trailing data
2. Use stego detection tools (StegDetect, Aperi'Solve) on files crossing network boundaries
3. Re-encode uploaded images server-side to strip appended data

### MITRE D3FEND Countermeasures

- **D3-FCR File Content Rules** to detect anomalous file structures with data beyond format boundaries (counters T1027.003)
- **D3-NTA Network Traffic Analysis** to flag image files with unusual sizes relative to their dimensions (counters T1001.002)

### NIST CSF 2.0

- **Detect (DE.CM-1):** Monitor network traffic for files with anomalous structure or size
- **Protect (PR.DS-5):** Validate file integrity at upload and transit points

### NIST SP 800-53 Rev. 5

- **SI-3: Malicious Code Protection** (detect steganographic payloads in media files)
- **SC-7: Boundary Protection** (inspect files at network boundaries for hidden content)

### CWE

- **CWE-353: Missing Support for Integrity Check** (no validation of file structure beyond format headers)

---

## References

- Solve approach based on research from [Jihun Hwang's POCTF 2023 writeup](https://jihunhwang.github.io/UWSP_CTF_2023_writeup/) and [Joooook's blog](https://joooook.github.io/2024/02/05/UWSP%20Pointer%20Overflow%20CTF/)

---

Thanks guys!! (❍ᴥ❍ʋ)

---

What the heart misses, the hex editor finds. Sometimes the simplest hiding spots are right past the end of the file, waiting for someone curious enough to look beyond what the viewer shows.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
