# ANNA-PR Pipeline: Automated PSYCHS P2 Scoring via Local LLMs

## Project Overview

The ANNA-PR pipeline is an automated clinical interview scoring system that replicates the PSYCHS (Structured Interview for Prodromal Syndromes) P2 (Suspiciousness/Persecutory Ideation) measurement concept using local large language models. Part of the ANNA-PR project within the AMP-SCZ/ProNET consortium, this pipeline enables clinicians to score patient interviews for paranoia and suspicious thinking while maintaining complete data privacy — all transcripts remain on-cluster and no data leaves the machine.

## Architecture Overview

```
Raw Transcript (.txt / .json)
        ↓
QA/QC + P2 Extraction (Annie's existing scripts)
        ↓
build_batch.py → batch_input.csv (one row per transcript)
        ↓
run_scoring.py → 8-step chained LLM scoring
        ↓
scored_output.csv (~35 columns with all measurements)
        ↓
evaluate.py → ICC + metrics vs human raters
        ↓
metrics_report.csv
```

## Why Chained Prompting?

This pipeline uses **process supervision** rather than outcome supervision. Each measurement concept (Description, Tenacity, Distress, Interference, Frequency) is scored independently via separate LLM calls, with Python handling all synthesis logic. This design:
- **Minimizes token bloat**: Only single integers passed between steps, not full JSON blobs
- **Maximizes interpretability**: Each step produces explicit evidence quotations
- **Enforces decision-tree fidelity**: Python implements PSYCHS Figure 1/Table 3 exactly — the LLM never produces the final score directly
- **Enables audit trails**: Every intermediate step is recorded for clinical review

## Models Supported

- **GPT-OSS** via Harmony encoding + vLLM (custom lab infrastructure)
- **Llama 3.3-70B** via standard vLLM
- **Gemma 3-27B** via standard vLLM

All models run locally. Temperature is hardcoded to 0.0 for deterministic scoring.

## Requirements

- Python 3.10+
- `vllm >= 0.4.0`
- `pandas >= 2.0`
- `scipy >= 1.10` (for ICC)
- `bert-score >= 0.3.13` (for CoT reasoning evaluation)
- For GPT-OSS: `openai_harmony` (custom lab package)
- CUDA 12.0+ with sufficient VRAM (70B model needs ~40 GB)

## Installation

```bash
# Clone the repo
git clone https://github.com/yiouyoyo/ANNA-PR-pipeline-AMPSCZ.git
cd ANNA-PR-pipeline-AMPSCZ

# Create Python environment
python3.10 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip setuptools wheel
pip install vllm pandas scipy bert-score

# For GPT-OSS only (if available in lab infrastructure)
pip install openai_harmony
```

## How to Run

### Step 1: Prepare Batch Input

```bash
python build_batch.py \
  --input_dir /path/to/p2_extracted_transcripts \
  --output_csv data/batch_input.csv \
  --gold_csv /path/to/human_scores.csv
```

This reads all `.txt` and `.json` files from your input directory, computes QA/QC flags, and produces a single CSV with one transcript per row. Resume-safe: re-running skips files already processed by content hash.

**Output columns:**
- `row_id`, `transcript_id`, `source_file`, `file_type`, `text_length`, `content_hash`
- `transcript` (raw text string)
- `human_score` (optional, from gold_csv)
- `qaqc_flags` ("OK" or pipe-separated: EMPTY_TEXT | TEXT_TOO_SHORT | TEXT_VERY_LONG | MISSING_ID)

### Step 2: Dry Run (Test Without GPU)

```bash
python run_scoring.py \
  --input_csv data/batch_input.csv \
  --output_csv outputs/test_dryrun.csv \
  --model llama \
  --condition ZS \
  --dry_run
```

Generates mock scores without LLM calls. Validates output structure (~35 columns).

### Step 3: Real Scoring Run

Example: Llama 3.3-70B, zero-shot condition, GPU 1

```bash
CUDA_VISIBLE_DEVICES=1 python run_scoring.py \
  --input_csv data/batch_input.csv \
  --output_csv outputs/scored_llama_ZS.csv \
  --model llama \
  --model_name meta-llama/Llama-3.3-70B-Instruct \
  --condition ZS \
  --gpu_id 1 \
  --temperature 0.0 \
  --max_tokens 512
```

**Key CLI arguments:**
- `--model`: `gptoss` | `llama` | `gemma`
- `--condition`: `ZS` (zero-shot) | `FS` (few-shot with examples) | `CoT` (chain-of-thought reasoning)
- `--max_tokens`: Use 512 for ZS/FS; use 1500+ for CoT (reasoning chains need space)
- `--temperature`: Always 0.0 (stochastic scoring breaks ICC reproducibility)
- `--skip_flagged`: Skip rows where qaqc_flags ≠ "OK"
- `--batch_size`: Default 10; reduce if OOM errors
- `--dry_run`: Run without LLM calls

