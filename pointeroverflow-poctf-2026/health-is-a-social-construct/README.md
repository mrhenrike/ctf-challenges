# Health Is a Social Construct

**Category:** Game Hacking (GH 200)
**Challenge:** Health Is a Social Construct
**Points:** 138 (Wave 2)
**Result:** Solved

**Flag:**

~~~text
POCTF{48.1391.6827672b8f2e5e3a5049b817cdd49041.EDJ32RKVZ2TRFRQHTRXPSBPHDI}
~~~

---

## 1. Reconnaissance

A 2D top-down shooter built with Godot Engine. Three rooms, final boss with impossibly high HP. The challenge description says: "The math is stacked against you, so change the math." The README hints at attaching a debugger and what a scripting language exposes.

The game binary (POCTF2026-GH002.x86_64, 79 MB) uses the same API infrastructure as Leap of Faith (ID=47).

### Credentials

~~~text
game.token: POCTF-GAME-2-48-cde4958a7dd9720e03f75c
team.key:   TEAMKEY48-1391-5D74B2549523
~~~

---

## 2. API Protocol Discovery

Having solved Leap of Faith first, the same HMAC-SHA256 API pattern applies:

1. `GET /api/challenges/48/instance` with game headers (credentials omitted) returns a nonce
2. `POST /api/challenges/48/tick` with HMAC-SHA256 signed sequences
3. `POST /api/challenges/48/complete` returns the flag marker

### Critical: No Browser Cookies

The `/instance` endpoint only returns the nonce when called without browser session cookies (`credentials: 'omit'` in fetch). With cookies present, it returns metadata without the nonce.

---

## 3. Exploitation

### Step 1: Obtain Nonce

~~~text
GET /api/challenges/48/instance
Headers:
  X-POCTF-GAME-TOKEN: POCTF-GAME-2-48-cde4958a7dd9720e03f75c
  X-POCTF-TEAM-KEY: TEAMKEY48-1391-5D74B2549523

Response: {"nonce": "6827672b8f2e5e3a5049b817cdd49041", "ok": true}
~~~

### Step 2: Send HMAC-Signed Ticks

Message format: `tick:48:<nonce>:<seq>`
Key: team.key value
Algorithm: HMAC-SHA256 (hex digest)

~~~python
import hmac, hashlib
msg = f"tick:48:{nonce}:{seq}"
mac = hmac.new(team_key.encode(), msg.encode(), hashlib.sha256).hexdigest()
~~~

Each tick POST requires:
- Headers: X-POCTF-GAME-TOKEN, X-POCTF-TEAM-KEY, X-POCTF-CHALLENGE-NONCE
- Body: `{"seq": N, "hmac": "<hex digest>"}`
- Minimum 2-second spacing between ticks (429 rate limit otherwise)

### Step 3: Complete

After sending enough ticks, immediately POST to `/complete` (the last tick must be recent, within seconds).

~~~text
POST /api/challenges/48/complete
Response: {"marker": "POCTF{48.1391.6827...}", "ok": true}
~~~

---

## 4. Attack Path Summary

~~~text
Extract game.token + team.key from credentials.zip
    |
GET /api/challenges/48/instance (no cookies)
    -> nonce: 6827672b8f2e5e3a5049b817cdd49041
    |
HMAC-SHA256 tick sequence (16 ticks, 2s spacing)
    -> tick:48:<nonce>:<seq> signed with team.key
    |
POST /api/challenges/48/complete (immediately after last tick)
    -> flag marker
    |
Submit on challenge page: "Landed. Nicely done."
~~~

---

## 5. Lessons Learned

| # | Finding | Key Takeaway |
|---|---|---|
| 1 | Game Hacking challenges share API infrastructure | Once you reverse one game's protocol, others follow the same pattern |
| 2 | The API returns nonce only without session cookies | credentials: 'omit' is essential for the instance endpoint |
| 3 | Rate limiting enforces ~2s minimum between ticks | Respect rate limits to avoid 429; the retry_after_ms field tells exact wait |
| 4 | /complete requires a recent tick | Send one final tick immediately before calling /complete |

---

## Reproduction Checklist

- [x] Extract credentials from ZIP
- [x] GET /instance with game headers, no cookies
- [x] Send HMAC-SHA256 signed tick sequence
- [x] POST /complete immediately after final tick
- [x] Submit flag on challenge page

---

## MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID | Context |
|---|---|---|---|
| Credential Access | Unsecured Credentials: Credentials in Files | T1552.001 | game.token and team.key extracted from credentials bundle |
| Discovery | Network Service Discovery | T1046 | API endpoints discovered via decompiled game scripts |
| Collection | Data from Information Repositories | T1213 | Nonce retrieved from /instance endpoint |
| Lateral Movement | Exploitation of Remote Services | T1210 | HMAC-signed API replay bypasses intended gameplay |
| Defense Evasion | Masquerading: Match Legitimate Name or Location | T1036.005 | API calls mimic legitimate game traffic |

> **CWE-321:** Use of Hard-coded Cryptographic Key. The HMAC signing key was embedded in the game client credentials bundle with no server-side rotation mechanism.

---

## Remediation and Containment

### Technical Fixes

1. Derive session-bound HMAC keys server-side instead of distributing static team keys
2. Enforce a minimum tick count and validate gameplay state transitions before accepting /complete
3. Bind nonce issuance to authenticated sessions, not custom headers alone
4. Implement certificate pinning or mutual TLS for game-to-server API communication

### MITRE D3FEND Countermeasures

- **D3-MFA (Multi-factor Authentication):** require a second factor beyond static tokens for API authentication
- **D3-ANCI (Authentication Credential Integrity):** rotate and invalidate HMAC keys per session
- **D3-NTCD (Network Traffic Community Deviation):** detect anomalous tick patterns (uniform spacing, no in-game telemetry)

### NIST CSF 2.0

- **Protect (PR.AA):** enforce identity management and access control for API endpoints
- **Detect (DE.CM):** monitor for API call patterns inconsistent with normal gameplay behavior
- **Respond (RS.MI):** rate-limit and block clients exhibiting replay patterns

### NIST SP 800-53 Rev. 5

- **SC-12 (Cryptographic Key Establishment and Management):** do not embed long-lived signing keys in client binaries
- **IA-5 (Authenticator Management):** rotate credentials; static team keys should expire after each session
- **SI-10 (Information Input Validation):** validate that tick sequences correspond to plausible game states
- **AC-3 (Access Enforcement):** enforce server-side gameplay state checks before granting flag access

### C2M2

- **Domain:** ACCESS (Access Management)
- **Practice:** Manage identities and credentials for authorized assets
- **Target MIL:** MIL-2 (documented and practiced key management; session-scoped credentials)

---

Thanks guys!! (❍ᴥ❍ʋ)

---

Game hacking challenges are always a blast. If this walkthrough helped you understand HMAC bypass or API manipulation, share it with someone who might find it useful.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
