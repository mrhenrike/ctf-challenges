# Intentional Exercise — Writeup (1/1)

**Difficulty:** Easy  
**Category:** Android (APK Reverse Engineering, Hash Bypass)  
**Flags:** 1/1 (complete)  
**Platform:** Hacker101 CTF

---

## Challenge Overview

**Context:** An Android app that authenticates requests with a SHA-256 hash of a secret key concatenated with the URL path. The goal is to access a protected endpoint (`/appRoot/flagBearer`) without the app running correctly.

**What you face:** An APK that uses a custom URI scheme (`android:host="level13.hacker101.com"`) to derive the hash payload. The key is hardcoded in Java. Without replicating the exact hash calculation (key + correct path), the server rejects the request.

**Vulnerabilities exploited:**
- Hardcoded Secret Key (CWE-798) — key `s00p3rs3cr3tk3y` hardcoded in `MainActivity.java`
- Predictable Authentication Token (CWE-340) — deterministic SHA-256 with static key is forgeable
- Information Disclosure via APK Decompilation (CWE-200) — authentication logic exposed by decompilation

**What you learn:**
- Java (Dalvik) APKs can be converted to `.jar` and inspected with `jd-gui`
- `substring(28)` on the full URI is a non-obvious trick that must be reproduced faithfully
- Hash algorithms with static keys provide no real security — they are only security through obscurity
- Hardcoded keys at any layer of the app are trivially extractable

---

## Objective

Reverse engineer an Android APK to discover the secret key used to generate request hashes, then forge the correct request to obtain the flag.

---

## Setup

1. Install the APK in the Android emulator
2. Configure Burp Suite proxy
3. Observe requests

---

## Flag 0 — SHA-256 Hash Forge

**Vulnerability:** Secret key hardcoded in the APK + recoverable hash algorithm via reverse engineering.

### Step 1: Observe the protocol

With Burp intercepting, the app makes a request:
```
GET /appRoot?&hash=61f4518d844a9bd27bb971e55a23cd6cf3a9f5ef7f46285461cf6cf135918a1a
```

Server responds: "invalid request" or similar. A second endpoint `/appRoot/flagBearer` is mentioned in the response.

### Step 2: Decompile the APK

```bash
d2j-dex2jar level13.apk -o level13-dex2jar.jar
jd-gui level13-dex2jar.jar
```

Navigate to `MainActivity.java` and find the hash logic:

```java
MessageDigest messageDigest = MessageDigest.getInstance("SHA-256");
messageDigest.update("s00p3rs3cr3tk3y".getBytes(StandardCharsets.UTF_8));
messageDigest.update(str3.getBytes(StandardCharsets.UTF_8));
byte[] arrayOfByte = messageDigest.digest();
```

### Step 3: Understand the payload

The code also reveals:
```java
Uri uri = getIntent().getData();
str3 = uri.toString().substring(28);
```

With `android:host="level13.hacker101.com"`, the payload for `/appRoot/flagBearer` is:
```
"http://level13.hacker101.com/flagBearer".substring(28) = "/flagBearer"
```

### Step 4: Calculate the correct hash

```python
import hashlib
key = "s00p3rs3cr3tk3y"
payload = "/flagBearer"
h = hashlib.sha256((key + payload).encode()).hexdigest()
# = 8743a18df6861ced0b7d472b34278dc29abba81b3fa4cf836013426d6256bd5e
```

### Step 5: Send the forged request

```
GET /appRoot/flagBearer?&hash=8743a18df6861ced0b7d472b34278dc29abba81b3fa4cf836013426d6256bd5e
```

The server returns the flag.

---

## Attack Summary

```
1. APK → dex2jar → jd-gui → MainActivity.java → key s00p3rs3cr3tk3y
2. payload = "http://level13.hacker101.com/flagBearer".substring(28) = "/flagBearer"
3. SHA-256("s00p3rs3cr3tk3y/flagBearer") = 8743a18d...
4. GET /appRoot/flagBearer?&hash=8743a18d... → FLAG
```

---

## Lessons Learned

1. **Hardcoded keys in APKs** are trivially extractable via reverse engineering
2. **Security through obscurity** (hiding the endpoint) fails when the APK can be decompiled
3. **Hash algorithms are predictable**: knowing the key and algorithm, any hash can be forged
4. **Use HMAC with a dynamic per-session key** instead of a static hardcoded key

---

## MITRE ATT&CK Mapping

| Tactic | Technique | ID | Description |
|---|---|---|---|
| Credential Access | Unsecured Credentials: Credentials In Files | T1552.001 | Secret key `s00p3rs3cr3tk3y` hardcoded in `MainActivity.java` |
| Resource Development | Obtain Capabilities: Tool | T1588.002 | Using dex2jar + jd-gui for APK decompilation |
| Initial Access | Valid Accounts | T1078 | Forging authentication hash to access protected `/flagBearer` endpoint |
| Defense Evasion | Obfuscated Files or Information | T1027 | `substring(28)` trick obscuring the payload derivation |

---

## Remediation

### Technical Fixes

1. **Replace static keys with server-issued session tokens** that expire and cannot be extracted from the binary
2. **Use HMAC with a dynamic nonce/timestamp** to prevent replay and forgery attacks
3. **Implement certificate pinning** to prevent traffic interception during analysis
4. **Apply R8/ProGuard obfuscation** as defense-in-depth (never the sole protection)
5. **Server-side validation** of request origin, not just hash correctness

### OWASP Mobile Top 10 2024

| ID | Risk | Relevance |
|---|---|---|
| M1 | Improper Credential Usage | SHA-256 key hardcoded in Java source, extractable via decompilation |
| M7 | Insufficient Binary Protections | No obfuscation; key and algorithm visible in plain decompiled Java |

### D3FEND Countermeasures

| ID | Technique | Application |
|---|---|---|
| D3-DENCR | Data Encryption | TLS with certificate pinning for all API communication |
| D3-AODO | Application Developer Obfuscation | Code obfuscation to raise the cost of static analysis |
| D3-CKMS | Cryptographic Key Management | Server-side key management, no client-embedded secrets |

### NIST CSF 2.0

| Function | Category | Subcategory | Application |
|---|---|---|---|
| Protect | PR.DS | PR.DS-01 | Protect data-at-rest (keys should not be in the binary) |
| Protect | PR.AA | PR.AA-01 | Dynamic authentication instead of static hash-based auth |
| Identify | ID.AM | ID.AM-08 | Inventory all embedded secrets in mobile releases |

### NIST SP 800-53 Rev. 5

| Control | Title | Application |
|---|---|---|
| SC-12 | Cryptographic Key Establishment and Management | No hardcoded keys; use key exchange protocols |
| SC-13 | Cryptographic Protection | Use HMAC with dynamic nonces instead of bare SHA-256 |
| IA-5 | Authenticator Management | Rotate authentication secrets; never embed in client code |

---

## Final Thoughts

This challenge is a textbook example of why "security through obscurity" fails. A static key in a decompilable APK is no secret at all. The fix: server-issued ephemeral tokens and proper HMAC with nonces. When you audit mobile apps, always start with `dex2jar` + `jd-gui` and grep for "key", "secret", "password".

Thanks guys!! (❍ᴥ❍ʋ)

Found this useful? Let's connect and trade notes on mobile security:

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
