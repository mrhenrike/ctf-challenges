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

Phase 1 (27 VMs) + Phase 2 (100 VMs) = **127 total documented**.

| VM | Difficulty | Key Techniques |
|----|-----------|----------------|
| [HA: Joker](ha-joker/) | Medium | HTTP Basic Auth brute, Joomla PHP shell, LXD container mount |
| [SecTalks BNE0x00: Minotaur](sectalks-bne0x00-minotaur/) | Easy | WPScan + CeWL, Slideshow Gallery MSF, shadow.bak crack, sudo |
| [HA: Dhanush](ha-dhanush/) | Medium | CeWL + Hydra SSH, sudo cp key injection, sudo zip GTFOBin |
| [HA: Chanakya](ha-chanakya/) | Medium | dirb .txt + ROT13, pcap FTP creds, chkrootkit MSF local exploit |
| [Raven: 2](raven-2/) | Intermediate | PHPMailer 5.2.6 RCE CVE-2016-10033, UDF EDB-1518, SUID find |
| [SkyDog: 2016](skydog-2016/) | Easy | hex decode, TLS cert OSINT, User-Agent spoofing, steghide, Volatility |
| [CyberSploit: 1](cybersploit-1/) | Easy | HTML comment/robots.txt, kernel CVE-2015-1328 EDB-37292 |
| [Matrix: 3](matrix-3/) | Hard | hidden dir traversal, DOS binary Ghidra reversal, rbash escape, sudo oracle |
| [Broken Gallery](broken-gallery/) | Easy | hex-to-JPEG creds, sudo timedatectl, time-triggered init script |
| [DC: 8](dc-8/) | Medium | Drupal SQLi sqlmap, PHP text filter RCE, Exim 4.89 SUID CVE-2019-10149 |
| [Five86: 1](five86-1/) | Medium | OpenNetAdmin 18.1.1 EDB-47772, crunch+john .htpasswd, sudo cp SSH key |
| [Kioptrix: Level 1.3 #4](kioptrix-level-13-4/) | Easy | User-agent IE6 bypass, phptax MSF, FreeBSD 9.0 kernel EDB-28718 |
| [DPWWN: 2](dpwwn-2/) | Medium | WPScan Site Editor 1.1.1 LFI EDB-44340, NFS shell plant, SUID find |
| [Hacker Fest: 2019](hacker-fest-2019/) | Easy | WP Google Maps SQLi REST API, john (kittykat1), wp_admin_shell_upload |
| [Sunset: Decoy](sunset-decoy/) | Easy | save.zip zip2john crack, /etc/shadow crack, rbash bash --noprofile, pspy |
| [DevGuru: 1](devguru-1/) | Medium | .git dump, October CMS RCE, Gitea pre-receive hook, CVE-2019-14287 |
| [The Necromancer: 1](the-necromancer-1/) | Easy | UDP/TCP multi-flag, steganography, GDB exploit, 802.11 cap aircrack-ng |
| [Enubox: Mattermost](enubox-mattermost/) | Medium | TFTP anon read, Zoom plugin FTP creds, Ghidra hex constant, sudo bash |
| [UA: Literally Vulnerable](ua-literally-vulnerable/) | Easy | FTP anon + password list, WordPress brute, MSF shell, SUID PWD hijack |
| [Sunset: Sunrise](sunset-sunrise/) | Easy | MySQL unauthenticated root, INTO OUTFILE webshell, root shell |
| [TBBT: Fun with Flags](tbbt-funwithflags/) | Easy | WordPress Reflex Gallery MSF RCE, writable cron, FTP + ZIP + steghide (7 flags) |
| [HappyCorp: 1](happycorp-1/) | Easy | NFS no_root_squash UID spoof, SSH key crack (john), rbash escape, SUID cp |
| [SpyderSec: Challenge](spydersec-challenge/) | Medium | EXIF hex decode, JS eval unpack, TrueCrypt hidden volume |
| [HA: Sherlock](ha-sherlock/) | Medium | Morse decode, OurSecret steg, Hydra POP3, Volatility WinXP notepad ROT13 |
| [HA: ISRO](ha-isro/) | Medium | base64 → path, TrueCrypt, steghide, LFI PHP revshell, MySQL root, world-writable /etc/passwd |
| [Seattle: v0.3](seattle-v03/) | Easy | sqlmap cookie SQLi, admin login, netdiscover + Nikto |
| [HA: Natraj](ha-natraj/) | Easy | dirb LFI (file.php), SSH log poisoning, apache2.conf user → mahakal, sudo nmap |
| [DPWWN: 1](dpwwn-1/) | Easy | MySQL blank root, ssh.users table, writable cron script |
| [Sputnik: 1](sputnik-1/) | Medium | Splunk Free no-auth, scripted input app upload, Python reverse shell |
| [Typhoon: 1.02](typhoon-102/) | Medium | MongoDB admin no-auth, CVE-2015-1328 overlayfs, Tomcat WAR, Drupalgeddon2 |
| [HA: Pandavas](ha-pandavas/) | Medium | SNMP + CeWL, SSH brute MSF, Docker FTP/MySQL, sudo (5 flags) |
| [DC: 7](dc-7/) | Medium | OSINT Twitter/GitHub, Drupal SSH, drush admin reset, PHP filter, writable cron |
| [HA: Chakravyuh](ha-chakravyuh/) | Hard | multi-user chain, credential reuse, privesc chain |
| [MaskCrafter: 1.1](maskcrafter-11/) | Medium | anon FTP, /debug cmd injection, MySQL, ZIP, sudo socat/dpkg fpm |
| [Panabee: 1](panabee-1/) | Easy | SMB note, Hydra FTP, writable home, sudo status.py, pspy tmux socket |
| [Breach: 1](breach-1/) | Intermediate | SSL cert email, Java .jks crack, Tomcat creds, pcap creds, OSSEC path |
| [CengBox: 1](cengbox-1/) | Easy | WordPress vuln, admin shell upload, SUID/sudo privesc |
| [DarkHole: 2](darkhole-2/) | Medium | git log credentials, SQLi, SSH, sudo privesc |
| [KB-VULN: 3](kb-vuln-3/) | Easy | web enum, credential reuse, SUID/sudo escalation |
| [GitRoot: 1](gitroot-1/) | Easy | exposed .git, code review → creds, sudo privesc |
| [Sidney: 0.2](sidney-02/) | Easy | web recon, SUID/sudo escalation |
| [Sunset: Dawn](sunset-dawn/) | Easy | writable SMB share executed by cron, SUID /usr/bin/zsh |
| [LAMPSecurity: CTF6](lampsecurity-ctf6/) | Medium | exposed /sql/db.sql, PHP file upload, Meterpreter, udev EDB-8478 |
| [Healthcare: 1](healthcare-1/) | Medium | OpenEMR 4.1.0 SQLi, PHP config.php replace, SUID healthcheck PATH hijack |
| [DC: 9](dc-9/) | Medium | SQLi → LFI /etc/knockd.conf → port knock → Hydra SSH → sudo file-append |
| [Sunset: Nightfall](sunset-nightfall/) | Easy | enum4linux, Hydra FTP, SSH key inject, SUID find lateral, sudo cat shadow |
| [BossPlayersCTF: 1](bossplayersctf-1/) | Easy | Triple Base64 HTML comment, hidden PHP RCE, SUID find root |
| [Hogwarts: Bellatrix](hogwarts-bellatrix/) | Medium | LFI via PHP param, SSH log poisoning, john cracks hash, sudo vim GTFOBins |
| [PowerGrid: 1.0.1](powergrid-101/) | Hard | HTTP Basic Auth, Roundcube RCE EDB-40892, GPG decrypt SSH key, Docker pivot |
| [Presidential: 1](presidential-1/) | Hard | config.php.bak leak, vhost gobuster, phpMyAdmin RCE, tar capabilities |
| [MuzzyBox: 1](muzzybox-1/) | Medium | NoSQL injection, Werkzeug debug console Python shell, SSTI + SSH + PATH hijack |
| [Born2Root: 2](born2root-2/) | Easy | CeWL + Joomla brute, PHP template shell, hardcoded creds, broad sudo |
| [FowSniff: 1](fowsniff-1/) | Easy | OSINT Pastebin hash dump, MD5 crack, Metasploit POP3 brute, writable MOTD |
| [Tommy Boy: 1](tommy-boy-1/) | Medium | 5 flags: robots.txt, EXIF MD5, FTP, WPScan, .png→.php rename (LOOT.zip) |
| [Xerxes: 1](xerxes-1/) | Hard | QR code → Base64 → pixel stego → Brainfuck, .pht upload bypass, SUID pickle RCE |
| [Silky CTF: 0x01](silky-ctf-0x01/) | Easy | robots.txt + JS partial pw, Crunch + Hydra SSH, SUID /usr/bin/sky PATH hijack |
| [CengBox: 2](cengbox-2/) | Medium | anon FTP, vhost admin, Gila CMS RCE, MOTD SUID nano, /etc/passwd |
| [LemonSqueezy: 1](lemonsqueezy-1/) | Easy | WP creds, phpMyAdmin INTO OUTFILE, writable /etc/logrotate.d/ root cron |
| [Mumbai: 1](mumbai-1/) | Medium | web enum, credential chain, SUID/sudo privesc |
| [The Library: 2](the-library-2/) | Easy | web enum, credential reuse, sudo privesc |
| [HA: Forensics](ha-forensics/) | Medium | EXIF flag, PGP decrypt fcrackzip, pypykatz LSASS, Docker pivot, Autopsy (4 flags) |
| [Misdirection: 1](misdirection-1/) | Easy | port 8080 Apache, /debug PHP shell, MSF Meterpreter, writable /etc/passwd |
| [MHZ: CxF C1F](mhz-cxf-c1f/) | Easy | notes.txt SSH creds, steghide, su mhz_c1f, sudo su |
| [Victim: 1](victim-1/) | Easy | WP cap aircrack-ng (p4ssword), world-writable PHP revshell, nohup SUID |
| [HA: Narak](ha-narak/) | Medium | TFTP → creds.txt base64, WebDAV cadaver PHP shell, Brainfuck, MOTD SUID nano |
| [Lord Of The Root: 1.0.1](lord-of-the-root-101/) | Medium | port knocking (1,2,3), Base64 hint, SQLMap, SSH brute, kernel exploit 39166.c |
| [HA: Vedas](ha-vedas/) | Medium | SNMP enum, CeWL + dirb, SQLi EDB-46635, Meterpreter port-forward (4 flags) |
| [Tempus Fugit: 3](tempus-fugit-3/) | Hard | Jinja2 SSTI, SQLCipher key, ProcessWire module upload, QR-code 2FA, SUID ping |
| [Casino Royale: 1](casino-royale-1/) | Hard | PokerMax SQLi, Snowfox CSRF SMTP phishing, XXE, Hydra FTP, SUID PATH hijack |
| [HA: Rudra](ha-rudra/) | Medium | NFS world-export, LFI nandi.php, MySQL → Cloakify emoji-steg, CVE-2019-14287 |
| [The Library: 1](the-library-1/) | Easy | SQLi via cookie (sqlmap), FTP PHP shell upload, password reuse su root |
| [Broken: 2020-1](broken-2020-1/) | Easy | command injection, SUID/sudo privesc |
| [Corrosion: 2](corrosion-2/) | Medium | backup.zip fcrackzip, Tomcat WAR upload, look capability shadow, Python lib hijack |
| [Relevant: 1](relevant-1/) | Easy | wp-file-manager 6.7 RCE CVE-2020-25213, SHA-1 crack, sudo node GTFOBins |
| [Empire: LupinOne](empire-lupinone/) | Medium | ffuf /~secret/, Base58 SSH key, john passphrase, webbrowser.py hijack, sudo pip |
| [My File Server: 1](my-file-server-1/) | Easy | anon FTP write → SSH key inject, Dirty COW CVE-2016-5195 EDB-40616 |
| [Loly: 1](loly-1/) | Easy | WPScan brute, malicious plugin shell, wp-config pw reuse, kernel CVE-2017-16995 |
| [AI: Web 1](ai-web-1/) | Easy | SQL injection User ID, sqlmap --os-shell, world-writable /etc/passwd |
| [Nezuko: 1](nezuko-1/) | Easy | Webmin 1.920 RCE CVE-2019-15107, zenitsu hash crack, writable root cron |
| [Photographer: 1](photographer-1/) | Easy | SMB mailsent.txt creds, Koken CMS upload bypass, SUID php7.2 GTFOBins |
| [DC: 5](dc-5/) | Medium | LFI + nginx log poisoning, screen 4.5.0 SUID EDB-41154 |
| [HA: Avengers Arsenal](ha-avengers-arsenal/) | Medium | Git leak, whitespace stego, zip/PDF crack, Splunk RCE, SUID PATH hijack (5 flags) |
| [VulnUni: 1.0.1](vulnuni-101/) | Easy | eClass SQLi credential extraction, authenticated PHP file upload |
| [GrimTheRipper: 1](grimtheripper-1/) | Easy | Double-Base64 hidden WP path, wpscan brute, wp_admin_shell_upload, EDB-37292 |
| [Serial: 1](serial-1/) | Medium | PHP deserialization RFI chain, SSH leaked creds, sudo vim GTFOBins |
| [Djinn: 1](djinn-1/) | Medium | FTP anon, base64 filter bypass /wish cmd injection, Python 2 input() RCE |
| [EVM: 1](evm-1/) | Easy | WordPress brute MSF, plaintext root password in config |
| [Sunset: Midnight](sunset-midnight/) | Easy | MySQL brute, DB pw swap, WP theme RCE, PATH hijack SUID |
| [Matrix: 1](matrix-1/) | Easy | Brainfuck-encoded creds, Hydra SSH, rbash vi escape, sudo su |
| [Zeus: 1](zeus-1/) | Medium | Jailkit chroot escape, SUID binary PATH hijack |
| [CyNix: 1](cynix-1/) | Medium | LFI hidden form, SSH key theft, LXD privesc |
| [HackDay: Albania](hackday-albania/) | Easy | robots.txt, SQLi auth bypass, PHP upload ext bypass, writable /etc/passwd |
| [MinU: v2](minu-v2/) | Medium | SVG XXE, .ash_history read, SUID micro editor |
| [Hackme: 1](hackme-1/) | Easy | sqlmap DB dump, PHP shell upload admin panel, SUID touchmenot binary |
| [TopHatSec: Freshly](tophatsec-freshly/) | Easy | SQLi credential dump, WordPress theme PHP injection, password reuse to root |
| [TopHatSec: Zorz](tophatsec-zorz/) | Easy | three file upload bypasses: extension rename, GIF98 magic bytes, no validation |
| [CryptoBank: 1](cryptobank-1/) | Hard | vhost + time-based SQLi, GitHack .git, cmd injection, Solr 8.1.1 RCE EDB-47572 |
| [Gears of War: Ep1](gears-of-war-ep1/) | Easy | SMB ZIP, crunch fcrackzip, SSH restricted shell bypass, SUID cp passwd overwrite |
| [VulnOS: 2](vulnos-2/) | Medium | OpenDocMan 1.2.7 SQLi EDB-32075, webmin SSH, Ubuntu 14.04 overlayfs EDB-37292 |
| [So Simple: 1](so-simple-1/) | Easy | WP Social Warfare 3.5.0 RCE CVE-2019-9978, SSH key, sudo path traversal |

---

See [PIPELINE.md](PIPELINE.md) for the full list of 308 VMs planned.
