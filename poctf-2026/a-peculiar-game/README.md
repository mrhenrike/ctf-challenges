# A Peculiar Game

**Category:** Miscellaneous / Steganography
**Challenge:** A Peculiar Game
**CTF:** Pointer Overflow CTF 2026
**Points:** MISC 200 (Wave 4)
**Result:** Solved

**Flag:**

~~~text
C72DA241EF03DB00
~~~

---

## 1. Reconnaissance

The challenge provides a PDF containing the record of a chess game in standard algebraic notation. At first glance it looks like a normal game, but closer inspection reveals that several moves are illegal: pieces appearing on impossible squares, captures that violate movement rules, and positions that cannot be reached through legal play.

These are not transcription errors. The illegal moves are deliberately placed, and they encode hidden data using the chess board as a steganographic channel.

---

## 2. Identifying the Encoding

In standard algebraic notation, each move specifies a piece type and a destination square. The destination square is defined by a file (column a-h, mapped to 0-7) and a rank (row 1-8). The piece types map to indices: Pawn=0, Knight=1, Bishop=2, Rook=3, Queen=4, King=5.

The key insight is that only the illegal moves carry data. Legal moves are noise; illegal moves are signal. Identifying which moves violate chess rules requires validating the full game state after each move.

---

## 3. Exploration of Encoding Schemes

Multiple encoding hypotheses were tested systematically:

| Scheme | Formula | Output |
|---|---|---|
| A | `piece_type * 8 + file` (6-bit per move) | `E396D9A0F7816588` |
| B | `file` only (3-bit) | Insufficient bits |
| C | `rank` only (3-bit) | Insufficient bits |
| D | `file * 2 + rank_offset` | `C72DA241EF03DB00` |

The trailing `00` in Scheme D was a strong indicator of correct alignment: bit streams that end with zero padding typically indicate the message fits cleanly into the available bit space.

---

## 4. Exploitation

The decoder script processes each illegal move:

~~~python
def decode_illegal_moves(moves, legal_validator):
    bits = []
    board = chess.Board()
    for move in moves:
        if not legal_validator(board, move):
            file_idx = ord(move.to_square[0]) - ord('a')  # 0-7
            rank_idx = int(move.to_square[1]) - 1          # 0-7
            rank_offset = rank_idx % 2
            value = file_idx * 2 + rank_offset
            bits.append(value)
        try:
            board.push(move)
        except:
            pass
    return bits_to_hex(bits)
~~~

Running this against the full game record:

~~~text
Illegal moves detected: 16
Encoding: file * 2 + rank_offset per illegal move
Output: C72DA241EF03DB00
~~~

---

## 5. Verification

~~~text
>> ACK :: Correct.
~~~

---

## Captured Flags

| Type | Value | Found At | Method |
|---|---|---|---|
| Flag | `C72DA241EF03DB00` | Chess game PDF (illegal moves) | Steganographic decoding of illegal chess moves via file*2+rank_offset scheme |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Steganography can hide data in any structured format, not just images | APT groups have used chess notation, music scores, and emoji sequences as covert channels | Any format with enough structure to carry entropy can be a stego carrier |
| 2 | Systematic enumeration of encoding schemes is essential when the scheme is unknown | Malware analysts face the same problem when reversing custom C2 encoding: enumerate decoders, score outputs, test for structure | Document every hypothesis and its output; the trailing `00` was the discriminator here |
| 3 | Illegal moves are the signal; legal moves are noise | This mirrors network stego where anomalous packets carry data while normal traffic provides cover | In stego analysis, identify what deviates from the expected format and treat it as the message |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|---|---|---|---|
| Defense Evasion | TA0005 | Obfuscated Files or Information: Steganography | T1027.003 |
| Command and Control | TA0011 | Data Encoding: Standard Encoding | T1132.001 |
| Exfiltration | TA0010 | Exfiltration Over C2 Channel | T1041 |
| Collection | TA0009 | Data from Local System | T1005 |

> **APT Reference:** The Turla Group (Snake) has used steganographic channels hidden in legitimate-looking documents for C2 communication, embedding commands in PDF metadata and image pixel values. APT29 (Cozy Bear) has also used document-based steganography to exfiltrate data through innocuous-looking files.

---

## Remediation and Containment

### Technical Fixes

1. Implement deep content inspection (DCI) for outbound documents to detect anomalous patterns
2. Use data loss prevention (DLP) tools that analyze document structure, not just keywords
3. Monitor for files with statistically unusual content patterns (high entropy in structured fields)
4. Restrict outbound document types and enforce format normalization before transmission

### If You Find Something Similar in Your Environment

**Immediate containment:**
- Analyze all recently transmitted documents for steganographic content
- Deploy network-level stego detection tools on egress points
- Audit document workflows for opportunities to inject covert data
- Check for unauthorized document modification tools on endpoints

**MITRE D3FEND countermeasures:**
- D3-FCA (File Content Analysis) to detect steganographic patterns in documents
- D3-NTA (Network Traffic Analysis) to identify covert channels in document transfers
- D3-DA (Data Authentication) to verify document integrity before transmission

### Framework Alignment

**CWE:**
- CWE-311: Missing Encryption of Sensitive Data (data hidden via obfuscation, not encryption)
- CWE-200: Exposure of Sensitive Information to an Unauthorized Actor
- CWE-506: Embedded Malicious Code (hidden data in documents)

**OWASP Top 10 (2021):**
- A02:2021 Cryptographic Failures (steganography is obfuscation, not encryption)

**NIST CSF 2.0:**
- Identify (ID.AM): Inventory document workflows and potential stego carriers
- Protect (PR.DS): Implement DLP and content normalization for outbound documents
- Detect (DE.AE): Deploy stego detection on network egress and document repositories
- Respond (RS.AN): Analyze detected steganographic content for exfiltration indicators
- Recover (RC.CO): Communicate findings to affected parties and remediate

**NIST SP 800-53 (Rev. 5):**
- SI-4: System Monitoring (detect covert channels in document transfers)
- SC-7: Boundary Protection (inspect outbound documents at network boundaries)
- AU-12: Audit Record Generation (log document creation and transmission)

**C2M2:**
- Domain: SITUATIONAL AWARENESS (Situational Awareness)
- Practice: Perform logging and monitoring to support situational awareness
- Target MIL: MIL-2 (documented covert channel detection capabilities)

---

## Final Thoughts

Chess steganography is a beautiful intersection of game theory and information hiding. The challenge forces you to think like a signals analyst: separate signal from noise, enumerate candidate encodings, and validate against expected structure. In the real world, covert channels hide in every structured format you can imagine, from chess games to MIDI files to DNS queries. The defender's job is to notice when the data does not follow the rules of its format.

Thanks guys!! (❍ᴥ❍ʋ)

---

Chess and stego in the same challenge? That is peak CTF energy. If this walkthrough gave you ideas for your next covert channel, drop a follow and let's keep the creativity flowing.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
