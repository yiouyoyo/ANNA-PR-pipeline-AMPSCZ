# ANNA-PR Pipeline Architecture

## Overview

The pipeline has **12 Python files** organized into **3 entry points** (files you run) and **9 library files** (imported automatically). Understanding the distinction will help you navigate the codebase.

---

## 3 Entry-Point Files (What You Run)

These are the only files you execute directly from the command line:

### 1. `build_batch.py`
**Purpose**: Convert raw transcript files (.txt, .json) into a standardized CSV.

**Command**:
```bash
python build_batch.py \
  --input_dir data/transcripts \
  --output_csv data/batch_input.csv \
  --gold_csv data/human_scores.csv  # optional
```

**Output**: `data/batch_input.csv` with columns:
- `row_id`, `transcript_id`, `source_file`, `text_length`, `transcript`, `human_score`, `qaqc_flags`

**Run once** to prepare data for scoring.

---

### 2. `run_scoring.py`
**Purpose**: Orchestrate the 8-step PSYCHS P2 scoring pipeline on all transcripts.

**Command**:
```bash
python run_scoring.py \
  --input_csv data/batch_input.csv \
  --output_csv outputs/scored_gptoss_zs.csv \
  --model gptoss \
  --model_name "your-model-id" \
  --condition ZS \
  --temperature 0.0 \
  --max_tokens 512
```

**Output**: `outputs/scored_gptoss_zs.csv` with ~35 columns including all step scores and diagnostics.

**Features**:
- Automatically processes all rows in input CSV
- Flushes each row to disk immediately (resume-safe)
- Skips already-scored rows on re-run
- Supports `--dry_run` mode (no GPU/LLM calls)

---

### 3. `evaluate.py`
**Purpose**: Compute performance metrics across all scored outputs.

**Command**:
```bash
python evaluate.py \
  --scored_dir outputs/ \
  --output_csv outputs/metrics_report.csv
```

**Output**: CSV and summary table with:
- ICC(2,1) between LLM scores and human scores
- Exact match %, adjacent agreement %, sensitivity/specificity at CHR boundary
- Per-model, per-condition breakdown

---

## 9 Library Files (Imported Automatically)

These files are **never called directly**. They are imported by the entry-point files and run inside the pipeline.

### **prompts/ folder (6 files)**

Contains the anchor texts and system prompts for each LLM scoring step.

- **`general_rules.py`**
  - Shared preamble inserted into every LLM prompt
  - Clinical rating rules, scale definition (0-6), ATHEORETICAL instruction
  - Imported by: `chain.py`

- **`step1_screen.py`**
  - System prompt for screening step (Is P2 content present?)
  - Imported by: `chain.py` → used in LLM call 1

- **`step2_description.py`**
  - Anchor text for Description score (0-6)
  - Detailed behavioral benchmarks
  - Imported by: `chain.py` → used in LLM call 2

- **`step3_tenacity.py`**
  - Anchor text for Tenacity score (0-6, CONDITIONAL on D>0)
  - "When asked" vs "spontaneous doubt" distinctions
  - Imported by: `chain.py` → used in LLM call 3

- **`step5_distress.py`**
  - Anchor text for Distress score (0-6, SECONDARY tiebreaker)
  - Only used when D and T are adjacent or within odd diff
  - Imported by: `chain.py` → used in LLM call 4 (conditional)

- **`step6_interference.py`**
  - Anchor text for Interference score (0-6, SECONDARY tiebreaker)
  - Behavioral/social impact definitions
  - Imported by: `chain.py` → used in LLM call 5 (conditional)

- **`step7_frequency.py`**
  - Anchor text for Frequency scores (PM and LT/PY, 0-6 each)
  - Duration/frequency definitions per CAARMS/SIPS manual
  - Imported by: `chain.py` → used in LLM call 6

---

### **scoring/ folder (3 files)**

Core Python logic for the pipeline orchestration and synthesis.

- **`chain.py`**
  - Main orchestrator: `score_transcript(transcript, llm_backend, condition)`
  - Implements the 8-step dependency chain exactly as specified
  - Manages conditional LLM calls (skips tenacity if D=0, skips distress/interference if no tiebreaker)
  - Imports: `general_rules.py`, all `step*.py` files, `synthesize.py`, `diagnostics.py`
  - Called by: `run_scoring.py`

- **`synthesize.py`**
  - Function: `synthesize_p2_severity(D, T, distress, interference)`
  - Implements PSYCHS Table 3 logic in pure Python (no LLM)
  - Handles same scores, even averages, adjacent/odd tie-breaker logic
  - Called by: `chain.py` (step 4b)

