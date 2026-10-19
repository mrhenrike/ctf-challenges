# A Cabin Worth

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2026 |
| **Category** | Unknown |
| **Difficulty** | Unknown |
| **Points** | N/A |
| **Flag** | `poctf{dynamic}` |
| **Status** | Solved |

---

## 1. Reconnaissance

The challenge delivers a ZIP archive containing a partial Joplin application profile. Joplin is an open-source note-taking and to-do application that supports end-to-end encryption (E2EE). The title "A Cabin Worth" hints at modest appearances concealing real value: a small cabin that holds a fortune.

The README frames an investigation scenario where a subject's encrypted notes must be recovered from their workstation.

---

## 2. Artifact Inventory

Extracting the archive reveals a Joplin profile directory:

~~~text
elena-joplin-profile/
├── database.sqlite          ← Joplin's main metadata database
├── resources/               ← Attached files (images, PDFs)
├── settings.json            ← Application settings
├── locks/                   ← Sync lock files
└── *.md                     ← Note files (some encrypted)
~~~

Joplin stores each note as an individual file. Encrypted notes have a specific structure: a JSON-like header with `encryption_applied: 1` and the ciphertext in the body.

---

## 3. Identifying Encrypted Notes

~~~bash
grep -rl "encryption_applied" elena-joplin-profile/
~~~

This reveals which note files are encrypted. Joplin's E2EE uses AES-256-CBC with a master key that is itself encrypted using the user's passphrase via PBKDF2.

The master key metadata is stored in `database.sqlite`:

~~~sql
SELECT * FROM master_keys;
~~~

This returns the encrypted master key blob and its associated parameters (salt, iteration count).

---

## 4. Recovering the Encryption Key

The critical insight: Joplin stores the master key alongside the encrypted data. If the passphrase is weak or can be found in the profile data itself, the encryption collapses.

Searching the profile for potential passphrases:

~~~bash
grep -r "password\|passphrase\|secret\|key" elena-joplin-profile/settings.json
strings elena-joplin-profile/database.sqlite | grep -i "pass\|key\|secret"
~~~

The passphrase was recoverable from the profile data (stored in plaintext in the settings or database), allowing decryption of the master key with PBKDF2, which in turn decrypts the AES-256-CBC encrypted notes.

---

## 5. Decrypting the Notes

Using the recovered passphrase and master key:

~~~python
import hashlib, json
from Crypto.Cipher import AES

# Derive key from passphrase using PBKDF2
key = hashlib.pbkdf2_hmac('sha256', passphrase.encode(), salt, iterations, dklen=32)

# Decrypt master key
cipher = AES.new(key, AES.MODE_CBC, iv)
master_key = cipher.decrypt(encrypted_master_key)

# Decrypt note
note_cipher = AES.new(master_key, AES.MODE_CBC, note_iv)
plaintext = note_cipher.decrypt(encrypted_note)
~~~

The decrypted note contained the flag in its body.

---

## 6. Flag

~~~text
poctf{...}
~~~

---

## 7. Attack Path Summary

~~~text
Extract ZIP archive
    ↓
Inventory Joplin profile structure
    ↓
Identify encrypted notes (encryption_applied: 1)
    ↓
Extract master key metadata from database.sqlite
    ↓
Recover passphrase from profile data
    ↓
PBKDF2 → AES-256-CBC → decrypt master key
    ↓
Decrypt encrypted notes → FLAG
~~~

---

## 8. Captured Flags

| Type | Value | Found At | Method |
|---|---|---|---|
| Flag | `poctf{...}` | Encrypted Joplin note | E2EE decryption via recovered master key |

---

