# Maq100: Servidor DNS

Writeup for the **Servidor DNS** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Easy
> **Difficulty:** Easy
> **Points:** 100

---

## Overview

A misconfigured DNS server allows unauthorized zone transfers, leaking internal hostnames, IP addresses and sensitive records that should remain private.

## Reconnaissance

Start with a full port scan to identify running services.

```bash
nmap -sV -sC -p- [TARGET_IP] -oN nmap_scan.txt
```

Port 53 (DNS) should be open. Identify the domain name through reverse lookups or banner information.

```bash
nmap -sV -p 53 --script dns-nsid [TARGET_IP]
```

## Exploitation

Attempt an AXFR (zone transfer) against the target DNS server.

```bash
dig axfr [DOMAIN] @[TARGET_IP]
```

If the server allows unrestricted zone transfers, the entire zone file is returned. This includes all A, CNAME, MX, TXT and other records. Examine the output carefully for hidden subdomains, internal IPs, TXT records containing credentials or tokens, and any other sensitive data.

An alternative approach using `host`:

```bash
host -t axfr [DOMAIN] [TARGET_IP]
```

## Post-Exploitation

Review all returned records. Hidden subdomains may host additional services, and TXT records sometimes contain encoded secrets or verification tokens that lead to the flag.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Remote System Discovery | T1018 |
| Network Service Discovery | T1046 |
| Gather Victim Network Information: DNS | T1590.002 |

### CWE

- **CWE-200:** Exposure of Sensitive Information to an Unauthorized Actor
- **CWE-16:** Configuration (improper DNS server configuration allowing zone transfers)

### NIST SP 800-53

- **AC-3:** Access Enforcement (restrict zone transfer to authorized secondaries)

---

When your DNS speaks too freely, every secret in the zone becomes an open book. Restrict AXFR to trusted secondaries, or the next visitor will read every page.

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