- **`diagnostics.py`**
  - Function: `diagnostic_groupings(severity, frequency_pm, frequency_lt_py)`
  - Pure Python: converts final severity + frequency → diagnostic flags
  - Outputs: `lifetime_psychosis`, `sips_bips`, `sips_apss`, `caarms_blips`, etc.
  - Called by: `chain.py` (step 8)

---

### **models/ folder (2 files)**

Abstract interface and concrete implementations for LLM backends.

- **`base.py`**
  - Abstract class: `LLMBackend`
  - Method: `generate(prompt_system: str, prompt_user: str) -> str`
  - Inherited by: `gptoss.py`, `vllm_standard.py`

- **`gptoss.py`**
  - Concrete class: `GPTOSSBackend(LLMBackend)`
  - Uses vLLM + openai_harmony Harmony encoding
  - Implements: tokenization, prefix caching, temperature/max_tokens control
  - Instantiated by: `run_scoring.py` when `--model gptoss` is specified

- **`vllm_standard.py`**
  - Concrete class: `VLLMStandardBackend(LLMBackend)`
  - Uses vLLM with standard chat template (Llama, Gemma)
  - Implements: chat formatting, tokenization, generation parameters
  - Instantiated by: `run_scoring.py` when `--model llama` or `--model gemma` is specified

---

## Data Flow Diagram

```
Your 30 .txt transcripts
         ↓
   build_batch.py
         ↓
  data/batch_input.csv (30 rows)
         ↓
   run_scoring.py  ← MAIN ENTRY POINT
         ├─ imports chain.py
         │    ├─ imports prompts/*.py (all 6 step files)
         │    ├─ imports synthesize.py
         │    └─ imports diagnostics.py
         ├─ imports models/gptoss.py or vllm_standard.py
         │    └─ imports models/base.py
         │
         └─ For each transcript in batch_input.csv:
              call chain.score_transcript()
              ├─ (8 steps with conditional LLM calls)
              └─ write 1 output row → outputs/scored_*.csv
         
         ↓
 outputs/scored_gptoss_zs.csv (30 rows, ~35 columns)
         ↓
   evaluate.py
         ↓
 outputs/metrics_report.csv
```

---

## How It All Works Together (Example Run)

When you execute:
```bash
python run_scoring.py --input_csv data/batch_input.csv --output_csv outputs/scored_gptoss_zs.csv --model gptoss --condition ZS
```

**What happens internally:**

1. `run_scoring.py` reads your CSV
2. For each row (transcript):
   - Instantiates a `GPTOSSBackend` (from `models/gptoss.py`)
   - Calls `chain.score_transcript(transcript, backend, condition='ZS')`
   - Inside `chain.py`:
     - Step 1: Screening LLM call (uses `step1_screen.py` + `general_rules.py`)
     - If suspicious=False → write zeros, skip to next transcript
     - Step 2: Description LLM call (uses `step2_description.py` + `general_rules.py`)
     - Step 3: Tenacity LLM call (uses `step3_tenacity.py` + `general_rules.py`, or skip if D=0)
     - Step 4: Python synthesis check (pure logic, no LLM)
     - Step 5-6: Distress/Interference LLM calls (ONLY if tiebreaker needed, uses `step5_*.py`, `step6_*.py`)
     - Step 4b: Final synthesis via `synthesize.py` (pure Python, applies PSYCHS Table 3)
     - Step 7: Frequency LLM call (uses `step7_frequency.py`)
     - Step 8: Diagnostics via `diagnostics.py` (pure Python, computes flags)
   - Write result row to CSV
   - Flush to disk (safe point)
3. Repeat for next 29 transcripts
4. Close CSV and exit

---

## Summary

| File Type | Files | How to Use |
|-----------|-------|-----------|
| **Entry Points** | `build_batch.py`, `run_scoring.py`, `evaluate.py` | Run these directly from CLI |
| **Prompts** | 6 files in `prompts/` | Auto-imported by `chain.py` |
| **Scoring Logic** | 3 files in `scoring/` | Auto-imported by `chain.py` and `run_scoring.py` |
| **Model Backends** | 2-3 files in `models/` | Auto-instantiated by `run_scoring.py` |
| **Tests** | 3 files in `tests/` | Run via `pytest` |

**You only ever run 3 commands:**
```bash
python build_batch.py ...
python run_scoring.py ...
python evaluate.py ...
```

All other files work in the background.
