# SpyderSec: Challenge — Spin the Web, Decode the Truth

Alright dudes!! SpyderSec is genuinely one of the most creative boxes I have seen on VulnHub. Forget the usual SQLi or brute-force. This one chains EXIF metadata extraction, hex-to-ASCII decoding, Base64 decryption, JavaScript eval unpacking, Burp Suite cookie analysis, TrueCrypt steganographic hidden volume detection, and VeraCrypt mounting, all to find two flags inside a hidden volume. It is a forensics and stego puzzle disguised as a boot2root. No shell required. The challenge rewards patience, curiosity, and a refusal to skip "boring" steps like exiftool. Legit one of the most unique CTF experiences available. Big respect to SpyderSec.

| Field | Value |
|---|---|
| **Level** | Intermediate |
| **Target VM** | SpyderSec: Challenge |
| **Attacker VM** | Kali Linux 2024.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/spydersec-challenge,128/ |
| **Techniques** | Network service enumeration, EXIF metadata analysis with exiftool, hex-to-ASCII decoding, Base64 decoding, JavaScript eval unpacking and obfuscation analysis, Burp Suite cookie interception and URL construction, TrueCrypt hidden volume steganography detection with tcsteg.py, VeraCrypt hidden volume mounting |
| **CVEs** | CWE-312 (Cleartext Storage of Sensitive Information: password embedded in EXIF metadata), CWE-200 (Information Exposure: internal path disclosed via session cookie), CWE-327 (Use of a Broken or Risky Cryptographic Algorithm: TrueCrypt hidden volume for data concealment) |
| **APT Groups** | APT29 (Cozy Bear): uses steganographic techniques to conceal command-and-control data within image files; Lazarus Group: embeds encoded payloads and paths in obfuscated JavaScript for C2 communication and data staging |

---

## Attack Summary

```
nmap → port 22 (SSH), port 80 (HTTP)
  → wget Challenge.png from web root
  → exiftool Challenge.png → Comment: hex string
  → hex → ASCII → Base64 → decoded password/hint
  → page source: obfuscated eval() JavaScript block
  → JS eval unpack → hex string → "alert('mulder.fbi')"
  → Burp Suite: intercept request → session cookie contains URL path
  → construct download URL: http://target/<path>/mulder.fbi
  → file mulder.fbi → TrueCrypt volume
  → python tcsteg.py mulder.fbi → hidden drive detected
  → VeraCrypt: mount hidden volume with password from Step 1
  → ls /media/veracrypt1/ → flag1.txt + flag2.txt
  → cat flags
```

---

## Methodology

1. Host discovery and port scan: SSH and HTTP only
2. Download and analyze `Challenge.png` for EXIF metadata
3. Decode hex string from EXIF comment: hex to ASCII to Base64 decode
4. Unpack JavaScript `eval()` obfuscation: extract hex string and decode to filename
5. Intercept HTTP session cookie with Burp Suite to discover hidden file path
6. Download `mulder.fbi` TrueCrypt container from constructed URL
7. Detect hidden steganographic volume using `tcsteg.py`
8. Mount hidden volume with VeraCrypt and the password from Step 3
9. Read both flags from the mounted volume

---

## Step 1 — Host Discovery and Port Scan

Identify the target and enumerate services:

```bash
sudo netdiscover -i eth1 -r 192.168.1.0/24
# Target: 192.168.1.101

export TARGET=192.168.1.101
nmap -A $TARGET
```

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.x
80/tcp open  http    Apache httpd 2.4.x
```

Only two ports. SSH and HTTP. No obvious web application frameworks. The attack surface is almost entirely forensic.

**MITRE ATT&CK:** T1046 — Network Service Discovery

---

## Step 2 — EXIF Metadata Analysis

Download the main web image and analyze its EXIF metadata. EXIF fields are frequently overlooked during web assessments but can contain critical information placed by challenge designers and, in real engagements, accidentally by developers or cameras.

```bash
mkdir /tmp/spydersec && cd /tmp/spydersec

