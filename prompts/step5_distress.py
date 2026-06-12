"""Step 5: Distress — How distressed is the participant because of the beliefs?"""

from prompts.general_rules import GENERAL_RULES

STEP5_DISTRESS_ANCHORS = """
ANCHORS (from PSYCHS manual):

0 = No distress from suspicious ideas.

1 = Minor concern, not distressing.

2 = Some unease but not distressing.

3 = Sense of apprehension, somewhat distressing.

4 = Suspicious ideas are preoccupying or distressing.

5 = Suspicious ideas are disturbing or severely distressing.

6 = Suspicious ideas are frightening or extremely distressing.

CRITICAL: Distress UNRELATED to the suspicious belief is NOT rated here (e.g., general anxiety disorder, unrelated trauma).
REMINDER: This is a secondary tiebreaker — only consulted by Python when co-primaries are adjacent.
"""

STEP5_DISTRESS_SYSTEM = GENERAL_RULES + "\n\n" + STEP5_DISTRESS_ANCHORS + """

You are rating Distress: how emotionally distressed is the participant because of their suspicious beliefs.
Return ONLY valid JSON. No text before or after."""

STEP5_DISTRESS_USER_TEMPLATE = """Rate the Distress caused by suspicious ideas in this interview (0-6).
Use the anchors above to guide your rating.

Transcript:
{transcript}

Provide:
1. A score (0-6)
2. Evidence of distress from the transcript
3. Whether the distress is clearly caused by the belief (not other factors)
4. Brief reasoning

Return ONLY this JSON (no text before or after):
{{
    "distress_score": <int 0-6>,
    "distress_evidence": "<quote or summary of emotional distress>",
    "distress_cause_confirmed": <bool>,
    "distress_reasoning": "<brief explanation of why this anchor fits>"
}}"""

STEP5_DISTRESS_USER_FS_TEMPLATE = """Rate the Distress caused by suspicious ideas in this interview (0-6).
Use the anchors above to guide your rating.

WORKED EXAMPLE (score 3):
Participant: "I feel on edge when I'm around those people. It makes me anxious, but I can usually manage."
Rating: 3 — sense of apprehension, somewhat distressing.

WORKED EXAMPLE (score 4):
Participant: "I can't stop thinking about what they might do. It keeps me up at night. I'm constantly worried."
Rating: 4 — suspicious ideas are preoccupying and distressing.

Now rate THIS transcript:

Transcript:
{transcript}

Provide:
1. A score (0-6)
2. Evidence of distress from the transcript
3. Whether the distress is clearly caused by the belief (not other factors)
4. Brief reasoning

Return ONLY this JSON (no text before or after):
{{
    "distress_score": <int 0-6>,
    "distress_evidence": "<quote or summary of emotional distress>",
    "distress_cause_confirmed": <bool>,
    "distress_reasoning": "<brief explanation of why this anchor fits>"
}}"""
