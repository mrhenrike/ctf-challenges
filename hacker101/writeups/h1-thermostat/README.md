# H1 Thermostat: Writeup (2/2)

**Difficulty:** Easy  
**Category:** Android (Traffic Interception, APK Reverse Engineering)  
**Flags:** 2/2 (complete)  
**Platform:** Hacker101 CTF

---

## Challenge Overview

**Context:** An Android smart thermostat app. The app communicates with a server via HTTP requests, sending temperature control commands. The challenge is to intercept the traffic and reverse engineer the APK to gain unauthorized access.

**What you face:** A real Android app that needs to be intercepted with a proxy (Burp Suite) and decompiled. Flag 0 is exposed in network traffic, and Flag 1 requires understanding the authentication protocol (MAC) and replicating it with a key extracted from the APK.

**Vulnerabilities exploited:**
- Transmission of sensitive data in plaintext (CWE-319): flag transmitted without encryption
- Hardcoded Secret Key (CWE-798): HMAC/MAC key hardcoded in the APK, extractable by decompilation
- Insecure Authentication Protocol: integrity check based on a static secret

**What you learn:**
- How to configure a MitM proxy (Burp Suite) in an Android emulator
- APK reverse engineering with `jadx` or `apktool` to extract constants
- MAC-based authentication protocols: how to replicate them with the correct key
- Never rely on security through hardcoded secrets: APKs are easily decompiled

---

## Objective

Analyze the traffic from an Android thermostat app and reverse engineer the APK to obtain both flags.

---

## Setup

1. Configure the Android emulator with the Burp Suite proxy
2. Install `thermostat.apk` on the emulator
3. Start the app

---

## Flag 0: Intercept POST traffic

**Vulnerability:** The flag is transmitted in plaintext in network traffic.

### Step

With the Burp Suite proxy intercepting, start the app and observe the POST requests. Flag 0 appears directly in the body of a POST request.

---

## Flag 1: APK Reverse Engineering (MAC bypass)

**Vulnerability:** The app uses a MAC calculated with a static value accessible in the source code.

### Step 1: Understand the protocol

Commands are sent as base64-encoded JSON:
```
eyJjbWQiOiJzZXRUZW1wIiwidGVtcCI6NzN9 = {"cmd":"setTemp","temp":73}
```

When attempting to modify the temperature, the server responds:
```json
{"success": false, "error": "MAC failure"}
```

### Step 2: Decompile the APK

Use `jadx` or `apktool` to decompile the APK:

```bash
jadx thermostat.apk -d thermostat_src/
```

Navigate to: `classes.dex → com → hacker101 → level11 → PayloadRequest`

### Step 3: Find Flag 1

Flag 1 is embedded in the source code of the `PayloadRequest` class, alongside the MAC generation logic.

---

## Attack Summary

```
FLAG 0: Burp Proxy → intercept app POST → flag in traffic
FLAG 1: jadx thermostat.apk → PayloadRequest.java → flag in source code
```

---

## Lessons Learned

1. **Android apps are not secure by obscurity**: the APK can be easily decompiled
2. **Secrets in source code** are trivially extractable with `jadx`/`apktool`
3. **Unencrypted network traffic** exposes sensitive data to MITM proxies
4. **MACs with static values** are bypassable after reverse engineering

---

## MITRE ATT&CK Mapping

| Tactic | Technique | ID | Description |
|---|---|---|---|
| Collection | Adversary-in-the-Middle | T1557 | Intercepting app traffic via Burp Suite proxy to capture plaintext flag |
| Credential Access | Credentials from Password Stores | T1555 | Extracting hardcoded HMAC key from decompiled APK source |
| Credential Access | Unsecured Credentials: Credentials In Files | T1552.001 | Secret key hardcoded in `PayloadRequest.java` |
| Resource Development | Obtain Capabilities: Tool | T1588.002 | Using jadx/apktool for APK reverse engineering |
| Defense Evasion | Obfuscated Files or Information | T1027 | MAC-based authentication obscuring the real secret |

---

## Remediation

### Technical Fixes

1. **Encrypt all traffic** with TLS 1.2+ and certificate pinning to prevent MITM interception
2. **Never hardcode secrets** in mobile apps; use a key exchange protocol or server-side authentication
3. **Use HMAC with dynamic per-session keys** instead of static secrets embedded in the binary
4. **Implement certificate pinning** to detect proxy interception
5. **Enable ProGuard/R8 obfuscation** as a defense-in-depth layer (not a replacement for proper key management)

### OWASP Mobile Top 10 2024

| ID | Risk | Relevance |
|---|---|---|
| M1 | Improper Credential Usage | HMAC key hardcoded in APK, extractable via decompilation |
| M5 | Insecure Communication | Flag transmitted in plaintext over HTTP without TLS |
| M8 | Security Misconfiguration | No certificate pinning, no traffic encryption enforcement |

### D3FEND Countermeasures

| ID | Technique | Application |
|---|---|---|
| D3-DENCR | Data Encryption | Encrypt all network traffic with TLS 1.2+ |
| D3-MAN | Mandatory Access Control | Server-side session tokens instead of client-side secrets |
| D3-AODO | Application Developer Obfuscation | ProGuard/R8 to hinder static analysis |

### NIST CSF 2.0

| Function | Category | Subcategory | Application |
|---|---|---|---|
| Protect | PR.DS | PR.DS-02 | Encrypt data in transit (TLS with certificate pinning) |
| Protect | PR.AA | PR.AA-01 | Use dynamic authentication tokens, not static keys |
| Detect | DE.CM | DE.CM-09 | Monitor for anomalous API usage patterns |

### NIST SP 800-53 Rev. 5

| Control | Title | Application |
|---|---|---|
| SC-8 | Transmission Confidentiality and Integrity | Mandatory TLS for all app-to-server communication |
| SC-12 | Cryptographic Key Establishment and Management | Dynamic key exchange instead of hardcoded keys |
| IA-5 | Authenticator Management | Rotate and protect authentication secrets |
| SA-15 | Development Process, Standards, and Tools | Static analysis in CI/CD to detect hardcoded secrets |

---

## Final Thoughts

Smart home devices and IoT apps often ship with the same mistakes we see in this challenge: plaintext traffic and hardcoded secrets. The attack surface is real, and the fix is straightforward: TLS everywhere and zero secrets in the binary. If you find yourself auditing Android apps, `jadx` and Burp Suite are your best friends.

Thanks guys!! (❍ᴥ❍ʋ)

If this writeup helped you understand mobile app security, share your findings with the community:

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
