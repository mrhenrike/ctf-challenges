# Leap of Faith

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2026 |
| **Category** | Game Hacking |
| **Difficulty** | Unknown |
| **Points** | 87 |
| **Flag** | `poctf{dynamic}` |
| **Status** | Solved |

---

## 1. Reconnaissance

The challenge provides a Godot 4 3D platformer binary (`POCTF2026-GH001.x86_64`, ~85 MB) and a credentials bundle containing:

- `game.token`: per-team authentication token
- `team.key`: HMAC signing key

The challenge description states:

> "Games are just numbers pretending to be physics. One of those numbers is the height of your jump. In this case, that number is not quite high enough to reach the last platform. That is the point."

A critical note on the challenge page reveals: "An error in this challenge led to the wrong game version being uploaded. The test binary trivializes the challenge."

---

## 2. Binary Analysis

~~~bash
file POCTF2026-GH001.x86_64
# ELF 64-bit LSB executable, x86-64, Godot Engine v4.7.1
~~~

The binary includes an embedded PCK (Godot package) at offset `0x4611138`. The PCK header shows `flags=2` (encrypted), but since this is the test binary, the encryption key is embedded in the engine itself.

---

## 3. Decompiling with GDRE Tools

Using GDRE Tools v2.7.4 in headless mode, all 79 files from the PCK were extracted and decompiled:

~~~bash
./gdre_tools.x86_64 --headless \
  --recover="POCTF2026-GH001.x86_64" \
  --output-dir="./decompiled"
# Verified 79 files, no errors detected!
~~~

Key GDScript files recovered:

| File | Purpose |
|---|---|
| `auth_check.gd` | Initial authentication, obtains session nonce |
| `Ticker.gd` | Sends HMAC-SHA256 signed ticks during gameplay |
| `FlagToken.gd` | Requests the flag after game completion |
| `GameController.gd` | Wires goal detection, starts ticker |
| `end_screen.gd` | Displays flag to player |
| `goal.gd` | Detects player reaching the hoop |

---

## 4. API Protocol (from decompiled sources)

The decompiled scripts reveal a three-phase API protocol:

### Phase 1: Instance Creation (`auth_check.gd`)

~~~
GET /api/challenges/47/instance
Headers:
  X-POCTF-GAME-TOKEN: <game.token>
  X-POCTF-TEAM-KEY: <team.key>
Response: {"nonce": "<session_nonce>", "ok": true}
~~~

Critical finding: the request must NOT include browser session cookies. The game client authenticates solely via `X-POCTF-*` headers. Sending browser cookies causes the server to return a response without the nonce field.

### Phase 2: Gameplay Ticks (`Ticker.gd`)

~~~
POST /api/challenges/47/tick
Headers:
  Content-Type: application/json
  X-POCTF-GAME-TOKEN: <game.token>
  X-POCTF-TEAM-KEY: <team.key>
  X-POCTF-CHALLENGE-NONCE: <nonce>
Body: {"seq": <N>, "hmac": "<hmac_hex>"}
~~~

HMAC computation (SHA-256):

~~~
message = "tick:47:<nonce>:<seq>"
key     = <team.key>
hmac    = HMAC-SHA256(key, message).hex()
~~~

The ticker runs every 2.5 seconds in-game. The server enforces rate limiting (~1.5s between accepted ticks) and returns `429` with `retry_after_ms` when exceeded.

### Phase 3: Flag Retrieval (`FlagToken.gd`)

~~~
POST /api/challenges/47/complete
Headers:
  Content-Type: application/json
  X-POCTF-GAME-TOKEN: <game.token>
  X-POCTF-TEAM-KEY: <team.key>
  X-POCTF-CHALLENGE-NONCE: <nonce>
Body: {}
Response: {"marker": "poctf{...}"}
~~~

The server requires a recent tick (within a few seconds). If `stale_last_tick` is returned, send fresh ticks first.

---

## 5. Exploitation

With the full protocol understood, no need to actually play the game. The solver:

1. Requests an instance (GET with game headers, no cookies) to obtain the nonce.
2. Sends ticks with HMAC-SHA256 signatures, respecting the rate limiter.
3. Calls `/complete` immediately after the last accepted tick.

~~~python
import hmac, hashlib

nonce = "d7690bd43ae8e9d4302e23dcb6876479"
team_key = "TEAMKEY47-1391-4C2C2D10B00B"

for seq in range(1, 16):
    msg = f"tick:47:{nonce}:{seq}"
    mac = hmac.new(team_key.encode(), msg.encode(), hashlib.sha256).hexdigest()
    # POST /api/challenges/47/tick with {"seq": seq, "hmac": mac}
~~~

