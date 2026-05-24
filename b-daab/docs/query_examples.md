# B-DAAB Query Examples

Annotated walkthroughs of representative benchmark queries — covering the Bengali input, linguistic analysis, ground truth SQL reasoning, and observed failure patterns across evaluated models.

---

## Example 1 — Easy · Standard Bengali · Healthcare

### Input

| | |
|---|---|
| **Bengali** | সকল হাসপাতালের তালিকা দেখান। |
| **Romanized** | Shokal haspataler talika dekhan. |
| **English** | Show the list of all hospitals. |
| **ID** | q001 |

### Linguistic Analysis

A simple imperative construction. The word _হাসপাতালের_ is the genitive plural of _হাসপাতাল_ (hospital), formed by the suffix _-এর_. The verb _দেখান_ is the formal imperative of _দেখা_ (to show/see). No ambiguity — the query maps directly to a full-table scan.

### Ground Truth SQL

```sql
SELECT * FROM hospitals;
```

**Reasoning:** No filtering, ordering, or aggregation required. The command "show list of all" maps to an unrestricted SELECT.

### Model Performance

| Model | Result |
|---|---|
| Claude 3.5 Sonnet | ✅ Exact match |
| GPT-4 | ✅ Exact match |
| Llama 2 70B | ✅ Exact match |

### Common Failure Patterns

None observed — this query serves as a sanity check for schema awareness. All models passed.

---

## Example 2 — Easy · Standard Bengali · Healthcare

### Input

| | |
|---|---|
| **Bengali** | মোট কতজন রোগী আছেন? |
| **Romanized** | Moto kotojon rogi achen? |
| **English** | How many patients are there in total? |
| **ID** | q002 |

### Linguistic Analysis

_মোট_ means "total/altogether". _কতজন_ is a classifier-fused interrogative: _কত_ (how many) + _জন_ (the human classifier, used exclusively for people). Models that lack Bengali-specific tokenization may fail to decompose _কতজন_ correctly and produce a wrong target column or miss the COUNT intent.

### Ground Truth SQL

```sql
SELECT COUNT(*) AS total_patients FROM patients;
```

**Reasoning:** _কতজন_ signals COUNT aggregation over the entire patients table. The alias _total_patients_ is preferred for readability but not required for result match.

### Model Performance

| Model | Result |
|---|---|
| Claude 3.5 Sonnet | ✅ Exact match |
| GPT-4 | ✅ Exact match |
| Llama 2 70B | ✅ Exact match |

### Common Failure Patterns

Occasional failure: generating `COUNT(patient_id)` vs `COUNT(*)` — both are semantically correct but fail strict exact-match evaluation. This is why B-DAAB uses normalized match as the primary metric alongside exact match.

---

## Example 3 — Medium · Standard Bengali · Healthcare

### Input

| | |
|---|---|
| **Bengali** | প্রতিটি হাসপাতালে কত জন রোগী আছেন? |
| **Romanized** | Protitek haspatale koto jon rogi achen? |
| **English** | How many patients are registered in each hospital? |
| **ID** | q003 |

### Linguistic Analysis

_প্রতিটি_ (protitek) means "each/every" and is a strong signal for GROUP BY. _হাসপাতালে_ is the locative form of _হাসপাতাল_ (in the hospital). The phrase _প্রতিটি X-এ কত_ is a reliable syntactic pattern for per-group COUNT queries.

### Ground Truth SQL

```sql
SELECT h.name, COUNT(p.id) AS patient_count
FROM hospitals h
LEFT JOIN patients p ON h.id = p.hospital_id
GROUP BY h.id
ORDER BY h.name;
```

**Reasoning:**
- LEFT JOIN is required because some hospitals may have zero patients — an INNER JOIN would silently drop them, producing wrong row counts.
- GROUP BY `h.id` (not `h.name`) avoids potential duplicate name collisions.
- ORDER BY `h.name` ensures a deterministic, human-readable output order.

### Model Performance

