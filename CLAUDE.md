# ANNA-PR Pipeline — Claude Code Build Prompt
**Repo:** https://github.com/yiouyoyo/ANNA-PR-pipeline-AMPSCZ
**Author:** Annie (Yiou) He, Language Biomarker Lab, Emory University

---

## WHAT YOU ARE BUILDING

An automated clinical interview scoring pipeline that replicates the PSYCHS P2
(Suspiciousness/Persecutory Ideation) clinician decision tree using local LLMs.
Part of the ANNA-PR project, AMP-SCZ/ProNET consortium.

Core innovation: LLM scores each measurement concept separately via chained calls.
Python runs all synthesis and diagnostic logic. The LLM never produces the final
score directly — it only scores each concept, and Python applies the decision tree.

Data privacy: all transcripts stay on-cluster. No data leaves the machine.
All models run locally via vLLM. No external API calls.

---

## REPO STRUCTURE TO CREATE

```
ANNA-PR-pipeline-AMPSCZ/
├── CLAUDE.md                    ← this file
├── README.md                    ← human-readable project summary
├── INSTRUCTIONS.md              ← step-by-step cluster run guide for Annie
├── build_batch.py               ← transcripts → batch_input.csv
├── run_scoring.py               ← 8-step chained LLM scoring
├── evaluate.py                  ← ICC + metrics vs human scores
├── prompts/
│   ├── __init__.py
│   ├── general_rules.py         ← shared preamble inserted into every prompt
│   ├── step1_screen.py          ← is P2 content present?
│   ├── step2_description.py     ← Description anchors 0-6
│   ├── step3_tenacity.py        ← Tenacity anchors 0-6
│   ├── step5_distress.py        ← Distress anchors 0-6 (conditional)
│   ├── step6_interference.py    ← Interference anchors 0-6 (conditional)
│   └── step7_frequency.py       ← CAARMS frequency PM + LT/PY
├── scoring/
│   ├── __init__.py
│   ├── chain.py                 ← score_transcript() walks all 8 steps
│   ├── synthesize.py            ← synthesize_p2_severity() — Python only
│   └── diagnostics.py           ← diagnostic_groupings() — Python only
├── models/
│   ├── __init__.py
│   ├── base.py                  ← abstract LLMBackend class
│   ├── gptoss.py                ← GPT-OSS via Harmony encoding + vLLM
│   └── vllm_standard.py         ← Llama 3.3 + Gemma via standard vLLM
├── data/
│   └── .gitkeep                 ← transcripts never committed to git
├── outputs/
│   └── .gitkeep
└── tests/
    ├── test_synthesize.py        ← unit tests for all synthesis edge cases
    ├── test_diagnostics.py       ← unit tests for diagnostic flags
    └── test_chain.py             ← dry-run integration test
```

---

## PREPROCESSING (already coded by Annie — do not rewrite)

```
Raw transcript (.txt / .json)
        │
        ▼
Step 0a — QA/QC (Annie's existing script)
        │  clean encoding, strip PHI flags, validate format
        ▼
Step 0b — P2 extraction (Annie's existing script)
        │  crop P2 section only from full interview
        ▼
Step 0c — build_batch.py  ← BUILD THIS
        │  one row per transcript → batch_input.csv
        │  transcript column = plain text string, no encoding/vectorizing
        ▼
        CSV → run_scoring.py → 8-step chain
```

---

## SCRIPT 1: build_batch.py

Read all .txt and .json files from input_dir → batch_input.csv.

CLI:
  --input_dir     folder with .txt/.json transcripts
  --output_csv    default: data/batch_input.csv
  --gold_csv      optional CSV with [transcript_id, human_score]

JSON key priority for text: transcript, text, content, body, response
JSON key priority for ID: interview_id, participant_id, subject_id, id
Fallback ID: filename stem

QA/QC flags (pipe-separated, or "OK"):
  EMPTY_TEXT, TEXT_TOO_SHORT (<50 chars), TEXT_VERY_LONG (>15000 chars), MISSING_ID

