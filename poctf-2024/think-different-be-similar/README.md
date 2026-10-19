# Think Different, Be Similar

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2024 |
| **Category** | Reverse Engineering |
| **Difficulty** | Hard |
| **Points** | 300 |
| **Flag** | `poctf{uwsp_4b4nd0n_4ll_h0p3}` |
| **Status** | Solved |

---

## 1. Challenge Overview

A Windows .NET executable that fetches the flag from a remote server. The URL is split into Base64-encoded fragments, and the HTTP request requires specific headers. The challenge combines .NET reversing with web request reconstruction.

**Files:** `Reverse300-2.exe` (Windows .NET binary)

---

## 2. .NET Decompilation

Opened the executable in **ILSpy**. Among several distraction modules, found the relevant `fetch_flag` function in the main module (entry: `Reverse300-2 - Constructed Languages.deps.json`).

The decompiled C# code:

~~~csharp
string[] value = new string[8] {
    "aHR0cDovL24", "2c3RndC5jb2", "0vVGhpbmtEa",
    "WZmZXJlbnRC", "ZVNpbWlsYXIv", "cG9jdGYyMDI0",
    "X3JldmVyc2Uz", "MDAyLnR4dA=="
};
string s = string.Join("", value);
string url = Encoding.UTF8.GetString(Convert.FromBase64String(s));

using HttpClient client = new HttpClient();
client.DefaultRequestHeaders.Add("User-Agent", "ThinkDifferentBeSimilar");
client.DefaultRequestHeaders.Referrer = new Uri("https://www.nvstgt.com/");
~~~

---

## 3. URL Reconstruction

Concatenating and decoding the Base64 fragments:

~~~text
aHR0cDovL24 + 2c3RndC5jb2 + 0vVGhpbmtEa + WZmZXJlbnRC + ZVNpbWlsYXIv + cG9jdGYyMDI0 + X3JldmVyc2Uz + MDAyLnR4dA==
~~~

Decoded URL:

~~~text
http://nvstgt.com/ThinkDifferentBeSimilar/poctf2024_reverse3002.txt
~~~

---

## 4. Flag Retrieval

Sent a GET request with the required `User-Agent` header using Postman/curl:

~~~bash
curl -H "User-Agent: ThinkDifferentBeSimilar" \
     http://nvstgt.com/ThinkDifferentBeSimilar/poctf2024_reverse3002.txt
~~~

Response: `poctf{uwsp_4b4nd0n_4ll_h0p3}`

---

## Lessons Learned

| # | Lesson | Detail |
|---|--------|--------|
| 1 | .NET binaries decompile cleanly | ILSpy/dnSpy recover near-original source code |
| 2 | Split Base64 is a common obfuscation technique | Concatenation before decode reveals the full string |
| 3 | Custom HTTP headers can gate access | User-Agent validation is a simple access control mechanism |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID | Context |
|---|---|---|---|
| Command and Control | Application Layer Protocol: Web Protocols | T1071.001 | Flag fetched via HTTP with custom headers |
| Defense Evasion | Obfuscated Files or Information | T1027 | URL split into Base64 fragments to prevent direct extraction |
| Defense Evasion | Deobfuscate/Decode Files or Information | T1140 | Base64 decoding to reconstruct the fetch URL |

> **CWE-312:** Cleartext Storage of Sensitive Information. The flag is served as plaintext from the remote endpoint.
> **CWE-290:** Authentication Bypass by Spoofing. Access gated only by a User-Agent header, trivially spoofable.

---

## Remediation and Containment

### Technical Fixes

1. Do not gate access solely on User-Agent headers, which are client-controlled
2. Use proper authentication (API keys, tokens) for sensitive endpoints
3. If URL obfuscation is desired, use encryption rather than split Base64
4. Implement TLS for data in transit (the URL uses HTTP, not HTTPS)

### MITRE D3FEND Countermeasures

- **D3-NTA (Network Traffic Analysis):** detect requests to known flag endpoints
- **D3-FE (File Encryption):** encrypt the flag at the server endpoint
- **D3-ACL (Access Control List):** implement proper authentication, not header-based gating

### NIST CSF 2.0

- **Protect (PR.AC):** implement proper authentication for all API endpoints
- **Protect (PR.DS):** use TLS for data in transit to prevent interception
- **Detect (DE.CM):** log and alert on requests with known CTF User-Agent strings

### NIST SP 800-53 Rev. 5

- **IA-2 (Identification and Authentication):** require proper authentication for resource access
- **SC-8 (Transmission Confidentiality and Integrity):** encrypt all data in transit with TLS
- **AC-3 (Access Enforcement):** enforce access control based on validated credentials

### C2M2

- **ACCESS-3:** audit web endpoints for header-only access controls
- **THREAT-2:** include .NET decompilation in application security testing

---

Thanks guys!! (❍ᴥ❍ʋ)

---

Abandon all hope, ye who rely on User-Agent strings for security. ILSpy turns .NET binaries into readable source, and split Base64 is just a speed bump for anyone with a decoder.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

> **Reference:** Adapted from [shivang1209-dot/CTF-Writeups](https://github.com/shivang1209-dot/CTF-Writeups). Original scripts credited to the author.
