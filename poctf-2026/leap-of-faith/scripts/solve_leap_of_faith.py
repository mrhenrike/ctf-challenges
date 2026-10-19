#!/usr/bin/env python3 -I
"""
Leap of Faith (POCTF 2026, ID=47) solver.

Flow:
  1. GET /api/challenges/47/instance with game headers -> nonce
  2. POST /api/challenges/47/tick (HMAC-SHA256 signed) x N
  3. POST /api/challenges/47/complete -> flag (marker)

The game binary was the wrong (test) version, so its GDScript could be
decompiled with GDRE Tools, revealing the full API protocol.

Usage:
  python3 -I solve_leap_of_faith.py <game_token> <team_key>
"""

import sys
import hmac
import hashlib
import json
import time
import urllib.request

API_BASE = "https://pointeroverflowctf.com"
CHALLENGE_ID = 47
TICK_COUNT = 15
TICK_INTERVAL = 2.0


def api_request(path, method="GET", body=None, headers=None):
    url = API_BASE + path
    if headers is None:
        headers = {}
    data = json.dumps(body).encode() if body else None
    if data:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.status, json.loads(resp.read().decode())


def hmac_sha256_hex(key_str, msg_str):
    return hmac.new(
        key_str.encode(), msg_str.encode(), hashlib.sha256
    ).hexdigest()


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <game_token> <team_key>")
        sys.exit(1)

    game_token = sys.argv[1].strip()
    team_key = sys.argv[2].strip()

    game_headers = {
        "X-POCTF-GAME-TOKEN": game_token,
        "X-POCTF-TEAM-KEY": team_key,
    }

    print("[*] Requesting instance (nonce)...")
    status, data = api_request(
        f"/api/challenges/{CHALLENGE_ID}/instance",
        headers=game_headers.copy(),
    )
    print(f"    status={status} data={data}")

    nonce = data.get("nonce")
    if not nonce:
        print("[!] No nonce in response. Check credentials.")
        sys.exit(1)

    print(f"[+] Nonce: {nonce}")

    nonce_headers = {**game_headers, "X-POCTF-CHALLENGE-NONCE": nonce}

    print(f"[*] Sending {TICK_COUNT} ticks (interval={TICK_INTERVAL}s)...")
    for seq in range(1, TICK_COUNT + 1):
        msg = f"tick:{CHALLENGE_ID}:{nonce}:{seq}"
        mac = hmac_sha256_hex(team_key, msg)

        while True:
            status, resp = api_request(
                f"/api/challenges/{CHALLENGE_ID}/tick",
                method="POST",
                body={"seq": seq, "hmac": mac},
                headers=nonce_headers.copy(),
            )
            if status == 429:
                wait = resp.get("retry_after_ms", 2000) / 1000.0 + 0.1
                print(f"    tick {seq}: rate limited, waiting {wait:.1f}s")
                time.sleep(wait)
                continue
            print(f"    tick {seq}: {status} tick_count={resp.get('tick_count', '?')}")
            break

        if seq < TICK_COUNT:
            time.sleep(TICK_INTERVAL)

    print("[*] Requesting flag (complete)...")
    status, data = api_request(
        f"/api/challenges/{CHALLENGE_ID}/complete",
        method="POST",
        body={},
        headers=nonce_headers.copy(),
    )
    print(f"    status={status}")

    marker = data.get("marker", "")
    if marker:
        print(f"\n[+] FLAG: {marker}")
    else:
        print(f"[!] No marker in response: {data}")
        sys.exit(1)


if __name__ == "__main__":
    main()
