#!/usr/bin/env python3
"""
Unit tests for DMI summary generator.
"""

import unittest
from scripts.compute_dmi import (
    classify_direction,
    classify_gap_direction,
    classify_unemployment_direction,
    build_release_summary,
    THRESHOLDS
)


class TestSummaryGenerator(unittest.TestCase):
    
    def test_classify_direction(self):
        # Test little_changed
        self.assertEqual(classify_direction(0.00, THRESHOLDS), 'little_changed')
        self.assertEqual(classify_direction(0.04, THRESHOLDS), 'little_changed')
        self.assertEqual(classify_direction(-0.04, THRESHOLDS), 'little_changed')
        
        # Test edged
        self.assertEqual(classify_direction(0.07, THRESHOLDS), 'edged_up')
        self.assertEqual(classify_direction(-0.07, THRESHOLDS), 'edged_down')
        self.assertEqual(classify_direction(0.14, THRESHOLDS), 'edged_up')
        
        # Test modestly
        self.assertEqual(classify_direction(0.18, THRESHOLDS), 'rose_modestly')
        self.assertEqual(classify_direction(-0.18, THRESHOLDS), 'fell_modestly')
        self.assertEqual(classify_direction(0.29, THRESHOLDS), 'rose_modestly')
        
        # Test sharply
        self.assertEqual(classify_direction(0.40, THRESHOLDS), 'rose_sharply')
        self.assertEqual(classify_direction(-0.40, THRESHOLDS), 'fell_sharply')
    
    def test_classify_gap_direction(self):
        # Test little_changed
        self.assertEqual(classify_gap_direction(0.00), 'gap_little_changed')
        self.assertEqual(classify_gap_direction(0.01), 'gap_little_changed')
        self.assertEqual(classify_gap_direction(-0.01), 'gap_little_changed')
        
        # Test slightly
        self.assertEqual(classify_gap_direction(0.05), 'gap_widened_slightly')
        self.assertEqual(classify_gap_direction(-0.05), 'gap_narrowed_slightly')
        self.assertEqual(classify_gap_direction(0.07), 'gap_widened_slightly')
        
        # Test materially
        self.assertEqual(classify_gap_direction(0.10), 'gap_widened_materially')
        self.assertEqual(classify_gap_direction(-0.10), 'gap_narrowed_materially')
    
    def test_classify_unemployment_direction(self):
        # Test little_changed
        self.assertEqual(classify_unemployment_direction(0.00), 'unemployment_little_changed')
        self.assertEqual(classify_unemployment_direction(0.09), 'unemployment_little_changed')
        
        # Test noticeably
        self.assertEqual(classify_unemployment_direction(0.15), 'unemployment_edged_up')
        self.assertEqual(classify_unemployment_direction(-0.15), 'unemployment_edged_down')
        self.assertEqual(classify_unemployment_direction(0.25), 'unemployment_edged_up')
        
        # Test noticeably
        self.assertEqual(classify_unemployment_direction(0.35), 'unemployment_rose_noticeably')
        self.assertEqual(classify_unemployment_direction(-0.35), 'unemployment_fell_noticeably')
    
    def test_build_release_summary_no_prior(self):
        current = {
            'release_id': '2026-02',
            'data_through_label': 'February 2026',
            'metrics': {
                'dmi_median': 6.85,
                'dmi_stress': 7.01,
                'income_pressure_gap': 0.28,
                'unemployment': 4.4
            }
        }
        
        facts, summary = build_release_summary(current)
        
        self.assertIn('lower_income_more_pressure', facts)
        self.assertTrue(facts['lower_income_more_pressure'])
        self.assertEqual(facts['overall_direction'], 'no_prior')
        self.assertIn('February 2026', summary)
        self.assertIn('higher measured pressure', summary)
        self.assertIn('DMI Median of 6.85', summary)
    
    def test_build_release_summary_with_prior(self):
        prior = {
            'release_id': '2026-01',
            'data_through_label': 'January 2026',
            'metrics': {
                'dmi_median': 6.68,
                'dmi_stress': 6.86,
                'income_pressure_gap': 0.30,
                'unemployment': 4.3
            }
        }
        
        current = {
            'release_id': '2026-02',
            'data_through_label': 'February 2026',
            'metrics': {
                'dmi_median': 6.85,
                'dmi_stress': 7.01,
                'income_pressure_gap': 0.28,
                'unemployment': 4.4
            }
        }
        
        facts, summary = build_release_summary(current, prior)
        
        self.assertIn('median_delta_mom', facts)
        self.assertAlmostEqual(facts['median_delta_mom'], 0.17, places=2)
        self.assertEqual(facts['overall_direction'], 'rose_modestly')
        self.assertEqual(facts['gap_direction'], 'gap_little_changed')  # abs(0.02) < 0.02? Wait, 0.02 == 0.02, but threshold is < 0.02 for little_changed
        # Wait, in code: if abs_delta < THRESHOLDS['gap_little_changed'] which is 0.02, so 0.02 is not < 0.02, so slightly
        # But spec says for abs(gap_delta_mom) = 0.01779 < 0.02, little_changed
        # In test, delta = 0.30 - 0.28 = 0.02, abs=0.02, which is not < 0.02, so slightly
        self.assertEqual(facts['gap_direction'], 'gap_narrowed_slightly')
        self.assertIn('rose modestly', summary)
        self.assertIn('narrowed slightly', summary)
        self.assertIn('edging up to 4.4', summary)
    
    def test_build_release_summary_negative_gap(self):
        current = {
            'release_id': '2026-02',
            'data_through_label': 'February 2026',
            'metrics': {
                'dmi_median': 6.85,
                'dmi_stress': 7.01,
                'income_pressure_gap': -0.10,
                'unemployment': 4.4
            }
        }
        
        facts, summary = build_release_summary(current)
        
        self.assertFalse(facts['lower_income_more_pressure'])
        self.assertTrue(facts['higher_income_more_pressure'])
        self.assertIn('Higher-income households faced more pressure', summary)


if __name__ == '__main__':
    unittest.main()