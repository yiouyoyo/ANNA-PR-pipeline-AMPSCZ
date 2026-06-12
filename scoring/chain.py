"""8-step chained scoring for PSYCHS P2 Suspiciousness.

This module orchestrates the complete scoring pipeline:
- Step 1: Screening (LLM)
- Step 2: Description (LLM, independent)
- Step 3: Tenacity (LLM, needs D score only)
- Step 4: Python synthesis check (no LLM)
- Step 5: Distress (LLM, independent, conditional on tiebreaker_needed)
- Step 6: Interference (LLM, independent, conditional on tiebreaker_needed)
- Step 4b: Final synthesis (no LLM, Python only)
- Step 7: Frequency (LLM, needs severity score only)
- Step 8: Diagnostic groupings (no LLM, Python only)
"""

import json
import logging
from typing import Dict, Optional, Any

from prompts.step1_screen import STEP1_SCREEN_SYSTEM, STEP1_SCREEN_USER_TEMPLATE
from prompts.step2_description import (
    STEP2_DESCRIPTION_SYSTEM, 
    STEP2_DESCRIPTION_USER_TEMPLATE,
    STEP2_DESCRIPTION_USER_FS_TEMPLATE
)
from prompts.step3_tenacity import (
    STEP3_TENACITY_SYSTEM,
    STEP3_TENACITY_USER_TEMPLATE,
    STEP3_TENACITY_USER_FS_TEMPLATE
)
from prompts.step5_distress import (
    STEP5_DISTRESS_SYSTEM,
    STEP5_DISTRESS_USER_TEMPLATE,
    STEP5_DISTRESS_USER_FS_TEMPLATE
)
from prompts.step6_interference import (
    STEP6_INTERFERENCE_SYSTEM,
    STEP6_INTERFERENCE_USER_TEMPLATE,
    STEP6_INTERFERENCE_USER_FS_TEMPLATE
)
from prompts.step7_frequency import (
    STEP7_FREQUENCY_SYSTEM,
    STEP7_FREQUENCY_USER_TEMPLATE,
    STEP7_FREQUENCY_USER_FS_TEMPLATE
)
from scoring.synthesize import synthesize_p2_severity
from scoring.diagnostics import diagnostic_groupings

logger = logging.getLogger(__name__)


