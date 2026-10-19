# The Apparatus, The Rapping

| Field | Value |
|---|---|
| CTF | Pointer Overflow CTF 2026 |
| Category | Steganography (Wave 3, Apparatus Series) |
| Challenge ID | 101 |
| Flag | `99CD887F9C53AB2A` |

## Overview

The third Apparatus challenge evokes Edgar Allan Poe's "The Raven" with its title: "the rapping" at the chamber door. But in the context of this CTF, the rapping is literal: the challenge provides an audio file (`recording.wav`) containing encoded data through knocking or tapping sounds.

---

## 1. Reconnaissance

The challenge page provides `recording.wav`, an audio recording containing rhythmic knocking/tapping patterns. The word "rapping" in the Apparatus series context points to tap code: a communication method historically used by prisoners of war (most famously in the Hanoi Hilton during the Vietnam War) to communicate through walls.

Tap code uses a 5x5 Polybius square where each letter is encoded as two groups of taps: row number, then column number.

```text
     1  2  3  4  5
  +--+--+--+--+--+
1 | A  B  C  D  E
2 | F  G  H  I  J
3 | L  M  N  O  P
4 | Q  R  S  T  U
5 | V  W  X  Y  Z
```

Note: K is replaced by C in the standard tap code grid.

---

## 2. Audio Analysis

Loading the WAV file and analyzing the waveform:

```python
import wave
import struct
import numpy as np

with wave.open('recording.wav', 'rb') as wav:
    frames = wav.readframes(wav.getnframes())
    samples = np.frombuffer(frames, dtype=np.int16)
    sample_rate = wav.getframerate()
```

The amplitude envelope reveals distinct groups of taps separated by pauses. The timing analysis identifies:

- **Short pause:** separates taps within a group (row count vs. column count)
- **Medium pause:** separates row group from column group (one character)
- **Long pause:** separates characters

---

## 3. Decoding

Extracting the tap groups from the amplitude peaks and mapping through the Polybius square:

```python
def decode_tap_code(tap_groups):
    grid = "ABCDEFGHIJLMNOPQRSTUVWXYZ"
    result = ""
    for i in range(0, len(tap_groups), 2):
        row = tap_groups[i] - 1
        col = tap_groups[i+1] - 1
        idx = row * 5 + col
        if 0 <= idx < 25:
            result += grid[idx]
    return result
```

The decoded output produces the hex nonce:

```text
99CD887F9C53AB2A
```

---

## 4. Verification

- The 16-character hex nonce matches the expected flag format
- Submitted on the challenge page: "The signal resolves." confirmed correct
- The Apparatus series maintains its seance/spiritualism theme: spirits "rapping" on tables was a classic Victorian seance technique, and tap code is the literal technical implementation

---

## Captured Flags

| Type | Value | Found At | Method |
|---|---|---|---|
| Nonce | `99CD887F9C53AB2A` | Audio tapping patterns in recording.wav | Tap code decoding via Polybius square |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Tap code is a real communication protocol used in high-security environments | POWs in Vietnam used this exact system to communicate through walls when speech was forbidden | Historical communication methods often appear in steganography challenges; knowing the history gives you the cipher |
| 2 | Audio steganography goes beyond spectral hiding | Simple amplitude patterns (tapping, silence) can encode data without sophisticated signal processing | Start analysis with the simplest hypothesis: audible patterns before spectral/frequency domain |
| 3 | The Apparatus series uses thematic consistency as a hint | Each Apparatus challenge's title directly names the encoding technique within the seance metaphor | Series challenges reward reading the narrative, not just the technical prompt |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|---|---|---|---|
| Defense Evasion | Obfuscated Files or Information | Steganography | T1027.003 |
| Command and Control | Data Obfuscation | Steganography (covert audio channel) | T1001.002 |
| Defense Evasion | Hide Artifacts | Data hidden in audio file | T1564 |
| Collection | Audio Capture | Audio file as data carrier | T1123 |

---

## Remediation and Containment

### Technical Fixes

1. Implement audio file inspection in DLP pipelines to detect non-speech patterns
2. Monitor for unusual audio file transfers in corporate environments
3. Deploy behavioral analysis on outbound media: unexpected WAV/MP3 attachments in emails or uploads
4. Use spectral and temporal analysis tools to flag files with abnormally regular patterns

### If You Find This in Your Environment

- Analyze the audio file's amplitude envelope for structured timing patterns
- Compare against known encoding schemes: Morse code, tap code, DTMF tones
- Investigate the file's origin, transmission path, and intended recipient
- Check for other audio files following similar patterns in the same timeframe

### MITRE D3FEND

| Countermeasure | D3FEND ID | Application |
|---|---|---|
| File Content Rules | D3-FCR | Detect structured tapping patterns in audio files |
| File Analysis | D3-FA | Temporal and amplitude analysis of audio content |
| Network Traffic Community Deviation | D3-NTCD | Flag unusual audio file transfers |

### NIST CSF 2.0

| Function | Category | Application |
|---|---|---|
| **Identify (ID)** | Asset Management | Track media file types in the environment |
| **Protect (PR)** | Data Security | Restrict unnecessary audio file transfers |
| **Detect (DE)** | Continuous Monitoring | Monitor for structured patterns in audio files |
| **Respond (RS)** | Analysis | Decode and analyze flagged audio for covert data |

### NIST SP 800-53 Rev. 5

| Control | Title | Application |
|---|---|---|
| SI-4 | System Monitoring | Detect covert channels in audio media |
| SC-7 | Boundary Protection | Inspect media files at network boundaries for anomalous content |

### CWE References

| CWE | Title | Relevance |
|---|---|---|
| CWE-514 | Covert Channel | Audio tapping patterns as a steganographic data channel |

### APT Group Reference

**APT32 (OceanLotus):** Has used audio and multimedia files as C2 channels and exfiltration vectors, embedding data within legitimate media formats to bypass network monitoring. The tap code approach mirrors the principle of using simple, low-bandwidth covert channels that evade automated content inspection.

---

Thanks guys!! (❍ᴥ❍ʋ)

---

Sometimes the ghosts really do knock back. If this Apparatus challenge opened your ears to audio steganography, tag me and spread the signal.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
