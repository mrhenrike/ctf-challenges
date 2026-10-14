# VulnHub UnknownDevice64: 2 — Hacking an Android Over the Network, No Physical Access Needed

Alright guys!! Ever wondered how sus it is that your Android phone might be sitting on a network with ADB exposed to the entire subnet? Well, dude, this VM is exactly that scenario, and it is lowkey terrifying. We are connecting to a running Android system over TCP, getting a shell, and su-ing to root with zero password prompts. Bussin.

Big shoutout to **Ajay Verma** for building a VM that raises a genuinely relevant question: how many Android devices in corporate networks right now have ADB dangling open on port 5555? The answer would make you cringe.

---

| Field | Value |
|-------|-------|
| **Level** | Beginner |
| **Target VM** | UnknownDevice64: 2 |
| **Attacker VM** | Kali Linux 2019.1 |
| **VulnHub** | https://www.vulnhub.com/entry/unknowndevice64-2,459/ |
| **Techniques** | Host discovery, Nmap enumeration, ADB remote connection, Android shell access, passwordless root escalation |
| **CVEs** | CVE-2019-2205 (ADB arbitrary file write, AOSP), general ADB-over-TCP exposure |

---

> **Context from the author:** This is an Android device running over the network. The challenge explores how easily accessible Android systems can be when ADB is left enabled in a networked environment.

---

## Attack Summary

```
[host-discovery: nmap -sn]
    |
    v
[nmap -A -T4 -p-: port 5555 -> ADB / Freeciv signature]
    |
    v
[adb connect TARGET_IP:5555]
    |
    v
[adb shell -> limited Android user shell]
    |
    v
[su root -> no password required on this device]
    |
    v
[find / -name *flag*.txt 2>/dev/null]
    |
    v
[cat /data/flag.txt (or wherever the flag lives)]
```

---

## Methodology

1. Host discovery to identify the Android device on the local network
2. Port scan revealing ADB listener on TCP 5555
3. ADB remote connection over the network
4. Android shell spawned via ADB
5. Passwordless root escalation with `su root`
6. Flag location and retrieval

---

## Step 1 — Identifying the Target

Same starting point as always: figure out who is on the network before touching anything else.

```bash
route -n
# Check the Iface and Gateway columns to identify your subnet
```

Scan for live hosts:

```bash
# Option 1: nmap ping scan
nmap -sn -T5 192.168.10.0/24

# Option 2: arp-scan (faster, fewer misses on local networks)
arp-scan --localnet --ignoredups
```

Note the IP that is not your Kali box and not your router. That is your Android device. Let us call it `TARGET_IP`.

> **MITRE ATT&CK:** T1595.001 Active Scanning: Scanning IP Blocks

---

## Step 2 — Reconnaissance: Nmap Reveals Port 5555

Full scan, all ports. ADB listens on TCP 5555 by default when network debugging is enabled.

```bash
nmap -A -T4 -p- TARGET_IP
# -A: OS detection, version detection, NSE scripts, traceroute
# -T4: aggressive timing (safe in a local lab)
# -p-: all 65535 TCP ports
```

Expected output:

```
5555/tcp open  freeciv?
```

Nmap fingerprints this as Freeciv (a turn-based strategy game) because ADB's network protocol does not have an official Nmap signature. But here is the thing: Freeciv on an Android device is basically a confirmation. Android is the only common OS where Freeciv and ADB coexist on the same host, and port 5555 is the canonical ADB-over-TCP port. The OS detection may show Linux (which is correct: Android runs on a Linux kernel).

> **MITRE ATT&CK:** T1595.002 Active Scanning: Vulnerability Scanning, T1046 Network Service Discovery

---

## Step 3 — Connecting via ADB (Android Debug Bridge)

> **What is ADB?**
> ADB (Android Debug Bridge) is a versatile command-line tool that allows communication with an Android device. It provides shell access, file transfer, app installation, and log access. Normally it is used over USB, but Android supports ADB over TCP (port 5555) when "USB Debugging" and "Network Debugging" are enabled in Developer Options. When this is left enabled on a networked device, anyone on the same network can connect without authentication.
> Reference: https://developer.android.com/studio/command-line/adb

Install ADB if it is not already present:

```bash
apt install adb -y
```

Connect to the Android device:

```bash
adb connect TARGET_IP:5555
```

Expected output:

```
connected to TARGET_IP:5555
```

If you get "unable to connect", the port is blocked or ADB is not running. In this VM it connects cleanly.

Now spawn a shell:

```bash
adb shell
```

You should get a shell prompt like:

```
shell@android:/ $
```

You are on the Android device as a limited shell user. ( ͡° ͜ʖ ͡°) Already a win, but not root yet.

