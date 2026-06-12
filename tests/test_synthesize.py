"""
Unit tests for scoring/synthesize.py

Test all cases from PSYCHS Table 3.
"""

import unittest
from scoring.synthesize import synthesize_p2_severity


class TestSynthesizeP2Severity(unittest.TestCase):
    """Test synthesis logic from PSYCHS Table 3."""
    
    def test_same_scores(self):
        """D=3, T=3 → 3 (same)"""
        severity, rule, secondary_used = synthesize_p2_severity(3, 3)
        self.assertEqual(severity, 3)
        self.assertEqual(rule, "same")
        self.assertFalse(secondary_used)
    
    def test_even_diff(self):
        """D=4, T=2 → 3 (even diff, average)"""
        severity, rule, secondary_used = synthesize_p2_severity(4, 2)
        self.assertEqual(severity, 3)
        self.assertEqual(rule, "even_avg")
        self.assertFalse(secondary_used)
    
    def test_adjacent_higher_with_secondary(self):
        """D=4, T=3, dist=4, interf=2 → 4 (adjacent, distress >= higher)"""
        severity, rule, secondary_used = synthesize_p2_severity(4, 3, distress_score=4, interference_score=2)
        self.assertEqual(severity, 4)
        self.assertEqual(rule, "adjacent_higher")
        self.assertTrue(secondary_used)
    
    def test_adjacent_lower_without_secondary(self):
        """D=4, T=3, dist=2, interf=2 → 3 (adjacent, both secondary < higher)"""
        severity, rule, secondary_used = synthesize_p2_severity(4, 3, distress_score=2, interference_score=2)
        self.assertEqual(severity, 3)
        self.assertEqual(rule, "adjacent_lower")
        self.assertTrue(secondary_used)
    
    def test_odd_non_adjacent_tiebreaker(self):
        """D=5, T=2, dist=4, interf=3 → 4 (odd non-adjacent, avg=3.5, tiebreaker)"""
        severity, rule, secondary_used = synthesize_p2_severity(5, 2, distress_score=4, interference_score=3)
        self.assertEqual(severity, 4)  # avg=3.5, distress >= 4 (higher), so use higher
        self.assertEqual(rule, "odd_tiebreaker_higher")
        self.assertTrue(secondary_used)
    
    def test_zero_scores(self):
        """D=0, T=0 → 0"""
        severity, rule, secondary_used = synthesize_p2_severity(0, 0)
        self.assertEqual(severity, 0)
        self.assertEqual(rule, "same")
        self.assertFalse(secondary_used)
    
    def test_odd_avg_no_secondary(self):
        """D=5, T=3, avg=4 (whole number) → 4, no secondary consulted"""
        severity, rule, secondary_used = synthesize_p2_severity(5, 3)
        self.assertEqual(severity, 4)
        self.assertEqual(rule, "odd_avg")
        self.assertFalse(secondary_used)
    
    def test_diff_5_odd_tiebreaker(self):
        """D=6, T=1, avg=3.5 → 4 (with dist/interf) or 3 (without)"""
        # Without secondary: should use lower (1)
        severity, rule, secondary_used = synthesize_p2_severity(6, 1)
        self.assertEqual(severity, 3)
        self.assertEqual(rule, "odd_tiebreaker_lower")
        self.assertTrue(secondary_used)
        
        # With secondary >= higher (6): should use higher
        severity, rule, secondary_used = synthesize_p2_severity(6, 1, distress_score=6, interference_score=None)
        self.assertEqual(severity, 4)
        self.assertEqual(rule, "odd_tiebreaker_higher")
        self.assertTrue(secondary_used)
    
    def test_missing_score_error(self):
        """None values should return error"""
        severity, rule, secondary_used = synthesize_p2_severity(None, 3)
        self.assertIsNone(severity)
        self.assertEqual(rule, "error_missing_score")
        self.assertFalse(secondary_used)


if __name__ == '__main__':
    unittest.main()
