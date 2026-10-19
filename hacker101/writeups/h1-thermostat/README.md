# H1 Thermostat — Writeup (2/2)

**Difficulty:** Easy  
**Category:** Android (Traffic Interception, APK Reverse Engineering)  
**Flags:** 2/2 (complete)  
**Platform:** Hacker101 CTF

---

## Challenge Overview

**Context:** An Android smart thermostat app. The app communicates with a server via HTTP requests, sending temperature control commands. The challenge is to intercept the traffic and reverse engineer the APK to gain unauthorized access.

**What you face:** A real Android app that needs to be intercepted with a proxy (Burp Suite) and decompiled. Flag 0 is exposed in network traffic, and Flag 1 requires understanding the authentication protocol (MAC) and replicating it with a key extracted from the APK.

**Vulnerabilities exploited:**
- Transmission of sensitive data in plaintext (CWE-319) — flag transmitted without encryption
- Hardcoded Secret Key (CWE-798) — HMAC/MAC key hardcoded in the APK, extractable by decompilation
- Insecure Authentication Protocol — integrity check based on a static secret

**What you learn:**
- How to configure a MitM proxy (Burp Suite) in an Android emulator
- APK reverse engineering with `jadx` or `apktool` to extract constants
- MAC-based authentication protocols: how to replicate them with the correct key
- Never rely on security through hardcoded secrets — APKs are easily decompiled

---

## Objective

Analyze the traffic from an Android thermostat app and reverse engineer the APK to obtain both flags.

---

## Setup

1. Configure the Android emulator with the Burp Suite proxy
2. Install `thermostat.apk` on the emulator
3. Start the app

---

## Flag 0 — Intercept POST traffic

**Vulnerability:** The flag is transmitted in plaintext in network traffic.

### Step

With the Burp Suite proxy intercepting, start the app and observe the POST requests. Flag 0 appears directly in the body of a POST request.

---

## Flag 1 — APK Reverse Engineering (MAC bypass)

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
