{
  "schema_version": "0.1.0",
  "generated_at": "2026-04-19T00:00:00Z",
  "reference_period": "2026-03",
  "headline_spec": "baseline",
  "specifications": [
    {
      "spec_id": "baseline",
      "label": "DMI Baseline",
      "summary": "Headline DMI using current inflation inputs and U-3 unemployment.",
      "release_json": "/data/outputs/dmi_release_2026-03.json",
      "metrics": {
        "dmi_median": 7.53,
        "dmi_stress": 7.57,
        "income_pressure_gap": -0.08,
        "slack_measure": "U3"
      }
    },
    {
      "spec_id": "slack_plus",
      "label": "DMI Slack+",
      "summary": "Companion DMI using broader labor-market slack.",
      "release_json": "/data/outputs/dmi_release_2026-03_slack_plus.json",
      "metrics": {
        "dmi_median": 0.0,
        "dmi_stress": 0.0,
        "income_pressure_gap": 0.0,
        "slack_measure": "U6"
      }
    },
    {
      "spec_id": "core",
      "label": "DMI Core",
      "summary": "Companion DMI using core inflation inputs.",
      "release_json": "/data/outputs/dmi_release_2026-03_core.json",
      "metrics": {
        "dmi_median": 0.0,
        "dmi_stress": 0.0,
        "income_pressure_gap": 0.0,
        "slack_measure": "U3"
      }
    }
  ],
  "robustness_assessment": {
    "headline_direction_consistent": true,
    "distributional_pattern_consistent": true,
    "notes": [
      "The main directional result is consistent across Baseline, Slack+, and Core."
    ]
  }
}
