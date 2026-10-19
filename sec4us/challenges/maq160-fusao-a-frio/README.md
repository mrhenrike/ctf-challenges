# Maq160: Fusao a Frio

Writeup for the **Fusao a Frio** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Medium
> **Difficulty:** Medium

---

## Overview

A ColdFusion server challenge where access to the admin panel enables creation of a scheduled task that writes a CFM webshell to disk. The `cfexecute` tag in the webshell is then used to run system commands and read the flag.

## Reconnaissance

1. Scan the target to identify ColdFusion and its administrative interface.
2. Enumerate the ColdFusion version and research default credentials or known vulnerabilities.
3. Locate the ColdFusion Administrator login page (typically `/CFIDE/administrator/`).
4. Test default or common credentials for the admin panel.

## Exploitation

1. Authenticate to the ColdFusion Administrator panel.
2. Navigate to "Scheduled Tasks" under the admin console.
3. Create a new scheduled task that fetches a remote CFM file (hosted on the attacker) and saves it to the web root.
4. The CFM file contains a webshell using `<cfexecute>` to run OS commands.
5. Trigger the scheduled task to download and save the webshell.
6. Access the deployed CFM webshell through the browser.
7. Use `cfexecute` within the webshell to run commands on the underlying server.

## Privilege Escalation

1. Enumerate the system from the ColdFusion service context.
2. Use `cfexecute` to read the flag directly if ColdFusion runs with sufficient privileges.
3. If additional escalation is needed, identify local misconfigurations or stored credentials.
4. Retrieve the flag from the target filesystem.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Valid Accounts | T1078 |
| Server Software Component: Web Shell | T1505.003 |
| Scheduled Task/Job | T1053 |
| Command and Scripting Interpreter | T1059 |

### CWE

- **CWE-798:** Use of Hard-coded Credentials (default or weak ColdFusion admin password)
- **CWE-94:** Improper Control of Generation of Code (cfexecute arbitrary command execution)
- **CWE-434:** Unrestricted Upload of File with Dangerous Type (scheduled task file write)

---

> "Cold fusion promises unlimited energy from a simple reaction. ColdFusion the server delivers unlimited access from a simple scheduled task. Neither was supposed to work this way."

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