| Model | Result |
|---|---|
| Claude 3.5 Sonnet | ✅ Exact match |
| GPT-4 | ⚠️ Partial — used INNER JOIN (missed hospitals with 0 patients) |
| Llama 2 70B | ❌ MISSING_GROUP_BY — returned per-row data without aggregation |

### Common Failure Patterns

1. **INNER JOIN instead of LEFT JOIN** — the most frequent medium-difficulty error. Models that default to INNER JOIN produce correct results only when all hospitals have at least one patient.
2. **MISSING_GROUP_BY** — weaker models produce `SELECT h.name, COUNT(p.id) FROM hospitals h JOIN patients p ...` without GROUP BY, causing a SQL error or returning a single aggregated row.
3. **GROUP BY h.name instead of h.id** — logically fragile; fails if two hospitals share a name.

---

## Example 4 — Medium · Dialect (Sylheti-influenced) · Healthcare

### Input

| | |
|---|---|
| **Bengali** | হাসপাতাল ভেদে গড় চিকিৎসা খরচ বের করো। |
| **Romanized** | Haspatol vede gôṛ chikitsha khoroch ber koro. |
| **English** | Find the average treatment cost per hospital. |
| **ID** | q012 |

### Linguistic Analysis

_ভেদে_ is a postposition meaning "by/according to" — it modifies _হাসপাতাল_ to express the grouping dimension (per hospital). _গড়_ means "average". _চিকিৎসা খরচ_ is a compound noun: _চিকিৎসা_ (treatment/medical) + _খরচ_ (cost/expense). _বের করো_ is an informal imperative meaning "find out/extract". The dialect marker here is the informal _করো_ (standard would be _করুন_) and the vowel quality in _হাসপাতাল_ → _হাসপাতল_.

### Ground Truth SQL

```sql
SELECT h.name, AVG(v.fee) AS avg_fee
FROM hospitals h
JOIN doctor_visits v ON h.id = v.hospital_id
GROUP BY h.id
ORDER BY avg_fee DESC;
```

**Reasoning:** _গড়_ unambiguously maps to AVG. The grouping dimension _হাসপাতাল ভেদে_ maps to GROUP BY hospital. INNER JOIN is appropriate here because we only want hospitals that have visit records.

### Model Performance

| Model | Result |
|---|---|
| Claude 3.5 Sonnet | ✅ Exact match |
| GPT-4 | ✅ Exact match |
| Llama 2 70B | ⚠️ Partial — omitted ORDER BY |

### Common Failure Patterns

1. **Missing ORDER BY** — the phrase _বের করো_ carries no explicit ordering cue, so models omit it. B-DAAB treats omitted ORDER BY as a partial match when row content is correct.
2. **Schema mismatch** — models unfamiliar with the schema sometimes target a non-existent `cost` column instead of `fee` in `doctor_visits`.

---

## Example 5 — Hard · Standard Bengali · Retail

### Input

| | |
|---|---|
| **Bengali** | হাসপাতাল ভেদে গড় চিকিৎসা খরচ বের করো, শুধু যাদের গড় খরচ ৫০০ টাকার বেশি। |
| **Romanized** | Haspatol vede gôṛ chikitsha khoroch ber koro, shudhu jader gôṛ khoroch 500 takar beshi. |
| **English** | Find the average treatment cost per hospital, only for those where the average cost exceeds 500 taka. |
| **ID** | q019 |

### Linguistic Analysis

This extends Example 4 with a post-aggregation filter. _শুধু যাদের_ means "only those whose" — a relative clause that applies to the grouped results, not to individual rows. _৫০০ টাকার বেশি_ means "more than 500 taka". The critical semantic cue is that the filter applies to the group average (_গড় খরচ_), not to individual visit fees — requiring HAVING, not WHERE.

### Ground Truth SQL

```sql
SELECT h.name, AVG(v.fee) AS avg_fee
FROM hospitals h
JOIN doctor_visits v ON h.id = v.hospital_id
GROUP BY h.id
HAVING AVG(v.fee) > 500
ORDER BY avg_fee DESC;
```

**Reasoning:** The relative clause _যাদের গড় খরচ ৫০০ টাকার বেশি_ applies to the aggregate result of each group, making HAVING the correct clause. WHERE would filter individual rows before aggregation, producing a different (incorrect) result.

