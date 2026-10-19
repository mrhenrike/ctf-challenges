#!/usr/bin/env python3 -I
"""
Columns of Holes (POCTF 2026, ID=85) - Punched card / Hollerith decoder.

"Columns of Holes" = IBM 80-column punched card encoding.

IBM Card Layout:
- 80 columns, 12 rows per column
- Rows from top: 12 (Y), 11 (X), 0, 1, 2, 3, 4, 5, 6, 7, 8, 9
- Zone punches (rows 12, 11, 0) + numeric punches encode characters
- Single digit punch (1-9) = that digit
- 0 alone = 0
- 12+1 = A, 12+2 = B, ..., 12+9 = I
- 11+1 = J, 11+2 = K, ..., 11+9 = R
- 0+1 = /, 0+2 = S, 0+3 = T, ..., 0+9 = Z

Usage: python3 -I solve_punchcard.py <artifact_file>
"""
import sys
import pathlib
import re

HOLLERITH = {
    (12,): '+', (11,): '-', (0,): '0',
    (12, 1): 'A', (12, 2): 'B', (12, 3): 'C', (12, 4): 'D',
    (12, 5): 'E', (12, 6): 'F', (12, 7): 'G', (12, 8): 'H', (12, 9): 'I',
    (11, 1): 'J', (11, 2): 'K', (11, 3): 'L', (11, 4): 'M',
    (11, 5): 'N', (11, 6): 'O', (11, 7): 'P', (11, 8): 'Q', (11, 9): 'R',
    (0, 1): '/', (0, 2): 'S', (0, 3): 'T', (0, 4): 'U',
    (0, 5): 'V', (0, 6): 'W', (0, 7): 'X', (0, 8): 'Y', (0, 9): 'Z',
    (1,): '1', (2,): '2', (3,): '3', (4,): '4',
    (5,): '5', (6,): '6', (7,): '7', (8,): '8', (9,): '9',
    (): ' ',
    (12, 8, 3): '#', (11, 8, 3): '@',
    (8, 3): ':', (8, 4): ';', (8, 5): "'", (8, 6): '=', (8, 7): '"',
    (12, 8, 4): '$', (12, 8, 5): '*', (12, 8, 6): ')',
    (11, 8, 4): '%', (11, 8, 5): '!', (11, 8, 6): '^',
    (0, 8, 3): ',', (0, 8, 4): '.', (0, 8, 5): '<', (0, 8, 6): '>',
    (12, 0): '&', (11, 0): '?',
    (12, 8, 2): '!',
}

def decode_column(punches):
    key = tuple(sorted(punches))
    if key in HOLLERITH:
        return HOLLERITH[key]
    for k, v in HOLLERITH.items():
        if set(k) == set(punches):
            return v
    return f'[{",".join(map(str,punches))}]'

def parse_text_grid(text):
    """Parse a text-based punched card representation."""
    lines = text.strip().split('\n')
    lines = [l for l in lines if l.strip()]

    if len(lines) >= 12:
        rows = lines[:12]
        max_cols = max(len(r) for r in rows)
        result = []
        for col in range(max_cols):
            punches = []
            row_labels = [12, 11, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
            for row_idx, row_label in enumerate(row_labels):
                if row_idx < len(rows) and col < len(rows[row_idx]):
                    ch = rows[row_idx][col]
                    if ch in ('1', 'X', 'O', '*', '#', 'x', 'o'):
                        punches.append(row_label)
            result.append(decode_column(punches))
        return ''.join(result)
    return None

def parse_binary_grid(data):
    """Parse binary data as punched card grid."""
    bits = ''.join(f'{b:08b}' for b in data)
    # Try 12-bit columns
    result = []
    for i in range(0, len(bits) - 11, 12):
        column_bits = bits[i:i+12]
        punches = []
        row_labels = [12, 11, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
        for j, label in enumerate(row_labels):
            if column_bits[j] == '1':
                punches.append(label)
        result.append(decode_column(punches))
    return ''.join(result)

def solve(filepath):
    filepath = pathlib.Path(filepath)
    data = filepath.read_bytes()
    text = data.decode('utf-8', errors='replace')

    print(f"[*] File: {filepath}")
    print(f"[*] Size: {len(data)} bytes")

    flag = re.search(r'POCTF\{[^}]+\}', text)
    if flag:
        print(f"[+] FLAG directly: {flag.group()}")
        return flag.group()

    result = parse_text_grid(text)
    if result:
        print(f"[*] Text grid decode: {result}")
        flag = re.search(r'POCTF\{[^}]+\}', result)
        if flag:
            return flag.group()
        return result

    result = parse_binary_grid(data)
    if result and len(result) > 5:
        print(f"[*] Binary grid decode: {result[:80]}")
        flag = re.search(r'POCTF\{[^}]+\}', result)
        if flag:
            return flag.group()

    print("[!] Could not decode. Manual analysis required.")
    return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 -I solve_punchcard.py <artifact>")
        sys.exit(1)
    result = solve(sys.argv[1])
    if result:
        outdir = pathlib.Path(__file__).parent.parent / "loot"
        outdir.mkdir(exist_ok=True)
        (outdir / "flag.txt").write_text(result + "\n")