> **Real-world note:** This exact technique was used in the "Stagefright" attack wave and later exploits targeting Android devices exposed on corporate Wi-Fi and IoT networks. In 2018, researchers found over 40,000 Android devices with ADB exposed to the internet, many of them silently mining cryptocurrency after being compromised via ADB with zero authentication. Reference: https://www.bleepingcomputer.com/news/security/over-40-000-android-devices-hacked-using-exposed-adb-ports/

> **MITRE ATT&CK:** T1133 External Remote Services, T1190 Exploit Public-Facing Application

---

## Step 4 — Passwordless Root Escalation

> **Why do Android devices often allow passwordless root?**
> Android is based on the Linux kernel and inherits its user model. However, most consumer and emulated Android devices are configured to allow `su` (switch user) without a password for the root account, especially when running in development/debug mode. Android rooting is also often intentionally permissive: devices sold as rooted, emulators, CTF VMs, and developer-configured devices routinely have root available with no credentials. This is by design for the use case, but catastrophic when those devices end up on a production network.

From inside the ADB shell, escalate to root:

```bash
su root
```

Expected prompt change:

```
root@android:/ #
```

That is it. No password. No prompt. Just root. ಠᴗಠ

Verify with:

```bash
id
# uid=0(root) gid=0(root)
whoami
# root
```

> **MITRE ATT&CK:** TA0004 Privilege Escalation, T1078 Valid Accounts (default/no-password root)

---

## Step 5 — Locating and Reading the Flag

Search for the flag:

```bash
find / -name "*flag*" -type f 2>/dev/null
```

Expected output shows a path like `/data/flag.txt` or similar. Read it:

```bash
cat /data/flag.txt
```

(⊙_☉) Wait, already?! Yes, that is really it. This VM is intentionally simple to make a point about Android device exposure, not to challenge you with layers of complexity.

> **MITRE ATT&CK:** T1005 Data from Local System, T1083 File and Directory Discovery

---

## Captured Flags, Hashes and Credentials

| Type | Value | Found At | Used |
|------|-------|----------|------|
| ADB root access | passwordless | TCP 5555, ADB-over-network | su root |
| Flag | see device at runtime | `/data/flag.txt` (or similar) | N/A |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|-------------|
| 1 | ADB exposed over TCP with no authentication | Thousands of Android devices on corporate Wi-Fi and IoT networks have ADB-over-TCP enabled and reachable | Disable ADB on all production devices; use firewall rules to block TCP 5555 from all untrusted interfaces |
| 2 | Passwordless root on Android | Development and debug builds routinely ship with passwordless root; these devices sometimes reach production environments | Never deploy debug/rooted Android builds in production; enforce MDM policies that detect and alert on rooted devices |
| 3 | ADB-over-network enables full device control | An attacker with ADB access can install apps, read all data, exfiltrate contacts and messages, and pivot to other network services | Treat ADB-over-network as equivalent to unauthenticated remote code execution |

**Why does this matter outside the lab?**

The Mirai botnet (2016) demonstrated at scale how devices with open management interfaces and default or no credentials become attack infrastructure within minutes of internet exposure. Android devices with ADB exposed are a specific subcase: in 2018 a cryptomining campaign compromised over 40,000 devices purely through exposed ADB ports. In enterprise environments, IoT gateways, digital signage, point-of-sale systems, and kiosks frequently run Android and are rarely monitored with the same rigor as workstations. The C-suite phone with Developer Options enabled and connected to the corporate Wi-Fi is a very real attack surface.

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Reconnaissance | TA0043 | Active Scanning: Scanning IP Blocks | T1595.001 |
| Reconnaissance | TA0043 | Active Scanning: Vulnerability Scanning | T1595.002 |
| Discovery | TA0007 | Network Service Discovery | T1046 |
| Discovery | TA0007 | File and Directory Discovery | T1083 |
| Initial Access | TA0001 | External Remote Services | T1133 |
| Initial Access | TA0001 | Exploit Public-Facing Application | T1190 |
| Privilege Escalation | TA0004 | Valid Accounts (default root) | T1078 |
| Collection | TA0009 | Data from Local System | T1005 |

> MITRE ATT&CK: https://attack.mitre.org/
> MITRE D3FEND: https://d3fend.mitre.org/

---

## Threat Actor Context

**Mirai botnet operators (2016):** Used unauthenticated Telnet and ADB-style access to compromise IoT devices running Linux and Android, building a botnet used in the October 2016 Dyn DDoS attack that took down major portions of the internet. Reference: MITRE ATT&CK Campaign C0028.

**ADB.Miner (2018):** A worm that scanned for Android devices with ADB-over-TCP exposed on port 5555 and deployed a Monero cryptomining payload. Infected devices were used for cryptocurrency mining without the owner's knowledge. Reference: https://www.bleepingcomputer.com/news/security/over-40-000-android-devices-hacked-using-exposed-adb-ports/

**APT groups targeting Android for surveillance:** Multiple nation-state actors including groups aligned with China and Iran have used ADB and Android-specific tooling to install persistent surveillance software on targeted devices. The initial access vector frequently involves compromised developer environments or devices brought in for "charging" that instead receive ADB commands.

