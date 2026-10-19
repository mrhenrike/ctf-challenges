#!/usr/bin/env python3 -I
"""
The Logic Inside (POCTF 2026, ID=79) - Web challenge solver.
"The Logic Inside" suggests logic-based web vulnerability.

Possible techniques:
- Logic flaws in authentication/authorization
- Business logic bypass
- Parameter manipulation
- Race conditions
- IDOR

Usage: python3 -I solve_logic.py <base_url> <session_cookie>
"""
import sys
import json
import urllib.request
import urllib.parse
import re
import pathlib


def fetch(url, cookie, method="GET", data=None, content_type=None):
    req = urllib.request.Request(url, method=method)
    req.add_header("Cookie", f"session={cookie}")
    if data:
        if isinstance(data, str):
            data = data.encode()
        req.data = data
    if content_type:
        req.add_header("Content-Type", content_type)
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.read().decode("utf-8", errors="replace")


def find_flag(text):
    m = re.search(r'POCTF\{[^}]+\}', text)
    return m.group(0) if m else None


def solve(base_url, cookie):
    print(f"[*] Fetching challenge page: {base_url}")
    html = fetch(base_url, cookie)

    flag = find_flag(html)
    if flag:
        print(f"[+] FLAG IN PAGE: {flag}")
        return flag

    print(f"[*] Page length: {len(html)}")
    print(f"[*] Looking for forms, links, and API endpoints...")

    links = re.findall(r'href=["\']([^"\']+)["\']', html)
    forms = re.findall(r'<form[^>]*action=["\']([^"\']*)["\']', html)
    scripts = re.findall(r'src=["\']([^"\']+\.js)["\']', html)

    print(f"  Links: {links[:10]}")
    print(f"  Forms: {forms}")
    print(f"  Scripts: {scripts[:5]}")

    for link in links:
        if link.startswith("#") or link.startswith("http"):
            continue
        full_url = base_url.rstrip("/") + "/" + link.lstrip("/") if not link.startswith("/") else f"https://pointeroverflowctf.com{link}"
        try:
            page = fetch(full_url, cookie)
            flag = find_flag(page)
            if flag:
                print(f"[+] FLAG at {link}: {flag}")
                return flag
        except Exception:
            pass

    for script_url in scripts:
        if not script_url.startswith("http"):
            script_url = base_url.rstrip("/") + "/" + script_url.lstrip("/")
        try:
            js = fetch(script_url, cookie)
            flag = find_flag(js)
            if flag:
                print(f"[+] FLAG in JS: {flag}")
                return flag
            api_endpoints = re.findall(r'["\'](/api/[^"\']+)["\']', js)
            fetch_urls = re.findall(r'fetch\(["\']([^"\']+)["\']', js)
            print(f"  JS APIs: {api_endpoints}")
            print(f"  JS fetches: {fetch_urls}")
        except Exception:
            pass

    print("[!] No flag found. Manual analysis needed.")
    return None


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 -I solve_logic.py <base_url> <session_cookie>")
        sys.exit(1)
    base_url = sys.argv[1]
    cookie = sys.argv[2]
    flag = solve(base_url, cookie)
    if flag:
        outdir = pathlib.Path(__file__).parent.parent / "loot"
        outdir.mkdir(exist_ok=True)
        (outdir / "flag.txt").write_text(flag + "\n")
