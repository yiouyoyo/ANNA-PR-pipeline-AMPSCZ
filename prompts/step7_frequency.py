"""Step 7: Frequency — How often do suspicious ideas occur?"""

from prompts.general_rules import GENERAL_RULES

STEP7_FREQUENCY_ANCHORS = """
ANCHORS (from PSYCHS manual):

PAST MONTH (PM) frequency scale:
0 = Absent
1 = 1 day/month - 2 days/week, <1 min/day
2 = 1 day/month - 2 days/week, 1 min - 1 hr/day
3 = 1 day/month - 2 days/week, >=1 hr/day OR 3-6 days/week, <1 hr/day
4 = 3-6 days/week, >=1 hr/day OR daily, <1 hr/day
5 = Daily, >=1 hr/day OR several times/day
6 = Continuous

LIFETIME / PAST YEAR (LT/PY) frequency scale:
0 = Absent
1 = <1 day/month
2 = 1 day/month - 2 days/week, <1 hr/day
3 = 1 day/month - 2 days/week, >=1 hr/day OR 3-6 days/week, <1 hr/day
4 = 3-6 days/week, >=1 hr/day OR daily, <1 hr/day
5 = Daily, >=1 hr/day OR several times/day
6 = Continuous

Rule: If severity = 0, both frequency scores = 0.
"""

STEP7_FREQUENCY_SYSTEM = GENERAL_RULES + "\n\n" + STEP7_FREQUENCY_ANCHORS + """

You are rating Frequency: how often suspicious ideas occur.
Rate both past month and lifetime/past year.
Return ONLY valid JSON. No text before or after."""

STEP7_FREQUENCY_USER_TEMPLATE = """Rate the Frequency of suspicious ideas in this interview.
Final P2 severity = {severity}/6.
Rate frequency during the period when severity was at this highest level.

Use the anchors above to guide your ratings.

Transcript:
{transcript}

Provide:
1. Past month frequency score (0-6)
2. Lifetime / past year frequency score (0-6)
3. Evidence supporting these ratings
4. Brief reasoning

Return ONLY this JSON (no text before or after):
{{
    "frequency_pm_score": <int 0-6>,
    "frequency_lt_py_score": <int 0-6>,
    "frequency_evidence": "<description of how often ideas occur>",
    "frequency_reasoning": "<brief explanation of ratings>"
}}"""

STEP7_FREQUENCY_USER_FS_TEMPLATE = """Rate the Frequency of suspicious ideas in this interview.
Final P2 severity = {severity}/6.
Rate frequency during the period when severity was at this highest level.

Use the anchors above to guide your ratings.

WORKED EXAMPLE (past month score 2, past year score 3):
Participant: "I think about it a few times a week, for maybe 20-30 minutes when I do."
PM rating: 2 (1 day/month - 2 days/week, 1 min - 1 hr/day)
PY rating: 3 (1 day/month - 2 days/week, >=1 hr total when thinking about it)

WORKED EXAMPLE (past month score 3, past year score 5):
Participant: "Last month it was constantly on my mind, hours every day. Before that, it was more like a few days a week."
PM rating: 3 (1 day/month - 2 days/week, >=1 hr/day OR 3-6 days/week, <1 hr/day)
PY rating: 5 (Daily, >=1 hr/day at peak)

Now rate THIS transcript:

Transcript:
{transcript}

Provide:
1. Past month frequency score (0-6)
2. Lifetime / past year frequency score (0-6)
3. Evidence supporting these ratings
4. Brief reasoning

Return ONLY this JSON (no text before or after):
{{
    "frequency_pm_score": <int 0-6>,
    "frequency_lt_py_score": <int 0-6>,
    "frequency_evidence": "<description of how often ideas occur>",
    "frequency_reasoning": "<brief explanation of ratings>"
}}"""