Output columns:
  row_id, transcript_id, source_file, file_type, text_length,
  content_hash (MD5 8 chars), transcript, human_score, qaqc_flags

Resume-safe: skip files already in output by content_hash.

---

## SCRIPT 2: run_scoring.py

Read batch_input.csv → run 8-step chain per transcript → scored_output.csv.

CLI:
  --input_csv     path to batch_input.csv
  --output_csv    default: outputs/scored_output.csv
  --model         gptoss | llama | gemma
  --model_name    full HuggingFace model ID string
  --condition     ZS | FS | CoT
  --gpu_id        default 0
  --gpu_memory_utilization  default 0.85
  --max_model_len optional int
  --temperature   default 0.0 (deterministic — never change for scoring)
  --max_tokens    default 512; use 1500 for CoT
  --dry_run       run without LLM calls, write mock scores
  --skip_flagged  skip rows where qaqc_flags != OK
  --batch_size    default 10
  --sleep_sec     default 1.0

Resume-safe: flush after every row, skip rows with non-null p2_severity_final on re-run.

---

## THE 8-STEP CHAIN — scoring/chain.py

Implement as score_transcript(transcript, llm_backend, condition).

CRITICAL DESIGN PRINCIPLE — minimal dependencies, maximum token efficiency:
Each LLM step reads the raw transcript independently wherever possible.
Only single integers (not full JSON blobs) are passed between steps.
This keeps every prompt small and avoids token bloat.

DEPENDENCY MAP (derived from PSYCHS manual measurement concept definitions):
  Step 1  — transcript only                         INDEPENDENT
  Step 2  — transcript only                         INDEPENDENT
  Step 3  — transcript + D score (int only)         one integer passed
  Step 4  — D score + T score (Python arithmetic)   no LLM
  Step 5  — transcript only                         INDEPENDENT
  Step 6  — transcript only                         INDEPENDENT
  Step 4b — D, T, dist, interf (Python arithmetic)  no LLM
  Step 7  — transcript + severity (int only)        one integer passed
  Step 8  — severity + frequency (Python logic)     no LLM

RATIONALE from manual:
- Description (step 2): clinician reads transcript and rates content directly.
  No prior output needed — screening is a machine efficiency gate only.
- Tenacity (step 3): manual states "when there are no unusual beliefs, there
  can be no tenacity." So if D=0, skip tenacity entirely (return T=0).
  Otherwise only the D integer is needed — not the full description JSON.
- Distress (step 5): manual asks "how distressed is the participant because
  of the belief?" — readable directly from transcript. No prior score needed.
- Interference (step 6): same — behavioral/social impact readable from
  transcript directly.
- Frequency (step 7): manual says rate frequency "during the period when
  severity was at its highest level." So only the final severity integer
  is needed to set the timeframe context.