After 5 accepted ticks (with 2-second spacing), the `/complete` endpoint returned the flag:

~~~json
{"marker": "poctf{...}"}
~~~

---

## 6. Attack Path Summary

~~~text
POCTF2026-GH001.x86_64 (test binary, wrong version)
    |
GDRE Tools v2.7.4 --headless --recover
    |
Decompiled 79 files (GDScript)
    |
auth_check.gd -> GET /api/challenges/47/instance (no cookies!)
    |                  -> nonce: d7690bd43ae8...
    |
Ticker.gd -> POST /api/challenges/47/tick
    |          msg = "tick:47:<nonce>:<seq>"
    |          hmac = HMAC-SHA256(team_key, msg)
    |          (5+ ticks with 2s spacing)
    |
FlagToken.gd -> POST /api/challenges/47/complete
                   -> marker = poctf{...}
~~~

---

## 7. Lessons Learned

| # | Finding | Key Takeaway |
|---|---|---|
| 1 | Test binary shipped with embedded encryption key | Never distribute debug/test builds in production; they expose internal logic |
| 2 | Authentication via custom headers, no CSRF | Game APIs using bearer-style headers bypass web CSRF protections |
| 3 | Browser cookies interfered with game API | The `/instance` endpoint returns different data depending on cookie presence; always test APIs with and without session context |
| 4 | Rate limiter on ticks but no minimum tick count | The server checked recency of last tick but not total tick count for /complete |
| 5 | HMAC-SHA256 with known key in decompiled source | Client-side crypto with embedded keys provides no real security against reverse engineering |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID | Context |
|---|---|---|---|
| Resource Development | Obtain Capabilities: Tool | T1588.002 | GDRE Tools used to decompile the Godot binary |
| Initial Access | Supply Chain Compromise: Compromise Software Supply Chain | T1195.002 | Test binary shipped with embedded encryption key, trivializing the challenge |
| Credential Access | Unsecured Credentials: Credentials in Files | T1552.001 | game.token and team.key extracted from credentials bundle |
| Discovery | Network Service Discovery | T1046 | API protocol reverse-engineered from decompiled GDScript sources |
| Collection | Data from Information Repositories | T1213 | Nonce obtained from /instance endpoint without browser cookies |
| Defense Evasion | Obfuscated Files or Information: Embedded Payloads | T1027.009 | PCK encrypted payload embedded inside the ELF binary |

> **CWE-321:** Use of Hard-coded Cryptographic Key. The PCK encryption key was embedded in the test binary, allowing trivial extraction of all game logic.
> **CWE-798:** Use of Hard-coded Credentials. The HMAC signing key was distributed as a static file.

---

## Remediation and Containment

### Technical Fixes

1. Never ship debug/test builds to production; use separate signing keys per build environment
2. Store PCK encryption keys in a hardware security module or server-side key vault, not embedded in the client
3. Rotate HMAC team keys per session and bind nonces to authenticated server sessions
4. Validate gameplay state server-side before accepting /complete requests (minimum play time, state transitions)
5. Implement server-side game simulation validation to detect API-only replays

### MITRE D3FEND Countermeasures

- **D3-OTP (One-time Password):** issue per-session credentials instead of static team keys
- **D3-FE (File Encryption):** use asymmetric encryption for game assets so client cannot recover the key
- **D3-NTCD (Network Traffic Community Deviation):** flag sessions with zero game telemetry but valid tick patterns

### NIST CSF 2.0

- **Identify (ID.AM):** maintain an inventory of build artifacts; test builds must never reach production channels
- **Protect (PR.DS):** protect cryptographic keys at rest; no embedded secrets in distributed binaries
- **Detect (DE.CM):** monitor API call patterns for anomalous replay behavior
- **Respond (RS.MI):** automatically revoke sessions exhibiting API-only interaction without gameplay telemetry

### NIST SP 800-53 Rev. 5

- **SC-12 (Cryptographic Key Establishment and Management):** keys must not be embedded in client binaries
- **CM-7 (Least Functionality):** strip debug symbols and test encryption keys from release builds
- **SI-10 (Information Input Validation):** validate tick sequences against plausible game state
- **IA-5 (Authenticator Management):** enforce credential rotation; static team keys should not persist across sessions

### C2M2

- **Domain:** TECHNOLOGY (Cybersecurity Architecture)
- **Practice:** Establish and maintain cybersecurity architecture for organizational assets
- **Target MIL:** MIL-2 (release management controls preventing test artifacts in production)

---

Thanks guys!! (❍ᴥ❍ʋ)

---

Taking that leap of faith into game hacking pays off when you know where to look. Got value from this breakdown? Let me know on socials, always happy to chat about offensive techniques.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
