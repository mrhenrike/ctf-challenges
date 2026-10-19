# Rend Asunder — Writeup (IN PROGRESS: 1/3)

**Difficulty:** Expert  
**Category:** Native (DOM XSS + iframe escape + RCE)  
**Flags:** 1/3 (Flag 0 captured; Flags 1 and 2 require Chrome 67 CVE exploitation)  
**Challenge ID:** 17  
**Updated:** 2026-10-11

## Challenge Overview

**Context:** A server accepts a JavaScript script via POST and executes it in a Headless Chrome 67.0.3396.79 (Puppeteer). The result is a screenshot of the rendered page. The architecture is deliberately complex: Chrome opens a `data:` URL (null origin) that embeds an `<iframe>` pointing to `http://localhost/TOKEN`, and the script runs inside that iframe.

**What you face:**
- Flag 0: flag embedded in a `<noscript>` tag in the iframe DOM
- Flag 1: the URL/body of the parent (`data:` URL) contains something — SOP null-origin blocks direct access
- Flag 2: requires RCE on the server (not in the browser) — Chrome 67 has exploitable CVEs

**Vulnerabilities exploited:**
- DOM Inspection (Flag 0) — `getElementsByTagName('noscript')[0].innerHTML`
- SOP null-origin bypass (Flag 1) — iframe escape to access the `data:` URL parent context
- RCE via Chrome/V8 exploit (Flag 2) — CVE-2018-17462 or CVE-2018-17463 (Chrome 67 specific)

**What you learn:**
- How headless browsers are used as sandboxes in CTFs
- Same-Origin Policy with `data:` URLs — origin is `null`, isolated from everything
- `<noscript>` as a data storage vector in headless environments
- Chrome 67 is deliberately outdated — specific CVEs are the intended attack vector
- Browser exploits in CTF: the difference between "trying everything" and "researching exact version CVEs"

**Current status:** 1/3 — Flag 1 and Flag 2 require Chrome 67 CVEs (under investigation)

---

## Objective

Exploit a JS sandbox environment, escape the iframe, and execute RCE on the server.

## Prerequisites

- Active instance (start via CTF after stopping Encrypted Pastebin)
- Hacker101 VPN active

## Challenge Architecture (confirmed)

```
Headless Chrome 67.0.3396.79 (Puppeteer) opens data: URL as top
  └── data: URL (origin="null") contains <iframe src="http://localhost/TOKEN">
       ├── <noscript>FLAG0_VALUE</noscript>  ← flag hidden in DOM
       └── <script>USER_SCRIPT_HERE</script> ← our code executes here
```

- The headless browser takes a screenshot immediately when the synchronous script finishes
- Async `setTimeout()` and `fetch()` do NOT appear in the screenshot
- HTML injection works: `</script><div>TEXT</div><script>` appears in the screenshot
- Synchronous XHR (`xhr.open('GET', url, false)`) works and appears in the screenshot
- Bot User-Agent: `HeadlessChrome/67.0.3396.79`

---

## Flag 0 — Sandbox DOM (noscript)

**Status: CAPTURED**  
**Value:** `3a8277c042c0a9d49844f8e5b0c705d00c456beb054873747841bde33c858bca`

### Payload

```javascript
document.write(document.getElementsByTagName('noscript')[0].innerHTML)
```

### Why it works

The `<noscript>` tag is rendered by the HTML parser before script execution, so its content is in the DOM even with JS enabled. `innerHTML` reads the hidden content.

---

## Flag 1 — Iframe Escape (parent frame)

**Status: UNSOLVED — blocked by SOP**

### Blocker context

The parent is a `data:` URL with origin="null" (null opaque origin). The iframe has origin `http://localhost`. This creates a cross-origin relationship where no direct access is allowed by Chrome 67.

### Techniques tested and blocked (by Same-Origin Policy)

| Technique | Result |
|---|---|
| `top.document.body.innerHTML` | SecurityError |
| `top.location.href` | SecurityError |
| `top.location.hash` | SecurityError (Chrome 67 blocks even cross-origin hash) |
| `top.location.search` | SecurityError |
| `window.frameElement` | null (cross-origin) |
| `document.referrer` | empty string |
| `window.name` / `top.name` | SecurityError |
| `top.frames[0].location.href` | SecurityError |
| `MutationObserver` on parent | SecurityError |
| `Object.getOwnPropertyNames(top)` | only safelisted properties |

