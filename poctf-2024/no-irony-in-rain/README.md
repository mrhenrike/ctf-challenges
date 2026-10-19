# No Irony in Rain

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2024 |
| **Category** | Digital Forensics |
| **Difficulty** | Expert |
| **Points** | 400 |
| **Flag** | `poctf{dynamic}` |
| **Status** | Solved |

---

## 1. Challenge Overview

A video file uploaded to YouTube as a "screener" for "POCTF 2024: The Movie." The challenge involves extracting and translating multi-language subtitles embedded in the video. The flag is hidden in the Russian subtitle track.

**Files:** `DF400.mov` (video file)

---

## 2. Video Analysis

The video is a short film with multiple subtitle tracks in different languages:

- **Arabic:** dialogue about a movie inspired by real events (translated to a reference to the film "Boneyard (2024)")
- **Bangla:** basic instructions unrelated to the flag
- **English:** ASCII art of a fish, a red herring
- **Russian:** commentary about the challenge creator with the flag embedded

---

## 3. Subtitle Extraction

Downloaded subtitles for all languages from the YouTube upload. The English subtitle track contained only a red herring (ASCII art fish).

---

## 4. Russian Subtitle Analysis

The Russian subtitle track contained conversational text about a professor ordering a student to write subtitles, complaining about lack of payment. At the end of the track, a key string appeared:

~~~text
зщсеаХгцыз_50_17_6035b
~~~

This transliteration, when mapped through a Russian keyboard layout or simply interpreted with the known `poctf{uwsp_...}` format, yields:

~~~text
poctf{uwsp_50_17_6035}
~~~

---

## 5. Verification

The flag follows the standard POCTF format and the leet-speak translates to "so it goes," a famous phrase from Kurt Vonnegut's "Slaughterhouse-Five," matching the challenge's literary themes.

---

## Lessons Learned

| # | Lesson | Detail |
|---|--------|--------|
| 1 | Multi-language subtitles are data channels | Each language track can carry independent content |
| 2 | Red herrings are deliberate in 400-level challenges | The English track exists to waste time |
| 3 | Keyboard layout transliteration is a forensic technique | Russian characters can map to Latin equivalents |
| 4 | Translation tools are forensic tools | Subtitle content in foreign languages requires systematic analysis |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID | Context |
|---|---|---|---|
| Defense Evasion | Obfuscated Files or Information: Steganography | T1027.003 | Flag hidden in video subtitle track |
| Defense Evasion | Obfuscated Files or Information | T1027 | Data concealed through foreign language and keyboard mapping |
| Exfiltration | Exfiltration Over Alternative Protocol | T1048 | Data embedded in multimedia subtitle metadata |

> **CWE-311:** Missing Encryption of Sensitive Data. The flag is embedded in plaintext within subtitle tracks.
> **CWE-200:** Exposure of Sensitive Information. Subtitle metadata leaks data to anyone who extracts it.

---

## Remediation and Containment

### Technical Fixes

1. Strip or sanitize all subtitle tracks before publishing video content
2. Implement DLP policies that scan multimedia subtitle metadata
3. Restrict who can add/modify subtitle tracks in video editing workflows
4. Use video metadata sanitization tools before distribution

### MITRE D3FEND Countermeasures

- **D3-FCOA (File Content Analysis):** extract and analyze all subtitle tracks from video files
- **D3-NTA (Network Traffic Analysis):** inspect uploaded videos for hidden subtitle content
- **D3-DA (Dynamic Analysis):** automated extraction and translation of multi-language subtitles

### NIST CSF 2.0

- **Protect (PR.DS):** sanitize multimedia metadata and subtitle tracks before distribution
- **Detect (DE.CM):** monitor for anomalous subtitle content in published videos
- **Respond (RS.MI):** review and remove suspicious subtitle tracks from published content

### NIST SP 800-53 Rev. 5

- **SC-8 (Transmission Confidentiality and Integrity):** inspect multimedia files for hidden data channels
- **AU-13 (Monitoring for Information Disclosure):** monitor subtitle tracks as potential data leakage vectors
- **SI-12 (Information Management and Retention):** sanitize metadata before publishing

### NIST SP 800-86

- **Multimedia Forensics:** extract and analyze all embedded tracks (audio, subtitle, metadata)
- **Evidence Handling:** preserve original video files before subtitle extraction

### C2M2

- **THREAT-3:** include subtitle-based data hiding in multimedia threat models
- **SITUATION-3:** monitor video publishing pipelines for unauthorized subtitle modifications

---

Thanks guys!! (❍ᴥ❍ʋ)

---

So it goes. When a video has subtitles in four languages and only one contains the flag, the real challenge is patience. Russian keyboard transliteration adds a nice touch to this 400-point treasure hunt.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

> **Reference:** Adapted from [shivang1209-dot/CTF-Writeups](https://github.com/shivang1209-dot/CTF-Writeups). Original scripts credited to the author.
