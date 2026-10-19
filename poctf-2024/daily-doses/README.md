# Daily Doses

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2024 |
| **Category** | Digital Forensics |
| **Difficulty** | Hard |
| **Points** | 300 |
| **Flag** | `poctf{uwsp_1_4m_l363nd}` |
| **Status** | Solved |

---

## 1. Challenge Overview

A PCAP network capture that tests attention to detail. The challenge author admits to repeatedly missing evidence in similar real cases. The flag is hidden in a custom User-Agent header within HTTP traffic.

**Files:** `DF300-2.pcap` (network capture)

---

## 2. Initial PCAP Analysis

Opened the capture in **Wireshark** and examined HTTP GET requests. Found requests to `travel.changsha.cn`:

- `/images_2014/css.css`
- `/h/8701/20150716/2288227.html`

Attempted visiting these URLs and checking Wayback Machine, but found no relevant content (404 after 2017). This was a red herring.

---

## 3. String Extraction

Extracted strings from the PCAP for deeper analysis:

~~~bash
strings DF300-2.pcap > output.txt
~~~

---

## 4. Anomalous User-Agent Discovery

While reviewing extracted strings, found a suspicious User-Agent header:

~~~text
User-Agent: Mozilla/5.0 (706F6374667B757773705F315F346D5F6C3336336E647D) (KHTML, like Gecko) Chrome/43.0.2357.93 Mobile Safari/537.36
~~~

The string `706F6374667B757773705F315F346D5F6C3336336E647D` embedded in the parenthetical version comment is clearly hexadecimal data.

---

## 5. Hex Decoding

Decoded the hex string:

~~~python
bytes.fromhex("706F6374667B757773705F315F346D5F6C3336336E647D").decode()
~~~

Output: `poctf{uwsp_1_4m_l363nd}`

---

## Lessons Learned

| # | Lesson | Detail |
|---|--------|--------|
| 1 | User-Agent headers can carry covert data | Custom strings in standard headers evade casual inspection |
| 2 | Hex encoding in HTTP headers is a red flag | Non-standard characters in version strings warrant decoding |
| 3 | String extraction catches what Wireshark filters miss | Broad text search reveals patterns across all packets |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID | Context |
|---|---|---|---|
| Command and Control | Application Layer Protocol: Web Protocols | T1071.001 | Covert data embedded in HTTP User-Agent header |
| Exfiltration | Exfiltration Over C2 Channel | T1041 | Hex-encoded flag transmitted within standard HTTP traffic |
| Defense Evasion | Obfuscated Files or Information | T1027 | Data concealed using hex encoding in a legitimate-looking header |

> **CWE-200:** Exposure of Sensitive Information. Data exfiltrated through standard HTTP headers evades basic monitoring.

---

## Remediation and Containment

### Technical Fixes

1. Implement deep packet inspection (DPI) for HTTP headers
2. Flag User-Agent strings containing hex-encoded or Base64 data
3. Establish baselines for expected User-Agent patterns and alert on deviations
4. Deploy SSL/TLS inspection to analyze encrypted traffic headers

### MITRE D3FEND Countermeasures

- **D3-NTA (Network Traffic Analysis):** inspect HTTP headers for encoded data payloads
- **D3-PHDL (Protocol Header Data Loss Prevention):** detect anomalous data in standard protocol fields
- **D3-SFA (Session Flow Analysis):** correlate unusual header patterns across sessions

### NIST CSF 2.0

- **Detect (DE.CM):** monitor HTTP headers for anomalous content patterns
- **Detect (DE.AE):** establish User-Agent baselines and detect deviations
- **Respond (RS.MI):** block traffic with suspicious header content at proxy level

### NIST SP 800-53 Rev. 5

- **SC-7 (Boundary Protection):** inspect traffic at network boundaries for covert channels
- **SI-4 (Information System Monitoring):** monitor protocol headers for data exfiltration
- **AU-3 (Content of Audit Records):** log full HTTP headers for forensic analysis

### NIST SP 800-86

- **Network Forensics:** apply deep packet inspection to PCAP evidence
- **Protocol Analysis:** examine all header fields, not just payloads, for hidden data

### C2M2

- **SITUATION-3:** include HTTP header analysis in network monitoring
- **THREAT-3:** model covert channel exfiltration through protocol headers

---

Thanks guys!! (❍ᴥ❍ʋ)

---

I am legend for checking User-Agent strings. This challenge is a masterclass in hiding data where no one looks: right in the middle of a perfectly normal-looking browser header.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

> **Reference:** Adapted from [shivang1209-dot/CTF-Writeups](https://github.com/shivang1209-dot/CTF-Writeups). Original scripts credited to the author.
