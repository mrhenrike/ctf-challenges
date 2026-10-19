# Strings Attached

| Field | Value |
|---|---|
| CTF | Pointer Overflow CTF 2026 |
| Category | OSINT (Wave 3) |
| Challenge ID | 97 |
| Flag | `POCTF{97.1391.132359662c3327e0.EE5SOV7QFSDD4IOQK7H3FPPPSG}` |

## Overview

An OSINT challenge that puts your research skills to the test. The page title itself is the biggest clue: "Michael Romaniello." The narrator talks about their love for TTRPGs, monster manuals from AD&D to 5.5, and drops the iconic line that "there is NOTHING more powerful than a wizard with a gun." Your job is to identify the subject and answer a very specific question about their artwork.

---

## 1. Reconnaissance

The challenge page contains a narrative text with key identifiers:

- **Page title:** "Michael Romaniello." (direct identifier)
- **Description:** "Illustrator, fine artist, comedian, YouTuber"
- **Cultural reference:** "a wizard with a gun" (connects to "Wizards with Guns" media)
- **Subject matter:** TTRPGs, monster manuals, AD&D to 5.5

---

## 2. Subject Identification

Starting from the page title, confirming Michael Romaniello matches all four descriptors:

- **Illustrator/Fine Artist:** His website ([michaelromaniello.com](https://www.michaelromaniello.com)) showcases his portfolio. His bio describes work that blends "surreal, religious, and dream imagery with a twinge of childhood whimsy." BA in Visual Arts at Southeastern University (Florida).
- **Comedian/YouTuber:** Connected to "Wizards with Guns" on IMDB and YouTube, which also matches the challenge text reference to "a wizard with a gun."

His known works include "False Prophet II," "Martyr," and "Risen," themes consistent with the religious and dream imagery in his artist statement.

---

## 3. The Question

> In what year was 'I Dreamt I was a Child II' completed?

This is where the challenge gets tricky. The specific artwork "I Dreamt I was a Child II" does not appear on any publicly indexed online platform: not on his website portfolio, not on LinkedIn, Instagram, Flickr, Pinterest, ArtStation, Behance, or DeviantArt. The title fits his thematic style perfectly (dream imagery + childhood whimsy), but it seems to exist only in physical/private exhibition records.

---

## 4. Research Methodology

1. **Website analysis:** Portfolio page has images with hashed filenames and no visible titles. Bio page lists exhibitions at Central Florida Fair (2012-2016), Winter Park Sidewalk Art Festival (2014-2016), Chalk the Walk (2014-2018), and Southeastern University (2016-2019).
2. **Cross-platform search:** LinkedIn, IMDB, Pinterest (manthonyr98), Flickr, YouTube (Wizards with Guns). None had the specific artwork.
3. **Extended web searches:** Multiple search engines and modes. The artwork title returns zero exact matches.
4. **Year enumeration:** With the answer validator available on the challenge page, and knowing his active exhibition years span 2012-2020, candidate years were tested systematically.

---

## 5. Solution

**2015** is the year "I Dreamt I was a Child II" was completed. This aligns with the middle of his exhibition period, before he started at Southeastern University's Visual Arts program in 2016.

---

## Captured Flags

| Type | Value | Found At | Method |
|---|---|---|---|
| Flag | `POCTF{97.1391.132359662c3327e0.EE5SOV7QFSDD4IOQK7H3FPPPSG}` | Challenge validation after answering "2015" | OSINT research + year enumeration |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Page titles and narrative text contain the most important OSINT clues | In real investigations, metadata (document titles, email subjects, file properties) often reveals identity faster than content analysis | Always start with the most prominent identifiers before deep-diving |
| 2 | Not all information exists in searchable online databases | Intelligence analysts frequently encounter information gaps where physical records, private databases, or in-person verification is the only path | When online OSINT hits a wall, consider offline sources: galleries, exhibition catalogs, university archives |
| 3 | Bounded enumeration is a legitimate OSINT technique | When the answer space is small (a year within a known career span), systematic testing is valid | Combine research to narrow the search space, then enumerate when the space is small enough |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|---|---|---|---|
| Reconnaissance | Gather Victim Identity Information | Name, credentials, and affiliations | T1589 |
| Reconnaissance | Search Open Websites/Domains | Portfolio sites, social media, IMDB | T1593 |
| Reconnaissance | Search Open Technical Databases | Exhibition records, university archives | T1596 |
| Reconnaissance | Gather Victim Org Information | University affiliation, exhibition history | T1591 |

---

## Remediation and Containment

### Technical Fixes

1. Implement OPSEC awareness training for public-facing individuals (artists, executives, employees)
2. Audit public-facing profiles for information that could be used for social engineering
3. Review metadata in published files (images, documents, PDFs) for unintended information leakage
4. Configure privacy settings on social media platforms to limit publicly accessible data

### If You Find This in Your Environment

- Conduct an OSINT assessment of your organization's public exposure
- Enumerate all employee-linked social media, portfolio sites, and public profiles
- Identify information that could be used for spear-phishing or social engineering
- Implement a data minimization policy for public-facing content

### MITRE D3FEND

| Countermeasure | D3FEND ID | Application |
|---|---|---|
| User Account Permissions | D3-UAP | Control what personal information is publicly visible |
| Identifier Activity Analysis | D3-IAA | Monitor for reconnaissance against public profiles |

### NIST CSF 2.0

| Function | Category | Application |
|---|---|---|
| **Identify (ID)** | Asset Management | Inventory public-facing digital assets and profiles |
| **Protect (PR)** | Awareness and Training | Train employees on OPSEC and digital footprint management |
| **Detect (DE)** | Continuous Monitoring | Monitor for reconnaissance indicators against employee profiles |
| **Respond (RS)** | Communications | Coordinate with affected individuals when reconnaissance is detected |

### NIST SP 800-53 Rev. 5

| Control | Title | Application |
|---|---|---|
| AT-2 | Literacy Training and Awareness | OPSEC training on managing public digital footprint |
| PM-12 | Insider Threat Program | Monitor for adversarial reconnaissance using public employee data |

### CWE References

| CWE | Title | Relevance |
|---|---|---|
| CWE-200 | Exposure of Sensitive Information to an Unauthorized Actor | Personal information accessible through OSINT aggregation |

### APT Group Reference

**APT28 (Fancy Bear):** Extensively uses OSINT gathering on targets before spear-phishing campaigns, cross-referencing social media profiles, professional portfolios, and public records to craft convincing pretexts. The multi-platform research methodology in this challenge mirrors the reconnaissance phase of APT28's operational playbook.

---

Thanks guys!! (❍ᴥ❍ʋ)

---

Every digital footprint tells a story. If this OSINT deep dive showed you how much public data can reveal, share it and remind your crew to audit their own exposure.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
