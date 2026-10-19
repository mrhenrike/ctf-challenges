# A Pale, Violet Light

**Category:** Crypto
**Challenge:** A Pale, Violet Light
**CTF:** Pointer Overflow CTF 2023
**Result:** Solved

**Flag:**

~~~text
poctf{uwsp_533k_4nd_y3_5h411_f1nd}
~~~

---

## 1. Challenge Overview

We are given RSA parameters and a ciphertext, and need to decrypt the message. The values provided are:

- `e = 5039`
- `N = 34034827`
- `C = 933969 15848125 24252056 5387227 5511551 10881790 3267174 14500698 28242580 933969 32093017 18035208 2594090 2594090 9122397 21290815 15930721 4502231 5173234 21290815 23241728 2594090 21290815 18035208 10891227 15930721 202434 202434 21290815 5511551 202434 4502231 5173234 25243036`

The ciphertext `C` is a space-separated list of integers, each representing one encrypted character.

---

## 2. Factoring N

Since `N = 34034827` is relatively small, it can be factored using tools like [FactorDB](http://factordb.com/) or `sympy`:

~~~text
N = 5807 × 5861
p = 5807
q = 5861
~~~

---

## 3. Computing the Private Key

With `p` and `q` known, we compute Euler's totient and the private exponent:

~~~text
phi(N) = (p - 1) * (q - 1) = 5806 * 5860 = 34023160
d = modinv(e, phi(N))
~~~

---

## 4. Decrypting Each Character

Each number in the ciphertext represents one encrypted character. For each `c_i`:

~~~text
m_i = c_i^d mod N
char_i = chr(m_i)
~~~

---

## 5. Solve Script

~~~python
# Original solve by a101e-lab, adapted for this writeup
import libnum
from Crypto.Util.number import long_to_bytes

c_origin = "933969 15848125 24252056 5387227 5511551 10881790 3267174 14500698 28242580 933969 32093017 18035208 2594090 2594090 9122397 21290815 15930721 4502231 5173234 21290815 23241728 2594090 21290815 18035208 10891227 15930721 202434 202434 21290815 5511551 202434 4502231 5173234 25243036"

c_list = c_origin.split(" ")
n = 34034827
e = 5039
q = 5807
p = 5861

d = libnum.invmod(e, (p - 1) * (q - 1))
res = ""
for i in range(len(c_list)):
    c = int(c_list[i])
    m = pow(c, d, n)
    string = chr(m)
    res += string

print(res)
~~~

**Output:**

~~~text
poctf{uwsp_533k 4nd y3 5h411 f1nd}
~~~

The spaces in the output need to be replaced with underscores to match the flag format:

~~~text
poctf{uwsp_533k_4nd_y3_5h411_f1nd}
~~~

The leetspeak reads: "seek and ye shall find."

---

## 6. Attack Path Summary

~~~text
RSA parameters (e, N, C)
    |
Factor N -> p=5807, q=5861
    |
Compute d = modinv(e, phi(N))
    |
Decrypt each c_i: m_i = c_i^d mod N
    |
chr(m_i) for each -> plaintext with spaces
    |
Replace spaces with underscores -> FLAG
~~~

---

## 7. Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|--------------|
| 1 | Small RSA modulus (N < 2^26) can be trivially factored | Real RSA keys under 1024 bits are considered broken; NIST recommends 2048+ bits | Always check if N is small enough to factor directly |
| 2 | Per-character RSA encryption leaks frequency information | ECB-mode-like patterns emerge when encrypting one character at a time | Use proper padding schemes (OAEP) and encrypt full messages, not individual characters |
| 3 | Flag format hints guide decryption validation | Knowing the expected output format helps verify decryption results | Use known-plaintext patterns (like `poctf{`) to validate partial results |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Credential Access | TA0006 | Brute Force | T1110 |
| Defense Evasion | TA0005 | Obfuscated Files or Information | T1027 |
| Collection | TA0009 | Data from Local System | T1005 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediation and Containment

### Technical Fixes

1. Use RSA key sizes of 2048 bits or larger; 4096 bits recommended for long-term security
2. Never encrypt individual characters with RSA; use hybrid encryption (RSA + AES) with proper padding (OAEP)
3. Implement PKCS#1 v2.1 (OAEP) padding to prevent deterministic encryption patterns
4. Rotate keys regularly and use certificate-based key management

### MITRE D3FEND Countermeasures

- **D3-CSPP Credential Strength Policy Enforcement** to mandate adequate key lengths (counters T1110)
- **D3-MFA Multi-Factor Authentication** to reduce reliance on single-factor cryptographic authentication

### NIST CSF 2.0

- **Protect (PR.DS-1):** Data at rest is protected with adequate cryptographic strength
- **Protect (PR.DS-2):** Data in transit is protected using current cryptographic standards

### NIST SP 800-53 Rev. 5

- **SC-12: Cryptographic Key Establishment and Management** (use adequate key sizes)
- **SC-13: Cryptographic Protection** (use approved algorithms with proper parameters)

### CWE

- **CWE-326: Inadequate Encryption Strength** (RSA modulus too small to resist factoring)
- **CWE-327: Use of a Broken or Risky Cryptographic Algorithm** (per-character encryption without padding)

---

## References

- Based on solve approach from [a101e-lab](https://github.com/a101e-lab/CTF-Writeups)

---

Thanks guys!! (❍ᴥ❍ʋ)

---

RSA with a tiny modulus is basically handing over the keys; always check whether N can be factored before reaching for heavier math. If this crypto walkthrough helped demystify RSA basics, spread the word.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
