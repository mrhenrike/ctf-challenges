# The Apparatus, Apport

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2026 |
| **Category** | OSINT |
| **Difficulty** | Medium |
| **Points** | 200 |
| **Flag** | `poctf{dynamic}` |
| **Status** | Solved |

---

## 1. Reconnaissance

The fourth entry in the Apparatus series drops you into a Victorian-era occult mystery. "Apport" in spiritualist tradition refers to the teleportation of objects during a seance. The challenge provides a zip archive containing five cryptic artifacts that all converge on a single historical figure.

---

## 2. Artifact Inventory

| # | File | Content |
|---|---|---|
| 1 | `recovered.jpg` | Photograph with EXIF GPS: 48 53'12.11"N, 2 20'35.16"E (Paris). Date: 1887-11-15 |
| 2 | `correspondence.eml` | Historical correspondence mentioning Golden Dawn cipher-manuscripts, Hackney birthplace (1854), Highland Scots clan name |
| 3 | `transcript.pdf` | Lecture transcript from the Isis-Urania Temple discussing cosmic planes and esoteric philosophy |
| 4 | `coordinates.gpx` | Four GPS waypoints: Hackney 1854, Isis-Urania Temple 1888, Ahathoor Temple 1894, Paris 1918 |
| 5 | `unaccounted_transmission.txt` | "The circle is closed against all who did not close it" (ritualistic phrase) |

---

## 3. OSINT Analysis

### EXIF Data Extraction

~~~bash
exiftool recovered.jpg
# GPS Position: 48 53'12.11"N, 2 20'35.16"E
# Date/Time Original: 1887:11:15
~~~

The coordinates point to Paris, France. The date places the photograph in late 1887, shortly before the founding of the Golden Dawn.

### Cross-Referencing the Clues

Each artifact provides independent evidence that converges on one person:

- **Hackney, London, 1854:** Birthplace
- **Golden Dawn cipher-manuscripts:** Co-founder who translated the founding documents
- **Isis-Urania Temple:** The original Golden Dawn temple in London, founded 1888
- **Ahathoor Temple, Paris, 1894:** The Paris chapter
- **Highland Scottish ancestry:** Claimed MacGregor clan lineage
- **Paris, 1918:** Place and year of death

All five artifacts point to **Samuel Liddell MacGregor Mathers** (1854-1918), co-founder of the Hermetic Order of the Golden Dawn.

---

## 4. Answer Construction

The challenge requires `LASTNAME_YEAR` format:

~~~text
MATHERS_1888
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
| Flag | `MATHERS_1888` | Multi-source OSINT convergence | EXIF GPS + historical correspondence + GPX timeline + temple references |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Five independent artifacts converge on a single answer | Intelligence analysis uses convergence methodology: multiple independent sources increase assessment confidence | Cross-reference all data points; convergence from independent sources confirms findings |
| 2 | EXIF metadata provides geolocation and temporal data | EXIF data has been used in OSINT investigations to geolocate journalists, identify whistleblowers, and track military personnel (Strava heatmap incident, 2018) | Always check image metadata for GPS, timestamps, device model, and software signatures |
| 3 | Historical OSINT requires domain knowledge | Intelligence agencies maintain historical research capabilities for archival data context | Build broad knowledge across history, geography, and culture; OSINT is not just technical tools |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|---|---|---|---|
| Reconnaissance | TA0043 | Gather Victim Identity Information | T1589 |
| Reconnaissance | TA0043 | Search Open Technical Databases | T1596 |
| Reconnaissance | TA0043 | Gather Victim Host Information: Software | T1592.002 |
| Resource Development | TA0042 | Obtain Capabilities: Tool | T1588.002 |

> **APT Reference:** APT29 (Cozy Bear) conducts extensive OSINT research using multi-source intelligence fusion. Sandworm has used EXIF metadata analysis and geolocation for targeting. The Strava heatmap incident (2018) demonstrated how fitness app metadata revealed secret military base locations and layouts.

---

## Remediation and Containment

### Technical Fixes

1. Strip EXIF metadata from all images before publication (`exiftool -all= image.jpg`)
2. Implement automated metadata sanitization in document publishing pipelines
3. Train personnel on OPSEC: avoid publishing geotagged photos or location-linked data
4. Use GPS coordinate fuzzing for any publicly shared location data

### If You Find Something Similar in Your Environment

**Immediate containment:**
- Audit all publicly accessible images and documents for metadata leaks
- Deploy automated EXIF stripping on web-facing image upload endpoints
- Review GPX/GPS data shared externally for sensitive location exposure
- Train employees on metadata OPSEC near sensitive facilities

**MITRE D3FEND countermeasures:**
- D3-FAPA (File Access Pattern Analysis) to detect bulk metadata extraction
- D3-NTA (Network Traffic Analysis) to identify OSINT tool signatures targeting assets
- D3-DA (Data Authentication) to verify provenance of published documents

### Framework Alignment

**CWE:**
- CWE-200: Exposure of Sensitive Information to an Unauthorized Actor
- CWE-359: Exposure of Private Personal Information to an Unauthorized Actor
- CWE-538: Insertion of Sensitive Information into Externally-Accessible File or Directory

**OWASP Top 10 (2021):**
- A01:2021 Broken Access Control (metadata exposure)
- A05:2021 Security Misconfiguration (EXIF data not stripped)

**NIST CSF 2.0:**
- Identify (ID.AM): Inventory all published content for metadata exposure
- Protect (PR.DS): Implement automated metadata sanitization
- Detect (DE.CM): Monitor for OSINT reconnaissance targeting organizational assets
- Respond (RS.AN): Assess impact of any confirmed metadata leaks
- Recover (RC.CO): Remove exposed metadata and notify affected individuals

**NIST SP 800-53 (Rev. 5):**
- SI-12: Information Management and Retention (sanitize metadata before publication)
- AT-2: Literacy Training and Awareness (OPSEC training for metadata)
- SC-28: Protection of Information at Rest (metadata in archived documents)

**C2M2:**
- Domain: THREAT (Threat and Vulnerability Management)
- Practice: Reduce cybersecurity vulnerabilities through proactive metadata management
- Target MIL: MIL-2 (documented metadata sanitization procedures)

---

## Final Thoughts

OSINT challenges are reminders that intelligence work is fundamentally about convergence. One data point is a clue; five independent data points are a finding. Extracting EXIF metadata, correlating GPS coordinates with historical records, and cross-referencing biographical timelines are the same skills used in real-world threat intelligence, fraud investigation, and counterespionage.

Thanks guys!! (❍ᴥ❍ʋ)

---

Historical OSINT is a niche that deserves more love. If this Victorian mystery got you thinking about metadata and intelligence fusion, share it and tag me.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
