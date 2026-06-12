"""
Integration test for scoring/chain.py

Test the 8-step chain with a mock backend.
"""

import unittest
from typing import Dict, Any
from scoring.chain import score_transcript


class MockLLMBackend:
    """Mock LLM backend for testing."""
    
    def generate(self, prompt_system: str, prompt_user: str) -> str:
        """Return mock JSON responses based on step type."""
        # Detect step from prompt
        if "screening" in prompt_system.lower():
            return '{"suspicious_content_present": true, "screening_evidence": "Test evidence"}'
        elif "description" in prompt_system.lower():
            return '{"description_score": 3, "supporting_evidence": "Test support", "disconfirming_evidence": "Test disconfirm", "description_reasoning": "Test reason"}'
        elif "tenacity" in prompt_system.lower():
            return '{"tenacity_score": 2, "doubt_expressed": true, "doubt_source": "when_asked", "tenacity_reasoning": "Test reason"}'
        elif "distress" in prompt_system.lower():
            return '{"distress_score": 2, "distress_evidence": "Test evidence", "distress_cause_confirmed": true, "distress_reasoning": "Test reason"}'
        elif "interference" in prompt_system.lower():
            return '{"interference_score": 2, "behavioral_change": "Test change", "social_impact": "Test impact", "interference_reasoning": "Test reason"}'
        elif "frequency" in prompt_system.lower():
            return '{"frequency_pm_score": 2, "frequency_lt_py_score": 3, "frequency_evidence": "Test evidence", "frequency_reasoning": "Test reason"}'
        else:
            return '{}'


class TestScoringChain(unittest.TestCase):
    """Test 8-step scoring chain."""
    
    def test_scoring_chain_zs(self):
        """Test scoring chain with zero-shot condition."""
        backend = MockLLMBackend()
        transcript = "The participant reported suspicious ideas about coworkers."
        
        result = score_transcript(transcript, backend, condition='ZS')
        
        # Check that result has all required keys
        self.assertIn('p2_severity_final', result)
        self.assertIn('description_score', result)
        self.assertIn('tenacity_score', result)
        self.assertIn('frequency_pm_score', result)
        self.assertIn('lifetime_psychosis', result)
        
        # Check that scores are present
        self.assertIsNotNone(result['p2_severity_final'])
        self.assertIsNotNone(result['description_score'])
        self.assertEqual(result['description_score'], 3)
    
    def test_screening_negative(self):
        """Test when screening is negative (no suspicious content)."""
        class NoSuspicionBackend(MockLLMBackend):
            def generate(self, prompt_system: str, prompt_user: str) -> str:
                if "screening" in prompt_system.lower():
                    return '{"suspicious_content_present": false, "screening_evidence": "No suspicious content"}'
                return super().generate(prompt_system, prompt_user)
        
        backend = NoSuspicionBackend()
        transcript = "Normal interview with no concerning content."
        
        result = score_transcript(transcript, backend, condition='ZS')
        
        # All scores should be 0
        self.assertFalse(result['suspicious_content_present'])
        self.assertEqual(result['description_score'], 0)
        self.assertEqual(result['tenacity_score'], 0)
        self.assertEqual(result['p2_severity_final'], 0)
        self.assertEqual(result['frequency_pm_score'], 0)
        self.assertEqual(result['frequency_lt_py_score'], 0)
    
    def test_llm_calls_counted(self):
        """Test that LLM calls are counted."""
        backend = MockLLMBackend()
        transcript = "Test transcript"
        
        result = score_transcript(transcript, backend, condition='ZS')
        
        # Should have multiple LLM calls (screening, description, tenacity, etc.)
        self.assertGreater(result['llm_calls'], 0)
    
    def test_cot_condition(self):
        """Test chain-of-thought condition."""
        backend = MockLLMBackend()
        transcript = "Test transcript"
        
        result = score_transcript(transcript, backend, condition='CoT')
        
        # Should still produce valid results
        self.assertIsNotNone(result['p2_severity_final'])
        self.assertIsNotNone(result['description_score'])


if __name__ == '__main__':
    unittest.main()