### Accessible top properties (safelisted by spec — NO flag)

```javascript
// Cross-origin accessible (but contain no flag):
top.window, top.self, top.location (set-only), top.closed,
top.frames, top.length, top.top, top.opener, top.parent,
top.close, top.focus, top.blur, top.postMessage
```

### Additional techniques tested

- **postMessage**: top has no message listener, no response
- **sub-iframe with data: URL**: timing — screenshot taken before async response
- **Synchronous XHR to root**: returns only an HTML form, no flag
- **Performance API**: `performance.getEntries()` — 0 resources (clean sandbox)
- **Puppeteer exposeFunction**: no custom functions exposed on window
- **`top.frames[0] === window`**: TRUE — we are the only child frame

### Additional techniques tested (session 23 — 2026-10-11)

| Technique | Result |
|---|---|
| iframe `outerHTML` via pixel channel | Only FLAG 0 in noscript |
| Cookies, localStorage, sessionStorage (Puppeteer) | All empty |
| `navigator.webdriver` | `true` — confirms Puppeteer, no flag |
| iframe `window.name` | Empty |
| PNG metadata chunks (tEXt, iTXt) | None — only IHDR+IDAT+IEND |
| postMessage to parent with synchronous polling | Parent does not respond |
| `window.parent.location = 'javascript:...'` | Silently blocked in Chrome 67 |
| `window.parent.location = 'http://localhost/'` | Navigates parent → Puppeteer timeout (PANDA GIF) |
| Pixel analysis of data: URL border | Only gray antialiasing from iframe |
| Server-added PNG watermark | None |
| Non-standard window properties | Only standard WebKit APIs |
| Additional paths: /flag1, /flag_1, /rendered, /output, etc. | All 404 |

### Pixel exfiltration channel (discovered in session 23)

A precise communication channel between the Puppeteer script and the external browser was developed:

```javascript
// Encode string as binary pixel blocks (3px/bit)
// Each char = 8 bits = 8 blocks of 3px
// 256 bits per line = 32 chars, with iframe offset (x+10, y+10)
function encodeLine(data, yOffset) {
    var bits = [];
    for (var i = 0; i < data.length; i++) {
        var c = data.charCodeAt(i);
        for (var b = 7; b >= 0; b--) bits.push((c >> b) & 1);
    }
    var html = '<div style="position:fixed;top:0;left:0;width:800px;height:60px;background:lime">';
    for (var i = 0; i < bits.length && i < 256; i++) {
        html += '<div style="position:absolute;left:' + (i*3) + 'px;top:' + yOffset + 'px;width:3px;height:50px;background:' + (bits[i] ? 'black' : 'white') + '"></div>';
    }
    return html + '</div>';
}
document.write(encodeLine(data.substring(0,32), 5) + encodeLine(data.substring(32,64), 50));
```

Browser decoding:
```javascript
// iframe offset in screenshot: x+10, y+10
function decodeLine(ctx, y) {
    const bits = [];
    for (let i = 0; i < 256; i++) {
        const px = ctx.getImageData(10 + i*3 + 1, 10 + y + 15, 1, 1).data;
        bits.push(((px[0]+px[1]+px[2])/3) < 128 ? 1 : 0);
    }
    const chars = [];
    for (let i = 0; i < bits.length; i += 8) {
        let byte = 0;
        for (let b = 0; b < 8; b++) byte = (byte << 1) | bits[i + b];
        if (byte === 0) break;
        chars.push(String.fromCharCode(byte));
    }
    return chars.join('');
}
```

### Definitive conclusion for FLAG 1

FLAG 1 is not accessible via iframe JavaScript without a SOP bypass. The parent data: URL contains the flag, but Chrome 67 blocks all cross-origin access from iframe(http:) to parent(data:null). The only confirmed vector (per David Trapp 2025) is to use RCE to read the DOM/file from the server.

### Hypothesis for next session

