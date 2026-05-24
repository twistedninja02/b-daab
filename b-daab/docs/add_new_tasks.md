# Adding New Benchmark Tasks

A complete guide to writing, annotating, and validating a new B-DAAB query before submitting it as a pull request.

---

## Quality Bar

Every new task must meet all of the following criteria before it is accepted:

- Written in Bengali (standard, dialect, or code-mixed) — not English
- Targets a real table and column in `data/schemas.sql`
- Has a single, unambiguous ground truth SQL query
- Has a manually verified expected result that matches the ground truth SQL output on `data/sample_data.sql`
- Covers a linguistic phenomenon or SQL construct not already covered by an existing task
- Assigned a correct difficulty rating (see criteria below)

---

## Step 1 — Pick a Query Idea

Choose a query that tests something meaningful. Good candidates:

- A Bengali linguistic structure not yet in the benchmark (e.g. a new postposition, a superlative form, a code-mixed phrasing)
- A SQL construct not yet covered (e.g. HAVING, subquery, multi-table JOIN, DISTINCT)
- A new domain concept (e.g. exam scores, monthly expenses, product inventory)

Check `data/tasks.json` first to avoid duplicates. Scan the `id`, `query_bengali`, and `sql_ground_truth` fields.

---

## Step 2 — Write the Query

Write the Bengali query in three forms:

| Field | Description | Example |
|---|---|---|
| `query_bengali` | Unicode Bengali script | `প্রতিটি দোকানের মোট বিক্রয় কত?` |
| `query_romanized` | Bengali phonetics in Latin script | `Protitek dokan-er moto bikroy koto?` |
| `query_english` | Plain English translation | `What is the total sales for each shop?` |

**Rules:**
- Use formal Bengali for `standard` category; regional phonology for `dialect`; mixed Latin+Bengali for `code-mixed`
- Avoid English loanwords in `standard` queries unless they are in everyday Bangladeshi use (e.g. hospital, school)
- The English translation must be literal, not paraphrased

---

## Step 3 — Write the Ground Truth SQL

Write the SQL query that exactly answers the Bengali question against the B-DAAB schema.

**Rules:**
- Use lowercase SQL keywords
- Use table aliases (`h` for hospitals, `p` for patients, `s` for schools, etc.)
- Prefer `LEFT JOIN` over `INNER JOIN` when zero-count rows are semantically meaningful
- Use `GROUP BY primary_key` (e.g. `GROUP BY h.id`), not `GROUP BY name`
- Use `HAVING` for post-aggregation filters, never `WHERE`
- Always include `ORDER BY` when the result order is meaningful or when using `LIMIT`

**Verify it runs:**

```bash
cd b-daab
python main.py query "<your Bengali query>" --english "<English translation>" --llm mock
```

Then run your SQL directly to confirm the output:

```python
import duckdb
conn = duckdb.connect()

# Load schema and data
conn.execute(open("data/schemas.sql").read())
conn.execute(open("data/sample_data.sql").read())

# Run your ground truth SQL
result = conn.execute("<your SQL here>").fetchall()
print(result)
```

---

## Step 4 — Determine Difficulty

Use this rubric:

| Difficulty | Criteria |
|---|---|
| **easy** | Single table, no JOIN, no aggregation, or a simple COUNT/SELECT ALL |
| **medium** | One JOIN, one aggregation (COUNT/AVG/SUM), GROUP BY, or a WHERE with a non-trivial condition |
| **hard** | Multiple JOINs, HAVING clause, subquery, superlative (ORDER BY + LIMIT), or code-mixed input requiring linguistic inference |

When in doubt, rate harder rather than easier. Overestimating difficulty is less harmful than understating it.

---

## Step 5 — Record the Expected Result

Run your ground truth SQL on the sample data and record the output as the `expected_result` field.

Format rules:

- `expected_result.type`: `"rows"` for multi-row results, `"scalar"` for single values
- `expected_result.columns`: list of column names in order
- `expected_result.rows`: list of row values (each row is a list)
- `expected_result.row_count`: total number of rows returned

**Example for a multi-row result:**

