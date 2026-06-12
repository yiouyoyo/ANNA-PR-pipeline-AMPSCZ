# ACTION CHECKLIST: Deploy Local → GitHub → Cluster

## Phase 1: Verify Local Setup ✅

### Check All Files Exist
```bash
cd /Users/yhe333/Desktop/ANNAPR\ 3.0

# Verify root files
ls -la *.py *.md .gitignore
# Should see: build_batch.py, run_scoring.py, evaluate.py, README.md, INSTRUCTIONS.md, CLAUDE.md, .gitignore

# Verify directories
ls -la prompts/ scoring/ models/ tests/ data/ outputs/
# Each should have files + __init__.py

# Count files
find . -name "*.py" -type f | wc -l
# Should be ~25+ Python files
```

### Run Tests Locally
```bash
# Make sure you're in the repo
cd /Users/yhe333/Desktop/ANNAPR\ 3.0

# Option A: With pytest
pip install pytest
python -m pytest tests/ -v

# Option B: Without pytest, run each test
python tests/test_synthesize.py
python tests/test_diagnostics.py
python tests/test_chain.py

# Expected: All tests pass ✓
```

### Quick Syntax Check
```bash
# Check for Python syntax errors
python -m py_compile build_batch.py run_scoring.py evaluate.py
python -m py_compile prompts/*.py scoring/*.py models/*.py tests/*.py

# Expected: No output (all files compile)
```

### Checklist
- [ ] All 25+ Python files present
- [ ] All tests pass
- [ ] No syntax errors
- [ ] README.md is readable and complete
- [ ] INSTRUCTIONS.md has step-by-step commands
- [ ] .gitignore is in place

---

## Phase 2: Push to GitHub 🚀

### Choose Your Strategy

**Strategy A: Force Update (Start Fresh, Recommended)**
```bash
cd /Users/yhe333/Desktop/ANNAPR\ 3.0

# 1. Initialize git (if not already done)
git init

# 2. Add all files
git add .

# 3. Create commit
git commit -m "Complete ANNA-PR PSYCHS P2 scoring pipeline

Implements full 8-step chained LLM scoring system with:
- Screening → Description → Tenacity → Python Synthesis
- Conditional Distress/Interference (tiebreaker logic)
- Final Synthesis (PSYCHS Table 3)
- Frequency Rating
- Diagnostic Groupings

New features:
✓ Resume-safe CSV operations
✓ Three prompting conditions (ZS, FS, CoT)
✓ Comprehensive unit tests
✓ ICC(2,1) evaluation metrics
✓ PSYCHS Table 3 logic
✓ Model backend abstraction

New modules:
- prompts/ (7 comprehensive prompt files)
- scoring/ (chain.py, synthesize.py, diagnostics.py)
- models/ (base, gptoss, vllm_standard backends)
- evaluate.py (ICC + metrics evaluation)"

# 4. Configure GitHub
git remote add origin https://github.com/yiouyoyo/ANNA-PR-pipeline-AMPSCZ.git

# 5. Push to GitHub (force overwrites)
git branch -M main
git push -u origin main --force

# Expected: Files appear on GitHub
```

**Strategy B: Merge with Existing (Keep GitHub History)**
```bash
# 1. Clone existing repo
git clone https://github.com/yiouyoyo/ANNA-PR-pipeline-AMPSCZ.git /tmp/github_repo
cd /tmp/github_repo

# 2. Copy new files (keeps 1_research/)
rsync -av /Users/yhe333/Desktop/ANNAPR\ 3.0/ . \
  --exclude='1_research' --exclude='.git' --exclude='*.tar.gz' \
  --exclude='GITHUB_MIGRATION_GUIDE.md' --exclude='QUICK_START_GITHUB_CLUSTER.md' \
  --exclude='COMPARISON_GITHUB_vs_LOCAL.md'

# 3. Add and commit
git add .
git commit -m "Add complete 8-step chained PSYCHS P2 scoring pipeline (see Phase 2 commit message above)"

# 4. Push
git push origin main

# Expected: Files appear on GitHub, 1_research/ preserved
```

### Verify on GitHub
```bash
# Open in browser:
open https://github.com/yiouyoyo/ANNA-PR-pipeline-AMPSCZ

# Check that these folders exist:
✓ prompts/
✓ scoring/
✓ models/
✓ tests/
✓ data/ (empty, with .gitkeep)
✓ outputs/ (empty, with .gitkeep)
✓ 1_research/ (if using Strategy B)

# Check that these files exist:
✓ README.md
✓ INSTRUCTIONS.md
✓ CLAUDE.md
✓ .gitignore
✓ build_batch.py
✓ run_scoring.py
✓ evaluate.py
```

### Checklist
- [ ] Chose Strategy A or B
- [ ] Executed git commands successfully
- [ ] Verified files appear on GitHub
- [ ] GitHub shows all prompts/, scoring/, models/, tests/ folders
- [ ] README.md is rendered correctly on GitHub