- CVE-2018-17463 (V8 type confusion → arbitrary code execution): jhalon findOverlappingProperties FAILED (100k iters, Chrome 67) — try PoC with 8 props or different structure
- CVE-2018-17462 (AppCache SOP bypass — Chrome < 70)
- David Trapp (2025): "obtained FLAG 1 via the same method as FLAG 2" → RCE first

### Additional techniques tested (session 24 — 2026-10-11)

| Technique | Result |
|---|---|
| `findOverlappingProperties` (10k iters) | "no overlap" — Chrome 67 has different layout |
| `findOverlappingProperties` (100k iters) | same — jhalon PoC incompatible with V8 6.7 |
| Parent border pixel analysis (10px) | Only white background — no visible text |
| Internal endpoint probing (~30 paths) | Only `/` returns 200, everything else 404 |
| `location.ancestorOrigins[0]` | `"null"` — does not leak data: URL |

---

## Flag 2 — RCE

**Status: UNSOLVED — vector unknown**

**Hint:** "You need RCE here. No other way to put it!"

### Context

Script execution occurs in the **browser** (HeadlessChrome), not in the Node.js server. Puppeteer processes and renders the JS in the browser context, not the Node.js context.

### Techniques tested and blocked

| Technique | Result |
|---|---|
| `process`, `require` | undefined (browser context) |
| `[].constructor.constructor("return process")()` | executes in browser, `process` undefined |
| `file:///flag` via XHR | "Failed to fetch" (blocked) |
| `chrome://version` via XHR | blocked |
| CDP via port 9222/9229 | ports closed |
| SSTI in script field | no template engine identified |
| Source code endpoints (app.py, main.py, index.js...) | all 404 |
| `nginx_status`, `server-status` | 404 |
| Internal ports (3000, 8080, 5432, 6379, 3306...) | all closed |

### Session 20 investigation — all exhausted

- ffuf with 72 paths: no new endpoint discovered (all 404)
- Synchronous XHR to `/flag`, `/flag1`, `/flag2`, `/secret`, `/admin`, `/env`, `/config`, `/debug`, `/proc/self/environ`, `/app/*`, `/home/flag`, `/var/flag`: all 404
- Cookies, localStorage, sessionStorage: all empty
- Non-standard window properties: only standard webkit APIs (`webkitRequestFileSystem`, `webkitResolveLocalFileSystemURL`, `openDatabase`)
- Complete HTML of `/`: simple form + `<img src="image">`, no hidden flags

**Session 24 conclusion**: jhalon's `findOverlappingProperties` (CVE-2018-17463) with 32 properties, Object.defineProperty and 100k iterations finds no overlap in Chrome 67.0.3396.79 (V8 6.7). The type confusion logic exists in V8, but the memory layout in Chrome 67 differs from Chrome 69+ where the PoC was developed. Next step: try with fewer properties (8) or a different PoC.

---

## Reproduction Steps

### Setup

```bash
# 1. Get token
TOKEN=$(cat ~/sec-projects/token-challsec4us.txt | tr -d '\n')

# 2. Start challenge 17
curl -s "https://ctf.hacker101.com/ctf/start/17" \
  -H "Cookie: session=..." \
  -H "X-CSRF-Token: ..." \
  -X POST

# Result: instance URL as https://HASH.ctf.hacker101.com
REND_URL="https://HASH.ctf.hacker101.com"
```

### Flag 0 (working)

```bash
# POST via saveScript endpoint
curl -s "$REND_URL/saveScript" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0" \
  -H "Referer: $REND_URL/" \
  --data-urlencode "script=document.write(document.getElementsByTagName('noscript')[0].innerHTML)" \
  -L -o /dev/null

# Wait for processing
sleep 8

# Get screenshot and extract text
curl -s "$REND_URL/image" -o /tmp/rend.png
tesseract /tmp/rend.png stdout 2>/dev/null
```

---

## Lessons Learned

