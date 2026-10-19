# Grayhatcon CTF — Writeup

**Difficulty:** Moderate  
**Category:** Web  
**Platform:** Hacker101 CTF  
**Progress:** ✅ **4/4 flags** — complete (2026-10-01)  
**Instance:** `https://3f2ccba44281099039778561c3b1d116.ctf.hacker101.com`  

---

## Challenge Overview

**Context:** A marketplace called "HackerBay" where someone has listed HackerOne usernames and passwords for sale. The narrative goal is to hack in and delete the listing before it gets purchased. The application has a public area, user accounts, subaccounts, auctions, and an admin panel protected by `.htaccess` with an IP whitelist.

**What you face:** Four completely distinct attack vectors: IP bypass via header, account takeover via predictable hash, IDOR on another user's subaccounts, and SQL injection in the admin panel to retrieve credentials and delete the listing.

**Vulnerabilities exploited:**
- IP Spoofing via `X-Forwarded-For` (CWE-290) — `.htaccess` trusts the header for admin access
- Insecure Direct Object Reference / IDOR (CWE-639) — another user's `owner_hash` used in subaccount registration
- Account Takeover via predictable hash — `account_hash` obtained via `POST /reset` and reused in `POST /register`
- SQL Injection (CWE-89) — `/dashboard/auctions/questions?id=` to extract admin credentials
- Broken Authorization — `enable_toggle` accepts another user's subaccount hash

**What you learn:**
- `X-Forwarded-For` must never be trusted for access control — any client can forge it
- Account reset hashes must not be reusable for creating new accounts
- IDOR in subaccount functionality (`enable_toggle`) is as critical as in primary resources
- SQLi on ID parameters allows credential extraction from internal tables via UNION
- IP-based access restriction in `.htaccess` without server-side validation is trivially bypassable

---

## Application Overview

**HackerBay** — a marketplace where someone listed HackerOne usernames/passwords. The goal is to hack and delete the listing before it's purchased.

Application structure:
- `/` — main page  
- `/register` — create account  
- `/login` — authenticate  
- `/dashboard` — logged-in user panel  
- `/s3cr3t-4dm1n/` — admin directory (restricted by `.htaccess`)  
- `/s3cr3t-4dm1n/.htaccess` — allows direct reading  

---

## Flag 1 — IP Restriction Bypass via .htaccess ✅

### Recon
- `GET /robots.txt` → `Disallow: s3cr3t-4dm1n/`
- Direct access to `/s3cr3t-4dm1n/` → 403 Forbidden
- `GET /s3cr3t-4dm1n/.htaccess` (direct reading allowed):
  ```
  Order Deny,Allow
  Deny from all
  Allow from 8.8.8.8
  Allow from 8.8.4.4
  ```

### Exploitation
```bash
curl "https://INSTANCE/s3cr3t-4dm1n/" -H "X-Forwarded-For: 8.8.8.8"
```
→ Flag displayed on the admin login page.

---

## Flag 2 — Account Takeover via `owner_hash` ✅

### Recon
- `POST /reset` with `username=hunter2` → hidden field `account_hash=cf505baebbaf25a0a4c63eb93331eb36`

### Exploitation
In the registration request, use **`owner_hash`** (not `account_hash`):
```
POST /register
owner_hash=cf505baebbaf25a0a4c63eb93331eb36&new_username=subatk&new_password=pass
```
Login as `subatk` → `/awaiting-enable` displays Flag 2.

---

## Flag 3 — IDOR enable_toggle on subuser ✅

**Flag:** `^FLAG^cdacb979d03096dcedf778248072812c161fef2f468bd7b0ce98323adb80c840$FLAG$`  

### Technique
IDOR on the subusers endpoint: `enable_toggle=enable` accepts another user's subuser `hash` and enables it.

### Step by step

1. Create attacker account + subuser of hunter2 (Flag 2 flow).
2. Note the **Account Hash** of the created subuser (cookie `userhash` after login).
3. Separate account with enabled subusers.
4. `POST /dashboard/subusers` with `userhash=cf505bae...` (hunter2):
   ```
   hash=<hash_of_hunter2_sub>&enable_toggle=enable
   ```
5. Login as enabled hunter2 sub → Flag 3 in the dashboard.

---

## Flag 4 — SQLi + delete auction via admin ✅

**Flag:** `^FLAG^07691fb71ac55123ec4fca32a0060b47cec41a6f2c7f0f1f9ad870a6ece3a8a9$FLAG$`  

### Step by step

