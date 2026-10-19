# Columns of Holes

| Field | Value |
|---|---|
| CTF | Pointer Overflow CTF 2026 |
| Category | Miscellaneous / Steganography (Wave 3) |
| Challenge ID | 85 |
| Flag | `503DA0579EC7E5CC` |

## Overview

Old-school meets new-school in this challenge. You are given images of two IBM Hollerith punch cards, and your job is to decode them. Sounds simple until you realize that accurate OCR of punch hole positions requires real image processing, and the cards contain an additional encoding layer via PAT markers that determine how to extract the final nonce.

## The Cards

Two punch card images are provided. Each card follows the standard IBM 80-column format with 12 rows (rows 12, 11, 0-9 from top to bottom). Holes in specific row combinations within each column encode a character using the Hollerith code.

## Approach: Connected Component Analysis

Rather than trying to manually read punch holes, we wrote a solver using `scipy.ndimage.label` for connected component analysis:

1. **Binarize** the image (threshold to find dark punch holes)
2. **Filter components** by height (>15px) to exclude column number labels at the bottom of the card
3. **Detect rows:** Take the top 12 rows by hole count (cards have 12 data rows)
4. **Detect columns:** Use median column spacing to interpolate a full 80-column grid, since some columns may have no holes
5. **Map holes to Hollerith code:** For each column, identify which rows have holes and look up the character

A key bug fix was needed: the Hollerith lookup table uses row tuples as keys, but the order of detected rows could vary. Sorting the keys solved this:

```python
HOLLERITH = {tuple(sorted(k)): v for k, v in HOLLERITH_RAW.items()}
```

## Decoded Cards

- **Card A:** `JOB.1391A   PID0437816/03/67OP!ZSN39PAT.34  B5E5X71095S3TOBD83DA5I00XI95N4J75TTN`
- **Card B:** `JOB.1391B   PID8470605/09/67OP!EJR59PAT.62  HUN6SI9IERC17DEO51CKC44CAY4MRPCZILRG`

## PAT Marker Extraction

The PAT fields encode stride and offset parameters:

- **PAT.34** = stride 3, offset 4 (applied to Card A's data portion)
- **PAT.62** = stride 6, offset 2 (applied to Card B's data portion)

Applying stride/offset extraction to the data portions of each card and combining the results yields 8 characters per card. The combined 16-character nonce:

**503DA0579EC7E5CC**

## Key Takeaways

- Hollerith punch card encoding is a real historical data format from the 1960s-70s era of mainframe computing. Understanding legacy data formats is surprisingly relevant in forensics and CTF.
- Image processing with connected component analysis is more robust than pixel-level threshold scanning for detecting structured patterns.
- Always sort your dictionary keys when the order of detected elements might vary.

---

## Captured Flags

| Type | Value | Found At | Method |
|---|---|---|---|
| Flag | `503DA0579EC7E5CC` | PAT stride/offset extraction from decoded punch cards | Hollerith OCR + connected component analysis + PAT marker decoding |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Hollerith punch card encoding is a real legacy data format | Government agencies, banks, and critical infrastructure still have archived data in legacy formats that require specialized decoding tools | Legacy format knowledge is essential for forensics and data recovery |
| 2 | Connected component analysis outperforms pixel-level scanning | Modern DFIR tools use the same CV techniques (OpenCV, scipy) for document analysis, stamp detection, and watermark recovery | Image processing with CCA is robust against noise and scanning artifacts |
| 3 | PAT markers encode additional transformation parameters | Real-world steganography and covert channels use multi-layer encoding with embedded parameters | Always look for metadata within decoded data that defines further processing steps |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|---|---|---|---|
| Collection | TA0009 | Data from Local System | T1005 |
| Defense Evasion | TA0005 | Obfuscated Files or Information: Steganography | T1027.003 |
| Discovery | TA0007 | File and Directory Discovery | T1083 |
| Exfiltration | TA0010 | Exfiltration Over C2 Channel (encoded data in images) | T1041 |

> **APT Reference:** APT29 (Cozy Bear) has used steganographic encoding in images for C2 communication and data exfiltration. The Turla Group embedded commands in image metadata and pixel patterns, similar to the multi-layer encoding demonstrated by the PAT markers in this challenge.

---

## Remediation and Containment

### Technical Fixes

1. Implement data-at-rest encryption for archived legacy formats to prevent offline decoding
2. Use integrity checksums (SHA-256) for legacy data archives to detect tampering
3. Restrict access to legacy data processing tools and archived media
4. Maintain documentation for proprietary or legacy encoding formats used in archival storage

### If You Find Something Similar in Your Environment

**Immediate containment:**
- Audit all legacy data archives for unencrypted sensitive content
- Implement access controls on legacy media and data conversion tools
- Monitor for unauthorized access to archival storage systems
- Validate integrity of legacy data during any migration or conversion process

**MITRE D3FEND countermeasures:**
- D3-FCA (File Content Analysis) to detect steganographic content in image files
- D3-FE (File Encryption) for legacy data at rest
- D3-DA (Data Authentication) to ensure integrity of archived data

### Framework Alignment

**CWE:**
- CWE-311: Missing Encryption of Sensitive Data (unencrypted archival data)
- CWE-200: Exposure of Sensitive Information to an Unauthorized Actor
- CWE-327: Use of a Broken or Risky Cryptographic Algorithm (obfuscation via legacy encoding)

**OWASP Top 10 (2021):**
- A02:2021 Cryptographic Failures (data encoded but not encrypted)

**NIST CSF 2.0:**
- Identify (ID.AM): Inventory legacy data formats and their sensitivity levels
- Protect (PR.DS): Encrypt legacy archives and restrict access
- Detect (DE.CM): Monitor for unauthorized decoding or conversion of legacy data
- Respond (RS.MI): Contain exposure if legacy data is decoded without authorization
- Recover (RC.RP): Re-encrypt and re-archive exposed legacy data

**NIST SP 800-53 (Rev. 5):**
- SC-28: Protection of Information at Rest
- MP-4: Media Storage (secure storage of legacy media)
- AC-3: Access Enforcement (restrict legacy data access)

**C2M2:**
- Domain: ASSET (Asset, Change, and Configuration Management)
- Practice: Manage IT and OT assets including legacy data and media
- Target MIL: MIL-1 (inventory and basic protection for legacy data stores)

---

## Final Thoughts

Hollerith punch cards are a beautiful reminder that data encoding predates the digital age. The same principles of frequency analysis, pattern recognition, and multi-layer decoding apply whether you are reading a 1967 mainframe card or analyzing modern steganographic C2 traffic. Legacy formats are not just historical curiosities; they show up in forensic investigations, data recovery, and archival systems far more often than most people expect.

Thanks guys!! (❍ᴥ❍ʋ)

---

Did this punch card decoding journey take you back in time? Share it with your crew and let's keep the old-school hacking spirit alive.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
