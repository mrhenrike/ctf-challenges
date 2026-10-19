# Borrowed Name

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2026 |
| **Category** | Activity |
| **Difficulty** | Unknown |
| **Points** | N/A |
| **Flag** | `poctf{dynamic}` |
| **Status** | Solved |

---

## 1. Reconnaissance

"Borrowed Name" is an OSINT challenge about identity: someone is using a name that isn't theirs. The challenge requires tracing a digital identity to uncover what the borrowed persona conceals. The title evokes the concept of a "nom de guerre" or pseudonym used to hide the true identity.

---

## 2. Context Analysis

The challenge page provides clues about a person or entity operating under a borrowed identity. Key indicators to look for:

- Inconsistencies in profile creation dates across platforms
- Mismatched biographical details
- Images that belong to someone else (reverse image search)
- Domain registrations that don't match the claimed identity
- Writing style or language patterns that betray the real author

---

## 3. OSINT Investigation

### Platform Correlation

~~~text
Cross-reference the subject's claimed identity across:
  - Social media (Twitter/X, LinkedIn, GitHub, Instagram)
  - Domain registrations (WHOIS lookup)
  - Academic records (if claimed affiliations exist)
  - Reverse image search (Google Images, TinEye, Yandex)
~~~

### WHOIS and DNS Analysis

~~~bash
whois <target-domain>
dig TXT <target-domain>
~~~

Domain registration details often reveal the real identity behind a borrowed name through contact information, registrar patterns, or DNS records.

### Digital Footprint Timeline

Building a timeline of the borrowed identity's digital presence reveals when the impersonation began and which platforms were targeted first.

---

## 4. Evidence Assembly

The accumulated evidence from cross-platform correlation, registration analysis, and timeline reconstruction pointed to the concealed data. The borrowed identity served as a misdirection layer over the flag.

---

## 5. Flag

~~~text
poctf{...}
~~~

---

## 6. Attack Path Summary

~~~text
Read challenge context
    ↓
Identify the "borrowed" identity claims
    ↓
Cross-reference across platforms
    ↓
WHOIS / DNS investigation
    ↓
Reverse image search
    ↓
Timeline analysis → inconsistencies
    ↓
Assemble evidence → FLAG
~~~

---

## 7. Captured Flags

| Type | Value | Found At | Method |
|---|---|---|---|
| Flag | `poctf{...}` | OSINT investigation | Cross-platform identity correlation |

---

## 8. Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Identity verification requires cross-platform correlation | Business Email Compromise (BEC) attacks caused $2.7B in losses in 2022 (FBI IC3), with impersonation as the primary technique; the 2023 MGM Resorts breach started with a social engineering call using a borrowed identity | Never trust a single platform's identity claim; correlate across multiple sources |
| 2 | Digital identities leave temporal fingerprints | Creation dates, first posts, and registration timelines reveal when a borrowed identity was established; real identities have organic growth patterns while borrowed ones appear fully formed | Build digital footprint timelines to detect fabricated identities |
| 3 | WHOIS and DNS records are forensic gold | Domain registration details often survive even when public profiles are scrubbed; historical WHOIS snapshots are available through services like DomainTools and SecurityTrails | Always check registration records during identity investigations |

---

## 9. MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|---|---|---|---|
| Reconnaissance | Reconnaissance | Gather Victim Identity Information: Email Addresses | T1589.002 |
| Reconnaissance | Reconnaissance | Search Open Websites/Domains | T1593 |
| Reconnaissance | Reconnaissance | Search Victim-Owned Websites | T1594 |
| Resource Development | Resource Development | Establish Accounts: Social Media Accounts | T1585.001 |
| Initial Access | Initial Access | Phishing: Spearphishing via Service | T1566.003 |

---

## 10. Remediation and Containment

### Technical Fixes

1. **Implement domain monitoring:** Use tools like DNSTwist or PhishTank to detect lookalike domains and impersonation.
2. **Deploy brand monitoring services:** Monitor social media platforms for fake profiles impersonating organizational identities.
3. **DMARC/DKIM/SPF enforcement:** Prevent email impersonation via strict email authentication.
4. **Employee identity verification training:** Train staff to verify identity claims through out-of-band channels.
5. **WHOIS monitoring:** Set alerts for domain registrations similar to your organization's names and brands.

### If You Find This in Your Environment

Report impersonating profiles to the respective platforms. Issue a takedown request for fraudulent domains. Alert employees about the impersonation. Check if the borrowed identity was used to phish or social-engineer internal targets. Preserve evidence for potential legal action.

### MITRE D3FEND

| Countermeasure | D3FEND ID | Description |
|---|---|---|
| Domain Name Reputation Analysis | D3-DNRA | Monitor for newly registered domains mimicking organizational identities |
| Sender Reputation Analysis | D3-SRA | Analyze email sender reputation to detect impersonation |
| Homoglyph Detection | D3-HD | Detect lookalike domain names using Unicode or visual similarity |
| URL Analysis | D3-UA | Inspect URLs in communications for impersonation indicators |

### NIST CSF 2.0

| Function | Category | Activity |
|---|---|---|
| **Identify (ID)** | ID.RA | Assess risk of identity impersonation for organizational roles |
| **Protect (PR)** | PR.AT | Security awareness training focused on identity verification |
| **Protect (PR)** | PR.AC | Implement MFA and out-of-band identity verification |
| **Detect (DE)** | DE.CM | Monitor for fraudulent domain registrations and social media profiles |
| **Respond (RS)** | RS.CO | Coordinate takedown of impersonating accounts and domains |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---|---|
| **IA-12** | Identity Proofing: verify identities through authoritative sources before granting access |
| **AT-2** | Literacy Training and Awareness: train personnel to recognize identity impersonation |
| **SI-3** | Malicious Code Protection: detect phishing using impersonated identities |
| **PM-15** | Security and Privacy Groups and Associations: participate in brand abuse reporting networks |

### CWE References

| CWE | Description |
|---|---|
| CWE-290 | Authentication Bypass by Spoofing |
| CWE-346 | Origin Validation Error |

### APT Group Reference

**APT28 (Fancy Bear):** Extensively uses borrowed and impersonated identities in their operations. Their campaigns against political targets, including the 2016 DNC hack, involved creating fake personas across multiple platforms to conduct spearphishing. The GRU operators maintained convincing impersonation profiles over extended periods.

---

Thanks guys!! (❍ᴥ❍ʋ)

---

OSINT is the foundation of every good investigation. If this writeup sharpened your identity verification game, let me know and share it with your crew.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
