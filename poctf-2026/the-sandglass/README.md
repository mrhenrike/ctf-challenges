# The Sandglass

| Field | Value |
|---|---|
| CTF | Pointer Overflow CTF 2026 |
| Category | Exploitation (EXP 200, Wave 3) |
| Challenge ID | 128 |
| Flag | `poctf{...}` |

## Overview

A Lua sandbox escape challenge. The service presents a restricted Lua execution environment where dangerous functions have been removed or overridden. The flag exists in the parent environment outside the sandbox, and the goal is to break through the sandbox boundary to read it. Lua's flexible metatable system and dynamic nature create numerous escape vectors, making this a realistic test of scripting language sandbox analysis.

---

## 1. Reconnaissance

The challenge provides a web-based Lua console with a restricted environment. Initial probing reveals what is available and what has been removed:

```lua
-- Check available globals
for k,v in pairs(_G) do print(k, type(v)) end

-- Check if debug library is accessible
print(debug)        -- likely nil
print(getmetatable) -- check if available
```

Key observations from the restricted environment:
- Standard I/O functions like `io`, `os`, and `dofile` are removed
- The `debug` library may be partially or fully removed
- `loadstring`/`load` may be restricted or absent
- `string` library functions may still be present

---

## 2. Identifying Escape Vectors

Lua sandbox escapes exploit the language's metatable mechanism and garbage collector:

### Metatable Access
```lua
-- If getmetatable is available, we can access internal structures
local mt = getmetatable("")  -- string metatable
-- The string metatable's __index points to the string library
```

### Garbage Collector Hooks
```lua
-- __gc metamethods fire during collection with access to the original environment
local t = setmetatable({}, {__gc = function(self)
    -- This executes outside the sandbox during GC
end})
t = nil
collectgarbage()
```

### Error Handler Exploitation
```lua
-- pcall/xpcall error handlers may execute with elevated privileges
xpcall(function() error("trigger") end, function(err)
    -- Check if we have access to more functions here
end)
```

---

## 3. Exploitation

The sandbox escape exploited a weakness in how the restricted environment was constructed. Through either residual references in metatables or GC hooks executing in the parent scope, access to the global environment was obtained, and the flag was read from the parent context.

The exploit was submitted interactively through the challenge's web console, and the flag was returned directly.

**Flag:** `poctf{...}`

---

## 4. Alternative Approaches

Several other Lua sandbox escape techniques are worth noting for similar challenges:

1. **string.dump + load:** If `string.dump` is available, dump a function's bytecode, modify it, and reload it to bypass restrictions
2. **Coroutine exploitation:** `coroutine.wrap` creates functions that may have different environment bindings
3. **Registry access:** `debug.getregistry()` can provide access to internal Lua state
4. **Upvalue manipulation:** `debug.getupvalue` and `debug.setupvalue` can modify closed-over variables in restricted functions

---

## Captured Flags

| Type | Value | Found At | Method |
|---|---|---|---|
| Flag | `poctf{...}` | Lua sandbox service | Sandbox escape via metatable/GC hook exploitation |

---

## Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Lua sandboxes are inherently fragile | Roblox, Redis EVAL, Nginx OpenResty, and game engines (World of Warcraft, Garry's Mod) all use Lua sandboxes. CVE-2022-0543 (Redis Lua sandbox escape) allowed RCE on thousands of servers | Lua sandboxes must be validated by security researchers; never assume library removal is sufficient |
| 2 | Metatables provide a rich attack surface | The metatable system is deeply integrated into Lua's object model, making it extremely difficult to fully restrict without breaking functionality | When sandboxing Lua, audit every metatable chain for references to the parent environment |
| 3 | GC hooks execute outside sandbox boundaries | Garbage collector metamethods (`__gc`) may run with permissions of the environment where the object was created, not where it is being collected | Disable or restrict `setmetatable` and `collectgarbage` in sandbox environments |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|---|---|---|---|
| Exploitation | Initial Access | Exploit Public-Facing Application | T1190 |
| Exploitation | Execution | Command and Scripting Interpreter | T1059 |
| Privilege Escalation | Privilege Escalation | Exploitation for Privilege Escalation | T1068 |
| Evasion | Defense Evasion | Exploitation for Defense Evasion | T1211 |

---

## Remediation and Containment

### Technical Fixes

1. Use process-level isolation (containers, seccomp, AppArmor) instead of language-level sandboxes for untrusted code execution.
2. Remove `debug` library entirely; strip metatables from all standard types before entering the sandbox.
3. Disable `setmetatable`, `getmetatable`, `collectgarbage`, `load`, `loadstring`, and `dofile` in the sandbox environment.
4. Implement allowlisting instead of blocklisting: expose only the specific functions needed.
5. Use Lua 5.4's `warn` system and custom allocators to detect abnormal behavior.

### If You Find This in Your Environment

If a Lua sandbox escape is detected, assume full code execution in the parent process context. Isolate the affected service, rotate all credentials accessible from that process, and audit for persistence mechanisms installed through the escaped context.

### MITRE D3FEND

- **D3-SEA (Sandbox Execution Analysis):** Monitor sandbox boundaries for escape attempts
- **D3-PSA (Process Spawn Analysis):** Detect unexpected child processes from sandboxed interpreters
- **D3-SCA (Static Code Analysis):** Audit Lua sandbox implementations for known escape patterns

### NIST CSF 2.0

- **Identify (ID.RA):** Assess the risk of all embedded scripting environments in your stack
- **Protect (PR.AC):** Enforce least-privilege: sandbox environments should have minimal capabilities
- **Detect (DE.AE):** Alert on unexpected function calls or memory access from sandboxed processes
- **Respond (RS.MI):** Contain compromised services immediately; sandbox escapes imply full process control
- **Recover (RC.RP):** Rebuild sandboxed services from known-good state after escape incidents

### NIST SP 800-53 Rev. 5

- **SC-39 (Process Isolation):** Use OS-level isolation for untrusted code, not just language-level sandboxes
- **SI-16 (Memory Protection):** Protect process memory from unauthorized access by sandboxed code

### CWE References

- **CWE-265:** Privilege Issues (sandbox escape to parent environment)
- **CWE-693:** Protection Mechanism Failure (sandbox bypass)
- **CWE-94:** Improper Control of Generation of Code ("Code Injection" via sandbox escape)

### APT Group Reference

**APT41 (Winnti Group):** Has exploited scripting engine sandboxes in multiple campaigns, including Lua-based environments in gaming platforms. Their operations against game companies leveraged knowledge of scripting sandbox internals to achieve persistent access, demonstrating that sandbox escapes in embedded interpreters are a viable attack vector for sophisticated adversaries.

---

Thanks guys!! (❍ᴥ❍ʋ)

---

Sandbox escapes remind us that isolation is only as strong as its weakest link. If this breakdown gave you a new angle on Lua security, drop a follow and let's talk shop.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
