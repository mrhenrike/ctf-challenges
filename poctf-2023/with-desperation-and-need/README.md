# With Desperation and Need

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2023 |
| **Challenge** | With Desperation and Need |
| **Category** | Cracking |
| **Difficulty** | Medium |
| **Points** | 200 |
| **Status** | Solved |

---

## 1. Challenge Overview

The challenge provides a VeraCrypt encrypted volume along with a clue that the password can be found in the rockyou.txt wordlist. A visual hint narrows the search to passwords starting with a specific prefix, making the brute-force attack feasible.

---

## 2. Analyzing the Clue

The challenge includes a hint (a post-it note or image) suggesting the password starts with `gUn`. This narrows the search space from millions of entries in rockyou.txt to a manageable subset.

Extracting matching candidates from the wordlist:

~~~bash
grep '^gUn' /usr/share/wordlists/rockyou.txt
~~~

This returns a small number of candidates, making a targeted brute-force practical.

---

## 3. Cracking the VeraCrypt Volume

Using the filtered wordlist to mount the volume:

~~~bash
grep '^gUn' /usr/share/wordlists/rockyou.txt > candidates.txt
~~~

Testing each candidate against the VeraCrypt volume:

~~~bash
veracrypt --text --non-interactive --password="<candidate>" volume.tc /mnt/veracrypt
~~~

Alternatively, using a scripted approach to iterate through candidates until the volume mounts successfully.

Once the correct password is found and the volume is mounted, the flag file is accessible inside.

---

## 4. Retrieving the Flag

After mounting with the correct password:

~~~bash
cat /mnt/veracrypt/flag.txt
~~~

**Output:**

~~~text
poctf{uwsp_d35p3r4710n_dr1v35_d15c0v3ry}
~~~

---

## 5. Attack Path Summary

~~~text
VeraCrypt volume + rockyou.txt hint
    |
Filter wordlist by prefix "gUn"
    |
Brute-force mount with candidates
    |
Mount volume, read flag
    |
FLAG: poctf{uwsp_d35p3r4710n_dr1v35_d15c0v3ry}
~~~

---

## 6. Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|--------------|
| 1 | Password hints drastically reduce search space | Social engineering or leaked hints about password patterns enable targeted attacks | Even partial password knowledge (prefix, length, charset) can collapse brute-force complexity |
| 2 | VeraCrypt volumes resist brute-force by design | Key derivation uses PBKDF2 with high iteration counts, making each attempt slow | The slow KDF is the defense; a weak password defeats it entirely |
| 3 | rockyou.txt remains a top credential source | The wordlist covers millions of real leaked passwords from the 2009 RockYou breach | Always test against common credential lists during assessments |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Credential Access | TA0006 | Brute Force: Password Cracking | T1110.002 |
| Credential Access | TA0006 | Unsecured Credentials: Credentials In Files | T1552.001 |
| Defense Evasion | TA0005 | Encrypted/Encoded File | T1027.013 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediation and Containment

### Technical Fixes

1. Use long, random passphrases for encrypted volumes instead of dictionary-derived passwords
2. Enable multi-factor decryption (keyfiles + password) for sensitive VeraCrypt volumes
3. Never store password hints alongside encrypted containers

### MITRE D3FEND Countermeasures

- **D3-SPP Strong Password Policy** to enforce passphrases that resist dictionary attacks (counters T1110.002)
- **D3-MFA Multi-factor Authentication** combining keyfiles with passwords for volume decryption (counters T1110.002)

### NIST CSF 2.0

- **Protect (PR.AC-1):** Identities and credentials are managed according to password complexity requirements
- **Protect (PR.DS-1):** Data-at-rest is protected with strong encryption and strong passphrases

### NIST SP 800-53 Rev. 5

- **IA-5: Authenticator Management** (enforce minimum passphrase complexity)
- **SC-28: Protection of Information at Rest** (use robust encryption with strong keys)

### CWE

- **CWE-521: Weak Password Requirements** (allowing dictionary-based passwords for encrypted volumes)
- **CWE-916: Use of Password Hash With Insufficient Computational Effort** (mitigated by VeraCrypt's KDF, but weak input defeats it)

---

## References

- Solve approach based on research from [Jihun Hwang's POCTF 2023 writeup](https://jihunhwang.github.io/UWSP_CTF_2023_writeup/)

---

Thanks guys!! (❍ᴥ❍ʋ)

---

When desperation drives you to crack an encrypted volume, remember that the weakest link is almost always the password. A good KDF buys time, but it cannot save a bad passphrase from a determined attacker with the right wordlist.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
