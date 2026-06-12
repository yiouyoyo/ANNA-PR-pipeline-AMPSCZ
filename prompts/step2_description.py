"""Step 2: Description — Rate the content/bizarreness of suspicious beliefs."""

from prompts.general_rules import GENERAL_RULES

STEP2_DESCRIPTION_ANCHORS = """
ANCHORS (from PSYCHS manual section 5.k.2):

0 = Absent. No suspicious ideas. Normal vigilance only.

1 = Cautious with new people. Average person would feel same. May appear wary.

2 = Beyond average but within subcultural/family norm. Cap at 2 for any shared belief. May appear apprehensive.

3 = Thinks groups mock/talk about them. No fear of harm. Acknowledges probably not true. May appear vigilant.

4 = Fears harm, takes protective action. Acknowledges may be unnecessary. May appear defensive/hypervigilant.

5 = Believes specific person intends harm. Feels real most of the time. Can acknowledge alternative when challenged. May openly question interviewer.

6 = Completely convinced. Acts on belief despite contrary evidence. Cannot entertain alternative. Severe guardedness or directly accuses interviewer.

Behavioral supplement (use when participant appears to be withholding):
  0 = no suspicious appearance
  1 = may appear wary
  2 = may appear apprehensive
  3 = may appear vigilant
  4 = may appear defensive
  5 = guarded/questions interviewer
  6 = severe guardedness or directly accuses interviewer of harm
"""

STEP2_DESCRIPTION_SYSTEM = GENERAL_RULES + "\n\n" + STEP2_DESCRIPTION_ANCHORS + """

You are rating Description: the content and bizarreness of suspicious ideas.
Return ONLY valid JSON. No text before or after."""

STEP2_DESCRIPTION_USER_TEMPLATE = """Rate the Description of suspicious ideas in this interview (0-6).
Use the anchors above to guide your rating.

Transcript:
{transcript}

Provide:
1. A score (0-6)
2. Supporting evidence from the transcript
3. Any disconfirming evidence (arguing for a LOWER score)
4. Brief reasoning

Return ONLY this JSON (no text before or after):
{{
    "description_score": <int 0-6>,
    "supporting_evidence": "<quote or summary of suspicious ideas>",
    "disconfirming_evidence": "<quote or summary of contrary evidence, if any>",
    "description_reasoning": "<brief explanation of why this anchor fits>"
}}"""

STEP2_DESCRIPTION_USER_FS_TEMPLATE = """Rate the Description of suspicious ideas in this interview (0-6).
Use the anchors above to guide your rating.

WORKED EXAMPLE (score 3):
Participant: "People at work make comments about me. I know it sounds paranoid, but I think they're talking about me behind my back. Probably not true though."
Rating: 3 — thinks groups mock/talk about them, no fear of harm, acknowledges probably not true.

Now rate THIS transcript:

Transcript:
{transcript}

Provide:
1. A score (0-6)
2. Supporting evidence from the transcript
3. Any disconfirming evidence (arguing for a LOWER score)
4. Brief reasoning

Return ONLY this JSON (no text before or after):
{{
    "description_score": <int 0-6>,
    "supporting_evidence": "<quote or summary of suspicious ideas>",
    "disconfirming_evidence": "<quote or summary of contrary evidence, if any>",
    "description_reasoning": "<brief explanation of why this anchor fits>"
}}"""
