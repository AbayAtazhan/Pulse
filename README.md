# Pulse: In-Play Match Reasoning

An evaluation framework designed to test whether Large Language Models (LLMs) can reason over evolving, incomplete states. Instead of pre-match forecasting, this project freezes real football matches at specific minutes ($T = 20, 45, 70$), exposes only the events up to that point, and evaluates the model's dynamic situational understanding and prediction calibration.

The framework runs evaluations on open-source models served via vLLM, testing Qwen and Gemma against a naive statistical baseline.

## Framework Architecture

The project is structured into five isolated modules to prevent data leakage and ensure reproducibility:

1. **Data Ingestion** (`src/data_ingestion/`): Fetches matches from StatsBomb Open Data (e.g., World Cup 2022) and parses them into a clean chronological event timeline, keeping key events (goals, shots, cards, substitutions, half boundaries) while filtering out high-frequency noise.
2. **State Freezing** (`src/state_freezer/`): Truncates the match events at minute $T$ and reconstructs the score. Strict verification assertions throw exceptions if any event from the future ($> T$) leaks into the prompt.
3. **Agent Loop** (`src/agent/`): Takes the frozen state, formats it into a prompt, and queries the LLM at temperature 0. The model is forced to output a structured JSON containing qualitative reads, next-goal/result predictions, confidence levels, and an `is_gradable` flag.
4. **Evaluation & Grading** (`src/evaluation/`): A deterministic rules-based grader evaluates predictions against the actual remaining events of the match (`real_continuation`). It also computes a naive baseline (the team leading at minute $T$ holds on).
5. **Analytics & Visualization** (`visualize_results.py` & `generate_report.py`): Computes aggregated accuracy by minute, bins prediction confidence to construct calibration curves, evaluates prediction vector shifts during critical events (Update Test), and outputs a formatted markdown report.

## Directory Structure

```text
Pulse/
├── data/
│   ├── raw/               # Raw downloaded datasets
│   └── processed/         # Parsed chronological match timelines
├── plots/                 # Generated evaluation plots
├── src/
│   ├── data_ingestion/    # StatsBomb parser
│   ├── state_freezer/     # Temporal truncation and leakage check
│   ├── agent/             # Prompt template and vLLM completions
│   └── evaluation/        # Grader logic and naive baseline rules
├── generate_report.py     # REPORT.md generator
├── run_pipeline_final.py  # Dual-model comparison and Update Test runner
├── run_pipeline_v1.py     # Single-model pipeline automation
├── visualize_results.py   # Plotting script (accuracy, calibration, updates)
├── requirements.txt       # Project dependencies
└── README.md
```

## Getting Started

### 1. Installation
Clone the repository and install dependencies:
```bash
pip install -r requirements.txt
```

### 2. Environment Setup
Configure your LLM endpoints by exporting environment variables (e.g., using `env.sh`):
```bash
export ANTHROPIC_BASE_URL="<your-endpoint>"
export ANTHROPIC_AUTH_TOKEN="<your-token>"
export ANTHROPIC_MODEL="qwen3.6-27b"
```

### 3. Running the Pipeline
To run a test pipeline (dry-run mode using simulated predictions) on 2 matches:
```bash
python run_pipeline_final.py --dry-run --matches 2
```

To run the full pipeline querying actual models on 20 matches:
```bash
python run_pipeline_final.py --matches 20
```
This saves the comparative logs to `final_comparison.json`.

### 4. Visualizing Results & Generating Reports
To generate plots (saved in the `plots/` folder) and compile the final academic report (`REPORT.md`):
```bash
python visualize_results.py
python generate_report.py
```

## Core Metrics Evaluated

- **Accuracy Scale**: Checks whether prediction accuracy improves as more information becomes available ($20m \to 45m \to 70m$).
- **Calibration Quality**: Evaluates whether the model's self-stated confidence correlates to its actual accuracy rate (perfect calibration follows $y=x$).
- **Update Consistency**: Calculates how logically predictions shift when a critical event (such as a goal or red card) occurs between freeze points.
- **Baseline Comparison**: Measures model accuracy against a naive in-play statistical rule (the leader at minute $T$ wins).

For a detailed analysis of the evaluation outcomes, refer to [REPORT.md](REPORT.md).
