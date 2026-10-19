#!/usr/bin/env python3
"""Lights Out solver for a 7x7 grid using Gaussian elimination over GF(2)."""
import sys
import json

N = 7

initial = [
    1, 1, 1, 0, 0, 0, 1,
    0, 1, 1, 0, 0, 1, 1,
    1, 0, 0, 1, 1, 0, 1,
    1, 0, 1, 0, 1, 1, 0,
    1, 1, 0, 1, 1, 1, 1,
    0, 1, 1, 0, 1, 1, 1,
    1, 1, 1, 1, 1, 0, 1,
]

def idx(r, c):
    return r * N + c

def build_toggle_matrix():
    size = N * N
    A = [[0] * size for _ in range(size)]
    for r in range(N):
        for c in range(N):
            press = idx(r, c)
            for dr, dc in [(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < N and 0 <= nc < N:
                    A[idx(nr, nc)][press] = 1
    return A

def solve_gf2(A, b):
    size = len(b)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]

    pivot_col = [0] * size
    row_idx = 0
    for col in range(size):
        found = -1
        for r in range(row_idx, size):
            if M[r][col] == 1:
                found = r
                break
        if found == -1:
            continue
        M[row_idx], M[found] = M[found], M[row_idx]
        pivot_col[row_idx] = col
        for r in range(size):
            if r != row_idx and M[r][col] == 1:
                for j in range(size + 1):
                    M[r][j] ^= M[row_idx][j]
        row_idx += 1

    x = [0] * size
    for i in range(row_idx):
        x[pivot_col[i]] = M[i][size]

    # verify
    for i in range(size):
        s = 0
        for j in range(size):
            s ^= A[i][j] * x[j]
        if s != b[i]:
            print("No solution exists!", file=sys.stderr)
            sys.exit(1)

    return x

A = build_toggle_matrix()
solution = solve_gf2(A, initial)

clicks = []
total = 0
print("Solution (cells to click):")
for r in range(N):
    row_str = ""
    for c in range(N):
        if solution[idx(r, c)]:
            clicks.append({"r": r, "c": c})
            row_str += "X "
            total += 1
        else:
            row_str += ". "
    print(f"  Row {r}: {row_str}")

print(f"\nTotal clicks: {total}")
print(f"\nClicks as JSON (for API): {json.dumps(clicks)}")

# Verify by simulation
state = initial[:]
for click in clicks:
    r, c = click["r"], click["c"]
    for dr, dc in [(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)]:
        nr, nc = r + dr, c + dc
        if 0 <= nr < N and 0 <= nc < N:
            state[idx(nr, nc)] ^= 1

assert all(s == 0 for s in state), "Verification failed!"
print("\nVerification: all candles are dark. PASS")
