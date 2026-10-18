# CTF Challenges

Personal collection of CTF writeups and boot2root challenge solutions.

---

## Platforms

| Platform | Machines | Status |
|----------|---------|--------|
| [Hacker101 CTF](hacker101-ctf/) | 27 web challenges | 🔄 Active |
| [VulnHub](vulnhub/) | 7 boot2root VMs | 🔄 Active |

---

## How to Use

Each platform folder contains individual challenge writeups. Every writeup follows the same structure:

- **Overview** — what the challenge is about and which vulnerabilities are involved
- **Attack Summary** — one-line kill chain
- **Step-by-step** — exact commands and expected outputs to reproduce the solution
- **Technical explanation** — why the vulnerability exists
- **Remediation** — how to fix it
- **scripts/** — exploit scripts when available

---

## Techniques Quick Reference

| Technique | Platform |
|-----------|---------|
| SQL Injection (UNION, error-based) | Hacker101 |
| XSS (reflected, stored, DOM) | Hacker101 |
| Padding Oracle (AES-CBC) | Hacker101 |
| IDOR / Broken Access Control | Hacker101 |
| GraphQL introspection & injection | Hacker101 |
| OAuth misconfiguration | Hacker101 |
| SOP bypass / iframe escape | Hacker101 |
| FTP anonymous + pcap analysis | VulnHub |
| Shellshock CVE-2014-6271 | VulnHub |
| Buffer overflow (SUID) | VulnHub |
| Tomcat WAR deploy | VulnHub |
| SSRF → credential extraction | VulnHub |
| DirtyCOW CVE-2016-5195 | VulnHub |
| Cron script injection | VulnHub |
| SSH key cracking (john) | VulnHub |

---

## License

For educational purposes only. Do not test techniques shown here against systems you do not own or have explicit written permission to test.

---
## POCTF-2026
POCTF:QJSZVGZE
https://pointeroverflowctf.com/
