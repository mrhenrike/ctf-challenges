# CTF Challenges

Personal collection of CTF writeups, boot2root challenge solutions and competition notes.

---

## Platforms

| Platform | Content | Status |
|----------|---------|--------|
| [Hacker101 CTF](hacker101/) | 27 web challenges | Active |
| [VulnHub](vulnhub/) | 140+ boot2root VMs | Active |
| [Pointer Overflow CTF 2023](pointeroverflow-poctf-2023/) | 4 challenges (Cracking, Forensics) | Complete |
| [Pointer Overflow CTF 2024](pointeroverflow-poctf-2024/) | Competition writeups | Coming soon |
| [Pointer Overflow CTF 2025](pointeroverflow-poctf-2025/) | Competition writeups | Coming soon |

---

## Structure

Each platform folder contains individual challenge writeups. Writeups follow a consistent structure:

### VulnHub

```
vulnhub/<vm-slug>/
  README.md          # Full writeup (EN-US)
  README-ptbr.md     # Full writeup (PT-BR)
  scripts/           # Exploit scripts
  images/            # Screenshots
```

### Pointer Overflow CTF

```
pointeroverflow-poctf-<year>/
  challenges/<challenge-slug>/
    WRITEUP.md       # Full writeup
    scripts/         # Solve scripts
```

### Hacker101

```
hacker101/
  writeups/<challenge>.md   # Individual writeups
```

---

## Techniques Quick Reference

| Technique | Platform |
|-----------|---------|
| SQL Injection (UNION, error-based, blind) | Hacker101, VulnHub |
| XSS (reflected, stored, DOM) | Hacker101 |
| Padding Oracle (AES-CBC) | Hacker101 |
| IDOR / Broken Access Control | Hacker101 |
| GraphQL introspection & injection | Hacker101 |
| OAuth misconfiguration | Hacker101 |
| Buffer overflow (SUID, SEH, ret2libc) | VulnHub |
| Tomcat WAR deploy / Axis2 exploitation | VulnHub |
| Shellshock CVE-2014-6271 | VulnHub |
| DirtyCOW CVE-2016-5195 | VulnHub |
| Cron script injection | VulnHub |
| SSH key cracking (john/hashcat) | VulnHub |
| SSRF, LFI, RFI | VulnHub |
| Active Directory (Kerberoasting, DCSync) | VulnHub |
| Hash cracking (SHA-1, dictionary attacks) | POCTF |
| Forensics (disk images, EXIF, file carving) | POCTF |
| Steganography (whitespace, image hiding) | POCTF |
| Cryptography (Beaufort, CBC, padding oracle) | POCTF |
| Web exploitation (NoSQL injection, GraphQL, cache poisoning) | POCTF |
| Reverse engineering (Godot, XOR, game hacking) | POCTF |

---

## Author

**Andre Henrike** (@mrhenrike)

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

## License

For educational purposes only. Do not test techniques shown here against systems you do not own or have explicit written permission to test.
