# SEC4US CTF Lab

Personal collection of writeups and notes from the [SEC4US](https://sec4us.com.br/) offensive security training platform.

> **Disclaimer:** All challenges were solved on the official SEC4US platform under an authorized training engagement. No real systems were targeted.

---

## Progress Overview

**77/90 challenges solved** | **Rank #1** | **14,073 pts**

| Difficulty | Total | Solved | Pending | Coverage |
|------------|-------|--------|---------|----------|
| Easy | 31 | 31 | 0 | 100% |
| Medium | 37 | 28 | 9 | 76% |
| Hard | 22 | 18 | 4 | 82% |
| **Total** | **90** | **77** | **13** | **86%** |

---

## Labs

| Lab | Content | Status |
|-----|---------|--------|
| [Challenges](challenges/) | 77/90 individual hacking challenges (network, web, BOF, XSS, pivot) | In progress |
| [AD Forest Lab](lab-ad-forest/) | Active Directory forest compromise: 8 flags, 1275 pts (Kerberoasting, DCSync, Golden Ticket, Forest Trust) | Complete |
| [DevSecOps Lab](lab-devsecops/) | CI/CD pipeline exploitation: 10 flags, 1833 pts (GitLab, Jenkins, Vault, Docker escape) | Complete |

---

## Techniques Quick Reference

| Technique | Challenges |
|-----------|-----------|
| SQL Injection (UNION, error-based, blind) | maq102, maq109, maq117, maq126, maq153 |
| XSS (reflected, stored, DOM, CSP bypass) | xss1, xss3, xss4 |
| Server-Side Template Injection (SSTI) | maq136, maq170 |
| Local/Remote File Inclusion (LFI/RFI) | maq113, maq152, maq154 |
| Insecure Deserialization (PHP) | maq178 |
| SSRF | maq185 |
| Buffer Overflow (x86, x64, SEH) | maq124, maq125, maq130, maq168 |
| CMS Exploitation (WordPress, Joomla, Drupal) | maq117, maq129, maq146, maq148, maq149, maq153, maq193 |
| Jenkins / CI-CD Exploitation | maq156, DevSecOps Lab |
| Heartbleed (CVE-2014-0160) | maq163 |
| Kernel Exploits (DirtyCow, Mempodipper, DirtyPipe) | maq140, maq151 |
| Windows Privilege Escalation (JuicyPotato, MS14-002, MS15-051) | maq162, maq168, maq171 |
| Active Directory (Kerberoasting, DCSync, Golden Ticket) | AD Forest Lab |
| Docker Escape / Container Breakout | DevSecOps Lab |
| Pivoting / Lateral Movement | maq119 (via maq156), adm2, adm4 |
| SSH Brute Force / Custom Protocol | maq164, maq166 |
| DNS Zone Transfer | maq100 |
| VoIP / SIP Sniffing | maq161 |

---

## Structure

```
sec4us/
  challenges/           # Individual challenge writeups (77 solved)
    maq100-servidor-dns/
      README.md         # Writeup (no flags)
    ...
  lab-ad-forest/        # Active Directory Forest lab
    README.md           # Full walkthrough
  lab-devsecops/        # DevSecOps Ecosystem lab
    README.md           # Full walkthrough
```

---

## Author

**Andre Henrike** (@mrhenrike)

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

## License

For educational purposes only. Do not test techniques shown here against systems you do not own or have explicit written permission to test.
