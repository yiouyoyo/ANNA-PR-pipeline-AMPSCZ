# Quick Start: Local → GitHub → Cluster

## 1️⃣ MOVE TO CLUSTER (Choose One)

### Option A: Via Git (Recommended)
```bash
cd /Users/yhe333/Desktop/ANNAPR\ 3.0
git init
git add .
git commit -m "Complete ANNA-PR pipeline implementation"
git remote add origin https://github.com/yiouyoyo/ANNA-PR-pipeline-AMPSCZ.git
git branch -M main
git push -u origin main

# Then on cluster:
git clone https://github.com/yiouyoyo/ANNA-PR-pipeline-AMPSCZ.git
cd ANNA-PR-pipeline-AMPSCZ
```

### Option B: Direct Rsync
```bash
rsync -avz --exclude='data/*' --exclude='outputs/*' \
  /Users/yhe333/Desktop/ANNAPR\ 3.0/ \
  annie@cluster.emory.edu:/home/annie/ANNA-PR/
```

### Option C: Tar + SCP
```bash
cd /Users/yhe333/Desktop/ANNAPR\ 3.0
tar --exclude='data' --exclude='outputs' --exclude='.git' -czf annapr.tar.gz .
scp annapr.tar.gz annie@cluster.emory.edu:/home/annie/
ssh annie@cluster.emory.edu "tar -xzf annapr.tar.gz -C /home/annie/ANNA-PR"
```

---

## 2️⃣ COMPARE WITH GITHUB

The GitHub repo has **older structure** from 2 months ago. Here's what's **NEW** vs what's on GitHub:

### 🆕 NEW FILES (Add to GitHub)
```
prompts/           ← 7 prompt files (step1-7)
scoring/           ← chain.py, synthesize.py, diagnostics.py
models/            ← base.py, gptoss.py, vllm_standard.py
tests/             ← test_synthesize.py, test_diagnostics.py, test_chain.py
README.md          ← NEW (comprehensive guide)
INSTRUCTIONS.md    ← NEW (cluster run guide)
.gitignore         ← NEW
evaluate.py        ← NEW (ICC metrics)
```

### ⚡ UPDATED FILES
```
build_batch.py     ← More complete version
run_scoring.py     ← More complete version
CLAUDE.md          ← Already there
```

### ⚠️ ON GITHUB BUT DIFFERENT STRUCTURE
```
GitHub has:        → Replace with:
synthesis/         → scoring/
2_code/inference/  → Can keep or remove
3_outputs/         → Keep as outputs/
```

---

## 3️⃣ PUSH TO GITHUB

### Method 1: Force Update (Start Fresh)
```bash
cd /Users/yhe333/Desktop/ANNAPR\ 3.0

# Check status
git status

# If not a git repo yet:
git init

# Add everything
git add .

# Commit with detailed message
git commit -m "Complete ANNA-PR PSYCHS P2 scoring pipeline

This implements the full 8-step chained LLM scoring system:

Core Features:
- Step 1: Screening (LLM, is P2 content present?)
- Step 2: Description (LLM, 0-6 anchors)
- Step 3: Tenacity (LLM, conditional on D>0)
- Step 4: Python synthesis check
- Step 5-6: Distress & Interference (LLM, conditional on tiebreaker)
- Step 4b: Python final synthesis (PSYCHS Figure 1/Table 3)
- Step 7: Frequency (LLM, depends on severity)
- Step 8: Diagnostics (Python, diagnostic flags)

Improvements:
- Comprehensive error handling
- Resume-safe CSV operations
- Three prompting conditions (ZS, FS, CoT)
- Unit tests for all core logic
- ICC(2,1) evaluation metrics
- Support for Llama 3.3, Gemma, GPT-OSS

Files:
+ prompts/ (7 step files + general_rules)
+ scoring/ (chain, synthesize, diagnostics)
+ models/ (base, gptoss, vllm_standard)
+ tests/ (synthesize, diagnostics, chain)
+ evaluate.py (ICC metrics)
+ INSTRUCTIONS.md (cluster guide)
+ README.md (comprehensive overview)
- Removed old 2_code/3_outputs structure
"

# Connect to GitHub
git remote add origin https://github.com/yiouyoyo/ANNA-PR-pipeline-AMPSCZ.git

# Push with force (overwrites GitHub main)
git branch -M main
git push -u origin main --force
```

