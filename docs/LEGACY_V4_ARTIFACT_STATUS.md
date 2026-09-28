# V4 artifact status

The current publication is `campaign_v41_verified/`, campaign `v41-463e8d1eca6867a9`. Its `validation_gate.json` passed with exact-genotype replay. Use its `manifest.json`, `report_v41.json`, stage datasets and figures together: they share one code, configuration, site and module-library identity.

The following paths are retained only as historical outputs. None supplied candidates or figures to the verified campaign.

| Historical path | Why it is superseded | Current output |
|---|---|---|
| `results_v4/` | Predates the corrected southern arrival edge and V4.1 construction stages. | `campaign_v41_verified/runs/main_s*.json` and `phenotypes/main_s*/` |
| `results_capacity_v4/` | Uses the earlier capacity/occupancy interpretation. | `campaign_v41_verified/data/capacity_scenarios.csv` |
| `selections_v4_day48/` | Its manifest includes zero-resident selected layouts. | `campaign_v41_verified/data/selection_manifest.json` and `phenotypes/day48_s*/` |
| `module_catalogue_v4/` | Predates explicit program compositions and population ratios. | `campaign_v41_verified/data/module_library.json` and `boards/module_library_catalogue.png` |
| `report_v4/` | References the earlier selections and model. | `campaign_v41_verified/report_v41.json` and `report_v41.md` |
| `campaign_v41/` | Preliminary V4.1 rerun before the strict shared-edge attachment grammar. Its source hash differs from the verified build. | `campaign_v41_verified/` |

The verified campaign regenerates the base, 48-day-user and 24 capacity-scenario studies from the current Python model. The historical files remain available to audit how the model changed, but should not be cited as current architectural findings.
