# Contributing to B-DAAB

## Getting Started

**1. Fork the repository**

Click **Fork** on [github.com/twistedninja02/b-daab](https://github.com/twistedninja02/b-daab), then clone your fork:

```bash
git clone https://github.com/YOUR_USERNAME/b-daab.git
cd b-daab
```

**2. Set up your environment**

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install ".[dev]"
```

**3. Verify everything works**

```bash
pytest tests/ -v
python main.py query "সকল হাসপাতালের তালিকা দেখান"
```

---

## Making Changes

**Create a branch for your work:**

```bash
git checkout -b feature/your-feature-name
```

Branch naming conventions:
- `feature/` — new functionality
- `fix/` — bug fixes
- `data/` — new benchmark tasks or datasets
- `docs/` — documentation only

---

## Code Style

This project uses `black` for formatting and `flake8` for linting.

**Format your code before committing:**

```bash
black . --line-length 120
flake8 . --max-line-length=120 --exclude=__pycache__,.git
mypy . --ignore-missing-imports
```

Or run all three at once:

```bash
black . --line-length 120 && flake8 . --max-line-length=120 --exclude=__pycache__,.git && mypy . --ignore-missing-imports
```

---

## Running Tests

```bash
pytest tests/ -v
```

If you add a new feature, add a matching test in `tests/`. Test files follow the naming pattern `test_<module>.py`.

---

## Submitting a Pull Request

1. Push your branch to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

2. Open a pull request on GitHub against the `main` branch of `twistedninja02/b-daab`.

3. Fill in the PR description with:
   - What changed and why
   - Which queries or modules are affected
   - Test results (paste `pytest` output if relevant)

4. The CI pipeline runs automatically — make sure all three jobs (Lint, Format, Test) pass before requesting a review.

---

## Adding Benchmark Tasks

New tasks go in `data/tasks.json` under the `tasks` array. Follow this structure exactly:

```json
{
  "id": "q006",
  "query_bengali": "...",
  "query_english_gloss": "...",
  "category": "bengali_standard",
  "difficulty": "easy | medium | hard",
  "domain": "healthcare | education | ...",
  "dialect": "standard",
  "sql_ground_truth": "SELECT ...",
  "expected_result": [
    { "column": "value" }
  ]
}
```

Update `metadata.total_tasks` in the same file after adding tasks.

---

## Project Layout

```
b-daab/
├── main.py              # CLI entry point
├── db.py                # DuckDB setup
├── executor.py          # Safe SQL execution
├── logging_config.py    # Logging
├── agent/
│   ├── planner.py       # LLM-based SQL generation
│   └── prompt.py        # Prompt templates
├── eval/
│   ├── metrics.py       # Evaluation metrics
│   └── runner.py        # Evaluation pipeline
├── data/
│   └── tasks.json       # Benchmark dataset
└── tests/               # pytest test suite
```

---

## Questions

Open an issue on GitHub or email [anuj.eee.00724105131179@aust.edu](mailto:anuj.eee.00724105131179@aust.edu).
