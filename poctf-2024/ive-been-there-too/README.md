# I've Been There Too

**Category:** Digital Forensics
**Challenge:** I've Been There Too
**CTF:** Pointer Overflow CTF 2024
**Points:** DF 100
**Result:** Solved

**Flag:**

~~~text
poctf{uwsp_d0_4ndr01d5_dr34m}
~~~

---

## 1. Challenge Overview

A SQLite database simulating a student records system where someone has tampered with entries. The flag is distributed across multiple records in the database.

**Files:** `DF100-3.sqlite` (SQLite database)

---

## 2. Database Exploration

Opened the database and enumerated tables:

~~~bash
sqlite3 DF100-3.sqlite
~~~

~~~sql
.tables
-- Output: new_students

.schema
-- CREATE TABLE new_students (
--     id INT PRIMARY KEY,
--     name TEXT NOT NULL,
--     photo BLOB NOT NULL,
--     gpa FLOAT NOT NULL,
--     has_covid_vaccine BOOLEAN NOT NULL,
--     year_graduated INT NOT NULL
-- );
~~~

---

## 3. Data Examination

Queried the `name` column to search for flag fragments:

~~~sql
SELECT name FROM new_students;
~~~

Scrolling through the results revealed flag fragments distributed across various entries. Near the end of the dataset, the fragment `_dr34m}` was visible, and other entries contained the remaining parts.

Assembling all fragments:

~~~text
poctf{uwsp_d0_4ndr01d5_dr34m}
~~~

---

## Lessons Learned

| # | Lesson | Detail |
|---|--------|--------|
| 1 | Database forensics involves record-by-record examination | Tampered entries hide among legitimate data |
| 2 | SQLite is a common evidence source | Browser history, mobile apps, and many applications use SQLite |
| 3 | Data exfiltration can use existing database fields | Hiding data in name fields blends with normal records |

---

## MITRE ATT&CK Mapping

| Tactic | Technique | TTP-ID | Context |
|---|---|---|---|
| Collection | Data from Local System | T1005 | Flag fragments extracted from SQLite database records |
| Defense Evasion | Data Manipulation: Stored Data Manipulation | T1565.001 | Tampered student records contain hidden flag data |
| Exfiltration | Exfiltration Over Alternative Protocol | T1048 | Data hidden in database fields for covert storage |

> **CWE-311:** Missing Encryption of Sensitive Data. Flag fragments stored as plaintext in database fields.
> **CWE-284:** Improper Access Control. Database modification went undetected due to lack of integrity monitoring.

---

## Remediation and Containment

### Technical Fixes

1. Implement database integrity monitoring (checksums, row-level hashing)
2. Enable audit logging for all INSERT/UPDATE operations on sensitive tables
3. Use database activity monitoring (DAM) to detect anomalous modifications
4. Apply least-privilege access to prevent unauthorized record manipulation

### MITRE D3FEND Countermeasures

- **D3-DQSA (Database Query String Analysis):** monitor SQL queries for data manipulation patterns
- **D3-FIM (File Integrity Monitoring):** detect unauthorized modifications to database files
- **D3-ACL (Access Control List):** enforce strict permissions on database write operations

### NIST CSF 2.0

- **Protect (PR.DS):** protect database integrity through access controls and monitoring
- **Detect (DE.CM):** deploy database activity monitoring for unauthorized modifications
- **Respond (RS.MI):** investigate and remediate detected database tampering

### NIST SP 800-53 Rev. 5

- **AU-10 (Non-Repudiation):** maintain audit trails for all database modifications
- **SI-7 (Software, Firmware, and Information Integrity):** monitor database files for unauthorized changes
- **AC-6 (Least Privilege):** restrict database write access to authorized processes only

### NIST SP 800-86

- **Database Forensics:** preserve database files with write-blocking before examination
- **Record Analysis:** systematically review all fields for anomalous or hidden data

### C2M2

- **SITUATION-2:** include database tampering detection in monitoring playbooks
- **ASSET-3:** classify student databases as sensitive assets requiring integrity controls

---

Thanks guys!! (❍ᴥ❍ʋ)

---

Do androids dream of electric sheep? They might, but they definitely dream of hiding flags in SQLite records. Always examine every field in a forensic database, not just the obvious columns.

- Instagram: https://www.instagram.com/uniaogeek
- LinkedIn: http://linkedin.com/in/mrhenrike
- X: https://x.com/mrhenrike

---

> **Reference:** Adapted from [shivang1209-dot/CTF-Writeups](https://github.com/shivang1209-dot/CTF-Writeups). Original scripts credited to the author.
