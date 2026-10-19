# Maq143: Servidor SSH 64bits

Writeup for the **Servidor SSH 64bits** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Easy
> **Difficulty:** Easy
> **Points:** 143

---

## Overview

A 64-bit Linux server with SSH as the primary attack surface. The challenge involves discovering valid credentials through enumeration, brute-forcing, or exploiting an SSH-related vulnerability.

## Reconnaissance

```bash
nmap -sV -sC -p- [TARGET_IP] -oN nmap_scan.txt
```

Focus on port 22 (SSH). Check the version for known vulnerabilities:

```bash
nmap -sV -p 22 --script ssh2-enum-algos,ssh-auth-methods [TARGET_IP]
```

Check for user enumeration vulnerability (CVE-2018-15473) on older OpenSSH versions:

```bash
searchsploit openssh user enumeration
```

## Exploitation

**User enumeration (if vulnerable):**

```bash
python3 ssh_user_enum.py [TARGET_IP] -U /usr/share/wordlists/seclists/Usernames/top-usernames-shortlist.txt
```

**Brute-force with discovered or common usernames:**

```bash
hydra -l [USERNAME] -P /usr/share/wordlists/rockyou.txt ssh://[TARGET_IP] -t 4
```

**Alternative: SSH key-based access.** Check other services for leaked private keys or authorized_keys files.

Once credentials are obtained:

```bash
ssh [USERNAME]@[TARGET_IP]
```

## Privilege Escalation

```bash
sudo -l
find / -perm -4000 -type f 2>/dev/null
cat /etc/crontab
```

Look for misconfigured sudo rules, SUID binaries, or cron jobs running as root.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Brute Force: Password Guessing | T1110.001 |
| Valid Accounts: Local Accounts | T1078.003 |
| Exploitation for Privilege Escalation | T1068 |

### CWE

- **CWE-521:** Weak Password Requirements
- **CWE-250:** Execution with Unnecessary Privileges

---

SSH is often the last door standing after every other service is locked down. When the only way in is a password, make sure it cannot be guessed before coffee gets cold.

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
