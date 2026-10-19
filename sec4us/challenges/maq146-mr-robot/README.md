# Maq146: Mr. Robot

Writeup for the **Mr. Robot** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Medium
> **Difficulty:** Medium

---

## Overview

Inspired by the TV series, this challenge features a WordPress installation where the user "elliot" holds admin privileges. After gaining WordPress admin access, privilege escalation exploits an old nmap binary (3.81) with SUID permissions and its interactive mode to spawn a root shell.

## Reconnaissance

1. Scan the target to discover the web server and WordPress installation.
2. Enumerate WordPress users; identify "elliot" as a valid admin account.
3. Look for `robots.txt` or other exposed files that hint at credentials or wordlists.
4. Download any discovered dictionary files for credential attacks.

## Exploitation

1. Brute-force the WordPress login for user "elliot" using the discovered or generated wordlist.
2. Authenticate to the WordPress admin dashboard.
3. Navigate to Appearance > Theme Editor or Plugins > Plugin Editor.
4. Inject a PHP reverse shell into a theme file (e.g., `404.php`) or upload a malicious plugin.
5. Trigger the modified page to execute the reverse shell.
6. Catch the shell as the `www-data` or `daemon` user.

## Privilege Escalation

1. Enumerate SUID binaries: `find / -perm -4000 -type f 2>/dev/null`.
2. Discover `/usr/local/bin/nmap` version 3.81 with the SUID bit set.
3. Launch nmap in interactive mode: `nmap --interactive`.
4. From the nmap interactive prompt, execute `!sh` to spawn a shell with root privileges.
5. Retrieve all three flags scattered across the filesystem.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Brute Force: Password Guessing | T1110.001 |
| Server Software Component: Web Shell | T1505.003 |
| Abuse Elevation Control Mechanism: SUID/SGID | T1548.001 |
| Valid Accounts | T1078 |

### CWE

- **CWE-521:** Weak Password Requirements (brute-forceable admin password)
- **CWE-269:** Improper Privilege Management (SUID nmap with interactive shell escape)

---

> "Control is an illusion, but SUID nmap with interactive mode is very real. Elliot would approve: the quieter you enumerate, the louder the shell pops."

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