wget http://$TARGET/Challenge.png
file Challenge.png
exiftool Challenge.png
```

The EXIF `Comment` field contains a long hex string:

```
Comment: 4d6f6c646572...  (long hex string)
```

Decode the hex to ASCII:

```bash
exiftool Challenge.png | grep -i comment | awk -F': ' '{print $2}' | xxd -r -p
# Output: a Base64-encoded string
```

Decode the Base64:

```bash
exiftool Challenge.png | grep -i comment | awk -F': ' '{print $2}' | xxd -r -p | base64 -d
```

The final decoded output is the password for the TrueCrypt/VeraCrypt hidden volume. Save it.

```bash
# Save for later
PASSWORD=$(exiftool Challenge.png | grep -i comment | awk -F': ' '{print $2}' | xxd -r -p | base64 -d)
echo "Password: $PASSWORD"
```

**Real-world note:** EXIF metadata extraction is a standard step in digital forensics investigations. In real-world incident response, EXIF data in images exfiltrated by threat actors has revealed GPS coordinates, device fingerprints, and encoded C2 communication channels. APT29 uses image EXIF fields to embed encoded configuration data for implants, making EXIF analysis essential in malware investigations.

**MITRE ATT&CK:** T1027 — Obfuscated Files or Information; T1552.001 — Credentials in Files (via EXIF)

---

## Step 3 — JavaScript Eval Unpacking

Inspect the web page source for obfuscated JavaScript:

```bash
curl -s http://$TARGET/ | grep -A 5 "eval("
```

The homepage contains a packed `eval(...)` block, a common JavaScript obfuscation technique that uses `p,a,c,k,e,d` encoding or similar:

```javascript
eval(function(p,a,c,k,e,d){...}(...))
```

**To unpack manually:**

1. Copy the entire `eval(...)` block
2. Replace `eval(` with `console.log(` (or paste into browser console with the outer `eval` removed)
3. Or use an online unpacker (e.g., `http://jsbeautifier.org/` or `https://beautifier.io/`)

**Alternatively with Node.js:**

```bash
# Save the eval block to a file, replace eval with console.log
node -e "$(cat eval_block.js | sed 's/^eval(/console.log(/')"
```

The unpacked output reveals another hex string. Decode it:

```bash
echo "4d756c6465722e666269" | xxd -r -p
# Output: mulder.fbi
```

The target file is `mulder.fbi`.

**MITRE ATT&CK:** T1027 — Obfuscated Files or Information; T1027.010 — Command Obfuscation

---

## Step 4 — Cookie Analysis and URL Construction

The file path for `mulder.fbi` is not directly accessible from the web root. It is disclosed via the session cookie. Use Burp Suite to intercept a request to the target:

**Setup Burp Suite:**

1. Configure browser proxy: `127.0.0.1:8080`
2. Navigate to `http://$TARGET/`
3. Intercept the request in Burp Suite Proxy

**Examine the Cookie header:**

```
Cookie: <name>=<URL-encoded-path>
```

URL-decode the cookie value:

```bash
echo "<cookie_value>" | python3 -c "import sys, urllib.parse; print(urllib.parse.unquote(sys.stdin.read().strip()))"
```

The decoded cookie contains a directory path. Append `mulder.fbi` to construct the download URL:

```
http://192.168.1.101/<path>/mulder.fbi
```

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1539 — Steal Web Session Cookie (defensive awareness)

---

## Step 5 — Download and Identify the TrueCrypt Container

Download the file and identify its type:

```bash
cd /tmp/spydersec

curl -s -o mulder.fbi "http://$TARGET/<path>/mulder.fbi"
file mulder.fbi
# TrueCrypt volume
ls -lh mulder.fbi
```

The file is identified as a TrueCrypt volume. TrueCrypt was discontinued in 2014; VeraCrypt is its maintained successor and reads TrueCrypt volumes.

**MITRE ATT&CK:** T1074.001 — Data Staged: Local Data Staging (understanding data concealment techniques)

---

## Step 6 — Hidden Volume Detection with tcsteg.py

TrueCrypt (and VeraCrypt) supports "hidden volumes": a second, plausibly deniable encrypted volume hidden within the free space of an outer volume. A specialized tool, `tcsteg.py`, detects the presence of hidden volumes by analyzing entropy patterns:

```bash
# Clone if not available
git clone https://github.com/ligos/tcsteg.git
cd tcsteg

python tcsteg.py /tmp/spydersec/mulder.fbi
# Output: "Hidden drive detected"
```

The presence of a hidden volume is confirmed. The outer volume password and the hidden volume password are different.

**What is a TrueCrypt hidden volume?** When someone accesses the outer volume with the outer password, they see decoy content (or nothing). The hidden volume is invisible and cannot be proven to exist. Law enforcement agencies and threat actors use this technique for plausible deniability. The hidden content is only accessible with the correct hidden volume password, which we obtained from the EXIF metadata.

**MITRE ATT&CK:** T1027.004 — Obfuscated Files: Compile After Delivery (analogous concept: hidden within container)

---

## Step 7 — VeraCrypt Hidden Volume Mounting

Mount the hidden volume using VeraCrypt with the password recovered in Step 2:

**GUI method:**

1. Open VeraCrypt
2. Click "Select File" and choose `/tmp/spydersec/mulder.fbi`
3. Click "Mount"
4. When prompted for password, enter `$PASSWORD`
5. Check "Mount as hidden volume" or simply try mounting with the hidden password

**CLI method:**

```bash
# Install VeraCrypt if not present
sudo apt-get install veracrypt

# Mount using CLI
veracrypt --text \
  --mount /tmp/spydersec/mulder.fbi \
  /media/veracrypt1 \
  --password "$PASSWORD" \
  --protect-hidden no
```

After mounting, browse the volume:

```bash
ls -la /media/veracrypt1/
# flag1.txt  flag2.txt
```

**MITRE ATT&CK:** T1078 — Valid Accounts (using discovered credentials to access protected data)

---

## Step 8 — Flag Capture

Read both flags:

```bash
cat /media/veracrypt1/flag1.txt
cat /media/veracrypt1/flag2.txt
```

Unmount when finished:

```bash
veracrypt --text --dismount /media/veracrypt1
```

(☞ﾟヮﾟ)☞ Both flags captured. The spider's web is untangled. gg, dude.

**MITRE ATT&CK:** T1005 — Data from Local System

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used For |
|---|---|---|---|
| Password (from EXIF) | (decoded from hex→base64 in EXIF Comment) | Challenge.png EXIF metadata | VeraCrypt hidden volume password |
| Target filename | `mulder.fbi` | JavaScript eval unpack: hex decode | Constructing download URL |
| Hidden file path | (from URL-decoded session cookie) | Burp Suite cookie interception | Download URL construction |
| Flag 1 | (varies) | /media/veracrypt1/flag1.txt | CTF proof |
| Flag 2 | (varies) | /media/veracrypt1/flag2.txt | CTF proof |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Password encoded in EXIF metadata | EXIF fields are routinely overlooked in web app security assessments; threat actors embed covert data in image EXIF fields for C2 communication | Always run `exiftool` on images from untrusted sources; strip EXIF before publishing images publicly |
| 2 | Internal path disclosed via session cookie | Cookie values containing URL-encoded paths expose internal directory structure | Cookie contents should never reveal internal paths; use opaque session identifiers |
| 3 | JavaScript obfuscation hides critical filename | Obfuscation provides no security: any client-side code is trivially reversible | Move secrets server-side; obfuscation is not encryption |
| 4 | TrueCrypt hidden volume provides plausible deniability | TrueCrypt/VeraCrypt hidden volumes are used by threat actors for covert data storage and by whistleblowers for protection | Organizations should test for hidden volumes in forensics investigations; tcsteg.py and VeraCrypt are the tools |
| 5 | Sensitive file served from web-accessible path | Container files in the web root can be downloaded and analyzed by any visitor | Keep sensitive files outside the web root; use authentication and signed URLs for download endpoints |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Reconnaissance | Discovery | File and Directory Discovery | T1083 |
| Collection | Collection | Data from Local System | T1005 |
| Defense Evasion | Defense Evasion | Obfuscated Files or Information | T1027 |
| Defense Evasion | Command Obfuscation | Command Obfuscation | T1027.010 |
| Credential Access | Credential Access | Credentials in Files (EXIF) | T1552.001 |
| Exfiltration | Data Staged | Local Data Staging | T1074.001 |
| Initial Access | Valid Accounts | Valid Accounts (VeraCrypt) | T1078 |

---

## Remediation and Containment

### Technical Fixes

1. **Strip EXIF metadata before publishing images**: use `exiftool -all= image.png` to remove all EXIF data before uploading to web servers
2. **Remove internal paths from session cookies**: use opaque session identifiers (e.g., random UUID); never encode file system paths in cookies
3. **Move obfuscated JavaScript hints server-side**: all logic that reveals file paths or filenames must be on the server, never in client-side code
4. **Move sensitive files outside the web root**: configure Apache/Nginx to serve downloads via authenticated endpoints only
5. **Implement download authentication**: use signed, expiring URLs for all file downloads; log all download attempts

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Audit all web-accessible files for sensitive data |
| Protect | Data Security | Strip EXIF before publishing; move secrets server-side |
| Protect | Access Control | Authenticate all file download endpoints; signed URLs |
| Detect | Anomalies and Events | Alert on bulk file downloads; monitor cookie anomalies |
| Respond | Response Planning | Revoke exposed session tokens; audit download logs |
| Recover | Recovery Planning | Move sensitive files; regenerate session signing keys |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| SC-28 | Protection of Information at Rest | Encrypt sensitive files; strip EXIF before publishing |
| AC-3 | Access Enforcement | Authenticate download endpoints; restrict file access |
| SC-8 | Transmission Confidentiality | Encrypt downloads over TLS; use signed download URLs |
| SI-12 | Information Management | Do not embed paths or credentials in cookie values |
| CM-7 | Least Functionality | Remove EXIF stripping gaps from deployment pipelines |

### CISA KEV

Data concealment via steganography and obfuscated metadata aligns with CISA guidance on insider threat and advanced persistent threat techniques (AA21-321A) describing covert data staging methods used before exfiltration.

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Asset, Change, and Configuration Management (ASSET) | Manage IT Asset Inventory | MIL2 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |
| Situational Awareness (SITUATION) | Perform Event and Incident Detection | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Application Configuration Hardening (strip EXIF; move secrets server-side; authenticate downloads)
- **D3-HBPI** — Harden Build Pipeline Integrity (automate EXIF stripping in deployment pipeline)
- **D3-SFA** — Software Feature Analysis (audit client-side JavaScript for embedded paths and credentials)

---

## Final Thoughts

SpyderSec: Challenge is a wild ride. No CVEs, no Metasploit, no brute-force. Just layers of encoding, metadata analysis, and cryptographic container mounting. This box demonstrates that "hacking" is often less about exploiting code and more about reading what is already there, in EXIF fields, in JavaScript comments, in cookie values.

The multi-layer steganography chain (EXIF hex to Base64 to VeraCrypt hidden volume) is directly applicable to digital forensics investigations. `tcsteg.py` and VeraCrypt are real tools used in real investigations. Learning to use them in a CTF context is genuine professional development.

This box earns its place in the "unique experience" tier. Legit one of the most creative CTF machines ever made. gg.

Thanks guys!! (❍ᴥ❍ʋ)
