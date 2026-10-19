# The Way Out is Through

| Detail      | Value                                      |
|-------------|--------------------------------------------|
| CTF         | Pointer Overflow CTF 2024                  |
| Category    | Web                                        |
| Difficulty  | Easy                                       |
| Points      | 100                                        |
| Flag        | `poctf{uwsp_7h3_7ru7h_15_0u7_7h3r3}`      |
| Status      | Solved                                     |

---

## Challenge Overview

A web challenge where the flag is scattered across multiple JavaScript encoding schemes embedded in the page source. The page presents a fake "Not Found" Apache error, but the HTML source contains five encoded flag fragments using character codes, Base64, hex arrays and Unicode escapes.

---

## Objective

Decode all JavaScript fragments in the page source to reconstruct the complete flag.

---

## Methodology

### Step 1: Inspect the page source

Visiting the challenge URL reveals a spoofed Apache 404 page. Viewing the source exposes a `<script>` block with five distinct encoded parts:

```html
<script>
    let part_1 = [112, 111, 99, 116].map(x => String.fromCharCode(x)).join('');
    let part_2 = atob("Znt1d3NwXw==");
    let part_3 = "document.cookie";
    let part_4 = "XzdydTdoXw==";
    let part_5_hex = [0x31, 0x35, 0x5f, 0x30, 0x75, 0x37, 0x5f, 0x37, 0x68, 0x33, 0x72, 0x33, 0x7d];

    console.log("The Tooth is Over There.");
    document.cookie = "7h3";
</script>
```

### Step 2: Decode each fragment

**Part 1** (decimal char codes):

```js
[112, 111, 99, 116].map(x => String.fromCharCode(x)).join('')
// Result: "poct"
```

**Part 2** (Base64):

```js
atob("Znt1d3NwXw==")
// Result: "f{uwsp_"
```

**Part 3**: a red herring (`"document.cookie"`), not part of the flag.

**Part 4** (Base64):

```js
atob("XzdydTdoXw==")
// Result: "_7ru7h_"
```

**Part 5** (hex byte array):

```js
[0x31, 0x35, 0x5f, 0x30, 0x75, 0x37, 0x5f, 0x37, 0x68, 0x33, 0x72, 0x33, 0x7d]
// Result: "15_0u7_7h3r3}"
```

**Console/cookie lines** (Unicode escapes):

```js
document.cookie = "7h3"
// Result: "7h3"
```

### Step 3: Assemble the flag

Concatenating: `poct` + `f{uwsp_` + `7h3_` + `7ru7h_` + `15_0u7_7h3r3}` = the complete flag.

---

## Flag

```
poctf{uwsp_7h3_7ru7h_15_0u7_7h3r3}
```

---

## Lessons Learned

| # | Lesson | Detail |
|---|--------|--------|
| 1 | Always view page source | Fake error pages can contain hidden scripts |
| 2 | Multiple encoding layers | Mixing char codes, Base64, hex and Unicode obscures data |
| 3 | Red herrings exist | Not every variable contributes to the flag |
| 4 | Console output matters | `console.log` and `document.cookie` can hold clues |

---

## MITRE ATT&CK Mapping

| Tactic          | Technique                      | ID        |
|-----------------|--------------------------------|-----------|
| Initial Access  | Drive-by Compromise            | T1189     |
| Defense Evasion | Obfuscated Files or Information| T1027     |
| Collection      | Data from Information Repositories | T1213 |

---

## OWASP Top 10 2021 Mapping

| Category | ID    | Relevance |
|----------|-------|-----------|
| Security Misconfiguration | A05:2021 | Sensitive data in client-side source |
| Cryptographic Failures    | A02:2021 | Weak obfuscation instead of proper secrets management |

---

## Remediation

### Technical Fixes
- Never embed secrets or flags in client-side JavaScript
- Use server-side validation for sensitive operations
- Strip debug/development scripts before deploying to production

### OWASP Top 10 2021
- **A05 Security Misconfiguration**: remove debug scripts and hidden data from production HTML
- **A02 Cryptographic Failures**: do not rely on encoding (Base64, char codes) as a substitute for encryption

### D3FEND Countermeasures
| Technique             | ID        |
|-----------------------|-----------|
| File Content Rules    | D3-FCR    |
| Application Hardening | D3-AH     |

### NIST CSF 2.0
| Function | Category                | Subcategory |
|----------|------------------------|-------------|
| Protect  | Data Security          | PR.DS-01    |
| Detect   | Security Continuous Monitoring | DE.CM-01 |

### NIST SP 800-53 Rev. 5
| Control     | Description                          |
|-------------|--------------------------------------|
| SC-28       | Protection of Information at Rest    |
| SI-11       | Error Handling                       |

### C2M2
| Practice Area               | MIL |
|-----------------------------|-----|
| Asset, Change and Configuration Management | MIL2 |

### CWE
| ID      | Name                                     |
|---------|------------------------------------------|
| CWE-540 | Inclusion of Sensitive Information in Source Code |
| CWE-615 | Inclusion of Sensitive Information in Source Code Comments |

---

## References

- Based on solve approach from [Jdwalli](https://github.com/Jdwalli/ctf-writeups)
- [OWASP Top 10 2021](https://owasp.org/Top10/)
- [MITRE ATT&CK](https://attack.mitre.org/)

---

## Closing

Thanks guys!! (❍ᴥ❍ʋ)

The truth really is out there if you know where to look. Sometimes the most important clues are hiding in plain sight, mixed into the noise of what seems ordinary. Keep decoding, keep questioning.

[![Instagram](https://img.shields.io/badge/-Instagram-E4405F?style=flat&logo=instagram&logoColor=white)](https://www.instagram.com/uniaogeek)
[![LinkedIn](https://img.shields.io/badge/-LinkedIn-0077B5?style=flat&logo=linkedin&logoColor=white)](http://linkedin.com/in/mrhenrike)
[![X](https://img.shields.io/badge/-X-000000?style=flat&logo=x&logoColor=white)](https://x.com/mrhenrike)