---

## Remediation and Containment

### Technical Fixes

1. Disable USB Debugging and Network Debugging in Android Developer Options on all non-development devices
2. Block TCP port 5555 at the network perimeter and on all internal firewalls/VLANs that host Android or IoT devices
3. Deploy Mobile Device Management (MDM) software that enforces a policy prohibiting rooted devices from connecting to corporate resources
4. Segment Android/IoT devices onto a dedicated VLAN with no lateral access to production systems
5. Enable Android Enterprise or equivalent corporate container mode to separate work data from device-level access

### If You Find Something Similar in Your Environment

**Immediate containment:**
- Isolate the device from the network immediately: pull VLAN membership or disable the switch port
- Audit all other devices on the same VLAN for exposed port 5555: `nmap -p 5555 --open <VLAN subnet>`
- Review logs for any prior ADB connections: check DHCP leases, ARP tables, and switch logs for the period the device was active
- Assume all data on the device is compromised: notify the data owner and start incident response

**MITRE D3FEND countermeasures:**
- D3-NTA (Network Traffic Analysis) against T1133: monitor for ADB protocol traffic on port 5555 across the corporate network
- D3-MFA (Multi-factor Authentication) against T1078: require authentication for all ADB access; use ADB key-based authentication (`adb keygen`)
- D3-NI (Network Isolation) against T1190: segment Android and IoT devices onto dedicated VLANs with no direct routing to production networks
- D3-OPS (OS Process Sandboxing) against T1548: enforce Android Enterprise Work Profile or dedicated device mode to contain blast radius

### Framework Alignment

**NIST CSF 2.0:**
- Identify (ID.AM): Include all Android and IoT devices in the asset inventory; document ADB status, root status, and MDM enrollment
- Protect (PR.AC-5): Segment IoT and mobile devices into dedicated network zones; enforce least privilege for device access
- Protect (PR.IP-1): Establish a configuration management baseline for Android devices; flag deviations (rooted, ADB on, unmanaged)
- Detect (DE.CM-1): Monitor network traffic for ADB protocol connections on TCP 5555; alert on any connection from external or unexpected IPs
- Respond (RS.MI-1): Contain impacted devices by network isolation; escalate to MDM revocation if corporate-enrolled

**NIST SP 800-53 (Rev. 5) Controls:**
- CM-7: Least Functionality: disable ADB-over-network on all devices not explicitly authorized for remote debugging
- SC-7: Boundary Protection: enforce network segmentation between mobile/IoT devices and production systems
- IA-3: Device Identification and Authentication: require cryptographic ADB key authentication for any authorized remote debugging sessions
- SI-2: Flaw Remediation: patch Android devices regularly; CVE-2019-2205 and similar ADB-related CVEs require OS-level updates
- AU-12: Audit Record Generation: log all ADB connections; integrate device logs into a centralized SIEM

**CISA Known Exploited Vulnerabilities:**
- CVE-2019-2205: Android ADB arbitrary file write (AOSP): in CISA KEV, apply OS updates immediately
- CVE-2020-0022: Android Bluetooth (BlueFrag) RCE: often paired with ADB exposure on the same device class
- Monitor: https://www.cisa.gov/known-exploited-vulnerabilities-catalog, filter by "Android"

**C2M2 (Cybersecurity Capability Maturity Model):**
- Domain: ASSET, Practice: Asset Inventory, Target MIL-2: Inventory all mobile and IoT assets; track OS version, root status, and management enrollment
- Domain: ACCESS, Practice: Access Management, Target MIL-2: Enforce authentication for all remote device management interfaces, including ADB
- Domain: TECHNOLOGY, Practice: Configuration Management, Target MIL-3: Automate detection of devices deviating from the hardened baseline (ADB enabled, rooted)

---

## Final Thoughts

Thanks to **Ajay Verma** for building a VM that is "simple" in execution but deeply relevant in context. Popping a shell in three commands and getting root in a fourth is humbling: it is a reminder that the attack complexity is sometimes zero, and the vulnerability is purely organizational.

The real takeaway here is not "Android is insecure." Android with proper MDM, ADB disabled, Work Profile enforced, and placed on a properly segmented VLAN is a reasonable enterprise endpoint. The takeaway is that default developer configurations, combined with zero network enforcement, produce devices that an intern with a laptop and `adb connect` can fully compromise in under two minutes.

This VM is a great piece to bring to a security awareness session: the demo is short enough to fit in thirty seconds and shocking enough that people remember it. If it helped you see that attack surface a little more clearly, mission accomplished.

If this walkthrough helped you, share it with your crew and keep hacking!

*Thanks guys!! (❍ᴥ❍ʋ)*

> Original article in Portuguese by André Henrique: https://medium.com/uniaogeek/vulnhub-unknown-device-vm-2

---

*Writeup by [André Henrique](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