### Model Performance

| Model | Result |
|---|---|
| Claude 3.5 Sonnet | ✅ Exact match |
| GPT-4 | ❌ WRONG_WHERE — used `WHERE v.fee > 500` instead of `HAVING` |
| Llama 2 70B | ❌ WRONG_WHERE — same error |

### Common Failure Patterns

1. **WHERE instead of HAVING** — the most diagnostic hard-query failure in B-DAAB. All models except Claude 3.5 Sonnet made this mistake. It reveals that models may understand the grouping intent but fail to correctly select the SQL clause when the filter operates on an aggregate.
2. **Hardcoded literal** — some models write `HAVING AVG(v.fee) > 500.00` (float) vs `> 500` (integer). B-DAAB normalizes numeric literals during comparison.

---

## Example 6 — Hard · Code-mixed (Banglish) · Education

### Input

| | |
|---|---|
| **Bengali** | Kon school e shobcheye beshi student ache? Name ta dao. |
| **Romanized** | (already romanized — Banglish) |
| **English** | Which school has the most students? Give the name. |
| **ID** | q020 |

### Linguistic Analysis

This is a fully code-mixed (Banglish) query written in Latin script using Bengali phonology. Key terms: _kon_ (which), _shobcheye beshi_ (most/greatest — superlative construction), _student ache_ (students are there), _name ta dao_ (give the name — informal imperative). There is no Bengali Unicode — models must rely entirely on phonological and semantic understanding of transliterated Bengali to identify the MAX-COUNT-over-GROUP superlative pattern.

### Ground Truth SQL

```sql
SELECT s.name
FROM schools s
JOIN students st ON s.id = st.school_id
GROUP BY s.id
ORDER BY COUNT(st.id) DESC
LIMIT 1;
```

**Reasoning:** _shobcheye beshi_ (most) signals a superlative over a COUNT. The canonical SQL pattern is GROUP BY → ORDER BY COUNT DESC → LIMIT 1, which avoids subqueries and is more portable than `WHERE id = (SELECT ...)`.

### Model Performance

| Model | Result |
|---|---|
| Claude 3.5 Sonnet | ⚠️ Partial — used correct structure but missed `GROUP BY s.id`, used `s.name` |
| GPT-4 | ⚠️ Partial — correct logic, used subquery form with syntax error |
| Llama 2 70B | ❌ SYNTAX_ERROR — malformed subquery, missing closing parenthesis |

### Common Failure Patterns

1. **Subquery instability** — models frequently attempt `WHERE id = (SELECT school_id ... LIMIT 1)` but introduce syntax errors (missing parentheses, wrong column references).
2. **Banglish parsing failure** — weaker models fail to link _shobcheye beshi_ to a superlative SQL pattern, producing a plain SELECT with no aggregation.
3. **Wrong table reference** — _student_ (Banglish) is conflated with the `schools` table rather than `students`, producing a self-join.

---

## Summary of Linguistic Signals → SQL Patterns

| Bengali / Banglish phrase | English meaning | SQL construct |
|---|---|---|
| _প্রতিটি X-এ_ / _X ভেদে_ | per X / by X | `GROUP BY X` |
| _মোট কতজন_ / _কতটি_ | how many (people/things) | `COUNT(*)` |
| _গড়_ | average | `AVG(...)` |
| _সর্বাধিক_ / _shobcheye beshi_ | most / maximum | `ORDER BY ... DESC LIMIT 1` |
| _শুধু যাদের [aggregate] > N_ | only those where [agg] > N | `HAVING [agg] > N` |
| _সকল_ / _সব_ | all | `SELECT *` / no WHERE |
| _শুধু_ / _যেখানে_ | only / where | `WHERE` |
| _বেশি_ / _কম_ | more than / less than | `>` / `<` |

---

*For the full annotated dataset, see [`data/tasks.json`](../data/tasks.json). To run these queries against the benchmark, see [`scripts/run_baseline.sh`](../scripts/run_baseline.sh).*
