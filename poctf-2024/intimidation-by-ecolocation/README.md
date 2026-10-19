# Intimidation by Ecolocation

| Property | Value |
|----------|-------|
| **CTF** | Pointer Overflow CTF 2024 (UWSP) |
| **Category** | OSINT |
| **Difficulty** | Hard |
| **Points** | 300 |
| **Status** | Solved |

## Challenge Overview

A multi-step OSINT challenge combining username reconnaissance, Mastodon social media investigation, geolocation, and Google Street View exploration. The flag is behind a Pastebin password derived from a road sign at a location identified through the investigation.

## Objective

Find a user across platforms using their username, locate a Pastebin URL and a map clue, geolocate the indicated position, find a road sign, and use its text as the password to access the flag.

## Methodology

### Step 1: Username Lookup

Used OSINT username search tools (Sherlock) to search for `0tYGJH2E` across platforms.

Found a profile on **Mastodon** (`mastodon.social`).

### Step 2: Examine the Mastodon Profile

The Mastodon page contained:
- A **map** with location markers
- A **video** containing a URL

The video revealed the Pastebin URL: `https://pastebin.com/0tYGJH2E`

Accessing the page showed a partial flag `poctf{uwsp_` and prompted for a password.

### Step 3: Analyze the Map and Image

The challenge image contained an arrow pointing to a specific sign location. Additional clues referenced:
- **OldBalt.Rd** (Old Baltimore Road)
- **North Maryland** area

### Step 4: Geolocate and Find the Sign

Using Google Maps, searched for **West Old Baltimore Road** in Maryland. Navigated Street View to the indicated location.

Found a road sign reading: **"HOV LANE ENDS"**

### Step 5: Unlock the Flag

Used the sign text formatted without spaces as the password: `HOVLANEENDS`

Entered on the Pastebin page to reveal the full flag.

```
Flag: poctf{uwsp_1_4m_7h3_0n3_wh0_kn0ck5}
```

## Lessons Learned

| # | Lesson | Details |
|---|--------|---------|
| 1 | Cross-platform enumeration | Tools like Sherlock efficiently identify accounts across hundreds of platforms |
| 2 | Mastodon as OSINT target | Federated social media platforms are increasingly used for CTF challenges |
| 3 | Multi-step OSINT chains | Each step (username, platform, URL, geolocation, sign) builds on the previous |
| 4 | Street View reconnaissance | Road signs are reliable landmarks that can be read remotely via mapping services |

## MITRE ATT&CK Mapping

| Tactic | Technique | ID | Details |
|--------|-----------|-----|---------|
| Reconnaissance | Search Open Websites/Domains | T1593 | Username enumeration across platforms |
| Reconnaissance | Gather Victim Identity Information | T1589 | Cross-referencing Mastodon profile with map data |
| Reconnaissance | Gather Victim Org Information: Physical Locations | T1591.001 | Geolocating the road sign via Street View |

## Remediation

### Technical Fixes

- Use unique usernames per platform to prevent cross-platform correlation
- Federated social media (Mastodon) profiles are publicly indexed and searchable
- Pastebin password-protected pastes are not encrypted; the password is just access control
- Road sign text is publicly observable and should not be used as secrets

### MITRE D3FEND

| Technique | ID | How it applies |
|-----------|-----|----------------|
| Identifier Activity Analysis | D3-IAA | Monitor for username enumeration attempts |
| Credential Hardening | D3-CH | Avoid passwords derived from publicly observable information |

### NIST CSF 2.0

| Function | Category | Relevance |
|----------|----------|-----------|
| Identify (ID) | Asset Management (ID.AM) | Track username exposure across platforms |
| Protect (PR) | Identity Management, Authentication and Access Control (PR.AA) | Prevent cross-platform tracking via unique identifiers |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---------|-------------|
| IA-4 | Identifier Management: use distinct identifiers across services |
| IA-5 | Authenticator Management: passwords from publicly observable sources are weak |

### CWE

| CWE ID | Name | Relevance |
|--------|------|-----------|
| CWE-521 | Weak Password Requirements | Road sign text as password |
| CWE-200 | Exposure of Sensitive Information to an Unauthorized Actor | Username reuse enabling cross-platform correlation |

## References

- [UWSP Pointer Overflow CTF 2024](https://pointeroverflowctf.com)
- [Sherlock: Username Search](https://github.com/sherlock-project/sherlock)
- Based on solve approach from [shivang1209-dot](https://github.com/shivang1209-dot/CTF-Writeup)

---

Thanks guys!! (❍ᴥ❍ʋ)

One username, many platforms. Cross-platform correlation is the bread and butter of OSINT, and username reuse makes it trivial.

[![Instagram](https://img.shields.io/badge/Instagram-%23E4405F.svg?style=for-the-badge&logo=Instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/linkedin-%230077B5.svg?style=for-the-badge&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/X-%23000000.svg?style=for-the-badge&logo=X&logoColor=white)](https://x.com/mrhenrike)
