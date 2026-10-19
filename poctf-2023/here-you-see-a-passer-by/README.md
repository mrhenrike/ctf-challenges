# Here You See A Passer By

| Detail | Value |
|--------|-------|
| **CTF** | Pointer Overflow CTF 2023 |
| **Category** | Miscellaneous |
| **Difficulty** | Medium |
| **Points** | 200 |
| **Flag** | `poctf{uwsp_p4553r_8y_7h3_m4z3}` |
| **Status** | Solved |

---

## 1. Challenge Overview

The challenge presents a 2D maze that must be solved to obtain the flag. The path through the maze encodes the flag, either by the directions taken or by the characters collected along the correct route.

---

## 2. Analyzing the Maze

The maze is provided as an image or text grid. Key observations:

- The maze has a single valid path from start to finish
- Characters or symbols are placed along the corridors
- The correct path through the maze collects characters that spell out the flag

---

## 3. Solving the Maze

Using a systematic approach:

1. **Identify start and end points** (typically marked with arrows or distinct markers)
2. **Trace the path** using wall-following (right-hand rule) or depth-first search
3. **Record characters** encountered along the valid path in order

For a programmatic approach, a simple BFS (Breadth-First Search) solver works well:

~~~python
from collections import deque

def solve_maze(maze, start, end):
    queue = deque([(start, [start])])
    visited = {start}
    
    while queue:
        (x, y), path = queue.popleft()
        if (x, y) == end:
            return path
        for dx, dy in [(0,1), (0,-1), (1,0), (-1,0)]:
            nx, ny = x+dx, y+dy
            if (nx, ny) not in visited and maze[ny][nx] != '#':
                visited.add((nx, ny))
                queue.append(((nx, ny), path + [(nx, ny)]))
    return None
~~~

Following the valid path through the maze and collecting the characters in order:

~~~text
poctf{uwsp_p4553r_8y_7h3_m4z3}
~~~

---

## 4. Attack Path Summary

~~~text
2D maze image/grid
    |
BFS/DFS path-finding algorithm
    |
Collect characters along valid path
    |
FLAG: poctf{uwsp_p4553r_8y_7h3_m4z3}
~~~

---

## 5. Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---------|---------------------|--------------|
| 1 | Algorithmic thinking solves structured puzzles efficiently | Malware analysis and exploit development require systematic problem decomposition | BFS and DFS are foundational algorithms applicable across security domains |
| 2 | Visual challenges may require programmatic solutions | Complex mazes, CAPTCHAs, and visual puzzles often yield to automated analysis | Python + PIL for image processing is a standard CTF combination |
| 3 | Pattern recognition in spatial data is a transferable skill | Network topology analysis, attack path mapping, and memory layout visualization all share spatial reasoning | Practice maze-solving skills as a foundation for complex graph-based security analysis |

---

## MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|-------|--------|-----------|--------|
| Discovery | TA0007 | Network Service Discovery | T1046 |
| Lateral Movement | TA0008 | Exploitation of Remote Services | T1210 |
| Reconnaissance | TA0043 | Active Scanning: Vulnerability Scanning | T1595.002 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediation and Containment

### Technical Fixes

1. Use CAPTCHAs and visual puzzles as an additional layer, never as the sole security control
2. Implement rate limiting on challenge-response systems to prevent automated solving
3. Design authentication challenges that resist programmatic solutions

### MITRE D3FEND Countermeasures

- **D3-ACL Access Control List** to enforce proper authentication beyond visual challenges (counters T1210)
- **D3-NTA Network Traffic Analysis** for detecting automated path-finding or scanning behavior (counters T1046)

### NIST CSF 2.0

- **Protect (PR.AC-1):** Authentication mechanisms are robust against automated bypass
- **Detect (DE.CM-1):** Monitor for automated scanning and brute-force attempts

### NIST SP 800-53 Rev. 5

- **IA-2: Identification and Authentication** (use multi-factor approaches beyond visual puzzles)
- **SI-10: Information Input Validation** (validate responses to prevent automated solving)

### CWE

- **CWE-804: Guessable CAPTCHA** (visual challenge vulnerable to algorithmic solving)

---

## References

- Solve approach based on research from [Jihun Hwang's POCTF 2023 writeup](https://jihunhwang.github.io/UWSP_CTF_2023_writeup/)

---

Thanks guys!! (❍ᴥ❍ʋ)

---

Every maze has a solution if you have the right algorithm. Like navigating a complex network during a penetration test, the path from entry to flag requires patience, method, and the willingness to explore every branch.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
