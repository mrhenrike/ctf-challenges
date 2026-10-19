# Never Met the Pieman

**Category:** Digital Forensics
**Challenge:** Never Met the Pieman
**CTF:** Pointer Overflow CTF 2024
**Points:** DF 200
**Result:** Solved

**Flag:**

~~~text
poctf{uwsp_71m3_3n0ugh_f0r_l0v3}
~~~

---

## 1. Challenge Overview

A MOV video file from a vacation recording in a European museum. The creator mentions adding "awesome video editing skills" to the footage. The flag is hidden in the video's audio stream metadata.

**Files:** `DF200-3.mov` (video file)

---

## 2. Initial Inspection

Viewed the video, which shows someone recording statues in a museum. Nothing visually suspicious.

Checked for alternate streams and metadata using `ffprobe` and `exiftool`:

~~~bash
ffprobe -show_streams DF200-3.mov
exiftool DF200-3.mov
~~~

---

## 3. Discovering the Hidden String

In the audio stream metadata, an unusual string appeared in the stream name field:

~~~text
4namecG9jdGZ7dXdzcF83MW0zXzNuMHVnaF9mMHJfbDB2M30=
~~~

The `4name` prefix appeared to be a metadata label artifact. Removing it leaves:

~~~text
cG9jdGZ7dXdzcF83MW0zXzNuMHVnaF9mMHJfbDB2M30=
~~~

---

## 4. Base64 Decoding

Decoded the Base64 string:

~~~bash
echo "cG9jdGZ7dXdzcF83MW0zXzNuMHVnaF9mMHJfbDB2M30=" | base64 -d
~~~

Output: `poctf{uwsp_71m3_3n0ugh_f0r_l0v3}`

---

## Lessons Learned

| # | Lesson | Detail |
|---|--------|--------|
| 1 | Video metadata hides data in stream properties | Audio stream names and tags are often overlooked |
| 2 | Base64 strings in metadata are suspicious | Encoded strings in non-standard fields warrant investigation |
| 3 | Prefix artifacts need manual removal | Metadata labels can prepend encoded content |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID | Context |
|---|---|---|---|
| Defense Evasion | Obfuscated Files or Information: Steganography | T1027.003 | Flag hidden in video file's audio stream metadata |
| Defense Evasion | Obfuscated Files or Information | T1027 | Base64 encoding conceals the plaintext flag |
| Collection | Data Staged: Local Data Staging | T1074.001 | Sensitive data embedded in a video file for transport |

> **CWE-312:** Cleartext Storage of Sensitive Information. The flag is Base64-encoded (not encrypted) in metadata.
> **CWE-200:** Exposure of Sensitive Information. Metadata fields leak data to anyone inspecting the file.

---

## Remediation and Containment

### Technical Fixes

1. Strip all non-essential metadata from media files before distribution
2. Inspect multimedia container metadata for anomalous entries
3. Implement DLP policies that scan video file metadata
4. Use metadata sanitization tools (mat2, ExifTool) in publishing pipelines

### MITRE D3FEND Countermeasures

- **D3-FCOA (File Content Analysis):** scan multimedia metadata for encoded strings
- **D3-NTA (Network Traffic Analysis):** inspect video files crossing network boundaries
- **D3-DA (Dynamic Analysis):** automated detection of Base64 patterns in metadata fields

### NIST CSF 2.0

- **Protect (PR.DS):** sanitize metadata from files before external sharing
- **Detect (DE.CM):** scan for Base64-encoded content in file metadata
- **Respond (RS.MI):** quarantine files with anomalous metadata for review

### NIST SP 800-53 Rev. 5

- **SC-8 (Transmission Confidentiality and Integrity):** inspect multimedia files for covert data
- **AU-13 (Monitoring for Information Disclosure):** monitor metadata channels for data leakage
- **SI-12 (Information Management and Retention):** strip unnecessary metadata from distributed files

### NIST SP 800-86

- **Multimedia Forensics:** examine all streams and metadata in container formats
- **Evidence Preservation:** hash files before metadata examination to maintain integrity

### C2M2

- **THREAT-3:** include multimedia metadata exfiltration in data loss threat models
- **SITUATION-2:** monitor for files with anomalous metadata patterns

---

Thanks guys!! (❍ᴥ❍ʋ)

---

Time enough for love, and time enough to check every metadata field in a video file. The Pieman might be lost in translation, but the flag was just a Base64 decode away.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

> **Reference:** Adapted from [shivang1209-dot/CTF-Writeups](https://github.com/shivang1209-dot/CTF-Writeups). Original scripts credited to the author.
