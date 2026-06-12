"""
Unit tests for scoring/diagnostics.py

Test diagnostic grouping logic.
"""

import unittest
from scoring.diagnostics import diagnostic_groupings


class TestDiagnosticGroupings(unittest.TestCase):
    """Test diagnostic flag generation."""
    
    def test_severity_zero(self):
        """All flags should be False when severity = 0"""
        result = diagnostic_groupings(0, 2, 3)
        self.assertFalse(result['lifetime_psychosis'])
        self.assertFalse(result['sips_bips'])
        self.assertFalse(result['sips_apss'])
        self.assertFalse(result['caarms_blips'])
        self.assertFalse(result['caarms_subthreshold_frequency'])
        self.assertFalse(result['caarms_subthreshold_intensity'])
    
    def test_lifetime_psychosis(self):
        """severity=6, freq_lt_py>=4 → lifetime_psychosis=True"""
        result = diagnostic_groupings(6, 2, 5)
        self.assertTrue(result['lifetime_psychosis'])
        self.assertFalse(result['sips_bips'])
        self.assertTrue(result['caarms_blips'])
    
    def test_sips_bips(self):
        """severity=6, freq_lt_py<4 → sips_bips=True"""
        result = diagnostic_groupings(6, 2, 2)
        self.assertFalse(result['lifetime_psychosis'])
        self.assertTrue(result['sips_bips'])
        self.assertFalse(result['caarms_blips'])
    
    def test_sips_apss(self):
        """3<=severity<=5, freq_pm>=3 → sips_apss=True"""
        result = diagnostic_groupings(4, 3, 2)
        self.assertTrue(result['sips_apss'])
    
    def test_sips_apss_false(self):
        """3<=severity<=5, freq_pm<3 → sips_apss=False"""
        result = diagnostic_groupings(4, 2, 2)
        self.assertFalse(result['sips_apss'])
    
    def test_caarms_subthreshold_frequency(self):
        """severity=6, freq_lt_py==3 → caarms_subthreshold_frequency=True"""
        result = diagnostic_groupings(6, 2, 3)
        self.assertTrue(result['caarms_subthreshold_frequency'])
    
    def test_caarms_subthreshold_intensity(self):
        """3<=severity<=5, freq_lt_py>=3 → caarms_subthreshold_intensity=True"""
        result = diagnostic_groupings(3, 2, 3)
        self.assertTrue(result['caarms_subthreshold_intensity'])


if __name__ == '__main__':
    unittest.main()
