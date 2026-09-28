# PAPER_PIPELINE_PARITY — V4.1

Campaign `v41-463e8d1eca6867a9`. All stage datasets are persisted under `stages/`.

| Stage | Paper mechanism | Architectural equivalent | Records | Code / dataset |
|---|---|---|---:|---|
| function_size_modularity | Figure 1 module-library axes | function size modularity | 29 | `arsitrad_evo/program_v41.py:catalogue` / `stages/function_size_modularity.jsonl` |
| module_unit | Figure 1 furniture module unit | module unit | 4736 | `arsitrad_evo/program_v41.py:module_record` / `stages/module_unit.jsonl` |
| initial_unit_population | Figure 4 initial population / Method 3.3 | initial unit population | 4736 | `arsitrad_evo/pipeline_v41.py:decode_v41` / `stages/initial_unit_population.jsonl` |
| population_seed | Figure 4 population seed / Method 3.3 | population seed | 4736 | `arsitrad_evo/pipeline_v41.py:decode_v41` / `stages/population_seed.jsonl` |
| modularity_ratios | Figure 4 specialized and general modularity ratios | modularity ratios | 4736 | `arsitrad_evo/program_v41.py:population_summary` / `stages/modularity_ratios.jsonl` |
| architectural_packing_grouping | Figure 4 circle packing, architecturally adapted | architectural packing grouping | 4736 | `arsitrad_evo/pipeline_v41.py:_place` / `stages/architectural_packing_grouping.jsonl` |
| dynamic_zoning | Figure 4 dynamic scaling and zoning | dynamic zoning | 4736 | `arsitrad_evo/context_v41.py:zoning_state` / `stages/dynamic_zoning.jsonl` |
| object_collision | Figure 4 object collision | object collision | 4736 | `arsitrad_evo/pipeline_v41.py:collision_gate` / `stages/object_collision.jsonl` |
| unit_filtration | Figure 4 unit filtration | unit filtration | 4736 | `arsitrad_evo/pipeline_v41.py:decode_v41` / `stages/unit_filtration.jsonl` |
| site_external_references | Figure 4 external references | site external references | 4736 | `arsitrad_evo/context_v41.py:SiteContext` / `stages/site_external_references.jsonl` |
| architectural_phenotype | Figure 4 phenotype | architectural phenotype | 4736 | `arsitrad_evo/pipeline_v41.py:decode_v41` / `stages/architectural_phenotype.jsonl` |
| fitness_evaluation | Figure 4 evaluation and fitness assignment | fitness evaluation | 4736 | `arsitrad_evo/objectives_v41.py:evaluate_objectives_v41` / `stages/fitness_evaluation.jsonl` |
| constraint_evaluation | Architectural extension: model-feasibility gate | constraint evaluation | 4736 | `arsitrad_evo/constraints_v41.py:evaluate_constraints_v41` / `stages/constraint_evaluation.jsonl` |
| nsga2_reproduction | Figure 4 Wallacei reproduction, Python NSGA-II equivalent | nsga2 reproduction | 29 | `arsitrad_evo/nsga2_v41.py:run_v41` / `stages/nsga2_reproduction.jsonl` |
| all_generation_archive | Figure 4 Archive X | all generation archive | 29 | `arsitrad_evo/archive_v41.py:phenotype_record` / `stages/all_generation_archive.jsonl` |
| pareto_front_selection | Figure 4 Pareto front selection | pareto front selection | 5 | `arsitrad_evo/selections_v41.py:pareto_set` / `stages/pareto_front_selection.jsonl` |
| fittest_selection | Figure 4 fittest solution selection | fittest selection | 5 | `arsitrad_evo/selections_v41.py:select_v41` / `stages/fittest_selection.jsonl` |
| relative_difference_selection | Figure 4 relative-difference selection | relative difference selection | 5 | `arsitrad_evo/selections_v41.py:relative_difference` / `stages/relative_difference_selection.jsonl` |
| average_fitness_selection | Figure 4 average-fitness selection | average fitness selection | 5 | `arsitrad_evo/selections_v41.py:average_fitness_rank` / `stages/average_fitness_selection.jsonl` |
| store_distribution | Figure 4 store and distribution | store distribution | 1 | `arsitrad_evo/campaign_v41.py:build_campaign` / `stages/store_distribution.jsonl` |
| post_analysis_comparison | Figure 4 post-analysis and comparison | post analysis comparison | 1 | `arsitrad_evo/campaign_v41.py:_report` / `stages/post_analysis_comparison.jsonl` |

Furniture circle packing becomes architectural grouping; dynamic office zoning becomes ordered care-campus depth with parallel service; Wallacei reproduction becomes constrained Python NSGA-II.

Unknown service access, TPST exposure, wind, noise, odour, dust, drainage, vegetation and directional expansion remain disabled and [TO VERIFY].
