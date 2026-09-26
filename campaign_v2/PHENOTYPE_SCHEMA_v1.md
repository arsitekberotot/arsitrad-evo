# Phenotype Schema v1 — arsitrad-evo (FROZEN @ f50bf7b)
*Contract for the schematic architectural prototype produced from a genotype.
Semantically validated: **36/36 tests pass** (incl. 20 gate tests). This schema
is the stable interface between the evolutionary engine and all downstream
visualisation / PA5 schematic development. **Diagrammatic, not finished design.***

---

## 1. Purpose & non-goals

`build_prototype(Phenotype) -> Prototype` converts an abstract module-rectangle
solution into a **readable but still schematic** architectural prototype: internal
kit-of-parts, orientation, anchors, privacy gradient, circulation skeletons,
sightline exposure, open-space types, stacking, groupings, threshold sequence.

**It does NOT produce:** parcel/site precision, detailed room dimensions,
structural systems, materiality, regulatory/safeguarding compliance, or building
services design. Internal parts are labelled **zones** with relative positions
inside the module rectangle; no part states an area (that would fabricate
unsupported room dimensions).

## 2. Provenance discipline (enforced)

Every internal component and connection carries exactly one tag:

| Tag | Meaning |
|-----|---------|
| `[PA5 CORPUS]` | Grounded in the PA5 corpus (module type, relation, floors). |
| `[DESIGN HYPOTHESIS]` | Reasonable diagrammatic inference; not corpus-fact. |
| `[TO VERIFY]` | Must be checked by the architect before use. |

Where a fact is unsupported it is **omitted** and recorded in `to_verify`.

## 3. Top-level Prototype fields

| Field | Type | Provenance | Notes |
|-------|------|-----------|-------|
| `candidate`, `rep_index`, `seed`, `program` | scalar | — | traceability to shortlist/seed |
| `site_w`, `site_h` | float | [PA5 CORPUS] | 90.0 × 61.5 m site frame |
| `residents`, `day_users`, `gfa`, `footprint` | float | [PA5 CORPUS] | from genotype capacity/area |
| `landscape_frac`, `landscape_area` | float | [PA5 CORPUS] | from genotype |
| `modules` | list[[ModuleNode](#4-modulenode)] | mixed | one per placed instance |
| `connections` | list[[Connection](#5-connection)] | mixed | corpus adjacency edges |
| `sightlines` | list[[Sightline](#6-sightline)] | [TO VERIFY] | geometric exposure checks |
| `open_spaces` | list[[OpenSpace](#7-openspace)] | [DESIGN HYPOTHESIS] | enclosure-classified |
| `courtyards` | list | [DESIGN HYPOTHESIS] | derived subset (COURTYARD only) |
| `privacy_gradient` | list | [DESIGN HYPOTHESIS] | PUBLIC→PERSONAL module ordering |
| `threshold_sequence` | list | [DESIGN HYPOTHESIS] | public→domestic interface steps |
| `stacking` | list | [PA5 CORPUS] | multi-floor modules |
| `groupings` | list | [DESIGN HYPOTHESIS] | MUST/NEAR connectivity clusters |
| `objectives` | dict | [PA5 CORPUS] | the 9 objective values |
| `provenance_log` | list[str] | — | how each structure was derived |
| `to_verify` | list[str] | — | all `[TO VERIFY]` items |
| `design_hypotheses` | list[str] | — | all `[DESIGN HYPOTHESIS]` items |

## 4. ModuleNode

`{inst_id, code, name, x, y, w, d, floors, privacy, orientation, entrance_anchor, connection_anchors[3], interface, parts[]}`

- `orientation`: `"EW"|"NS"` long-axis of the rectangle [DH].
- `entrance_anchor`: edge-midpoint facing nearest neighbour [DH].
- `connection_anchors`: the other 3 edge-midpoints [DH].
- `interface`: `public|protected|service|domestic|shared` [PA5 CORPUS→DH].
- `parts[]`: internal kit-of-parts `{name, x, y, w, d, privacy, provenance, note}`
  — relative zones, **no stated area**.

## 5. Connection

`{a_id, b_id, a_code, b_code, kind, provenance, circulations[]}`

- `kind`: corpus relation `MUST|NEAR|SCREENED` (only these are drawn).
- `circulations[]`: skeleton types from `{resident, care, service, public, controlled}`.
  **Rule (tested):** a connection touching private residential territory (R4) is
  **never** `public`; a `SCREENED`/controlled R4 link is `controlled` +
  `resident`/`care`. `public` only when both ends are public-facing and no
  private territory is crossed.

## 6. Sightline

`{from_id, from_code, to_id, to_code, relation, distance, exposed, screened_by[], provenance}`

- Computed for **all** `PROHIBITED` or private↔public-facing (safeguarding-sensitive)
  pairs. Straight segment between the two rectangles' nearest points; `exposed`
  = no other module's rectangle intersects the segment.
- `exposed=True` → recorded in `to_verify` (screening required).
- **Diagrammatic** [TO VERIFY]: not a regulatory sightline/angle study.

## 7. OpenSpace

`{cx, cy, area_cells, enclosure, space_type, provenance}`

Enclosure = number of 4 cardinal rays from the cell that hit built mass before
the site edge (ray-cast on a coarse grid). Classification (explicitly schematic):

| `enclosure` | `space_type` |
|-------------|--------------|
| 3–4 | `COURTYARD` |
| 2 | `POCKET COURT / THRESHOLD EDGE` |
| 0–1 | `OPEN LANDSCAPE` |

Contiguous same-type cells merge into one zone. `courtyards` = the `COURTYARD`
subset (back-compat).

## 8. Stacking, groupings, threshold sequence

- `stacking`: modules with `floors>1` (R4 is always single-storey per corpus).
- `groupings`: connected components over MUST/NEAR edges.
- `threshold_sequence`: modules ordered public→shared→protected/service→domestic.

## 9. Validation (tests/test_phenotype_gen.py — 20 tests)

sightline exposure (clear/screened/sensitive-only) · open-space classification
(courtyard enclosed / open-landscape present / enclosure thresholds) ·
circulation typing (A0-R4 not public / private never public / public pair /
care+service) · module anchors present & valid · orientation · stacking ·
privacy gradient ordering · kit-part tagging · deterministic build & render ·
end-to-end no-public-to-private.

## 10. Known simplifications

- `ponytail:` sightline exposure is a coarse segment-vs-rect test; upgrade path =
  angular view-cone study + landscape screening model.
- `ponytail:` open-space enclosure uses a 24×24 grid ray-cast; upgrade path =
  vector isovist per zone.
- Kit-of-parts zones are heuristic fractions of the module rectangle; replace
  with corpus-derived internal layouts when available.
