# SCIN acne-label feasibility specification

Status: proposed metadata and annotation logic only; no labels created
Review date: 2026-10-19

## Scope

This specification defines how official SCIN fields could be evaluated for the AI Skin Analyzer's **visible acne-like features** task. It does not authorize acquisition, create a label mapping, diagnose acne, or approve training. The project definition remains visual and non-diagnostic: positive means rubric-defined visible acne-like features in an assessable facial region; negative means the required region is assessable and those features are explicitly absent.

Authoritative field definitions come from the [official SCIN schema](https://github.com/google-research-datasets/scin/blob/main/dataset_schema.md). Collection and privacy context comes from the [official study](https://jamanetwork.com/journals/jamanetworkopen/fullarticle/2826506), [README](https://github.com/google-research-datasets/scin/blob/main/README.md), and [Google Research overview](https://research.google/blog/scin-a-new-resource-for-representative-dermatology-images/).

## Field-level interpretation

| SCIN field | Documented meaning | Permitted feasibility use | Must not be interpreted as |
|---|---|---|---|
| `case_id` | Case identifier, typically stable across releases | Join case and label metadata; group all case images | Subject/person identity or proof that different cases are different people |
| `release` | Semantic release identifier | Pin provenance and avoid mixing versions silently | A label version by itself |
| `related_category` | Contributor-reported category, including `ACNE` and `LOOKS_HEALTHY` | Candidate discovery and stratified audit | Dermatologist-confirmed positive or negative |
| `body_parts_HEAD_OR_NECK` | Contributor-reported affected body area | Broad location filter for candidate cases | Proof that a face or required facial subregion is visible |
| `image_*_shot_type` | Submission prompt: `CLOSE_UP`, `AT_AN_ANGLE`, or `AT_DISTANCE` | Describe view type and audit case/image composition | Proof of lesion visibility, quality, or full-face framing |
| `dermatologist_gradable_for_skin_condition_*` | Whether each dermatologist could determine a condition from case images | Require affirmative gradability for positive-candidate review; retain each reviewer result | Negative label when false; false can mean typical skin, insufficient information, multiple conditions, or quality issues |
| `dermatologist_skin_condition_label_name` | Original differential condition names from dermatologist reviewers | Strongest candidate evidence for an explicit acne-family term | Exhaustive image-level presence/absence annotation |
| `dermatologist_skin_condition_confidence` | Confidence 1–5 corresponding to each raw label | Preserve confidence and define later acceptance thresholds | Probability or calibrated certainty |
| `weighted_skin_condition_label` | Rank-reweighted, summed, normalized mapped differential labels | Secondary aggregated candidate evidence; audit raw-to-mapped terminology | Ground truth, image-level visibility, or an automatic binary label |
| `age_group` | Optional self-reported age bucket, beginning at 18–29 | Adult demographic audit if lawfully authorized | Exact age, skin age, or a facial label |
| Fitzpatrick and Monk fields | Phototype/skin-tone estimates or self-report | Representation audit only | Normal/Dry/Oily skin type |

## Proposed positive-candidate tiers

These tiers are queries for a future approved metadata audit, not training labels.

### Tier P0 — discovery only

- `related_category=ACNE`.

This is self-report and may be useful for locating candidate cases. It is insufficient for a project positive.

### Tier P1 — dermatologist-supported case candidate

- exact release is pinned;
- `body_parts_HEAD_OR_NECK=true`;
- at least one `dermatologist_gradable_for_skin_condition_*` value is true; and
- `dermatologist_skin_condition_label_name` or its documented mapped counterpart contains a predeclared acne-family term.

The allowed acne-family terminology must be defined from official SCIN label documentation before the audit, with no substring guessing. Preserve every original term, mapped term, reviewer confidence, reviewer count, rank, and weight.

### Tier P2 — stronger agreement candidate

- meets P1; and
- where multiple dermatologists reviewed a case, a predeclared agreement/confidence rule is met.

Most submissions in the official study were reviewed by one dermatologist, so P2 cannot be required without first determining the resulting missingness and selection bias. A single-reviewer case is not automatically invalid, but its evidence tier must remain explicit.

None of P0–P2 proves that the relevant lesion is visible in each case image. SCIN labels apply to a case of up to three images, and the condition may be visible in only one view.

## Binary target mapping

No direct SCIN-to-project binary mapping is approved.

| Project state | Documentary rule today | Future evidence required |
|---|---|---|
| `positive=1` | Not assignable from documents alone | Eligible source lot; P1/P2 case evidence; approved image-level rubric; required facial region visible; reviewer confirmation that qualifying acne-like features are present; adjudication as required |
| `negative=0` | Not available from current SCIN labels | Eligible source lot; full required facial region assessable; explicit trained-reviewer confirmation that no qualifying feature is present; no inference from silence, `LOOKS_HEALTHY`, or another diagnosis |
| `unknown=-1` | Default for absent or insufficient task evidence | No valid task review, unsupported field combination, or consent/eligibility unresolved |
| `uncertain=-1` | Masked | Assessable image but lesion/artifact or reviewer evidence is ambiguous |
| `unassessable=-1` | Masked | Required region removed, redacted, cropped, occluded, poorly lit, blurred, too distant, or otherwise inadequate |

Unknown, uncertain, and unassessable must remain separate in an annotation overlay even if all are masked for model loss.

## Genuine-negative protocol required later

Because SCIN is condition-seeking and differentials are not exhaustive absence annotations, a genuine negative can only be established through a separate, approved review:

1. Confirm the source lot, consent/custom-annotation scope, and reviewer authorization.
2. Define the exact facial regions and acne-like visual features before viewing data.
3. Require sufficient resolution, exposure, focus, and coverage of every required region.
4. Use at least two trained reviewers where feasible, blinded to self-reported `related_category` and nonessential demographic fields.
5. Assign one of `positive`, `negative`, `unknown`, `uncertain`, or `unassessable`; never force a binary decision.
6. Require explicit reviewer confirmation of absence for a negative.
7. Adjudicate disagreements and preserve individual reviews, rubric version, timestamps, and provenance.
8. Measure agreement and report negative counts by independent case/group, not image row.
9. Prevent source/category shortcuts by auditing whether self-report, shot type, redaction pattern, or case composition predicts the label.

This protocol is not authorized by Phase 5C.

## Facial coverage gate

The official study states that potentially identifying areas, including facial areas, were redacted. `HEAD_OR_NECK` and shot type cannot prove that a full face, cheek, forehead, chin, or eye region survives that processing. A metadata-only audit can quantify candidate cases and views but cannot enable labels.

Before any image-level review, a separate approval must specify:

- the minimum facial regions required by the acne task;
- whether a partial-face model would be redesigned instead of forcing SCIN into a full-face architecture;
- non-identity visual-suitability criteria;
- access controls, retention, and no-export rules;
- permitted reviewer roles; and
- a stop condition if too few cases preserve the required coverage.

## Leakage and split implications

- Treat `case_id` as the minimum group boundary.
- Keep all one-to-three images from a case together.
- Join cases connected by a confirmed exact duplicate or derivative relationship before splitting.
- Do not infer subject identity or subject overlap.
- If no authorized subject identifier exists, disclose that subject-disjoint evaluation cannot be guaranteed.
- Build the final holdout only after label eligibility and grouping are resolved.

## Metadata-only audit specification for a future approval

A narrowly scoped audit should read only the official tabular release fields needed to answer feasibility questions. It should avoid image retrieval and exclude optional demographic fields unless a separate, justified fairness audit requires them.

Minimum proposed fields:

- `case_id`, `release`, `source`;
- `body_parts_HEAD_OR_NECK`;
- shot-type presence, without fetching image content;
- dermatologist gradability fields;
- raw dermatologist condition terms and aligned confidence values;
- weighted mapped condition labels; and
- provider-documented duplicate/missing-file indicators if available.

Required aggregate outputs:

- counts of independent cases by P0/P1/P2 candidate tier;
- head/neck candidate counts and shot-type completeness;
- number of dermatologists per candidate case;
- raw and mapped acne-family term distributions under a predeclared exact mapping;
- gradability and missing-label distributions;
- overlap between self-reported and dermatologist-supported acne candidates;
- known duplicate impact at the case-group level; and
- no raw participant-level rows, paths, filenames, demographics, or small sensitive cells in public reports.

No image paths should be opened, resolved, printed, or downloaded. Audit code and private outputs would require a separate approval and data-handling plan.

## Acceptance criteria

SCIN may advance from metadata feasibility to a controlled visual-suitability review only if:

- rights/privacy review permits the exact task and metadata handling;
- the release and acne terminology mapping are pinned;
- enough independent P1/P2 head/neck cases exist for a predeclared study design;
- metadata missingness and single-reviewer selection do not make the study indefensible;
- known duplicates can be contained by grouping;
- a genuine-negative annotation route is permitted; and
- the owner separately approves access to images under a non-identity protocol.

Failure to meet these criteria should move SCIN to `unsuitable` for this task without creating substitute labels.
