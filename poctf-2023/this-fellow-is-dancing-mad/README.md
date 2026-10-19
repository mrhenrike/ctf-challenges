# This Fellow is Dancing Mad!

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2023 |
| **Category** | Miscellaneous |
| **Difficulty** | Hard |
| **Points** | 300 |
| **Flag** | `poctf{dynamic}` |
| **Status** | Not Solved |

---

## 1. Challenge Overview

The challenge title is a reference to "Dancing Mad," the iconic final boss theme from Final Fantasy VI (composed by Nobuo Uematsu). The title strongly suggests the challenge involves music, audio analysis, or a video game related puzzle.

No publicly available writeup exists for this challenge. The approach below documents the reconnaissance and hypotheses explored.

---

## 2. Reconnaissance

### Title Analysis

"Dancing Mad" is universally recognized in gaming culture as the multi-movement final boss theme of Final Fantasy VI. This reference likely indicates one of the following challenge types:

- **Audio steganography:** a music file with hidden data encoded in frequency, amplitude, or metadata
- **MIDI analysis:** extracting note values or timing data that encode a message
- **Game data extraction:** parsing ROM data, save files, or game assets for hidden content
- **Cultural knowledge:** answering a trivia question or decoding a cipher based on FF6 lore

### Potential Approaches

1. **Audio file analysis:** If an audio file is provided, examine it with Audacity (spectrogram view), Sonic Visualiser, or steganography tools (SteghideUI, DeepSound, OpenStego)
2. **MIDI parsing:** Extract note sequences, velocities, or timing data; convert to ASCII or hex
3. **Metadata inspection:** Check file headers, EXIF, ID3 tags for hidden text
4. **Game reference decoding:** Map Kefka's Tower floors, character dialogue, or spell data to alphanumeric values

---

## 3. Status

This challenge was not solved during the competition. No public writeup or walkthrough has been found from any participating team as of January 2024.

---

## 4. Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|--------------|
| 1 | Cultural references in challenge titles often hint at the technique required | CTF designers embed clues in titles; recognizing the reference narrows the search space | Research every unfamiliar title phrase; it may point directly to the encoding method or data source |
| 2 | Miscellaneous challenges combine multiple domains | Misc challenges often require creative thinking across audio, visual, programming, and cultural knowledge | Keep a broad toolkit ready: audio analysis, scripting, game emulation, and cultural databases |
| 3 | Not every challenge will be solved, and that is OK | In CTF competitions, time management matters more than perfection; documenting partial progress enables future revisits | Document all hypotheses and partial findings, even for unsolved challenges; they inform future attempts |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Defense Evasion | TA0005 | Obfuscated Files or Information: Steganography | T1027.003 |
| Defense Evasion | TA0005 | Obfuscated Files or Information: Embedded Payloads | T1027.009 |
| Collection | TA0009 | Audio Capture | T1123 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediation and Containment

### Technical Fixes

1. Deploy audio and media file inspection at network boundaries to detect steganographic content
2. Implement content-type validation to ensure media files match their declared formats
3. Monitor for unusual file types (MIDI, SPC, NSF) in environments where they are not expected

### MITRE D3FEND Countermeasures

- **D3-FCA File Content Analysis** to detect steganographic payloads in audio files (counters T1027.003)
- **D3-FCR File Content Rules** to flag media files with anomalous structure or embedded data (counters T1027.009)

### NIST CSF 2.0

- **Detect (DE.AE-3):** Event data aggregated to identify steganographic communication patterns
- **Protect (PR.DS-5):** Data leak prevention covering non-standard file formats

### CWE

- **CWE-506: Embedded Malicious Code** (data hidden in media files)
- **CWE-311: Missing Encryption of Sensitive Data** (data obscured via steganography rather than proper encryption)

---

## References

- Challenge name listed in [Enzo Cadoni's POCTF 2023 writeup](https://enzo-cadoni.fr/posts/poctf_2023/) (unsolved)
- "Dancing Mad" (FF6) reference: https://en.wikipedia.org/wiki/Music_of_Final_Fantasy_VI

---

Thanks guys!! (❍ᴥ❍ʋ)

---

Some challenges stay unsolved, and that is part of the game. Kefka would be proud: madness, after all, is its own reward. If you cracked this one, share the knowledge and keep the community moving forward.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