```
Raw transcript
        │
        ▼
Step 1 — LLM call 1: screening
        │  system: GENERAL_RULES + screen prompt
        │  user: transcript (only)
        │  out: suspicious_content_present (bool), screening_evidence
        │  If False → set all scores 0, write row, STOP
        ▼
Step 2 — LLM call 2: description         [INDEPENDENT — transcript only]
        │  system: GENERAL_RULES + P2_DESCRIPTION anchors 0-6
        │  user: transcript (only)
        │  out: description_score (int), supporting_evidence,
        │       disconfirming_evidence, reasoning
        ▼
Step 3 — LLM call 3: tenacity            [needs D score int only]
        │  If description_score == 0 → tenacity_score = 0, skip LLM call
        │  system: GENERAL_RULES + P2_TENACITY anchors 0-6
        │  user: transcript + "Description was rated {D}/6"
        │  out: tenacity_score (int), doubt_expressed,
        │       doubt_source, reasoning
        ▼
Step 4 — Python: synthesis check         [no LLM — arithmetic only]
        │  input: description_score (int) + tenacity_score (int)
        │  diff = abs(D - T)
        │  tiebreaker_needed = (diff == 1) or (diff in [3,5] and avg not whole)
        │  If tiebreaker_needed False → skip steps 5+6, go to 4b
        ▼ (only if tiebreaker_needed == True)
Step 5 — LLM call 4: distress            [INDEPENDENT — transcript only]
        │  system: GENERAL_RULES + P2_DISTRESS anchors 0-6
        │  user: transcript (only)
        │  out: distress_score (int), distress_evidence,
        │       distress_cause_confirmed (bool)
        ▼
Step 6 — LLM call 5: interference        [INDEPENDENT — transcript only]
        │  system: GENERAL_RULES + P2_INTERFERENCE anchors 0-6
        │  user: transcript (only)
        │  out: interference_score (int), behavioral_change, social_impact
        ▼
Step 4b — Python: final synthesis        [no LLM — Table 3 logic]
        │  input: D (int), T (int), dist (int|None), interf (int|None)
        │  implements PSYCHS Figure 1 / Table 3 exactly
        │  out: p2_severity_final (int 0-6),
        │       synthesis_rule_applied (str), secondary_used (bool)
        ▼
Step 7 — LLM call 6: frequency           [needs severity int only]
        │  system: GENERAL_RULES + P2_FREQUENCY_PM + P2_FREQUENCY_LT_PY
        │  user: transcript + "Final P2 severity = {severity}/6.
        │         Rate frequency during the period when severity
        │         was at this highest level."
        │  out: frequency_pm_score (int), frequency_lt_py_score (int),
        │       frequency_evidence
        ▼
Step 8 — Python: diagnostic groupings    [no LLM — boolean logic]
        │  input: p2_severity_final (int) + frequency scores (int)
        │  out: BIPS, APSS, BLIPS, subthreshold flags (bool)
        ▼
scored_output.csv (~35 columns)
```
---

## PYTHON SYNTHESIS — scoring/synthesize.py

Function: synthesize_p2_severity(D, T, distress, interference)
Implements PSYCHS manual Figure 1 / Table 3 exactly. Never ask the LLM to do this.

```python
def synthesize_p2_severity(D, T, distress=None, interference=None):
    if D is None or T is None:
        return None, "error", False
    diff = abs(D - T)
    higher = max(D, T)
    lower = min(D, T)

    if diff == 0:
        return D, "same", False

    if diff % 2 == 0:
        return (D + T) // 2, "even_avg", False

    if diff == 1:
        if (distress is not None and distress >= higher) or \
           (interference is not None and interference >= higher):
            return higher, "adjacent_higher", True
        return lower, "adjacent_lower", True

    if diff == 3 or diff == 5:
        avg = (D + T) / 2
        if avg == int(avg):
            return int(avg), "odd_avg", False
        if (distress is not None and distress >= higher) or \
           (interference is not None and interference >= higher):
            return higher, "odd_tiebreaker_higher", True
        return lower, "odd_tiebreaker_lower", True

    return round((D + T) / 2), "fallback", False
```

---

## PYTHON DIAGNOSTICS — scoring/diagnostics.py

Function: diagnostic_groupings(severity, frequency_pm, frequency_lt_py)
Only run if severity > 0. Returns dict of booleans.

```python
def diagnostic_groupings(severity, frequency_pm, frequency_lt_py):
    if severity == 0:
        return {k: False for k in [
            "lifetime_psychosis","sips_bips","sips_apss",
            "caarms_blips","caarms_subthreshold_frequency",
            "caarms_subthreshold_intensity"]}
    return {
        "lifetime_psychosis":             severity == 6 and frequency_lt_py >= 4,
        "sips_bips":                      severity == 6 and not (frequency_lt_py >= 4),
        "sips_apss":                      3 <= severity <= 5 and frequency_pm >= 3,
        "caarms_blips":                   severity == 6 and frequency_lt_py >= 4,
        "caarms_subthreshold_frequency":  severity == 6 and frequency_lt_py == 3,
        "caarms_subthreshold_intensity":  3 <= severity <= 5 and frequency_lt_py >= 3,
    }
```

