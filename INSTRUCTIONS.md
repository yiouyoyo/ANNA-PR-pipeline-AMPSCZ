# ANNA-PR Pipeline — Cluster Run Instructions for Annie

## Before You Start

Run these checks to confirm your environment is ready:

- [ ] Transcripts already QA/QC'd and P2-extracted via your existing scripts
- [ ] GPU availability: `nvidia-smi` — note which GPU is free
- [ ] vLLM installed: `python -c "import vllm; print(vllm.__version__)"`
- [ ] For GPT-OSS only: `python -c "from openai_harmony import load_harmony_encoding"`
- [ ] Model cache: Know your full HuggingFace model ID strings (check `config.json` in model cache directory)
- [ ] Sufficient VRAM:
  - Llama 3.3-70B: ~40 GB
  - Gemma 3-27B: ~15 GB
  - GPT-OSS: Depends on model size

---

## Step 1: Build Batch CSV

Read all `.txt` and `.json` transcripts from your input folder and create a single CSV for scoring.

```bash
python build_batch.py \
  --input_dir /path/to/p2_extracted_transcripts \
  --output_csv data/batch_input.csv \
  --gold_csv /path/to/human_scores.csv
```

**What it does:**
- Reads all transcript files in `input_dir`
- Extracts transcript text and interview ID
- Computes QA/QC flags (EMPTY_TEXT, TEXT_TOO_SHORT, TEXT_VERY_LONG, MISSING_ID)
- Computes content hash (MD5 8 chars) for resume safety
- Merges in human scores if `--gold_csv` provided
- Writes `data/batch_input.csv` with one transcript per row

**Check the output:**
```bash
head -5 data/batch_input.csv
wc -l data/batch_input.csv
grep "^OK$" data/batch_input.csv | wc -l  # count OK rows
```

Resume-safe: re-running skips files already processed by content hash.

---

## Step 2: Dry Run (No GPU Required)

Test the scoring pipeline without LLM calls. Generates mock scores to validate output structure.

```bash
python run_scoring.py \
  --input_csv data/batch_input.csv \
  --output_csv outputs/test_dryrun.csv \
  --model llama \
  --condition ZS \
  --dry_run
```

**Check the output:**
```bash
head -5 outputs/test_dryrun.csv
python -c "import pandas as pd; df = pd.read_csv('outputs/test_dryrun.csv'); print(f'Columns: {len(df.columns)}, Rows: {len(df)}')"
```

Should have ~35 columns and as many rows as your batch CSV.

---

## Step 3: Real Scoring Run — Example (Llama 3.3, Zero-Shot)

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

**Key parameters:**
- `--model`: `llama` | `gemma` | `gptoss`
- `--model_name`: Full HuggingFace model ID (check your cache)
- `--condition`: `ZS` (zero-shot) | `FS` (few-shot) | `CoT` (chain-of-thought)
- `--gpu_id`: Must match `CUDA_VISIBLE_DEVICES`
- `--max_tokens`:
  - ZS/FS: 512
  - CoT: 1500+ (reasoning chains need space)
- `--temperature`: Always 0.0 (deterministic scoring is critical for ICC)
- `--gpu_memory_utilization`: Default 0.85; reduce to 0.7 if OOM
- `--batch_size`: Default 10; reduce to 5 if OOM
- `--skip_flagged`: Skip rows where qaqc_flags ≠ "OK" (optional)

**Resume-safe:** Re-running the same command skips already-scored rows (checks for non-null `p2_severity_final`).

**Progress monitoring:**
```bash
tail -20 outputs/scored_llama_ZS.csv  # check latest rows
python -c "import pandas as pd; df = pd.read_csv('outputs/scored_llama_ZS.csv'); print(f'Scored: {df[\"p2_severity_final\"].notna().sum()} rows')"
```

---

## Step 4: Run All Nine Conditions (3 models × 3 conditions)

Name output files as: `scored_{model}_{condition}.csv`

