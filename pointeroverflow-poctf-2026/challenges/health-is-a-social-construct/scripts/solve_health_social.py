#!/usr/bin/env python3 -I
"""
Health Is a Social Construct (POCTF 2026, ID=48) solver.
Same protocol as Leap of Faith (ID=47): instance -> tick x15 -> complete.
"""

import sys
import hmac
import hashlib
import json
import time
import urllib.request

API_BASE = "https://pointeroverflowctf.com"
CHALLENGE_ID = 48
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
    nonce = data.get("nonce")
    if not nonce:
        print(f"[!] No nonce: {data}")
        sys.exit(1)
    print(f"[+] Nonce: {nonce}")

    nonce_headers = {**game_headers, "X-POCTF-CHALLENGE-NONCE": nonce}

    print(f"[*] Sending {TICK_COUNT} ticks...")
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
                time.sleep(wait)
                continue
            print(f"    tick {seq}: ok (count={resp.get('tick_count', '?')})")
            break
        if seq < TICK_COUNT:
            time.sleep(TICK_INTERVAL)

    print("[*] Requesting flag...")
    status, data = api_request(
        f"/api/challenges/{CHALLENGE_ID}/complete",
        method="POST",
        body={},
        headers=nonce_headers.copy(),
    )
    marker = data.get("marker", "")
    if marker:
        print(f"\n[+] FLAG: {marker}")
    else:
        print(f"[!] Failed: {data}")
        sys.exit(1)


if __name__ == "__main__":
    main()
