# The Gentle Rocking of the Sun

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2023 |
| **Category** | Cracking |
| **Difficulty** | Easy |
| **Points** | 100 |
| **Flag** | `poctf{uwsp_c411f02n14_d234m1n9}` |
| **Status** | Solved (reference) |

---

## 1. Reconnaissance

The challenge provides a password-protected 7-zip archive (`crack2.7z`) and a hash:

~~~text
crack2 = 4bd939ed2e01ed1e8540ed137763d73cd8590323
~~~

The description uses the German phrase "das Passwort" (the password), hinting at a German-language wordlist.

---

## 2. Hash Analysis

Checking the hash length:

~~~bash
echo -n "4bd939ed2e01ed1e8540ed137763d73cd8590323" | wc -c
# Output: 40
~~~

40 characters = SHA-1 hash.

---

## 3. Cracking with German Wordlist

Since the hint points to German, we use a German dictionary (`german_de_DE.dic`) and hash each word with SHA-1 until we find a match:

~~~python
import hashlib

target = '4bd939ed2e01ed1e8540ed137763d73cd8590323'

with open('german_de_DE.dic', 'r', errors='ignore') as f:
    for word in f:
        word = word.strip()
        if hashlib.sha1(word.encode()).hexdigest() == target:
            print(f"Password found: {word}")
            break
~~~

The cracked password unlocks the archive, which contains a file structure with directory names that, when concatenated, form the flag.

---

## 4. Flag Extraction

After extraction, the directory names concatenate to form:

~~~text
poctf{uwsp_c411f02n14_d234m1n9}
~~~

Leetspeak for "california dreaming."

---

## 5. Attack Path Summary

~~~text
crack2.7z (password-protected)
    |
Hash: 4bd939ed... (SHA-1, 40 chars)
    |
"das Passwort" hint -> German wordlist
    |
SHA-1 dictionary attack -> password found
    |
Extract archive -> directory names -> FLAG
~~~

---

## 6. Lessons Learned

| # | Finding | Key Takeaway |
|---|---|---|
| 1 | Hash length determines algorithm: 40 chars = SHA-1 | Always check length before choosing a cracking approach |
| 2 | Language hints in challenge text guide wordlist selection | "das Passwort" directly pointed to a German dictionary |
| 3 | Flags can be embedded in file/directory names | Don't just look at file contents; the filesystem structure itself can be the message |

---

## 7. MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID |
|--------|-----------|--------|
| Credential Access | Password Cracking | T1110.002 |
| Resource Development | Obtain Capabilities: Tool | T1588.002 |
| Collection | Data from Local System | T1005 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## 8. Remediation and Containment

### Technical Fixes

1. Enforce strong password policies: minimum 16 characters, mixed character classes, no dictionary words in any language
2. Use bcrypt, scrypt or Argon2id instead of SHA-1 for password hashing; SHA-1 is considered broken for cryptographic purposes (NIST deprecated since 2011)
3. Add salt to all password hashes to defeat precomputed rainbow table attacks
4. Implement account lockout or progressive delays after repeated failed authentication attempts

### MITRE D3FEND Countermeasures

- **D3-SPP (Strong Password Policy):** enforce complexity requirements that resist dictionary attacks
- **D3-MFA (Multi-factor Authentication):** add a second factor so cracked passwords alone are insufficient
- **D3-ANCI (Authentication Cache Invalidation):** rotate credentials periodically

### NIST CSF 2.0

- **Protect (PR.AA):** enforce identity management and access control with strong credential policies
- **Detect (DE.CM):** monitor for brute-force and dictionary attack patterns against authentication services

### NIST SP 800-53 Rev. 5

- **IA-5 (Authenticator Management):** enforce minimum password strength and prohibit weak hashing algorithms
- **IA-11 (Re-authentication):** require re-authentication for sensitive operations
- **SI-7 (Software, Firmware, and Information Integrity):** validate integrity of stored credential data

### C2M2

- **Domain:** ACCESS
- **Practice:** Establish and Maintain Identities and Credentials
- **Target MIL:** MIL-2

---

Thanks guys!! (❍ᴥ❍ʋ)

---

Cracking challenges always remind you to never underestimate a good dictionary. If this SHA-1 plus German wordlist combo was a learning moment for you, share it with your crew and let's connect!

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
