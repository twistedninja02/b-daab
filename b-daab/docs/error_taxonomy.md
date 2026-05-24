# B-DAAB Error Taxonomy

Complete reference for all error categories used in B-DAAB evaluation. Each category includes a definition, an example of the failure, and guidance on how to fix it.

---

## Overview

Errors are divided into five groups. Every failed query is assigned a **primary error** (the root cause) and optionally a **secondary error** (a downstream consequence).

| Group | Categories | Count |
|---|---|:---:|
| Syntax Errors | SYNTAX_ERROR, PARSE_ERROR | 2 |
| Schema Errors | TABLE_NOT_FOUND, COLUMN_NOT_FOUND, SCHEMA_MISMATCH | 3 |
| Logic Errors | WRONG_JOIN, WRONG_WHERE, WRONG_AGGREGATION, WRONG_GROUP_BY, MISSING_JOIN, MISSING_WHERE, MISSING_GROUP_BY, WRONG_ORDER_BY, WRONG_DISTINCT | 9 |
| Result Errors | WRONG_COLUMNS, WRONG_ROWS, WRONG_VALUES, PARTIAL_MATCH | 4 |
| Other | NO_SQL_GENERATED, TIMEOUT, EXECUTION_ERROR, WRONG_LIMIT, EXTRA_ROWS | 5 |

---

## Syntax Errors

### SYNTAX_ERROR

**Definition:** The generated SQL contains a grammatical error that prevents the database from parsing it at all.

**Example:**

```sql
-- Bengali query: "কোন স্কুলে সবচেয়ে বেশি ছাত্র আছে?"
-- (Which school has the most students?)

-- Generated (broken):
SELECT name FROM schools WHERE id = (
  SELECT school_id FROM students GROUP BY school_id ORDER BY COUNT(*) LIMIT 1;
-- ↑ semicolon inside subquery terminates the statement early

-- Ground truth:
SELECT s.name
FROM schools s
JOIN students st ON s.id = st.school_id
GROUP BY s.id
ORDER BY COUNT(st.id) DESC
LIMIT 1;
```

**How to fix:** Use the `ORDER BY ... LIMIT 1` pattern instead of a subquery for superlative queries. Avoid semicolons inside subquery parentheses.

---

### PARSE_ERROR

**Definition:** The model output contains non-SQL content (e.g. markdown fences, explanatory text) mixed into the query, causing the parser to fail before execution.

**Example:**

```
-- Generated output:
Here is the SQL:
```sql
SELECT * FROM hospitals
```
Please note that this returns all hospitals.

-- Extracted SQL after stripping:
SELECT * FROM hospitals
Please note that this returns all hospitals.   ← causes parse failure
```

**How to fix:** Strip all non-SQL content from model output before execution. The `executor.py` sanitizer handles this, but models that produce very long explanations may confuse the extractor.

---

## Schema Errors

### TABLE_NOT_FOUND

**Definition:** The generated SQL references a table that does not exist in the schema.

**Example:**

```sql
-- Generated:
SELECT * FROM hospital_records;
-- ↑ table is named 'hospitals', not 'hospital_records'

-- Ground truth:
SELECT * FROM hospitals;
```

**How to fix:** Always include the full schema description in the system prompt. Use the `Detailed` or `Chain-of-Thought` prompt template from `agent/prompt.py` which explicitly lists table names.

---

### COLUMN_NOT_FOUND

**Definition:** The generated SQL references a column that does not exist in the specified table.

**Example:**

```sql
-- Generated:
SELECT patient_name FROM patients;
-- ↑ column is named 'name', not 'patient_name'

-- Ground truth:
SELECT name FROM patients;
```

**How to fix:** Provide column names explicitly in the prompt schema section. Few-shot examples that demonstrate correct column names significantly reduce this error.

---

### SCHEMA_MISMATCH

**Definition:** The SQL uses the correct table and column names but applies them to the wrong table (cross-table confusion).

**Example:**

```sql
-- Generated (confuses 'fee' column from doctor_visits with patients table):
SELECT AVG(fee) FROM patients;
-- ↑ 'fee' belongs to 'doctor_visits', not 'patients'

-- Ground truth:
SELECT AVG(fee) FROM doctor_visits;
```

**How to fix:** Use join path hints in the prompt. The `Few-Shot` template includes examples of multi-table queries to anchor the model to correct table-column mappings.

---

## Logic Errors

### WRONG_JOIN

**Definition:** The SQL uses an incorrect join type (e.g. INNER when LEFT is required, or joins on the wrong keys).

**Example:**

```sql
-- Bengali query: "প্রতিটি হাসপাতালে কত জন রোগী আছেন?"
-- (How many patients are in each hospital?)

-- Generated (INNER JOIN drops hospitals with 0 patients):
SELECT h.name, COUNT(p.id)
FROM hospitals h
INNER JOIN patients p ON h.id = p.hospital_id
GROUP BY h.id;

-- Ground truth (LEFT JOIN preserves all hospitals):
SELECT h.name, COUNT(p.id) AS patient_count
FROM hospitals h
LEFT JOIN patients p ON h.id = p.hospital_id
GROUP BY h.id
ORDER BY h.name;
```