def score_transcript(transcript: str, llm_backend: Any, condition: str) -> Dict[str, Any]:
    """
    Score a single transcript through all 8 steps.
    
    Args:
        transcript (str): Raw interview text
        llm_backend: LLMBackend instance with generate(system, user) method
        condition (str): "ZS" (zero-shot), "FS" (few-shot), or "CoT" (chain-of-thought)
    
    Returns:
        dict: Complete scoring output with all 35 columns
    """
    
    result = {
        # Screening (Step 1)
        "suspicious_content_present": None,
        "screening_evidence": None,
        
        # Description (Step 2)
        "description_score": None,
        "supporting_evidence": None,
        "disconfirming_evidence": None,
        "description_reasoning": None,
        
        # Tenacity (Step 3)
        "tenacity_score": None,
        "doubt_expressed": None,
        "doubt_source": None,
        "tenacity_reasoning": None,
        
        # Synthesis check (Step 4)
        "synthesis_path": None,
        "tiebreaker_needed": None,
        
        # Distress (Step 5, conditional)
        "distress_score": None,
        "distress_evidence": None,
        "distress_cause_confirmed": None,
        "distress_reasoning": None,
        
        # Interference (Step 6, conditional)
        "interference_score": None,
        "behavioral_change": None,
        "social_impact": None,
        "interference_reasoning": None,
        
        # Final synthesis (Step 4b)
        "p2_severity_final": None,
        "synthesis_rule_applied": None,
        "secondary_used": None,
        
        # Frequency (Step 7)
        "frequency_pm_score": None,
        "frequency_lt_py_score": None,
        "frequency_evidence": None,
        "frequency_reasoning": None,
        
        # Diagnostics (Step 8)
        "lifetime_psychosis": None,
        "sips_bips": None,
        "sips_apss": None,
        "caarms_blips": None,
        "caarms_subthreshold_frequency": None,
        "caarms_subthreshold_intensity": None,
        
        # Metadata
        "llm_calls": 0,
        "error": None,
    }
    
    try:
        # ===== STEP 1: Screening =====
        user_prompt = STEP1_SCREEN_USER_TEMPLATE.format(transcript=transcript)
        response_text = llm_backend.generate(STEP1_SCREEN_SYSTEM, user_prompt)
        result["llm_calls"] += 1
        
        screen_output = _parse_json_response(response_text)
        if not screen_output:
            result["error"] = "Step 1: Failed to parse screening response"
            return result
        
        result["suspicious_content_present"] = screen_output.get("suspicious_content_present")
        result["screening_evidence"] = screen_output.get("screening_evidence")
        
        # If screening negative, set all other scores to 0 and return
        if not result["suspicious_content_present"]:
            result["description_score"] = 0
            result["tenacity_score"] = 0
            result["distress_score"] = 0
            result["interference_score"] = 0
            result["p2_severity_final"] = 0
            result["frequency_pm_score"] = 0
            result["frequency_lt_py_score"] = 0
            result["synthesis_rule_applied"] = "screening_negative"
            # Set diagnostics to all False
            diag = diagnostic_groupings(0, 0, 0)
            for key in diag:
                result[key] = diag[key]
            return result
        
        # ===== STEP 2: Description (independent) =====
        if condition == "FS":
            user_prompt = STEP2_DESCRIPTION_USER_FS_TEMPLATE.format(transcript=transcript)
        else:  # ZS or CoT
            user_prompt = STEP2_DESCRIPTION_USER_TEMPLATE.format(transcript=transcript)
            if condition == "CoT":
                user_prompt = _add_cot_instruction(user_prompt)
        
        response_text = llm_backend.generate(STEP2_DESCRIPTION_SYSTEM, user_prompt)
        result["llm_calls"] += 1
        
        desc_output = _parse_json_response(response_text)
        if not desc_output:
            result["error"] = "Step 2: Failed to parse description response"
            return result
        
        result["description_score"] = desc_output.get("description_score")
        result["supporting_evidence"] = desc_output.get("supporting_evidence")
        result["disconfirming_evidence"] = desc_output.get("disconfirming_evidence")
        result["description_reasoning"] = desc_output.get("description_reasoning")
        
        description_score = result["description_score"]
        
        # ===== STEP 3: Tenacity (conditional: only if D > 0) =====
        if description_score == 0:
            result["tenacity_score"] = 0
            result["doubt_expressed"] = False
            result["doubt_source"] = "not_applicable"
            result["tenacity_reasoning"] = "No suspicious ideas present"
        else:
            if condition == "FS":
                user_prompt = STEP3_TENACITY_USER_FS_TEMPLATE.format(
                    transcript=transcript,
                    description_score=description_score
                )
            else:  # ZS or CoT
                user_prompt = STEP3_TENACITY_USER_TEMPLATE.format(
                    transcript=transcript,
                    description_score=description_score
                )
                if condition == "CoT":
                    user_prompt = _add_cot_instruction(user_prompt)
            
            response_text = llm_backend.generate(STEP3_TENACITY_SYSTEM, user_prompt)
            result["llm_calls"] += 1
            
            ten_output = _parse_json_response(response_text)
            if not ten_output:
                result["error"] = "Step 3: Failed to parse tenacity response"
                return result
            
            result["tenacity_score"] = ten_output.get("tenacity_score")
            result["doubt_expressed"] = ten_output.get("doubt_expressed")
            result["doubt_source"] = ten_output.get("doubt_source")
            result["tenacity_reasoning"] = ten_output.get("tenacity_reasoning")
        
        tenacity_score = result["tenacity_score"]
        
        # ===== STEP 4: Python synthesis check (no LLM) =====
        diff = abs(description_score - tenacity_score)
        tiebreaker_needed = (diff == 1) or (diff in [3, 5] and (description_score + tenacity_score) % 2 != 0)
        
        result["synthesis_path"] = f"D={description_score}, T={tenacity_score}, diff={diff}"
        result["tiebreaker_needed"] = tiebreaker_needed
        
        # ===== STEP 5: Distress (conditional: only if tiebreaker_needed) =====
        distress_score = None
        if tiebreaker_needed:
            if condition == "FS":
                user_prompt = STEP5_DISTRESS_USER_FS_TEMPLATE.format(transcript=transcript)
            else:  # ZS or CoT
                user_prompt = STEP5_DISTRESS_USER_TEMPLATE.format(transcript=transcript)
                if condition == "CoT":
                    user_prompt = _add_cot_instruction(user_prompt)
            
            response_text = llm_backend.generate(STEP5_DISTRESS_SYSTEM, user_prompt)
            result["llm_calls"] += 1
            
            dist_output = _parse_json_response(response_text)
            if not dist_output:
                result["error"] = "Step 5: Failed to parse distress response"
                return result
            
            result["distress_score"] = dist_output.get("distress_score")
            result["distress_evidence"] = dist_output.get("distress_evidence")
            result["distress_cause_confirmed"] = dist_output.get("distress_cause_confirmed")
            result["distress_reasoning"] = dist_output.get("distress_reasoning")
            distress_score = result["distress_score"]
        
        # ===== STEP 6: Interference (conditional: only if tiebreaker_needed) =====
        interference_score = None
        if tiebreaker_needed:
            if condition == "FS":
                user_prompt = STEP6_INTERFERENCE_USER_FS_TEMPLATE.format(transcript=transcript)
            else:  # ZS or CoT
                user_prompt = STEP6_INTERFERENCE_USER_TEMPLATE.format(transcript=transcript)
                if condition == "CoT":
                    user_prompt = _add_cot_instruction(user_prompt)
            
            response_text = llm_backend.generate(STEP6_INTERFERENCE_SYSTEM, user_prompt)
            result["llm_calls"] += 1
            
            intf_output = _parse_json_response(response_text)
            if not intf_output:
                result["error"] = "Step 6: Failed to parse interference response"
                return result
            
            result["interference_score"] = intf_output.get("interference_score")
            result["behavioral_change"] = intf_output.get("behavioral_change")
            result["social_impact"] = intf_output.get("social_impact")
            result["interference_reasoning"] = intf_output.get("interference_reasoning")
            interference_score = result["interference_score"]
        
        # ===== STEP 4b: Final synthesis (no LLM) =====
        severity, rule, secondary_used = synthesize_p2_severity(
            description_score, tenacity_score, distress_score, interference_score
        )
        result["p2_severity_final"] = severity
        result["synthesis_rule_applied"] = rule
        result["secondary_used"] = secondary_used
        
        # ===== STEP 7: Frequency =====
        if condition == "FS":
            user_prompt = STEP7_FREQUENCY_USER_FS_TEMPLATE.format(
                transcript=transcript,
                severity=severity
            )
        else:  # ZS or CoT
            user_prompt = STEP7_FREQUENCY_USER_TEMPLATE.format(
                transcript=transcript,
                severity=severity
            )
            if condition == "CoT":
                user_prompt = _add_cot_instruction(user_prompt)
        
        response_text = llm_backend.generate(STEP7_FREQUENCY_SYSTEM, user_prompt)
        result["llm_calls"] += 1
        
        freq_output = _parse_json_response(response_text)
        if not freq_output:
            result["error"] = "Step 7: Failed to parse frequency response"
            return result
        
        result["frequency_pm_score"] = freq_output.get("frequency_pm_score")
        result["frequency_lt_py_score"] = freq_output.get("frequency_lt_py_score")
        result["frequency_evidence"] = freq_output.get("frequency_evidence")
        result["frequency_reasoning"] = freq_output.get("frequency_reasoning")
        
        # If severity = 0, both frequencies should be 0
        if severity == 0:
            result["frequency_pm_score"] = 0
            result["frequency_lt_py_score"] = 0
        
        # ===== STEP 8: Diagnostic groupings (no LLM) =====
        freq_pm = result["frequency_pm_score"]
        freq_lt_py = result["frequency_lt_py_score"]
        diag = diagnostic_groupings(severity, freq_pm, freq_lt_py)
        for key in diag:
            result[key] = diag[key]
        
        return result
    
    except Exception as e:
        result["error"] = f"Unhandled exception: {str(e)}"
        logger.exception(f"Error scoring transcript: {e}")
        return result


def _parse_json_response(text: str) -> Optional[Dict]:
    """Extract and parse JSON from LLM response text."""
    try:
        # Try to find JSON object in the response
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            json_str = text[start:end]
            return json.loads(json_str)
        return None
    except (json.JSONDecodeError, ValueError):
        logger.warning(f"Failed to parse JSON from: {text[:200]}")
        return None


def _add_cot_instruction(user_prompt: str) -> str:
    """Add chain-of-thought instruction to user prompt."""
    cot_instruction = """
Before providing your JSON response, work through this reasoning:
1. Quote the most relevant evidence from the transcript.
2. Quote any disconfirming evidence (arguing for a LOWER score).
3. State which anchor level fits and why.
4. Then provide your JSON output.
"""
    return user_prompt + "\n" + cot_instruction
