# Replacement dataset requirements

Status: acquisition specification only; no dataset is approved or downloaded
Last reviewed: 2026-10-19

## Purpose and governing constraints

This document defines the minimum requirements for a replacement dataset for the AI Skin Analyzer. It does not approve a source, authorize acquisition, or establish clinical validity. The existing 2,400-image collection remains unresolved and ineligible (`reports/PHASE_5A_PROVENANCE_TRIAGE.md:5-24`; `docs/DATA_CARD.md:1-7`). Every proposed source must pass the source-lot gates in `docs/DATASET_ELIGIBILITY_POLICY.md:5-35` before any image is obtained, annotated, split, or used.

Permissions for private training, model/weight distribution, and raw-image or metadata redistribution must be decided separately. Public accessibility and an academic-use statement are not substitutes for documented permission, consent or another reviewed lawful basis, minor safeguards, retention and withdrawal rules, and the contemplated facial-analysis use.

## Task definitions and label requirements

| Output | Required construct | Allowed usable target | Masked states | Evidence required before enabling |
|---|---|---|---|---|
| `skin_type` | A predeclared, observable skin-surface oiliness/dryness construct assessed under controlled capture conditions. It is not Fitzpatrick skin type and must not be described as a diagnosis. | Exactly one of `Normal=0`, `Dry=1`, or `Oily=2`, assigned under a validated rubric. Mixed presentations require an explicit rule rather than forced classification. | `unknown`, `uncertain`, `unassessable` | Construct-valid rubric; capture/lighting requirements; trained annotators or validated instrumentation; inter-rater reliability; adjudication; representation and subgroup analysis. |
| `has_acne` | Presence of one or more rubric-defined visible acne-like features in a specified, assessable facial region. It is a visual research label, not a medical diagnosis. | `positive=1`; `negative=0` only when the required region is visible and qualifying features are explicitly confirmed absent. | `unknown`, `uncertain`, `unassessable` | Feature/region definitions; minimum visibility; verified positive and verified negative examples; annotator qualifications; reliability and adjudication evidence. |
| `has_dark_circle` | Rubric-defined visible periorbital darkening in an assessable region, with controls for illumination, shadow, cosmetics, occlusion, camera processing, and skin-tone variation. | `positive=1`; `negative=0` only when the required periorbital region is assessable and defined darkening is explicitly confirmed absent. | `unknown`, `uncertain`, `unassessable` | Region/lighting rubric; verified positive and verified negative examples; annotator qualifications; reliability and adjudication evidence. |
| `skin_age` | One owner-approved target only: verified chronological age at capture, perceived age, or a separately validated appearance-based construct. These targets are not interchangeable. | A value with explicit units, provenance, capture-date relationship, and uncertainty. Perceived age should retain rater count and dispersion. An appearance score needs its own validated scale. | `unknown`, `uncertain`, `unassessable` as applicable | Precise target definition; lawful and consented age use; authoritative label lineage; uncertainty model; age-appropriate minor safeguards; evaluation protocol. |

The `skin_age` head must remain disabled until the owner selects one exact construct and every evidence requirement is met. A chronological-age dataset must not be marketed as “skin age.” Apparent/perceived age must not be treated as chronological truth.

Missing values remain missing. `-1`, blank, `unknown`, `uncertain`, and `unassessable` must never become class `0`. The masking and output conventions in `docs/MODEL_ARCHITECTURE.md:7-26` remain controlling.

## Source-lot evidence requirements

Before acquisition, record for each independently governed source lot:

1. Original publisher, authoritative landing page, release/version, persistent identifier, and retrieval date.
2. Copyright or database-rights holder and the full applicable license/terms captured at review time.
3. Explicit decisions for the intended facial-analysis ML use, commercial/portfolio use, derivative labels, trained model/weight distribution, and raw-data/metadata redistribution.
4. Consent or other reviewed lawful basis, purpose communicated to participants, geographic constraints, withdrawal process, retention/deletion process, and re-identification prohibitions.
5. Minor inclusion or exclusion, age verification, guardian consent where applicable, and restrictions on sensitive-age processing.
6. Collection method, capture devices/settings, transformations, inclusion/exclusion rules, and known quality or selection biases.
7. Annotation constructs, label schema, negative-label semantics, annotator qualifications, agreement/adjudication, label uncertainty, and version lineage.
8. Stable item and source-lot identifiers plus authorized subject, case, session, or derivative-family keys. Do not create identity keys with face recognition or appearance matching.
9. Dataset size, independent-group count, task-specific usable counts, missingness, class distribution, and authorized demographic/quality metadata.
10. A named reviewer, decision date, evidence locations, unresolved conditions, and one eligibility state from `docs/DATASET_ELIGIBILITY_POLICY.md`.

