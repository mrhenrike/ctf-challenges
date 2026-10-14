# VulnHub — Writeups

Boot2root VM writeups from [VulnHub](https://www.vulnhub.com/).

> Each VM was run locally in VirtualBox/VMware (host-only or NAT network). All techniques were performed in an isolated lab environment.

---

## Machines

| VM | Difficulty | OS | Techniques | Status |
|----|-----------|-----|-----------|--------|
| [Kioptrix: Level 1](kioptrix-1/) | Easy | Linux | Samba trans2open (CVE-2003-0201), Apache mod_ssl | ✅ Complete |
| [Kioptrix: Level 1.1](kioptrix-2/) | Easy | Linux | SQLi login bypass, command injection, kernel 2.6 LPE | ✅ Complete |
| [Kioptrix: Level 1.2](kioptrix-3/) | Medium | Linux | sqlmap, SSH, sudo ht sudoers edit | ✅ Complete |
| [Kioptrix: Level 1.3](kioptrix-4/) | Medium | Linux | SQLi, lshell escape, MySQL sys_exec UDF, SUID find | ✅ Complete |
| [DC: 1](dc-1/) | Easy | Linux | Drupal drupalgeddon2 (MSF), SUID find privesc | ✅ Complete |
| [DC: 2](dc-2/) | Easy | Linux | WordPress, CeWL wordlist, rbash escape, sudo git | ✅ Complete |
| [DC: 3](dc-3/) | Medium | Linux | Joomla SQLi, PHP reverse shell, kernel exploit | ✅ Complete |
| [DC: 4](dc-4/) | Easy | Linux | Command injection (Admin panel), Hydra SSH, sudo teehee | ✅ Complete |
| [Mr. Robot: 1](mr-robot/) | Medium | Linux | WordPress brute (fsocity.dic), Theme Editor shell, nmap SUID | ✅ Complete |
| [Stapler: 1](stapler/) | Medium | Linux | FTP anon, SMB enum, WordPress brute, webshell, kernel LPE | ✅ Complete |
| [SickOs: 1.1](sickos-1-1/) | Easy | Linux | SQUID proxy, Shellshock (CVE-2014-6271), writable cron | ✅ Complete |
| [LazySysAdmin: 1](lazysysadmin/) | Easy | Linux | SMB share, WordPress config.php, SSH, sudo su | ✅ Complete |
| [RickdiculouslyEasy: 1](rickdiculouslyeasy/) | Easy | Linux | FTP anon, multi-service (9 flags), SSH, sudo | ✅ Complete |
| [NullByte: 1](nullbyte/) | Medium | Linux | steghide, SQLi, PATH hijack via SUID procmail | ✅ Complete |
| [BSides Vancouver: 2018](bsides-vancouver-2018/) | Easy | Linux | WordPress, SSH brute, cron injection | ✅ Complete |
| [Toppo: 1](toppo-1/) | Easy | Linux | notes.txt plaintext creds, SUID mawk/awk privesc | ✅ Complete |
| [Symfonos: 1](symfonos-1/) | Medium | Linux | SMB creds, Mail Masta LFI, SMTP log poisoning, SUID PATH hijack | ✅ Complete |
| [Symfonos: 2](symfonos-2/) | Medium | Linux | SMB log.txt, Hydra SSH, LibreNMS RCE, sudo mysql escape | ✅ Complete |
| [Prime: 1](prime-1/) | Medium | Linux | Parameter fuzzing, LFI, WordPress code injection, kernel exploit | ✅ Complete |
| [Sar: 1](sar/) | Easy | Linux | robots.txt, sar2HTML RCE (CVE-2019-19634), writable cron | ✅ Complete |
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
| FTP anonymous / credential reuse | Tr0ll 1, 2, 3, RickdiculouslyEasy, NullByte |
| pcap analysis (Wireshark/tcpdump) | Tr0ll 1 |
| Shellshock (CVE-2014-6271) | Tr0ll 2, SickOs 1.1 |
| Buffer overflow (SUID) | Tr0ll 1, 2 |
| SMB enumeration (enum4linux, smbclient) | LazySysAdmin, Symfonos 1, Symfonos 2 |
| SQL Injection (login bypass, sqlmap) | Kioptrix 2, 4, DC-1, DC-2, DC-3, NullByte |
| Samba exploit (trans2open CVE-2003-0201) | Kioptrix 1 |
| Command injection (web panels) | Kioptrix 2, DC-4 |
| WordPress attack (wpscan, brute, webshell) | DC-2, Mr. Robot, Stapler, BSides Vancouver, LazySysAdmin |
| Drupal exploit (drupalgeddon) | DC-1 |
| Joomla exploit (joomscan, SQLi) | DC-3 |
| PHP reverse shell (theme/plugin editor) | DC-2, DC-3, Mr. Robot, Stapler |
| LFI (Local File Inclusion) | Symfonos 1, Prime 1 |
| Log poisoning via LFI | Symfonos 1 |
| SMTP log poisoning | Symfonos 1 |
| SQUID proxy abuse | SickOs 1.1 |
| steghide (image steganography) | NullByte |
| SUID privesc (find, nmap, mawk, procmail) | Kioptrix 4, Mr. Robot, Toppo 1, NullByte |
| PATH hijacking (SUID binary) | Symfonos 1, Kioptrix 4 |
| Kernel exploits (2.6, 3.x, 4.x) | Kioptrix 2, DC-3, Prime 1, Stapler |
| sudo misconfigurations | DC-2 (git), DC-4 (teehee), LazySysAdmin (su), Toppo (awk), Symfonos 2 (mysql) |
| Writable cron script injection | SickOs 1.1, BSides Vancouver, Sar 1, Thales 1 |
| rbash escape (vi, git) | DC-2 |
| MySQL UDF / sys_exec | Kioptrix 4 |
| POP3 credential chain | GoldenEye 1 |
| Moodle RCE via aspell | GoldenEye 1 |
| overlayfs LPE (CVE-2015-1328) | GoldenEye 1 |
| SSRF for credential extraction | Axis2 + Tomcat |
| Tomcat WAR deploy / manager | Axis2, My Tomcat Host, Thales |
| JSP webshell | Axis2, My Tomcat Host |
| DirtyCOW (CVE-2016-5195) | Axis2 + Tomcat |
| SSH key cracking (john) | Thales 1 |
| LibreNMS RCE | Symfonos 2 |
| sar2HTML RCE (CVE-2019-19634) | Sar 1 |
| Parameter fuzzing (wfuzz) | Prime 1 |

---

## Setup

All VMs were downloaded from VulnHub and imported into VirtualBox with a host-only adapter. The attacker machine is Kali Linux on the same host-only network.

```bash
# Discover VM IP after boot
sudo netdiscover -i eth1 -r 192.168.56.0/24
# or
sudo arp-scan -l
```

---

## Phase 2 — Additional 100 VMs

Phase 2 added writeups for 100 more machines from the HackingArticles catalog. Each includes README, 5 screenshots, and an exploit automation script.

Categories covered: web exploitation (SQLi, LFI, RCE, upload bypass), Active Directory, git exposure, SMB enumeration, password cracking, Docker escape, custom exploits, and more.

See [PIPELINE.md](PIPELINE.md) for the full list of 308 VMs planned. Phase 1 (20 VMs) + Phase 2 (100 VMs) = 127 total documented.
