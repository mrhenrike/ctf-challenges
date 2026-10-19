# Sight Without Vision

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2023 |
| **Challenge** | Sight Without Vision |
| **Category** | Miscellaneous |
| **Difficulty** | Easy |
| **Points** | 100 |
| **Status** | Solved |

---

## 1. Challenge Overview

The challenge presents a riddle whose answer is a common English word. The flag is that word encoded in leetspeak format following the standard POCTF flag structure.

---

## 2. Solving the Riddle

The riddle describes something that:
- Everyone has one
- It identifies you
- It can be spoken but not seen
- You use it every day without thinking

The answer is: **"name"**

Converting to the POCTF flag format with leetspeak encoding:

~~~text
poctf{uwsp_n4m3}
~~~

---

## 3. Attack Path Summary

~~~text
Riddle text
    |
Solve riddle -> answer: "name"
    |
Convert to leetspeak flag format
    |
FLAG: poctf{uwsp_n4m3}
~~~

---

## 4. Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|--------------|
| 1 | Social engineering relies on puzzle-solving skills | Phishing and pretexting scenarios require interpreting ambiguous clues from targets | Critical thinking and lateral problem-solving are core security skills |
| 2 | Leetspeak encoding is a common obfuscation in CTFs | Leetspeak is also used in underground forums and malware naming to evade filters | Recognizing common substitution patterns (4=a, 3=e, 0=o) aids in decoding obfuscated text |
| 3 | Simple challenges test fundamentals | Not every problem requires complex tools; logical reasoning is often sufficient | Start with the simplest hypothesis before reaching for technical solutions |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Reconnaissance | TA0043 | Gather Victim Identity Information | T1589 |
| Initial Access | TA0001 | Phishing | T1566 |
| Defense Evasion | TA0005 | Obfuscated Files or Information | T1027 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediation and Containment

### Technical Fixes

1. Implement content filters that detect leetspeak and common character substitutions in user inputs
2. Train security teams to recognize obfuscation patterns in social engineering attempts
3. Use normalized text comparison in detection rules to catch substitution-based evasion

### MITRE D3FEND Countermeasures

- **D3-UBA User Behavior Analysis** for detecting social engineering patterns (counters T1566)
- **D3-DA Data Analysis** to normalize and detect leetspeak in communication channels (counters T1027)

### NIST CSF 2.0

- **Protect (PR.AT-1):** Security awareness training covers social engineering and obfuscation techniques
- **Detect (DE.CM-3):** Personnel activity is monitored for social engineering indicators

### NIST SP 800-53 Rev. 5

- **AT-2: Literacy Training and Awareness** (train staff to recognize obfuscation and social engineering)
- **SI-3: Malicious Code Protection** (detect obfuscated content in communications)

### CWE

- **CWE-116: Improper Encoding or Escaping of Output** (character substitution to evade detection)

---

## References

- Solve approach based on research from [Jihun Hwang's POCTF 2023 writeup](https://jihunhwang.github.io/UWSP_CTF_2023_writeup/) and [Joooook's blog](https://joooook.github.io/2024/02/05/UWSP%20Pointer%20Overflow%20CTF/)

---

Thanks guys!! (❍ᴥ❍ʋ)

---

Having sight without vision is like having data without analysis. The answer was right in front of us, hiding behind a riddle that required nothing more than a clear head and a bit of lateral thinking.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
