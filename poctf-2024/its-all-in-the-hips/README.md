# It's All in the Hips

**Category:** Digital Forensics
**Challenge:** It's All in the Hips
**CTF:** Pointer Overflow CTF 2024
**Points:** DF 300
**Result:** Solved

**Flag:**

~~~text
poctf{uwsp_7h3_574r5_my_d3571n4710n}
~~~

---

## 1. Challenge Overview

A disk image from a security camera that went on an "adventure" overnight. The .001 file contains a FAT16 partition with deleted and corrupted JPEG files. File carving, extraction, and header repair are required to recover the flag image.

**Files:** `DF300-1.001` (952 MB disk image)

---

## 2. Disk Image Analysis

Identified the file type and partition structure:

~~~bash
file DF300-1.001
# DOS/MBR boot sector; partition 1: ID=0xe, startsector 129, 1950591 sectors

fdisk -l DF300-1.001
# DF300-1.001p1  129  1950719  1950591  952.4M  e  W95 FAT16 (LBA)
~~~

---

## 3. Initial File Recovery with Foremost

~~~bash
foremost -i DF300-1.001 -o output
~~~

Extracted two JPEG images. Ran `stegseek` and `exiftool` on both, but found no hidden data.

---

## 4. Detailed Filesystem Analysis with SleuthKit

Used `mmls` and `fls` for proper partition-aware file listing:

~~~bash
mmls DF300-1.001
# Offset 129 sectors, Win95 FAT16

fls -o 129 DF300-1.001
~~~

Found multiple files including deleted entries (marked with `*`):

| Inode | Filename |
|-------|----------|
| 8 | this-could-be_us.jpg * |
| 11 | night_monkey.jpg * |
| 12 | _tsme.jpg * |
| 13 | _ad.jpg * |
| 15 | gib_money.jpg * |

---

## 5. File Extraction with icat

Extracted all files individually:

~~~bash
icat -o 129 DF300-1.001 8 > this-could-be_us.jpg
icat -o 129 DF300-1.001 11 > night_monkey.jpg
icat -o 129 DF300-1.001 12 > _tsme.jpg
icat -o 129 DF300-1.001 13 > _ad.jpg
icat -o 129 DF300-1.001 15 > gib_money.jpg
~~~

Two files were valid JPEGs. The remaining had corrupted headers.

---

## 6. Header Repair and Flag

Opened the corrupt images in a hex editor and repaired their JPEG headers (restoring `FF D8 FF E0` magic bytes). The repaired image [this-could-be_us.jpg](images/this-could-be_us.jpg) contained the flag:

~~~text
poctf{uwsp_7h3_574r5_my_d3571n4710n}
~~~

---

## Lessons Learned

| # | Lesson | Detail |
|---|--------|--------|
| 1 | Deleted files on FAT16 are recoverable | FAT does not overwrite data on deletion, only marks entries |
| 2 | Foremost misses what SleuthKit finds | Partition-aware tools recover more files from disk images |
| 3 | JPEG header repair is a core forensic skill | Corrupted headers prevent viewing but data may be intact |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID | Context |
|---|---|---|---|
| Defense Evasion | Indicator Removal: File Deletion | T1070.004 | Files deleted from the FAT16 filesystem |
| Defense Evasion | Obfuscated Files or Information | T1027 | JPEG headers corrupted to prevent automated recovery |
| Collection | Data from Removable Media | T1025 | Evidence recovered from a camera's storage device |

> **CWE-311:** Missing Encryption of Sensitive Data. Evidence stored unencrypted on removable media.
> **CWE-404:** Improper Resource Shutdown or Release. FAT16 deletion does not sanitize data.

---

## Remediation and Containment

### Technical Fixes

1. Use full-disk encryption on all removable storage devices
2. Implement secure deletion (overwrite) rather than simple FAT entry removal
3. Monitor camera storage devices for unauthorized access/modification
4. Use modern filesystems (ext4, NTFS) with journaling for better access control

### MITRE D3FEND Countermeasures

- **D3-FE (File Encryption):** encrypt all data on removable media
- **D3-DRAM (Removable Media Analysis):** forensically examine camera storage for tampering
- **D3-FIM (File Integrity Monitoring):** detect unauthorized file operations on storage devices

### NIST CSF 2.0

- **Protect (PR.DS):** encrypt removable media and enforce secure deletion policies
- **Detect (DE.CM):** monitor physical security cameras for unauthorized access
- **Respond (RS.MI):** forensically analyze tampered devices using validated tools

### NIST SP 800-53 Rev. 5

- **MP-6 (Media Sanitization):** use overwriting or degaussing for actual data destruction
- **MP-5 (Media Transport):** protect removable media during transport
- **PE-3 (Physical Access Control):** restrict physical access to security camera equipment

### NIST SP 800-86

- **Disk Forensics:** use write-blocking tools for disk image acquisition
- **File Recovery:** combine foremost, Sleuthkit, and hex editing for comprehensive recovery

### C2M2

- **ASSET-3:** track camera storage devices as security assets
- **SITUATION-2:** include physical device tampering in incident detection scope

---

Thanks guys!! (❍ᴥ❍ʋ)

---

The stars are my destination, and deleted files on FAT16 are my forensic playground. When cameras go on midnight adventures, SleuthKit and a hex editor bring the evidence back to light.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

> **Reference:** Adapted from [shivang1209-dot/CTF-Writeups](https://github.com/shivang1209-dot/CTF-Writeups). Original scripts credited to the author.
