# Velocity

| Field | Value |
|---|---|
| CTF | Pointer Overflow CTF 2026 |
| Category | Steganography (Wave 3) |
| Challenge ID | 103 |
| Flag | `poctf{...}` |

## Overview

A MIDI steganography challenge. The artifact is `etude.mid`, a musical etude in MIDI format. "Velocity" in MIDI terminology refers to the force with which a note is struck (0-127), and in this challenge, the note velocities carry hidden data. The title is a direct, elegant hint.

---

## 1. Reconnaissance

The challenge page provides a downloadable MIDI file (`etude.mid`). MIDI (Musical Instrument Digital Interface) encodes music as a series of events: note-on, note-off, control changes, and more. Each note-on event carries three key values:

- **Channel** (0-15)
- **Note number** (0-127, where 60 = middle C)
- **Velocity** (0-127, how hard the note is struck)

Velocity is typically used for dynamics (loud vs. soft), but it is also the perfect hiding place for steganographic data: 7 bits per note, and listeners might not notice small velocity variations.

---

## 2. Identifying the Steganographic Channel

Using `python3 -I` with the `mido` library to parse the MIDI file:

```python
import mido

mid = mido.MidiFile('etude.mid')
velocities = []
for track in mid.tracks:
    for msg in track:
        if msg.type == 'note_on' and msg.velocity > 0:
            velocities.append(msg.velocity)

print(f"Total note-on events: {len(velocities)}")
print(f"Velocity range: {min(velocities)}-{max(velocities)}")
print(f"First 20 velocities: {velocities[:20]}")
```

The velocity values showed patterns inconsistent with natural musical dynamics: specific hex-range values that, when converted, spell out ASCII characters.

---

## 3. Extraction

Each velocity byte encodes part of the hex nonce. Extracting and converting:

```python
hex_chars = []
for v in velocities:
    if 0x30 <= v <= 0x39 or 0x41 <= v <= 0x46:
        hex_chars.append(chr(v))

nonce = ''.join(hex_chars)
print(f"Nonce: {nonce}")
```

Output:

```text
BF9DBAF4A82E68ED
```

The velocity values directly encode the ASCII representation of hex digits (0-9 = 0x30-0x39, A-F = 0x41-0x46).

---

## 4. Verification

- The decoded nonce is 16 hex characters, consistent with the CTF's nonce format
- Wrapped as `poctf{...}` and submitted: **Correct**
- The MIDI file plays as a legitimate musical piece; the velocity encoding does not produce audibly unusual dynamics

---

## Captured Flags

| Type | Value | Found At | Method |
|---|---|---|---|
| Flag | `poctf{...}` | MIDI note-on velocity values | ASCII hex extraction from velocity bytes |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | MIDI velocity is an underappreciated steganographic channel | Unlike audio files where modifications may be audible, MIDI velocity values can be tweaked without obviously changing the musical output | Non-audio media formats (MIDI, sheet music, notation files) can carry covert data |
| 2 | The challenge title was a direct technical hint | "Velocity" is the exact MIDI parameter name used for data hiding | CTF titles often contain the critical clue; always research domain-specific terminology |
| 3 | Steganographic data can be extracted with minimal tooling | A simple Python script with `mido` was sufficient to extract the full flag | Steganographic analysis should start with the simplest hypothesis before escalating to spectral analysis or deep tooling |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|---|---|---|---|
| Defense Evasion | Obfuscated Files or Information | Steganography | T1027.003 |
| Command and Control | Data Obfuscation | Steganography (covert channel via MIDI velocity) | T1001.002 |
| Exfiltration | Exfiltration Over C2 Channel | Data encoded in media file | T1041 |
| Defense Evasion | Hide Artifacts | Hidden data in legitimate media format | T1564 |

---

## Remediation and Containment

### Technical Fixes

1. Implement deep content inspection for media files leaving the network, not just file-type checks
2. Deploy steganographic detection tools (steganalysis) as part of DLP pipelines
3. Monitor for unusual MIDI file transfers in environments where they are not expected
4. Use statistical analysis on velocity distributions to detect non-musical patterns

### If You Find This in Your Environment

- Quarantine the MIDI file and extract all velocity values for analysis
- Check the velocity distribution: musical dynamics follow bell curves; steganographic encoding produces flat or patterned distributions
- Investigate the source of the file and the user who transferred it
- Scan for other media files (audio, image, video) that may carry similar covert channels

### MITRE D3FEND

| Countermeasure | D3FEND ID | Application |
|---|---|---|
| File Content Rules | D3-FCR | Detect non-musical velocity patterns in MIDI files |
| File Analysis | D3-FA | Deep inspection of media file metadata and payload fields |
| Network Traffic Community Deviation | D3-NTCD | Flag unusual media file transfers |

### NIST CSF 2.0

| Function | Category | Application |
|---|---|---|
| **Identify (ID)** | Asset Management | Catalog media file types traversing the network |
| **Protect (PR)** | Data Security | Implement DLP rules for media files with anomalous properties |
| **Detect (DE)** | Continuous Monitoring | Deploy steganalysis on outbound media files |
| **Respond (RS)** | Analysis | Investigate flagged media files for covert data channels |

### NIST SP 800-53 Rev. 5

| Control | Title | Application |
|---|---|---|
| SI-4 | System Monitoring | Monitor for steganographic covert channels in media files |
| AU-13 | Monitoring for Information Disclosure | Detect data exfiltration via non-standard encoding in media |

### CWE References

| CWE | Title | Relevance |
|---|---|---|
| CWE-514 | Covert Channel | MIDI velocity encoding as a data hiding channel |

### APT Group Reference

**Turla (Venomous Bear):** Known for using steganographic techniques to hide C2 data within media files, including embedding commands in image pixels and audio metadata. The MIDI velocity channel mirrors this approach: hiding operational data in a legitimate media format that bypasses standard content filters.

---

Thanks guys!! (❍ᴥ❍ʋ)

---

Music hides more than melodies. If you found this MIDI forensics walkthrough useful, share it with fellow CTF players and let's keep decoding the world together.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
