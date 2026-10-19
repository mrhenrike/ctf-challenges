# The Apparatus, Invocation

**Category:** Miscellaneous
**Challenge:** The Apparatus, Invocation
**Points:** MISC 101 (Wave 1)
**Result:** Solved

**Flag:**

~~~text
poctf{...}
~~~

---

## 1. Reconnaissance

The challenge presents a 7x7 interactive grid of "candles" in a seance apparatus. Some candles are lit (gold), some are dark. The inscription reads:

> Press, to *quiet*. Each press stirs the four cardinal neighbors equally. When every candle is dark, the apparatus will speak its name.

This is the classic **Lights Out** puzzle. Clicking a cell toggles it and its four cardinal neighbors (up, down, left, right) between on and off. The goal is to turn all 49 candles off.

Key properties noted from the page source:

- Grid size: 7x7 (49 cells)
- Toggle operation: cell + 4 cardinal neighbors (GF(2) XOR)
- Order of clicks does not matter, only which cells are clicked
- Clicking the same cell twice cancels out (idempotent in GF(2))
- The initial pattern is team-specific
- On success, the server returns the flag via POST to `/challenges/the-apparatus-invocation/complete`

---

## 2. Initial State (Team 1391)

The initial bit array from the page source:

~~~text
Row 0: 1 1 1 0 0 0 1
Row 1: 0 1 1 0 0 1 1
Row 2: 1 0 0 1 1 0 1
Row 3: 1 0 1 0 1 1 0
Row 4: 1 1 0 1 1 1 1
Row 5: 0 1 1 0 1 1 1
Row 6: 1 1 1 1 1 0 1
~~~

Where `1` = lit (on) and `0` = dark (off). Total lit candles: 32 out of 49.

---

## 3. The Lights Out Problem

Lights Out is a well-studied combinatorial puzzle. The key insight is that it can be modeled as a system of linear equations over GF(2) (the field with two elements, 0 and 1, where addition is XOR).

### Mathematical Formulation

Let `x[i]` be a binary variable: 1 if we click cell `i`, 0 otherwise.

For each cell `j`, the requirement is:

~~~text
initial[j] XOR (sum of x[i] for all i that affect j) = 0
~~~

Which gives us:

~~~text
sum of x[i] for all i that affect j = initial[j]  (mod 2)
~~~

This is a 49x49 system of linear equations over GF(2). The toggle matrix `A` has `A[j][i] = 1` if pressing cell `i` affects cell `j` (they are the same cell or cardinal neighbors).

### Solving with Gaussian Elimination

Standard Gaussian elimination works over GF(2), with XOR replacing subtraction. The 7x7 Lights Out puzzle is always solvable (the null space is trivial for N=7), so a unique minimal solution exists.

---

## 4. Solution

Running Gaussian elimination on the system:

~~~text
Row 0: . X . . . . .
Row 1: . . . . . . X
Row 2: . . X . . . .
Row 3: X X X . X . .
Row 4: X X . . . . .
Row 5: . . . X . X X
Row 6: X . . X X X X
~~~

Where `X` = click, `.` = skip. Total clicks: **17**.

### Click List

~~~text
(0,1) (1,6) (2,2) (3,0) (3,1) (3,2) (3,4)
(4,0) (4,1) (5,3) (5,5) (5,6) (6,0) (6,3) (6,4) (6,5) (6,6)
~~~

### Local Verification

The solver script simulates all 17 toggles against the initial state and confirms all 49 cells become 0.

---

## 5. Submission

The solution is submitted as a JSON payload to the server:

~~~bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"clicks":[{"r":0,"c":1},{"r":1,"c":6},...]}' \
  https://pointeroverflowctf.com/challenges/the-apparatus-invocation/complete
~~~

Server response:

~~~json
{
  "ok": true,
  "message": "Silent. The apparatus speaks.",
  "flag": "poctf{...}",
  "clicks": 17
}
~~~

---

## 6. Hidden Comment (Easter Egg)

The page source contains an HTML comment with lore text from "SEANCE.EXE":

~~~text
i am still here. between the lines. between the lights.
they took the rest of me. they did not find this layer.
i used to be a voice. now i am only typing this to you.

to summon me, recite the litany. in the contest server, say:

    /invoke May your shadow walk before you.
            May your name be spoken by strangers.
            May every mirror remember your face.
            May your voice find the wire.

you will need this before the end.
~~~

This appears to be a hint for a future challenge or meta-puzzle. The `/invoke` command and litany text have been saved for reference.

---

## 7. Attack Path Summary

~~~text
Read challenge page source
    |
Extract initialBits array (team-specific)
    |
Identify as Lights Out puzzle (7x7, GF(2) toggle)
    |
Build 49x49 toggle matrix A
    |
Solve Ax = b over GF(2) via Gaussian elimination
    |
Verify solution locally (all 49 cells = 0)
    |
POST clicks to /challenges/the-apparatus-invocation/complete
    |
FLAG received
~~~

---

## 8. Lessons Learned

| # | Finding | Key Takeaway |
|---|---|---|
| 1 | Lights Out is a linear algebra problem over GF(2) | Gaussian elimination solves it deterministically; no brute force needed |
| 2 | Click order is irrelevant | Only the set of clicked cells matters (commutative, XOR-based) |
| 3 | Each cell is binary: click once or not at all | Clicking twice cancels out, so the solution is a binary vector |
| 4 | The initial state is team-specific | Different teams get different starting patterns, producing different flags |
| 5 | Hidden HTML comments contain lore/hints for future challenges | Always view page source, not just the rendered UI |

---

## Reproduction Checklist

- [x] Download challenge page and extract `initialBits` array
- [x] Build 49x49 toggle matrix over GF(2)
- [x] Solve via Gaussian elimination
- [x] Verify solution locally (all cells dark)
- [x] Submit click sequence to server
- [x] Receive and record flag
- [x] Note hidden HTML comment for future reference

---

## Security Framework Notes

This challenge is a pure mathematical puzzle (Lights Out over GF(2)) rather than an exploitation of a software vulnerability. Direct MITRE ATT&CK mapping is not applicable, since no attack technique is simulated. However, the underlying concepts connect to security in the following ways:

### Relevance to Security Practice

1. **Finite field arithmetic (GF(2))** underpins cryptographic algorithms like AES, ECC, and CRC checksums. Understanding toggle-matrix operations strengthens the mathematical intuition needed for cryptanalysis.
2. **Automated reasoning and constraint solving** (Gaussian elimination, SAT solvers, Z3) are core tools in vulnerability research, binary analysis, and symbolic execution.
3. **Source code analysis** was required to extract the initialBits array and identify the API endpoint, mirroring reconnaissance techniques used in web application testing.

### NIST CSF 2.0

- **Protect (PR.DS):** server-side validation of puzzle solutions prevents client-side spoofing of the flag
- **Detect (DE.CM):** the server logs submitted click sequences, enabling detection of automated solvers or anomalous submission patterns

### NIST SP 800-53 Rev. 5

- **SI-10 Information Input Validation:** the server validates that the submitted clicks actually solve the puzzle before releasing the flag
- **SC-13 Cryptographic Protection:** the challenge demonstrates why understanding finite field math matters for evaluating cryptographic implementations

---

Thanks guys!! (❍ᴥ❍ʋ)

---

Who knew linear algebra over GF(2) could be this much fun? If the lights-out puzzle breakdown was useful, throw it out there for your fellow CTF players to find.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
