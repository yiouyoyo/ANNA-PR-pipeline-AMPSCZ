"""Diagnostic groupings based on final severity and frequency scores."""


def diagnostic_groupings(severity, frequency_pm, frequency_lt_py):
    """
    Determine diagnostic flags based on PSYCHS/CAARMS criteria.
    
    Args:
        severity (int): 0-6 final P2 severity
        frequency_pm (int): 0-6 past month frequency
        frequency_lt_py (int): 0-6 lifetime/past year frequency
    
    Returns:
        dict: Diagnostic flags with bool values
              {
                  'lifetime_psychosis': bool,
                  'sips_bips': bool,
                  'sips_apss': bool,
                  'caarms_blips': bool,
                  'caarms_subthreshold_frequency': bool,
                  'caarms_subthreshold_intensity': bool
              }
    
    Criteria:
    - If severity == 0: all flags False
    - lifetime_psychosis: severity == 6 AND frequency_lt_py >= 4
    - sips_bips: severity == 6 AND frequency_lt_py < 4
    - sips_apss: 3 <= severity <= 5 AND frequency_pm >= 3
    - caarms_blips: severity == 6 AND frequency_lt_py >= 4 (same as lifetime_psychosis)
    - caarms_subthreshold_frequency: severity == 6 AND frequency_lt_py == 3
    - caarms_subthreshold_intensity: 3 <= severity <= 5 AND frequency_lt_py >= 3
    """
    
    if severity == 0:
        return {
            "lifetime_psychosis": False,
            "sips_bips": False,
            "sips_apss": False,
            "caarms_blips": False,
            "caarms_subthreshold_frequency": False,
            "caarms_subthreshold_intensity": False,
        }
    
    return {
        "lifetime_psychosis": severity == 6 and frequency_lt_py >= 4,
        "sips_bips": severity == 6 and not (frequency_lt_py >= 4),
        "sips_apss": 3 <= severity <= 5 and frequency_pm >= 3,
        "caarms_blips": severity == 6 and frequency_lt_py >= 4,
        "caarms_subthreshold_frequency": severity == 6 and frequency_lt_py == 3,
        "caarms_subthreshold_intensity": 3 <= severity <= 5 and frequency_lt_py >= 3,
    }
