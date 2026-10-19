# You Never Liked My Music

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2024 |
| **Challenge** | You Never Liked My Music |
| **Category** | Steganography |
| **Difficulty** | Medium |
| **Points** | 200 |
| **Status** | Solved |

---

## Challenge Overview

A WAV audio file from a "jazz drummer" contains hidden data in ultrasonic frequencies (above 18kHz). The challenge description drops multiple hints about high-pitched sounds, tinnitus, and "frequencies of sound," pointing toward spectrogram analysis in the ultrasonic range.

**File provided:** `Stego200-1.wav`

---

## Objective

Analyze the audio spectrogram in the ultrasonic frequency range to extract binary-encoded data and decode the flag.

---

## Methodology

### Step 1: Listen and Observe

Playing the WAV file reveals normal jazz drumming with faint ticking sounds. Nothing audibly resembles a flag.

### Step 2: Spectrogram Analysis

Open the file in Audacity and switch to spectrogram view. At default settings, nothing unusual is visible.

### Step 3: Increase Frequency Range

Based on the challenge hints about "annoyingly high-pitched sounds" and "waving goodbye to another frequency," adjust the spectrogram view to display frequencies above **18kHz**.

This reveals distinct patterns of lines and spaces in the ultrasonic range, resembling binary encoding.

### Step 4: Decode Binary from Spectrogram

The patterns form stacks of 0s and 1s based on the width and spacing of the spectral lines:

```
01110000 01101111 01100011 01110100 01100110 01111011
01110101 01110111 01110011 01110000 01011111 00110111
01101000 00110011 01011111 01110101 01101110 00110011
01111000 00110100 01101101 00110001 01101110 00110011
01100100 01011111 01101100 00110001 01100110 00110011
01111101
```

### Step 5: Convert Binary to ASCII

Converting each 8-bit group to its ASCII character:

```
p o c t f { u w s p _ 7 h 3 _ u n 3 x 4 m 1 n 3 d _ l 1 f 3 }
```

The known prefix `poctf{uwsp_` was used to validate the initial binary values.

---

## Flag

```
poctf{uwsp_7h3_un3x4m1n3d_l1f3}
```

---

## Lessons Learned

| # | Insight |
|---|---------|
| 1 | Ultrasonic steganography hides data above human hearing range (~18kHz+) |
| 2 | Audacity's spectrogram view with extended frequency range is essential for audio stego |
| 3 | Challenge descriptions about sound, hearing, and frequencies strongly hint at spectrogram analysis |
| 4 | The flag references Socrates ("the unexamined life"), matching the theme of looking deeper |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | Description |
|--------|-----------|-------------|
| Defense Evasion | T1027.003 - Obfuscated Files: Steganography | Data hidden in ultrasonic frequencies |
| Command and Control | T1071.004 - Application Layer Protocol | Covert audio channel for data transmission |

---

## Remediation

### Technical Fixes

- Filter audio files to remove frequencies above the human hearing range (low-pass filter at 20kHz) before distribution.
- Implement spectral analysis in DLP pipelines for WAV/FLAC uploads.
- Monitor for unusual audio file transfers in environments where audio steganography is a concern.

### MITRE D3FEND

| ID | Technique |
|----|-----------|
| D3-SFA | Static File Analysis: spectral analysis on audio files |
| D3-NTA | Network Traffic Analysis: detect audio-based covert channels |

### NIST CSF 2.0

| Function | Category | Action |
|----------|----------|--------|
| Detect | DE.CM | Deploy spectral analysis tools for audio file inspection |
| Protect | PR.DS | Apply frequency filtering to audio files at ingress points |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---------|-------------|
| SI-3 | Malicious Code Protection |
| SI-4 | Information System Monitoring |

### C2M2

| Practice | Description |
|----------|-------------|
| DETECT | Include audio steganalysis in security monitoring |

### CWE

| ID | Description |
|----|-------------|
| CWE-506 | Embedded Malicious Code |

---

## References

- [shivang1209-dot POCTF 2024 Writeups](https://github.com/shivang1209-dot/shivang1209-dot) (original reference)
- [Audacity](https://www.audacityteam.org/)
- [Pointer Overflow CTF](https://pointeroverflowctf.com/)

---

Thanks guys!! (❍ᴥ❍ʋ)

Sons que ouvidos humanos nao captam, mas o espectrograma revela: esteganografia em frequencias ultrasonicas e pura elegancia tecnica. Socrates aprovaria!

[![Instagram](https://img.shields.io/badge/Instagram-%23E4405F.svg?style=for-the-badge&logo=Instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/linkedin-%230077B5.svg?style=for-the-badge&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/X-%23000000.svg?style=for-the-badge&logo=X&logoColor=white)](https://x.com/mrhenrike)
