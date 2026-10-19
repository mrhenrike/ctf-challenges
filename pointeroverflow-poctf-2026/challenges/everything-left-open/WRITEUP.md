# Everything Left Open

**Category:** Forensics
**Challenge:** Everything Left Open
**Points:** FOR 100 (Wave 1)
**Result:** Solved

**Flag:**

~~~text
POCTF{109.1391.67TQSOQ32U4S47B5.QFLAUNPCD4BBC75UPCRBZ75FST}
~~~

---

## 1. Reconnaissance

The challenge provides a ZIP archive (`left-open-profile.zip`, SHA-256: `0f6eac9130a30e35460816eb051d9a9c0751b1e9a811f8e8754dd8fa8db49502`) containing a partial Firefox browser profile from a laptop found unlocked at a hotel.

The README describes the scenario:

> DOCKET MARCHETTI / 2026-14
> SUBJECT: E. Marchetti disappearance investigation
> ANALYST: K. Vance (retained by R. Marchetti)
> Firefox profile pulled from Elena's office workstation at Hollis University, found unlocked with an SPR provenance page in the last active tab.
> Session appears to have been interrupted mid-review.
> **Find what she was about to submit.**

The key phrase is "data entered mid-form." The flag is in form data from an active session.

---

## 2. Artifact Inventory

The ZIP extracts to:

~~~text
k-vance-profile/
├── places.sqlite            ← browsing history & bookmarks
├── logins.json              ← saved passwords (base64 "encrypted")
├── formhistory.sqlite       ← autocomplete form field data
├── prefs.js                 ← Firefox preferences
└── sessionstore-backups/
    └── recovery.jsonlz4     ← active session state with form data
~~~

The critical file is `recovery.jsonlz4`, which stores the active browser session, including any data entered into forms but not yet submitted.

---

## 3. Credential Extraction (logins.json)

The passwords are stored as base64, not actually encrypted (no `key4.db` / NSS encryption):

~~~bash
echo "ZS5tYXJjaGV0dGlAaG9sbGlzLmVkdQ==" | base64 -d
# e.marchetti@hollis.edu

echo "TW5EYXlXM2RuZXNkQHk3" | base64 -d
# MnDayW3dnesd@y7

echo "YW5vbi1hbmFseXN0" | base64 -d
# anon-analyst

echo "aHVudGVyMg==" | base64 -d
# hunter2
~~~

| Site | Username | Password |
|---|---|---|
| hollis.edu | e.marchetti@hollis.edu | MnDayW3dnesd@y7 |
| pastebin.com | anon-analyst | hunter2 |

These credentials are relevant for the broader investigation narrative ("just in case") but not needed for the flag.

---

## 4. Browsing History (places.sqlite)

~~~sql
SELECT datetime(last_visit_date/1000000, 'unixepoch'), url, title
FROM moz_places WHERE last_visit_date IS NOT NULL
ORDER BY last_visit_date DESC;
~~~

| Time (UTC) | URL | Title |
|---|---|---|
| 2026-06-27 03:21 | catalog.spr.org.uk/apparatus/provenance/lssf | LSSF Apparatus, Provenance & Loan History |
| 2026-06-27 02:21 | catalog.spr.org.uk/ | Society for Psychical Research, Catalogue |
| 2026-06-27 01:21 | catalog.spr.org.uk/lssf/session-records | LSSF Session Records (partial) |
| 2026-06-27 00:21 | hollis.edu/special-collections/lssf-papers | Hollis Special Collections, LSSF Papers |
| 2026-06-26 23:21 | scholar.google.com/... | marcus yee dissertation liminal |
| 2026-06-26 22:21 | en.wikipedia.org/.../Society_for_Psychical_Research | SPR Wikipedia |

The last active tab was the SPR provenance page, consistent with the README.

---

## 5. Form History (formhistory.sqlite)

~~~sql
SELECT * FROM moz_formhistory;
~~~

| Field | Value |
|---|---|
| search | eighth session lssf redacted |
| email | e.marchetti@hollis.edu |
| search | halberd office hours wednesday |

Autocomplete data from past form submissions. Not the flag itself.

---

## 6. Session Store Extraction (recovery.jsonlz4)

This is the critical file. Firefox's `recovery.jsonlz4` stores the live session state, including form fields that were filled but NOT submitted.

### Format

The file starts with an 8-byte magic header `mozLz40\x00`, followed by an LZ4-compressed JSON payload.

### Extraction

~~~python
import lz4.block, json

with open("recovery.jsonlz4", "rb") as f:
    f.read(8)  # skip magic header
    data = json.loads(lz4.block.decompress(f.read()))
~~~

### Session Content

The session contains one window with one tab, open to `https://catalog.spr.org.uk/apparatus/provenance/lssf`.

The tab has **form data** with fields filled mid-submission:

~~~json
{
  "formdata": {
    "id": {
      "workstation": "hollis-office-desktop-elena",
      "analyst-name": "K. Vance",
      "artifact-flag": "POCTF{109.1391.67TQSOQ32U4S47B5.QFLAUNPCD4BBC75UPCRBZ75FST}",
      "case-notes": "Subject: E. Marchetti disappearance. Chain of custody initiated 2026-06-29."
    }
  }
}
~~~

The flag is in the `artifact-flag` field, entered into the form but never submitted ("session appears to have been interrupted mid-review").

---

## 7. Flag Discovery

~~~text
POCTF{109.1391.67TQSOQ32U4S47B5.QFLAUNPCD4BBC75UPCRBZ75FST}
~~~

Submitted and confirmed correct.

---

## 8. Attack Path Summary

~~~text
Extract ZIP
    ↓
Inventory: 5 Firefox profile files
    ↓
logins.json → base64 decode → credentials (context, not flag)
    ↓
places.sqlite → browsing history → SPR provenance page
    ↓
formhistory.sqlite → autocomplete entries (not flag)
    ↓
recovery.jsonlz4 → mozLz4 decompress → session JSON
    ↓
Tab 0 formdata → artifact-flag field → FLAG
~~~

---

## 9. Lessons Learned

| # | Finding | Key Takeaway |
|---|---|---|
| 1 | The flag was in `recovery.jsonlz4`, not in browsing history or form autocomplete | Firefox session store preserves unsaved form data, a goldmine for forensics |
| 2 | `logins.json` used base64, not real NSS encryption | Without `key4.db`, passwords are trivially recoverable |
| 3 | `formhistory.sqlite` stores autocomplete, not active session data | Don't confuse autocomplete history with live form state |
| 4 | mozLz4 format needs the 8-byte header stripped before LZ4 decompression | Standard LZ4 tools fail without removing the `mozLz40\x00` prefix |

---

## Reproduction Checklist

- [x] Download and verify `left-open-profile.zip` (SHA-256 match)
- [x] Extract ZIP contents
- [x] Decode credentials from `logins.json` (base64)
- [x] Query `places.sqlite` for browsing history
- [x] Query `formhistory.sqlite` for autocomplete data
- [x] Decompress `recovery.jsonlz4` (mozLz4 → JSON)
- [x] Extract form data from active tab
- [x] Recover flag from `artifact-flag` field
- [x] Submit flag

---

## MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID | Relevance |
|---|---|---|---|
| Collection | Data from Local System | T1005 | Extracting credentials and session data from Firefox profile artifacts |
| Credential Access | Credentials from Password Stores: Credentials from Web Browsers | T1555.003 | Decoding passwords stored in logins.json (base64, no NSS encryption) |
| Discovery | File and Directory Discovery | T1083 | Inventorying Firefox profile files to locate session store |
| Defense Evasion | Indicator Removal: File Deletion | T1070.004 | Scenario involves recovering data from an interrupted session before cleanup |
| Collection | Automated Collection | T1119 | Systematic extraction of browsing history, form data, and session state |

---

## Remediation and Containment

### Technical Fixes

1. Enable NSS master password encryption for Firefox saved credentials (prevents trivial base64 decode of logins.json)
2. Configure full-disk encryption (BitLocker, LUKS, FileVault) to protect profile data at rest
3. Set Firefox to clear session data on close (`privacy.sanitize.sanitizeOnShutdown = true`)
4. Enforce automatic screen lock after idle timeout to prevent unlocked-workstation scenarios

### MITRE D3FEND Countermeasures

- **D3-DENCR Disk Encryption:** protect browser profile files from offline extraction
- **D3-AAER Authentication Event Recording:** log workstation lock/unlock events to detect unauthorized access
- **D3-FCA File Content Analysis:** scan exported profiles for sensitive data before sharing

### NIST CSF 2.0

- **Protect (PR.DS):** encrypt data at rest, including browser profile directories
- **Protect (PR.AC):** enforce screen lock timeouts and workstation access controls
- **Detect (DE.AE):** alert on unusual file access patterns against browser profile paths
- **Respond (RS.MI):** contain incident by isolating the workstation and rotating exposed credentials

### NIST SP 800-53 Rev. 5

- **AC-11 Device Lock:** enforce automatic session lock after inactivity
- **SC-28 Protection of Information at Rest:** require encryption for locally stored credentials
- **IA-5 Authenticator Management:** enforce master password on browser credential stores
- **AU-12 Audit Record Generation:** log access to sensitive profile directories

### C2M2

- **Domain:** ACCESS (Access Management)
- **Practice:** Manage identities and credentials with appropriate lifecycle controls
- **Target MIL:** MIL-2 (documented policies for credential storage and workstation lock)

---

Thanks guys!! (❍ᴥ❍ʋ)

---

Enjoyed the browser forensics ride? If you picked up something new about session recovery, spread the word and tag me. Let's grow the community together.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