---

## Phase 3: Setup on Cluster 🖥️

### Connect to Cluster
```bash
# SSH to cluster
ssh annie@your_cluster.emory.edu

# Optional: Request interactive GPU node
salloc --gpus=1 --mem=50G --cpus-per-task=4 -t 00:30:00
```

### Clone Repository
```bash
# Clone from GitHub
git clone https://github.com/yiouyoyo/ANNA-PR-pipeline-AMPSCZ.git
cd ANNA-PR-pipeline-AMPSCZ

# Verify files
ls -la *.py
ls -la prompts/ scoring/ models/ tests/
```

### Load Modules (Cluster-Specific)
```bash
# Example for Emory cluster (adjust for your cluster)
module load python/3.10 cuda/12.0

# Verify
python --version
nvidia-smi
```

### Create Python Environment
```bash
# Create virtual environment
python3.10 -m venv venv

# Activate
source venv/bin/activate

# Verify activated (should show (venv) prefix)
which python

# Upgrade pip
pip install --upgrade pip setuptools wheel
```

### Install Dependencies
```bash
# Core dependencies
pip install vllm pandas scipy numpy

# Evaluation metrics
pip install bert-score

# For GPT-OSS only (if available)
pip install openai_harmony

# Verify installations
python -c "import vllm; print(vllm.__version__)"
python -c "import pandas; print('pandas OK')"
python -c "import scipy; print('scipy OK')"
```

### Prepare Transcripts
```bash
# Copy your QA/QC'd, P2-extracted transcripts
mkdir -p data/transcripts
# Copy your .txt or .json files here
# e.g.: scp -r annie@local_machine:/path/to/p2_transcripts/* data/transcripts/

# Verify
ls data/transcripts/ | head -10
```

### Checklist
- [ ] Successfully SSH'd to cluster
- [ ] GitHub repo cloned
- [ ] Python 3.10 + CUDA 12.0 modules loaded
- [ ] Virtual environment created and activated
- [ ] All dependencies installed
- [ ] Transcripts copied to data/transcripts/

---

## Phase 4: Run Pipeline 🏃

### Step 1: Build Batch
```bash
cd ~/ANNA-PR-pipeline-AMPSCZ
source venv/bin/activate

# Build batch input CSV
python build_batch.py \
  --input_dir data/transcripts \
  --output_csv data/batch_input.csv \
  --gold_csv /path/to/human_scores.csv  # if you have gold scores

# Verify output
head -5 data/batch_input.csv
wc -l data/batch_input.csv
```

### Step 2: Dry Run (Test without GPU)
```bash
python run_scoring.py \
  --input_csv data/batch_input.csv \
  --output_csv outputs/test_dryrun.csv \
  --model llama \
  --condition ZS \
  --dry_run

# Verify output
head -5 outputs/test_dryrun.csv
wc -l outputs/test_dryrun.csv
```

### Step 3: Real Scoring (Choose Model/Condition)

**Llama 3.3-70B, Zero-Shot (ZS)**
```bash
python run_scoring.py \
  --input_csv data/batch_input.csv \
  --output_csv outputs/scored_llama_ZS.csv \
  --model llama \
  --model_name meta-llama/Llama-3.3-70B-Instruct \
  --condition ZS \
  --gpu_id 0 \
  --temperature 0.0 \
  --max_tokens 512

# Monitor progress
tail -f outputs/scored_llama_ZS.csv
```

**Llama 3.3-70B, Few-Shot (FS)**
```bash
python run_scoring.py \
  --input_csv data/batch_input.csv \
  --output_csv outputs/scored_llama_FS.csv \
  --model llama \
  --model_name meta-llama/Llama-3.3-70B-Instruct \
  --condition FS \
  --gpu_id 0 \
  --max_tokens 512
```

**Llama 3.3-70B, Chain-of-Thought (CoT)**
```bash
python run_scoring.py \
  --input_csv data/batch_input.csv \
  --output_csv outputs/scored_llama_CoT.csv \
  --model llama \
  --model_name meta-llama/Llama-3.3-70B-Instruct \
  --condition CoT \
  --gpu_id 0 \
  --max_tokens 1500  # IMPORTANT: 1500 for CoT
```

### Step 4: Run All 9 Conditions (If Running Multiple Models)
```bash
# Create batch script or loop
for model in llama gemma; do
  for condition in ZS FS CoT; do
    max_tokens=512
    [ "$condition" = "CoT" ] && max_tokens=1500
    
    python run_scoring.py \
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

### Step 5: Evaluate Results
```bash
python evaluate.py \
  --scored_dir outputs/ \
  --output_csv outputs/metrics_report.csv

