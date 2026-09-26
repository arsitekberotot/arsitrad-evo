# Evolutionary Catalogue — arsitrad-evo (Campaign v2)

The evolutionary story of **SPATIAL PHENOTYPES**, not just objectives. Chain shown:

```
GENERATION -> GENOTYPE -> SPATIAL PHENOTYPE -> PERFORMANCE -> SELECTION
```

Run: `pop_size=80, generations=60, seed=42` (Campaign v2 seed). Snapshots at
Gen **0 / 10 / 20 / 40 / 60** (Gen 80 not reached: `GAConfig.generations` caps
at 60 — clamped, not fabricated). Diagrammatic only; see
`../PHENOTYPE_SCHEMA_v1.md` for the prototype schema.

## Boards (`evo_board_*.png`)

| Board | Content |
|-------|---------|
| `population_evolution` | Grid: one diverse feasible phenotype per snapshot generation — watch module population & programme change across evolution |
| `pareto_representative` | Final front, 6 max-min diverse feasible reps (not only winners) |
| `objective_extremes` | Best plan per objective (9 panels) |
| `balanced` | Lowest objective-spread selections + parallel-coordinate profile |
| `final_shortlist` | Plan + radar (1−objective) per shortlisted candidate |
| `convergence` | feasible / rank1 / soft_cv over generations (GENERATION→PERFORMANCE) |

## Thumbnails (`evo_g{gen}_rep{r}.png`)

20 miniatures (5 gens × 4 diverse reps), each plan rendered by `visualize.plot_layout`.
Every record in `evo_manifest.json` links **seed + generation + genotype (programme:
`n_R4`, `has_*` module set) + module population + 9 objectives + feasibility**.

## Selection methods

- **Diverse reps** (`_select_diverse`): max-min spread in objective space — returns
  distinct spatial phenotypes, not clustered near-winners.
- **Objective extremes**: argmin per objective.
- **Balanced / relative-difference**: min (max−min) objective spread.

## Observed evolution (this run)

Gen 0 rep0: infeasible (cv=75.96), 13 modules, n_R4=4 → converges to feasible
(cv=0) by Gen 10; programme and module population refine across generations.

`ponytail:` representative selection is max-min over the final population only;
upgrade path = per-generation archive with crowding on programme distance.
