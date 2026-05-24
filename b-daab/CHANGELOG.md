# Changelog

All notable changes to B-DAAB will be documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [1.0.0] — 2026-05-24

### Added
- `main.py` — CLI with four commands: `query`, `evaluate`, `metrics`, `leaderboard`
- `db.py` — DuckDB initialization, schema loading, sample data loading, and validation
- `executor.py` — Safe SQL execution layer with query sanitization, safety checks, and execution metrics
- `logging_config.py` — Rotating file + colored console logging with optional JSON output
- `agent/planner.py` — SQL generation agent supporting Anthropic, OpenAI, Ollama, and Mock providers
- `agent/prompt.py` — Prompt templates (Basic, Detailed, Chain-of-Thought, Few-Shot) and few-shot library
- `eval/metrics.py` — Query and aggregate metrics, SQL normalization, result comparison, error classification
- `eval/runner.py` — Full evaluation pipeline with JSON, CSV, and leaderboard output
- `docs/query_examples.md` — Annotated walkthroughs of 6 representative benchmark queries with linguistic analysis, SQL reasoning, and failure patterns
- `scripts/run_baseline.sh` — One-command script to reproduce all baseline results across mock, Anthropic, and OpenAI providers
- `data/tasks.json` — Initial benchmark dataset with 5 Bengali NL-to-SQL tasks across healthcare and education domains
- `data/schemas.sql` — DuckDB schema for hospitals, patients, schools, students, shops, and products tables
- `data/sample_data.sql` — Sample data aligned with `tasks.json` expected results (10 patients, 5 hospitals, 5 schools, 3 shops, 5 products)
- `tests/` — 35 unit tests covering SQL normalization, query safety, metrics calculation, and aggregation
- `pyproject.toml` — Package configuration with runtime and dev dependency groups
- `.github/workflows/ci.yml` — CI pipeline (lint, type check, format check, tests) on every push and PR
- `LICENSE` — MIT license
- `README.md` — Installation, usage, LLM provider guide, project structure
- `CONTRIBUTING.md` — Setup guide, branch conventions, code style, PR process, task schema

---

## [Unreleased]

### Planned
- Expanded benchmark dataset (50+ tasks across more domains)
- Dialect-aware evaluation (Sylheti, Chittagonian, Barisali variants)
- Schema-aware few-shot example retrieval
- HTML evaluation report generation
- Support for additional LLM providers (Gemini, Mistral API)
