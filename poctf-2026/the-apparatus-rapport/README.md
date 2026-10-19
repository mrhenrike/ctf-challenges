# The Apparatus, Rapport

**Category:** Cryptography
**Challenge:** The Apparatus, Rapport
**Points:** CRYP 125 (Wave 2)
**Series:** The Apparatus (2 of 8)
**Result:** Solved

**Flag:**

~~~text
poctf{...}
~~~

---

## 1. Reconnaissance

The challenge presents a completed Tic-Tac-Toe board and two ciphertexts. The prompt states:

> X won. The order in which each square was played, written as a sequence of square labels, is the key to the ciphertext.

### The Board

~~~text
A: .  B: .  C: X
D: O  E: .  F: X
G: .  H: O  I: X
~~~

X won via the right column (C, F, I). The squares are labeled A through I, left-to-right, top-to-bottom.

### Ciphertexts

Primary:
~~~text
URE[N!808;>40>U]\HH?I]G`?:S9X6:HYWI7U[XOHETY^L]5:S[FERI\!
~~~

Secondary:
~~~text
G|"ziqw"hvi#d!(fvj3(g|"{pj#dymfwj'lwdyu(gxv'vtw"ymyxtumi/"~m%rrlv%wjl(|d{5
~~~

---

## 2. Game Analysis

### Constraints

- X moves first (positions 1, 3, 5), O moves second (positions 2, 4)
- X played: C, F, I (3 moves)
- O played: D, H (2 moves)
- Total: 5 moves. X wins on move 5.
- X cannot win before move 5 (with only 2 pieces, no 3-in-a-row is possible)

### Possible Orderings

There are 3! x 2! = 12 possible game orderings. Only one produces valid plaintext when used as the cipher key.

---

## 3. Cipher Identification

Working backwards from the expected flag prefix "POCTF{":

~~~text
Ciphertext:  U  R  E  [  N  !
Expected:    P  O  C  T  F  {
Difference:  5  3  2  7  8  5 (repeating)
~~~

The cipher is a **printable ASCII shift cipher** with modular arithmetic:

~~~text
C[i] = ((P[i] - 32 + shift[i % keylen]) % 95) + 32
P[i] = ((C[i] - 32 - shift[i % keylen]) % 95) + 32
~~~

Operating on the printable ASCII range (32-126, mod 95).

### Key Derivation

The shifts [5, 3, 2, 7, 8] map to labels with offset from 'A':
- 5 = F (ord('F') - ord('A'))
- 3 = D
- 2 = C
- 7 = H
- 8 = I

So the game order is **F, D, C, H, I** and the key string is `FDCHI`.

### Game Verification

~~~text
Move 1 (X): F     Board: F=X
Move 2 (O): D     Board: F=X, D=O
Move 3 (X): C     Board: F=X, D=O, C=X
Move 4 (O): H     Board: F=X, D=O, C=X, H=O
Move 5 (X): I     Board: F=X, D=O, C=X, H=O, I=X  -> X wins! (C-F-I column)
~~~

Valid game. X wins on move 5 by completing the right column.

---

## 4. Decryption

### Primary Message (Flag)

~~~text
poctf{...}
~~~

### Secondary Message (Lore)

~~~text
By salt and by ash, by the breath drawn but not returned, we open the way.
~~~

This appears to be another ritual phrase from the Apparatus series, similar to the litany found in the Invocation challenge.

---

## 5. Attack Path Summary

~~~text
Extract board state from SVG (labels A-I, X/O positions)
    |
Identify X wins via right column (C, F, I)
    |
Enumerate 12 possible game orderings
    |
Test each as shift key against "POCTF{" prefix
    |
Unique match: FDCHI with shifts [5, 3, 2, 7, 8]
    |
Verify game legality (X wins on move 5)
    |
Decrypt both ciphertexts with printable-ASCII mod-95 shift
    |
Flag submitted and confirmed
~~~

---

## 6. Lessons Learned

| # | Finding | Key Takeaway |
|---|---|---|
| 1 | The cipher operates on full printable ASCII (mod 95), not just A-Z | Always consider the character range when the ciphertext contains special characters |
| 2 | Known-plaintext attack (POCTF{ prefix) reduces 12 orderings to 1 | Flag prefix is a powerful oracle for key recovery |
| 3 | Tic-Tac-Toe game logic constrains valid orderings | X moves on odd turns, O on even; the winning move must be last |
| 4 | The secondary message is lore for the Apparatus series | Keep ritual phrases and lore text for future challenges |

---

## Reproduction Checklist

- [x] Extract board state from challenge page SVG
- [x] Identify winning line and played squares
- [x] Enumerate valid game orderings
- [x] Use POCTF{ prefix as known plaintext to determine key
- [x] Verify game legality
- [x] Decrypt primary ciphertext (flag)
- [x] Decrypt secondary ciphertext (lore)
- [x] Submit flag

---

## MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID | Relevance |
|---|---|---|---|
| Credential Access | Brute Force: Password Cracking | T1110.002 | Enumerating 12 game orderings as candidate keys is a small keyspace brute force |
| Collection | Data from Information Repositories | T1213 | Extracting board state from the SVG to derive the key |
| Defense Evasion | Obfuscated Files or Information | T1027 | The cipher uses printable-ASCII mod-95 shift to obscure the plaintext |

---

## Remediation and Containment

### Technical Fixes

1. Never derive encryption keys from low-entropy game states; 12 possible keys is equivalent to ~3.6 bits of entropy
2. Use authenticated encryption (AES-GCM, ChaCha20-Poly1305) instead of simple substitution or shift ciphers
3. If a shared secret must come from a visual puzzle, apply a KDF (HKDF, Argon2) to expand entropy before using it as a key
4. Avoid exposing the flag prefix as known plaintext; it enables trivial known-plaintext attacks

### MITRE D3FEND Countermeasures

- **D3-MFA** (Multi-factor Authentication): do not rely on a single low-entropy factor for access to sensitive data
- **D3-ANCI** (Authentication Normalization and Credential Integrity): ensure credentials have sufficient entropy

### NIST CSF 2.0

- **Protect (PR.DS-1):** protect data at rest using strong, standards-based encryption, not custom ciphers
- **Protect (PR.AA-1):** identities and credentials are issued, managed, and verified using appropriate entropy levels

### NIST SP 800-53 Rev. 5

- **SC-12 (Cryptographic Key Establishment and Management):** keys must have sufficient entropy; 3.6 bits is far below the 128-bit minimum
- **SC-13 (Cryptographic Protection):** use FIPS-validated algorithms; mod-95 shift cipher does not qualify
- **IA-5 (Authenticator Management):** authenticators (keys, passwords) must meet minimum complexity requirements

---

Thanks guys!! (❍ᴥ❍ʋ)

---

Cryptography challenges that tie gameplay to ciphertext are next-level creative. If this walkthrough helped you see the connection, share it with someone who loves puzzles as much as we do.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