---

## PROMPT CONDITIONS

All conditions share the same system prompt per step.
Only the user message changes.

ZS (zero-shot):
  user = transcript only (+ previous step outputs passed as context)

FS (few-shot):
  user = 1 worked example per step + transcript + previous outputs
  Examples sourced from PSYCHS manual anchor illustrations only.
  Never use test transcripts as examples.
  Anchor examples per step:
    Step 1: suspicious vs not suspicious
    Step 2: score 3 (CHR boundary — most important)
    Step 3: score 3 vs 4 (when_asked vs effortful)
    Step 5: score 3 vs 4 (apprehension vs preoccupying)
    Step 6: score 3 vs 4 (no behavior vs slight behavior change)
    Step 7: score 2 vs 3 (frequency threshold)

CoT (chain-of-thought):
  user = same as ZS + instruction:
    "Before giving your JSON, work through this out loud:
     1. Quote the most relevant evidence from the transcript.
     2. Quote any disconfirming evidence (arguing for a LOWER score).
     3. State which anchor level fits and why.
     4. Then output your JSON."
  max_tokens must be >= 1500 for CoT.

---

## GENERAL_RULES PREAMBLE — prompts/general_rules.py

Insert into every step's system prompt.

```
You are an expert clinical rater trained on the PSYCHS interview instrument.
You are rating P2 Suspiciousness/Paranoia for the past month timeframe only.

Core rating rules:
- Rate ATHEORETICALLY. Base ratings ONLY on what the participant explicitly reports.
  Do not infer causes, formulate, or rate up/down to qualify or disqualify for CHR.
- Do not discount symptoms because they seem caused by anxiety, trauma, or another disorder.
- Do not rate symptoms absent in the past month. If absent, score = 0.
- Social anxiety (fear of mental judgment only) rates no higher than 2.
  To rate 3+: must involve anticipated deliberate ill will or threat of harm.
- Subcultural or family-shared beliefs: Description caps at 2.
- Scale: 0-2 normative range. 3-5 CHR range. 6 psychotic level.
- Return ONLY valid JSON. No text before or after the JSON object.
```

---

## P2 ANCHOR TEXT PER STEP — prompts/

### step2_description.py
Anchors from PSYCHS manual section 5.k.2:
0 = Absent. No suspicious ideas. Normal vigilance only.
1 = Cautious with new people. Average person would feel same. May appear wary.
2 = Beyond average but within subcultural/family norm. Cap at 2 for any shared belief. May appear apprehensive.
3 = Thinks groups mock/talk about them. No fear of harm. Acknowledges probably not true. May appear vigilant.
4 = Fears harm, takes protective action. Acknowledges may be unnecessary. May appear defensive/hypervigilant.
5 = Believes specific person intends harm. Feels real most of the time. Can acknowledge alternative when challenged. May openly question interviewer.
6 = Completely convinced. Acts on belief despite contrary evidence. Cannot entertain alternative. Severe guardedness or directly accuses interviewer.
Behavioral supplement (use when participant appears to be withholding):
0=no suspicious appearance. 1=may appear wary. 2=may appear apprehensive.
3=may appear vigilant. 4=may appear defensive. 5=guarded/questions interviewer.
6=severe guardedness or directly accuses interviewer of harm.

### step3_tenacity.py
Anchors from PSYCHS manual section 5.i:
0 = No suspicious ideas present. Nothing to rate.
1 = Immediately and spontaneously dismisses belief as unreal without any prompting.
2 = Easily self-generates skepticism with very little effort.
3 = Readily discloses skepticism WHEN ASKED. Does NOT self-generate unprompted.
4 = Can self-generate skepticism but requires considerable time and effort.
5 = Cannot self-generate doubt. Skepticism only arises when directly challenged by another.
6 = Delusional conviction. No doubt possible even when directly challenged.
   If no one challenged the belief: infer conviction level from participant behavior.