### Method 2: Merge with Existing (Keep GitHub History)
```bash
# Clone existing repo
git clone https://github.com/yiouyoyo/ANNA-PR-pipeline-AMPSCZ.git old_repo
cd old_repo

# Copy new files (preserve 1_research/)
rsync -av /Users/yhe333/Desktop/ANNAPR\ 3.0/ . \
  --exclude='1_research' --exclude='.git' --exclude='GITHUB_MIGRATION_GUIDE.md'

# Commit and push
git add .
git commit -m "Add complete 8-step chained PSYCHS P2 scoring pipeline"
git push origin main
```

---

## 4️⃣ VERIFY AFTER PUSH

```bash
# Check GitHub
open https://github.com/yiouyoyo/ANNA-PR-pipeline-AMPSCZ

# Verify folder structure on GitHub:
# ✓ prompts/
# ✓ scoring/
# ✓ models/
# ✓ tests/
# ✓ build_batch.py
# ✓ run_scoring.py
# ✓ evaluate.py
# ✓ README.md
# ✓ INSTRUCTIONS.md
```

---

## 5️⃣ ON CLUSTER: Setup & Run

```bash
# Clone fresh repo
git clone https://github.com/yiouyoyo/ANNA-PR-pipeline-AMPSCZ.git
cd ANNA-PR-pipeline-AMPSCZ

# Create Python environment
module load python/3.10 cuda/12.0
python3.10 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install vllm pandas scipy bert-score

# Test dry run (no GPU needed)
python run_scoring.py \
  --input_csv data/batch_input.csv \
  --output_csv outputs/test_dryrun.csv \
  --model llama \
  --condition ZS \
  --dry_run

# See INSTRUCTIONS.md for full workflow
cat INSTRUCTIONS.md
```

---

## 📊 File Checklist

### Local `/Users/yhe333/Desktop/ANNAPR 3.0/`

- [ ] `.gitignore` present
- [ ] `README.md` complete
- [ ] `INSTRUCTIONS.md` complete
- [ ] `CLAUDE.md` present
- [ ] `build_batch.py` complete
- [ ] `run_scoring.py` complete
- [ ] `evaluate.py` complete
- [ ] `prompts/` with 7 files
- [ ] `scoring/` with 3 files
- [ ] `models/` with 4 files
- [ ] `tests/` with 3 files
- [ ] `data/.gitkeep` present
- [ ] `outputs/.gitkeep` present

### GitHub after push

- [ ] All files above pushed
- [ ] `1_research/` preserved (if using merge method)
- [ ] No `__pycache__` or `*.pyc` files
- [ ] No `data/` contents (should be empty)

---

## 🆘 Troubleshooting

### "fatal: not a git repository"
```bash
cd /Users/yhe333/Desktop/ANNAPR\ 3.0
git init
```

### "Updates were rejected because the tip of your current branch is behind its remote counterpart"
```bash
git push -u origin main --force
```

### Want to verify before pushing?
```bash
git log --oneline -5  # Check commit history
git status            # Check what will be pushed
git diff --cached     # Review changes before push
```

---

## 💡 Tips

1. **Always backup** before `--force` push: `tar -czf backup.tar.gz ANNAPR\ 3.0/`
2. **Test locally first**: Run `python -m pytest tests/` before pushing
3. **Clear old branches**: `git remote prune origin`
4. **On cluster**: Use `git pull` to update if you push changes later
