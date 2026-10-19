# SOCBrazil CTF Blue Team: Writeups

Personal collection of writeups for the [SOCBrazil CTF](https://app.socbrazil.com/) Blue Team platform.

> **Disclaimer:** All challenges were solved on the official SOCBrazil platform. No real systems were targeted. Flag values are redacted since they are static and platform-specific.

---

## Progress Overview

**2,572/2,572 challenges** across 15 completed trails. **#1 Global Ranking**, 454,998 pts.

### Trail Completion

| Trail | Challenges | Points | Status |
|-------|-----------|--------|--------|
| [Cyber, O Comeco](cyber-o-comeco/) | 200/200 | varies | Complete |
| [Admin](admin/) | 100/100 | varies | Complete |
| [Matrix (Root)](matrix/) | 100/100 | varies | Complete |
| [Network](network/) | 100/100 | varies | Complete |
| [Injection](injection/) | 100/100 | varies | Complete |
| [Payload](payload/) | 100/100 | varies | Complete |
| [Binary](binary/) | 100/100 | varies | Complete |
| [Sudo](sudo/) | 100/100 | varies | Complete |
| [Hash](hash/) | 100/100 | varies | Complete |
| [Exploit](exploit/) | 100/100 | varies | Complete |
| [Vector](vector/) | 100/100 | varies | Complete |
| [Control](control/) | 250/250 | varies | Complete |
| [Risk](risk/) | 200/200 | varies | Complete |
| [Response](response/) | 500/500 | varies | Complete |
| [Shadow (Threat)](shadow/) | 100/100 | varies | Complete |

### Additional Content

| Content | Status | Notes |
|---------|--------|-------|
| Hunt (Log Analysis Sandbox) | 96 challenges explored | Non-scoreable sandbox |
| Cyber Games (Super Trunfo + Mitre Game) | Explored | Client-side educational games |
| Warriors (7 modules) | Locked | Requires `packs.use` capability (plan upgrade) |
| Simulados | Coming Soon | Not yet published |
| Mystical | Coming Soon | Not yet published |

---

## Platform Overview

SOCBrazil is a Brazilian Blue Team CTF platform focused on defensive security operations. Challenges simulate real SOC analyst tasks: log analysis, threat hunting, incident response, and security monitoring.

### Challenge Format

Each challenge presents a security investigation scenario with:
- Log data from Windows Event Logs, Syslog, firewall logs, or SIEM outputs
- A specific question about the incident (source IP, hostname, timestamp, event ID, hash, etc.)
- The answer is a specific data point extracted from the logs

### Key Techniques

| Technique | Trails |
|-----------|--------|
| Windows Event Log Analysis (4624, 4625, 4648, 4688, 4720, etc.) | Admin, Matrix, Response |
| Network Traffic Analysis (NetFlow, DNS, HTTP) | Network, Control |
| SQL/Command Injection Detection | Injection |
| Malware Payload Analysis (hashes, IOCs) | Payload, Binary |
| Privilege Escalation Detection (sudo, SUID) | Sudo, Exploit |
| Hash Cracking and Correlation | Hash |
| Attack Vector Identification | Vector |
| Risk Assessment and Scoring | Risk |
| Incident Response Procedures | Response |
| Threat Intelligence and Hunting | Shadow |

### Solving Methodology

Most trails follow a pattern-based approach:

1. **Identify the event type** from the challenge name/description
2. **Filter logs** by relevant fields (src_ip, hostname, event_id, timestamp)
3. **Correlate events** across multiple log sources
4. **Extract the answer** (usually a specific field value: IP, hash, hostname, timestamp)

Advanced trails (Control, Risk, Response) require multi-step correlation across sessions, hosts, and time windows.

---

## Automation

A custom solver script (`autosolve_routine.py`) was developed to automate challenge resolution across trails. The script:
- Connects to the SOCBrazil API
- Parses investigation data and log entries
- Identifies the correct answer based on event patterns
- Validates and submits answers

> **Note:** The solver was built as a learning exercise in API interaction and log parsing automation, not as a shortcut. Understanding the underlying techniques is essential.

---

## Security Frameworks

| Framework | Application |
|-----------|-------------|
| MITRE ATT&CK | Technique mapping for each attack phase (T1110, T1190, T1046, T1204, etc.) |
| NIST CSF 2.0 | Detect (DE.CM, DE.AE), Respond (RS.AN, RS.CO) functions |
| NIST SP 800-53 Rev. 5 | AU-6 (Audit Review), IR-4 (Incident Handling), SI-4 (System Monitoring) |
| CIS Controls v8 | Control 8 (Audit Log Management), Control 17 (Incident Response) |
| D3FEND | D3-DA (Dynamic Analysis), D3-NTA (Network Traffic Analysis) |

---

## Structure

```
socbrazil/
  README.md              # This file
  <trail-slug>/
    README.md            # Trail overview and methodology
```

> Individual challenge writeups are organized by trail. Due to the large number (2,572 challenges), writeups focus on methodology and patterns rather than individual solutions.

---

## Author

**Andre Henrike** (@mrhenrike)

The SOC never sleeps, but when it does, it dreams in regex. Keep hunting, keep learning: the logs always have something to say. Thanks guys!! (❍ᴥ❍ʋ)

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

## License

These writeups are released for educational purposes. Do not use any technique shown here against systems you do not own or have explicit permission to test.