doubt_source values: spontaneous | when_asked | when_challenged | not_induced | inferred_from_behavior

### step5_distress.py
0 = No distress from suspicious ideas.
1 = Minor concern, not distressing.
2 = Some unease but not distressing.
3 = Sense of apprehension, somewhat distressing.
4 = Suspicious ideas are preoccupying or distressing.
5 = Suspicious ideas are disturbing or severely distressing.
6 = Suspicious ideas are frightening or extremely distressing.
Critical: distress UNRELATED to the suspicious belief is NOT rated here.
Reminder: this is a secondary tiebreaker — only consulted by Python when co-primaries are adjacent.

### step6_interference.py
0 = No interference.
1 = Do not affect thoughts, feelings, social relations, or behavior.
2 = May affect but do not interfere. Behavior not affected.
3 = May slightly interfere. Behavior not affected.
4 = May somewhat interfere. Behavior may be slightly affected.
5 = May clearly interfere. Behavior may be somewhat affected.
6 = May significantly interfere. Behavior clearly affected.
Critical: reality checks (turning to look when name called) do NOT count as interference.
Reminder: secondary tiebreaker only.

### step7_frequency.py
Past Month (PM):
0=Absent. 1=1day/month-2days/week <1min/day. 2=1day/month-2days/week 1min-1hr/day.
3=1day/month-2days/week >=1hr/day OR 3-6days/week <1hr/day.
4=3-6days/week >=1hr/day OR daily <1hr/day.
5=Daily >=1hr/day OR several times/day. 6=Continuous.

Lifetime/Past Year (LT/PY):
0=Absent. 1=<1day/month. 2=1day/month-2days/week <1hr/day.
3=1day/month-2days/week >=1hr/day OR 3-6days/week <1hr/day.
4=3-6days/week >=1hr/day OR daily <1hr/day.
5=Daily >=1hr/day OR several times/day. 6=Continuous.
Rule: if severity = 0 → both frequency scores = 0.

---

## MODEL BACKENDS — models/

### models/base.py
Abstract class LLMBackend:
  method: generate(prompt_system: str, prompt_user: str) -> str

### models/gptoss.py — GPT-OSS via Harmony encoding
```python
import os
from vllm import LLM, SamplingParams
from openai_harmony import HarmonyEncodingName, Role, load_harmony_encoding

class GPTOSSBackend(LLMBackend):
    def __init__(self, model_name, gpu_id, gpu_memory_utilization,
                 max_model_len, temperature, max_tokens):
        os.environ['CUDA_DEVICE_ORDER'] = 'PCI_BUS_ID'
        os.environ['CUDA_VISIBLE_DEVICES'] = str(gpu_id)
        llm_kwargs = {
            'model': model_name,
            'enable_prefix_caching': True,
            'tensor_parallel_size': 1,
            'gpu_memory_utilization': gpu_memory_utilization,
            'dtype': 'auto',
            'trust_remote_code': True,
        }
        if max_model_len:
            llm_kwargs['max_model_len'] = max_model_len
        self.llm = LLM(**llm_kwargs)
        self.encoding = load_harmony_encoding(HarmonyEncodingName.HARMONY_GPT_OSS)
        self.stop_token_ids = self.encoding.stop_tokens_for_assistant_actions()
        self.sampling = SamplingParams(
            temperature=temperature,
            max_tokens=max_tokens,
            stop_token_ids=self.stop_token_ids
        )

    def generate(self, prompt_system, prompt_user):
        # Adapt build_harmony_conversation() to match exact lab codebase signature
        conversation = build_harmony_conversation(
            system=prompt_system, user=prompt_user
        )
        token_ids = self.encoding.render_conversation_for_completion(
            conversation, Role.ASSISTANT
        )
        output = self.llm.generate(
            [{'prompt_token_ids': token_ids}], self.sampling
        )
        return output[0].outputs[0].text if output[0].outputs else ''
```