```json
"expected_result": {
  "type": "rows",
  "columns": ["name", "total_sales"],
  "rows": [
    ["Dhaka Electronics", 77000.00],
    ["Sylhet Cloth House", 2000.00],
    ["CTG Furniture", 3500.00]
  ],
  "row_count": 3
}
```

**Example for a scalar result:**

```json
"expected_result": {
  "type": "scalar",
  "columns": ["total_patients"],
  "rows": [[10]],
  "row_count": 1
}
```

---

## Step 6 — Add to tasks.json

Open `data/tasks.json` and add your new task object to the `tasks` array. Assign the next available ID (e.g. if the last task is `q005`, yours is `q006`).

**Full task schema:**

```json
{
  "id": "q006",
  "query_bengali": "প্রতিটি দোকানের মোট বিক্রয় কত?",
  "query_romanized": "Protitek dokan-er moto bikroy koto?",
  "query_english": "What is the total sales for each shop?",
  "category": "standard",
  "difficulty": "medium",
  "domain": "retail",
  "sql_ground_truth": "SELECT s.name, SUM(sl.amount) AS total_sales FROM shops s LEFT JOIN sales sl ON s.id = sl.shop_id GROUP BY s.id ORDER BY s.name;",
  "expected_result": {
    "type": "rows",
    "columns": ["name", "total_sales"],
    "rows": [
      ["CTG Furniture", 3500.00],
      ["Dhaka Electronics", 77000.00],
      ["Sylhet Cloth House", 2000.00]
    ],
    "row_count": 3
  },
  "reasoning": "Tests LEFT JOIN + SUM aggregation with GROUP BY. The postposition -এর signals possession/grouping. প্রতিটি signals per-group aggregation."
}
```

**Field reference:**

| Field | Type | Allowed values |
|---|---|---|
| `id` | string | `q001`–`q999` (sequential) |
| `query_bengali` | string | Bengali Unicode text |
| `query_romanized` | string | Latin-script Bengali phonetics |
| `query_english` | string | Literal English translation |
| `category` | string | `standard`, `dialect`, `code-mixed` |
| `difficulty` | string | `easy`, `medium`, `hard` |
| `domain` | string | `healthcare`, `education`, `retail` |
| `sql_ground_truth` | string | Valid DuckDB SQL |
| `expected_result` | object | See schema above |
| `reasoning` | string | Linguistic and SQL phenomena tested |

---

## Step 7 — Run the Tests

After adding your task, run the full test suite to make sure nothing is broken:

```bash
pip install ".[dev]"
pytest tests/ -v
```

All 35 existing tests must pass. If your new task changes any fixture data in `data/sample_data.sql`, update the corresponding test expectations.

---

## Step 8 — Run a Mock Evaluation

Verify your task appears in the evaluation pipeline:

```bash
python main.py evaluate \
    --dataset data/tasks.json \
    --model test_run \
    --version 0.0.1 \
    --team "Your Name" \
    --llm mock
```

Check the output — your new task ID should appear in the results.

---

## Step 9 — Open a Pull Request

1. Fork the repo and create a branch: `data/add-q006-shop-sales`
2. Commit only `data/tasks.json` (and `data/sample_data.sql` if you added rows)
3. In the PR description include:
   - The Bengali query and English translation
   - The ground truth SQL
   - Why this task adds value (what phenomenon or SQL construct it tests)
   - Screenshot or paste of the expected result from your local run

---

## Common Mistakes to Avoid

| Mistake | Why it's a problem |
|---|---|
| Using INNER JOIN when a hospital/school with 0 records should appear | Silently drops rows — expected_result will be wrong |
| GROUP BY column name instead of id | Breaks if two entities share a name |
| Writing expected_result by hand without running the SQL | Values may be wrong — always run it |
| Duplicate linguistic phenomenon | Adds noise without increasing benchmark coverage |
| English query in `query_bengali` field | Defeats the purpose of the benchmark |
| Missing `reasoning` field | Makes it hard to understand what the task is testing |

---

*For more context on the benchmark design, see [`docs/query_examples.md`](query_examples.md). For error categories used in evaluation, see [`docs/error_taxonomy.md`](error_taxonomy.md).*