# View results
cat outputs/metrics_report.csv
```

### Checklist
- [ ] build_batch.py ran successfully
- [ ] test_dryrun.csv created with ~35 columns
- [ ] First real scoring run completed
- [ ] outputs/scored_*.csv files created
- [ ] evaluate.py ran and produced metrics_report.csv
- [ ] ICC(2,1), sensitivity, specificity computed

---

## Phase 5: Review Results 📊

### Check Output Files
```bash
# List all output CSVs
ls -lh outputs/

# Check one scoring file
head -2 outputs/scored_llama_ZS.csv | cut -d, -f1-10
# Should have columns: row_id, transcript_id, source_file, human_score, model, condition...

# Metrics report
cat outputs/metrics_report.csv
```

### Interpret Metrics
```
Key metrics to check:
- ICC(2,1):           Should be ≥ 0.75 (good agreement)
- Exact match %:      Percentage of scores that match human exactly
- Adjacent %:         Percentage within 1 point of human
- Sensitivity@2→3:    True positive rate at CHR threshold (most important!)
- Specificity@2→3:    True negative rate at CHR threshold (clinically critical)
- Mean bias:          Should be close to 0 (no systematic over/under-scoring)
```

### Troubleshooting Issues

**ICC < 0.70?**
- Check if transcripts are representative
- Try few-shot (FS) or chain-of-thought (CoT)
- Review disagreement cases manually

**Many parsing errors?**
- Check LLM response format
- May need to adjust --max_tokens
- CoT needs higher max_tokens (≥1500)

**OOM errors?**
- Reduce --batch_size to 5
- Reduce --gpu_memory_utilization to 0.7
- Use a smaller model

### Checklist
- [ ] All scoring runs completed
- [ ] No data loss or corruption
- [ ] metrics_report.csv generated
- [ ] ICC(2,1) reviewed
- [ ] Sensitivity/Specificity at 2→3 reviewed

---

## Phase 6: Optional - Push Results Back to GitHub

```bash
# Go to repo
cd ~/ANNA-PR-pipeline-AMPSCZ

# Copy results to a results branch (don't commit large CSVs to main)
git checkout -b results/v1

# Add summary (not large CSV files)
git add RESULTS_SUMMARY.md  # Create a summary of findings

# Commit
git commit -m "Add initial scoring results summary"

# Push
git push -u origin results/v1

# View on GitHub: https://github.com/yiouyoyo/ANNA-PR-pipeline-AMPSCZ/tree/results/v1
```

### Checklist
- [ ] Optional: Push results summary to separate branch
- [ ] Keep large CSV files out of git (use .gitignore)

---

## Final Checklist ✨

### Local Setup
- [ ] All Python files syntax-checked
- [ ] All tests pass
- [ ] Documentation complete

### GitHub
- [ ] Files pushed successfully
- [ ] All folders appear on GitHub
- [ ] README renders correctly

### Cluster
- [ ] Environment loaded and configured
- [ ] Virtual environment created
- [ ] Dependencies installed
- [ ] Transcripts copied

### Pipeline Execution
- [ ] build_batch.py completed
- [ ] Dry run passed
- [ ] Real scoring runs completed
- [ ] Evaluation metrics computed
- [ ] Results reviewed

---

## Quick Commands Reference

```bash
# Local
cd /Users/yhe333/Desktop/ANNAPR\ 3.0
python -m pytest tests/ -v
git add . && git commit -m "message" && git push origin main

# Cluster Setup
git clone https://github.com/yiouyoyo/ANNA-PR-pipeline-AMPSCZ.git
source venv/bin/activate

# Cluster Run
python build_batch.py --input_dir data/transcripts --output_csv data/batch_input.csv
python run_scoring.py --input_csv data/batch_input.csv --output_csv outputs/scored_llama_ZS.csv --model llama --model_name meta-llama/Llama-3.3-70B-Instruct --condition ZS --gpu_id 0 --max_tokens 512
python evaluate.py --scored_dir outputs/ --output_csv outputs/metrics_report.csv
```

---

## 🎉 Success Criteria

You've completed the deployment when:
1. ✅ All files are on GitHub
2. ✅ Cluster repository is cloned and ready
3. ✅ At least one scoring run completed
4. ✅ ICC(2,1) ≥ 0.70
5. ✅ Sensitivity/Specificity at 2→3 threshold reviewed

**Estimated Timeline:**
- Phase 1-2: 30 minutes
- Phase 3: 20 minutes
- Phase 4 (one condition): 2-4 hours (depends on corpus size)
- Phase 5: 30 minutes
- **Total: 4-6 hours for one model/condition pair**

---

## Questions?

Refer to:
- `README.md` — Project overview
- `INSTRUCTIONS.md` — Detailed cluster guide
- `QUICK_START_GITHUB_CLUSTER.md` — Quick reference
- `COMPARISON_GITHUB_vs_LOCAL.md` — Detailed differences
- `GITHUB_MIGRATION_GUIDE.md` — Migration details