### models/vllm_standard.py — Llama 3.3 + Gemma
```python
import os
from vllm import LLM, SamplingParams

class VLLMStandardBackend(LLMBackend):
    def __init__(self, model_name, gpu_id, gpu_memory_utilization,
                 max_model_len, temperature, max_tokens):
        os.environ['CUDA_DEVICE_ORDER'] = 'PCI_BUS_ID'
        os.environ['CUDA_VISIBLE_DEVICES'] = str(gpu_id)
        llm_kwargs = {
            'model': model_name,
            'enable_prefix_caching': True,
            'tensor_parallel_size': 1,
            'gpu_memory_utilization': gpu_memory_utilization,
            'dtype': 'auto',
            'trust_remote_code': True,
        }
        if max_model_len:
            llm_kwargs['max_model_len'] = max_model_len
        self.llm = LLM(**llm_kwargs)
        self.tokenizer = self.llm.get_tokenizer()
        self.sampling = SamplingParams(
            temperature=temperature,
            max_tokens=max_tokens
        )

    def generate(self, prompt_system, prompt_user):
        messages = [
            {"role": "system", "content": prompt_system},
            {"role": "user",   "content": prompt_user}
        ]
        prompt = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        output = self.llm.generate([prompt], self.sampling)
        return output[0].outputs[0].text if output[0].outputs else ''
```

---

## OUTPUT COLUMNS — scored_output.csv (~35 total)

Screening:
  suspicious_content_present, screening_evidence

Description (Step 2):
  description_score, supporting_evidence, disconfirming_evidence, description_reasoning

Tenacity (Step 3):
  tenacity_score, doubt_expressed, doubt_source, tenacity_reasoning

Synthesis check (Step 4):
  synthesis_path, tiebreaker_needed

Distress (Step 5, blank if skipped):
  distress_score, distress_evidence, distress_cause_confirmed

Interference (Step 6, blank if skipped):
  interference_score, behavioral_change, social_impact

Final synthesis (Step 4b):
  p2_severity_final, synthesis_rule_applied, secondary_used

Frequency (Step 7):
  frequency_pm_score, frequency_lt_py_score, frequency_evidence

Diagnostics (Step 8):
  lifetime_psychosis, sips_bips, sips_apss,
  caarms_blips, caarms_subthreshold_frequency, caarms_subthreshold_intensity

Metadata:
  transcript_id, source_file, human_score, model, condition,
  prompt_tokens_total, completion_tokens_total, api_error, scored_at

---

## SCRIPT 3: evaluate.py

Read all scored_output.csv files in outputs/.
Compute per model, per condition:
  ICC(2,1) of p2_severity_final vs human_score
  Exact match % (p2_severity_final == human_score)
  Adjacent agreement % (|p2_severity_final - human_score| <= 1)
  Mean score delta — bias (mean LLM - mean human)
  Sensitivity at 2→3 boundary (CHR threshold) — most important metric
  Specificity at 2→3 boundary
  BERTScore F1 on reasoning chains (CoT condition only)

Output: outputs/metrics_report.csv + printed summary table.

---

## TESTS — tests/

### test_synthesize.py — cover every case from PSYCHS Table 3
  D=3, T=3 → 3 (same)
  D=4, T=2 → 3 (even diff, average)
  D=4, T=3, dist=4, interf=2 → 4 (adjacent, distress >= higher)
  D=4, T=3, dist=2, interf=2 → 3 (adjacent, both secondary < higher)
  D=5, T=2, dist=4, interf=3 → 4 (odd non-adjacent, avg=3.5, tiebreaker)
  D=0, T=0 → 0
  D=6, T=1 → 4 (diff=5, avg=3.5, check secondary)

### test_diagnostics.py
  severity=6, freq_lt_py=5 → lifetime_psychosis=True
  severity=6, freq_lt_py=2 → sips_bips=True
  severity=4, freq_pm=3 → sips_apss=True
  severity=2 → all False

