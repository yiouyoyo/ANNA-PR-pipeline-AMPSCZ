# GitHub Migration Guide: Local vs Remote

## Summary
Your **local files** (ANNAPR 3.0) implement the **complete Claude specification** with:
- ✅ 8-step chained scoring (steps 1-8)
- ✅ Python synthesis logic (PSYCHS Table 3)
- ✅ Three prompting conditions (ZS, FS, CoT)
- ✅ Comprehensive error handling
- ✅ Unit tests (synthesize, diagnostics, chain)
- ✅ Resume-safe CSV operations
- ✅ ICC(2,1) evaluation metrics

The **GitHub repo** (last updated 2 days ago) has:
- ⚠️ Older folder structure (1_research, 2_code, 3_outputs)
- ⚠️ Different directory names (synthesis → scoring, etc.)
- ⚠️ Incomplete implementation
- ⚠️ SLURM scripts for multi-GPU inference (GPU A/B split)

---

## Files to Add/Replace on GitHub

### ✅ NEW CORE FILES (Add these)
```
prompts/
  ├── __init__.py
  ├── general_rules.py
  ├── step1_screen.py
  ├── step2_description.py
  ├── step3_tenacity.py
  ├── step5_distress.py
  ├── step6_interference.py
  └── step7_frequency.py

scoring/
  ├── __init__.py
  ├── chain.py                    ← 8-step orchestration (MAIN FILE)
  ├── synthesize.py               ← PSYCHS Table 3 logic
  └── diagnostics.py              ← Diagnostic flags

models/
  ├── __init__.py
  ├── base.py
  ├── gptoss.py
  └── vllm_standard.py

tests/
  ├── test_synthesize.py
  ├── test_diagnostics.py
  └── test_chain.py

README.md                          (REPLACE with new version)
INSTRUCTIONS.md                    (NEW)
.gitignore                         (NEW)
```

### ⚠️ SCRIPTS TO ADD/REPLACE
```
build_batch.py                     (Much more complete)
run_scoring.py                     (New with all CLI flags)
evaluate.py                        (New with ICC + metrics)
```

### 📝 DOCUMENTATION
```
CLAUDE.md                          (Reference spec, already there)
README.md                          (NEW - comprehensive guide)
INSTRUCTIONS.md                    (NEW - cluster run guide)
```

---

## Directory Structure Differences

### GitHub (Current)
```
ANNA-PR-pipeline-AMPSCZ/
├── 1_research/          ← Literature, cost analysis
├── 2_code/
│   ├── inference/       ← SLURM scripts (GPU A/B split)
│   └── analysis/        ← Comparison scripts
├── 3_outputs/           ← Results folder
├── data/
├── outputs/
├── prompts/
├── synthesis/           ← OLD NAME (should be "scoring")
├── tests/
├── CLAUDE.md
└── README.md
```

### Local (New - Recommended)
```
ANNA-PR-pipeline-AMPSCZ/
├── README.md            ← NEW, comprehensive
├── INSTRUCTIONS.md      ← NEW, for Annie
├── CLAUDE.md            ← Spec reference
├── .gitignore           ← NEW
├── build_batch.py       ← Batch preparation
├── run_scoring.py       ← 8-step chain runner
├── evaluate.py          ← ICC + metrics evaluation
├── prompts/             ← All 7 prompt files
├── scoring/             ← NEW NAME (synthesis → scoring)
├── models/              ← Backend abstraction
├── data/                ← Transcripts (gitignored)
├── outputs/             ← Results (gitignored)
└── tests/               ← Unit tests
```

---

## Key Logic Differences

### GitHub Version (Old)
- Multi-GPU strategy: **GPU A/B split** (question-split, not tensor parallel)
- Runs separate inference processes on each GPU
- Different SLURM scripts for A and B

### Local Version (New)
- **Single GPU or sequential** execution (simpler, more maintainable)
- Can run on single GPU with all dimensions
- More flexible: support for gptoss, llama, gemma
- **Chained prompting**: each step depends on prior output

---

## Push-to-GitHub Strategy

