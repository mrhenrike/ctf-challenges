#!/usr/bin/env python3 -I
"""Fast padding oracle attack with concurrent requests."""

import json
import urllib.request
import time
import sys
import concurrent.futures

API_URL = "https://pointeroverflowctf.com/challenges/consulting-room/oracle"
API_TOKEN = "rBRo2xfG9QhZMA_Gw3u4gXLvEj1XQ_CI"
CT_HEX = "9bed8df35e213ab04833ff160d1b04c5d7a3aa1394da2622bdfc0d76c85cdaf19346be97a8ef7e3e416645f5ec62c7584b07913ca68f5ba257a82664860347a4185c5bbbaf88a3b751dc3c7a84cdd4aa"
BS = 16


def oracle(hex_ct):
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json",
    }
    body = json.dumps({"record": hex_ct}).encode()
    for attempt in range(5):
        try:
            req = urllib.request.Request(API_URL, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                return data.get("padding") == "valid"
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(1.5)
                continue
            try:
                data = json.loads(e.read().decode())
                return data.get("padding") == "valid"
            except:
                return False
        except Exception:
            time.sleep(0.5)
    return False


def check_guess(guess, crafted_prefix, crafted_suffix, target_hex):
    hex_ct = crafted_prefix + format(guess, '02x') + crafted_suffix + target_hex
    valid = oracle(hex_ct)
    return guess, valid


def decrypt_block(prev_block, target_block):
    intermediate = bytearray(BS)
    plaintext = bytearray(BS)
    target_hex = target_block.hex()

    for byte_pos in range(BS - 1, -1, -1):
        pad_val = BS - byte_pos
        suffix_bytes = bytearray(BS - byte_pos - 1)
        for k in range(byte_pos + 1, BS):
            suffix_bytes[k - byte_pos - 1] = intermediate[k] ^ pad_val
        crafted_suffix = suffix_bytes.hex()
        crafted_prefix = '00' * byte_pos

        found = False
        # Try batches of guesses concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = {}
            for guess in range(256):
                f = executor.submit(check_guess, guess, crafted_prefix, crafted_suffix, target_hex)
                futures[f] = guess

            for f in concurrent.futures.as_completed(futures):
                guess, valid = f.result()
                if valid:
                    # For pad_val == 1, verify
                    if pad_val == 1 and byte_pos > 0:
                        verify_prefix = '00' * (byte_pos - 1) + format(1, '02x')
                        verify_hex = verify_prefix + format(guess, '02x') + crafted_suffix + target_hex
                        if not oracle(verify_hex):
                            continue

                    intermediate[byte_pos] = guess ^ pad_val
                    plaintext[byte_pos] = intermediate[byte_pos] ^ prev_block[byte_pos]
                    found = True
                    # Cancel remaining futures
                    for remaining in futures:
                        remaining.cancel()
                    break

        if not found:
            print(f"  [!] Failed at byte {byte_pos}", flush=True)
            return None

        sys.stdout.write(f"\r  byte {BS - byte_pos}/{BS} -> {chr(plaintext[byte_pos]) if 32 <= plaintext[byte_pos] < 127 else '?'}")
        sys.stdout.flush()

    print()
    return bytes(plaintext)


def main():
    ct = bytes.fromhex(CT_HEX)
    num_blocks = len(ct) // BS
    blocks = [ct[i * BS:(i + 1) * BS] for i in range(num_blocks)]

    print(f"[*] {len(ct)} bytes, {num_blocks} blocks ({num_blocks - 1} to decrypt)")

    plaintext = b""
    for i in range(1, num_blocks):
        print(f"\n[*] Block {i}/{num_blocks - 1}...", flush=True)
        pt = decrypt_block(blocks[i - 1], blocks[i])
        if pt is None:
            print(f"[!] Failed block {i}")
            break
        plaintext += pt
        print(f"  -> {pt!r}")

    # Remove PKCS7
    if plaintext:
        pad = plaintext[-1]
        if 1 <= pad <= BS and all(b == pad for b in plaintext[-pad:]):
            plaintext = plaintext[:-pad]

    print(f"\n[+] PLAINTEXT: {plaintext.decode('utf-8', errors='replace')}")


if __name__ == "__main__":
    main()
