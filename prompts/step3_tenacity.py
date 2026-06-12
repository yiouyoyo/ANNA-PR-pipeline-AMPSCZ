"""Step 3: Tenacity — How much doubt does the participant express about their beliefs?"""

from prompts.general_rules import GENERAL_RULES

STEP3_TENACITY_ANCHORS = """
ANCHORS (from PSYCHS manual section 5.i):

0 = No suspicious ideas present. Nothing to rate.

1 = Immediately and spontaneously dismisses belief as unreal without any prompting.

2 = Easily self-generates skepticism with very little effort.

3 = Readily discloses skepticism WHEN ASKED. Does NOT self-generate unprompted.

4 = Can self-generate skepticism but requires considerable time and effort.

5 = Cannot self-generate doubt. Skepticism only arises when directly challenged by another.

6 = Delusional conviction. No doubt possible even when directly challenged.
   If no one challenged the belief: infer conviction level from participant behavior.

doubt_source values: "spontaneous" | "when_asked" | "when_challenged" | "not_induced" | "inferred_from_behavior"
"""

STEP3_TENACITY_SYSTEM = GENERAL_RULES + "\n\n" + STEP3_TENACITY_ANCHORS + """

You are rating Tenacity: how much doubt the participant expresses about their suspicious beliefs.
Return ONLY valid JSON. No text before or after."""

STEP3_TENACITY_USER_TEMPLATE = """Rate the Tenacity of suspicious ideas in this interview (0-6).
Use the anchors above to guide your rating.

Context: Description was rated {description_score}/6.

Transcript:
{transcript}

Provide:
1. A score (0-6)
2. Whether doubt was spontaneously expressed, expressed when asked, or expressed when challenged
3. The source of doubt
4. Brief reasoning

Return ONLY this JSON (no text before or after):
{{
    "tenacity_score": <int 0-6>,
    "doubt_expressed": <bool>,
    "doubt_source": "<one of: spontaneous, when_asked, when_challenged, not_induced, inferred_from_behavior>",
    "tenacity_reasoning": "<brief explanation of why this anchor fits>"
}}"""

STEP3_TENACITY_USER_FS_TEMPLATE = """Rate the Tenacity of suspicious ideas in this interview (0-6).
Use the anchors above to guide your rating.

WORKED EXAMPLE (score 3):
Interviewer: "Do you think people are really talking about you?"
Participant: "Well, when you put it that way... no, probably not. I guess I was being paranoid."
Rating: 3 — readily discloses skepticism WHEN ASKED, but does not self-generate unprompted.

WORKED EXAMPLE (score 4):
Participant: "I know they're after me. But... maybe I'm overthinking. It took me a while to admit that."
Rating: 4 — can self-generate skepticism but requires considerable time and effort.

Now rate THIS transcript:

Context: Description was rated {description_score}/6.

Transcript:
{transcript}

Provide:
1. A score (0-6)
2. Whether doubt was spontaneously expressed, expressed when asked, or expressed when challenged
3. The source of doubt
4. Brief reasoning

Return ONLY this JSON (no text before or after):
{{
    "tenacity_score": <int 0-6>,
    "doubt_expressed": <bool>,
    "doubt_source": "<one of: spontaneous, when_asked, when_challenged, not_induced, inferred_from_behavior>",
    "tenacity_reasoning": "<brief explanation of why this anchor fits>"
}}"""
