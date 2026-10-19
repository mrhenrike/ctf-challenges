# Commit to Memory

| Field | Value |
|---|---|
| CTF | Pointer Overflow CTF 2026 |
| Category | Steganography / Forensics (Wave 2) |
| Challenge ID | 100 |
| Flag | `POCTF{100.1391.ATHYP4AT7NVE5SL4.TLGMIYEQXOEMBW67DX7FC2EN4B}` |

---

## 1. Reconnaissance

The title "Commit to Memory" is a double entendre: the everyday phrase meaning "memorize," and a direct reference to `git commit`. The challenge provides a git bundle file containing a repository with hidden data encoded across its commit history.

---

## 2. The Artifact

The challenge delivers `commits.bundle`, a git bundle file. Git bundles are portable archives that package repository objects (commits, trees, blobs) into a single binary file, useful for offline transfer.

~~~bash
file commits.bundle
# commits.bundle: Git bundle
~~~

---

## 3. Cloning and Initial Exploration

~~~bash
git clone commits.bundle repo
cd repo

# Full commit history
git log --oneline --all
# Check for hidden branches and tags
git branch -a
git tag -l
# Examine all refs
git show-ref
~~~

The repository contains multiple commits, each carrying a small fragment of the flag. The key question: where exactly is the data hidden?

---

## 4. Examining Commit Metadata

~~~bash
# Check commit messages for encoded data
git log --format="%H %s" --all

# Check author/committer fields for anomalies
git log --format="%H | %an | %ae | %cn | %ce | %s" --all

# Check commit notes
git notes list
~~~

Git commits store metadata across multiple fields: message, author name, author email, committer name, committer email, and optional notes. Any of these can serve as a steganographic channel.

---

## 5. Extracting the Hidden Data

The solver script (`scripts/solve_git.sh`) walks through the commit history and extracts the flag fragments from the commits. The fragments, assembled in chronological order, reconstruct the full flag.

~~~bash
# Example extraction approach
for commit in $(git rev-list --reverse HEAD); do
    git log -1 --format="%s" "$commit"
done | tr -d '\n'
~~~

The extracted data assembles into the flag.

---

## 6. Flag

~~~text
POCTF{100.1391.ATHYP4AT7NVE5SL4.TLGMIYEQXOEMBW67DX7FC2EN4B}
~~~

---

## 7. Attack Path Summary

~~~text
Receive commits.bundle
    ↓
git clone → local repository
    ↓
Enumerate branches, tags, refs
    ↓
Walk commit history (rev-list)
    ↓
Extract data from commit metadata
    ↓
Assemble fragments → FLAG
~~~

---

## 8. Captured Flags

| Type | Value | Found At | Method |
|---|---|---|---|
| Flag | `POCTF{100.1391.ATHYP4AT7NVE5SL4.TLGMIYEQXOEMBW67DX7FC2EN4B}` | Git commit history | Commit metadata extraction from bundle |

---

## 9. Lessons Learned

| # | Finding | Real-World Relevance | Key Takeaway |
|---|---|---|---|
| 1 | Git repositories store far more data than the working tree | The 2023 Mercedes-Benz GitHub token leak exposed API keys in commit history that were "deleted" from the current branch but persisted in git objects | Always audit full commit history, not just HEAD |
| 2 | Git bundles are portable and can bypass network controls | Bundles enable offline repository transfer; an insider can exfiltrate an entire repository as a single binary file without triggering git protocol monitoring | Monitor for git bundle creation in DLP policies |
| 3 | Commit metadata fields are a viable steganographic channel | Author name, email, timestamp, and message can all carry encoded payloads; this has been used in real covert C2 channels via GitHub | Validate commit metadata against expected patterns |

---

## 10. MITRE ATT&CK Mapping

| Phase | Tactic | Technique | TTP-ID |
|---|---|---|---|
| Collection | Collection | Data from Information Repositories: Code Repositories | T1213.003 |
| Exfiltration | Exfiltration | Exfiltration Over Web Service | T1567 |
| Defense Evasion | Defense Evasion | Obfuscated Files or Information: Steganography | T1027.003 |
| Collection | Collection | Archive Collected Data | T1560 |
| Persistence | Persistence | Account Manipulation | T1098 |

---

## 11. Remediation and Containment

### Technical Fixes

1. **Implement git secret scanning:** Use tools like Gitleaks, TruffleHog, or GitHub Secret Scanning to detect secrets in commit history.
2. **Enforce commit signing:** Require GPG or SSH-signed commits to verify authorship and detect metadata tampering.
3. **Audit git bundle operations:** Monitor for `git bundle create` commands in endpoint detection logs.
4. **Regular history audits:** Periodically scan full repository history (not just HEAD) for sensitive data leaks.
5. **BFG Repo-Cleaner or git filter-repo:** When secrets are found in history, use these tools to rewrite history and remove them.

### If You Find This in Your Environment

Check if the bundle was transmitted outside the organization. Audit the repository for any secrets or credentials in its history. Rotate any exposed tokens. Review access logs for who created and accessed the bundle.

### MITRE D3FEND

| Countermeasure | D3FEND ID | Description |
|---|---|---|
| File Content Analysis | D3-FCA | Scan git bundles and repository objects for embedded secrets |
| Data Content Rules | D3-DCR | Enforce patterns matching on commit content to detect data exfiltration |
| File Transfer Analysis | D3-FTA | Monitor for git bundle file transfers across network boundaries |

### NIST CSF 2.0

| Function | Category | Activity |
|---|---|---|
| **Identify (ID)** | ID.AM | Inventory code repositories and classify by sensitivity |
| **Protect (PR)** | PR.DS | Enforce secret scanning in CI/CD pipelines |
| **Protect (PR)** | PR.AC | Restrict repository cloning and bundle creation permissions |
| **Detect (DE)** | DE.CM | Monitor for git bundle creation and unauthorized repository access |
| **Respond (RS)** | RS.AN | Investigate commit history for data leakage upon detection |

### NIST SP 800-53 Rev. 5

| Control | Description |
|---|---|
| **CM-3** | Configuration Change Control: track and audit all changes to code repositories |
| **AU-12** | Audit Record Generation: log git operations including clone, bundle, and push |
| **SC-28** | Protection of Information at Rest: encrypt repositories and bundles at rest |
| **AC-6** | Least Privilege: restrict bundle creation and force-push permissions |

### CWE References

| CWE | Description |
|---|---|
| CWE-538 | Insertion of Sensitive Information into Externally-Accessible File or Directory |
| CWE-200 | Exposure of Sensitive Information to an Unauthorized Actor |
| CWE-312 | Cleartext Storage of Sensitive Information (secrets in commit history) |

### APT Group Reference

**APT41 (Double Dragon):** Known for targeting source code repositories and version control systems. Their dual espionage/financial crime operations have included exfiltrating git repositories to steal intellectual property and embedded credentials, using techniques that parallel the data extraction demonstrated in this challenge.

---

Thanks guys!! (❍ᴥ❍ʋ)

---

Git forensics is a skill every security researcher should have in their toolbox. If this breakdown helped you understand how data hides in version control, pass it along.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike
