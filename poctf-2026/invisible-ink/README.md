# Invisible Ink (The Invisible Text)

**Category:** Steganography
**Challenge:** Invisible Ink / The Invisible Text
**CTF:** Pointer Overflow CTF 2026
**Points:** STEG 200, Wave 1
**Result:** Solved

**Flag:**

~~~text
poctf{...}
~~~

---

## 1. Reconnaissance

The challenge page provides a downloadable Python script (`invisible_text.py` / `diary_reader.py`) and a philosophical prompt about hidden communication. The "Whitmore Storage Engine" branding ties it thematically to the rest of the CTF's universe.

The script is 81 lines, about 4 KB. It runs as a legitimate Python program with visible output, but the real payload is invisible: trailing whitespace characters at the end of source lines.

---

## 2. Identifying the Steganographic Channel

Opening the file in a hex editor immediately reveals that most lines end with a mix of spaces (0x20) and tabs (0x09) after the visible code. For example, the shebang line:

~~~text
#!/usr/bin/env python3   \t \t    
~~~

The trailing characters are a mix of spaces and tabs, forming binary patterns.

The challenge name ("Invisible Ink") and the prompt ("listen for what it says silently") point directly at whitespace steganography, where trailing whitespace encodes a hidden message that most text editors strip or ignore.

---

## 3. Decoding Scheme

Each flag character is encoded as a 7-bit binary value using the last 7 trailing whitespace characters per carrier line:

- **Space** (0x20) = binary **0**
- **Tab** (0x09) = binary **1**
- MSB-first ordering
- One character per line with sufficient trailing whitespace

The decoding algorithm:

~~~python
for each line with >= 7 trailing whitespace chars:
    trailer = line[len(line.rstrip()):]
    last7 = trailer[-7:]
    bits = ''.join('0' if c == ' ' else '1' for c in last7)
    char = chr(int(bits, 2))
~~~

---

## 4. Exploitation

The decode was executed directly in the browser via JavaScript against the challenge's download endpoint:

~~~javascript
const resp = await fetch('/challenges/invisible-text/download', {credentials: 'include'});
const text = await resp.text();
const lines = text.split('\n');
let flag = '';
for (let i = 0; i < lines.length; i++) {
    const stripped = lines[i].replace(/[\s]+$/, '');
    const trailer = lines[i].slice(stripped.length);
    if (trailer.length < 7) continue;
    const last7 = trailer.slice(-7);
    let bits = '';
    for (const c of last7) bits += c === ' ' ? '0' : '1';
    const val = parseInt(bits, 2);
    if (val >= 32 && val < 127) flag += String.fromCharCode(val);
}
~~~

Both the even-indexed-only approach and the all-lines approach produced the same result, confirming that every line with sufficient trailing whitespace carried exactly one flag character.

Output:

~~~text
poctf{...}
~~~

---

## 5. Verification

- The decoded string starts with `poctf{...}`, matching the expected flag format.
- All 18 characters inside the braces are uppercase alphabetic, consistent with the CTF's token style.
- Both decoding approaches (every-other-line carrier selection vs. all-trailing-lines) converge on the same output.
- Submitted on the challenge page: **Correct.**

---

## 6. Tools Used

- Browser JavaScript (fetch + in-page decode)
- Python solver script (`solve_whitespace_stego.py`) for local verification

---

## 7. MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID | Relevance |
|---|---|---|---|
| Defense Evasion | Obfuscated Files or Information | T1027 | Flag hidden via whitespace encoding in a legitimate Python script |
| Defense Evasion | Hide Artifacts | T1564 | Trailing spaces/tabs are invisible in most editors and terminals |
| Command and Control | Data Obfuscation: Steganography | T1001.002 | Binary data encoded as space/tab patterns in source code |
| Collection | Data from Local System | T1005 | Extracting the encoded payload from the downloaded file |

---

## 8. Remediation and Containment

### Technical Fixes

1. Strip trailing whitespace from all committed source files using pre-commit hooks (e.g., `pre-commit` with `trailing-whitespace` fixer)
2. Configure editors and CI pipelines to flag or reject files with suspicious trailing whitespace patterns
3. Use `git diff --check` to detect trailing whitespace before merge

### MITRE D3FEND Countermeasures

- **D3-FE File Encoding Analysis:** detect non-standard whitespace patterns in source files
- **D3-DA Dynamic Analysis:** execute files in sandbox and compare visible behavior against hidden payload size
- **D3-SFA Static File Analysis:** scan for anomalous trailing bytes in text files

### NIST CSF 2.0

- **Protect (PR.DS):** enforce file integrity checks on source code repositories
- **Detect (DE.CM):** monitor for files with unusual whitespace-to-code ratios in CI pipelines

### NIST SP 800-53 Rev. 5

- **SI-3 Malicious Code Protection:** scan for steganographic payloads in source files
- **SI-7 Software, Firmware, and Information Integrity:** validate that source files match expected hashes
- **CM-3 Configuration Change Control:** review all file changes, including whitespace modifications

---

Thanks guys!! (❍ᴥ❍ʋ)

---

Steganography is all about seeing what others miss. If this writeup opened your eyes to whitespace hiding techniques, drop a follow and share it with your study group.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
