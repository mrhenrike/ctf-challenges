# Petshop Pro — Writeup (3/3)

**Difficulty:** Easy  
**Category:** Web (Price Manipulation, Brute Force, Stored XSS)  
**Flags:** 3/3 (complete)  
**Platform:** Hacker101 CTF

---

## About the Challenge

**Context:** An online pet store (kittens and puppies). It has a shopping cart with checkout, an admin panel accessible via `/login`, and product editing functionality visible only to logged-in admins.

**What you face:** A checkout that trusts prices sent by the client, a login with distinct error messages for wrong username vs wrong password, and product fields that are reflected in the cart without sanitization.

**Vulnerabilities exploited:**
- Client-Side Price Manipulation (CWE-602) — price in a `hidden` field is not validated server-side
- Username Enumeration (CWE-204) — different response for "Invalid username" vs "Invalid password"
- Stored XSS (CWE-79) — product name injected with HTML/JS is rendered in the cart

**What you learn:**
- Prices and critical values must NEVER come from the client — always fetch from the database server-side
- Distinct error messages for user/password allow two-phase enumeration
- Stored XSS on products can affect other users who view the cart
- Burp Turbo Intruder outperforms the Community Intruder for brute-force without throttling
- The cart (not the checkout) is where stored XSS manifests in this challenge

---

## Objective

Exploit three vulnerabilities in a pet shop application: price manipulation at checkout, admin credential brute-force, and Stored XSS on product edit fields.

---

## Flag 0 — Price Manipulation (Hidden Field in Cart)

**Vulnerability:** The checkout form sends item prices in a `type="hidden"` field that is not validated server-side.

### Step 1: Add items to the cart

Add any combination of kitten/puppy to the cart and navigate to `/cart`.

### Step 2: Inspect the HTML

In the page source, locate the hidden field with the prices:

```html
<input type="hidden" name="price" value="...">
```

### Step 3: Modify the field

Remove the `type="hidden"` attribute to make the field visible, or use Burp Suite to intercept the checkout POST request and change the price value to `0`.

### Step 4: Complete checkout

With the price set to zero, finalize the checkout. The flag appears in the order summary.

---

## Flag 1 — Admin Credential Brute Force

**Vulnerability:** The `/login` endpoint differentiates between "Invalid username" and "Invalid password", allowing username enumeration separately from password enumeration.

### Step 1: Locate the endpoint

The admin endpoint is at `/login` (sometimes hidden, but found via manual enumeration or HTML inspection).

### Step 2: Enumerate the username

The server responds with different messages:
- Non-existent username: `"Invalid username"`
- Correct username + wrong password: `"Invalid password"`

Use Burp Turbo Intruder, ffuf, or Hydra to enumerate usernames with a wordlist:

```bash
ffuf -u https://<INSTANCE>/login -X POST \
  -d "username=FUZZ&password=test" \
  -w /usr/share/wordlists/seclists/Usernames/Names/names.txt \
  -mr "Invalid password"
```

### Step 3: Enumerate the password

With the correct username, enumerate the password:

```bash
ffuf -u https://<INSTANCE>/login -X POST \
  -d "username=<USER>&password=FUZZ" \
  -w /usr/share/wordlists/rockyou.txt \
  -fr "Invalid password"
```

### Step 4: Log in

After finding the correct credentials, log in at `/login`. The flag appears immediately upon entering the admin panel.

---

## Flag 2 — Stored XSS on Product Edit Field

**Vulnerability:** Product edit fields (name, description) are stored and reflected without sanitization in the cart.

### Step 1: Log in as admin

Use the credentials found in Flag 1 to log in.

### Step 2: Edit a product

Navigate to `/edit?id=0` (or any product ID) and inject an XSS payload into the `name` field:

```html
<img src=x onerror=alert(1)>
```

Save the product.

### Step 3: Add to cart and verify

Add the edited product to the cart and access `/cart`.

**Important:** Do NOT proceed to checkout. The flag appears in the **Name** column inside the cart table when viewing the items.

---

## Attack Summary

```
FLAG 0: hidden field price=0 in checkout POST → flag in order summary
FLAG 1: ffuf username enum (Invalid username vs Invalid password) → password brute → login
FLAG 2: Stored XSS in product name → /cart (no checkout) → flag in item name column
```

---

## Lessons Learned

1. **Prices must never come from the client**: validate values server-side against the database
2. **Distinct error messages** for username/password allow two-phase enumeration
3. **Unsanitized text fields** = Stored XSS if displayed on any page
4. **XSS in the cart** can be exploited by other users and admins who access the cart
5. **Username enumeration** before password brute-force drastically reduces the search space