```bash
# Model 1: Llama 3.3-70B
CUDA_VISIBLE_DEVICES=0 python run_scoring.py \
  --input_csv data/batch_input.csv \
  --output_csv outputs/scored_llama_ZS.csv \
  --model llama \
  --model_name meta-llama/Llama-3.3-70B-Instruct \
  --condition ZS \
  --gpu_id 0 \
  --max_tokens 512

CUDA_VISIBLE_DEVICES=0 python run_scoring.py \
  --input_csv data/batch_input.csv \
  --output_csv outputs/scored_llama_FS.csv \
  --model llama \
  --model_name meta-llama/Llama-3.3-70B-Instruct \
  --condition FS \
  --gpu_id 0 \
  --max_tokens 512

CUDA_VISIBLE_DEVICES=0 python run_scoring.py \
  --input_csv data/batch_input.csv \
  --output_csv outputs/scored_llama_CoT.csv \
  --model llama \
  --model_name meta-llama/Llama-3.3-70B-Instruct \
  --condition CoT \
  --gpu_id 0 \
  --max_tokens 1500

# Model 2: Gemma 3-27B (similar pattern)
CUDA_VISIBLE_DEVICES=0 python run_scoring.py \
  --input_csv data/batch_input.csv \
  --output_csv outputs/scored_gemma_ZS.csv \
  --model gemma \
  --model_name google/gemma-3-27b-it \
  --condition ZS \
  --gpu_id 0 \
  --max_tokens 512

# ... (repeat for gemma_FS, gemma_CoT)

# Model 3: GPT-OSS (if available)
CUDA_VISIBLE_DEVICES=1 python run_scoring.py \
  --input_csv data/batch_input.csv \
  --output_csv outputs/scored_gptoss_ZS.csv \
  --model gptoss \
  --model_name YOUR_GPTOSS_MODEL_STRING_HERE \
  --condition ZS \
  --gpu_id 1 \
  --max_tokens 512

# ... (repeat for gptoss_FS, gptoss_CoT)
```

Each run takes 1–3 hours depending on your corpus size and GPU. All runs are independent and can be parallelized on different GPUs.

---

## Step 5: Evaluate All Runs

After all nine conditions are complete, compute metrics:

```bash
python evaluate.py \
  --scored_dir outputs/ \
  --output_csv outputs/metrics_report.csv
```

**Output:**
- `outputs/metrics_report.csv` with per-model, per-condition metrics
- Printed table with:
  - ICC(2,1) intraclass correlation
  - Exact match %
  - Adjacent agreement %
  - Mean bias (LLM - human)
  - **Sensitivity/Specificity at 2→3 boundary** (CHR-P clinical threshold)
  - BERTScore F1 (CoT only)

---

## Troubleshooting

### Run Dies Mid-Way

**Solution:** Re-run the exact same command. The script resumes automatically by skipping rows already scored.

```bash
# If run was interrupted, just re-run:
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

### Out-of-Memory (OOM) Error

**Solutions (in order of preference):**
1. Reduce `--batch_size` to 5 or 3
2. Reduce `--gpu_memory_utilization` to 0.7 or 0.6
3. Use a different GPU (lower VRAM usage model)
4. Split input CSV into smaller chunks and run separately

### vLLM Complains About Model Not Found

**Solution:** Confirm model is in your HuggingFace cache:
```bash
ls ~/.cache/huggingface/hub/ | grep llama
# Should see: models--meta-llama--Llama-3.3-70B-Instruct or similar
```

If missing, download first:
```bash
python -c "from huggingface_hub import snapshot_download; snapshot_download('meta-llama/Llama-3.3-70B-Instruct')"
```

### GPT-OSS Harmony Encoding Error

**Solution:** Ensure `openai_harmony` is installed and available:
```bash
python -c "from openai_harmony import load_harmony_encoding; print('OK')"
```

If missing, contact lab IT for installation.

---

## Token Reminders

✅ **ZS/FS:** `--max_tokens 512`  
✅ **CoT:** `--max_tokens 1500` (minimum — reasoning chains need space)  

**Why:** With CoT, the model first writes reasoning before the JSON. If max_tokens is too low, the chain gets truncated and the JSON never appears, breaking parsing.

---

## Expected Runtime

- **build_batch.py:** < 1 minute
- **test_dryrun.csv:** < 1 minute (no GPU)
- **One real run** (e.g., 100 transcripts):
  - Llama 3.3-70B: ~90–120 minutes
  - Gemma 3-27B: ~60–90 minutes
  - GPT-OSS: Varies by model size
- **evaluate.py:** < 5 minutes
- **Total for all 9 conditions:** ~20–30 hours on a single GPU

---

## Final Checklist

- [ ] data/batch_input.csv created and validated
- [ ] outputs/test_dryrun.csv passed structure check
- [ ] All 9 real runs completed (scored_*.csv files in outputs/)
- [ ] outputs/metrics_report.csv generated
- [ ] ICC(2,1) ≥ 0.75 for at least one model/condition pair
- [ ] Sensitivity/Specificity at 2→3 boundary reviewed for clinical relevance

---

## Next Steps (For Annie)

Once metrics_report.csv is ready:
1. Email results to Language Biomarker Lab team
2. If ICC < 0.70, investigate top sources of disagreement
3. Consider fine-tuning on anchor examples if needed
4. Prepare write-up on model performance vs clinician raters