**How to fix:** When the Bengali query uses "each/every" (প্রতিটি) over an entity, use LEFT JOIN to preserve entities with zero matches.

---

### WRONG_WHERE

**Definition:** The WHERE clause contains an incorrect condition — wrong column, wrong operator, wrong value, or filters when no filter is needed.

**Example:**

```sql
-- Bengali query: "ঢাকার হাসপাতালের তালিকা দেখান।"
-- (Show hospitals in Dhaka.)

-- Generated:
SELECT * FROM hospitals WHERE name = 'Dhaka';
-- ↑ filters by name instead of city

-- Ground truth:
SELECT * FROM hospitals WHERE city = 'Dhaka';
```

---

### WRONG_AGGREGATION

**Definition:** The wrong aggregate function is used (e.g. SUM instead of COUNT, MAX instead of AVG).

**Example:**

```sql
-- Bengali query: "গড় চিকিৎসা খরচ কত?"
-- (What is the average treatment cost?)

-- Generated:
SELECT SUM(fee) FROM doctor_visits;
-- ↑ SUM instead of AVG

-- Ground truth:
SELECT AVG(fee) AS avg_fee FROM doctor_visits;
```

---

### WRONG_GROUP_BY

**Definition:** The GROUP BY clause groups on the wrong column, producing incorrect aggregation boundaries.

**Example:**

```sql
-- Generated (groups by name — fragile if two hospitals share a name):
SELECT name, COUNT(*) FROM patients GROUP BY name;

-- Ground truth (groups by id — stable primary key):
SELECT h.name, COUNT(p.id)
FROM hospitals h
LEFT JOIN patients p ON h.id = p.hospital_id
GROUP BY h.id;
```

---

### MISSING_JOIN

**Definition:** The SQL retrieves data from multiple tables without joining them, causing a Cartesian product or a column-not-found error.

**Example:**

```sql
-- Bengali query: "প্রতিটি হাসপাতালের নাম এবং রোগীর সংখ্যা দেখান।"
-- (Show each hospital name and patient count.)

-- Generated (missing JOIN):
SELECT hospitals.name, COUNT(patients.id)
FROM hospitals, patients
GROUP BY hospitals.id;
-- ↑ implicit cross join — returns wrong counts

-- Ground truth:
SELECT h.name, COUNT(p.id) AS patient_count
FROM hospitals h
LEFT JOIN patients p ON h.id = p.hospital_id
GROUP BY h.id;
```

---

### MISSING_WHERE

**Definition:** A necessary WHERE condition is absent, returning all rows when a subset was requested.

**Example:**

```sql
-- Bengali query: "ঢাকার স্কুলগুলো দেখান।"
-- (Show schools in Dhaka.)

-- Generated (no filter):
SELECT * FROM schools;

-- Ground truth:
SELECT * FROM schools WHERE city = 'Dhaka';
```

---

### MISSING_GROUP_BY

**Definition:** The SQL uses an aggregate function but omits GROUP BY, causing either a SQL error or a single collapsed result.

**Example:**

```sql
-- Generated:
SELECT h.name, COUNT(p.id) AS patient_count
FROM hospitals h
LEFT JOIN patients p ON h.id = p.hospital_id;
-- ↑ no GROUP BY — returns one row or a SQL error

-- Ground truth:
SELECT h.name, COUNT(p.id) AS patient_count
FROM hospitals h
LEFT JOIN patients p ON h.id = p.hospital_id
GROUP BY h.id;
```

---

### WRONG_ORDER_BY

**Definition:** Results are ordered by the wrong column or in the wrong direction (ASC vs DESC).

**Example:**

```sql
-- Bengali query: "সর্বাধিক রোগী আছে এমন হাসপাতাল দেখান।"
-- (Show the hospital with the most patients.)

-- Generated (ASC returns fewest patients first):
SELECT h.name, COUNT(p.id) AS cnt
FROM hospitals h
JOIN patients p ON h.id = p.hospital_id
GROUP BY h.id
ORDER BY cnt ASC LIMIT 1;

-- Ground truth:
SELECT h.name, COUNT(p.id) AS cnt
FROM hospitals h
JOIN patients p ON h.id = p.hospital_id
GROUP BY h.id
ORDER BY cnt DESC LIMIT 1;
```

---

### WRONG_DISTINCT

**Definition:** DISTINCT is used when it should not be (changing the result set), or is missing when it is required.

**Example:**

```sql
-- Bengali query: "কোন কোন শহরে হাসপাতাল আছে?"
-- (Which cities have hospitals?)

-- Generated (missing DISTINCT — returns duplicate city names):
SELECT city FROM hospitals;

-- Ground truth:
SELECT DISTINCT city FROM hospitals ORDER BY city;
```

---

## Result Errors

### WRONG_COLUMNS

**Definition:** The SQL executes successfully but returns different columns than expected (wrong names, extra columns, or missing columns).

**Example:**

```sql
-- Generated (returns id column that was not requested):
SELECT id, name FROM hospitals;

-- Ground truth:
SELECT name FROM hospitals;
```

