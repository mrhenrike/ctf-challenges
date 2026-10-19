# What Goes Unwritten

**Category:** Forensics
**Challenge:** What Goes Unwritten
**CTF:** Pointer Overflow CTF 2026
**Points:** FOR 200 (Wave 3)
**Result:** Solved

**Flag:**

~~~text
44MUDQYGRDWRTJW5
~~~

---

## 1. Reconnaissance

The challenge provides `library-workstation-firefox.dmp`, a Windows minidump from a Firefox browser process. Minidumps capture a snapshot of process memory at the time of a crash, including heap data, stack frames, loaded modules, and any data resident in memory.

The title "What Goes Unwritten" hints at data that exists in memory but was never committed to disk: browser session state, cookies, form data, and temporary tokens that live only in process memory.

~~~bash
file library-workstation-firefox.dmp
# library-workstation-firefox.dmp: Mini DuMP crash report, 16 streams
~~~

---

## 2. String Extraction Strategy

Firefox internally stores many strings in UTF-16LE encoding due to its cross-platform JavaScript engine (SpiderMonkey). Standard ASCII `strings` misses these. Both encodings must be extracted:

### ASCII Strings

~~~bash
strings library-workstation-firefox.dmp | grep -iE "token|session|flag|poctf|nonce"
~~~

### UTF-16LE Strings

~~~bash
strings -e l library-workstation-firefox.dmp | grep -iE "token|session|flag|poctf|nonce"
~~~

The UTF-16LE extraction reveals two key tokens:

1. A **sessionRestoreToken** from Firefox's session recovery system
2. A **cookie value** from the active browsing session

---

## 3. Token Reconstruction

The two extracted tokens, when combined, form the 16-character nonce:

~~~text
Token 1 (sessionRestoreToken): 44MUDQYG
Token 2 (session cookie):      RDWRTJW5
Combined: 44MUDQYGRDWRTJW5
~~~

---

## 4. Attack Path Summary

~~~text
library-workstation-firefox.dmp
    |
strings (ASCII) -> partial results
    |
strings -e l (UTF-16LE) -> session tokens visible
    |
sessionRestoreToken: 44MUDQYG
    |
Session cookie: RDWRTJW5
    |
Combined nonce: 44MUDQYGRDWRTJW5 -> FLAG
~~~

---

## 5. Verification

~~~text
>> ACK :: Correct.
~~~

---

## Captured Flags

| Type | Value | Found At | Method |
|---|---|---|---|
| Flag | `44MUDQYGRDWRTJW5` | Firefox minidump (process memory) | UTF-16LE string extraction + token combination |
| Token | `44MUDQYG` | sessionRestoreToken in heap | `strings -e l` |
| Cookie | `RDWRTJW5` | Session cookie in heap | `strings -e l` |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Process memory dumps contain data never written to disk | The 2023 LastPass breach involved memory dumps from developer workstations containing vault decryption keys; Volatility framework is standard for memory forensics | Memory forensics recovers session tokens, passwords, and encryption keys that disk forensics misses |
| 2 | Firefox stores strings in UTF-16LE internally | Windows applications use UTF-16; using only ASCII `strings` misses half the data | Always extract both ASCII and UTF-16LE strings from memory dumps |
| 3 | Session tokens and cookies persist in memory long after use | Browser processes keep dead session references until garbage collection or process termination | Memory is not automatically cleared; sensitive data lingers until the process exits |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|---|---|---|---|
| Collection | TA0009 | Data from Local System | T1005 |
| Credential Access | TA0006 | OS Credential Dumping: LSASS Memory | T1003.001 |
| Credential Access | TA0006 | Credentials from Password Stores: Credentials from Web Browsers | T1555.003 |
| Discovery | TA0007 | Process Discovery | T1057 |
| Collection | TA0009 | Browser Session Hijacking | T1185 |

> **APT Reference:** APT29 (Cozy Bear) routinely targets browser process memory during post-compromise to harvest session tokens and cookies. Mimikatz (used by APT28, FIN6, ransomware operators) demonstrates the same principle: extracting credentials from memory never saved to disk. The 2022 Uber breach used stolen session cookies from a compromised endpoint.

---

## Remediation and Containment

### Technical Fixes

1. Enable Credential Guard (Windows) or similar memory isolation for sensitive process memory
2. Configure Firefox to use encrypted session storage and clear session data on crash
3. Implement full-disk encryption (BitLocker, LUKS) to protect crash dumps at rest
4. Disable automatic crash dump generation in production, or encrypt dumps on creation
5. Deploy process memory protection (PPL, VBS) to prevent unauthorized memory access

### If You Find Something Similar in Your Environment

**Immediate containment:**
- Rotate all session tokens and cookies that may have been captured in the dump
- Delete the minidump file securely (overwrite, not just delete)
- Audit crash dump directories for unexpected or exfiltrated dump files
- Review endpoint protection logs for memory access tools (ProcDump, Mimikatz, comsvcs.dll)

**MITRE D3FEND countermeasures:**
- D3-PLA (Process Lineage Analysis) to detect unauthorized process memory access
- D3-FE (File Encryption) for crash dumps and memory captures
- D3-CH (Credential Hardening) to reduce credential exposure in process memory

### Framework Alignment

**CWE:**
- CWE-316: Cleartext Storage of Sensitive Information in Memory
- CWE-312: Cleartext Storage of Sensitive Information
- CWE-200: Exposure of Sensitive Information to an Unauthorized Actor

**OWASP Top 10 (2021):**
- A02:2021 Cryptographic Failures (sensitive data in cleartext memory)
- A05:2021 Security Misconfiguration (crash dumps not encrypted/restricted)

**NIST CSF 2.0:**
- Identify (ID.AM): Inventory all crash dump generation and storage locations
- Protect (PR.DS): Encrypt crash dumps and restrict access to memory capture tools
- Detect (DE.CM): Monitor for unauthorized process memory access (ProcDump, MiniDumpWriteDump)
- Respond (RS.MI): Rotate all credentials potentially captured in memory dumps
- Recover (RC.RP): Securely delete exposed crash dumps and rebuild affected sessions

**NIST SP 800-53 (Rev. 5):**
- SC-28: Protection of Information at Rest (encrypt memory dumps)
- SI-12: Information Management and Retention (retention of crash dumps)
- AC-3: Access Enforcement (restrict access to crash dump directories)
- SC-4: Information in Shared System Resources (clear memory after sensitive operations)

**C2M2:**
- Domain: TECHNOLOGY (Cybersecurity Architecture)
- Practice: Implement data protection for transient data in process memory
- Target MIL: MIL-2 (documented crash dump security policies and memory protection standards)

---

## Final Thoughts

"What goes unwritten" is the perfect description of process memory: full of data that was never saved, never logged, never intended to persist. But a crash dump captures it all, frozen in time. Session tokens, cookies, form data, passwords in transit: everything the application was holding in memory at the moment of the dump. Memory forensics is the discipline of reading what was never written, and it remains one of the most powerful tools in the investigator's toolkit.

Thanks guys!! (❍ᴥ❍ʋ)

---

Memory forensics is where the deepest secrets hide. If this dump analysis gave you new ideas for your DFIR toolkit, pass it along.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