Silence or ambiguity means blocked, not permitted.

## Grouping and split requirements

Build a grouping graph before any split is generated. Its connected components must keep together:

- byte-identical files;
- confirmed crops, re-encodes, augmentations, or other derivatives;
- all images sharing a reliable, authorized subject identifier;
- all images in a source-defined case/session when that unit could leak target information; and
- any additional provider-defined dependence unit.

Perceptual similarity is review evidence only. It must not be used to infer identity. If no reliable subject key is available, report that subject-disjoint evaluation cannot be guaranteed.

A future split specification must be versioned and deterministic, assign whole groups rather than rows, and reserve an untouched final holdout. The same source, duplicate family, subject, case, or session may not cross splits at the relevant grouping level. Existing publisher partitions may be retained only after their grouping guarantees and leakage risks are verified.

## Quantitative acceptance requirements

Do not invent a fixed sample count before eligibility and label audits. For every enabled task, a prospective analysis must justify the required number of independent groups from the intended confidence interval, minimum detectable performance difference, expected prevalence, subgroup analysis plan, and attrition from masking.

At minimum:

- both binary classes must appear as independently verified labels in training, validation, and the final holdout;
- every skin-type class must have sufficient independent groups in every evaluation partition;
- evaluation counts must be reported as valid labels and independent groups, not raw image rows;
- no subject or derivative group may inflate more than one split;
- uncertainty and missingness must be reported by source, task, split, and any lawfully available audit subgroup;
- a final holdout must be large enough for predeclared uncertainty intervals and must not be used for model or threshold selection; and
- a source-held-out or independently sourced evaluation should be used when feasible to measure source-specific shortcut learning.

## Multi-source interoperability

Each row in a future private manifest must retain `source_lot_id`, original record identifier, release/version, item checksum, task-specific label provenance, assessability, uncertainty, grouping keys, and permission flags. Harmonization creates a versioned overlay; it must not overwrite original labels.

Labels from different sources may be combined only when their constructs and thresholds are shown to be compatible. Otherwise, keep the task masked for that source or model it as a distinct task. Preserve `source_id` for audit and stratified evaluation, but do not offer it as an input feature. Audit whether source, resolution, crop style, background, device, watermark, or capture protocol predicts the target. A head should not be enabled when positive and negative classes are effectively separable by source alone.

## Privacy, fairness, and portfolio requirements

- Minimize collected fields and access; separate sensitive source records from the public repository.
- Do not expose face images, original filenames, participant identifiers, private manifests, contracts, consent forms, access tokens, or signed URLs in Git.
- Do not infer protected traits, identity, or health conditions from appearance. Use only authorized demographic metadata for predeclared fairness audits.
- Document unknown demographic coverage rather than filling it through inference.
- Assess performance and label missingness across authorized skin-tone, age-range, sex/gender, device, illumination, and source groups where those fields are ethically and legally usable.
- State that photographic predictions are not diagnoses and may be affected by lighting, cosmetics, processing, skin tone, and capture domain.
- A reproducible public portfolio should contain acquisition instructions, schemas, synthetic fixtures, validation code, version pins, checksums of public release manifests where allowed, and aggregate audit results—not restricted data.

## Dataset acceptance gate

A source lot may proceed to a separately approved acquisition or annotation phase only when:

- an authoritative source and version are identified;
- rights, consent/lawful basis, minor safeguards, retention, and withdrawal have been reviewed;
- exact private-training and intended model-release uses are affirmatively permitted;
- raw redistribution has an explicit decision and defaults to prohibited;
- task constructs and negative-label semantics are compatible or the incompatible outputs are masked;
- grouping metadata and leakage limitations are documented;
- a security and privacy handling plan exists;
- the reviewer records `verified_allowed`, `verified_training_only`, or narrowly defined `conditional` status under the project policy; and
- the owner separately approves the acquisition action and any required registration, contract, fee, or terms acceptance.

Until then, all four outputs remain disabled for replacement-data training.
