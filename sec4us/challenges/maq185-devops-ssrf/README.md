# maq185: Sec4US DevOps

Writeup for the **Sec4US DevOps** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** SSRF  
> **Difficulty:** Medium  
> **Points:** 185

---

## Overview

A DevOps-oriented web application allows users to fetch URLs or interact with internal services. Insufficient validation on the URL input enables Server-Side Request Forgery (SSRF), granting access to internal services, cloud metadata endpoints, and restricted resources.

## Reconnaissance

Scan the target:

```bash
nmap -sC -sV -p- <TARGET_IP>
```

Explore the application for URL-fetching features: webhook configurations, URL previews, import-from-URL functionality, or health-check endpoints.

## Exploitation

### Step 1: Identify SSRF Vector

Locate a parameter that accepts URLs and test with an external callback:

```bash
python3 -m http.server 8080
```

Submit your listener URL and confirm the server makes the request.

### Step 2: Probe Internal Services

Use the SSRF to scan internal hosts and ports:

```
http://127.0.0.1:80
http://127.0.0.1:8080
http://localhost:6379
```

### Step 3: Access Cloud Metadata

If running on cloud infrastructure, target the metadata endpoint:

```
http://169.254.169.254/latest/meta-data/
http://169.254.169.254/latest/meta-data/iam/security-credentials/
```

### Step 4: Access Internal Services

Use discovered internal endpoints to extract sensitive data, credentials, or interact with databases and admin interfaces not exposed to the internet.

### Step 5: Retrieve the Flag

Read the flag from an internal service, metadata, or by leveraging obtained credentials for system access.

## Privilege Escalation

If shell access is obtained, enumerate for escalation:

```bash
sudo -l
env | grep -i aws
cat /etc/crontab
```

## Security Framework Mapping

### MITRE ATT&CK

| Technique                         | ID        |
|-----------------------------------|-----------|
| Exploit Public-Facing Application | T1190     |
| Cloud Instance Metadata API       | T1552.005 |
| Internal Proxy                    | T1090.001 |

### CWE

- **CWE-918:** Server-Side Request Forgery (SSRF)
- **CWE-441:** Unintended Proxy or Intermediary

---

In DevOps, automation connects everything; an unvalidated URL parameter turns the server into a proxy that knocks on every internal door on your behalf.

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
