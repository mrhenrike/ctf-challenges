# A Great Interior Desert

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2023 |
| **Category** | OSINT |
| **Difficulty** | Medium |
| **Points** | 200 |
| **Flag** | `poctf{dynamic}` |
| **Status** | Solved |

---

## 1. Challenge Overview

This OSINT challenge requires chaining multiple social media platforms to track down a hidden flag. Starting from a username hint, the solver must follow a trail across Mastodon, Twitter/X, and Instagram to locate a photo containing the flag.

The title "A Great Interior Desert" alludes to the Australian Outback, hinting at the geographic or thematic context behind the target persona.

---

## 2. Reconnaissance

The challenge provides a username or profile hint. The first step is to enumerate where this username exists across social media platforms.

Using **Sherlock** (or a similar OSINT username enumeration tool):

~~~bash
sherlock <target_username>
~~~

This reveals the target has accounts on multiple platforms, including a **Mastodon** instance.

---

## 3. Following the OSINT Chain

### Step 1: Mastodon Profile

The Mastodon profile contains a bio or post linking to a **Twitter/X** account. The link is not immediately obvious; it may be in a pinned post, bio field, or reply thread.

### Step 2: Twitter/X Trail

On the linked Twitter account, a reply or interaction points to **another Twitter account**. This second account's bio or pinned tweet contains a link to an **Instagram** profile.

### Step 3: Instagram Flag

The Instagram profile's first published photo contains the flag embedded in the image itself (visible text overlay, EXIF data, or caption).

---

## 4. Attack Path Summary

~~~text
Challenge hint (username)
    |
Sherlock enumeration -> Mastodon profile found
    |
Mastodon bio/post -> linked Twitter/X account
    |
Twitter reply chain -> second Twitter account
    |
Second account bio -> Instagram profile link
    |
Instagram first photo -> FLAG embedded in image
~~~

---

## 5. Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|--------------|
| 1 | Cross-platform username enumeration reveals hidden connections | Threat actors reuse handles across platforms; OSINT analysts use tools like Sherlock, Maigret, and WhatsMyName to map digital footprints | Always enumerate usernames across multiple platforms during reconnaissance |
| 2 | Social media breadcrumbs form traceable chains | People link accounts in bios, replies, and posts, creating paths that connect seemingly unrelated personas | Follow every link in a profile: bio URLs, pinned posts, reply threads, and tagged accounts |
| 3 | Images on social media can contain hidden data | Flags, credentials, and sensitive information can be embedded in photos via text overlays, steganography, or EXIF metadata | Inspect images thoroughly: visual content, metadata (exiftool), and steganographic layers |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Reconnaissance | TA0043 | Search Open Websites/Domains | T1593 |
| Reconnaissance | TA0043 | Gather Victim Identity Information: Social Media Accounts | T1589.001 |
| Reconnaissance | TA0043 | Search Victim-Owned Websites | T1594 |
| Resource Development | TA0042 | Establish Accounts: Social Media Accounts | T1585.001 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediation and Containment

### Technical Fixes

1. Avoid reusing the same username across platforms if compartmentalization is desired
2. Audit all social media profiles for unintended cross-links (bios, replies, followers)
3. Scrub EXIF metadata from photos before publishing (exiftool -all= image.jpg)
4. Use platform privacy settings to limit who can view followers, following lists, and tagged content

### MITRE D3FEND Countermeasures

- **D3-OUSM Online User Session Management** to control cross-platform identity exposure (counters T1593)
- **D3-IAA Identity and Access Auditing** to detect unauthorized enumeration of user accounts (counters T1589.001)

### NIST CSF 2.0

- **Protect (PR.AC-1):** Identity management controls limit exposure of linked accounts
- **Detect (DE.CM-7):** Monitoring for automated username enumeration attempts

### NIST SP 800-53 Rev. 5

- **IA-4: Identifier Management** (unique identifiers per context to prevent cross-platform correlation)
- **AC-22: Publicly Accessible Content** (review and sanitize content before public posting)

### CWE

- **CWE-200: Exposure of Sensitive Information to an Unauthorized Actor** (flag visible in public photo)
- **CWE-359: Exposure of Private Personal Information to an Unauthorized Actor** (cross-platform identity linkage)

---

## References

- Solve methodology based on [Enzo Cadoni's POCTF 2023 writeup](https://enzo-cadoni.fr/posts/poctf_2023/)
- OSINT approach confirmed by [yocchin's POCTF 2023 writeup](https://yocchin.hatenablog.com/entry/2024/01/23/082431)

---

Thanks guys!! (❍ᴥ❍ʋ)

---

The internet is a game of breadcrumbs. One username, three platforms, and a flag hidden in plain sight. In the real world, this is how investigators map threat actors, and how careless operators get burned.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