### Option 1: Clean Overwrite (Recommended for Fresh Start)
```bash
cd /Users/yhe333/Desktop/ANNAPR\ 3.0

# Initialize git
git init

# Add all files
git add .

# Commit
git commit -m "Update: Complete 8-step chained PSYCHS P2 scoring pipeline

- Implement full 8-step chained scoring (steps 1-8)
- Add PSYCHS Table 3 synthesis logic
- Support ZS, FS, CoT prompting conditions
- Add ICC(2,1) evaluation metrics
- Comprehensive unit tests (synthesize, diagnostics, chain)
- Resume-safe CSV operations
- New: prompts, scoring, models modules
- Updated: README.md, INSTRUCTIONS.md
- New: evaluate.py with ICC metrics"

# Connect to GitHub
git remote add origin https://github.com/yiouyoyo/ANNA-PR-pipeline-AMPSCZ.git

# Force push (WARNING: overwrites GitHub)
git branch -M main
git push -u origin main --force
```

### Option 2: Merge with Existing (Preserve GitHub History)
```bash
# Clone existing repo
git clone https://github.com/yiouyoyo/ANNA-PR-pipeline-AMPSCZ.git
cd ANNA-PR-pipeline-AMPSCZ

# Copy new files from local (preserve 1_research/)
cp -r /Users/yhe333/Desktop/ANNAPR\ 3.0/prompts .
cp -r /Users/yhe333/Desktop/ANNAPR\ 3.0/scoring .
cp -r /Users/yhe333/Desktop/ANNAPR\ 3.0/models .
cp -r /Users/yhe333/Desktop/ANNAPR\ 3.0/tests .
cp /Users/yhe333/Desktop/ANNAPR\ 3.0/build_batch.py .
cp /Users/yhe333/Desktop/ANNAPR\ 3.0/run_scoring.py .
cp /Users/yhe333/Desktop/ANNAPR\ 3.0/evaluate.py .
cp /Users/yhe333/Desktop/ANNAPR\ 3.0/README.md .
cp /Users/yhe333/Desktop/ANNAPR\ 3.0/INSTRUCTIONS.md .
cp /Users/yhe333/Desktop/ANNAPR\ 3.0/.gitignore .

# Commit
git add .
git commit -m "Add complete 8-step chained PSYCHS P2 scoring implementation"

# Push
git push origin main
```

---

## Post-GitHub Setup for Cluster

### Step 1: Clone on Cluster
```bash
module load git python/3.10 cuda/12.0  # or your cluster's module commands
git clone https://github.com/yiouyoyo/ANNA-PR-pipeline-AMPSCZ.git
cd ANNA-PR-pipeline-AMPSCZ
```

### Step 2: Create Cluster Virtual Environment
```bash
python3.10 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install vllm pandas scipy bert-score

# If using GPT-OSS
pip install openai_harmony
```

### Step 3: Follow INSTRUCTIONS.md
```bash
python build_batch.py --input_dir /path/to/transcripts --output_csv data/batch_input.csv
python run_scoring.py --input_csv data/batch_input.csv --output_csv outputs/scored_llama_ZS.csv --model llama --model_name meta-llama/Llama-3.3-70B-Instruct --condition ZS --gpu_id 0 --max_tokens 512
python evaluate.py --scored_dir outputs/ --output_csv outputs/metrics_report.csv
```

---

## What to Keep from GitHub

- `1_research/` folder (literature, cost analysis) — **DO NOT DELETE**
- Any existing `2_code/inference/slurm_*.sh` scripts (if you want multi-GPU inference)
- Existing `.git` history

---

## Checklist for Push to GitHub

- [ ] Local files in `/Users/yhe333/Desktop/ANNAPR 3.0/` are finalized
- [ ] `.gitignore` created and in place
- [ ] All `*.py` files have proper imports and no syntax errors
- [ ] README.md and INSTRUCTIONS.md are complete
- [ ] Tests pass locally: `python -m pytest tests/ -v`
- [ ] Ready to push to GitHub using Option 1 or 2 above

---

## Questions to Clarify

1. **Preserve GitHub history?** If yes, use Option 2. If no, use Option 1.
2. **Keep `1_research/` folder?** Recommend YES (preserves context).
3. **Keep old `2_code/` and `3_outputs/` structure?** Recommend NO (simplify).
