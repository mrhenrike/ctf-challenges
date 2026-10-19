# A Record of Events

**Category:** Digital Forensics
**Challenge:** A Record of Events
**CTF:** Pointer Overflow CTF 2024
**Points:** DF 100
**Result:** Solved

**Flag:**

~~~text
poctf{uwsp_57r4n63r_1n_4_57r4n63_14nd}
~~~

---

## 1. Challenge Overview

A 480 MB disk image from a flash drive lost near a university campus ~20 years ago. The scenario involves recovering data from the drive to find a hidden flag among various embedded files.

**Files:** `DF100-1.001` (480 MB disk image)

---

## 2. Initial Disk Analysis

Ran `binwalk` to identify embedded file types:

~~~bash
binwalk DF100-1.001
~~~

Detected numerous MP3s, JPEGs, PNGs, PDFs, and ZIPs. Direct extraction with `binwalk -e` produced many nested disk images, making that approach impractical.

---

## 3. Forensic Analysis with Sleuthkit

Switched to Sleuthkit for proper filesystem analysis:

**Identify partitions:**

~~~bash
mmls DF100-1.001
~~~

**List files recursively:**

~~~bash
fls -r -o 32 DF100-1.001
~~~

**Extract individual files:**

~~~bash
icat -o 32 DF100-1.001 <inode> > extracted_file
~~~

---

## 4. Audio Analysis

Among the extracted files, `sotto-voce.mp3` stood out. Opened it in **Audacity** and played the audio.

The recording contained a voice dictating the flag character by character:

~~~text
poctf{uwsp_57r4n63r_1n_4_57r4n63_14nd}
~~~

---

## Lessons Learned

| # | Lesson | Detail |
|---|--------|--------|
| 1 | Sleuthkit outperforms binwalk for disk images | Proper partition-aware tools handle nested structures correctly |
| 2 | Audio files are valid forensic evidence carriers | Flags can be spoken, not just written |
| 3 | Partition offsets are critical for Sleuthkit | `mmls` output determines the correct offset for `fls` and `icat` |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID | Context |
|---|---|---|---|
| Collection | Data from Removable Media | T1025 | Evidence recovered from a USB flash drive image |
| Collection | Audio Capture | T1123 | Flag hidden in an audio recording on the drive |
| Defense Evasion | Obfuscated Files or Information: Steganography | T1027.003 | Sensitive data concealed in an audio file among normal files |

> **CWE-311:** Missing Encryption of Sensitive Data. The flag is spoken in plaintext audio with no encryption.

---

## Remediation and Containment

### Technical Fixes

1. Encrypt removable media with BitLocker/LUKS to protect data at rest
2. Implement DLP policies for USB devices to prevent data exfiltration
3. Use full-disk encryption on all portable storage
4. Monitor and log USB device connections to corporate systems

### MITRE D3FEND Countermeasures

- **D3-FE (File Encryption):** encrypt all data on removable media
- **D3-DRAM (Removable Media Analysis):** scan removable devices for hidden or anomalous files
- **D3-DUC (Device Usage Control):** restrict USB device access through endpoint policies

### NIST CSF 2.0

- **Protect (PR.DS):** encrypt data on removable media per organizational policy
- **Detect (DE.CM):** monitor for unauthorized removable media connections
- **Respond (RS.MI):** quarantine and forensically analyze recovered storage media

### NIST SP 800-53 Rev. 5

- **MP-5 (Media Transport):** protect removable media during transport with encryption
- **MP-6 (Media Sanitization):** sanitize media before disposal to prevent data recovery
- **SC-28 (Protection of Information at Rest):** encrypt all stored data on portable devices

### NIST SP 800-86

- **Evidence Collection:** create forensic copies of removable media before analysis
- **Evidence Examination:** use validated tools (Sleuthkit, Autopsy) for filesystem recovery

### C2M2

- **ASSET-3:** track all removable media as assets requiring encryption
- **SITUATION-2:** include removable media forensics in incident response procedures

---

Thanks guys!! (❍ᴥ❍ʋ)

---

A stranger in a strange land, hiding on a forgotten flash drive for 20 years. When binwalk chokes on nested disk images, Sleuthkit and a good pair of headphones save the day.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

> **Reference:** Adapted from [shivang1209-dot/CTF-Writeups](https://github.com/shivang1209-dot/CTF-Writeups). Original scripts credited to the author.
