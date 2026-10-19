#!/usr/bin/env python3 -I
"""
Whitespace Steganography solver for "Invisible Ink" (POCTF 2026, ID=102).
Based on reference writeup: trailing spaces/tabs encode 7-bit ASCII.
space=0, tab=1, MSB-first, carrier lines are odd-numbered (0-indexed).

Usage: python3 -I solve_whitespace_stego.py <artifact.py>
"""
import sys
import pathlib


def extract_flag(filepath):
    lines = pathlib.Path(filepath).read_text(encoding="utf-8").splitlines()

    print(f"[*] File: {filepath}")
    print(f"[*] Total lines: {len(lines)}")

    # First pass: find lines with trailing whitespace
    trailing_lines = []
    for i, line in enumerate(lines):
        stripped = line.rstrip(" \t")
        trailer = line[len(stripped):]
        if trailer:
            trailing_lines.append((i, trailer))

    print(f"[*] Lines with trailing whitespace: {len(trailing_lines)}")

    if not trailing_lines:
        print("[!] No trailing whitespace found")
        return None

    # Try approach 1: odd-numbered lines (0-indexed), last 7 chars of trailer
    flag_chars = []
    for i in range(0, len(lines), 2):  # even indices = odd line numbers
        stripped = lines[i].rstrip(" \t")
        trailer = lines[i][len(stripped):]
        if len(trailer) < 7:
            continue
        last7 = trailer[-7:]
        bits = "".join("0" if c == " " else "1" for c in last7)
        ch = chr(int(bits, 2))
        flag_chars.append(ch)

    flag1 = "".join(flag_chars)
    if "POCTF{" in flag1:
        print(f"\n[+] FLAG (approach 1 - even indices): {flag1}")
        return flag1

    # Try approach 2: all lines with trailing whitespace, last 7 chars
    flag_chars = []
    for i, trailer in trailing_lines:
        if len(trailer) < 7:
            continue
        last7 = trailer[-7:]
        bits = "".join("0" if c == " " else "1" for c in last7)
        ch = chr(int(bits, 2))
        flag_chars.append(ch)

    flag2 = "".join(flag_chars)
    if "POCTF{" in flag2:
        print(f"\n[+] FLAG (approach 2 - all trailing lines): {flag2}")
        return flag2

    # Try approach 3: only lines with >= 7 trailing whitespace
    flag_chars = []
    for i, trailer in trailing_lines:
        if len(trailer) < 7:
            continue
        # Use exactly 7 bits from the end
        last7 = trailer[-7:]
        bits = "".join("0" if c == " " else "1" for c in last7)
        val = int(bits, 2)
        if 32 <= val < 127:
            flag_chars.append(chr(val))
        else:
            flag_chars.append(f"[{val}]")

    flag3 = "".join(flag_chars)
    print(f"\n[*] Decoded (approach 3): {flag3}")

    # Try inverted: space=1, tab=0
    flag_chars = []
    for i, trailer in trailing_lines:
        if len(trailer) < 7:
            continue
        last7 = trailer[-7:]
        bits = "".join("1" if c == " " else "0" for c in last7)
        val = int(bits, 2)
        if 32 <= val < 127:
            flag_chars.append(chr(val))

    flag4 = "".join(flag_chars)
    if "POCTF{" in flag4:
        print(f"\n[+] FLAG (inverted): {flag4}")
        return flag4

    print(f"[*] Inverted: {flag4}")

    # Dump raw whitespace for manual inspection
    print("\n[*] Raw trailing whitespace dump (first 30 lines):")
    for i, trailer in trailing_lines[:30]:
        visual = trailer.replace(" ", "S").replace("\t", "T")
        print(f"  line {i:3d} ({len(trailer):3d} chars): ...{visual[-20:]}")

    return flag3


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 -I solve_whitespace_stego.py <artifact.py>")
        sys.exit(1)
    result = extract_flag(sys.argv[1])
    if result and "POCTF{" in result:
        outdir = pathlib.Path(__file__).parent.parent / "loot"
        outdir.mkdir(exist_ok=True)
        (outdir / "flag.txt").write_text(result)
        print(f"[+] Saved to {outdir / 'flag.txt'}")