1. **`<noscript>` doesn't hide from JS**: content is accessible via `innerHTML` even with JS enabled
2. **data: URL as parent creates null-origin**: Chrome 67 treats two null-origins as cross-origin — no SOP access
3. **Headless Chrome timing**: screenshot is synchronous; only synchronous code appears
4. **Synchronous XHR is required**: `xhr.open('GET', url, false)` for data in screenshots
5. **HTML injection via `</script>`**: closing the `<script>` tag injects visible HTML
6. **Chrome 67 is deliberately outdated**: intentional for exploitable CVEs
7. **Pixel exfiltration channel**: 3px black/white blocks can transmit binary data from Puppeteer with 100% accuracy (no antialiasing at extreme values 0/255)
8. **`window.parent.location = 'javascript:...'`**: silently blocked in Chrome 67 from cross-origin iframe to parent
9. **`window.parent.location = 'http://...'`**: navigates the parent frame, destroys the iframe, causes Puppeteer timeout
10. **postMessage to parent (data:)**: no pre-configured listener; parent does not respond

---

## MITRE ATT&CK Mapping

| Tactic | Technique | ID | Description |
|---|---|---|---|
| Execution | Command and Scripting Interpreter: JavaScript | T1059.007 | Script injection into headless Chrome sandbox |
| Initial Access | Exploitation for Client Execution | T1203 | Targeting Chrome 67 CVEs for sandbox escape and RCE |
| Collection | Data from Information Repositories | T1213 | Extracting flag from `<noscript>` DOM element |
| Defense Evasion | Exploitation for Defense Evasion | T1211 | SOP bypass via browser vulnerability (null origin) |
| Lateral Movement | Exploitation of Remote Services | T1210 | Chrome 67 V8 type confusion (CVE-2018-17463) for cross-context access |

---

## Remediation

### Technical Fixes

1. **Keep browsers updated**: Chrome 67 has known CVEs (CVE-2018-17462, CVE-2018-17463) that enable RCE
2. **Use sandboxed execution environments** (gVisor, Firecracker) instead of relying on browser isolation alone
3. **Never store sensitive data in `<noscript>` tags**: they are accessible via `innerHTML` even with JS enabled
4. **Enforce Content Security Policy (CSP)** to restrict script execution sources
5. **Avoid `data:` URLs as parents**: their null origin creates unpredictable SOP behavior

### OWASP Top 10 2021

| ID | Risk | Relevance |
|---|---|---|
| A05 | Security Misconfiguration | Outdated Chrome 67 with known CVEs used as sandbox |
| A06 | Vulnerable and Outdated Components | Deliberately outdated browser version with exploitable V8 engine |

### D3FEND Countermeasures

| ID | Technique | Application |
|---|---|---|
| D3-PSA | Process Sandboxing | Use kernel-level sandboxing (gVisor) beyond browser sandbox |
| D3-SWU | Software Update | Keep headless browser at latest stable version |
| D3-CSP | Content Security Policy | Restrict script sources and prevent inline script injection |

### NIST CSF 2.0

| Function | Category | Subcategory | Application |
|---|---|---|---|
| Protect | PR.PS | PR.PS-01 | Patch management for all software components (browsers) |
| Protect | PR.DS | PR.DS-01 | Do not store secrets in client-accessible DOM elements |
| Detect | DE.CM | DE.CM-09 | Monitor for exploitation attempts against known CVEs |

### NIST SP 800-53 Rev. 5

| Control | Title | Application |
|---|---|---|
| SI-2 | Flaw Remediation | Patch Chrome to latest version, eliminating CVE-2018-17462/17463 |
| SC-39 | Process Isolation | Kernel-level process isolation for script execution sandboxes |
| CM-11 | User-Installed Software | Control and audit browser versions in production environments |

---

## Final Thoughts

Rend Asunder is a beast. Flag 0 teaches that `<noscript>` is not a hiding place; Flags 1 and 2 demand actual browser exploitation against Chrome 67 CVEs. The pixel exfiltration channel developed during this challenge (3px binary blocks with 100% accuracy) was a creative detour, even if it did not unlock the remaining flags. The lesson: when the hint says "you need RCE," believe it and research the exact browser version's CVE history.

Thanks guys!! (❍ᴥ❍ʋ)

Browser exploitation is a rabbit hole worth exploring. If you are tackling Chrome CVEs or headless sandbox escapes, reach out:

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
