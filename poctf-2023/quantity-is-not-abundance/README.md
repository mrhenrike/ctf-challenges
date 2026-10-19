# Quantity is Not Abundance

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2023 |
| **Category** | Web Exploitation |
| **Difficulty** | Hard |
| **Points** | 300 |
| **Flag** | `poctf{uwsp_qu4n717y_15_n07_48und4nc3}` |
| **Status** | Solved |

---

## 1. Challenge Overview

A web application with a hidden file at `/.secret/flag.txt`. Direct access returns a `403 Forbidden` response, but the server-side access control has a bypass that allows file retrieval through request header manipulation.

---

## 2. Initial Reconnaissance

Browsing the application and examining the page source reveals a reference to `/.secret/flag.txt`. Attempting to access it directly:

~~~bash
curl -v https://<target>/.secret/flag.txt
~~~

**Response:** `403 Forbidden`

The server blocks direct access. However, the restriction appears to be based on request headers rather than proper filesystem permissions.

---

## 3. Bypassing the Access Control

Testing various header manipulations to bypass the 403 restriction:

~~~bash
curl -H "Referer: https://<target>/" https://<target>/.secret/flag.txt
~~~

Alternatively, using `wget` which sets different default headers:

~~~bash
wget https://<target>/.secret/flag.txt
~~~

The download succeeds because the server's access control checks for specific request patterns rather than implementing proper authentication. The `Referer` header or the different `User-Agent` from wget satisfies the server's weak validation.

---

## 4. Extracting the Flag

Reading the downloaded file:

~~~text
poctf{uwsp_qu4n717y_15_n07_48und4nc3}
~~~

---

## 5. Attack Path Summary

~~~text
Target web application
    |
Discover /.secret/flag.txt reference
    |
403 Forbidden on direct access
    |
Bypass via Referer header / wget
    |
FLAG: poctf{uwsp_qu4n717y_15_n07_48und4nc3}
~~~

---

## 6. Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|--------------|
| 1 | Header-based access control is unreliable | Request headers are fully client-controlled and trivially spoofable | Never rely on Referer, User-Agent, or custom headers as sole access controls |
| 2 | 403 does not mean secure | A 403 may just be a suggestion if the backend check is superficial | Always test 403 responses with varied request methods, headers, and paths |
| 3 | Hidden paths in source code are a common finding | Developers frequently reference restricted paths in client-side code | Source review, JavaScript analysis, and directory brute-forcing are standard recon steps |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Initial Access | TA0001 | Exploit Public-Facing Application | T1190 |
| Defense Evasion | TA0005 | Indicator Removal: File Deletion | T1070.004 |
| Discovery | TA0007 | File and Directory Discovery | T1083 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediation and Containment

### Technical Fixes

1. Implement proper authentication and authorization checks on server-side endpoints, not header-based validation
2. Remove or relocate sensitive files outside the web root entirely
3. Do not reference restricted paths in client-accessible source code or comments

### OWASP Top 10 2021

- **A01:2021 Broken Access Control:** relying on client-supplied headers for authorization decisions

### MITRE D3FEND Countermeasures

- **D3-ACL Access Control List** to enforce filesystem-level restrictions independent of request headers (counters T1190)
- **D3-WSAA Web Session Activity Analysis** to detect unusual access patterns to restricted paths (counters T1083)

### NIST CSF 2.0

- **Protect (PR.AC-4):** Access permissions are managed and enforced consistently
- **Detect (DE.CM-7):** Monitoring for unauthorized access attempts to restricted resources

### NIST SP 800-53 Rev. 5

- **AC-3: Access Enforcement** (enforce proper server-side access controls)
- **AC-6: Least Privilege** (restrict file access based on authentication, not headers)

### CWE

- **CWE-284: Improper Access Control** (relying on spoofable headers for authorization)
- **CWE-200: Exposure of Sensitive Information** (hidden file discoverable through source code)

---

## References

- Solve approach based on research from [Jihun Hwang's POCTF 2023 writeup](https://jihunhwang.github.io/UWSP_CTF_2023_writeup/)

---

Thanks guys!! (❍ᴥ❍ʋ)

---

Abundance of security controls means nothing if the quality of each control is shallow. One header check does not a fortress make; always validate access on the server side with proper authentication.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
