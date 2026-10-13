# Hacker101 CTF — Writeups

Personal collection of writeups for the [Hacker101 CTF](https://ctf.hacker101.com/) challenges by HackerOne.

> **Disclaimer:** All challenges were solved on the Hacker101 CTF platform using personally provisioned instances. No real systems were targeted. Hashes shown are CTF challenge hashes, not real credentials.

---

## Progress Overview

| # | Challenge | Difficulty | Category | Flags | Status |
|---|-----------|-----------|----------|-------|--------|
| 01 | [A Little Something to Get You Started](writeups/01-a-little-something-to-get-you-started/) | Easy | Web | 1/1 | ✅ Complete |
| 02 | [Micro-CMS v1](writeups/02-micro-cms-v1/) | Easy | Web | 4/4 | ✅ Complete |
| 03 | [Micro-CMS v2](writeups/03-micro-cms-v2/) | Moderate | Web | 3/3 | ✅ Complete |
| 04 | [Encrypted Pastebin](writeups/04-encrypted-pastebin/) | Hard | Web, Crypto | 4/4 | ✅ Complete |
| 05 | [Photo Gallery](writeups/05-photo-gallery/) | Easy | Web | 3/3 | ✅ Complete |
| 06 | [Cody's First Blog](writeups/06-codys-first-blog/) | Easy | Web | 5/5 | ✅ Complete |
| 07 | [Postbook](writeups/07-postbook/) | Easy | Web | 7/7 | ✅ Complete |
| 08 | [Ticketastic: Live Instance](writeups/09-ticketastic-live/) | Moderate | Web | 2/2 | ✅ Complete |
| 09 | [Petshop Pro](writeups/10-petshop-pro/) | Moderate | Web | 3/3 | ✅ Complete |
| 10 | [BugDB v1](writeups/18-bugdb-v1/) | Moderate | Web, GraphQL | 3/3 | ✅ Complete |
| 11 | [BugDB v2](writeups/19-bugdb-v2/) | Moderate | Web, GraphQL | 4/4 | ✅ Complete |
| 12 | [TempImage](writeups/20-tempimage/) | Hard | Web | 3/3 | ✅ Complete |
| 13 | [Ticketastic: Demo Instance](writeups/ticketastic-demo/) | Easy | Web | 0/0 | ℹ️ Practice only |
| 14 | [Oauthbreaker](writeups/oauthbreaker/) | Hard | Web, OAuth | 2/2 | ✅ Complete |
| 15 | [Mobile Webdev](writeups/mobile-webdev/) | Hard | Android, Web | 2/2 | ✅ Complete |
| 16 | [Intentional Exercise](writeups/intentional-exercise/) | Hard | Web | 1/1 | ✅ Complete |
| 17 | [Grayhatcon CTF](writeups/grayhatcon/) | Expert | Web, Multi | 4/4 | ✅ Complete |
| 18 | [Hackyholidays CTF](writeups/hackyholidays/) | Expert | Multi | 12/12 | ✅ Complete |
| 19 | [RTFM](writeups/22-rtfm/) | Expert | Web, Multi | 8/8 | ✅ Complete |
| 20 | [XSS Playground by zseano](writeups/22-xss-playground/) | Expert | Web, XSS | 3/3 | ✅ Complete |
| 21 | [H1 Thermostat](writeups/h1-thermostat/) | Expert | IoT, Web | 2/2 | ✅ Complete |
| 22 | [Ticketastic (full version)](writeups/21-ticketastic/) | Moderate | Web | 2/2 | ✅ Complete |
| 23 | [Model E1337 — Rolling Code Lock](writeups/model-e1337/) | Expert | Crypto, Math | 3/3 | ✅ Complete |
| 24 | [Model E1337 v1](writeups/model-e1337-v1/) | Expert | Crypto, Math | 2/2 | ✅ Complete |
| 25 | [Model E1337 v2 — Hardened](writeups/model-e1337-v2/) | Expert | Crypto, Math | 1/1 | ✅ Complete |
| 26 | [Y2FuIHlvdSByZWNvbj8 — Can You Recon?](writeups/y2fu-can-you-recon/) | Expert | OSINT, Recon | 3/3 | ✅ Complete |
| 27 | [Rend Asunder](writeups/rend-asunder/) | Expert | DOM XSS, Browser | 1/3 | 🔄 In Progress |

---

## Techniques Index

A quick reference of vulnerability classes covered across these challenges.

| Technique | Challenges |
|-----------|-----------|
| SQL Injection (error-based, UNION) | Micro-CMS v2, Encrypted Pastebin, Ticketastic, Petshop Pro |
| XSS (reflected, stored, DOM) | Micro-CMS v1, Cody's First Blog, Grayhatcon, XSS Playground, Rend Asunder |
| Padding Oracle Attack (AES-CBC) | Encrypted Pastebin |
| IDOR / Broken Access Control | Postbook, Ticketastic, Petshop Pro |
| File Inclusion / Path Traversal | Photo Gallery, TempImage |
| GraphQL Introspection & Injection | BugDB v1, BugDB v2 |
| OAuth Misconfiguration | Oauthbreaker |
| Cryptographic Weakness (GF/Z3) | Model E1337, Model E1337 v1, Model E1337 v2 |
| Android WebView / Deep Links | Mobile Webdev |
| SSRF | TempImage |
| HTTP Method Bypass | Micro-CMS v2 |
| IP Spoofing via X-Forwarded-For | Grayhatcon |
| SOP Bypass / iframe escape | Rend Asunder |

---

## Repository Structure

```
writeups/
├── 01-a-little-something-to-get-you-started/
│   └── README.md
├── 02-micro-cms-v1/
│   └── README.md
├── 03-micro-cms-v2/
│   └── README.md
├── 04-encrypted-pastebin/
│   ├── README.md
│   └── scripts/
│       └── padding_oracle.py
├── 05-photo-gallery/
│   └── README.md
└── ...  (each challenge in its own directory)
```

Each challenge folder contains:
- `README.md` — step-by-step writeup with commands and expected output
- `scripts/` — exploit scripts (when applicable)

---

## License

These writeups are released for educational purposes. Do not use any technique shown here against systems you do not own or have explicit permission to test.
