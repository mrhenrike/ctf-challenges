# Maq119: Gato Tom

Writeup for the **Gato Tom** challenge on [SEC4US](https://sec4us.com.br/).

> **Category:** Hacking: Medium
> **Difficulty:** Medium

---

## Overview

A Tomcat server that requires network pivoting from another compromised machine (maq156) to reach. After resolving DNS connectivity issues through the internal network, the Tomcat manager allows WAR file deployment for remote code execution.

## Reconnaissance

1. From the pivot host (maq156), scan the internal network to discover maq119.
2. Identify Apache Tomcat running on the target.
3. Note that direct DNS resolution may hang; configure `/etc/hosts` or use the internal IP directly.
4. Enumerate Tomcat manager and default credential paths.

## Exploitation

1. Access the Tomcat Manager interface through the pivot connection.
2. Test default or discovered Tomcat manager credentials for authentication.
3. Generate a malicious WAR file containing a reverse shell payload.
4. Deploy the WAR file through the Tomcat Manager upload feature.
5. Trigger the deployed application to establish a reverse shell back through the pivot.
6. Gain initial access as the Tomcat service user.

## Privilege Escalation

1. Enumerate the system for SUID binaries, writable scripts, or sudo misconfigurations.
2. Check Tomcat configuration files for stored credentials or additional pivot opportunities.
3. Escalate privileges using the discovered misconfiguration to obtain root access.
4. Retrieve the flag from the root-restricted area.

## Security Framework Mapping

### MITRE ATT&CK

| Technique | ID |
|-----------|----|
| Exploitation of Remote Services | T1210 |
| Server Software Component: Web Shell | T1505.003 |
| Lateral Movement: Proxy | T1090 |
| Valid Accounts: Default Accounts | T1078.001 |

### CWE

- **CWE-798:** Use of Hard-coded Credentials (default Tomcat manager credentials)
- **CWE-434:** Unrestricted Upload of File with Dangerous Type (WAR deployment)

---

> "Tom the cat always lands on his feet, but a careless Tomcat lands its credentials in default configs. Pivoting through the network, we followed the yarn straight to the manager console."

```
(❍ᴥ❍ʋ)
```

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
