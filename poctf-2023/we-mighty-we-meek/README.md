# We Mighty, We Meek

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2023 |
| **Category** | Cracking |
| **Difficulty** | Hard |
| **Points** | 300 |
| **Flag** | `poctf{uwsp_m19h7y_m33k_cr4ck3d_w1d3_0p3n}` |
| **Status** | Solved |

---

## 1. Challenge Overview

The challenge provides a password-protected Microsoft Excel file (`crack1.excel`). The goal is to crack the password protecting the document and extract the flag from within.

---

## 2. Extracting the Hash

First, extract the password hash from the Excel file using `office2john`, a tool from the John the Ripper suite designed for Microsoft Office documents:

~~~bash
office2john crack1.excel > crack1.hash
~~~

The extracted hash uses the Office 2013 format with PBKDF2 key derivation:

~~~text
crack1.excel:$office$*2013*100000*256*16*912a7246e4f68e941d6c46fc6e08a483*...
~~~

The hash format tells us:
- **Office 2013** encryption
- **100,000 PBKDF2 iterations** (computationally expensive per attempt)
- **256-bit AES** encryption

---

## 3. Cracking with John the Ripper

Using John the Ripper with the rockyou.txt wordlist:

~~~bash
john --wordlist=/usr/share/wordlists/rockyou.txt crack1.hash
~~~

Due to the high iteration count (100,000 rounds), each candidate takes significant time. On a modern CPU, this can process roughly 10-50 passwords per second.

After running through a portion of rockyou.txt, John finds the password. Checking the result:

~~~bash
john --show crack1.hash
~~~

---

## 4. Extracting the Flag

Open the Excel file with the recovered password. The flag is stored within one of the spreadsheet cells:

~~~text
poctf{uwsp_m19h7y_m33k_cr4ck3d_w1d3_0p3n}
~~~

---

## 5. Attack Path Summary

~~~text
crack1.excel (password-protected)
    |
office2john -> extract hash
    |
john --wordlist=rockyou.txt
    |
Recover password, open file
    |
FLAG: poctf{uwsp_m19h7y_m33k_cr4ck3d_w1d3_0p3n}
~~~

---

## 6. Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|--------------|
| 1 | Office 2013+ uses strong key derivation | 100,000 PBKDF2 iterations make brute-force slow but not impossible with weak passwords | Strong KDF parameters only help if paired with strong passwords |
| 2 | office2john bridges document security and password cracking | Many forensic and pentest scenarios involve cracking protected Office documents | Keep specialized hash extraction tools in your toolkit: office2john, pdf2john, zip2john |
| 3 | Dictionary attacks remain effective against human-chosen passwords | Even with expensive hash functions, common passwords fall quickly | Password managers and randomly generated passphrases are the only reliable defense |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Credential Access | TA0006 | Brute Force: Password Cracking | T1110.002 |
| Collection | TA0009 | Data from Local System | T1005 |
| Defense Evasion | TA0005 | Encrypted/Encoded File | T1027.013 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediation and Containment

### Technical Fixes

1. Use passphrases of 16+ characters with mixed character types for document encryption
2. Consider removing document passwords in favor of file-level encryption (BitLocker, VeraCrypt) where feasible
3. Audit protected documents periodically to ensure they do not contain weak passwords

### MITRE D3FEND Countermeasures

- **D3-SPP Strong Password Policy** to prevent weak passwords on protected documents (counters T1110.002)
- **D3-FE File Encryption** using enterprise key management instead of document-level passwords (counters T1005)

### NIST CSF 2.0

- **Protect (PR.DS-1):** Data-at-rest protection through strong encryption and passphrases
- **Protect (PR.AC-1):** Credential management enforces complexity requirements

### NIST SP 800-53 Rev. 5

- **IA-5: Authenticator Management** (enforce password strength for document protection)
- **SC-28: Protection of Information at Rest** (evaluate document encryption adequacy)

### CWE

- **CWE-521: Weak Password Requirements** (document protected with a dictionary-crackable password)
- **CWE-916: Use of Password Hash With Insufficient Computational Effort** (mitigated by Office 2013 KDF, but still vulnerable to dictionary attacks)

---

## References

- Hash extracted from [sandwithcheese's UWSP POCTF artifacts](https://github.com/sandwithcheese)
- Solve approach based on research from [Joooook's POCTF writeup](https://joooook.github.io/2024/02/05/UWSP%20Pointer%20Overflow%20CTF/)

---

Thanks guys!! (❍ᴥ❍ʋ)

---

A mighty document can fall to a meek password. Office 2013's 100k iterations of PBKDF2 put up a decent fight, but rockyou.txt still wins when the password was chosen by a human who thought "nobody will guess this."

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
