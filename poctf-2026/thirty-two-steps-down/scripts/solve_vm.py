#!/usr/bin/env python3 -I
"""
Thirty-Two Steps Down (POCTF 2026, ID=129) - Custom VM sandbox escape.

The prompt says: "Custom stack-based virtual machine. It's happy to execute
whatever bytecode you feed it, within the rules of its sandbox."

"32 steps" = 32-bit addressing or 32 VM instructions.

Strategy:
1. Connect and get the VM spec/source
2. Understand the instruction set
3. Find a way to read the flag (likely stored in memory outside sandbox)
4. Possible: stack overflow, type confusion, OOB read, instruction injection

Usage: python3 -I solve_vm.py <host> <port> <token>
"""
import socket
import sys
import time
import re
import pathlib


def recv_all(sock, timeout=3):
    sock.settimeout(timeout)
    data = b""
    while True:
        try:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
        except socket.timeout:
            break
    return data.decode("utf-8", errors="replace")


def send_recv(sock, msg, timeout=3):
    sock.sendall((msg + "\n").encode())
    time.sleep(0.5)
    return recv_all(sock, timeout)


def find_flag(text):
    m = re.search(r'POCTF\{[^}]+\}', text)
    return m.group(0) if m else None


def solve(host, port, token):
    print(f"[*] Target: {host}:{port}")

    # Recon
    print("[*] Recon: connecting to understand the VM...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(15)
        sock.connect((host, int(port)))
        banner = recv_all(sock, 3)
        print(f"[BANNER]\n{banner}")

        resp = send_recv(sock, token)
        print(f"[AFTER TOKEN]\n{resp}")

        # Try various inputs
        for test in ["help", "?", "list", "nop", "push 1", "0", "AAAA", ""]:
            resp = send_recv(sock, test)
            print(f"['{test}'] -> {resp.strip()[:200]}")
            flag = find_flag(resp)
            if flag:
                sock.close()
                return flag
            if not resp:
                break

        sock.close()
    except Exception as e:
        print(f"[!] Recon error: {e}")

    # The VM likely accepts bytecode. Try common patterns:
    bytecode_tests = [
        # NOP sled
        "00" * 32,
        # Push and print
        "01 41 02",
        # Overflow attempt
        "01 " * 40 + "02",
        # Negative index
        "01 FF FF FF FF",
        # Read from memory address 0
        "03 00 00 00 00",
    ]

    for bc in bytecode_tests:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(15)
            sock.connect((host, int(port)))
            recv_all(sock, 2)
            send_recv(sock, token)

            resp = send_recv(sock, bc, timeout=5)
            flag = find_flag(resp)
            if flag:
                print(f"\n[+] FLAG with bytecode: {bc}")
                sock.close()
                return flag

            if resp.strip() and 'error' not in resp.lower():
                print(f"  [*] {bc[:30]} -> {resp.strip()[:100]}")

            sock.close()
        except Exception:
            pass

    print("[!] Need to analyze VM source code for instruction set. Manual analysis required.")
    return None


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python3 -I solve_vm.py <host> <port> <token>")
        sys.exit(1)

    flag = solve(sys.argv[1], sys.argv[2], sys.argv[3])
    if flag:
        outdir = pathlib.Path(__file__).parent.parent / "loot"
        outdir.mkdir(exist_ok=True)
        (outdir / "flag.txt").write_text(flag + "\n")
