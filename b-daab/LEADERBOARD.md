# B-DAAB Leaderboard

Tracks model performance on the B-DAAB benchmark (20 Bengali NL-to-SQL queries).

Submit your results by opening a pull request — see [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Overall Accuracy

| Rank | Model | Team | Version | Exact Match | Execution | Result | Date |
|:----:|-------|------|---------|:-----------:|:---------:|:------:|------|
| 1 | Claude 3.5 Sonnet | Anuj Sarker | 1.0.0 | 75% | 90% | 75% | 2026-05-24 |
| 2 | GPT-4 | Anuj Sarker | 1.0.0 | 68% | 85% | 68% | 2026-05-24 |
| 3 | Llama 2 70B | Anuj Sarker | 1.0.0 | 62% | 78% | 62% | 2026-05-24 |

---

## By Difficulty

| Rank | Model | Easy (7) | Medium (8) | Hard (5) |
|:----:|-------|:--------:|:----------:|:--------:|
| 1 | Claude 3.5 Sonnet | 100% | 75% | 40% |
| 2 | GPT-4 | 86% | 62% | 40% |
| 3 | Llama 2 70B | 71% | 62% | 40% |

---

## By Domain

| Rank | Model | Healthcare (8) | Education (4) | Retail (8) |
|:----:|-------|:--------------:|:-------------:|:----------:|
| 1 | Claude 3.5 Sonnet | 87.5% | 75% | 62.5% |
| 2 | GPT-4 | 75% | 75% | 50% |
| 3 | Llama 2 70B | 62.5% | 50% | 62.5% |

---

## By Language Variant

| Rank | Model | Standard Bengali (10) | Dialect (5) | Code-mixed (5) |
|:----:|-------|:---------------------:|:-----------:|:--------------:|
| 1 | Claude 3.5 Sonnet | 80% | 80% | 60% |
| 2 | GPT-4 | 70% | 60% | 60% |
| 3 | Llama 2 70B | 70% | 60% | 40% |

---

## Error Distribution

Top error types observed across all evaluated models:

| Error Type | Frequency | Primary Cause |
|---|:---------:|---|
| WRONG_ROWS | 20% | GROUP BY aggregation issues |
| WRONG_WHERE | 18% | Missing or incorrect WHERE conditions |
| SYNTAX_ERROR | 15% | Complex JOIN constructs |
| MISSING_JOIN | 12% | Multi-table queries |
| WRONG_AGGREGATION | 10% | COUNT/SUM misuse |

---

## Submitting Results

1. Run the full benchmark evaluation:
   ```bash
   python main.py evaluate \
       --model <your_model_name> \
       --version <version> \
       --team "<your_name>" \
       --llm <provider>
   ```

2. This generates `evaluation_results/<timestamp>_results.json`.

3. Open a pull request with:
   - The result JSON file added to `evaluation_results/`
   - Your row added to each table in this file (maintaining rank order by Exact Match)

---

## Metric Definitions

| Metric | Definition |
|---|---|
| **Exact Match** | Generated SQL matches ground truth exactly (after normalization) |
| **Execution** | Generated SQL executes without runtime error |
| **Result** | Query output matches expected rows and columns |

---

**Maintained by**: [Anuj Sarker](mailto:anuj.eee.00724105131179@aust.edu) · [github.com/twistedninja02](https://github.com/twistedninja02)