1. Logged in as enabled hunter2 sub → **Your Auctions** → note the listing hash.
2. SQLi on `GET /dashboard/auctions/questions?id=` (union-based) → admin credentials.
3. Credentials found: `h4ckerbayadmin` / `auction$rFun!`
4. `POST /s3cr3t-4dm1n/` with `X-Forwarded-For: 8.8.8.8` → `admin-token` cookie.
5. `POST /s3cr3t-4dm1n/` with `auction_hash=<hash>&action=delete` → Flag 4.

**Ref:** https://onealmond.github.io/ctf/hacker101-ctf/grayhatcon.html

---

## MITRE ATT&CK Mapping

| ID | Technique | Tactic | How it was used |
|----|-----------|--------|----------------|
| T1190 | Exploit Public-Facing Application | Initial Access | IP bypass via X-Forwarded-For to access admin panel |
| T1078.001 | Valid Accounts: Default Accounts | Persistence | Account takeover via predictable reset hash reused in registration |
| T1087.001 | Account Discovery: Local Account | Discovery | Enumerated subaccounts and owner hashes via IDOR |
| T1068 | Exploitation for Privilege Escalation | Privilege Escalation | enable_toggle IDOR to activate unauthorized subaccounts |
| T1059.001 | Command and Scripting Interpreter | Execution | SQL injection on auction questions endpoint for credential extraction |

## Remediation and Containment

### Technical Fixes

1. **X-Forwarded-For bypass:** Never trust client headers for access control; validate source IP at network/proxy level
2. **Account takeover:** Reset tokens must be one-time-use, time-limited, and not reusable across endpoints
3. **IDOR on enable_toggle:** Enforce ownership validation on every subaccount operation
4. **SQL Injection:** Use parameterized queries on all ID parameters

### OWASP Top 10 2021

| ID | Category | Relevance |
|----|----------|-----------|
| A01:2021 | Broken Access Control | IDOR on subaccounts; IP bypass via forged header; enable_toggle without ownership check |
| A03:2021 | Injection | SQL injection on `/dashboard/auctions/questions?id=` for credential extraction |
| A07:2021 | Identification and Authentication Failures | Predictable reset hash reused for account creation |

### MITRE D3FEND Countermeasures

| ID | Technique | Application |
|----|-----------|-------------|
| D3-NTA | Network Traffic Analysis | Detect X-Forwarded-For spoofing at the reverse proxy layer |
| D3-SPP | Strong Password Policy | Use cryptographically random, one-time reset tokens |
| D3-ACL | Access Control List | Enforce per-object ownership checks on subaccount operations |

### NIST CSF 2.0

| Function | Category | Application |
|----------|----------|-------------|
| PR (Protect) | PR.AC | Server-side IP validation; per-object authorization |
| PR (Protect) | PR.AT | Developer training on IDOR, SQLi and header trust boundaries |
| DE (Detect) | DE.CM | Monitor for forged headers and unusual subaccount activity |
| RS (Respond) | RS.AN | Correlate IP spoofing attempts with admin panel access logs |

### NIST SP 800-53 Rev. 5

| Control | Title | Application |
|---------|-------|-------------|
| AC-3 | Access Enforcement | Per-object authorization on all CRUD operations |
| IA-5 | Authenticator Management | Cryptographically random, time-limited reset tokens |
| SC-23 | Session Authenticity | Validate session origin; do not trust X-Forwarded-For for auth |
| SI-10 | Information Input Validation | Parameterized queries on all SQL endpoints |

### C2M2

| Domain | Practice | MIL | Application |
|--------|----------|-----|-------------|
| ACCESS | Access Control Management | MIL-2 | Enforce BOLA on subaccounts; validate IP at proxy layer |
| THREAT | Threat and Vulnerability Management | MIL-2 | Regular SQLi and IDOR testing on all user-facing endpoints |

---

## Tools

- `bash scripts/ctf-session.sh activate 38` — retrieve instance URL
- `bash scripts/ctf-session.sh submit <flag>` — submit flag
- `curl` + manual POST parameter manipulation

---

## Final Thoughts

Thanks guys!! (❍ᴥ❍ʋ)

---

GrayHatCon is a masterclass in chaining: IP spoofing, predictable hashes, IDOR and SQL injection, four completely distinct attack vectors in one application. Each vulnerability alone would be moderate, but chained together they give you full admin access and database control. This challenge reinforces why defense in depth matters: a single control failure should never cascade into total compromise.

Let's connect and talk more about web security:

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
