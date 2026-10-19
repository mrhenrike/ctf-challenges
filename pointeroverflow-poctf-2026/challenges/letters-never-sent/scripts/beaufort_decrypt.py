#!/usr/bin/env python3
"""Beaufort cipher decryptor para Letters Never Sent - POCTF 2026 (Variant 088)"""

def beaufort(s, k):
    result = ''
    key_index = 0
    for ch in s:
        if 'A' <= ch <= 'Z':
            c = ord(ch) - 65
            kk = ord(k[key_index % len(k)]) - 65
            result += chr((kk - c) % 26 + 65)
            key_index += 1
        else:
            result += ch
    return result

ct = 'HUROZ{2.1391.4EPNB27L3IBRG6E3.A3CJZ3QQS37EWMB5YVGO5X42WR}'
key = 'WITHER'

pt = beaufort(ct, key)
print(f"Key:        {key}")
print(f"Ciphertext: {ct}")
print(f"Plaintext:  {pt}")

assert beaufort(pt, key) == ct, "Reciprocity check failed!"
print("Reciprocity check: PASS")
