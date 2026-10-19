# I'm a Stranger Here Myself

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2024 |
| **Category** | Digital Forensics |
| **Difficulty** | Hard |
| **Points** | 300 |
| **Flag** | `poctf{uwsp_f34r_15_7h3_m1nd_k1113r}` |
| **Status** | Solved |

---

## 1. Challenge Overview

A PCAP file inspired by a real criminal investigation involving steganographic evidence. The challenge reproduces a scenario with six conspiracy members, where evidence is transmitted via FTP in two parts that must be reassembled into a JPEG image.

**Note:** The flag uses '1' for both 'i' and 'l' characters.

**Files:** `DF300-3.pcap` (network capture)

---

## 2. FTP Session Analysis

Opened the PCAP in Wireshark and identified FTP data transfers:

- **FTP credentials:** `user` / `password`
- **Working directory:** `/home/user`
- **Two file transfers detected:**
  - **Part 1** (TCP stream eq 2, Packet 218): JPEG body data (missing header)
  - **Part 2** (TCP stream eq 4, Packet 267): JPEG header fragment

---

## 3. File Reconstruction

The flag image was split across two FTP transfers in reverse order:

1. Extracted Part 2 (the header) as raw bytes from Wireshark
2. Extracted Part 1 (the body) as raw bytes
3. Concatenated: header (Part 2) + body (Part 1)

---

## 4. JPEG Header Repair

The first 4 bytes of the reconstructed file were `de ad be ef` (a placeholder). Replaced them with the JPEG magic number in a hex editor:

~~~text
de ad be ef -> ff d8 ff e0
~~~

Saved as [recovered_image.jpg](images/recovered_image.jpg).

---

## 5. Image Repair and Flag

The initial reconstruction had minor corruption. Used an online JPEG repair tool to fix remaining inconsistencies. The [repaired image](images/repaired_image.jpg) revealed the flag:

~~~text
poctf{uwsp_f34r_15_7h3_m1nd_k1113r}
~~~

---

## Lessons Learned

| # | Lesson | Detail |
|---|--------|--------|
| 1 | Split file transfers require reassembly | FTP sessions can transmit file fragments in separate streams |
| 2 | Magic number manipulation is anti-forensic | Replacing headers prevents automated file type detection |
| 3 | JPEG repair tools recover from minor corruption | Online and offline tools can fix header and structure issues |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID | Context |
|---|---|---|---|
| Exfiltration | Exfiltration Over Alternative Protocol | T1048 | Data exfiltrated via FTP in split fragments |
| Defense Evasion | Obfuscated Files or Information: Steganography | T1027.003 | Flag hidden in a reconstructed image |
| Defense Evasion | Indicator Removal: File Deletion | T1070.004 | File headers modified to prevent automated detection |

> **CWE-311:** Missing Encryption of Sensitive Data. Conspiracy evidence transmitted via unencrypted FTP.
> **CWE-319:** Cleartext Transmission of Sensitive Information. FTP transmits data without encryption.

---

## Remediation and Containment

### Technical Fixes

1. Monitor FTP sessions for split file transfers (multiple STOR operations to related filenames)
2. Implement network DLP capable of reconstructing fragmented transfers
3. Block or monitor unencrypted FTP, enforce SFTP/FTPS
4. Deploy file magic number validation on network egress

### MITRE D3FEND Countermeasures

- **D3-NTA (Network Traffic Analysis):** reassemble and inspect FTP data transfers
- **D3-FCOA (File Content Analysis):** validate file headers against expected magic numbers
- **D3-EAL (Encrypted Tunnels):** enforce encrypted file transfer protocols

### NIST CSF 2.0

- **Protect (PR.DS):** enforce encrypted protocols for all file transfers
- **Detect (DE.CM):** reconstruct and inspect fragmented network file transfers
- **Respond (RS.MI):** investigate FTP sessions with anomalous transfer patterns

### NIST SP 800-53 Rev. 5

- **SC-8 (Transmission Confidentiality and Integrity):** require encryption for file transfers
- **SC-7 (Boundary Protection):** inspect and reconstruct files at network boundaries
- **AU-3 (Content of Audit Records):** log complete FTP sessions for forensic reconstruction

### NIST SP 800-86

- **Network Forensics:** reconstruct file transfers from PCAP evidence
- **File Reconstruction:** reassemble fragmented files using stream ordering and header repair

### C2M2

- **SITUATION-3:** monitor for split/fragmented file exfiltration patterns
- **THREAT-3:** model multi-part file transfer as an exfiltration technique

---

Thanks guys!! (❍ᴥ❍ʋ)

---

Fear is the mind-killer, and so is split-file FTP exfiltration for anyone who is not watching their network captures closely. Reassembling fragments and fixing magic bytes is digital forensics at its most hands-on.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

> **Reference:** Adapted from [shivang1209-dot/CTF-Writeups](https://github.com/shivang1209-dot/CTF-Writeups). Original scripts credited to the author.
