# CTF Challenges

Personal collection of CTF writeups, boot2root challenge solutions and competition notes.

---

## Platforms

| Platform | Content | Status |
|----------|---------|--------|
| [Hacker101 CTF](hacker101/) | 27 web challenges | Complete |
| [VulnHub](vulnhub/) | 140+ boot2root VMs | In progress |
| [SEC4US CTF](sec4us/) | 77/90 challenges + AD Forest Lab (8 flags) + DevSecOps Lab (10 flags) | In progress |
| [SOCBrazil CTF](socbrazil/) | 2,572 challenges, 15/15 trails, #1 ranking | Complete |
| [POCTF 2023](poctf-2023/) | 24/27 challenges (Crypto, Crack, Web, Forensics, Exploit, Stego, RE, Misc, OSINT) | Incomplete |
| [POCTF 2024](poctf-2024/) | 80/80 challenges (Crack, Crypto, Exploit, Forensics, Misc, OSINT, RE, Stego, Web) | Complete |
| [POCTF 2025](poctf-2025/) | 0/80 challenges | Incomplete |
| [POCTF 2026](poctf-2026/) | 34/34 challenges (Web, Crypto, Stego, Forensics, RE, Exploitation, Misc, OSINT) | Complete |

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

### SEC4US CTF

```
sec4us/
  lab-ad-forest/     # Active Directory Forest lab (8 flags, 1275 pts)
  lab-devsecops/     # DevSecOps Ecosystem lab (10 flags, 1833 pts)
  challenges/        # Individual machine challenges (77/90 solved)
    <maq-slug>/
      README.md      # Full writeup
```

### SOCBrazil CTF

```
socbrazil/
  README.md          # Overview, 2572 challenges, 15 trails
  <trail-slug>/
    README.md        # Trail methodology and patterns
```

### Pointer Overflow CTF

```
poctf-<year>/
  <challenge-slug>/
    README.md        # Full writeup
    scripts/         # Solve scripts
```

### Hacker101

```
hacker101/
  <challenge-slug>/
    README.md        # Full writeup
```

---

## Techniques Quick Reference

| Technique | Platform |
|-----------|---------|
| SQL Injection (UNION, error-based, blind) | Hacker101, VulnHub, SEC4US |
| XSS (reflected, stored, DOM, CSP bypass) | Hacker101, SEC4US |
| Padding Oracle (AES-CBC) | Hacker101 |
| IDOR / Broken Access Control | Hacker101 |
| GraphQL introspection and injection | Hacker101 |
| OAuth misconfiguration | Hacker101 |
| Buffer overflow (SUID, SEH, ret2libc, BOF manual) | VulnHub, SEC4US |
| Tomcat WAR deploy / Axis2 exploitation | VulnHub, SEC4US |
| Shellshock CVE-2014-6271 | VulnHub |
| DirtyCOW CVE-2016-5195 | VulnHub, SEC4US |
| Cron script injection | VulnHub, SEC4US |
| SSH key cracking (john/hashcat) | VulnHub |
| SSRF, LFI, RFI | VulnHub, SEC4US |
| Active Directory (Kerberoasting, DCSync, Golden Ticket, Forest Trust) | SEC4US |
| DevSecOps (GitLab CI, Jenkins, Docker escape, Vault) | SEC4US |
| SSTI (Twig, Jinja2) | SEC4US |
| Insecure Deserialization (PHP, Java) | SEC4US |
| Windows privesc (JuicyPotato, MS14-002, MS15-051) | SEC4US |
| Port Knocking, SSH brute force | SEC4US |
| ColdFusion RCE | SEC4US |
| Heartbleed CVE-2014-0160 | SEC4US |
| Log analysis, threat hunting, incident response | SOCBrazil |
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
