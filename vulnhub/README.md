# VulnHub — Writeups

Boot2root VM writeups from [VulnHub](https://www.vulnhub.com/).

> Each VM was run locally in VirtualBox/VMware (host-only or NAT network). All techniques were performed in an isolated lab environment.

---

## Machines

| VM | Difficulty | OS | Techniques | Status |
|----|-----------|-----|-----------|--------|
| [Tr0ll: 1](tr0ll-1/) | Easy | Linux | FTP enum, pcap analysis, SSH brute, SUID privesc | ✅ Complete |
| [Tr0ll: 2](tr0ll-2/) | Medium | Linux | FTP, web enum, Shellshock (CVE-2014-6271), BOF privesc | ✅ Complete |
| [Tr0ll: 3](tr0ll-3/) | Hard | Linux | FTP, multi-user chain, RSA key, root escalation | ⚠️ Partial |
| [GoldenEye: 1](goldeneye-1/) | Intermediate | Linux | JS recon, POP3 auth, Moodle RCE (CVE-2013-3630), overlayfs LPE | ✅ Complete |
| [Axis2 + Tomcat Manager](axis2-tomcat-manager/) | Medium | Linux | SSRF → creds, WAR deploy, JSP webshell, DirtyCOW (CVE-2016-5195) | ✅ Complete |
| [My Tomcat Host](my-tomcat-host/) | Medium | Linux | Default creds, WAR deploy, sudo java privesc | ✅ Complete |
| [Thales: 1](thales-1/) | Easy | Linux | Tomcat brute-force, MSF shell, SSH key + john, cron script injection | ✅ Complete |

---

## Techniques Index

| Technique | VMs |
|-----------|-----|
| FTP anonymous / credential reuse | Tr0ll 1, 2, 3 |
| pcap analysis (Wireshark/tcpdump) | Tr0ll 1 |
| Shellshock (CVE-2014-6271) | Tr0ll 2 |
| Buffer overflow (SUID) | Tr0ll 1, 2 |
| POP3 credential chain | GoldenEye 1 |
| Moodle RCE via aspell | GoldenEye 1 |
| overlayfs LPE (CVE-2015-1328) | GoldenEye 1 |
| SSRF for credential extraction | Axis2 + Tomcat |
| Tomcat WAR deploy / manager | Axis2, My Tomcat Host, Thales |
| JSP webshell | Axis2, My Tomcat Host |
| DirtyCOW (CVE-2016-5195) | Axis2 + Tomcat |
| sudo NOPASSWD misconfig | My Tomcat Host |
| SSH key cracking (john) | Thales |
| Writable cron script injection | Thales |

---

## Setup

All VMs were downloaded from VulnHub and imported into VirtualBox with a host-only adapter. The attacker machine is Kali Linux on the same host-only network.

```bash
# Discover VM IP after boot
sudo netdiscover -i eth1 -r 192.168.56.0/24
# or
sudo arp-scan -l
```
