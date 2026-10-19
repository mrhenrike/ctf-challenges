# MAQ134: LiGoat 3

Writeup for the **LiGoat 3** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Hard
> **Difficulty:** Hard
> **Points:** 134

---

## Overview

LiGoat 3 is an advanced web exploitation challenge built around OWASP WebGoat. The target exposes a deliberately vulnerable Java web application where multiple OWASP Top 10 flaws must be chained to reach the final flag.

## Reconnaissance

```bash
nmap -sC -sV -p- [TARGET_IP]
```

Port scanning reveals HTTP services running WebGoat on a non-standard port. Directory enumeration confirms the WebGoat application context path and identifies accessible lesson endpoints.

```bash
gobuster dir -u http://[TARGET_IP]:8080/WebGoat -w /usr/share/wordlists/dirb/common.txt
```

## Exploitation

1. Access the WebGoat interface and enumerate available lessons.
2. Identify the injection point in the advanced SQL lesson; craft a UNION-based payload to extract stored credentials from the backend database.
3. Use the extracted credentials to authenticate into the administrative section.
4. Chain a path traversal vulnerability in the file upload lesson to write a JSP webshell outside the sandbox directory.
5. Execute the webshell to obtain command execution on the underlying server and retrieve the flag from the filesystem.

```bash
curl -b "JSESSIONID=[SESSION]" "http://[TARGET_IP]:8080/WebGoat/[VULN_ENDPOINT]" \
  --data "param=[SQLI_PAYLOAD]"
```

## Post-Exploitation

With shell access, enumerate local users and sensitive files. The flag is stored in a restricted directory readable only by the application service account.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Exploit Public-Facing Application | T1190 |
| Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Valid Accounts | T1078 |
| Data from Local System | T1005 |

### CWE

- **CWE-89:** Improper Neutralization of Special Elements used in an SQL Command (SQL Injection)
- **CWE-22:** Improper Limitation of a Pathname to a Restricted Directory (Path Traversal)
- **CWE-434:** Unrestricted Upload of File with Dangerous Type

### NIST SP 800-53

- **SI-10:** Information Input Validation
- **AC-6:** Least Privilege

---

Every goat eventually leads you to the gate; chain enough flaws and you will find the shepherd left the key under the mat.

(❍ᴥ❍ʋ)

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
