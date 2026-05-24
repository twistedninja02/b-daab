# B-DAAB

Bengali Database as a Benchmark — a framework for evaluating Bengali Natural Language to SQL conversion.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Single query

```bash
python main.py query "সকল হাসপাতালের তালিকা দেখান"
python main.py query "সকল হাসপাতালের তালিকা দেখান" --english "Show all hospitals" --llm anthropic
```

### Full benchmark evaluation

```bash
python main.py evaluate --model my_model --team my_team --llm mock
python main.py evaluate --dataset data/tasks.json --limit 10 --llm anthropic
```

### View metrics

```bash
python main.py metrics --results evaluation_results/evaluation_*.json
```

### Leaderboard

```bash
python main.py leaderboard --top 10
```

## LLM Providers

| Flag | Provider |
|------|----------|
| `mock` | Built-in pattern matcher (no API key needed) |
| `anthropic` | Claude via Anthropic API |
| `openai` | GPT via OpenAI API |
| `ollama` | Local model via Ollama |

Set your API key via environment variable before using a real provider:

```bash
export ANTHROPIC_API_KEY=sk-...
export OPENAI_API_KEY=sk-...
```

## Project Structure

```
b-daab/
├── main.py               # CLI entry point
├── db.py                 # DuckDB initialization and queries
├── executor.py           # Safe SQL execution layer
├── logging_config.py     # Logging setup
├── requirements.txt
├── agent/
│   ├── planner.py        # SQL generation agent + LLM clients
│   └── prompt.py         # Prompt templates and few-shot library
├── eval/
│   ├── metrics.py        # Evaluation metrics and error classification
│   └── runner.py         # Evaluation pipeline and leaderboard
└── data/
    └── tasks.json        # Benchmark task dataset
```

## Adding Data

Place your DuckDB schema in `data/schemas.sql` and seed data in `data/sample_data.sql`. The database is initialized in-memory by default; pass `--db-path mydb.duckdb` to persist it.
