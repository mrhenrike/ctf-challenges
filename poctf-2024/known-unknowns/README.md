# Known Unknowns

**Category:** Digital Forensics
**Challenge:** Known Unknowns
**CTF:** Pointer Overflow CTF 2024
**Points:** DF 200
**Result:** Solved

**Flag:**

~~~text
poctf{uwsp_7h3_13f7_h4nd_0f_d4rkn355}
~~~

---

## 1. Challenge Overview

A WAV audio file allegedly containing the sounds of space recorded with a directional microphone. The challenge title references the famous "known unknowns" concept. The flag is hidden visually in the audio's spectrogram.

**Files:** `DF200-2.wav` (audio file)

---

## 2. Audio Playback

Loaded the file in Audacity and listened. No audible clues were detected in normal playback.

---

## 3. Spectrogram Analysis

Switched to the **Spectrogram** view in Audacity (View > Spectrogram):

The flag text appeared visually encoded in the frequency domain. Characters were "drawn" using audio frequencies at specific time positions, creating a readable message when viewed as a spectrogram.

Flag visible in the spectrogram:

~~~text
poctf{uwsp_7h3_13f7_h4nd_0f_d4rkn355}
~~~

---

## Lessons Learned

| # | Lesson | Detail |
|---|--------|--------|
| 1 | Audio spectrograms hide visual data | Frequency-domain visualization reveals patterns invisible to hearing |
| 2 | Always check spectrogram view for audio forensics | Standard practice for CTF audio challenges |
| 3 | Data can exist in domains humans cannot perceive | Ultrasonic frequencies encode data outside audible range |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID | Context |
|---|---|---|---|
| Defense Evasion | Obfuscated Files or Information: Steganography | T1027.003 | Flag hidden in audio spectrogram |
| Exfiltration | Exfiltration Over Alternative Protocol | T1048 | Data concealed in audio file for covert transmission |
| Collection | Audio Capture | T1123 | Sensitive data embedded within audio medium |

> **CWE-311:** Missing Encryption of Sensitive Data. The flag is encoded visually in frequency space without encryption.

---

## Remediation and Containment

### Technical Fixes

1. Encrypt data before encoding in audio carriers
2. Apply DLP solutions capable of audio steganalysis
3. Use spectral analysis on outbound audio files in high-security environments
4. Implement noise injection to disrupt spectrogram-based steganography

### MITRE D3FEND Countermeasures

- **D3-FCOA (File Content Analysis):** apply spectral analysis to detect audio steganography
- **D3-NTA (Network Traffic Analysis):** inspect audio files transmitted across network boundaries
- **D3-DA (Dynamic Analysis):** automated spectrogram generation for audio file inspection

### NIST CSF 2.0

- **Protect (PR.DS):** include audio files in DLP scanning scope
- **Detect (DE.CM):** deploy audio steganalysis on network egress
- **Respond (RS.MI):** quarantine audio files flagged by spectral anomaly detection

### NIST SP 800-53 Rev. 5

- **SC-8 (Transmission Confidentiality and Integrity):** inspect transmitted media for covert channels
- **AU-13 (Monitoring for Information Disclosure):** monitor for steganographic exfiltration
- **SI-4 (Information System Monitoring):** include audio analysis in monitoring capabilities

### NIST SP 800-86

- **Media Analysis:** apply spectral and waveform analysis to audio evidence
- **Tool Validation:** use Audacity, Sonic Visualiser, and custom spectral tools for examination

### C2M2

- **THREAT-3:** include audio steganography in data exfiltration threat models
- **SITUATION-2:** monitor for unusual audio file generation or transmission

---

Thanks guys!! (❍ᴥ❍ʋ)

---

The left hand of darkness reveals itself in the spectrogram. Audio forensics is one of those skills that pays off every time a CTF drops a .wav file.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

> **Reference:** Adapted from [shivang1209-dot/CTF-Writeups](https://github.com/shivang1209-dot/CTF-Writeups). Original scripts credited to the author.
