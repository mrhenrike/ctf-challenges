#!/usr/bin/env python3 -I
"""
Padding Oracle Attack against The Consulting Room (POCTF 2026, ID=72).

AES-CBC with PKCS#7 padding. The oracle at /challenges/consulting-room/oracle
returns {"padding": "valid"} or {"padding": "invalid"}.
"""
import sys
import json
import urllib.request
import time

BASE_URL = "https://pointeroverflowctf.com"
ORACLE_PATH = "/challenges/consulting-room/oracle"
API_TOKEN = "rBRo2xfG9QhZMA_Gw3u4gXLvEj1XQ_CI"
BLOCK_SIZE = 16

CT_HEX = "9bed8df35e213ab04833ff160d1b04c5d7a3aa1394da2622bdfc0d76c85cdaf19346be97a8ef7e3e416645f5ec62c7584b07913ca68f5ba257a82664860347a4185c5bbbaf88a3b751dc3c7a84cdd4aa"


def oracle(ct_hex):
    url = BASE_URL + ORACLE_PATH
    data = json.dumps({"record": ct_hex}).encode()
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode())
            return body.get("padding") == "valid"
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        if "invalid" in body:
            return False
        raise


def split_blocks(ct_bytes):
    return [ct_bytes[i:i+BLOCK_SIZE] for i in range(0, len(ct_bytes), BLOCK_SIZE)]


def decrypt_block(prev_block, target_block):
    """Decrypt one block using the padding oracle."""
    intermediate = bytearray(BLOCK_SIZE)
    plaintext = bytearray(BLOCK_SIZE)

    for byte_pos in range(BLOCK_SIZE - 1, -1, -1):
        pad_val = BLOCK_SIZE - byte_pos

        crafted = bytearray(BLOCK_SIZE)
        for k in range(byte_pos + 1, BLOCK_SIZE):
            crafted[k] = intermediate[k] ^ pad_val

        found = False
        for guess in range(256):
            crafted[byte_pos] = guess
            test_ct = crafted.hex() + target_block.hex()

            if oracle(test_ct):
                candidate = guess ^ pad_val

                if byte_pos == BLOCK_SIZE - 1:
                    crafted2 = bytearray(crafted)
                    crafted2[byte_pos - 1] ^= 1
                    test_ct2 = crafted2.hex() + target_block.hex()
                    if not oracle(test_ct2):
                        continue

                intermediate[byte_pos] = candidate
                plaintext[byte_pos] = candidate ^ prev_block[byte_pos]
                found = True
                decoded_so_far = bytes(plaintext[byte_pos:]).decode("latin-1")
                print(f"  byte {byte_pos:2d}: 0x{candidate:02x} -> '{decoded_so_far}'")
                break

        if not found:
            print(f"  byte {byte_pos}: FAILED (no valid padding found)")
            return None

    return bytes(plaintext)


def main():
    ct = bytes.fromhex(CT_HEX)
    blocks = split_blocks(ct)
    print(f"[*] Ciphertext: {len(ct)} bytes, {len(blocks)} blocks (including IV)")
    print(f"[*] Starting Padding Oracle Attack...")
    print()

    full_plaintext = b""
    for i in range(1, len(blocks)):
        print(f"[*] Decrypting block {i}/{len(blocks)-1}...")
        pt_block = decrypt_block(blocks[i-1], blocks[i])
        if pt_block is None:
            print(f"[!] Failed on block {i}")
            break
        full_plaintext += pt_block
        print(f"  -> block {i} plaintext: {pt_block!r}")
        print()

    pad_len = full_plaintext[-1] if full_plaintext else 0
    if 1 <= pad_len <= BLOCK_SIZE and all(b == pad_len for b in full_plaintext[-pad_len:]):
        full_plaintext = full_plaintext[:-pad_len]

    print(f"\n[+] PLAINTEXT: {full_plaintext.decode('utf-8', errors='replace')}")

    with open("../loot/flag.txt", "w") as f:
        f.write(full_plaintext.decode("utf-8", errors="replace"))
    print("[+] Saved to loot/flag.txt")


if __name__ == "__main__":
    main()
