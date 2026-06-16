#!/usr/bin/env python3
"""
Unit tests for DMI summary generator.
"""

import unittest
from scripts.compute_dmi import (
    classify_direction,
    classify_spread_direction,
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

    def test_classify_spread_direction(self):
        # Test little_changed (|delta| < 0.015)
        self.assertEqual(classify_spread_direction(0.00), 'spread_little_changed')
        self.assertEqual(classify_spread_direction(0.01), 'spread_little_changed')
        self.assertEqual(classify_spread_direction(-0.01), 'spread_little_changed')

        # Test slightly (0.015 <= |delta| < 0.08)
        self.assertEqual(classify_spread_direction(0.05), 'spread_widened_slightly')
        self.assertEqual(classify_spread_direction(-0.05), 'spread_narrowed_slightly')
        self.assertEqual(classify_spread_direction(0.07), 'spread_widened_slightly')

        # Test materially (|delta| >= 0.08)
        self.assertEqual(classify_spread_direction(0.10), 'spread_widened_materially')
        self.assertEqual(classify_spread_direction(-0.10), 'spread_narrowed_materially')

    def test_classify_unemployment_direction(self):
        # Test little_changed
        self.assertEqual(classify_unemployment_direction(0.00), 'unemployment_little_changed')
        self.assertEqual(classify_unemployment_direction(0.09), 'unemployment_little_changed')

        # Test edged
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
                'income_pressure_spread': 0.28,
                'income_pressure_tilt': 0.28,
                'most_pressured_group': 'Q1',
                'least_pressured_group': 'Q5',
                'unemployment': 4.4
            }
        }

        facts, summary = build_release_summary(current)

        self.assertIn('lower_income_more_pressure', facts)
        self.assertTrue(facts['lower_income_more_pressure'])
        self.assertEqual(facts['most_pressured_group'], 'Q1')
        self.assertEqual(facts['least_pressured_group'], 'Q5')
        self.assertEqual(facts['overall_direction'], 'no_prior')
        self.assertIn('February 2026', summary)
        self.assertIn('higher measured pressure', summary)
        self.assertIn('DMI Median of 6.85', summary)
        self.assertIn('Income Pressure Spread of 0.28', summary)

    def test_build_release_summary_with_prior(self):
        prior = {
            'release_id': '2026-01',
            'data_through_label': 'January 2026',
            'metrics': {
                'dmi_median': 6.68,
                'dmi_stress': 6.86,
                'income_pressure_spread': 0.30,
                'income_pressure_tilt': 0.30,
                'most_pressured_group': 'Q1',
                'least_pressured_group': 'Q5',
                'unemployment': 4.3
            }
        }

        current = {
            'release_id': '2026-02',
            'data_through_label': 'February 2026',
            'metrics': {
                'dmi_median': 6.85,
                'dmi_stress': 7.01,
                'income_pressure_spread': 0.28,
                'income_pressure_tilt': 0.28,
                'most_pressured_group': 'Q1',
                'least_pressured_group': 'Q5',
                'unemployment': 4.4
            }
        }

        facts, summary = build_release_summary(current, prior)

        self.assertIn('median_delta_mom', facts)
        self.assertAlmostEqual(facts['median_delta_mom'], 0.17, places=2)
        self.assertAlmostEqual(facts['spread_delta_mom'], -0.02, places=2)
        self.assertAlmostEqual(facts['tilt_delta_mom'], -0.02, places=2)
        self.assertEqual(facts['overall_direction'], 'rose_modestly')
        # |spread_delta| = 0.02 >= 0.015 (spread_little_changed threshold)
        # and < 0.08 (spread_slightly threshold), so "narrowed_slightly"
        self.assertEqual(facts['spread_direction'], 'spread_narrowed_slightly')
        self.assertIn('rose modestly', summary)
        self.assertIn('narrowed slightly', summary)
        self.assertIn('edging up to 4.4', summary)

    def test_build_release_summary_negative_tilt(self):
        current = {
            'release_id': '2026-02',
            'data_through_label': 'February 2026',
            'metrics': {
                'dmi_median': 6.85,
                'dmi_stress': 7.01,
                'income_pressure_spread': 0.10,
                'income_pressure_tilt': -0.10,
                'most_pressured_group': 'Q5',
                'least_pressured_group': 'Q1',
                'unemployment': 4.4
            }
        }

        facts, summary = build_release_summary(current)

        self.assertFalse(facts['lower_income_more_pressure'])
        self.assertTrue(facts['higher_income_more_pressure'])
        self.assertEqual(facts['most_pressured_group'], 'Q5')
        self.assertIn('higher-income households', summary)

    def test_build_release_summary_similar_tilt(self):
        # |tilt| <= 0.02 -> pressure_similar_across_bottom_top
        current = {
            'release_id': '2026-02',
            'data_through_label': 'February 2026',
            'metrics': {
                'dmi_median': 6.85,
                'dmi_stress': 7.01,
                'income_pressure_spread': 0.10,
                'income_pressure_tilt': 0.01,
                'most_pressured_group': 'Q3',
                'least_pressured_group': 'Q5',
                'unemployment': 4.4
            }
        }

        facts, _ = build_release_summary(current)

        self.assertFalse(facts['lower_income_more_pressure'])
        self.assertFalse(facts['higher_income_more_pressure'])
        self.assertTrue(facts['pressure_similar_across_bottom_top'])


if __name__ == '__main__':
    unittest.main()
