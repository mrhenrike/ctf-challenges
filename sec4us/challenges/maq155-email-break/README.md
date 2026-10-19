# Maq155: Email Break

Writeup for the **Email Break** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Medium
> **Difficulty:** Medium

---

## Overview

An email server challenge where exploitation of the mail infrastructure provides initial access. Misconfigured mail services, weak authentication, or known vulnerabilities in the mail server software allow pivoting from email access to system-level compromise.

## Reconnaissance

1. Scan the target for mail-related ports: SMTP (25/587), POP3 (110/995), IMAP (143/993), and web interfaces.
2. Enumerate SMTP using VRFY or EXPN commands to discover valid email accounts.
3. Identify the webmail interface and its software version.
4. Research known vulnerabilities for the identified mail server and webmail application.

## Exploitation

1. Test for SMTP relay misconfiguration or open relay capabilities.
2. Brute-force or guess credentials for discovered email accounts.
3. Access the webmail interface or mail client with valid credentials.
4. Search mailbox contents for sensitive information: internal credentials, system details, or configuration files.
5. Exploit a vulnerability in the mail server or webmail application to achieve code execution.
6. Establish a reverse shell as the mail service user.

## Privilege Escalation

1. Enumerate local system configuration from the mail service user context.
2. Check for credentials stored in mail server configuration files.
3. Identify misconfigurations in file permissions, cron jobs, or sudo rules.
4. Escalate privileges to root and retrieve the flag.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Exploit Public-Facing Application | T1190 |
| Brute Force: Password Guessing | T1110.001 |
| Email Collection: Local Email Collection | T1114.001 |
| Valid Accounts | T1078 |

### CWE

- **CWE-521:** Weak Password Requirements (guessable email credentials)
- **CWE-16:** Configuration (misconfigured mail server)
- **CWE-200:** Exposure of Sensitive Information to an Unauthorized Actor

---

> "Breaking into email is like reading someone's diary: it holds conversations, credentials, and clues. When the mail server is the weakest link, every inbox becomes an open book."

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
