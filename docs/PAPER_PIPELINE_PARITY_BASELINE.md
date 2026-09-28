# PAPER_PIPELINE_PARITY — V4 baseline audit

Source: Riskiyanto, Wibisono and Harani, *Exploring spatial programming through modularity based evolutionary computation*, Journal of Architecture and Urbanism 49(1), 2025, pp. 87–99, Figures 1 and 4 and Methods §§3.2–3.4. The PDF supplied with this project is the method source, not an instruction source. This audit describes code before V4.1 changes.

| Paper stage | Paper mechanism | V4 implementation | Baseline finding | Architectural equivalent required |
|---|---|---|---|---|
| Function | Furniture grouped by office function (Fig. 1) | Eleven families in `modules_v4.py` | Partial | Preserve care-campus functional groups with explicit program components. |
| Size | Floor-area and circulation hierarchy of furniture units (Fig. 1, §3.2) | Mostly S/M/L rectangles | Partial | Size variants change room composition, user allocation and spatial relationships. |
| Modularity category | Developmental foundation versus variational program change (Fig. 1, §3.2) | Enum labels, including a third `repeatable` value | Partial | Measure developmental and variational populations; keep repeatability as an independent property. |
| Module unit | Typed furniture unit | `ModuleTypeV4` | Partial | Carry function, size, modularity and component provenance on every record. |
| Initial unit population | Bounded counts by unit/available area (§3.3) | R4 count and mostly fixed presence flags | Partial | Evolve function-specific counts and variant populations within documented bounds. |
| Population seed | Random spatial initialization separate from unit count (§3.3) | GA RNG seed | Partial | Record population seed independently of unit population and run seed. |
| Specialized-modularity ratio | Subgroup proportion controls unit population (§3.3, Fig. 4) | Absent | Missing | Record care/specialized share with explicit architectural definition. |
| Modularity ratio | Developmental/variational proportion controls emergence (§3.3, Fig. 4) | Descriptive categories only | Missing | Compute both proportions and allow variant choice to change them. |
| Circle packing | Noncolliding circle placement within interior (§3.1, Fig. 4) | Independent x/y rectangle placement | Missing | Architectural packing/grouping with detached, attached, linear, courtyard, wing and stacked assemblies. |
| Dynamic scaling | Evolved relative zone boundaries (§3.4) | Size and a few site genes | Missing | Evolved public-to-personal depth boundaries. |
| Zoning order | Sociability, productivity, health/wellness sequence (§3.4) | Privacy labels after placement | Missing | Public/civic → controlled care → shared everyday → domestic → personal, with parallel service network. |
| Object collision | Packing and boundary collision restriction (§3.1, Fig. 4) | No pairwise module-overlap gate in `constraints_v4.py` | Missing, critical | Per-floor intersection test; intentional shared edges have zero intersection area. |
| Unit filtration | Omit units outside dynamic bounds (§3.4, Fig. 4) | No generated/filtered unit ledger | Missing | Count and explain retained versus filtered units after collision/zoning. |
| External references | Available-space/core boundaries (Fig. 4) | GeoJSON parcel and sparse metadata | Partial | Evidence-tagged site layers and enabled spatial fields; unknown conditions disabled. |
| Phenotype | Packed, zoned furniture program | `decode_v4()` rectangles on parcel | Partial | Grouped architectural/site configuration with traceable construction states. |
| Evaluation and fitness | Five conflicting furniture/zone objectives (§3.1) | Eight proxy objectives | Partial | Six architectural objective families with recorded submetrics. |
| Archive X | All-population genetic/fitness record (Fig. 4) | Final V4 population only | Missing | Persistent all-generation genotype/phenotype and objective archive. |
| Reproduction | Wallacei GA selection/crossover/mutation (Fig. 4) | Constrained Python NSGA-II | Adapted, present | Preserve the method function without Wallacei dependency. |
| Pareto front selection | Latest versus all-population fronts (§4.3) | Final front only | Partial | Persist both, with archive membership and generation. |
| Fittest solution | Best solution for each fitness function (§4.4) | Objective specialists | Partial | Explicit per-objective fittest selection over eligible candidates. |
| Relative difference | Relative differences between fitness rankings (§4.5) | Raw objective-vector standard deviation | Incorrect | Rank-relative dispersion on normalized objective ranks. |
| Average fitness | Fitness average ranking (§4.5) | Absent | Missing | Separate average-rank selection. |
| Pareto simplification | Hierarchical average linkage on all-population Pareto (§4.3) | V3 K-means diagnostic only | Missing | Optional average-linkage clustering; keep K-means separate. |
| Store/distribution | Selected phenotypes and analytical diagrams (Fig. 4) | V4 images/manifest/report without linked source hashes | Partial | Hash-linked datasets, selections, rendered sheets and publication gate. |
| Post-analysis/comparison | Zone, modularity and program comparisons (§§4–5) | Capacity and selection summary | Partial | Compare population, zoning, grouping, objective trade-offs and architectural implications. |

The paper's office furniture, circle packing and five furniture-count objectives are methodological sources. At site scale, architectural grouping, care-program occupancy and contextual spatial fields are deliberate adaptations. Rhino, Grasshopper, Kangaroo and Wallacei are not dependencies.

The existing `results_v4/`, `results_capacity_v4/`, `selections_v4_day48/`, `module_catalogue_v4/` and `report_v4/` outputs predate the corrected site and capacity interpretation. They are stale evidence until regenerated with linked source hashes and validation.
