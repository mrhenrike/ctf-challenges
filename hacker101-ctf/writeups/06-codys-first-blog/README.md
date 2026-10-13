# Cody's First Blog — Writeup (3/3)

**Difficulty:** Easy  
**Category:** Web — PHP Injection, LFI, RFI  
**Flags:** 3/3 (complete)  
**Platform:** Hacker101 CTF

---

## Challenge Overview

**Context:** A PHP blog created by "Cody", a beginner developer. Allows posting public comments, has a hidden admin panel, and uses `include()` to load pages via the `?page=` parameter.

**What you face:** An apparently harmless comment field, a link to the admin panel commented out in the HTML, and a file inclusion feature that accepts any value — including external URLs.

**Vulnerabilities exploited:**
- PHP Code Injection (CWE-94) — comments saved to disk and included via `include()`
- Local File Inclusion / LFI (CWE-98) — `?page=admin.inc` bypasses authentication
- Remote File Inclusion / RFI — `include()` with `allow_url_include=On` accepts HTTP URLs
- Information Disclosure — HTML comments expose internal paths (`admin.auth.inc`)

**What you learn:**
- `include()` with user input = critical LFI/RFI — never combine the two
- HTML comments are public: do not hide sensitive paths in them
- User comments must NEVER be included as executable PHP files
- Removing "auth" from `admin.auth.inc` to reach `admin.inc` is a classic filename-based auth bypass
- `allow_url_include=On` in `php.ini` is an extremely dangerous setting

---

## Objective

Exploit PHP code injection via comments and Local/Remote File Inclusion to capture 3 flags.

---

## Flag 0 — PHP Code Injection via Comments

**Vulnerability:** Comments are written to disk and included via PHP's `include()` without sanitization.

### Payload

In the comment field, enter:

```php
<?php system($_GET['cmd']); ?>
```

The comment is saved as a PHP file and included on the page, executing the code directly.

**Simpler alternative:**

```php
<?php phpinfo(); ?>
```

The flag appears in the execution output.

---

## Flag 1 — Admin Panel Authentication Bypass via LFI

**Vulnerability:** The `?page=` parameter includes PHP files directly; removing "auth" from the path bypasses authentication.

### Step 1: Discover the admin panel in the source

In the HTML source of the page, there is a commented-out link:
```html
<!--<a href="?page=admin.auth.inc">Admin login</a>-->
```

### Step 2: Access admin without authentication

Modify the parameter to remove "auth":

```
/?page=admin.inc
```

This includes the admin panel directly, bypassing authentication entirely.

The flag appears in the admin panel.

---

## Flag 2 — Remote File Inclusion (RFI) via Source Code Disclosure

**Vulnerability:** `include()` accepts URLs and `http://localhost/` returns processed PHP code (with comments already executed).

### Step 1: Read the index source code

```
/?page=http://localhost/index
```

PHP includes the file itself via HTTP, executing any previously injected PHP comments (Flag 0), and the source code appears in the response.

**Alternative: Use RFI to execute a file-reading payload**

Inject in the comments:
```php
<?php echo file_get_contents("index.php"); ?>
```

Then access the page to see the full source with the embedded flag.

### Why this works

`include('http://localhost/index.php')` makes an HTTP request to itself. Previously stored PHP comments in the included files are executed, revealing the contents of `index.php` in the response.

---

## Attack Summary

```
1. Comment with <?php system(...)?> → FLAG 0 via direct code execution
2. ?page=admin.inc (without "auth") → FLAG 1 via authentication bypass
3. ?page=http://localhost/index → FLAG 2 via RFI/source disclosure
```

---

## Lessons Learned

1. **PHP `include()` with user input** = critical LFI/RFI
2. **Comments must never execute code** — sanitize and escape all user input
3. **HTML comments (`<!-- -->`)** expose internal paths and hidden functionality
4. **`include()` accepts URLs by default** — disable `allow_url_include` in php.ini
5. **Authentication checks via filename** are fragile and trivially bypassable
