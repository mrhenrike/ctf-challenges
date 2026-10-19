# Giving Up the Game

| Detail      | Value                                      |
|-------------|--------------------------------------------|
| CTF         | Pointer Overflow CTF 2024                  |
| Category    | Web                                        |
| Difficulty  | Easy                                       |
| Points      | 100                                        |
| Flag        | `poctf{uwsp_1_7H1nk_7H3r3r0_1_4m}`       |
| Status      | Solved                                     |

---

## Challenge Overview

A web challenge disguised as a loading screen for a fake game called "Space Adventure." The page runs a 300-second progress bar animation while making a background `fetch` call to `/getSprites`. The console shows a Base64 red herring, but the actual flag is returned by the API endpoint.

---

## Objective

Identify the hidden API call in the JavaScript source and retrieve the flag from the `/getSprites` endpoint.

---

## Methodology

### Step 1: Analyze the page source

The challenge page shows a fake game loading screen with a progress bar, spinning animation, and rotating tips. The JavaScript contains:

```js
fetch('/getSprites')
    .then(response => response.json())
    .then(data => {
        console.log("VGhhbmsgeW91IE1hcmlvISBCdXQgb3VyIHByaW5jZXNzIGlzIGluIGFub3RoZXIgY2FzdGxlIQ==");
    });
```

### Step 2: Investigate the console output

The Base64 string logged to the console decodes to: `Thank you Mario! But our princess is in another castle!` This is a red herring referencing the classic Super Mario Bros. message.

### Step 3: Navigate to the API endpoint

Directly accessing `/getSprites` in the browser returns a JSON response containing another Base64 string:

```
"cG9jdGZ7dXdzcF8xXzdIMW5rXzdIM3IzcjBfMV80bX0="
```

### Step 4: Decode the flag

```bash
echo "cG9jdGZ7dXdzcF8xXzdIMW5rXzdIM3IzcjBfMV80bX0=" | base64 -d
# poctf{uwsp_1_7H1nk_7H3r3r0_1_4m}
```

---

## Flag

```
poctf{uwsp_1_7H1nk_7H3r3r0_1_4m}
```

---

## Lessons Learned

| # | Lesson | Detail |
|---|--------|--------|
| 1 | Check network requests | Background fetch calls can reveal hidden endpoints |
| 2 | Red herrings are common | Console output may be a distraction from the real data |
| 3 | API endpoints matter | `/getSprites` is a non-obvious path containing the flag |
| 4 | Don't wait for animations | The 300-second loading bar is pure misdirection |

---

## MITRE ATT&CK Mapping

| Tactic          | Technique                         | ID        |
|-----------------|-----------------------------------|-----------|
| Discovery       | Application Layer Protocol        | T1071     |
| Collection      | Data from Information Repositories| T1213     |
| Defense Evasion | Obfuscated Files or Information   | T1027     |

---

## OWASP Top 10 2021 Mapping

| Category | ID    | Relevance |
|----------|-------|-----------|
| Security Misconfiguration | A05:2021 | Unprotected API endpoint leaking secrets |
| Broken Access Control     | A01:2021 | No authentication on sensitive endpoint |

---

## Remediation

### Technical Fixes
- Protect API endpoints with authentication and authorization
- Never return sensitive data from unauthenticated endpoints
- Remove debug endpoints before deploying to production

### OWASP Top 10 2021
- **A01 Broken Access Control**: require authentication for all API endpoints that return sensitive data
- **A05 Security Misconfiguration**: remove or restrict development/debug endpoints

### D3FEND Countermeasures
| Technique             | ID        |
|-----------------------|-----------|
| Application Hardening | D3-AH     |
| Network Traffic Filtering | D3-NTF |

### NIST CSF 2.0
| Function | Category                | Subcategory |
|----------|------------------------|-------------|
| Protect  | Identity Management and Access Control | PR.AA-01 |
| Protect  | Data Security          | PR.DS-01    |

### NIST SP 800-53 Rev. 5
| Control     | Description                          |
|-------------|--------------------------------------|
| AC-3        | Access Enforcement                   |
| SC-8        | Transmission Confidentiality and Integrity |

### C2M2
| Practice Area               | MIL |
|-----------------------------|-----|
| Access Management           | MIL2 |

### CWE
| ID      | Name                                     |
|---------|------------------------------------------|
| CWE-200 | Exposure of Sensitive Information to an Unauthorized Actor |
| CWE-284 | Improper Access Control                  |

---

## References

- Based on solve approach from [Jdwalli](https://github.com/Jdwalli/ctf-writeups)
- [OWASP Top 10 2021](https://owasp.org/Top10/)

---

## Closing

Thanks guys!! (❍ᴥ❍ʋ)

I think, therefore I am, and I also think you should always check the network tab in DevTools before staring at a fake loading bar for five minutes. The real game was the API we found along the way.

[![Instagram](https://img.shields.io/badge/-Instagram-E4405F?style=flat&logo=instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/-LinkedIn-0077B5?style=flat&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/-X-000000?style=flat&logo=x&logoColor=white)](https://x.com/mrhenrike)
