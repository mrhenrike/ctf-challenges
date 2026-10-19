#!/usr/bin/env python3
"""
Embrace the Suck - POCTF 2024
Converts plaintext to POCTF leetspeak format.
Original solve script by Jdwalli.
"""

char_set = '4bcd3f6h1jklmn0pqr57uvwxyz'
text = "the needs of the many"
mapping = dict(zip("abcdefghijklmnopqrstuvwxyz", char_set))
flag = ""
for char in text:
    if char == " ":
        flag += "_"
    else:
        flag += str(mapping[char.lower()])

print(f"poctf{{uwsp_{flag}}}")