Resume-safe: re-running skips rows already scored (non-null `p2_severity_final`).

### Step 4: Run All Nine Conditions (3 models × 3 conditions)

```bash
for model in llama gemma gptoss; do
  for condition in ZS FS CoT; do
    max_tokens=512
    [ "$condition" = "CoT" ] && max_tokens=1500
    CUDA_VISIBLE_DEVICES=0 python run_scoring.py \
      --input_csv data/batch_input.csv \
      --output_csv outputs/scored_${model}_${condition}.csv \
      --model $model \
      --model_name <your_model_string> \
      --condition $condition \
      --gpu_id 0 \
      --max_tokens $max_tokens
  done
done
```

### Step 5: Evaluate Against Human Raters

```bash
python evaluate.py \
  --scored_dir outputs/ \
  --output_csv outputs/metrics_report.csv
```

Computes per model and per condition:
- ICC(2,1) intraclass correlation
- Exact match % (predicted == human)
- Adjacent agreement % (|predicted - human| ≤ 1)
- Mean bias (mean LLM score - mean human score)
- **Sensitivity/Specificity at 2→3 boundary** (CHR-P threshold) — most clinically important
- BERTScore F1 on CoT reasoning chains

Output: `metrics_report.csv` + printed summary table.

## Output Column Reference

**Screening (Step 1):**
- `suspicious_content_present` (bool)
- `screening_evidence` (str)

**Description (Step 2):**
- `description_score` (0-6)
- `supporting_evidence`, `disconfirming_evidence`, `description_reasoning` (str)

**Tenacity (Step 3):**
- `tenacity_score` (0-6)
- `doubt_expressed`, `doubt_source`, `tenacity_reasoning` (str)

**Distress (Step 5, skipped if tiebreaker not needed):**
- `distress_score` (0-6)
- `distress_evidence`, `distress_cause_confirmed` (str)

**Interference (Step 6, skipped if tiebreaker not needed):**
- `interference_score` (0-6)
- `behavioral_change`, `social_impact` (str)

**Final Synthesis (Step 4b):**
- `p2_severity_final` (0-6) — **primary output score**
- `synthesis_rule_applied` (str: "same", "even_avg", "adjacent_higher", etc.)
- `secondary_used` (bool: whether distress/interference was consulted)

**Frequency (Step 7):**
- `frequency_pm_score` (0-6) — past month
- `frequency_lt_py_score` (0-6) — lifetime/past year
- `frequency_evidence` (str)

**Diagnostics (Step 8):**
- `lifetime_psychosis`, `sips_bips`, `sips_apss`, `caarms_blips` (bool)
- `caarms_subthreshold_frequency`, `caarms_subthreshold_intensity` (bool)

**Metadata:**
- `transcript_id`, `source_file`, `human_score`
- `model` (llama | gemma | gptoss)
- `condition` (ZS | FS | CoT)
- `prompt_tokens_total`, `completion_tokens_total` (int)
- `api_error` (str or null)
- `scored_at` (ISO timestamp)

## Data Privacy

✅ **All transcripts remain on-cluster.** No data is sent to external APIs.  
✅ **Models run locally via vLLM.**  
✅ **No internet connectivity required after model download.**  

The `data/` folder is git-ignored; transcripts are never committed to version control.

## Clinical Notes

- The **2→3 boundary** marks the CHR-P threshold. Use `metrics_report.csv` sensitivity/specificity at this boundary to assess clinical utility.
- **Temperature is fixed at 0.0** to ensure reproducible ICC measurements across runs.
- The LLM **never produces the final score**. Python always applies the PSYCHS decision tree (Figure 1 / Table 3) to determine `p2_severity_final`.
- Distress and Interference are **secondary tiebreakers** only — they are consulted by Python when Description and Tenacity scores differ by exactly 1 or when the average would be non-integer.

## References

- PSYCHS manual: https://www.psychiatry.org/File%20Library/Psychiatrists/Practice/DSM/APA_DSM-5-TR_Structured-Interview-for-Prodromal-Syndromes.pdf
- AMP-SCZ/ProNET: https://www.ampscz.org/
- ANNA-PR project: Internal documentation (Language Biomarker Lab, Emory University)

## Contact

Author: Annie (Yiou) He  
Lab: Language Biomarker Lab, Emory University  
Repo: https://github.com/yiouyoyo/ANNA-PR-pipeline-AMPSCZ