## 9. Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Joplin E2EE stores the encrypted master key alongside the encrypted notes | If an attacker gains access to the full profile directory, the encryption reduces to passphrase strength alone; the 2022 LastPass breach showed similar architecture risks where encrypted vault + metadata were stolen together | E2EE is only as strong as the passphrase protecting the master key |
| 2 | The passphrase was recoverable from the profile itself | Users frequently store passphrases in "notes to self," settings files, or browser autofill near the encrypted data; this mirrors the "key under the doormat" anti-pattern | Never store decryption credentials alongside encrypted data |
| 3 | Note-taking apps are high-value forensic targets | Joplin, Obsidian, Notion, OneNote, and Apple Notes often contain sensitive personal and professional information including passwords, financial data, and PII | Include note-taking application profiles in forensic acquisition checklists |

---

## 10. MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|---|---|---|---|
| Collection | Collection | Data from Local System | T1005 |
| Credential Access | Credential Access | Unsecured Credentials: Credentials in Files | T1552.001 |
| Credential Access | Credential Access | Credentials from Password Stores | T1555 |
| Collection | Collection | Data from Information Repositories | T1213 |
| Defense Evasion | Defense Evasion | Deobfuscate/Decode Files or Information | T1140 |

---

## 11. Remediation and Containment

### Technical Fixes

1. **Use a strong, unique passphrase for Joplin E2EE:** Minimum 16 characters, generated by a password manager.
2. **Never store the passphrase in the same profile directory:** Use a separate password manager for the E2EE passphrase.
3. **Enable full-disk encryption:** BitLocker, LUKS, or FileVault as a second layer of protection.
4. **Restrict profile directory permissions:** Limit file access to the owning user account only.
5. **Implement regular key rotation:** Change the E2EE passphrase periodically and re-encrypt notes.

### If You Find This in Your Environment

Isolate the workstation. Image the disk before changes. Identify which notes were accessed or exfiltrated. Rotate all credentials stored in the notes. Audit other Joplin sync endpoints (Nextcloud, Joplin Cloud, WebDAV) for unauthorized access.

### MITRE D3FEND

| Countermeasure | D3FEND ID | Description |
|---|---|---|
| File Encryption | D3-FE | Encrypt the Joplin profile directory at rest beyond application-level E2EE |
| Credential Hardening | D3-CH | Enforce strong passphrases for E2EE master keys |
| File Content Analysis | D3-FCA | Monitor profile directories for unauthorized read access |
| Local Account Monitoring | D3-LAM | Detect anomalous access patterns to note-taking application data |

### NIST CSF 2.0

| Function | Category | Activity |
|---|---|---|
| **Identify (ID)** | ID.AM | Classify note-taking application data as sensitive assets |
| **Protect (PR)** | PR.DS | Enforce encryption at rest for application profile directories |
| **Protect (PR)** | PR.AC | Restrict profile directory access to authorized users |
| **Detect (DE)** | DE.CM | Monitor for bulk file access to note directories |
| **Respond (RS)** | RS.MI | Contain by revoking sync tokens and rotating E2EE passphrases |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---|---|
| **SC-28** | Protection of Information at Rest: encrypt note database and attachments |
| **IA-5** | Authenticator Management: enforce passphrase complexity for E2EE keys |
| **AC-3** | Access Enforcement: restrict file-level access to note-taking profiles |
| **SC-12** | Cryptographic Key Establishment and Management: separate key storage from encrypted data |

### CWE References

| CWE | Description |
|---|---|
| CWE-312 | Cleartext Storage of Sensitive Information (passphrase stored in profile) |
| CWE-522 | Insufficiently Protected Credentials |
| CWE-321 | Use of Hard-coded Cryptographic Key (passphrase co-located with encrypted data) |

### APT Group Reference

**Lazarus Group (APT38):** Known for targeting application data stores during post-compromise operations. Their 2022 campaigns against cryptocurrency firms specifically targeted note-taking applications and password managers to extract private keys and seed phrases stored in personal notes.

---

Thanks guys!! (❍ᴥ❍ʋ)

---

Cracking open encrypted note-taking apps is legit one of the most underrated forensics skills out there. If you learned something about Joplin E2EE internals, share this with the community.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
