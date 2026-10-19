# A Quiet Home

**Category:** Forensics
**Challenge:** A Quiet Home
**CTF:** Pointer Overflow CTF 2026
**Points:** FOR 200 (Wave 4)
**Result:** Solved

**Flag:**

~~~text
5SDRSL7HESH4VHD3
~~~

---

## 1. Reconnaissance

The challenge provides a Home Assistant backup archive from "Elena's quiet home." Home Assistant is an open-source home automation platform that connects smart devices, sensors, and cloud services. Its backup files contain the full configuration state of the smart home, including secrets.

The archive extracts to:

~~~text
elena-ha-backup/
├── configuration.yaml     <- main HA config
├── secrets.yaml           <- encrypted/referenced secrets
├── automations.yaml       <- automation rules
├── scripts.yaml           <- custom scripts
├── .storage/              <- internal state database
│   ├── auth               <- authentication data
│   ├── core.config_entries <- integration configs with tokens
│   └── ...
└── custom_components/     <- third-party integrations
~~~

---

## 2. Artifact Analysis

### configuration.yaml

The main configuration file references `!secret` tags for sensitive values, which pull from `secrets.yaml`. However, some entries contain inline values:

~~~yaml
homeassistant:
  name: Elena's Quiet Home
  unit_system: metric
  currency: GBP

http:
  ssl_certificate: /ssl/fullchain.pem
  ssl_key: /ssl/privkey.pem
~~~

### secrets.yaml

Contains the referenced secrets, including API tokens, WiFi passwords, and device credentials:

~~~yaml
wifi_password: "QuietHome2026!"
ha_token: "eyJhbGciOiJIUzI1NiIs..."
mqtt_password: "elena_mqtt_secure"
~~~

### .storage/core.config_entries

The internal storage files contain integration configurations in JSON format with authentication tokens and API keys.

---

## 3. Flag Discovery

Searching across all configuration files for patterns matching the expected flag format:

~~~bash
grep -rn '[A-Z0-9]\{16\}' elena-ha-backup/
~~~

The flag was found in the `.storage` directory, within a custom integration's configuration entry, stored as a device token:

~~~json
{
  "entry_id": "elena_lock_001",
  "domain": "smart_lock",
  "data": {
    "token": "5SDRSL7HESH4VHD3",
    "device_name": "Front Door Lock"
  }
}
~~~

---

## 4. Attack Path Summary

~~~text
Extract HA backup archive
    |
Inventory: configuration.yaml, secrets.yaml, .storage/
    |
secrets.yaml -> WiFi password, MQTT creds, HA token (context)
    |
.storage/core.config_entries -> integration configs
    |
Smart lock token = 5SDRSL7HESH4VHD3 -> FLAG
~~~

---

## Captured Flags

| Type | Value | Found At | Method |
|---|---|---|---|
| Flag | `5SDRSL7HESH4VHD3` | `.storage/core.config_entries` (smart lock token) | Home Assistant backup forensic analysis |
| Credential | `QuietHome2026!` | `secrets.yaml` | WiFi password (plaintext) |
| Token | `eyJhbGciOiJIUzI1NiIs...` | `secrets.yaml` | HA long-lived access token |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | HA backups contain all secrets in plaintext or reversible format | Smart home backups synced to cloud or NAS are high-value targets; the 2023 Wyze camera data leak exposed millions of home camera feeds due to similar token exposure | Smart home backups must be encrypted at rest and access-controlled |
| 2 | Device tokens for smart locks provide physical access | Compromised smart lock tokens can unlock doors remotely; Ring camera credential stuffing incidents (2019-2020) demonstrated real-world consequences | Device tokens for physical access controls must be rotated regularly and stored securely |
| 3 | `.storage/` directory contains more sensitive data than `secrets.yaml` | HA's internal state database stores integration credentials that users never directly manage, creating a blind spot | Forensic analysis must include internal state databases, not just user-facing config |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|---|---|---|---|
| Collection | TA0009 | Data from Local System | T1005 |
| Credential Access | TA0006 | Unsecured Credentials: Credentials In Files | T1552.001 |
| Credential Access | TA0006 | Credentials from Password Stores | T1555 |
| Discovery | TA0007 | File and Directory Discovery | T1083 |
| Lateral Movement | TA0008 | Use Alternate Authentication Material: Application Access Token | T1550.001 |

> **APT Reference:** APT28 (Fancy Bear) has targeted IoT devices and smart home infrastructure as entry points into corporate networks via home office VPN connections. The Mirai botnet demonstrated the scale of IoT compromise, and recent research shows smart home platforms are increasingly targeted for credential harvesting that enables physical access.

---

## Remediation and Containment

### Technical Fixes

1. Encrypt Home Assistant backups at rest (use HA's built-in backup encryption or GPG)
2. Use a secrets vault (HashiCorp Vault, SOPS) instead of plaintext `secrets.yaml`
3. Enable MFA on the Home Assistant admin interface
4. Rotate all device tokens and API keys after any backup exposure
5. Restrict backup storage to encrypted, access-controlled locations

### If You Find Something Similar in Your Environment

**Immediate containment:**
- Rotate all credentials found in the backup: WiFi passwords, API tokens, device tokens, MQTT credentials
- Revoke and regenerate smart lock/camera tokens immediately (physical access implications)
- Audit backup storage locations for unauthorized access
- Enable encryption on all future backups

**MITRE D3FEND countermeasures:**
- D3-FE (File Encryption) for backup archives at rest
- D3-CH (Credential Hardening) to enforce encrypted credential storage
- D3-FCA (File Content Analysis) to detect plaintext credentials in backup files

### Framework Alignment

**CWE:**
- CWE-312: Cleartext Storage of Sensitive Information
- CWE-522: Insufficiently Protected Credentials
- CWE-311: Missing Encryption of Sensitive Data

**OWASP Top 10 (2021):**
- A02:2021 Cryptographic Failures (plaintext credential storage)
- A05:2021 Security Misconfiguration (unencrypted backups)

**NIST CSF 2.0:**
- Identify (ID.AM): Inventory all smart home devices and their credential storage
- Protect (PR.DS): Encrypt all backups and credential stores
- Detect (DE.CM): Monitor for unauthorized access to backup files
- Respond (RS.MI): Rotate all exposed credentials and revoke compromised tokens
- Recover (RC.RP): Re-provision devices with new credentials from encrypted storage

**NIST SP 800-53 (Rev. 5):**
- SC-28: Protection of Information at Rest (encrypt backups)
- IA-5: Authenticator Management (secure credential storage)
- CP-9: System Backup (backup security requirements)
- MP-4: Media Storage (secure backup media)

**C2M2:**
- Domain: ASSET (Asset, Change, and Configuration Management)
- Practice: Manage IT and OT assets including IoT device credentials
- Target MIL: MIL-2 (documented IoT credential management and backup encryption policies)

---

## Final Thoughts

Smart homes are quiet, but their backups are loud. A single unencrypted backup file contains WiFi passwords, API tokens, smart lock codes, and enough information to physically access a residence. In real forensic investigations, Home Assistant backups are increasingly valuable evidence sources. The "quiet home" is only quiet until someone reads the config files.

Thanks guys!! (❍ᴥ❍ʋ)

---

Smart home forensics is a growing field, and this challenge barely scratches the surface. If it opened your eyes to IoT security, share it with your network.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
