"""Step 1: Screening — Is P2 (suspicious/paranoid content) present?"""

from prompts.general_rules import GENERAL_RULES

STEP1_SCREEN_SYSTEM = GENERAL_RULES + """

You must determine whether this interview contains suspicious, paranoid, or persecutory ideation.
Return ONLY valid JSON. No text before or after."""

STEP1_SCREEN_USER_TEMPLATE = """Rate whether this interview contains suspicious, paranoid, or persecutory ideation about others intending harm or talking about the participant.

Transcript:
{transcript}

Return ONLY this JSON structure (no text before or after):
{{
    "suspicious_content_present": <bool>,
    "screening_evidence": "<brief quote or description of suspicious content if present, or 'No suspicious content detected' if absent>"
}}"""
