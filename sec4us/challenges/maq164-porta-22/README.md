# MAQ164: Porta 22

Writeup for the **Porta 22** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Hard
> **Difficulty:** Hard
> **Points:** 164

---

## Overview

This challenge features an SSH service running a custom banner protocol that identifies itself as "BRUTEFORCE-2.0-BRUTEFORCE". Standard SSH clients fail to connect due to banner validation. A patched paramiko library is required to handle the non-standard banner and successfully brute-force credentials.

## Reconnaissance

```bash
nmap -sC -sV -p 22 [TARGET_IP]
```

The scan reports port 22 open with an unusual service banner. Manual banner grabbing reveals the custom identification string.

```bash
nc -v [TARGET_IP] 22
# Response: SSH-BRUTEFORCE-2.0-BRUTEFORCE
```

Standard SSH clients reject this banner because it does not match the expected `SSH-2.0-*` format defined in RFC 4253.

## Exploitation

### Paramiko Patch

The paramiko library enforces strict banner validation. To connect, the `_check_banner` method in `transport.py` must be patched to accept the custom protocol string.

```python
# Locate paramiko's transport.py
# Modify the banner check to accept "BRUTEFORCE-2.0-BRUTEFORCE"
# The exact patch depends on the paramiko version installed
```

### Brute-Force Authentication

1. With the patched paramiko, write a brute-force script targeting the SSH service.
2. The service has a rate limiter; adjust timing between attempts accordingly.
3. Test common credential pairs; the valid credentials are: `[FOUND_CREDS]`.

```python
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('[TARGET_IP]', username='[USER]', password='[PASS]')
stdin, stdout, stderr = client.exec_command('cat /flag.txt')
print(stdout.read().decode())
```

4. Upon successful authentication, execute commands to retrieve the flag.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Brute Force: Password Guessing | T1110.001 |
| Valid Accounts: Default Accounts | T1078.001 |
| Remote Services: SSH | T1021.004 |
| Command and Scripting Interpreter: Python | T1059.006 |

### CWE

- **CWE-521:** Weak Password Requirements
- **CWE-307:** Improper Restriction of Excessive Authentication Attempts
- **CWE-798:** Use of Hard-coded Credentials

### NIST SP 800-53

- **IA-5:** Authenticator Management
- **AC-7:** Unsuccessful Logon Attempts

---

Port 22 speaks a dialect all its own; when the door answers in a foreign tongue, learning its language is the only way in.

(❍ᴥ❍ʋ)

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
