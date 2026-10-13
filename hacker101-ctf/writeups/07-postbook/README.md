# Postbook — Writeup (5/5)

**Difficulty:** Easy  
**Category:** Web (IDOR, Weak Credentials, Hidden Parameters)  
**Flags:** 5/5 (complete)  
**Platform:** Hacker101 CTF

---

## About the Challenge

**Context:** A mini social network where users create accounts and publish posts. There are private posts from other users that the attacker needs to access, create posts on behalf of others, and edit third-party posts — all without permission.

**What you face:** A post system with sequential IDs, forms with hidden fields (`user_id`), and a login screen with weak credentials. It looks simple, but each feature has a different authorization flaw.

**Vulnerabilities exploited:**
- IDOR — Insecure Direct Object Reference (CWE-639) on post viewing, creation, and editing
- Weak/default credentials (CWE-521) — `user/password`
- Hidden parameter manipulation (`type="hidden"`) on the post creation form
- Predictable/calculated ID (189 × 5 = 945) to access a specific post

**What you learn:**
- IDOR is the most prevalent vulnerability: the server must verify ownership for EVERY operation
- HTML `type="hidden"` fields are trivially visible and modifiable by the client
- Sequential or calculable IDs facilitate enumeration — use UUIDs or opaque tokens instead
- Authorization must be enforced server-side for read, create, edit, and delete operations
- Default credentials are the first vector to test in any new application

---

## Objective

Exploit IDOR (Insecure Direct Object Reference) and weak credentials in a blog system.

---

## Flag 0 — Weak Credentials

### Payload

```
username: user
password: password
```

The flag appears after a successful login.

---

## Flag 1 — IDOR on the `id` Parameter (View)

**Vulnerability:** The `id` parameter in the post view URL does not validate authorization.

### Steps

When viewing a post:
```
/index.php?page=view.php&id=1
```

Change `id` to other values:
```
/index.php?page=view.php&id=2
```

Post 2 belongs to another user and contains the flag.

---

## Flag 2 — IDOR via Hidden Field (Post as Another User)

**Vulnerability:** The post creation form has a hidden `user_id` field that can be manipulated.

### Steps

1. Open the new post form
2. Inspect the HTML and find the hidden field:
   ```html
   <input type="hidden" name="user_id" value="2">
   ```
3. Change `user_id` to `1` (admin/another user)
4. Submit the post

The post is created on behalf of user 1, and the flag appears.

---

## Flag 3 — IDOR with a Calculated ID

**Vulnerability:** Predictable mathematical pattern in private post IDs.

### Steps

Calculate `189 × 5 = 945` and access:
```
/index.php?page=view.php&id=945
```

The flag is in the hidden post with this calculated ID.

**Note:** The specific pattern (189 × 5) may vary by instance. Numeric fuzzing may be required.

---

## Flag 4 — IDOR on Post Editing

**Vulnerability:** The edit form also does not validate whether the post belongs to the current user.

### Steps

1. Access one of your own posts for editing:
   ```
   /index.php?page=edit.php&id=3
   ```
2. Change `id` to another user's post:
   ```
   /index.php?page=edit.php&id=1
   ```
3. Modify and save the post

The flag appears after saving the edit on someone else's post.

---

## Attack Summary

```
FLAG 0: Login with user/password
FLAG 1: id=2 in view (another user's post)
FLAG 2: Hidden field user_id=1 in post creation form
FLAG 3: id=945 (189×5) in view
FLAG 4: id=1 in edit form
```

## Lessons Learned

1. **IDOR** is the most common vulnerability: never trust IDs coming from the client
2. **Hidden HTML fields** are trivially manipulable by the client
3. **Sequential or predictable IDs** facilitate enumeration
4. **Authorization must be enforced server-side** for each operation (read, create, edit, delete)
5. **Default credentials** must never be used in production
