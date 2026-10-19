# A Little Something to Get You Started: Writeup (1/1)

**Difficulty:** Trivial  
**Category:** Web  
**Flags:** 1/1 (complete)  
**Platform:** Hacker101 CTF

---

## Challenge Overview

- **Name:** A little something to get you started
- **Difficulty:** Trivial
- **Category:** Web
- **Flags:** 1/1
- **Instance URL:** `https://962347ed4d68a1af81a474eb97abede0.ctf.hacker101.com`

---

## Objective

Find the flag hidden somewhere in the challenge page resources. Flags use the format `^FLAG^<hex>$FLAG$`.

---

## Reconnaissance

### Index Page

Accessing `GET /`:

```html
<!doctype html>
<html>
    <head>
        <style>
            body {
                background-image: url("background.png");
            }
        </style>
    </head>
    <body>
        <p>Welcome to level 0.  Enjoy your stay.</p>
    </body>
</html>
```

**Observations:**
- Extremely simple page with the text "Welcome to level 0. Enjoy your stay."
- Reference to a `background.png` file as the background image

### How to Find the Instance URL

Hacker101 CTF uses a polling mechanism to provision instances:
1. `POST /ctf/start/1` → returns HTML with JavaScript that calls `/ctf/activate_level/1`
2. `GET /ctf/activate_level/1` → returns JSON: `{"url": "https://<hash>.ctf.hacker101.com", "status_code": 200}`

```bash
curl -s -b cookies.txt "https://ctf.hacker101.com/ctf/activate_level/1"
# {"url":"https://962347ed4d68a1af81a474eb97abede0.ctf.hacker101.com","status_code":200}
```

### Resource Analysis

- `GET /robots.txt` → 404 Not Found
- `GET /background.png` → suspicious response (small file, 76 bytes)

```bash
file /tmp/bg.png
# /tmp/bg.png: ASCII text, with no line terminators
```

The `background.png` file is actually a **text file disguised as a PNG**!

---

## Vulnerability

**Information Disclosure via Misnamed File**: The flag is stored in a file named `background.png` which, despite its extension, is a plain ASCII text file. The server serves it without proper Content-Type validation. The flag is fully exposed when the resource is requested.

**Technique:** Source code review / asset inspection.

---

## Exploit

### Step 1: Access and inspect the page

```bash
curl -s "https://962347ed4d68a1af81a474eb97abede0.ctf.hacker101.com/"
```

### Step 2: Download background.png and read its contents

```bash
curl -s "https://962347ed4d68a1af81a474eb97abede0.ctf.hacker101.com/background.png" -o bg.png
strings bg.png
```

**Output:**
```
^FLAG^9b2fb480a72f7fc132b30ca45a812a0ff0c805360cd1f047bac5995a3ec30d1a$FLAG$
```

### Step 3: Submit the flag

```bash
curl -s -X POST \
  -b cookies.txt \
  -H "Referer: https://ctf.hacker101.com/ctf/submit_flag" \
  --data-urlencode "authenticity_token=<CSRF_TOKEN>" \
  --data-urlencode "flag=9b2fb480a72f7fc132b30ca45a812a0ff0c805360cd1f047bac5995a3ec30d1a" \
  "https://ctf.hacker101.com/ctf/check_flag"
```

---

## Flags

| # | Flag | Status |
|---|------|--------|
| 1 | `^FLAG^9b2fb480a72f7fc132b30ca45a812a0ff0c805360cd1f047bac5995a3ec30d1a$FLAG$` | ✅ Accepted |

---

## Lessons Learned

1. **Always inspect all page resources**: Images, CSS, and JS files can contain sensitive information.
2. **Do not trust file extensions**: A `.png` file can be plain text. Use `file` or `strings` to verify the actual content.
3. **Hacker101 instance mechanism**: The `/ctf/activate_level/:id` endpoint returns the real instance URL via JSON polling.
4. **Source code review**: Even in "trivial" challenges, reviewing the HTML source can reveal references to files containing sensitive data.

---

## Timeline

- **Reconnaissance:** GET on the main page, HTML source review
- **Discovery:** Identified `background.png` referenced in the CSS tag
- **Exploitation:** Downloaded and read the file with `strings`
- **Submission:** Flag submitted and accepted, 1/26 points

---

## MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID |
|---|---|---|
| Reconnaissance | Active Scanning: Vulnerability Scanning | T1595.002 |
| Initial Access | Exploit Public-Facing Application | T1190 |
| Collection | Data from Information Repositories | T1213 |
| Discovery | File and Directory Discovery | T1083 |

## Remediation and Containment

### Technical Fixes

1. Never serve sensitive data through files accessible via direct URL, even if they have misleading extensions
2. Implement proper access controls on all static assets
3. Remove debug or placeholder files from production deployments
4. Use a Content Security Policy (CSP) header to restrict resource loading

### OWASP Top 10 2021

- **A01:2021 Broken Access Control**: sensitive data exposed through a publicly accessible file with no authentication

### MITRE D3FEND Countermeasures

- **D3-AL (Authorization Limiting)**: restrict access to static resources based on authentication status
- **D3-FA (File Analysis)**: scan deployed assets for unintended sensitive content before going live

### NIST CSF 2.0

- **Protect (PR.DS-1)**: data-at-rest is protected through access controls
- **Detect (DE.CM-1)**: the network is monitored to detect potential cybersecurity events

### NIST SP 800-53 Rev. 5

- **AC-3 Access Enforcement**: enforce approved authorizations for logical access to information
- **CM-7 Least Functionality**: configure systems to provide only essential capabilities
- **SC-28 Protection of Information at Rest**: protect the confidentiality of information at rest

---

Thanks guys!! (❍ᴥ❍ʋ)

---

Sometimes the simplest challenges teach the most important lesson: always check every resource the page loads. A "background image" that turns out to be plain text is a classic reminder that file extensions mean nothing without validation.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