### test_chain.py
  Dry run with mock backend → valid output row structure
  Step 1 returns False → all scores 0, steps 2-8 skipped
  tiebreaker_needed=False → steps 5+6 blank in output

---

## README.md — write with these sections

1. Project overview (3 sentences: ANNA-PR, P2 Suspiciousness, what the pipeline does)
2. Architecture overview:
   Raw transcript → QA/QC → P2 extraction → build_batch.py →
   8-step chained LLM scoring → scored_output.csv → evaluate.py
3. Why chained prompting: process supervision vs outcome supervision
4. Models supported: GPT-OSS (Harmony), Llama 3.3-70B, Gemma 3-27B
5. Requirements: Python 3.10+, vLLM, openai_harmony, pandas, scipy, bert-score
6. Installation
7. How to run (exact commands for all 3 scripts)
8. Output column reference
9. Data privacy statement

---

## INSTRUCTIONS.md — write for Annie to run on the cluster

### Before you start
- [ ] Transcripts already QA/QC'd and P2-extracted (your existing scripts)
- [ ] Run: nvidia-smi → confirm which GPU is free
- [ ] Run: python -c "import vllm; print(vllm.__version__)"
- [ ] For GPT-OSS: python -c "from openai_harmony import load_harmony_encoding"
- [ ] Know your model name strings (check config.json in model cache)

### Step 1 — build_batch.py
```bash
python build_batch.py \
  --input_dir /path/to/p2_extracted_transcripts \
  --output_csv data/batch_input.csv \
  --gold_csv /path/to/human_scores.csv
```
Check: open data/batch_input.csv, confirm rows, check qaqc_flags column.

### Step 2 — dry run first (no GPU)
```bash
python run_scoring.py \
  --input_csv data/batch_input.csv \
  --output_csv outputs/test_dryrun.csv \
  --model llama \
  --condition ZS \
  --dry_run
```
Check: outputs/test_dryrun.csv has all 35 columns with mock values.

### Step 3 — real run (example: GPT-OSS, zero-shot)
```bash
CUDA_VISIBLE_DEVICES=1 python run_scoring.py \
  --input_csv data/batch_input.csv \
  --output_csv outputs/scored_gptoss_ZS.csv \
  --model gptoss \
  --model_name YOUR_GPTOSS_MODEL_NAME_HERE \
  --condition ZS \
  --gpu_id 1 \
  --temperature 0.0 \
  --max_tokens 512
```

### Step 4 — run all 9 conditions (3 models × 3 conditions)
Name output files: scored_{model}_{condition}.csv
e.g. scored_llama_ZS.csv, scored_llama_FS.csv, scored_llama_CoT.csv
For CoT: add --max_tokens 1500

### Step 5 — evaluate
```bash
python evaluate.py \
  --scored_dir outputs/ \
  --output_csv outputs/metrics_report.csv
```

### If a run dies mid-way
Re-run the same command. Script resumes automatically — already-scored rows are skipped.

### Token reminders
ZS + FS: --max_tokens 512
CoT: --max_tokens 1500 minimum (reasoning chain truncates and JSON never appears if lower)

---

## CRITICAL IMPLEMENTATION NOTES

1. temperature=0.0 always. Stochastic scoring kills ICC reproducibility.
2. The LLM never outputs p2_severity_final directly. Python always synthesizes it.
3. Steps 5+6 are conditional — only fire when Python determines tiebreaker is needed.
4. Flush CSV after every row — safe if cluster job dies mid-run.
5. The 2→3 boundary is the CHR-P clinical threshold. Report sensitivity/specificity here separately.
6. For GPT-OSS: adapt build_harmony_conversation() to match exact lab codebase signature.
7. Transcripts are plain text in the CSV. Never vectorize or encode before passing to LLM.
8. data/ folder is gitignored — transcripts never committed.
