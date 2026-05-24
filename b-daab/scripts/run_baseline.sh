#!/usr/bin/env bash
# run_baseline.sh — Reproduce B-DAAB leaderboard baseline results
#
# Usage:
#   ./scripts/run_baseline.sh              # runs all three providers
#   ./scripts/run_baseline.sh mock         # runs mock only (no API key needed)
#   ./scripts/run_baseline.sh anthropic    # runs Anthropic only
#   ./scripts/run_baseline.sh openai       # runs OpenAI only
#
# Required environment variables (for real providers):
#   ANTHROPIC_API_KEY   — for --llm anthropic
#   OPENAI_API_KEY      — for --llm openai

set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────

DATASET="data/tasks.json"
VERSION="1.0.0"
TEAM="Anuj Sarker"
RESULTS_DIR="evaluation_results"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Providers to run (default: all three)
PROVIDERS=("${@:-mock anthropic openai}")
if [ $# -gt 0 ]; then
    PROVIDERS=("$@")
else
    PROVIDERS=(mock anthropic openai)
fi

# ── Helpers ───────────────────────────────────────────────────────────────────

log()  { echo "[$(date +%H:%M:%S)] $*"; }
warn() { echo "[$(date +%H:%M:%S)] WARNING: $*" >&2; }
die()  { echo "[$(date +%H:%M:%S)] ERROR: $*" >&2; exit 1; }

check_api_key() {
    local provider="$1"
    case "$provider" in
        anthropic)
            [ -n "${ANTHROPIC_API_KEY:-}" ] || die "ANTHROPIC_API_KEY is not set. Export it before running."
            ;;
        openai)
            [ -n "${OPENAI_API_KEY:-}" ] || die "OPENAI_API_KEY is not set. Export it before running."
            ;;
    esac
}

run_provider() {
    local provider="$1"
    local model_name

    case "$provider" in
        mock)      model_name="mock_baseline" ;;
        anthropic) model_name="claude_35_sonnet" ;;
        openai)    model_name="gpt4" ;;
        ollama)    model_name="llama2_70b" ;;
        *)         die "Unknown provider: $provider. Choose: mock, anthropic, openai, ollama" ;;
    esac

    log "Running evaluation: provider=$provider  model=$model_name"

    python main.py evaluate \
        --model    "$model_name" \
        --version  "$VERSION" \
        --team     "$TEAM" \
        --dataset  "$DATASET" \
        --llm      "$provider" \
        2>&1 | tee "${RESULTS_DIR}/${TIMESTAMP}_${provider}.log"

    log "Done: $provider — results saved to ${RESULTS_DIR}/"
    echo ""
}

# ── Pre-flight checks ─────────────────────────────────────────────────────────

[ -f "main.py" ] || die "Run this script from the b-daab project root."
[ -f "$DATASET" ] || die "Dataset not found at $DATASET."

command -v python >/dev/null 2>&1 || die "python not found in PATH."
python -c "import duckdb" 2>/dev/null || die "duckdb not installed. Run: pip install ."

mkdir -p "$RESULTS_DIR"

# ── Run ───────────────────────────────────────────────────────────────────────

echo "=============================================="
echo "  B-DAAB Baseline Evaluation"
echo "  Team:      $TEAM"
echo "  Version:   $VERSION"
echo "  Dataset:   $DATASET"
echo "  Providers: ${PROVIDERS[*]}"
echo "  Started:   $(date)"
echo "=============================================="
echo ""

for provider in "${PROVIDERS[@]}"; do
    if [ "$provider" != "mock" ]; then
        check_api_key "$provider"
    fi
    run_provider "$provider"
done

# ── Summary ───────────────────────────────────────────────────────────────────

echo "=============================================="
echo "  All evaluations complete."
echo ""
echo "  View aggregate metrics:"
echo "    python main.py metrics --results ${RESULTS_DIR}/*.json"
echo ""
echo "  View leaderboard:"
echo "    python main.py leaderboard --top 10"
echo "=============================================="
