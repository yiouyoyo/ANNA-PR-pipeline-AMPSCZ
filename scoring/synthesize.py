"""Synthesize P2 severity from Description, Tenacity, Distress, and Interference.

Implements PSYCHS Figure 1 / Table 3 logic exactly.
The LLM never produces p2_severity_final directly — Python always synthesizes it.
"""


def synthesize_p2_severity(description_score, tenacity_score, distress_score=None, interference_score=None):
    """
    Synthesize final P2 severity from co-primary (Description, Tenacity) and secondary (Distress, Interference).
    
    Args:
        description_score (int or None): 0-6, from LLM step 2
        tenacity_score (int or None): 0-6, from LLM step 3
        distress_score (int or None): 0-6, from LLM step 5 (only if tiebreaker needed)
        interference_score (int or None): 0-6, from LLM step 6 (only if tiebreaker needed)
    
    Returns:
        tuple: (final_severity: int 0-6, rule_applied: str, secondary_used: bool)
        
    Rules from PSYCHS manual:
    - If D == T: return D (same)
    - If diff is even: return average (no rounding, integer division)
    - If diff == 1 (adjacent): consult secondary; if secondary >= higher, return higher; else return lower
    - If diff == 3 or 5: compute average; if whole number, return it; else consult secondary
    - Fallback: round to nearest integer
    """
    
    if description_score is None or tenacity_score is None:
        return None, "error_missing_score", False
    
    D = description_score
    T = tenacity_score
    diff = abs(D - T)
    higher = max(D, T)
    lower = min(D, T)
    
    # Case 1: Same scores
    if diff == 0:
        return D, "same", False
    
    # Case 2: Even difference → take average (no rounding needed for even diff)
    if diff % 2 == 0:
        return (D + T) // 2, "even_avg", False
    
    # Case 3: Adjacent (diff == 1) → consult secondary if available
    if diff == 1:
        if (distress_score is not None and distress_score >= higher) or \
           (interference_score is not None and interference_score >= higher):
            return higher, "adjacent_higher", True
        return lower, "adjacent_lower", True
    
    # Case 4: Odd non-adjacent (diff == 3 or 5)
    if diff == 3 or diff == 5:
        avg = (D + T) / 2
        if avg == int(avg):
            # Average is a whole number → use it without consulting secondary
            return int(avg), "odd_avg", False
        else:
            # Average is fractional → consult secondary for tiebreaker
            if (distress_score is not None and distress_score >= higher) or \
               (interference_score is not None and interference_score >= higher):
                return higher, "odd_tiebreaker_higher", True
            return lower, "odd_tiebreaker_lower", True
    
    # Fallback (should not reach here given the above cases)
    return round((D + T) / 2), "fallback", False
