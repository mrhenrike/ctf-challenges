#!/usr/bin/env python3 -I
"""
Excavation (POCTF 2026, ID=119) solver.
Repeating 8-byte XOR on .sav files, then acrostic extraction from item names.

Usage: python3 -I solve_excavation.py <team_file.sav> [sample1.sav ...]
"""
import sys
import struct
import pathlib

ENGLISH_FREQ = {
    ord(' '): 18.0, ord('e'): 9.5, ord('t'): 7.0, ord('a'): 6.5,
    ord('o'): 6.2, ord('i'): 6.0, ord('n'): 5.7, ord('s'): 5.3,
    ord('h'): 5.0, ord('r'): 4.8, ord('d'): 3.5, ord('l'): 3.3,
    ord('c'): 2.3, ord('u'): 2.3, ord('m'): 2.0, ord('w'): 1.8,
    ord('f'): 1.8, ord('g'): 1.6, ord('y'): 1.5, ord('p'): 1.5,
    ord('b'): 1.2, ord('v'): 0.8, ord('k'): 0.5, ord('j'): 0.1,
    ord('x'): 0.1, ord('q'): 0.05, ord('z'): 0.05,
}

for c in range(ord('A'), ord('Z') + 1):
    ENGLISH_FREQ[c] = ENGLISH_FREQ.get(c + 32, 0.05) * 0.08


def score_english(data):
    total = 0.0
    for b in data:
        if b in ENGLISH_FREQ:
            total += ENGLISH_FREQ[b]
        elif 33 <= b <= 126:
            total += 0.5
        elif b == 0:
            total += 0.3
        else:
            total += 0.01
    return total / max(len(data), 1)


def recover_key(payload, key_len=8):
    key = bytearray(key_len)
    for r in range(key_len):
        chunk = payload[r::key_len]
        best_k = 0
        best_score = -1
        for k in range(256):
            decrypted = bytes(b ^ k for b in chunk)
            s = score_english(decrypted)
            if s > best_score:
                best_score = s
                best_k = k
        key[r] = best_k
    return bytes(key)


def decrypt(payload, key):
    return bytes(c ^ key[i % len(key)] for i, c in enumerate(payload))


def parse_sav(filepath):
    data = pathlib.Path(filepath).read_bytes()
    if len(data) < 12:
        print(f"[!] File too small: {filepath}")
        return None

    magic = data[0:4]
    version = data[4:8]
    total = struct.unpack('<I', data[8:12])[0]

    print(f"\n[*] File: {filepath}")
    print(f"[*] Size: {len(data)} bytes")
    print(f"[*] Magic: {magic.hex()}")
    print(f"[*] Version: {version.hex()}")
    print(f"[*] Total field: {total}")

    if total != len(data):
        print(f"[!] Total field mismatch (expected {len(data)}, got {total})")

    payload = data[12:]
    print(f"[*] Payload: {len(payload)} bytes")

    key = recover_key(payload, 8)
    print(f"[*] Recovered key: {key.hex()}")

    plain = decrypt(payload, key)

    printable_ratio = sum(1 for b in plain if 32 <= b < 127 or b in (0, 10, 13)) / len(plain)
    print(f"[*] Printable ratio: {printable_ratio:.1%}")

    return plain


def extract_item_names(plain):
    """Extract item names from decrypted save data."""
    items = []
    i = 0
    while i < len(plain):
        if plain[i] == 0x10 and i + 4 < len(plain):
            item_idx = plain[i + 1]
            name_len = plain[i + 4]
            if 1 <= name_len <= 64 and i + 5 + name_len <= len(plain):
                try:
                    name = plain[i + 5: i + 5 + name_len].decode('utf-8', errors='replace')
                    if all(c.isprintable() or c == ' ' for c in name):
                        items.append((item_idx, name))
                        i += 5 + name_len
                        continue
                except Exception:
                    pass
        i += 1

    items.sort(key=lambda x: x[0])
    return items


def extract_acrostic(items):
    return ''.join(name[0].upper() if name else '?' for _, name in items)


def extract_strings_fallback(plain, min_len=4):
    """Fallback: extract printable strings."""
    strings = []
    current = []
    for b in plain:
        if 32 <= b < 127:
            current.append(chr(b))
        else:
            if len(current) >= min_len:
                strings.append(''.join(current))
            current = []
    if len(current) >= min_len:
        strings.append(''.join(current))
    return strings


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 -I solve_excavation.py <team_file.sav> [sample.sav ...]")
        sys.exit(1)

    for filepath in sys.argv[1:]:
        plain = parse_sav(filepath)
        if plain is None:
            continue

        items = extract_item_names(plain)
        if items:
            print(f"\n[*] Inventory ({len(items)} items):")
            for idx, name in items:
                print(f"    [{idx:2d}] {name}")
            token = extract_acrostic(items)
            print(f"\n[+] Acrostic token: {token}")
            if len(token) == 16:
                print(f"[+] FLAG candidate: POCTF{{{token}}}")
        else:
            print("[!] No items parsed via structured approach; trying string extraction...")
            strings = extract_strings_fallback(plain)
            print(f"[*] Extracted {len(strings)} strings:")
            for s in strings[:30]:
                print(f"    {s}")

        print(f"\n[*] First 500 bytes (decoded, printable only):")
        preview = ''.join(chr(b) if 32 <= b < 127 else '.' for b in plain[:500])
        for line_start in range(0, len(preview), 80):
            print(f"    {preview[line_start:line_start + 80]}")

    team_file = sys.argv[1]
    plain = parse_sav(team_file)
    if plain:
        items = extract_item_names(plain)
        if items and len(items) == 16:
            token = extract_acrostic(items)
            outdir = pathlib.Path(__file__).parent.parent / "loot"
            outdir.mkdir(exist_ok=True)
            flag = f"POCTF{{{token}}}"
            (outdir / "flag.txt").write_text(flag + "\n")
            print(f"\n[+] Saved flag to loot/flag.txt: {flag}")
