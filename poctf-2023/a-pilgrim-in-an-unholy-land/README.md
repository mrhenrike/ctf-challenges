# A Pilgrim in an Unholy Land

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2023 |
| **Category** | OSINT |
| **Difficulty** | Hard |
| **Points** | 300 |
| **Flag** | `poctf{dynamic}` |
| **Status** | Solved |

---

## 1. Challenge Overview

This is a multi-step OSINT challenge requiring geolocation, phone number extraction, map coordinate analysis, and street-level reconnaissance. Each step unlocks the next, forming a chain of five connected puzzles that ultimately reveal an archive password protecting the flag.

The title "A Pilgrim in an Unholy Land" suggests a journey through unfamiliar territory, which aptly describes the geographic investigation required.

---

## 2. Step 1: Airplane Geolocation (Oregon)

The challenge begins with an image of an airplane at a specific location. Using reverse image search and geolocation techniques:

1. Identify distinctive landmarks in the image (terrain, buildings, runway features)
2. Cross-reference with satellite imagery (Google Earth, Bing Maps)
3. The location is identified as a site in **Oregon, USA**
4. A phone number associated with the location is extracted from public records or signage visible in the imagery

---

## 3. Step 2: Map Coordinates

The phone number or data from Step 1 provides specific coordinates that must be entered into a mapping service. These coordinates point to a new location relevant to the next clue.

---

## 4. Step 3: Street-Level Investigation

Using Google Street View at the identified coordinates, additional clues are found. This step requires careful observation of the surroundings: signs, storefronts, vehicles, and other visual elements that contain encoded information.

---

## 5. Step 4: Brand Banner and Van Halen Lane

Street-view reconnaissance reveals a brand banner at a specific location. Following the clues leads to **Van Halen Lane in Stockton, California**. This geographic reference connects to the next step in the chain.

---

## 6. Step 5: The Van and the Archive

At the Van Halen Lane location, a van is visible with a phone number displayed on it. This phone number serves as the **password for an encrypted archive** containing the flag.

~~~text
Archive password: <phone number from van>
Extracted flag: poctf{uwsp_175_411_02_n07h1n9}
~~~

---

## 7. Attack Path Summary

~~~text
Step 1: Airplane image -> geolocation (Oregon) -> phone number
    |
Step 2: Phone number -> map coordinates
    |
Step 3: Street View investigation -> visual clues
    |
Step 4: Brand banner -> Van Halen Lane, Stockton, CA
    |
Step 5: Van phone number -> archive password -> FLAG
~~~

---

## 8. Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|--------------|
| 1 | Geolocation from images is a powerful OSINT technique | Intelligence agencies and OSINT researchers routinely geolocate images using terrain, vegetation, architecture, and shadow analysis | Always analyze environmental context in images: landmarks, signage, terrain features, and sun position |
| 2 | Phone numbers are high-value OSINT pivots | A single phone number can unlock business records, location data, ownership information, and connected identities | Treat phone numbers as first-class intelligence artifacts; search across directories, social media, and business registries |
| 3 | Street View is an OSINT goldmine | Google Street View captures signage, license plates, business names, and physical security posture at a point in time | Systematically survey Street View at identified coordinates; check historical imagery for changes over time |
| 4 | Multi-step OSINT requires methodical documentation | Each step depends on the previous; losing track means restarting the entire chain | Document every finding, coordinate, phone number, and URL as you go; chain analysis demands a clear audit trail |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Reconnaissance | TA0043 | Search Open Websites/Domains | T1593 |
| Reconnaissance | TA0043 | Gather Victim Org Information: Determine Physical Locations | T1591.001 |
| Reconnaissance | TA0043 | Gather Victim Org Information: Business Relationships | T1591.002 |
| Reconnaissance | TA0043 | Search Open Technical Databases | T1596 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediation and Containment

### Technical Fixes

1. Strip EXIF and geolocation metadata from images before publishing (exiftool -all= image.jpg)
2. Audit publicly visible phone numbers, addresses, and business details for unintended information leakage
3. Use geofencing alerts to detect when organizational locations appear in OSINT databases
4. Encrypt sensitive archives with strong passphrases, not guessable phone numbers

### MITRE D3FEND Countermeasures

- **D3-FCA File Content Analysis** to detect metadata in published images before distribution (counters T1591.001)
- **D3-DNSA DNS Analysis** to monitor domain reconnaissance targeting organizational assets (counters T1593)

### NIST CSF 2.0

- **Identify (ID.AM-5):** Inventory publicly accessible organizational information
- **Protect (PR.DS-5):** Data leak prevention covering image metadata and geolocation data

### NIST SP 800-53 Rev. 5

- **AC-22: Publicly Accessible Content** (review and authorize content before public release)
- **SC-28: Protection of Information at Rest** (encrypt archives with strong, non-guessable passwords)

### CWE

- **CWE-200: Exposure of Sensitive Information to an Unauthorized Actor** (phone numbers and locations in public imagery)
- **CWE-521: Weak Password Requirements** (archive password derived from publicly visible phone number)

---

## References

- Solve methodology based on [Enzo Cadoni's POCTF 2023 writeup](https://enzo-cadoni.fr/posts/poctf_2023/)

---

Thanks guys!! (❍ᴥ❍ʋ)

---

Five steps, two states, and a phone number on a van. OSINT is patience rewarded: every dead end is data, every pivot is progress. If you enjoyed this chain, imagine what a determined investigator can do with your public footprint.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
