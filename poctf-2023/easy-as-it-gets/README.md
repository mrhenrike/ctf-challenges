# Easy as it Gets

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2023 |
| **Category** | Reverse Engineering |
| **Difficulty** | Easy |
| **Points** | 100 |
| **Flag** | `poctf{uwsp_4d_v1c70r14m_w4573l4nd3r}` |
| **Status** | Solved |

---

## 1. Challenge Overview

The challenge provides a "secure" PowerShell script and asks us to find the passphrase to decrypt the flag. This is described as the simplest reverse engineering challenge available.

---

## 2. Inspecting the Script

Opening the PowerShell script (`RE1.ps1`) reveals that the passphrase is hardcoded directly in the source code:

~~~text
Canadian_Soap_Opera
~~~

The script uses this passphrase to decrypt an embedded string using PowerShell's `ConvertTo-SecureString` and related cmdlets.

---

## 3. Running the Script

Execute the PowerShell script and enter the passphrase when prompted:

~~~powershell
# If script execution is restricted, first run as Administrator:
Set-ExecutionPolicy Unrestricted -Scope CurrentUser

# Then run the script:
.\RE1.ps1
~~~

When prompted for the passphrase, enter `Canadian_Soap_Opera`. The script decrypts and displays the flag.

![PowerShell script execution](images/powershell.png)

---

## 4. Attack Path Summary

~~~text
RE1.ps1 (PowerShell script)
    |
Read source code -> passphrase "Canadian_Soap_Opera" found in plaintext
    |
Execute script, enter passphrase
    |
FLAG: poctf{uwsp_4d_v1c70r14m_w4573l4nd3r}
~~~

The leetspeak reads: "ad victoriam wastelander," a reference to the Brotherhood of Steel motto from Fallout 4.

---

## 5. Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|--------------|
| 1 | Hardcoded credentials in scripts are immediately visible | Developers frequently embed API keys, passwords, and secrets directly in scripts committed to repositories | Never hardcode secrets; use environment variables, vaults, or credential managers |
| 2 | PowerShell execution policy is not a security boundary | `Set-ExecutionPolicy Unrestricted` bypasses the restriction trivially | Execution policies are a convenience feature, not a security control |
| 3 | "Encrypted" data with a hardcoded key provides no protection | The encryption is meaningless when the key sits right next to the ciphertext | Encryption strength depends entirely on key management, not the algorithm |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Execution | TA0002 | Command and Scripting Interpreter: PowerShell | T1059.001 |
| Credential Access | TA0006 | Unsecured Credentials: Credentials in Files | T1552.001 |
| Defense Evasion | TA0005 | Obfuscated Files or Information | T1027 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediation and Containment

### Technical Fixes

1. Remove all hardcoded credentials from scripts and use secrets management solutions (HashiCorp Vault, AWS Secrets Manager, Azure Key Vault)
2. Implement pre-commit hooks with tools like `gitleaks` or `trufflehog` to prevent committing secrets
3. Use PowerShell Constrained Language Mode and AppLocker to limit script execution in production environments
4. Rotate any credentials that have been exposed in source code

### MITRE D3FEND Countermeasures

- **D3-SPP Secret Rotation** to ensure hardcoded credentials are rotated immediately upon discovery (counters T1552.001)
- **D3-EAL Execution Prevention** to restrict unauthorized PowerShell script execution (counters T1059.001)

### NIST CSF 2.0

- **Protect (PR.AC-1):** Identities and credentials are issued, managed, and revoked; no hardcoded secrets
- **Detect (DE.CM-5):** Unauthorized code execution (scripts with embedded secrets) is detected

### NIST SP 800-53 Rev. 5

- **IA-5: Authenticator Management** (never embed authenticators in source code)
- **SC-28: Protection of Information at Rest** (encrypt secrets with externally managed keys)

### CWE

- **CWE-798: Use of Hard-coded Credentials** (passphrase embedded directly in the script)
- **CWE-312: Cleartext Storage of Sensitive Information** (secret visible in source code)

---

## References

- Based on solve approach from [a101e-lab](https://github.com/a101e-lab/CTF-Writeups)

---

Thanks guys!! (❍ᴥ❍ʋ)

---

Hardcoded secrets are the low-hanging fruit of both CTF challenges and real-world breaches. If this quick reverse engineering tip saved you some time, pass it forward to someone learning the ropes.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
