#!/usr/bin/env python3
"""
Solve The Apparatus, Rapport (POCTF 2026, ID=5).
Tic-Tac-Toe order deduction + ASCII shift cipher.
"""
from itertools import permutations

# Board state:
# A:. B:. C:X  |  D:O E:. F:X  |  G:. H:O I:X
# X won with right column C-F-I
# X positions: {C, F, I}, O positions: {D, H}

# Primary ciphertext (HTML entities decoded)
ct_primary = 'URE[N!808;>40>U]\\HH?I]G`?:S9X6:HYWI7U[XOHETY^L]5:S[FERI\\!'
# Secondary ciphertext
ct_secondary = 'G|"ziqw"hvi#d!(fvj3(g|"{pj#dymfwj\'lwdyu(gxv\'vtw"ymyxtumi/"~m%rrlv%wjl(|d{5'

def decrypt_ascii(ct, key_shifts):
    pt = []
    for i, ch in enumerate(ct):
        shift = key_shifts[i % len(key_shifts)]
        p = ((ord(ch) - 32 - shift) % 95) + 32
        pt.append(chr(p))
    return ''.join(pt)

# Generate all valid game orders
# X moves at positions 0, 2, 4 (moves 1, 3, 5)
# O moves at positions 1, 3 (moves 2, 4)
x_positions = ['C', 'F', 'I']
o_positions = ['D', 'H']

expected_prefix = "POCTF{"

found = False
for x_perm in permutations(x_positions):
    for o_perm in permutations(o_positions):
        order = [x_perm[0], o_perm[0], x_perm[1], o_perm[1], x_perm[2]]
        key_shifts = [ord(c) - ord('A') for c in order]
        pt = decrypt_ascii(ct_primary, key_shifts)
        if pt.startswith(expected_prefix):
            print(f"Order: {''.join(order)}")
            print(f"Key shifts: {key_shifts}")
            print(f"Primary plaintext: {pt}")
            print()
            pt2 = decrypt_ascii(ct_secondary, key_shifts)
            print(f"Secondary plaintext: {pt2}")
            found = True
            print()

if not found:
    print("No valid ordering found with POCTF{{ prefix!")
