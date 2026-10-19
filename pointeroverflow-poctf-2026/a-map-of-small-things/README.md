# A Map of Small Things

**Category:** Cryptography
**Challenge:** A Map of Small Things
**CTF:** Pointer Overflow CTF 2026
**Points:** 137 (CRYP 300, Wave 4)
**Result:** Solved

**Flag:**

~~~text
POCTF{73.1391.YTRCNRU3QYH4T7U7.E7MFBDMKUAVEV4UJMVJ7ZA2F5F}
~~~

---

## 1. Reconnaissance

Meridian Analytics uses a "proprietary" elliptic-curve key exchange called MapCrypt. We are given the curve parameters and a public key, and must recover the private key k.

**Curve parameters:**

| Parameter | Value |
|---|---|
| Equation | y^2 = x^3 + x (a=1, b=0) over Fp |
| p | 17759930830448937043 |
| G | (2, 2130375071143573863) |
| Q = k*G | (310951215520125117, 6072823342940074756) |

The prime p is only ~64 bits (1.78 x 10^19). This is catastrophically small for an elliptic curve: production curves use 256+ bit primes.

---

## 2. Identifying the Vulnerability

Two critical weaknesses:

1. **Small prime field:** p fits in 64 bits, making the group order around 64 bits. The Elliptic Curve Discrete Logarithm Problem (ECDLP) over such a small group is tractable.

2. **Smooth curve order:** The curve y^2 = x^3 + x over Fp with p = 3 mod 4 has order exactly p + 1 = 17759930830448937044. This factors as:

~~~text
17759930830448937044 = 2^2 * 38603 * 121123 * 949584469
~~~

All prime factors are small (largest ~10^9), making the Pohlig-Hellman algorithm extremely efficient.

---

## 3. Exploitation

### Step 1: Determine Curve Order

For the curve y^2 = x^3 + x over Fp where p = 3 mod 4, a well-known result in algebraic geometry gives #E(Fp) = p + 1. This is because the curve has complex multiplication by the Gaussian integers Z[i], and when p = 3 mod 4, the Frobenius endomorphism acts as multiplication by a purely imaginary element, giving trace t = 0.

~~~python
p = 17759930830448937043
assert p % 4 == 3
order = p + 1  # = 17759930830448937044
~~~

### Step 2: Factor the Order

~~~text
order = 2^2 * 38603 * 121123 * 949584469
~~~

All factors are small, confirming Pohlig-Hellman will be fast.

### Step 3: Pohlig-Hellman with BSGS

For each prime power factor q^e of the order:

1. Project G and Q into the subgroup of order q^e
2. Solve the DLP in this small subgroup using Baby-step Giant-step (O(sqrt(q)) time)
3. Combine results via Chinese Remainder Theorem

~~~text
k mod 4         = 3
k mod 38603     = 16798
k mod 121123    = 65949
k mod 949584469 = 135069154
~~~

CRT gives: **k = 3414047123619293099**

### Step 4: Verify

~~~python
assert point_mul(3414047123619293099, G) == Q  # True
~~~

---

## 4. Attack Path Summary

~~~text
Identify curve: y^2 = x^3 + x, p ~ 64 bits
    |
p mod 4 == 3  ->  order = p + 1
    |
Factor order: 2^2 * 38603 * 121123 * 949584469
    |  -> all smooth (largest factor ~ 10^9)
    |
Pohlig-Hellman: DLP in each subgroup via BSGS
    |  -> CRT combines residues
    |
k = 3414047123619293099  ->  submit  ->  FLAG
~~~

---

## 5. Lessons Learned

| # | Finding | Key Takeaway |
|---|---|---|
| 1 | 64-bit prime field is trivially small | Production ECC must use 256+ bit primes (NIST P-256, Curve25519); anything under 160 bits is breakable |
| 2 | Curve order p+1 is smooth | When #E has only small factors, Pohlig-Hellman reduces ECDLP to several tiny DLPs; always use curves with (near-)prime order |
| 3 | Special curve form y^2 = x^3 + x | This curve has CM by Z[i], giving predictable order structure; "proprietary" crypto parameters from a junior engineer are a red flag |
| 4 | BSGS is O(sqrt(q)) per subgroup | The largest subgroup only needs ~31,000 steps, making the entire attack instant |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID | Relevance |
|---|---|---|---|
| Credential Access | Brute Force | T1110 | Pohlig-Hellman is a structured brute force against weak ECC parameters |
| Credential Access | Steal Application Access Token | T1528 | Recovering the private key grants full impersonation of the keyholder |
| Resource Development | Obtain Capabilities: Tool | T1588.002 | SageMath/custom scripts used to compute ECDLP |

---

## Remediation and Containment

### Technical Fixes

1. Use standardized curves with 256+ bit primes (NIST P-256, Curve25519, secp256k1) for all ECC operations
2. Reject custom or "proprietary" curve parameters in code review; mandate only well-audited curves
3. Verify that the curve order is (near-)prime to prevent Pohlig-Hellman decomposition
4. Enforce key size minimums in cryptographic libraries via policy configuration

### MITRE D3FEND Countermeasures

- **D3-CALM** (Certificate Analysis): validate that TLS/SSH certificates use curves of adequate strength
- **D3-SPP** (Strong Password Policy): analogous principle: enforce minimum key sizes just as password length minimums are enforced

### NIST CSF 2.0

- **Protect (PR.DS-2):** data in transit must be protected using approved cryptographic algorithms and key lengths
- **Identify (ID.AM-5):** maintain an inventory of cryptographic assets and their parameter strengths

### NIST SP 800-53 Rev. 5

- **SC-12 (Cryptographic Key Establishment and Management):** use NIST-approved key lengths; ECC keys must be at least 224 bits (256 recommended)
- **SC-13 (Cryptographic Protection):** employ FIPS-validated cryptographic modules; reject non-standard curve parameters
- **SA-8 (Security and Privacy Engineering Principles):** design crypto subsystems with well-analyzed primitives, not custom constructions

### C2M2

- **Domain:** TECHNOLOGY
- **Practice:** Apply cryptographic controls consistent with organizational policy
- **Target MIL:** MIL-2 (documented and practiced: cryptographic parameter validation is part of the SDLC)

---

Thanks guys!! (❍ᴥ❍ʋ)

---

If this deep dive into elliptic curve math helped you crack the code, share it with your crew and let's connect! Always down to talk crypto, CTFs and offensive security.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
