# Oauthbreaker — Writeup (2/2)

**Difficulty:** Medium | **Category:** Android | **Points:** 7 (estimated)

---

## Challenge Overview

**Context:** An Android app that implements OAuth authentication. The APK contains security logic obfuscated in an esoteric language (Brainfuck) and exposes a `WebAppInterface` that dynamically computes the path to a flag file.

**What you face:** A real APK that needs to be decompiled, analyzed, and its logic reverse-engineered. OAuth exposes the `access_token` in the callback URL, and the flag path is computed via embedded Brainfuck code.

**Vulnerabilities exploited:**
- OAuth Token Exposure (CWE-522) — `access_token` exposed in the redirect URL
- Insecure Data Storage / Hardcoded Logic — flag path computable via APK reverse engineering
- WebAppInterface exposure — Java method accessible from JS inside a WebView

**What you learn:**
- OAuth flows: how `access_token` can leak in the callback URL (implicit flow)
- Android APK reverse engineering with `androguard` or `jadx`
- Decoding esoteric languages (Brainfuck) embedded in code
- Android WebView: `@JavascriptInterface` exposes Java methods to JavaScript
- How to dynamically compute resource paths via static APK analysis

---

## Flag 1 — OAuth Token Leak

Previously credited. The Android app redirects to the CTF server exposing the access_token in the callback URL.

## Flag 2 — APK Reverse Engineering (getFlagPath)

### Objective

The APK contains `WebAppInterface.getFlagPath()` which dynamically computes the path of an HTML file on the CTF instance. Accessing that file returns the flag.

### Prerequisites

- Active Oauthbreaker instance at `https://<hash>.ctf.hacker101.com`
- Python 3.14 + androguard 4.1.4: `pip3 install androguard --break-system-packages`
- APK: download from `https://<hash>.ctf.hacker101.com/oauth.apk`

### Step by Step

#### 1. Download and extract the APK

```bash
curl -s -o oauth.apk https://e8072a862be3003083ebea167ef89592.ctf.hacker101.com/oauth.apk
unzip oauth.apk -d apk_contents
# classes.dex generated at apk_contents/classes.dex
```

#### 2. Extract iArr and compute the path

```python
#!/usr/bin/env python3.14
import sys, struct, logging
sys.path.insert(0, '/home/mrhenrike/.local/lib/python3.14/site-packages')
logging.disable(logging.CRITICAL)
from androguard.core.dex import DEX

with open('apk_contents/classes.dex', 'rb') as f:
    dex_data = f.read()

d = DEX(dex_data)
iArr = None

for cls in d.get_classes():
    if 'WebAppInterface' not in cls.get_name():
        continue
    for method in cls.get_methods():
        if method.get_name() != 'getFlagPath':
            continue
        bc = method.get_code().get_bc()
        for ins in bc.get_instructions():
            if ins.get_name() == 'fill-array-data-payload':
                payload = ins.get_data()  # bytes
                count = len(payload) // 4
                iArr = list(struct.unpack(f'<{count}i', payload[:count*4]))

# Transformation: iArr[i] = ((iArr[i] + 256000) - i - (i+1)*173) % 256
for i in range(len(iArr)):
    iArr[i] = ((iArr[i] + 256000) - i - (i + 1) * 173) % 256

# Brainfuck-like interpreter
# Opcodes: 0=+, 1=-, 2=ptr--, 3=ptr++, 4=[, 5=], 6=output
tape = [0] * 65536
ptr = 0
pc = 0
result = ""

while pc < len(iArr):
    op = iArr[pc]
    if op == 0: tape[ptr] = (tape[ptr] + 1) & 0xFF
    elif op == 1: tape[ptr] = (tape[ptr] - 1) & 0xFF
    elif op == 2: ptr = (ptr - 1) & 0xFFFF
    elif op == 3: ptr = (ptr + 1) & 0xFFFF
    elif op == 4:
        if tape[ptr] == 0:
            depth = 1
            while depth:
                pc += 1
                if iArr[pc] == 4: depth += 1
                elif iArr[pc] == 5: depth -= 1
    elif op == 5:
        if tape[ptr] != 0:
            depth = 1
            while depth:
                pc -= 1
                if iArr[pc] == 5: depth += 1
                elif iArr[pc] == 4: depth -= 1
    elif op == 6: result += chr(tape[ptr])
    pc += 1

print(f"Path: /{result}.html")
```

**Output:**
```
Path: /48ce217fea4529a070a9d3e3c87db512b1596d413e580f7b2e1eab65f3948ab8.html
```

#### 3. Access the path and capture the flag

```bash
curl -s "https://e8072a862be3003083ebea167ef89592.ctf.hacker101.com/48ce217fea4529a070a9d3e3c87db512b1596d413e580f7b2e1eab65f3948ab8.html"
# ^FLAG^b3030312ba3221901ce36e54f2d0cba6eae2cd4b86f39f1987019d34310d2710$FLAG$
```

### Flags

- Flag 2: `b3030312ba3221901ce36e54f2d0cba6eae2cd4b86f39f1987019d34310d2710` — **Congratulations ✓**

### Technical Explanation

The app uses a Brainfuck-like interpreter embedded in the DEX to obfuscate the flag path. The `iArr` array of 557 integers is transformed by `((v + 256000) - i - (i+1)*173) % 256` before being interpreted. Opcodes 0–5 are the standard BF commands (`+-<>[]`); opcode 6 produces an output character. The result is a 64-character hexadecimal string that, with `.html`, forms the flag's path on the server.

### Lesson Learned

Writeups with hardcoded arrays (e.g., CyberNilsen) may be from older APK versions. Always extract the array from the real APK with androguard before running the algorithm.
