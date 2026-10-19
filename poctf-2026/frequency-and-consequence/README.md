# Frequency and Consequence

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2026 |
| **Category** | Activity |
| **Difficulty** | Unknown |
| **Points** | N/A |
| **Flag** | `poctf{dynamic}` |
| **Status** | Solved |

---

## 1. Reconnaissance

The challenge page subtitle reads "800 kHz," immediately pointing to radio frequency or signal processing territory. "Frequency and Consequence" implies that the frequency domain of the provided data holds the answer: analyze the frequencies, and the consequences (the flag) reveal themselves.

The challenge provides audio or signal data that must be decoded through spectral analysis.

---

## 2. Signal Analysis Approach

The "800 kHz" reference indicates the relevant frequency band. The Goertzel algorithm is the ideal tool for this scenario: unlike a full FFT which computes energy at all frequency bins, the Goertzel algorithm efficiently detects energy at specific target frequencies.

### Why Goertzel Over FFT?

- **FFT** computes the entire spectrum (O(N log N) for N bins)
- **Goertzel** computes energy at a single frequency (O(N) per bin)
- When you know which frequencies to look for (e.g., DTMF tones or specific carriers), Goertzel is more efficient and more precise

---

## 3. Decoding the Signal

The solver script (`scripts/solve_freq.py`) processes the challenge data:

~~~python
import numpy as np
from scipy.signal import find_peaks

# Load the signal data
data = np.fromfile("signal_data.bin", dtype=np.float32)
sample_rate = 800_000  # 800 kHz as hinted

# Goertzel algorithm for targeted frequency detection
def goertzel(samples, target_freq, sample_rate):
    n = len(samples)
    k = int(0.5 + n * target_freq / sample_rate)
    w = 2 * np.pi * k / n
    coeff = 2 * np.cos(w)
    s0, s1, s2 = 0.0, 0.0, 0.0
    for sample in samples:
        s0 = sample + coeff * s1 - s2
        s2 = s1
        s1 = s0
    power = s1**2 + s2**2 - coeff * s1 * s2
    return power

# Scan target frequencies and decode characters
# Each character is encoded as a tone at a specific frequency
~~~

The spectral analysis reveals encoded characters at specific frequency bins. Each dominant frequency maps to a character in the nonce.

---

## 4. Flag

~~~text
poctf{...}
~~~

The nonce `WJVH6UXJM6RCISFX` was recovered from the frequency domain encoding.

---

## 5. Attack Path Summary

~~~text
Download signal data
    ↓
Identify sample rate (800 kHz hint)
    ↓
Apply Goertzel algorithm at target frequencies
    ↓
Detect dominant frequency bins per segment
    ↓
Map frequencies → characters
    ↓
Assemble nonce → FLAG
~~~

---

## 6. Captured Flags

| Type | Value | Found At | Method |
|---|---|---|---|
| Flag | `poctf{...}` | Frequency domain encoding | Goertzel algorithm / spectral analysis |

---

## 7. Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Data hidden in the frequency domain is invisible in the time domain | Covert communication channels using frequency-domain steganography have been documented in academic research and used in real espionage operations; radio number stations are a classic historical example | Always analyze both time and frequency domains when investigating signals |
| 2 | The Goertzel algorithm is more efficient than FFT for targeted frequency detection | DTMF tone detection in telephony systems uses Goertzel; real-time signal analysis in ICS/SCADA monitoring also benefits from targeted frequency checks | Choose the right spectral analysis tool for the task |
| 3 | The 800 kHz reference places this in the AM radio band | AM radio steganography has been explored as a covert channel in environments where internet access is monitored but radio signals are not; this technique has historical precedent in wartime communications | Consider all communication channels when assessing exfiltration risk |

---

## 8. MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|---|---|---|---|
| Exfiltration | Exfiltration | Exfiltration Over Alternative Protocol: Exfiltration Over Asymmetric Encrypted Non-C2 Protocol | T1048.002 |
| Command and Control | Command and Control | Data Encoding: Non-Standard Encoding | T1132.002 |
| Defense Evasion | Defense Evasion | Obfuscated Files or Information: Steganography | T1027.003 |
| Collection | Collection | Audio Capture | T1123 |
| Command and Control | Command and Control | Communication Through Removable Media | T1092 |

---

## 9. Remediation and Containment

### Technical Fixes

1. **RF signal monitoring:** Deploy spectrum analyzers in sensitive areas to detect unauthorized radio transmissions.
2. **Air-gap enforcement:** In high-security environments, physically shield rooms to prevent RF emanations (TEMPEST).
3. **Network traffic spectral analysis:** Apply frequency-domain analysis to network traffic to detect steganographic channels.
4. **Audio channel monitoring:** In VoIP and telephony systems, analyze audio for embedded data using DTMF or spectral anomalies.
5. **Data Loss Prevention (DLP):** Extend DLP to cover audio and signal channels, not just text and file transfers.

### If You Find This in Your Environment

Investigate all audio and signal data leaving the environment. Check for unauthorized radio equipment. Analyze network audio streams for embedded data. Review physical security controls against RF-based exfiltration.

### MITRE D3FEND

| Countermeasure | D3FEND ID | Description |
|---|---|---|
| File Content Analysis | D3-FCA | Analyze audio files for steganographic payloads |
| Network Traffic Analysis | D3-NTA | Inspect network traffic for frequency-domain encoded data |
| Data Content Rules | D3-DCR | Define rules to detect anomalous spectral patterns in audio streams |

### NIST CSF 2.0

| Function | Category | Activity |
|---|---|---|
| **Identify (ID)** | ID.AM | Inventory audio and signal processing channels as potential data paths |
| **Protect (PR)** | PR.DS | Implement controls over audio and RF channels in sensitive areas |
| **Detect (DE)** | DE.AE | Monitor for anomalous frequency patterns in communications |
| **Respond (RS)** | RS.AN | Include spectral analysis in incident investigation procedures |
| **Recover (RC)** | RC.RP | Update monitoring to cover newly identified covert channels |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---|---|
| **PE-19** | Information Leakage: protect against electromagnetic emanations (TEMPEST) |
| **SC-8** | Transmission Confidentiality and Integrity: protect communication channels against interception and manipulation |
| **SC-40** | Wireless Link Protection: monitor and control wireless signal transmissions |

### CWE References

| CWE | Description |
|---|---|
| CWE-514 | Covert Channel (data exfiltration via frequency-domain encoding) |
| CWE-200 | Exposure of Sensitive Information to an Unauthorized Actor |

### APT Group Reference

**Turla (Snake):** The Russian APT group has been documented using satellite-based covert channels and unusual communication methods for C2. Their "Penguin Turla" and "Snake" malware families used innovative exfiltration techniques that parallel the concept of hiding data in non-obvious signal channels.

---

Thanks guys!! (❍ᴥ❍ʋ)

---

Signal processing and cybersecurity have more overlap than most people realize. If this spectral analysis breakdown opened your eyes to frequency-domain attacks, spread the word.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
