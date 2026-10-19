# All is Green and Comfort

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2023 |
| **Category** | OSINT |
| **Difficulty** | Easy |
| **Points** | 100 |
| **Flag** | `poctf{uwsp_7h3_2357_15_45h}` |
| **Status** | Solved |

---

## 1. Challenge Overview

The challenge requires finding a leaked secret by examining archived versions of a web page using the Wayback Machine. The flag was present in a previous version of the target page but has since been removed.

---

## 2. Identifying the Target

The challenge description provides a URL or hints toward a specific web page. The current live version of the page does not contain the flag, implying the secret was exposed at some point in the past and later scrubbed.

---

## 3. Using the Wayback Machine

Searching the target URL on the Wayback Machine (web.archive.org):

1. Navigate to `https://web.archive.org/`
2. Enter the target URL
3. Browse through archived snapshots, focusing on earlier dates
4. Compare current and historical versions to find the removed content

In one of the earlier snapshots, the flag is visible in the page source, embedded in a comment or a hidden element:

~~~text
poctf{uwsp_7h3_2357_15_45h}
~~~

---

## 4. Attack Path Summary

~~~text
Challenge hint -> target URL
    |
Wayback Machine archive search
    |
Browse historical snapshots
    |
Find flag in archived page version
    |
FLAG: poctf{uwsp_7h3_2357_15_45h}
~~~

---

## 5. Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|--------------|
| 1 | Deleted content persists in web archives | Secrets, credentials, and PII removed from live sites remain in Wayback Machine snapshots | Always check web archives during OSINT reconnaissance for historical exposures |
| 2 | Removing content from production is not enough | Cached versions exist in Google Cache, Wayback Machine, CDN caches, and browser caches | Credential rotation must follow any accidental exposure, regardless of how quickly it was removed |
| 3 | Web archiving is a double-edged sword | Archives preserve knowledge but also preserve mistakes | Implement robots.txt and request archive removal for sensitive pages (though compliance is voluntary) |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Reconnaissance | TA0043 | Search Open Technical Databases | T1596 |
| Reconnaissance | TA0043 | Search Open Websites/Domains | T1593 |
| Reconnaissance | TA0043 | Gather Victim Org Information: Determine Physical Locations | T1591.001 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediation and Containment

### Technical Fixes

1. Rotate any credentials or secrets immediately upon discovering accidental exposure
2. Request removal from web archives through the Wayback Machine's exclusion process
3. Implement pre-commit hooks and CI/CD scanning (e.g., gitleaks, truffleHog) to prevent secret publication
4. Use `.robots.txt` Disallow directives to discourage archiving of sensitive paths

### MITRE D3FEND Countermeasures

- **D3-SRA Source Code Repository Analysis** to detect leaked secrets before they reach production (counters T1596)
- **D3-DNSA DNS Analysis** to monitor for domain reconnaissance activity (counters T1593)

### NIST CSF 2.0

- **Protect (PR.DS-5):** Data leak prevention measures catch secrets before publication
- **Detect (DE.CM-8):** Vulnerability scans identify exposed secrets on public-facing assets

### NIST SP 800-53 Rev. 5

- **IA-5: Authenticator Management** (rotate compromised credentials immediately)
- **SC-28: Protection of Information at Rest** (prevent secrets from being stored in public web content)

### CWE

- **CWE-200: Exposure of Sensitive Information to an Unauthorized Actor** (secret visible in archived web page)
- **CWE-312: Cleartext Storage of Sensitive Information** (flag/secret stored in plaintext in HTML)

---

## References

- Flag value from [sandwithcheese's UWSP POCTF artifacts](https://github.com/sandwithcheese)
- Solve approach based on research from [Jihun Hwang's POCTF 2023 writeup](https://jihunhwang.github.io/UWSP_CTF_2023_writeup/)

---

Thanks guys!! (❍ᴥ❍ʋ)

---

The internet never forgets, even when you delete. The Wayback Machine is both a historian's treasure and a developer's nightmare, proof that "I removed it" is never the same as "it's gone."

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
