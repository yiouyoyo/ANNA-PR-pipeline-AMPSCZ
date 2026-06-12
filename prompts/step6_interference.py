"""Step 6: Interference — How much do suspicious beliefs interfere with functioning?"""

from prompts.general_rules import GENERAL_RULES

STEP6_INTERFERENCE_ANCHORS = """
ANCHORS (from PSYCHS manual):

0 = No interference.

1 = Do not affect thoughts, feelings, social relations, or behavior.

2 = May affect but do not interfere. Behavior not affected.

3 = May slightly interfere. Behavior not affected.

4 = May somewhat interfere. Behavior may be slightly affected.

5 = May clearly interfere. Behavior may be somewhat affected.

6 = May significantly interfere. Behavior clearly affected.

CRITICAL: Reality checks (e.g., turning to look when name called) do NOT count as interference.
REMINDER: This is a secondary tiebreaker — only consulted by Python when co-primaries are adjacent.
"""

STEP6_INTERFERENCE_SYSTEM = GENERAL_RULES + "\n\n" + STEP6_INTERFERENCE_ANCHORS + """

You are rating Interference: how much do suspicious beliefs interfere with the participant's functioning and behavior.
Return ONLY valid JSON. No text before or after."""

STEP6_INTERFERENCE_USER_TEMPLATE = """Rate the Interference caused by suspicious ideas in this interview (0-6).
Use the anchors above to guide your rating.

Transcript:
{transcript}

Provide:
1. A score (0-6)
2. Evidence of behavioral change or social impact
3. Nature of the interference (avoidance, hypervigilance, etc.)
4. Brief reasoning

Return ONLY this JSON (no text before or after):
{{
    "interference_score": <int 0-6>,
    "behavioral_change": "<description of how the belief affects the participant's behavior>",
    "social_impact": "<description of impact on relationships, work, or daily activities>",
    "interference_reasoning": "<brief explanation of why this anchor fits>"
}}"""

STEP6_INTERFERENCE_USER_FS_TEMPLATE = """Rate the Interference caused by suspicious ideas in this interview (0-6).
Use the anchors above to guide your rating.

WORKED EXAMPLE (score 3):
Participant: "I avoid certain people at work, but I still go to work. I just sit alone at lunch."
Rating: 3 — may slightly interfere, but behavior not notably affected (participant still functions).

WORKED EXAMPLE (score 4):
Participant: "I've been calling in sick to avoid seeing those people. I stay home more now."
Rating: 4 — may somewhat interfere, behavior may be slightly affected (avoiding situations).

Now rate THIS transcript:

Transcript:
{transcript}

Provide:
1. A score (0-6)
2. Evidence of behavioral change or social impact
3. Nature of the interference (avoidance, hypervigilance, etc.)
4. Brief reasoning

Return ONLY this JSON (no text before or after):
{{
    "interference_score": <int 0-6>,
    "behavioral_change": "<description of how the belief affects the participant's behavior>",
    "social_impact": "<description of impact on relationships, work, or daily activities>",
    "interference_reasoning": "<brief explanation of why this anchor fits>"
}}"""