---

### WRONG_ROWS

**Definition:** The SQL executes successfully but returns a different number of rows than expected.

**Example:**

```sql
-- Bengali query: "গত মাসে সর্বাধিক বিক্রয় করা দোকানের নাম ও মোট বিক্রয়।"
-- (Name and total sales of the best-selling shop last month.)

-- Generated (returns one sale row, not one aggregated row per shop):
SELECT s.name, sl.amount
FROM shops s
JOIN sales sl ON s.id = sl.shop_id
ORDER BY sl.amount DESC LIMIT 1;

-- Ground truth (aggregates all sales per shop first):
SELECT s.name, SUM(sl.amount) AS total_sales
FROM shops s
JOIN sales sl ON s.id = sl.shop_id
GROUP BY s.id
ORDER BY total_sales DESC LIMIT 1;
```

---

### WRONG_VALUES

**Definition:** The SQL returns the correct columns and row count but the values themselves are incorrect.

**Example:**

```sql
-- Generated (average of individual fees, not grouped by hospital):
SELECT 'Dhaka Medical Hospital', AVG(fee) FROM doctor_visits;
-- ↑ hardcoded name + global average — values are wrong

-- Ground truth:
SELECT h.name, AVG(v.fee) AS avg_fee
FROM hospitals h
JOIN doctor_visits v ON h.id = v.hospital_id
GROUP BY h.id;
```

---

### PARTIAL_MATCH

**Definition:** The query output partially matches the expected result — correct structure but missing rows, or correct rows with minor value differences (e.g. rounding, alias name difference).

**Example:**

```sql
-- Expected: 5 hospitals with patient counts (including 0 for Khulna)
-- Generated: 4 hospitals (Khulna missing because INNER JOIN was used)
-- Result: PARTIAL_MATCH with secondary error WRONG_JOIN
```

---

## Other Errors

### NO_SQL_GENERATED

**Definition:** The model returned a response but it contained no extractable SQL statement.

**Typical causes:** The model refused to answer, produced only an explanation, or the Bengali query was too ambiguous for the model to attempt SQL generation.

---

### TIMEOUT

**Definition:** SQL execution exceeded the configured time limit (default: 30 seconds).

**Typical causes:** Unintentional Cartesian product from a missing JOIN condition, or a very expensive aggregation on large data.

---

### EXECUTION_ERROR

**Definition:** The SQL is syntactically valid but fails at runtime for a reason other than a schema error (e.g. type mismatch, division by zero, constraint violation).

**Example:**

```sql
-- Generated (divides by zero if no visits exist for a hospital):
SELECT h.name, SUM(v.fee) / COUNT(v.id) FROM hospitals h
JOIN doctor_visits v ON h.id = v.hospital_id
GROUP BY h.id;
-- Use AVG() instead of manual division to avoid this
```

---

### WRONG_LIMIT

**Definition:** A LIMIT clause is present with the wrong value, or is missing when only one result was expected.

**Example:**

```sql
-- Bengali query: "সবচেয়ে বেশি রোগী আছে এমন ৩টি হাসপাতাল দেখান।"
-- (Show the top 3 hospitals with the most patients.)

-- Generated:
... ORDER BY patient_count DESC LIMIT 1;
-- ↑ LIMIT 1 instead of LIMIT 3
```

---

### EXTRA_ROWS

**Definition:** The query returns more rows than expected, typically because a LIMIT clause was omitted or a DISTINCT was missing.

**Example:**

```sql
-- Expected: 1 row (the top shop)
-- Generated: all shops ranked — missing LIMIT 1
SELECT s.name, SUM(sl.amount) AS total_sales
FROM shops s
JOIN sales sl ON s.id = sl.shop_id
GROUP BY s.id
ORDER BY total_sales DESC;
-- Missing: LIMIT 1
```

---

## Error Co-occurrence Patterns

Some errors frequently appear together as primary + secondary pairs:

| Primary Error | Common Secondary | Explanation |
|---|---|---|
| MISSING_GROUP_BY | WRONG_ROWS | No grouping → single collapsed row |
| WRONG_JOIN (INNER) | WRONG_ROWS | Missing zero-count rows |
| WRONG_WHERE | WRONG_ROWS | Filter too broad or too narrow |
| SYNTAX_ERROR | — | Always primary; execution never starts |
| MISSING_WHERE | EXTRA_ROWS | No filter → returns all rows |

---

## Quick Reference

| Error | Group | Frequency (baseline avg) |
|---|---|:---:|
| WRONG_ROWS | Result | 20% |
| WRONG_WHERE | Logic | 18% |
| SYNTAX_ERROR | Syntax | 15% |
| MISSING_JOIN | Logic | 12% |
| WRONG_AGGREGATION | Logic | 10% |
| WRONG_GROUP_BY | Logic | 8% |
| MISSING_GROUP_BY | Logic | 7% |
| COLUMN_NOT_FOUND | Schema | 5% |
| PARTIAL_MATCH | Result | 5% |

---

*See [`docs/query_examples.md`](query_examples.md) for annotated walkthroughs of real benchmark queries where these errors occur.*
