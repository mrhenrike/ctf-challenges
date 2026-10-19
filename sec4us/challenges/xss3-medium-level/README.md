# XSS3: Medium Level

> **Platform:** SEC4US CTF Lab | **Category:** Web: XSS | **Points:** Dynamic

## Overview

Cross-site scripting challenge with moderate input filtering that requires encoding or alternative injection techniques to bypass.

---

## Approach

**Technique:** XSS with Input Filtering Bypass

### Reconnaissance

Analyze the web application's input handling and identify where user input is reflected in the page.

### Exploitation

1. **Filter analysis:** Test common XSS payloads to understand the filtering mechanism
2. **Bypass identification:** The filter blocks basic `<script>` tags but may miss:
   - Case variation: `<ScRiPt>`
   - Event handlers: `<img src=x onerror=alert(1)>`
   - Encoding: HTML entities, URL encoding, double encoding
   - Alternative tags: `<svg onload=...>`, `<body onload=...>`
3. **Payload crafting:** Construct a payload that bypasses the specific filter implementation
4. **Flag exfiltration:** Use the XSS to read the flag from the DOM or redirect to a controlled server with the cookie/flag

### Tools Used

Burp Suite, browser, XSS payload lists

---

## Security Frameworks

### MITRE ATT&CK

| Technique | Description |
|-----------|-------------|
| T1059.007 | JavaScript |

### CWE

| ID | Description |
|----|-------------|
| CWE-79 | Improper Neutralization of Input During Web Page Generation |

---

## Author

**Andre Henrike** (@mrhenrike)

Filters are speed bumps, not walls. A creative attacker always finds the gap. Thanks guys!! (❍ᴥ❍ʋ)

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

*For educational purposes only. Do not use any technique shown here against systems you do not own or have explicit permission to test.*
