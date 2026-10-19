# maq137: Servidor Web Jakarta

Writeup for the **Servidor Web Jakarta** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Web Hacking  
> **Difficulty:** Easy  
> **Points:** 137

---

## Overview

A Java-based web server running Apache Struts or Tomcat exposes known vulnerabilities that allow remote code execution through crafted requests targeting the Jakarta Multipart parser or default credentials.

## Reconnaissance

Enumerate services and identify the web stack:

```bash
nmap -sC -sV -p- <TARGET_IP>
```

Fingerprint the Java application server:

```bash
curl -v http://<TARGET_IP>/
whatweb http://<TARGET_IP>
```

Look for Tomcat manager panels, Struts action endpoints, or Jakarta error pages that reveal version information.

## Exploitation

### Step 1: Identify the Vulnerability

Check for known Struts/Tomcat vulnerabilities. Common targets include:

- Apache Struts CVE-2017-5638 (Content-Type OGNL injection)
- Tomcat manager with default credentials
- Jakarta Multipart parser RCE

### Step 2: Exploit the Vulnerability

For Struts2 Content-Type injection:

```bash
curl -H "Content-Type: %{(#_='multipart/form-data')...}" http://<TARGET_IP>/action
```

Use Metasploit or manual payloads to confirm code execution.

### Step 3: Obtain Shell Access

Deploy a JSP webshell through the Tomcat manager or exploit RCE to get a reverse shell:

```bash
nc -lvnp 4444
```

### Step 4: Retrieve the Flag

Navigate the server filesystem and read the flag.

## Privilege Escalation

Check Java process permissions, SUID binaries, and sudo rules:

```bash
sudo -l
ps aux | grep java
```

## Security Framework Mapping

### MITRE ATT&CK

| Technique                         | ID        |
|-----------------------------------|-----------|
| Exploit Public-Facing Application | T1190     |
| Server Software Component         | T1505     |
| Web Shell                         | T1505.003 |

### CWE

- **CWE-20:** Improper Input Validation
- **CWE-94:** Improper Control of Generation of Code (Code Injection)

---

Java frameworks carry the weight of enterprise trust; when that trust meets an unpatched parser, the entire stack becomes a launchpad.

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
